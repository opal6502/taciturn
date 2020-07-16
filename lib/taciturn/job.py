
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


# interface to taciturn jobs!

from importlib.machinery import SourceFileLoader
from abc import ABC, abstractmethod
import os

from taciturn.config import load_config
from taciturn.db.base import User, Application, AppAccount, JobId

from sqlalchemy import and_
from sqlalchemy.orm import Session

from datetime import timedelta
from time import sleep, time
import logging


class TaciturnJob(ABC):
    __jobname__ = 'taciturn_job'
    __appnames__ = None

    def __init__(self, options, config=None):
        self.accounts = dict()
        self.options = options
        self.config = config or load_config()
        self.session = None
        self.stop_no_quota = None

        if 'database_engine' in self.config:
            self.session = Session(bind=self.config['database_engine'])
        else:
            raise TypeError("No 'database_engine' provided by config!")

        if self.__appnames__ is None and not isinstance(self.__appnames__, list):
            raise TypeError('Job needs to define self.__appnames__ as a list of apps the job interacts with')
        if self.options.user is None:
            raise TypeError('User name must be provided in the options with -u')
        self.username = self.options.user[0]
        if self.options.stop is not None and self.options.stop is True:
            self.stop_no_quota = True
        else:
            self.stop_no_quota = False
        self.load_accounts()
        self.job_id = self.new_job_id()

        # initialize logging here:
        if self.config['log_individual_jobs'] is True:
            log_file_path = os.path.join(self.config['log_dir'], '{}.log'.format(self))
        else:
            log_file_path = os.path.join(self.config['log_dir'], self.config['log_file'])

        log_level = self.config.get('log_level') or logging.INFO
        self.log = logging.getLogger('taciturn_log')
        self.log.setLevel(log_level)

        lf = logging.Formatter(self.config['log_format'].format(job_name=str(self)))

        fh = logging.FileHandler(log_file_path)
        fh.setLevel(log_level)
        fh.setFormatter(lf)

        sh = logging.StreamHandler()
        sh.setLevel(log_level)
        sh.setFormatter(lf)

        self.log.addHandler(sh)
        self.log.addHandler(fh)

        self.log.info('Initializing taciturn job.')




    def __str__(self):
        return '{}.{}'.format(self.__jobname__, self.job_id)

    def new_job_id(self):
        job_id_row = self.session.query(JobId).filter_by(id=1).one()
        new_job_id = job_id_row.job_id + 1
        job_id_row.job_id = new_job_id
        self.session.commit()
        return new_job_id

    def load_accounts(self):
        for app_name in self.__appnames__:
            app_account = self.session.query(AppAccount).\
                filter(and_(AppAccount.application_id == Application.id,
                            AppAccount.user_id == User.id,
                            User.name == self.username,
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

    @abstractmethod
    def run(self):
        pass


class TaciturnJobLoader:
    def __init__(self, config=None, jobs_dir=None):
        self.config = config or load_config()
        self.jobs_dir = jobs_dir or self.determine_jobs_dir()
        self.jobs = dict()

    def determine_jobs_dir(self):
        job_dir = os.environ.get('TACITURN_JOB_ROOT') or \
                  self.config.get('taciturn_job_root')
        if job_dir is None and self.config.get('taciturn_root') is not None:
            job_dir = os.path.join(self.config.get('taciturn_root'), 'jobs')
        else:
            raise RuntimeError("Could not determine jobs directory from environment and config.")

        if not os.path.isdir(job_dir):
            raise RuntimeError("Job dir '{}' does not exist".format(job_dir))

        return job_dir

    def load_job(self, job_name, options, config):
        job_full_name = os.path.join(self.jobs_dir, job_name+'.py')

        if not os.path.exists(job_full_name):
            raise RuntimeError("Job '{}' doesn't exist at: {}".format(job_name, job_full_name))

        job_module = SourceFileLoader('site_config', job_full_name).load_module()
        if not hasattr(job_module, 'job'):
            raise TypeError("Job file does not define 'job' object: {}".format(job_full_name))
        return job_module.job(options, config)


class TaskExecutor:
    def __init__(self, log=None, call=None, name=None, retries=None):
        self.log = log
        self.call = call
        self.name = name
        self.retries = retries or 1

    def run(self):
        for try_n in range(1, self.retries + 1):
            try:
                operation_count = self.call()
            except Exception as e:
                self.log.exception('Task: Failed, try {} of {}; exception occurred: {}'
                                      .format(try_n, self.retries, e))
                if try_n >= self.retries:
                    raise e
            else:
                break
        else:
            self.log.error('Task: Failed after {} tries.'
                              .format(try_n))


class RoundTaskExecutor(TaskExecutor):
    def __init__(self,
                 log=None,
                 call=None,
                 name=None,
                 quota=None,
                 max=None,
                 period=None,
                 retries=None,
                 stop_no_quota=False):
        super().__init__(log=log, call=call, name=name, retries=retries)
        self.quota = quota
        self.max = max
        self.period = period  # datetime.timedelta() object
        self.stop_no_quota = stop_no_quota

        self.total_time = 0
        self.operations_total = 0
        self.failed_rounds = 0

        self.start_epoch = None

    def run(self):
        total_rounds = self.max // self.quota
        task_timeout = self.period.total_seconds() / total_rounds

        for round_n in range(1, total_rounds+1):
            operation_count = 0
            task_start_epoch = time()

            for try_n in range(1, self.retries+1):
                try:
                    operation_count = self.call()
                except Exception as e:
                    self.log.exception('Task: Round {} of {} failed, try {} of {}; exception occurred: {}'
                                          .format(round_n, total_rounds, try_n, self.retries, str(e)))
                    if try_n >= self.retries:
                        raise e
                else:
                    break
            else:
                print('Task: Round {} of {} failed after {} tries.'
                          .format(round_n, total_rounds, try_n))
                self.failed_rounds += 1

            task_time = time() - task_start_epoch
            task_sleep_time = task_timeout - task_time
            if task_sleep_time < 0:
                task_sleep_time = 0

            self.total_time += task_time
            self.operations_total += operation_count

            if operation_count < self.quota:
                self.log.warn("Task {}: couldn't fulfill quota; expected {} operations, actual {}"
                                 .format(self.name, self.quota, operation_count))
                if self.stop_no_quota:
                    self.log.warn("Quota unfulfilled, stopping.")
                    break
            elif operation_count == self.max:
                print("Task: round complete with {} operations."
                        .format(operation_count))

            # last round, no need to sleep:
            if round_n >= total_rounds or self.operations_total >= self.max:
                break

            self.log.info("Task: sleeping for {} until next round."
                             .format(timedelta(seconds=task_sleep_time)))
            sleep(task_sleep_time)

        self.log.info("Task: ran {} rounds, {} operations, {} rounds_failed"
                         .format(total_rounds, self.operations_total, self.failed_rounds))
        self.log.info("Task: total time: {}"
                         .format(timedelta(seconds=self.total_time)))
        self.log.info("Task: complete")


class TaciturnJobException(Exception):
    pass


class TaciturnJobNoAccountException(TaciturnJobException):
    pass