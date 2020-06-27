#!python

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


from sqlalchemy.orm import Session
from sqlalchemy import create_engine, and_

import argparse
import collections
import sys
from getpass import getpass
from datetime import datetime

from taciturn.config import load_config

from taciturn.job import TaciturnJobLoader

from taciturn.db.base import (
    Application,
    User
)

config = load_config()
engine = config['database_engine']

# features to do with the CLI now:
#  - application commands:
#    - add application
#    - add user to application
#    - display whitelist
#    - add to whitelist
#    - display blacklist
#    - add to blacklist
#    - display followers, following, unfollow
#    - clear followers, following, unfollow for a user
# In the future:
#  - queue commands:
#    - list, add, delete - from a queue
#    - list all active queues
#  - job commands:
#    - run a job with command line config

command_job_choices = ['whitelist', 'blacklist', 'followers', 'following', 'unfollowed']
command_admin_choices = ['application', 'user']
command_verb_choices = ['list', 'add', 'delete', 'password']
command_verb_arg_required = ['add', 'delete']
command_verb_default = 'list'
all_command_choices = command_job_choices + command_admin_choices


def run_job(job_name, options):
    loader = TaciturnJobLoader(config=config)
    job = loader.load_job(job_name)
    job.init_job(options, config)
    job.run()


def cmd_application(verb, arg=None):
    "Handle the application command"
    session = Session(bind=engine)
    if verb == 'list':
        # list applications ...
        print('-'*72)
        print('Applications')
        print('-'*72)
        for a in session.query(Application).order_by(Application.name):
            print(' ', a.id, '\t', a.name, '\t', a.established)
    # XXX implement the other verbs, too!
    else:
        raise NotImplementedError("This needs to be written!!")


def cmd_user(verb, arg=None, application=None):
    "Handle the user command"
    session = Session(bind=engine)
    if verb == 'list':
        # list applications ...
        print('-'*72)
        print('Users')
        print('-'*72)
        if session.query(User, Application).filter(Application.id == User.application_id).count() == 0:
            print('*** No users ***')
            return
        for u, a in session.query(User, Application).filter(Application.id == User.application_id).order_by(User.name):
            print(' ', u.id, '\t', u.name, '\t', a.name, '\t', u.established)

    elif verb == 'add':
        if application is None:
            raise TypeError("Application must be specified when adding a new user (-n) flag")
        if session.query(User)\
            .filter(and_(User.name == arg,
                         Application.name == application,
                         Application.id == User.application_id)).count() != 0:
            raise TypeError("User with name '{}' for application already exists.".format(arg))
        app = session.query(Application).filter_by(name=application).one()

        password1 = getpass('Password for {}: '.format(arg))
        password2 = getpass('Password for {}: '.format(arg))
        if password1 != password1:
            print("Passwords do not match.")
            return

        new_user = User(name=arg, password=password1, application_id=app.id, established=datetime.now())

        session.add(new_user)
        session.commit()
        print("Added user '{}' to '{}'.".format(new_user.name, app.name))

    elif verb == 'delete':
        if application is None:
            raise TypeError("Application must be specified when deleting new user (-n) flag")

        user = session.query(User).filter(and_(User.name == arg,
                                           Application.name == application,
                                           Application.id == User.application_id)).one_or_none()
        if user is None:
            raise TypeError("No user '{}' for application '{}' found".format(arg, application))
        session.delete(user)
        session.commit()
        print("Deleted user '{}' from '{}'.".format(user.name, application))

    elif verb == 'password':
        user = session.query(User).filter(and_(User.name == arg,
                                           Application.name == application,
                                           Application.id == User.application_id)).one_or_none()
        if user is None:
            raise TypeError("No user '{}' for application '{}' found".format(arg, application))
        password1 = getpass('Password for {}: '.format(arg))
        password2 = getpass('Password for {}: '.format(arg))

        if password1 != password1:
            print("Passwords do not match.")
            return

        user.password = password1
        session.commit()
        print("Password updated for '{}' from '{}'.".format(user.name, application))


admin_dispatcher = {
    'application': cmd_application,
    'user': cmd_user
}


# parse arguments:
def parse_arguments(args=None):
    if args is None:
        args = sys.argv[1:]

    ap = argparse.ArgumentParser(description='Taciturn CLI tool.')
    ap.add_argument('-u', '--user', type=str, nargs=1,
                    help='specify a taciturn user for job')
    ap.add_argument('-j', '--job', type=str, nargs=1, required=True,
                    help="job to run, with arguments for job")
    #ap.add_argument('-l', '--queue', type=str, nargs='+',
    #               help="specify a queue to list, add or delete from")
    ap.add_argument('-t', '--target', type=str, nargs=1, default=None,
                    help="Target account")
    ap.add_argument('-m', '--max', type=int,
                    help="Maximum follows per 24-hour period, divided into quota rounds")
    ap.add_argument('-q', '--quota', type=int,
                    help="Quota of follows per each round in a 24-hour period")
    ap.add_argument('-s', '--stop', action='store_true',
                    help="Stop job if round quota can't be fulfilled")
    ap.add_argument('-D', '--driver', type=str, nargs=1, default=None,
                    help="Webdriver to use: htmlunit htmlunitjs chrome chrome_headless firefox firefox_headless")

    # parse arguments:
    pa = ap.parse_args(args)
    print(pa)

    return pa


if __name__ == '__main__':
    pa = parse_arguments()

    # XXX need to put in better input validation here!

    if pa.job is not None:
        run_job(pa.job[0], pa)
    else:
        print("You must specify a job with -j job-name")
        pa.print_help()

    # elif pa.admin is not None:
    #     # displatch command!
    #     admin_dispatcher[pa.admin.name](pa.admin.verb,
    #                                     arg=pa.admin.arg,
    #                                         application=pa.app[0])

