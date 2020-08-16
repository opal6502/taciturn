
# This file is part of the Taciturn web automation framework.
#
# Taciturn is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Tactiurn is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Tactiurn.  If not, see <https://www.gnu.org/licenses/>.


import sys
import os

import signal

from abc import ABC, abstractmethod
from collections import namedtuple
from importlib.machinery import SourceFileLoader

from datetime import timedelta
from time import sleep, time

from sqlalchemy import and_

from taciturn.config import get_config, get_options, init_logger, get_logger, get_session
from taciturn.db.base import TaciturnUser, Application, AppAccount, JobId
from taciturn.datetime import datetime_now_tz, datetime_fromtimestamp_tz

from taciturn.applications.login import (
    ApplicationHandlerEndOfListException,
    ApplicationHandlerUserPrivilegeSuspendedException
)


class TaciturnJob(ABC):
    __jobname__ = 'taciturn_job'
    __appnames__ = None

    def __init__(self):
        self.accounts = dict()
        self.options = get_options()
        self.config = get_config()
        self.session = get_session()

        self._job_number = self._new_job_number()
        self.log = init_logger(self.job_name())
        self._load_accounts()

        self.log.info(f"Initializing taciturn job #{self._job_number}.")

    def job_name(self):
        return f'{self.__jobname__}.{self._job_number}'

    def _new_job_number(self):
        job_id_row = self.session.query(JobId).filter_by(id=1).one()
        new_job_id = job_id_row.job_id + 1
        job_id_row.job_id = new_job_id
        self.session.commit()
        return new_job_id

    def _load_accounts(self):
        self.log.info("Loading accounts for job.")

        # some input validation for self.__appnames__:
        if self.__appnames__ is None and not isinstance(self.__appnames__, list):
            raise TypeError('Job needs to define self.__appnames__ as a list of apps the job interacts with')
        if self.options.user is None:
            raise TypeError('User name must be provided in the options with -u')
        self.username = self.options.user[0]
        if self.options.stop is not None and self.options.stop is True:
            self.stop_no_quota = True
        else:
            self.stop_no_quota = False

        for app_name in self.__appnames__:
            app_account = self.session.query(AppAccount).\
                filter(and_(AppAccount.application_id == Application.id,
                            AppAccount.taciturn_user_id == TaciturnUser.id,
                            TaciturnUser.name == self.username,
                            Application.name == app_name
                            )).one_or_none()
            if app_account is None:
                raise RuntimeError("User '{}' has no '{}' account.".format(self.username, app_name))
            else:
                self.accounts[app_name] = app_account

    def get_account(self, app_name):
        try:
            return self.accounts[app_name]
        except KeyError:
            raise TaciturnJobNoAccountException("Error: no account for app '{}' loaded.".format(app_name))

    def get_taciturn_user(self, user_name):
        return self.session.query(TaciturnUser).filter(TaciturnUser.name == user_name).one()

    @abstractmethod
    def run(self):
        pass


class TaciturnJobLoader:
    def __init__(self, jobs_dir=None):
        self.config = get_config()
        self.jobs_dir = jobs_dir or self._determine_jobs_dir()
        self.jobs = dict()

    def _determine_jobs_dir(self):
        job_dir = os.environ.get('TACITURN_JOB_ROOT') or \
                  self.config.get('taciturn_job_root')
        if job_dir is None and self.config.get('taciturn_root') is not None:
            job_dir = os.path.join(self.config.get('taciturn_root'), 'jobs')
        else:
            raise RuntimeError("Could not determine jobs directory from environment and config.")

        if not os.path.isdir(job_dir):
            raise RuntimeError("Job dir '{}' does not exist".format(job_dir))

        return job_dir

    def load_job(self, job_name):
        job_full_name = os.path.join(self.jobs_dir, job_name+'.py')

        if not os.path.exists(job_full_name):
            raise RuntimeError("Job '{}' doesn't exist at: {}".format(job_name, job_full_name))

        job_module = SourceFileLoader('site_config', job_full_name).load_module()
        if not hasattr(job_module, 'job'):
            raise TypeError("Job file does not define 'job' object: {}".format(job_full_name))
        return job_module.job()


class TaskExecutor:
    def __init__(self, driver=None, job_name=None, call=None, retries=None, handler_stats=None):
        self.driver = driver
        self.job_name = job_name
        self.call = call
        self.retries = retries or 1
        self.config = get_config()
        self.log = get_logger()
        self.handler_stats = handler_stats

        self.total_time = 0
        self.operations_total = 0
        self.task_start_time = 0
        self.retry = 0
        self.screenshot_n = 0

        # handler SIGTERM, which Jenkins will send to stop a process:
        signal.signal(signal.SIGTERM, self._signal_handler_report_exit)

    def _signal_handler_report_exit(self, signum, frame):
        self.log_report(incomplete=True)
        sys.exit(1)

    def run(self):
        try_n = 0
        self.task_start_time = time()

        for try_n in range(1, self.retries + 1):
            self.retry = try_n
            try:
                self.log.info(f"Task: starting try {try_n} of {self.retries}")
                self.call()
            except KeyboardInterrupt:
                self.log.exception("Task: incomplete: cancelled by keyboard interrupt.")
                self.log_report(incomplete=True)
                sys.exit(1)
            except SystemExit:
                self.log.exception("Task: incomplete: cancelled by system exit.")
                self.log_report(incomplete=True)
                sys.exit(1)
            except SystemError:
                self.log.exception("Task: incomplete: cancelled by system error.")
                self.log_report(incomplete=True)
                sys.exit(1)
            except ApplicationHandlerEndOfListException:
                self.log.info("Task: end of list encountered.")
                break
            except ApplicationHandlerUserPrivilegeSuspendedException:
                self.log.warning("Task: incomplete: user privileges revoked by application.")
                self.take_screenshot()
                self.log_report(incomplete=True)
                return
            except Exception as e:
                self.log.exception(f"Task: failed: try {try_n} of {self.retries}; exception occurred.")
                self.take_screenshot()
                if try_n >= self.retries:
                    self.log_report(incomplete=True)
                    raise e
            else:
                break
        else:
            self.log.error(f"Task: Failed after {try_n} tries.")

        self.total_time += time() - self.task_start_time
        self.operations_total += self.handler_stats.get_operation_count()

        self.log_report()

    def log_report(self, incomplete=False):
        if incomplete is True:
            self.log.info(f"Task: incomplete: "
                          f"operations = {self.handler_stats.get_operation_count()}; "
                          f"failures = {self.retry-1}; "
                          f"start_time = '{datetime_fromtimestamp_tz(self.task_start_time)}'; "
                          f"end_time = '{datetime_now_tz()}'; "
                          f"task_time = '{timedelta(seconds=self.total_time+(time() - self.task_start_time))}';")
            self.log.info("Task: stopped prematurely.")
        else:
            self.log.info(f"Task: complete: "
                          f"operations = {self.handler_stats.get_operation_count()}; "
                          f"failures = {self.retry-1}; "
                          f"start_time = '{datetime_fromtimestamp_tz(self.task_start_time)}'; "
                          f"end_time = '{datetime_now_tz()}'; "
                          f"task_time = '{timedelta(seconds=self.total_time)}';")
            self.log.info("Task: finished.")

    def take_screenshot(self):
        screenshot_filename = os.path.join(self.config['screenshots_dir'], f'{self.job_name}.{self.screenshot_n}.png')
        self.driver.save_screenshot(screenshot_filename)
        self.log.info(f"Saved screenshot at {screenshot_filename}")
        self.screenshot_n += 1


class RoundTaskExecutor(TaskExecutor):
    def __init__(self,
                 driver=None,
                 job_name=None,
                 call=None,
                 handler_stats=None,
                 quota=None,
                 max=None,
                 period=None,
                 retries=None,
                 stop_no_quota=False):

        super().__init__(driver=driver, job_name=job_name, call=call, handler_stats=handler_stats, retries=retries)
        self.quota = quota
        self.max = max
        self.period = period  # datetime.timedelta() object
        self.stop_no_quota = stop_no_quota

        self.failed_rounds = 0
        self.round_retries = 0
        self.total_rounds = self.max // self.quota
        self.task_timeout = self.period.total_seconds() / self.total_rounds
        self.task_sleep_start = None

        self.round_stats = RoundExecutorStats()

    def run(self):
        try_n = 0   # for use in loop else clause

        for round_n in range(1, self.total_rounds+1):
            self.log.info(f"Task: starting round {round_n} of {self.total_rounds}.")
            self.log.info(f"Task: timeout between rounds is {timedelta(seconds=self.task_timeout)}.")
            self.task_start_time = time()
            self.round_retries = 0

            for try_n in range(1, self.retries+1):
                try:
                    self.log.info(f"Task: starting try {try_n} of {self.retries}.")
                    self.call()
                except KeyboardInterrupt:
                    self.log.exception("Task: cancelled by keyboard interrupt.")
                    self.log_report(incomplete=True)
                    sys.exit(1)
                except SystemExit:
                    self.log.exception("Task: incomplete: cancelled by system exit.")
                    self.log_report(incomplete=True)
                    sys.exit(1)
                except SystemError:
                    self.log.exception("Task: incomplete: cancelled by system error.")
                    self.log_report(incomplete=True)
                    sys.exit(1)
                except ApplicationHandlerEndOfListException:
                    self.log.info("Task: end of list encountered.")
                    break
                except ApplicationHandlerUserPrivilegeSuspendedException:
                    self.log.warning("Task: incomplete: user privileges revoked by application.")
                    self.take_screenshot()
                    self.log_report(incomplete=True)
                    return
                except Exception as e:
                    self.log.exception(f"Task: round {round_n} of {self.total_rounds} failed, "
                                       f"try {try_n} of {self.retries}; exception occurred.")
                    self.take_screenshot()
                    self.round_retries += 1
                    if try_n >= self.retries:
                        self.log_report(incomplete=True)
                        raise e
                else:
                    break
            else:
                self.log.error(f"Task: Round {round_n} of {self.total_rounds} failed after {try_n} tries.")
                self.failed_rounds += 1

            task_time = time() - self.task_start_time
            task_sleep_time = self.task_timeout - task_time
            if (task_sleep_time < 0 or
                    round_n >= self.total_rounds or self.operations_total >= self.max):
                task_sleep_time = 0

            self.total_time += task_time
            operation_count = self.handler_stats.get_operation_count()
            self.operations_total += operation_count

            if operation_count < self.quota:
                self.log.warning(f"Task: couldn't fulfill quota; "
                                 f"expected {self.quota} operations, actual {operation_count}.")
                if self.stop_no_quota:
                    self.log.warning("Task: Quota unfulfilled, stopping.")
                    self.log_report(incomplete=True)
                    return
            elif operation_count == self.max:
                self.log.info(f"Task: round complete with {operation_count} operations.")

            self.round_stats.add_round(operations=operation_count,
                                       failures=try_n-1,
                                       start_time=datetime_fromtimestamp_tz(self.task_start_time),
                                       end_time=datetime_now_tz(),
                                       task_time=timedelta(seconds=task_time),
                                       task_sleep_time=timedelta(seconds=task_sleep_time))

            # last round, no need to sleep:
            if round_n >= self.total_rounds or self.operations_total >= self.max:
                break

            self.log.info(f"Task: sleeping for {timedelta(seconds=task_sleep_time)} until next round.")

            try:
                self.task_sleep_start = time()
                sleep(task_sleep_time)
            except KeyboardInterrupt:
                self.log.exception("Task: cancelled by keyboard interrupt.")
                self.log_report(incomplete=True)
                sys.exit(1)
            except SystemExit:
                self.log.exception("Task: incomplete: cancelled by system exit.")
                self.log_report(incomplete=True)
                sys.exit(1)
            except SystemError:
                self.log.exception("Task: incomplete: cancelled by system error.")
                self.log_report(incomplete=True)
                sys.exit(1)

        self.log_report()

    def log_report(self, incomplete=False):
        round_n = 0
        total_operations = 0
        total_failures = 0
        total_task_time = timedelta(seconds=0)
        total_sleep_time = timedelta(seconds=0)
        total_job_time = timedelta(seconds=0)
        for round_n, round in enumerate(self.round_stats.all_rounds(), 1):
            self.log.info(f"Task: complete round #{round_n}: "
                          f"operations = {round.operations}; "
                          f"failures = {round.failures}; "
                          f"start_time = '{round.start_time}'; "
                          f"end_time = '{round.end_time}'; "
                          f"task_time = '{round.task_time}'; "
                          f"task_sleep_time = {round.task_sleep_time}")
            total_operations += round.operations
            total_failures += round.failures
            total_task_time += round.task_time
            total_sleep_time += round.task_sleep_time
            total_job_time += round.task_time + round.task_sleep_time
        if incomplete is True:
            round_n += 1
            task_time = timedelta(seconds=self.total_time+(time() - self.task_start_time))
            sleep_time = timedelta(seconds=0)
            if self.task_sleep_start is not None:
                sleep_time = timedelta(seconds=(time() - self.task_sleep_start))
            self.log.info(f"Task: incomplete round #{round_n}: "
                          f"operations = {self.handler_stats.get_operation_count()}; "
                          f"failures = {self.round_retries}; "
                          f"start_time = '{datetime_fromtimestamp_tz(self.task_start_time)}'; "
                          f"end_time = '{datetime_now_tz()}'; "
                          f"task_time = '{task_time}';")
            total_operations += self.handler_stats.get_operation_count()
            total_failures += self.round_retries
            total_task_time += task_time
            total_sleep_time += sleep_time
            total_job_time += task_time + sleep_time

        # finally, print job grand totals:
        self.log.info(f"Job: activity totals: "
                      f"total_rounds = {round_n}; "
                      f"total_operations = {total_operations}; "
                      f"total_failures = {total_failures}; "
                      f"total_task_time = '{total_task_time}'; "
                      f"total_sleep_time = '{total_sleep_time}'; "
                      f"total_job_time = '{total_job_time}';")

        if incomplete is True:
            self.log.info("Task: stopped prematurely.")
        else:
            self.log.info("Task: finished.")


class ApplicationHandlerStats:
    def __init__(self):
        self.operation_count = 0
        self.operation_failures = 0

    def get_operation_count(self):
        return self.operation_count

    def get_failure_count(self):
        return self.operation_failures

    def one_operation_successful(self):
        self.operation_count += 1

    def reset_operation_count(self):
        self.operation_count = 0

    def one_operation_failed(self):
        self.operation_failures += 1

    def reset_failure_count(self):
        self.operation_failures = 0


class RoundExecutorStats:
    round = namedtuple('Round', ['operations', 'failures', 'start_time', 'end_time', 'task_time', 'task_sleep_time'])

    def __init__(self):
        self.rounds = list()

    def add_round(self, **round_attributes):
        self.rounds.append(self.round(**round_attributes))

    def all_rounds(self):
        for round in self.rounds:
            yield round


class TaciturnJobException(Exception):
    pass


class TaciturnJobNoAccountException(TaciturnJobException):
    pass