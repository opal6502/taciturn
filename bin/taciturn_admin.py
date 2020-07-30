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
#  taciturn_admin.py user user-name app app-name whitelist
#  -- list user-name's whitelist
#  taciturn_admin.py user user-name app app-name whitelist account-name
#  -- list user-name's and app-name's whitelist account account-name
#  taciturn_admin.py user user-name app app-name whitelist account-name { add | delete }
#  -- add or delete whitelist entry
#  taciturn_admin.py user user-name app app-name blacklist
#  -- list user-name's blacklist
#  taciturn_admin.py user user-name app app-name blacklist account-name
#  -- list user-name's and app-name's blacklist account account-name
#  taciturn_admin.py user user-name app app-name blacklist account-name { add | delete }
#  -- add or delete blacklist entry


import sys

from getpass import getpass

from sqlalchemy.orm import Session
from sqlalchemy import and_

from taciturn.config import get_config
from taciturn.datetime import datetime_now_tz

from taciturn.db.base import (
    Application,
    TaciturnUser,
    AppAccount,
    Whitelist,
    Blacklist
)

config = get_config()
engine = config['database_engine']
session = Session(bind=engine)


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
        print(f"App '{app_name}' already exists.", file=sys.stderr)
        return False

    new_app = Application(name=app_name, established=datetime_now_tz())
    session.add(new_app)
    session.commit()

    print(f"App '{app_name}' added.")

    return True


def delete_app(app_name):
    app = session.query(Application).filter(Application.name == app_name).one_or_none()

    if app is None:
        print(f"App '{app_name}' does not exist.")
        return False

    session.delete(app)
    session.commit()

    print(f"App '{app_name}' deleted.")

    return True


def list_users(user_name=None):
    users = None

    if user_name is None:
        users = session.query(TaciturnUser)
    elif user_name is not None:
        users = session.query(TaciturnUser).filter(TaciturnUser.name == user_name)

    print('-'*72)
    print(' Users:')
    print('-'*72)

    if users is None or users.count() == 0:
        print('*** None ***')
        return False

    for app in users.all():
        print(' ', app.id, '\t', app.name, '\t', app.established)


def add_user(user_name):
    if session.query(TaciturnUser).filter(TaciturnUser.name == user_name).count() > 0:
        print(f"User '{user_name}' already exists.", file=sys.stderr)
        return False

    new_app = TaciturnUser(name=user_name, established=datetime_now_tz())
    session.add(new_app)
    session.commit()

    print(f"User '{user_name}' added.")

    return True


def delete_user(user_name):
    app = session.query(TaciturnUser).filter(TaciturnUser.name == user_name).one_or_none()

    if app is None:
        print(f"User '{user_name}' does not exist.", file=sys.stderr)
        return False

    session.delete(app)
    session.commit()

    print(f"User '{user_name}' deleted.")

    return True


def list_user_accounts(user_name, app_name=None, account_name=None):
    accounts = None
    app = None

    user = session.query(TaciturnUser).filter_by(name=user_name).one_or_none()
    if app_name is not None:
        app = session.query(Application).filter_by(name=app_name).one_or_none()

    if app_name is not None and user is None and app is None:
        print(f"No such user '{user_name}' or app '{app_name}'.", file=sys.stderr)
        return False
    if app_name is not None and user is not None and app is None:
        print(f"No such app '{app_name}'.", file=sys.stderr)
        return False
    if user is None:
        print(f"No such user '{user_name}'.", file=sys.stderr)
        return False

    if app_name is None and account_name is None:
        accounts = session.query(TaciturnUser, AppAccount).filter(AppAccount.taciturn_user_id == TaciturnUser.id)
    elif app_name is not None and account_name is None:
        accounts = session.query(TaciturnUser, AppAccount).filter(and_(Application.name == app_name,
                                                                       AppAccount.taciturn_user_id == TaciturnUser.id,
                                                                       AppAccount.application_id == Application.id))
    elif app_name is not None and account_name is not None:
        accounts = session.query(TaciturnUser, AppAccount).filter(and_(AppAccount.name == account_name,
                                                                       Application.name == app_name,
                                                                       AppAccount.taciturn_user_id == TaciturnUser.id,
                                                                       AppAccount.application_id == Application.id))

    # print('-'*72)

    if app_name is not None and account_name is not None:
        if accounts.count() == 0:
            print(f"No such account '{account_name}' for '{user_name}' on app {app_name}", file=sys.stderr)
            return False
        elif accounts.count() == 1:
            print(f"Account '{account_name}' for '{user_name}' "
                  f"on app {app_name}, created {accounts[0].established}")
            return True
        else:
            print(f"There should only be one account for '{user_name}' on app '{app_name}', found {accounts.count()}?",
                  file=sys.stderr)
            sys.exit(1)

    print('-'*72)
    if app_name is not None:
        print(f" Accounts for '{user_name}' on '{app_name}':")
    else:
        print(f" Accounts for '{user_name}':")
    print('-'*72)

    if accounts is None or accounts.count() == 0:
        print('*** None ***')
        return False

    for account in accounts.all():
        print(account)


def add_user_account(user_name, app_name, account_name):
    account = session.query(TaciturnUser, AppAccount).filter(and_(AppAccount.name == account_name,
                                                                  Application.name == app_name,
                                                                  AppAccount.taciturn_user_id == TaciturnUser.id,
                                                                  AppAccount.application_id == Application.id)).one_or_none()
    if account is not None:
        print(f"Account '{account_name}' already exists for '{user_name}' on app '{app_name}'",
             file=sys.stderr)
        return False

    app = session.query(Application).filter_by(name=app_name).one_or_none()
    user = session.query(TaciturnUser).filter_by(name=user_name).one_or_none()
    if app is None and user is None:
        print(f"No such user '{user_name}', no such app '{app_name}'.", file=sys.stderr)
        return False
    if app is None:
        print(f"No such app '{app_name}'", file=sys.stderr)
        return False
    if user is None:
        print(f"No such user '{user_name}'", file=sys.stderr)
        return False

    account_password = input_account_password()

    new_account = AppAccount(name=account_name,
                             password=account_password,
                             established=datetime_now_tz(),
                             application_id=app.id,
                             taciturn_user_id=user.id)
    session.add(new_account)
    session.commit()

    print(f"New account '{account_name}' added for '{user_name}' on app '{app_name}'")
    return True


def delete_user_account(user_name, app_name, account_name):
    account = session.query(AppAccount).filter(and_(AppAccount.name == account_name,
                                                    Application.name == app_name,
                                                    AppAccount.taciturn_user_id == TaciturnUser.id,
                                                    AppAccount.application_id == Application.id)).one_or_none()
    if account is None:
        print(f"No account '{account_name}' for user '{user_name}' on app '{app_name}'", file=sys.stderr)
        return False

    session.delete(account)
    session.commit()

    print(f"Deleted account '{account_name}' for '{user_name}' on app '{app_name}'")
    return True


def password_user_account(user_name, app_name, account_name):
    account = session.query(AppAccount).filter(and_(AppAccount.name == account_name,
                                                    Application.name == app_name,
                                                    AppAccount.taciturn_user_id == TaciturnUser.id,
                                                    AppAccount.application_id == Application.id)).one_or_none()
    if account is None:
        print(f"No account '{account_name}' for user '{user_name}' on app '{app_name}'", file=sys.stderr)
        return False

    account_password = input_account_password()
    account.password = account_password

    session.commit()

    print(f"New password for account '{account_name}' for user '{user_name}' on app '{app_name}'")
    return True


def list_whitelist(user_name, app_name, entry_name=None):
    if entry_name is not None:
        entries = session.query(Whitelist, Application, TaciturnUser)\
                        .filter(and_(Whitelist.name == entry_name,
                                     TaciturnUser.name == user_name,
                                     Application.name == app_name,
                                     TaciturnUser.id == Whitelist.taciturn_user_id,
                                     Application.id == Whitelist.application_id))
    else:
        entries = session.query(Whitelist, Application, TaciturnUser)\
                        .filter(and_(TaciturnUser.name == user_name,
                                     Application.name == app_name,
                                     TaciturnUser.id == Whitelist.taciturn_user_id,
                                     Application.id == Whitelist.application_id))

    print('-' * 72)
    if entry_name is not None:
        print(f" Whitelist entry '{entry_name}' for '{user_name}' on '{app_name}':")
    else:
        print(f" Whitelist for '{user_name}' on '{app_name}':")
    print('-' * 72)

    if entries.count() == 0:
        print("*** None ***")
        return False
    else:
        for w, a, u in entries.all():
            print(w.name, '\t', u.name, '\t', a.name, '\t', w.established)
        return True


def add_to_whitelist(user_name, app_name, entry_name):
    entry = session.query(Whitelist) \
        .filter(and_(Whitelist.name == entry_name,
                     TaciturnUser.name == user_name,
                     Application.name == app_name,
                     TaciturnUser.id == Whitelist.taciturn_user_id,
                     Application.id == Whitelist.application_id))\
        .one_or_none()
    if entry is not None:
        print(f"'{entry_name}' is already in whitelist for '{user_name}' on app '{app_name}'", file=sys.stderr)
        return False

    app = session.query(Application).filter_by(name=app_name).one_or_none()
    user = session.query(TaciturnUser).filter_by(name=user_name).one_or_none()
    if app is None and user is None:
        print(f"No such user '{user_name}', no such app '{app_name}'.", file=sys.stderr)
        return False
    if app is None:
        print(f"No such app '{app_name}'", file=sys.stderr)
        return False
    if user is None:
        print(f"No such user '{user_name}'", file=sys.stderr)
        return False

    new_whitelist_entry = Whitelist(name=entry_name,
                                    established=datetime_now_tz(),
                                    taciturn_user_id=user.id,
                                    application_id=app.id)
    session.add(new_whitelist_entry)
    session.commit()

    print(f"Added '{entry_name}' to whitelist for '{user_name}' on app '{app_name}'")
    return True


def delete_from_whitelist(user_name, app_name, entry_name):
    app = session.query(Application).filter_by(name=app_name).one_or_none()
    user = session.query(TaciturnUser).filter_by(name=user_name).one_or_none()
    if app is None and user is None:
        print(f"No such user '{user_name}', no such app '{app_name}'.", file=sys.stderr)
        return False
    if app is None:
        print(f"No such app '{app_name}'", file=sys.stderr)
        return False
    if user is None:
        print(f"No such user '{user_name}'", file=sys.stderr)
        return False

    entry = session.query(Whitelist)\
        .filter(and_(Whitelist.name == entry_name,
                     TaciturnUser.name == user_name,
                     Application.name == app_name,
                     TaciturnUser.id == Whitelist.taciturn_user_id,
                     Application.id == Whitelist.application_id))\
        .one_or_none()

    if entry is None:
        print(f"'{entry_name}' is not in whitelist for '{user_name}' on app '{app_name}'", file=sys.stderr)
        return False

    session.delete(entry)
    session.commit()

    print(f"Deleted '{entry_name}' to whitelist for '{user_name}' on app '{app_name}'")
    return True


def list_blacklist(user_name, app_name, entry_name=None):
    if entry_name is not None:
        entries = session.query(Blacklist, Application, TaciturnUser)\
                        .filter(and_(Blacklist.name == entry_name,
                                     TaciturnUser.name == user_name,
                                     Application.name == app_name,
                                     TaciturnUser.id == Blacklist.taciturn_user_id,
                                     Application.id == Blacklist.application_id))
    else:
        entries = session.query(Blacklist, Application, TaciturnUser)\
                        .filter(and_(TaciturnUser.name == user_name,
                                     Application.name == app_name,
                                     TaciturnUser.id == Blacklist.taciturn_user_id,
                                     Application.id == Blacklist.application_id))

    print('-' * 72)
    if entry_name is not None:
        print(f" Blacklist entry '{entry_name}' for '{user_name}' on '{app_name}':")
    else:
        print(f" Blacklist for '{user_name}' on '{app_name}':")
    print('-' * 72)

    if entries.count() == 0:
        print("*** None ***")
        return False
    else:
        for w, a, u in entries.all():
            print(w.name, '\t', u.name, '\t', a.name, '\t', w.established)
        return True


def add_to_blacklist(user_name, app_name, entry_name):
    entry = session.query(Blacklist) \
        .filter(and_(Blacklist.name == entry_name,
                     TaciturnUser.name == user_name,
                     Application.name == app_name,
                     TaciturnUser.id == Blacklist.taciturn_user_id,
                     Application.id == Blacklist.application_id))\
        .one_or_none()
    if entry is not None:
        print(f"'{entry_name}' is already in whitelist for '{user_name}' on app '{app_name}'", file=sys.stderr)
        return False

    app = session.query(Application).filter_by(name=app_name).one_or_none()
    user = session.query(TaciturnUser).filter_by(name=user_name).one_or_none()
    if app is None and user is None:
        print(f"No such user '{user_name}', no such app '{app_name}'.", file=sys.stderr)
        return False
    if app is None:
        print(f"No such app '{app_name}'", file=sys.stderr)
        return False
    if user is None:
        print(f"No such user '{user_name}'", file=sys.stderr)
        return False

    new_blacklist_entry = Blacklist(name=entry_name,
                                    established=datetime_now_tz(),
                                    taciturn_user_id=user.id,
                                    application_id=app.id)
    session.add(new_blacklist_entry)
    session.commit()

    print(f"Added '{entry_name}' to blacklist for '{user_name}' on app '{app_name}'")
    return True


def delete_from_blacklist(user_name, app_name, entry_name):
    app = session.query(Application).filter_by(name=app_name).one_or_none()
    user = session.query(TaciturnUser).filter_by(name=user_name).one_or_none()
    if app is None and user is None:
        print(f"No such user '{user_name}', no such app '{app_name}'.", file=sys.stderr)
        return False
    if app is None:
        print(f"No such app '{app_name}'", file=sys.stderr)
        return False
    if user is None:
        print(f"No such user '{user_name}'", file=sys.stderr)
        return False

    entry = session.query(Blacklist)\
        .filter(and_(Blacklist.name == entry_name,
                     TaciturnUser.name == user_name,
                     Application.name == app_name,
                     TaciturnUser.id == Blacklist.taciturn_user_id,
                     Application.id == Blacklist.application_id))\
        .one_or_none()

    if entry is None:
        print(f"'{entry_name}' is not in blacklist for '{user_name}' on app '{app_name}'", file=sys.stderr)
        return False

    session.delete(entry)
    session.commit()

    print(f"Deleted '{entry_name}' from blacklist for '{user_name}' on app '{app_name}'")
    return True


def input_account_password():
    while True:
        password1 = getpass("Enter new password: ")
        password2 = getpass("Enter password again: ")
        if password1 == password2:
            return password1
        else:
            print("Passwords do not match, try again.", file=sys.stderr)


def run_command(args):
    if len(args) < 1:
        print("At least one argument required: 'app' or 'user'", file=sys.stderr)
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
                print(f"cannot perform '{args[2]}' on app '{args[1]}'", file=sys.stderr)
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
                print("Syntax error.", file=sys.stderr)
                return False
        # taciturn_admin.py user user-name app app-name
        elif len(args) == 4:
            if args[0] == 'user' and args[2] == 'app':
                return list_user_accounts(args[1], args[3])
            else:
                print("Syntax error.", file=sys.stderr)
                return False
        #  taciturn_admin.py user user-name app app-name account
        elif len(args) == 5:
            if args[0] == 'user' and args[2] == 'app' and args[4] == 'account':
                return list_user_accounts(args[1], args[3])
            #  taciturn_admin.py user user-name app app-name whitelist
            elif args[0] == 'user' and args[2] == 'app' and args[4] == 'whitelist':
                return list_whitelist(args[1], args[3])
            elif args[0] == 'user' and args[2] == 'app' and args[4] == 'blacklist':
                return list_blacklist(args[1], args[3])
            else:
                print("Syntax error.", file=sys.stderr)
                return False
        #  taciturn_admin.py user user-name app app-name account account-name
        elif len(args) == 6:
            if args[0] == 'user' and args[2] == 'app' and args[4] == 'account':
                return list_user_accounts(args[1], args[3], args[5])
            elif args[0] == 'user' and args[2] == 'app' and args[4] == 'whitelist':
                return list_whitelist(args[1], args[3], args[5])
            elif args[0] == 'user' and args[2] == 'app' and args[4] == 'blacklist':
                return list_blacklist(args[1], args[3], args[5])
            else:
                print("Syntax error.", file=sys.stderr)
                return False
        #  taciturn_admin.py user user-name app app-name account account-name { add | delete | password }
        elif len(args) == 7:
            if args[0] == 'user' and args[2] == 'app' and args[4] == 'account' and args[6] == 'add':
                return add_user_account(args[1], args[3], args[5])
            elif args[0] == 'user' and args[2] == 'app' and args[4] == 'account' and args[6] == 'delete':
                return delete_user_account(args[1], args[3], args[5])
            elif args[0] == 'user' and args[2] == 'app' and args[4] == 'account' and args[6] == 'password':
                return password_user_account(args[1], args[3], args[5])
            if args[0] == 'user' and args[2] == 'app' and args[4] == 'whitelist' and args[6] == 'add':
                return add_to_whitelist(args[1], args[3], args[5])
            elif args[0] == 'user' and args[2] == 'app' and args[4] == 'whitelist' and args[6] == 'delete':
                return delete_from_whitelist(args[1], args[3], args[5])
            if args[0] == 'user' and args[2] == 'app' and args[4] == 'blacklist' and args[6] == 'add':
                return add_to_blacklist(args[1], args[3], args[5])
            elif args[0] == 'user' and args[2] == 'app' and args[4] == 'blacklist' and args[6] == 'delete':
                return delete_from_blacklist(args[1], args[3], args[5])
            else:
                print("Syntax error.", file=sys.stderr)
                return False


if __name__ == '__main__':
    code = run_command(sys.argv[1:])
    sys.exit(1 if code is False else 0)