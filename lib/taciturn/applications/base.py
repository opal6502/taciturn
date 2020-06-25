
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


# SQLAlchemy:
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, and_

from taciturn.db.base import (
    Application,
    User,
    Whitelist,
    Blacklist
)

from taciturn.config import load_config

# Selenium automation:
from selenium.webdriver import Chrome

# base class abstraction:
from abc import ABC
from abc import abstractmethod
from io import BytesIO

# image handling:
from PIL import Image, ImageChops
import requests
from io import BytesIO

import os
import time
import random
import numbers


class BaseApplicationHandler(ABC):
    """
    Contains things all applications will have in common:
        - service homepage
        - user login
        - user password
        - user homepage
        - config, an initialized taciturn.config.Config object
        - selenium webdriver, defaults to Firefox
    """
    application_name = None

    # retry limit for sensitive information:
    default_load_retries = 5
    # timeout wait between retries:
    default_load_retry_timeout = 60*3

    local_asset_prefix = '/Users/johnk/PycharmProjects/Taciturn/Taciturn/assets/application'
    application_asset_dirname = 'base_app'

    implicit_wait_default = 10

    # database
    db_default_uri = "sqlite:///db/taciturn.sqlite"

    def __init__(self, db_session, app_account, elements=None):
        # database rows, as SQLAlchemy objects:
        # self.app_db = None
        # self.user = None

        self.session = db_session
        self.app_username = app_account.name
        self.app_password = app_account.password
        self.app_account = app_account

        self.config = load_config()

        # init white/blacklists:
        self._load_access_lists()

        # init Selenium:
        self.driver = Chrome()
        self.driver.implicitly_wait(self.implicit_wait_default)

        if elements is not None:
            self.e = elements(self.driver, self.implicit_wait_default)
        else:
            print("Warning: it's a good idea to use the ApplicationWebElements pattern for your webelement selectors!")

    def _load_access_lists(self):
        # load whitelist:
        wl = self.session.query(Whitelist.name)\
                        .filter(and_(Whitelist.user_id == self.app_account.id,
                                     Whitelist.application_id == Application.id,
                                     Application.name == self.application_name,
                                     Application.id == Whitelist.application_id))
        self.whitelist = {w.lower() for w, in wl}
        print("whitelist =", self.whitelist)

        # load blacklist:
        bl = self.session.query(Blacklist.name)\
                        .filter(and_(Blacklist.user_id == self.app_account.id,
                                     Blacklist.application_id == Application.id,
                                     Application.name == self.application_name,
                                     Application.id == Blacklist.application_id))
        self.blacklist = {b.lower() for b, in bl}
        print("blacklist =", self.whitelist)

    def in_whitelist(self, name):
        return name.lower() in self.whitelist

    def in_blacklist(self, name):
        return name.lower() in self.blacklist

    def quit(self):
        self.driver.quit()
        self.session.close()
        del self.driver
        del self.session

    @abstractmethod
    def goto_homepage(self):
        raise NotImplementedError

    @abstractmethod
    def goto_user_page(self):
        raise NotImplementedError

    @abstractmethod
    def login(self):
        raise NotImplementedError

    def is_default_image(self, image_url, default_image=None):
        return self.image_cmp(
            image_url,
            default_image or os.path.join(self.app_asset_prefix(),
                                          default_image or self.default_profile_image))

    def scrollto_element(self, element, offset=None):
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
        if offset is not None:
            scroll_position = self.driver.execute_script("return document.documentElement.scrollTop;")
            self.driver.execute_script("window.scrollTo(0, arguments[0]);", scroll_position - offset)

    @staticmethod
    def sleepmsrange(r):
        if isinstance(r, tuple) and len(r) == 2:
            time.sleep(random.randrange(r[0], r[1]) / 1000)
        elif isinstance(r, numbers.Number):
            time.sleep(r / 1000)
        else:
            raise TypeError("sleepmsrange: takes one integer or a two-tuple of millisecond values.")

    @staticmethod
    def image_cmp(image1_path, image2_path):
        """Compare two images from url or disk path
            if image1_path or image2_path is a valid URL, we try
            to download it, if it's not a valid URL, we try to read it
            from the filesystem!

            We fetch URLs using BytesIO, so no tmp files are created!
        """
        # print("image_cmp, image1_path:", image1_path)
        # print("image_cmp, image2_path:", image2_path)

        try:
            response = requests.get(image1_path)
            image1_file = Image.open(BytesIO(response.content))
        except (requests.exceptions.MissingSchema, requests.exceptions.URLRequired, ) as e:
            # print("Image {} is not valid URL, trying as path ...".format(image1_path, e))
            image1_file = Image.open(image1_path)

        try:
            response = requests.get(image2_path)
            image2_file = Image.open(BytesIO(response.content))
        except (requests.exceptions.MissingSchema, requests.exceptions.URLRequired) as e:
            # print("Image {} is not valid URL, trying as path ...".format(image2_path, e))
            image2_file = Image.open(image2_path)

        try:
            if ImageChops.difference(image1_file, image2_file).getbbox():
                return False
        except ValueError:
            return False
        return True

    def app_asset_prefix(self):
        return os.path.join(self.local_asset_prefix, self.application_asset_dirname)


class ApplicationWebElements(ABC):
    """Container that wraps webelement selectors in methods!

    a convienent way of adressing common element selectors as self.e.method(...) within ApplicationHandlers!
    """
    def __init__(self, driver, default_wait):
        self.driver = driver
        self.implicit_default_wait = default_wait


# base classes for application patterns:
#  for example follower based, we can create a common interface for this!

class FollowerApplicationHandler(BaseApplicationHandler):
    @abstractmethod
    def start_following(self, target_account, quota=None, unfollow_hiatus=None):
        "start following the followers of target_account"
        raise NotImplementedError

    @abstractmethod
    def update_followers(self):
        "scan our followers, and update the database, new follower timestamp is when this method scans a new follower!"
        raise NotImplementedError

    @abstractmethod
    def update_following(self):
        "scan who we are following, if an entry is unexpected, we add it and timespamp it if it's not whitelisted"
        pass

    @abstractmethod
    def start_unfollow(self, quota=None, follow_back_hiatus=None):
        "scan followers, and unfollow accounts that we've been following for a time, and don't follow us back!"
        raise NotImplementedError


# app state exceptions:


class AppException(Exception):
    "Base taciturn app handler exception"
    pass


class AppLoginException(AppException):
    "Raise if handler can't login"
    pass


class AppUnexpectedStateException(AppException):
    "App is in an unexpected state"
    pass


class AppActivityLimitException(AppException):
    "Raise if handler encounters activity limit"
    pass


class AppDataAnchorMissingException(AppException):
    "Can't find a critical data anchor in the page"
    pass


class AppRetryLimitException(AppException):
    "Raise if retry limit reached"
    pass


class AppWebElementException(AppRetryLimitException):
    "Raise if handler can't find web element after retry limit, specific retry fail case!"
    pass


# utility functions:

