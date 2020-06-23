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


# taciturn admin, for dealing with application and account related stuff!

# so this admin script will interpret its arguments as commands, and the
# command language will be defined as follows:
#
#  taciturn_admin.py app
#  -- list all apps
#  taciturn_admin.py app app-name
#  -- list app
#  taciturn_admin.py app app-name { add | delete }
#  -- create/delete app
#
#  taciturn_admin.py user
#  -- list all users
#  taciturn_admin.py user user-name
#  -- list user
#  taciturn_admin.py user user-name { add | delete }
#  -- create/delete user
#  taciturn_admin.py user user-name app
#  -- display all apps/accounts for user
#  taciturn_admin.py user user-name app app-name
#  -- display user account for app
#  taciturn_admin.py user user-name app app-name account
#  -- display user account for app
#  taciturn_admin.py user user-name app app-name account account-name
#  -- display user account for app
#  taciturn_admin.py user user-name app app-name account account-name { add | delete | password }
#  -- create/delete/edit user account for app

# eventually it might be nice to collect stats!

from sqlalchemy.orm import Session
from sqlalchemy import and_

from taciturn.db.base import (
    Application,
    User,
    AppAccount
)

from taciturn.config import load_config

from getpass import getpass
from datetime import datetime
import sys

config = load_config()
engine = config['database_engine']
session = Session(bind=engine)

def warn(*args):
    print(*args, file=sys.stderr)


def list_apps(app_name=None):
    apps = None

    if app_name is None:
        apps = session.query(Application)
    elif app_name is not None:
        apps = session.query(Application).filter(Application.name == app_name)

    print('-'*72)
    print(' Applications:')
    print('-'*72)

    if apps is None or apps.count() == 0:
        print('*** None ***')
        return False

    for app in apps.all():
        print(' ', app.id, '\t', app.name, '\t', app.established)

    return True


def add_app(app_name):
    if session.query(Application).filter(Application.name == app_name).count() > 0:
        print("App '{}' already exists.".format(app_name))
        return False

    new_app = Application(name=app_name, established=datetime.now())
    session.add(new_app)
    session.commit()

    print("App '{}' added.".format(app_name))

    return True


def delete_app(app_name):
    app = session.query(Application).filter(Application.name == app_name).one_or_none()

    if app is None:
        print("App '{}' does not exist.".format(app_name))
        return False

    session.delete(app)
    session.commit()

    print("App '{}' deleted.".format(app_name))

    return True


def list_users(user_name=None):
    users = None

    if user_name is None:
        users = session.query(User)
    elif user_name is not None:
        users = session.query(User).filter(User.name == user_name)

    print('-'*72)
    print(' Users:')
    print('-'*72)

    if users is None or users.count() == 0:
        print('*** None ***')
        return False

    for app in users.all():
        print(' ', app.id, '\t', app.name, '\t', app.established)


def add_user(user_name):
    if session.query(User).filter(User.name == user_name).count() > 0:
        print("User '{}' already exists.".format(user_name))
        return False

    new_app = User(name=user_name, established=datetime.now())
    session.add(new_app)
    session.commit()

    print("User '{}' added.".format(user_name))

    return True


def delete_user(user_name):
    app = session.query(User).filter(User.name == user_name).one_or_none()

    if app is None:
        print("User '{}' does not exist.".format(user_name))
        return False

    session.delete(app)
    session.commit()

    print("User '{}' deleted.".format(user_name))

    return True


def list_user_accounts(user_name, app_name=None, account_name=None):
    accounts = None
    app = None

    user = session.query(User).filter_by(name=user_name).one_or_none()
    if app_name is not None:
        app = session.query(Application).filter_by(name=app_name).one_or_none()

    if app_name is not None and user is None and app is None:
        warn("No such user '{}' or app '{}'.".format(user_name, app_name))
        return False
    if app_name is not None and user is not None and app is None:
        warn("No such app '{}'.".format(app_name))
        return False
    if user is None:
        warn("No such user '{}'.".format(user_name))
        return False

    if app_name is None and account_name is None:
        accounts = session.query(User, AppAccount).filter(AppAccount.user_id == User.id)
    elif app_name is not None and account_name is None:
        accounts = session.query(User, AppAccount).filter(and_(Application.name == app_name,
                                                               AppAccount.user_id == User.id,
                                                               AppAccount.application_id == Application.id))
    elif app_name is not None and account_name is not None:
        accounts = session.query(User, AppAccount).filter(and_(AppAccount.name == account_name,
                                                               Application.name == app_name,
                                                               AppAccount.user_id == User.id,
                                                               AppAccount.application_id == Application.id))

    print('-'*72)

    if app_name is not None and account_name is not None:
        if accounts.count() == 0:
            warn("No such account '{}' for '{}' on app {}".format(account_name, user_name, app_name))
            return False
        elif accounts.count() == 1:
            print("Account '{}' for '{}' on app {}, created {}".format(account_name,
                                                                       user_name,
                                                                       app_name,
                                                                       accounts[0].established))
            return True
        else:
            raise ValueError("There should only be one account for "
                             "'{}' on app '{}', found {}?".format(user_name, app_name, accounts.count()))

    print('-'*72)
    if app_name is not None:
        print(" Accounts for '{}' on '{}':".format(user_name, app_name))
    else:
        print(" Accounts for '{}':".format(user_name))
    print('-'*72)

    if accounts is None or accounts.count() == 0:
        print('*** None ***')
        return False

    for account in accounts.all():
        print()


def add_user_account(user_name, app_name, account_name):
    account = session.query(User, AppAccount).filter(and_(AppAccount.name == account_name,
                                                          Application.name == app_name,
                                                          AppAccount.user_id == User.id,
                                                          AppAccount.application_id == Application.id)).one_or_none()
    if account is not None:
        warn("Account '{}' already exists for '{}' on app '{}'".format(account_name, user_name, app_name))
        return False

    app = session.query(Application).filter_by(name=app_name).one_or_none()
    user = session.query(User).filter_by(name=user_name).one_or_none()
    if app is None and user is None:
        warn("No such user '{}', no such app '{}'.".format(user_name, app_name))
        return False
    if app is None:
        warn("No such app '{}'".format(app_name))
        return False
    if user is None:
        warn("No such user '{}'".format(user_name))
        return False

    account_password = input_account_password()

    new_account = AppAccount(name=account_name,
                             password=account_password,
                             established=datetime.now(),
                             application_id=app.id,
                             user_id=user.id)
    session.add(new_account)
    session.commit()

    print("New account '{}' added for '{}' on app '{}'".format(account_name, user_name, app_name))
    return True


def delete_user_account(user_name, app_name, account_name):
    raise NotImplementedError("Write me!")


def password_user_account(user_name, app_name, account_name):
    raise NotImplementedError("Write me!")


def input_account_password():
    while True:
        password1 = getpass("Enter new password: ")
        password2 = getpass("Enter password again: ")
        if password1 == password2:
            return password1
        else:
            print("Passwords do not match, try again.")


def run_command(args):
    if len(args) < 1:
        warn("At least one argument required: 'app' or 'user'")
        return False

    #  taciturn_admin.py app
    if args[0] == 'app':
        # list all apps ...
        if len(args) == 1:
            return list_apps()
        # list an app ...
        elif len(args) == 2:
            return list_apps(args[1])
        # add/delete an app ...
        elif len(args) == 3:
            if args[2] == 'add':
                return add_app(args[1])
            elif args[2] == 'delete':
                return delete_app(args[1])
            else:
                warn("cannot perform '{}' on app '{}'".format(args[2], args[1]))
                return False
    elif args[0] == 'user':
        #  taciturn_admin.py user
        if len(args) == 1:
            return list_users()
        #  taciturn_admin.py user user-name
        elif len(args) == 2:
            return list_users(args[1])
        #  taciturn_admin.py user user-name { add | delete | app }
        elif len(args) == 3:
            if args[2] == 'add':
                return add_user(args[1])
            elif args[2] == 'delete':
                return delete_user(args[1])
            elif args[2] == 'app':
                list_user_accounts(args[1])
            else:
                warn("Syntax error.")
                return False
        # taciturn_admin.py user user-name app app-name
        elif len(args) == 4:
            if args[0] == 'user' and args[2] == 'app':
                return list_user_accounts(args[1], args[3])
            else:
                warn("Syntax error.")
                return False
        #  taciturn_admin.py user user-name app app-name account
        elif len(args) == 5:
            if args[0] == 'user' and args[2] == 'app' and args[4] == 'account':
                return list_user_accounts(args[1], args[3])
            else:
                warn("Syntax error.")
                return False
        #  taciturn_admin.py user user-name app app-name account account-name
        elif len(args) == 6:
            if args[0] == 'user' and args[2] == 'app' and args[4] == 'account':
                return list_user_accounts(args[1], args[3], args[5])
            else:
                warn("Syntax error.")
                return False
        #  taciturn_admin.py user user-name app app-name account account-name { add | delete | password }
        elif len(args) == 7:
            if args[0] == 'user' and args[2] == 'app' and args[4] == 'account' and args[6] == 'add':
                return add_user_account(args[1], args[3], args[5])
            elif args[0] == 'user' and args[2] == 'app' and args[4] == 'account' and args[6] == 'delete':
                return delete_user_account(args[1], args[3], args[5])
            elif args[0] == 'user' and args[2] == 'app' and args[4] == 'account' and args[6] == 'password':
                return password_user_account(args[1], args[3], args[5])
            else:
                warn("Syntax error.")
                return False


if __name__ == '__main__':
    code = run_command(sys.argv[1:])
    sys.exit(1 if code is False else 0)