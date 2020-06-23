
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

from abc import ABC, abstractmethod
import os, glob
from importlib.machinery import SourceFileLoader

from taciturn.db.base import ORMBase
from taciturn.config import load_config

from sqlalchemy.orm import Session


class TaciturnJob(ABC):
    __jobname__ = 'taciturn_job'

    def init_job(self, options, config=None):
        self.options = options
        self.config = config or load_config()

        if 'database_engine' in self.config:
            self.session = Session(bind=self.config['database_engine'])
        else:
            raise TypeError("No 'database_engine' provided by config!")

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

    def load_job(self, job_name):
        job_full_name = os.path.join(self.jobs_dir, job_name+'.py')

        if not os.path.exists(job_full_name):
            raise RuntimeError("Job '{}' doesn't exist at: {}".format(job_name, job_full_name))

        return self.load_jobfile(job_full_name)

    def load_jobfile(self, job_full_name=None):
        job_module = SourceFileLoader('site_config', job_full_name).load_module()

        if not hasattr(job_module, 'job'):
            raise TypeError("Job file does not define 'job' object: {}".format(job_full_name))
        if not isinstance(job_module.job, TaciturnJob):
            raise TypeError("'job' object is not type TaciturnJob in file: {}".format(job_full_name))
        return job_module.job


class TaciturnJobException(Exception):
    pass


class TaciturnJobNoAccountException(TaciturnJobException):
    pass