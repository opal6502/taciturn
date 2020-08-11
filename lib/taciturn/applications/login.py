
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


from abc import abstractmethod

from datetime import timedelta
from time import time, sleep

import random
import numbers

from sqlalchemy import and_

from taciturn.applications.base import BaseApplicationHandler, ApplicationHandlerException

from taciturn.db.base import (
    Application,
    Whitelist,
    Blacklist
)


class LoginApplicationHandler(BaseApplicationHandler):

    def __init__(self, app_account, handler_stats=None, driver=None):
        super().__init__(driver)

        self.haltlogin = self.options.haltlogin

        self.app_username = app_account.name
        self.app_password = app_account.password
        self.app_account = app_account

        self.stats = handler_stats

        self._last_action = None
        # init white/blacklists:
        self._load_access_lists()

        try:
            config_name = 'app:' + self.application_name
            self.action_timeout = self.config[config_name]['action_timeout']
        except KeyError:
            self.log.warning(f"Application '{self.application_name}' doesn't specify 'action_timeout' in config.")

    @abstractmethod
    def login(self):
        pass

    @abstractmethod
    def goto_homepage(self):
        pass

    @abstractmethod
    def goto_profile_page(self, user_name=None):
        pass

    def goto_login_page(self):
        self.log.info(f"Going to login page: {self.application_login_url}")
        self.driver.get(self.application_login_url)

    def _load_access_lists(self):
        self.log.info("Loading whitelist.")
        wl = self.session.query(Whitelist.name)\
                        .filter(and_(Whitelist.taciturn_user_id == self.app_account.taciturn_user_id,
                                     Whitelist.application_id == Application.id,
                                     Application.name == self.application_name,
                                     Application.id == Whitelist.application_id))
        self.whitelist = {w.lower() for w, in wl}

        self.log.info("Loading blacklist.")
        bl = self.session.query(Blacklist.name)\
                        .filter(and_(Blacklist.taciturn_user_id == self.app_account.taciturn_user_id,
                                     Blacklist.application_id == Application.id,
                                     Application.name == self.application_name,
                                     Application.id == Blacklist.application_id))
        self.blacklist = {b.lower() for b, in bl}

    def in_whitelist(self, name):
        return name.lower() in self.whitelist

    def in_blacklist(self, name):
        return name.lower() in self.blacklist

    def last_action_mark(self):
        self._last_action = time()

    def last_action_pause(self, r=None):
        if r is None:
            r = self.action_timeout
        if isinstance(r, tuple) and len(r) == 2:
            sleep_duration = random.randrange(r[0], r[1]) / 1000
        elif isinstance(r, numbers.Real):
            sleep_duration = r / 1000
        else:
            raise TypeError("pause_last_action: takes one integer or a two-tuple of millisecond values.")

        if self._last_action is not None and \
            time() < (self._last_action + sleep_duration):
            corrected_sleep_duration = (self._last_action + sleep_duration) - time()
            self.log.info(f"Pausing action for {timedelta(seconds=corrected_sleep_duration)}")
            sleep(corrected_sleep_duration)
        else:
            self.log.debug("No pause necessary.")


class ApplicationHandlerEndOfListException(ApplicationHandlerException):
    "Raise whenever a list end is encountered"
    pass


class ApplicationHandlerUserPrivilegeSuspendedException(ApplicationHandlerException):
    "Raise whenever a user privilege has been suspended"
    pass
