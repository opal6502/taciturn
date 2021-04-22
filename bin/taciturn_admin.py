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


# taciturn_admin.py, for administering Taciturn!

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

from taciturn.db.listq import ListQueues, ListQueueEntry


config = get_config()
engine = config['database_engine']
session = Session(bind=engine)


# Command help strings:

_help_general = """taciturn_admin.py - a command-line interface to edit Taciturn admin data.

This utility provides a simple command syntax to allow you to add and edit Taciturn users, apps, accounts,
as well as access lists.

You can run 'taciturn_admin.py -' to send commands via stdin, or 'taciturn_admin.py -f {command-file}' to 
read commands from a command file.
"""

_help_app_command = """'app' commands:
  app
     - list all apps
  app {app-name}
     - list '{app-name}'
  app {add|delete} {app-name}
     - add or delete '{app-name}'

It is unlikely you'll ever need to use this unless you're writing your own application handler.
"""

_help_user_command = """'user' commands:
  user
    - list all Taciturn users
  user [user-name]
    - list 'user-name'
  user {add|delete} {user-name}
    - add or delete 'user-name'

Most things in Taciturn belong to a user/app pair such as accounts and access lists.

examples:
  user add my_taciturn_user1
    - add a Taciturm user
  user delete my_taciturn_user1
    - delete this Taciturn user
"""

_help_account_command = """'account' commands:
  account user {user-name}
    - list all accounts belonging to 'user-name'
  account user {user-name} app {app-name}
    - list account for '{user-name}' on '{app-name}'
  account user {user-name} app {app-name} {account-name}
    - list account '{account-name}' for '{user-name}' on '{app-name}'
  account user {user-name} app {app-name} {add|delete} {account-name}
    - add or delete '{account-name}' for '{user-name}' on '{app-name}'

Administer application accounts associated with a Taciturn user.

examples:
  account user taciturn_user1 app twitter add twitter_login@foo.com
     - add a 'twitter' account for 'taciturn_user1', with the name 'twitter_login@foo.com',
       you'll be prompted to enter a password, too
  account user chef_123 app instagram add chef_123@bar.com
     - add an 'instagram' account for your Taciturn user 'chef_123'

Note each Taciturn user can only have one application account each.  If you need more, you can
simply create a new Taciturn user.
"""

# list_name, user_cmd, user_name, app_cmd, app_name, list_entry_list, *_e = _args
# list_name, user_cmd, user_name, app_cmd, app_name, list_verb, list_entry_edit, *_e = _args

_help_access_list_command = """access list commands:
  {blacklist|whitelist} user {user-name} app {app-name}
    - list blacklist or whitelist for '{user-name}' on '{app-name}'
  {blacklist|whitelist} user {user-name} app {app-name} {list-entry}
    - make sure '{list-entry}' is in the whitelist or blacklist for '{user-name}' on '{app-name}'
  {blacklist|whitelist} user {user-name} app {app-name} {add|delete} {list-entry}
    - delete or add '{list-entry}' from the whitelist or blacklist for '{user-name}' on '{app-name}'

examples:
  blacklist user fred_needs_followers app twitter add @nasty_person
    - prevent 'fred_needs_followers' from following '@nasty_person' on 'twitter'
  whitelist user my_insta_posse app instagram add crony_1
    - make sure that 'my_insta_posse' never un-follows 'crony_1' on 'instagram'

By default, even Taciturn mutual followers will expire, you need to whitelist friends
that you want to keep.
"""

# _s, user_cmd, user_name, app_cmd, app_name, listq_verb, listq_name, *_e = _args
# _s, user_cmd, user_name, app_cmd, app_name, listq_name, listq_entry_verb, listq_entry_edit, *_e = _args
# _s, user_cmd, user_name, app_cmd, app_name, listq_name, listq_entry_edit, read_cmd, read_count, *_e = _args

_help_listq_command = """listq commands:
  listq user {user-name} app {app-name} {add|delete} {listq-name}
    - add or delete listq called '{listq-name}' for use by '{user-name}' app '{app-name}'
  listq user {user-name} app {app-name} {listq-name} {add|delete} {listq-data}
    - add or delete a entry containing '{listq-data}' to '{listq-name}' for use
      by '{user-name}' app '{app-name}'
  listq user {user-name} app {app-name} {listq-name} {listq-data} reads {read-limit}
    - edit listq entry containing '{listq-data}' to an integer read limit of '{read-limit}'
      for use by '{user-name}' app '{app-name}'
      
List-queues provide a handy way of storing persistent data between Taciturn jobs and other
user tasks.
"""


def _print_full_help():
    print(_help_general, file=sys.stderr)
    print(file=sys.stderr)
    print(_help_app_command, file=sys.stderr)
    print(file=sys.stderr)
    print(_help_user_command, file=sys.stderr)
    print(file=sys.stderr)
    print(_help_account_command, file=sys.stderr)
    print(file=sys.stderr)
    print(_help_access_list_command, file=sys.stderr)
    print(file=sys.stderr)
    print(_help_listq_command, file=sys.stderr)


def run_command(args):
    len_args = len(args)
    max_args = 9
    _args = args + [None] * ((max_args + 1) - len_args)

    if len_args > max_args:
        raise TaciturnAdminSyntaxError("Too many arguments for a valid command")
    if len_args < 1:
        raise TaciturnAdminSyntaxError("Too few arguments for a valid command")

    if _args[0] == 'help':
        _print_full_help()
        return False

    if _args[0] == 'app':
        # 'app' command:
        _s, app_verb, app_name_edit, *_e = _args
        _s, app_name_list, *_e = _args

        if (not 1 <= len_args <= 3
                or len_args == 3 and not (app_verb == 'add' or app_verb == 'delete')
                or len_args > 3):
            print(_help_app_command, file=sys.stderr)
            raise TaciturnAdminSyntaxError("Syntax error")

        if app_verb is not None and len_args == 3:
            if app_verb == 'add':
                return app_add(app_name_edit)
            elif app_verb == 'delete':
                return app_delete(app_name_edit)
        if 1 <= len_args <= 2:
            return list_apps(app_name_list)

    if _args[0] == 'user':
        # parse 'user' command:
        _s, user_name_list, *_e = _args
        _s, user_verb, user_name_edit, *_e = _args

        if ((not 1 <= len_args <= 3) or
                (len_args == 3 and not(user_verb == 'add' or user_verb == 'delete'))):
            print(_help_user_command, file=sys.stderr)
            raise TaciturnAdminSyntaxError("Syntax error")

        if user_verb is not None:
            if len_args == 3:
                if user_verb == 'add':
                    return user_add(user_name_edit)
                elif user_verb == 'delete':
                    return user_delete(user_name_edit)
        if 1 <= len_args <= 2:
            return list_users(user_name_list)

    if _args[0] == 'account':
        # app account-related commands:
        _s, user_cmd, user_name, app_cmd, app_name, acct_name_list, *_e = _args
        _s, user_cmd, user_name, app_cmd, app_name, acct_verb, acct_name_edit, *_e = _args

        if ((not 3 <= len_args <= 7) or
                user_cmd != 'user' or
                len_args == 4 or
                (app_cmd is not None and app_cmd != 'app')):
            print(_help_account_command, file=sys.stderr)
            raise TaciturnAdminSyntaxError("Syntax error")

        if len_args == 7:
            print("len_args == 7")
            if acct_verb == 'add':
                return user_account_add(user_name, app_name, acct_name_edit)
            if acct_verb == 'delete':
                return user_account_delete(user_name, app_name, acct_name_edit)
            if acct_verb == 'password':
                return user_account_input_password(user_name, app_name, acct_name_edit)
        if 3 <= len_args <= 6:
            return user_accounts_list(user_name, app_name, acct_name_list)

    if _args[0] in ('whitelist', 'blacklist'):
        # access-list related commands:
        list_name, user_cmd, user_name, app_cmd, app_name, list_entry_list, *_e = _args
        list_name, user_cmd, user_name, app_cmd, app_name, list_verb, list_entry_edit, *_e = _args

        if ((not 5 <= len_args <= 7) or
                user_cmd != 'user' or app_cmd != 'app'):
            print(_help_access_list_command, file=sys.stderr)
            raise TaciturnAdminSyntaxError("Syntax error")

        if list_name == 'whitelist':
            if len_args == 7:
                if list_verb == 'add':
                    return whitelist_add_to(user_name, app_name, list_entry_edit)
                elif list_verb == 'delete':
                    return whitelist_delete_from(user_name, app_name, list_entry_edit)
            elif 5 <= len_args <= 6:
                return list_whitelist(user_name, app_name, list_entry_list)

        if list_name == 'blacklist':
            if len_args == 7:
                if list_verb == 'add':
                    return blacklist_add_to(user_name, app_name, list_entry_edit)
                elif list_verb == 'delete':
                    return blacklist_delete_from(user_name, app_name, list_entry_edit)
            elif 5 <= len_args <= 6:
                return list_blacklist(user_name, app_name, list_entry_list)

    if _args[0] == 'listq':
        # listq-related commands:
        _s, user_cmd, user_name, app_cmd, app_name, listq_verb, listq_name, *_e = _args
        _s, user_cmd, user_name, app_cmd, app_name, listq_name, listq_entry_verb, listq_entry_edit, *_e = _args
        _s, user_cmd, user_name, app_cmd, app_name, listq_name, listq_entry_edit, read_cmd, read_count, *_e = _args

        if ((not 4 <= len_args <= 9) or
                user_cmd != 'user' or
                len_args == 5 or
                (app_cmd is not None and app_cmd != 'app')):
            print(_help_listq_command, file=sys.stderr)
            raise TaciturnAdminSyntaxError("Syntax error")

        if len_args == 7:
            # add or delete a listq:
            if listq_verb == 'add':
                return listq_add(user_name, app_name, listq_name)
            if listq_verb == 'delete':
                return listq_delete(user_name, app_name, listq_name)

        if 3 <= len_args <= 6:
            return list_listq_entries(user_name, app_name, listq_name)

        if len_args == 8:
            # edit listq entries:
            if listq_entry_verb == 'add':
                listq_entry_add(user_name, app_name, listq_name, listq_entry_edit)
            if listq_entry_verb == 'delete':
                listq_entry_delete(user_name, app_name, listq_name, listq_entry_edit)
        if len_args == 7:
            return list_listq_entries(user_name, app_name, listq_name)

        if len_args == 9:
            if read_cmd == 'reads':
                # set entry read count ...
                listq_entry_set_reads(user_name, app_name, listq_name, listq_entry_edit, read_count)

    raise TaciturnAdminSyntaxError(f"Syntax error")



###################################################################################################################
# app functions
###################################################################################################################

def list_apps(app_name=None):
    apps = _get_apps(app_name)

    print('-'*72)
    print(' Applications:')
    print('-'*72)

    if apps.count() == 0:
        print('*** None ***')
        return False

    for app in apps.all():
        print(' ', app.id, '\t', app.name, '\t', app.established)

    return True


def app_add(app_name):
    app = _get_app(app_name)
    if app is not None:
        print(f"App '{app_name}' already exists.", file=sys.stderr)
        return False

    new_app = _new_app(app_name)

    session.add(new_app)
    session.commit()

    print(f"App '{app_name}' added.")

    return True


def app_delete(app_name):
    app = _get_app(app_name)

    if app is None:
        print(f"App '{app_name}' does not exist.")
        return False

    session.delete(app)
    session.commit()

    print(f"App '{app_name}' deleted.")

    return True


def _get_app(app_name):
    return session.query(Application).filter(Application.name == app_name).one_or_none()


def _get_apps(app_name=None):
    if app_name is not None:
        return session.query(Application).filter(Application.name == app_name)
    return session.query(Application)


def _new_app(app_name):
    return Application(name=app_name, established=datetime_now_tz())


###################################################################################################################
# user functions
###################################################################################################################

def list_users(user_name=None):
    users = _get_users(user_name)

    print('-'*72)
    print(' Users:')
    print('-'*72)

    if users.count() == 0:
        print('*** None ***')
        return False

    for app in users.all():
        print(' ', app.id, '\t', app.name, '\t', app.established)


def user_add(user_name):
    user = _get_user(user_name)
    if user is not None:
        print(f"User '{user_name}' already exists.", file=sys.stderr)
        return False

    new_user = _new_user(user_name)
    session.add(new_user)
    session.commit()

    print(f"User '{user_name}' added.")

    return True


def user_delete(user_name):
    user = _get_user(user_name)

    if user is None:
        print(f"User '{user_name}' does not exist.", file=sys.stderr)
        return False

    session.delete(user)
    session.commit()

    print(f"User '{user_name}' deleted.")

    return True


def _new_user(user_name):
    return TaciturnUser(name=user_name, established=datetime_now_tz())


def _get_user(user_name):
    return session.query(TaciturnUser).filter_by(name=user_name).one_or_none()


def _get_users(user_name=None):
    if user_name is not None:
        return session.query(TaciturnUser).filter(TaciturnUser.name == user_name)
    return session.query(TaciturnUser)


###################################################################################################################
# accounts functions
###################################################################################################################

def user_accounts_list(user_name, app_name=None, account_name=None):
    input_valid = True

    # explicitly validate inputs:
    user = _get_user(user_name)
    if app_name is not None:
        app = _get_app(app_name)
        if not _validate_app_and_user(user_name, user, app_name, app):
            input_valid = False
    if account_name is not None:
        account = _get_account(user_name, app_name, account_name)
        if account is None:
            print(f"No such account '{account_name}' for user '{user_name}' on app '{app_name}'")
            input_valid = False

    if not input_valid:
        return False

    accounts = _get_accounts(user_name, app_name, account_name)

    print('-'*72)
    if app_name is not None:
        print(f" Accounts for '{user_name}' on '{app_name}':")
    else:
        print(f" Accounts for '{user_name}':")
    print('-'*72)

    if accounts.count() == 0:
        print('*** None ***')
        return False

    for acct, app_name in accounts.all():
        print(' ', acct.id, '\t', acct.name, '\t', app_name, '\t', acct.established)


def user_account_add(user_name, app_name, account_name):
    account = _get_account(user_name, app_name, account_name)

    if account is not None:
        print(f"Account '{account_name}' already exists for '{user_name}' on app '{app_name}'",
             file=sys.stderr)
        return False

    app = _get_app(app_name)
    user = _get_user(user_name)

    if not _validate_app_and_user(user_name, user, app_name, app):
        print("Not valid!")
        return False

    account_password = input_account_password()

    new_account = _new_account(user, app, account_name, account_password)

    session.add(new_account)
    session.commit()

    print(f"New account '{account_name}' added for '{user_name}' on app '{app_name}'")
    return True


def user_account_delete(user_name, app_name, account_name):
    account = _get_account(user_name, app_name, account_name)
    if account is None:
        return False

    session.delete(account)
    session.commit()

    print(f"Deleted account '{account_name}' for '{user_name}' on app '{app_name}'")
    return True


def user_account_input_password(user_name, app_name, account_name):
    account = _get_account(user_name, app_name, account_name)
    if account is None:
        return False

    account_password = input_account_password()
    account.password = account_password

    session.commit()

    print(f"New password for account '{account_name}' for user '{user_name}' on app '{app_name}'")
    return True


def _new_account(user, app, account_name, account_password):
    return AppAccount(name=account_name,
                      password=account_password,
                      established=datetime_now_tz(),
                      application_id=app.id,
                      taciturn_user_id=user.id)


def _get_account(user_name, app_name, account_name):
    account = session.query(AppAccount)\
        .filter(and_(AppAccount.name == account_name,
                     Application.name == app_name,
                     AppAccount.taciturn_user_id == TaciturnUser.id,
                     AppAccount.application_id == Application.id)).one_or_none()
    return account


def _get_accounts(user_name, app_name=None, account_name=None):
    user = _get_user(user_name)
    if app_name is not None:
        app = _get_app(app_name)

    if app_name is None and account_name is None:
        return session.query(AppAccount, Application.name)\
                                .filter(TaciturnUser.id == user.id,
                                        AppAccount.taciturn_user_id == TaciturnUser.id,
                                        AppAccount.application_id == Application.id)
    elif app_name is not None and account_name is None:
        return session.query(AppAccount, Application.name)\
                                .filter(and_(Application.name == app_name,
                                             TaciturnUser.id == user.id,
                                             AppAccount.taciturn_user_id == TaciturnUser.id,
                                             AppAccount.application_id == Application.id))
    elif app_name is not None and account_name is not None:
        return session.query(AppAccount, Application.name)\
                                .filter(and_(AppAccount.name == account_name,
                                             TaciturnUser.id == user.id,
                                             Application.name == app_name,
                                             AppAccount.taciturn_user_id == TaciturnUser.id,
                                             AppAccount.application_id == Application.id))


###################################################################################################################
# whitelist functions
###################################################################################################################

def list_whitelist(user_name, app_name, entry_name=None):
    entries = _get_whitelist_entries(user_name, app_name, entry_name)

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


def whitelist_add_to(user_name, app_name, entry_name):
    user = _get_user(user_name)
    app = _get_app(app_name)
    if not _validate_app_and_user(user_name, user, app_name, app):
        return False

    entry = _get_whitelist_entry(user_name, app_name, entry_name)

    if entry is not None:
        print(f"'{entry_name}' is already in whitelist for '{user_name}' on app '{app_name}'", file=sys.stderr)
        return False

    new_whitelist_entry = _new_whitelist_entry(user, app, entry_name)

    session.add(new_whitelist_entry)
    session.commit()

    print(f"Added '{entry_name}' to whitelist for '{user_name}' on app '{app_name}'")
    return True


def whitelist_delete_from(user_name, app_name, entry_name):
    app = _get_user(user_name)
    user = _get_app(app_name)
    if not _validate_app_and_user(user_name, user, app_name, app):
        return False

    entry = _get_whitelist_entry(user_name, app_name, entry_name)

    if entry is None:
        print(f"'{entry_name}' is not in whitelist for '{user_name}' on app '{app_name}'", file=sys.stderr)
        return False

    session.delete(entry)
    session.commit()

    print(f"Deleted '{entry_name}' to whitelist for '{user_name}' on app '{app_name}'")
    return True


def _get_whitelist_entry(user_name, app_name, entry_name):
    entry = session.query(Whitelist)\
        .filter(and_(Whitelist.name == entry_name,
                     TaciturnUser.name == user_name,
                     Application.name == app_name,
                     TaciturnUser.id == Whitelist.taciturn_user_id,
                     Application.id == Whitelist.application_id))\
        .one_or_none()
    return entry


def _get_whitelist_entries(user_name, app_name, entry_name=None):
    if entry_name is not None:
        return session.query(Whitelist, Application, TaciturnUser)\
                        .filter(and_(Whitelist.name == entry_name,
                                     TaciturnUser.name == user_name,
                                     Application.name == app_name,
                                     TaciturnUser.id == Whitelist.taciturn_user_id,
                                     Application.id == Whitelist.application_id))
    else:
        return session.query(Whitelist, Application, TaciturnUser)\
                        .filter(and_(TaciturnUser.name == user_name,
                                     Application.name == app_name,
                                     TaciturnUser.id == Whitelist.taciturn_user_id,
                                     Application.id == Whitelist.application_id))


def _new_whitelist_entry(user, app, entry_name):
    return Whitelist(name=entry_name,
                     established=datetime_now_tz(),
                     taciturn_user_id=user.id,
                     application_id=app.id)


###################################################################################################################
# blacklist functions
###################################################################################################################

def list_blacklist(user_name, app_name, entry_name=None):
    entries = _get_blacklist_entries(user_name, app_name, entry_name)

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
        for b, a, u in entries.all():
            print(b.name, '\t', u.name, '\t', a.name, '\t', b.established)
        return True


def blacklist_add_to(user_name, app_name, entry_name):
    app = _get_user(user_name)
    user = _get_app(app_name)
    if not _validate_app_and_user(user_name, user, app_name, app):
        return False

    entry = _get_blacklist_entry(user_name, app_name, entry_name)
    if entry is not None:
        print(f"'{entry_name}' is already in whitelist for '{user_name}' on app '{app_name}'", file=sys.stderr)
        return False

    new_blacklist_entry = _new_blacklist_entry(user, app, entry_name)

    session.add(new_blacklist_entry)
    session.commit()

    print(f"Added '{entry_name}' to blacklist for '{user_name}' on app '{app_name}'")
    return True


def blacklist_delete_from(user_name, app_name, entry_name):
    app = _get_user(user_name)
    user = _get_app(app_name)
    if not _validate_app_and_user(user_name, user, app_name, app):
        return False

    entry = _get_blacklist_entry(user_name, app_name, entry_name)

    if entry is None:
        print(f"'{entry_name}' is not in blacklist for '{user_name}' on app '{app_name}'", file=sys.stderr)
        return False

    session.delete(entry)
    session.commit()

    print(f"Deleted '{entry_name}' from blacklist for '{user_name}' on app '{app_name}'")
    return True


def _get_blacklist_entry(user_name, app_name, entry_name):
    entry = session.query(Blacklist)\
        .filter(and_(Blacklist.name == entry_name,
                     TaciturnUser.name == user_name,
                     Application.name == app_name,
                     TaciturnUser.id == Blacklist.taciturn_user_id,
                     Application.id == Blacklist.application_id))\
        .one_or_none()
    return entry


def _get_blacklist_entries(user_name, app_name, entry_name=None):
    if entry_name is not None:
        return session.query(Blacklist, Application, TaciturnUser)\
                        .filter(and_(Blacklist.name == entry_name,
                                     TaciturnUser.name == user_name,
                                     Application.name == app_name,
                                     TaciturnUser.id == Blacklist.taciturn_user_id,
                                     Application.id == Blacklist.application_id))
    else:
        return session.query(Blacklist, Application, TaciturnUser)\
                        .filter(and_(TaciturnUser.name == user_name,
                                     Application.name == app_name,
                                     TaciturnUser.id == Blacklist.taciturn_user_id,
                                     Application.id == Blacklist.application_id))


def _new_blacklist_entry(user, app, entry_name):
    return Blacklist(name=entry_name,
                     established=datetime_now_tz(),
                     taciturn_user_id=user.id,
                     application_id=app.id)


###################################################################################################################
# listq functions
###################################################################################################################

def listq_add(user_name, app_name, listq_name):
    app = _get_user(user_name)
    user = _get_app(app_name)
    if not _validate_app_and_user(user_name, user, app_name, app):
        return False

    listq = _get_listq(user_name, app_name, listq_name)
    if listq is not None:
        print(f"Listq with name '{listq_name}' for '{user_name}' on app '{app_name}' already exists.", file=sys.stderr)
        return False

    new_listq = _new_listq(user, app, listq_name)

    session.add(new_listq)
    session.commit()

    print(f"Created listq '{listq_name}' for '{user_name}' on app '{app_name}'")
    return True


def listq_delete(user_name, app_name, listq_name):
    app = _get_user(user_name)
    user = _get_app(app_name)
    if not _validate_app_and_user(user_name, user, app_name, app):
        return False

    listq = _get_listq(user_name, app_name, listq_name)

    if listq is None:
        print(f"Listq '{listq_name}' for '{user_name}' on app '{app_name}' does not exist.", file=sys.stderr)
        return False

    session.delete(listq)
    session.commit()

    print(f"Deleted listq '{listq_name}' for '{user_name}' on app '{app_name}'")
    return True


def listq_entry_add(user_name, app_name, listq_name, listq_data):
    listq_entry = _get_listq_entry(user_name, app_name, listq_name, listq_data)

    if listq_entry is not None:
        print(f"Listq entry on '{listq_name}' for '{user_name}' "
              f"on app '{app_name}' already exists with this data.", file=sys.stderr)
        return False

    new_listq_entry = _new_listq_entry(user_name, app_name, listq_name, listq_data)

    session.add(new_listq_entry)
    session.commit()

    print(f"Added entry to listq '{listq_name}' for '{user_name}' on app '{app_name}'")
    return True


def listq_entry_delete(user_name, app_name, listq_name, listq_data):
    listq_entry = _get_listq_entry(user_name, app_name, listq_name, listq_data)

    if listq_entry is None:
        print(f"Listq entry on '{listq_name}' for '{user_name}' "
              f"on app '{app_name}' does not exist with this data.", file=sys.stderr)

    session.delete(listq_entry)
    session.commit()

    print(f"Deleted entry from listq '{listq_name}' for '{user_name}' on app '{app_name}'")
    return True


def listq_entry_set_reads(user_name, app_name, listq_name, listq_data, listq_reads):
    listq_entry = _get_listq_entry(user_name, app_name, listq_name, listq_data)

    if listq_entry is None:
        print(f"Listq entry on '{listq_name}' for '{user_name}' "
              f"on app '{app_name}' does not exist with this data.", file=sys.stderr)
        return False

    if listq_reads.lower() == 'none' or listq_reads.lower() == 'inf':
        listq_entry.reads_left = None
        display_reads = 'infinite'
    else:
        listq_entry.reads_left = int(listq_reads)
        display_reads = str(listq_reads)

    session.flush()

    print(f"Listq entry on '{listq_name}' for '{user_name}' "
            f"on app '{app_name}' read count set to {display_reads}.")


def list_listq_entries(user_name, app_name=None, listq_name=None):
    listq_ids = _get_listq_ids(user_name, app_name, listq_name)

    entries = session.query(TaciturnUser.name, Application.name, ListQueues.listq_name, ListQueueEntry)\
                   .filter(and_(ListQueueEntry.listq_id.in_(listq_ids),
                                ListQueueEntry.listq_id == ListQueues.id))\
                   .order_by(ListQueueEntry.last_read_datetime,
                             TaciturnUser.name,
                             ListQueues.listq_name)

    print('-' * 72)
    if app_name is None and listq_name is None:
        print(f" Listq entries for user '{user_name}'")
    elif app_name is not None and listq_name is None:
        print(f" Listq entries for user '{user_name}' on app '{app_name}'")
    elif app_name is not None and listq_name is not None:
        print(f" Listq '{listq_name}' for user '{user_name}' on app '{app_name}'")
    print('-' * 72)

    for u_n, a_n, lq_n, lq_e in entries.all():
        l = lq_e.last_read_datetime if lq_e.last_read_datetime is not None else 'no reads'
        r = lq_e.reads_left if lq_e.reads_left is not None else 'inf'
        print(u_n, '\t', a_n, '\t', lq_n, '\t', lq_e.reads_left, '\t', l, '\t', r)


def _get_listq(user_name, app_name, listq_name):
    return session.query(ListQueues).filter(and_(ListQueues.listq_name == listq_name,
                                                 TaciturnUser.name == user_name,
                                                 Application.name == app_name,
                                                 TaciturnUser.id == ListQueues.taciturn_user_id,
                                                 Application.id == ListQueues.application_id))\
                                    .one_or_none()


def _get_listq_id(user_name, app_name, listq_name):
    return session.query(ListQueues.id).filter(and_(ListQueues.listq_name == listq_name,
                                                    TaciturnUser.name == user_name,
                                                    Application.name == app_name,
                                                    TaciturnUser.id == ListQueues.taciturn_user_id,
                                                    Application.id == ListQueues.application_id))\
                                       .one_or_none()


def _get_listq_ids(user_name, app_name=None, listq_name=None):
    if app_name is not None and listq_name is not None:
        return session.query(ListQueues.id)\
                    .filter(and_(TaciturnUser.name == user_name,
                                 Application.name == app_name,
                                 ListQueues.listq_name == listq_name,
                                 Application.id == ListQueues.application_id,
                                 TaciturnUser.id == ListQueues.taciturn_user_id))\
                    .subquery()
    elif app_name is not None and listq_name is None:
        return session.query(ListQueues.id)\
                    .filter(TaciturnUser.name == user_name,
                            Application.name == app_name,
                            Application.id == ListQueues.application_id,
                            TaciturnUser.id == ListQueues.taciturn_user_id)\
                    .subquery()
    elif app_name is None and listq_name is None:
        return session.query(ListQueues.id)\
                    .filter(TaciturnUser.name == user_name,
                            Application.id == ListQueues.application_id,
                            TaciturnUser.id == ListQueues.taciturn_user_id)\
                    .subquery()


def _new_listq(user, app, listq_name):
    return ListQueues(
        listq_name=listq_name,
        taciturn_user_id=user.id,
        application_id=app.id,
        established=datetime_now_tz()
    )


def _get_listq_entry(user_name, app_name, listq_name, listq_data):
    listq_id = _get_listq_id(user_name, app_name, listq_name)
    return session.query(ListQueueEntry).filter(ListQueueEntry.listq_data == listq_data,
                                                ListQueueEntry.listq_id == listq_id)


def _new_listq_entry(user_name, app_name, listq_name, listq_data):
    listq_id = _get_listq_id(user_name, app_name, listq_name)
    return ListQueueEntry(
        listq_data=listq_data,
        listq_id=listq_id,
        read_limit=None,
        last_read_datetime=None,
        established=datetime_now_tz()
    )


###################################################################################################################
# misc functions
###################################################################################################################

def _validate_app_and_user(user_name, user, app_name, app):
    if app is None and user is None:
        print(f"No such user '{user_name}', no such app '{app_name}'.", file=sys.stderr)
        return False
    if app is None:
        print(f"No such app '{app_name}'", file=sys.stderr)
        return False
    if user is None:
        print(f"No such user '{user_name}'", file=sys.stderr)
        return False
    return True


def input_account_password():
    while True:
        password1 = getpass("Enter new password: ")
        password2 = getpass("Enter password again: ")
        if password1 == password2:
            return password1
        else:
            print("Passwords do not match, try again.", file=sys.stderr)


def command_repl(input_file):
    line_number = 1
    for line in input_file:
        print(f"> {line.rstrip()}")
        de_comment = list(line.split('#'))[0]
        line_as_args = de_comment.split()
        # print("line_as_args:", line_as_args)
        if len(line_as_args) == 0:
            continue
        try:
            run_command(line_as_args)
        except TaciturnAdminSyntaxError as e:
            raise type(e)(str(e) + f" at line {line_number} of '{input_file.name}'")

        line_number += 1


###################################################################################################################
# exceptions
###################################################################################################################

class TaciturnAdminSyntaxError(Exception):
    pass


###################################################################################################################
# main
###################################################################################################################

if __name__ == '__main__':
    # see if we're configured to do a file-repl:
    args = sys.argv[1:]

    if len(args) == 0:
        _print_full_help()
        sys.exit(1)

    if len(args) == 1 and args[0] == '-':
        command_repl(sys.stdin)
    elif len(args) == 2 and args[0] == '-f':
        cmd_filename = args[1]
        with open(cmd_filename, 'r') as cmd_file:
            command_repl(cmd_file)
    else:
        code = True
        try:
            code = run_command(sys.argv[1:])
        except TaciturnAdminSyntaxError as e:
            print(f"taciturn_admin.py: error: {e}")
            code = False
            raise e
        sys.exit(1 if code is False else 0)
