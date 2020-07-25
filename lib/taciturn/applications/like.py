
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


from taciturn.applications.login import LoginApplicationHandler

from abc import abstractmethod


class LikeApplicationHandler(LoginApplicationHandler):

    def __init__(self, app_account, handler_stats, driver=None):
        super().__init__(app_account, handler_stats, driver)

    # plist_profile_* methods:

    @abstractmethod
    def plist_profile_first(self):
        pass

    @abstractmethod
    def plist_profile_next(self, plist_entry):
        pass

    @abstractmethod
    def plist_profile_is_last(self, plist_entry):
        pass

    @abstractmethod
    def plist_profile_is_empty(self, plist_entry):
        pass

    @abstractmethod
    def plist_profile_like_button(self, plist_entry):
        pass

    @abstractmethod
    def plist_profile_already_liked(self, plist_entry):
        pass

    @abstractmethod
    def plist_profile_wait_verify_like(self, plist_entry):
        pass

    # plist_search_* methods:

    @abstractmethod
    def plist_search_first(self):
        pass

    @abstractmethod
    def plist_search_next(self, plist_entry):
        pass

    @abstractmethod
    def plist_search_is_last(self, plist_entry):
        pass

    @abstractmethod
    def plist_search_is_empty(self, plist_entry):
        pass

    @abstractmethod
    def plist_search_like_button(self, plist_entry):
        pass

    @abstractmethod
    def plist_search_already_liked(self, plist_entry):
        pass

    @abstractmethod
    def plist_search_wait_verify_like(self, plist_entry):
        pass
