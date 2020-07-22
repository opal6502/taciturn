
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
from sqlalchemy import and_

from taciturn.db.base import (
    Application,
    User,
    Whitelist,
    Blacklist
)

from taciturn.config import get_config, get_options, get_logger, get_session

from selenium.webdriver import Chrome, Firefox, Remote
from selenium import webdriver

from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait

from abc import ABC
from abc import abstractmethod

# for default image compare processing:
from PIL import Image, ImageChops
import requests
from io import BytesIO

import os
from time import time, sleep
import random
import numbers
from datetime import datetime, timedelta
from hashlib import sha256
from http.cookiejar import MozillaCookieJar


class BaseApplicationHandler(ABC):
    application_name = None

    application_url = None
    application_login_url = None

    application_asset_dirname = None
    default_profile_image = None

    webdriver_user_agent = None
    webdriver_wait_ignored_exceptions = (StaleElementReferenceException, NoSuchElementException)

    def __init__(self, app_account, handler_stats, driver=None):
        self.config = get_config()
        self.log = get_logger()
        self.options = get_options()
        self.session = get_session()

        self.app_username = app_account.name
        self.app_password = app_account.password
        self.app_account = app_account

        self.stats = handler_stats
        self._last_action = None

        self.assets_dir = self.config['assets_dir']
        self.screenshots_dir = self.config.get('screenshots_dir')

        self.driver = driver
        if self.driver is None:
            self._init_webdriver()

        # we'll say every app has to have an action_timeout:
        config_name = 'app:'+self.application_name
        self.action_timeout = self.config[config_name]['action_timeout']

        # init white/blacklists:
        self._load_access_lists()

    def _load_access_lists(self):
        self.log.info('Loading whitelist.')
        wl = self.session.query(Whitelist.name)\
                        .filter(and_(Whitelist.user_id == self.app_account.user_id,
                                     Whitelist.application_id == Application.id,
                                     Application.name == self.application_name,
                                     Application.id == Whitelist.application_id))
        self.whitelist = {w.lower() for w, in wl}

        self.log.info('Loading blacklist.')
        bl = self.session.query(Blacklist.name)\
                        .filter(and_(Blacklist.user_id == self.app_account.user_id,
                                     Blacklist.application_id == Application.id,
                                     Application.name == self.application_name,
                                     Application.id == Blacklist.application_id))
        self.blacklist = {b.lower() for b, in bl}

    def _init_webdriver(self):
        # init Selenium webdriver:

        # driver is usually passed by command line or config:
        if self.options.driver:
            webdriver_type = self.options.driver[0]
        else:
            webdriver_type = self.options.driver or self.config['selenium_webdriver']

        self.log.info("Starting Selenium with '{}' web driver".format(webdriver_type))

        if webdriver_type is None or webdriver_type == 'chrome':
            from selenium.webdriver.chrome.options import Options
            opts = Options()
            opts.add_argument("--start-maximized")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--disable-popup-blocking")
            opts.page_load_strategy = 'normal'
            if self.webdriver_user_agent:
                opts.add_argument("user-agent={}".format(self.webdriver_user_agent))
                self.driver = Chrome(options=opts)
            else:
                self.driver = Chrome()
        elif webdriver_type == 'chrome_headless':
            from selenium.webdriver.chrome.options import Options
            opts = Options()
            opts.add_argument("--start-maximized")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--disable-popup-blocking")
            opts.page_load_strategy = 'normal'
            if self.webdriver_user_agent:
                opts.add_argument("user-agent={}".format(self.webdriver_user_agent))
            opts.add_argument("--headless")
            self.driver = Chrome(options=opts)
        elif webdriver_type == 'firefox':
            from selenium.webdriver import FirefoxProfile
            profile = FirefoxProfile()
            if self.webdriver_user_agent:
                profile.set_preference('general.useragent.override', self.webdriver_user_agent)
            self.driver = Firefox(profile)
        elif webdriver_type == 'firefox_headless':
            from selenium.webdriver.firefox.options import Options
            from selenium.webdriver import FirefoxProfile
            profile = FirefoxProfile()
            options = Options()
            if self.webdriver_user_agent:
                profile.set_preference('general.useragent.override', self.webdriver_user_agent)
            options.headless = True
            self.driver = Firefox(profile, options=options)
            driver = webdriver.Firefox(options=options)
        # XXX this htmlunit stuff has not at all been tested by me, but it should be enough?
        elif webdriver_type == 'htmlunit':
            self.driver = Remote(desired_capabilities=webdriver.DesiredCapabilities.HTMLUNIT)
        elif webdriver_type == 'htmlunitwithjs':
            self.driver = Remote(desired_capabilities=webdriver.DesiredCapabilities.HTMLUNITWITHJS)
        else:
            self.log.critical("Webdriver '{}' not supported, check config!".format(webdriver_type))
            raise TypeError("Webdriver '{}' not supported, check config!".format(webdriver_type))

    def load_cookies(self, cookie_file):
        self.log.info("loading cookies from {}".format(cookie_file))
        cookiejar = MozillaCookieJar(cookie_file)
        cookiejar.load()
        for c in cookiejar:
            self.driver.get_cookie({'name': c.name, 'value': c.value})

    def in_whitelist(self, name):
        return name.lower() in self.whitelist

    def in_blacklist(self, name):
        return name.lower() in self.blacklist

    def quit(self):
        self.log.info('Quitting.')
        self.driver.quit()
        self.session.close()
        del self.driver
        del self.session

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
        self.log.info("Going to login page: {}".format(self.application_login_url))
        self.driver.get(self.application_login_url)

    def download_image(self, image_url, prefix=None, file_extension='.jpg'):
        if prefix is None:
            prefix = self.application_name+'-'

        file_name = prefix + sha256(str(datetime.now()).encode('utf-8')).hexdigest()+file_extension
        local_file_name = os.path.join(self.assets_dir, 'application', self.application_name, file_name)

        image_request = requests.get(image_url, stream=True)
        if image_request.status_code == 200:
            with open(local_file_name, 'wb') as f:
                for chunk in image_request:
                    f.write(chunk)
        return local_file_name

    def is_default_image(self, image_url, default_image=None):
        return self.image_cmp(
            image_url,
            default_image or os.path.join(self.assets_dir, 'application', self.application_name,
                                          default_image or self.default_profile_image))

    def scrollto_element(self, element, y_offset=None):
        self.driver.execute_script("arguments[0].scrollIntoView();", element)
        if y_offset is not None:
            scroll_position = self.driver.execute_script("return document.documentElement.scrollTop;")
            self.driver.execute_script("window.scrollTo(0, arguments[0]);", scroll_position - y_offset)

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
            self.log.info("Pausing action for {}".format(timedelta(seconds=corrected_sleep_duration)))
            sleep(corrected_sleep_duration)
        else:
            self.log.debug("No pause necessary.")

    @staticmethod
    def image_cmp(image1_file, image2_file):
        """Compare two images from url or disk path
            if image1_path or image2_path is a valid URL, we try
            to download it, if it's not a valid URL, we try to read it
            from the filesystem!

            We fetch URLs using BytesIO, so no tmp files are created!
        """
        try:
            response = requests.get(image1_file)
            image1_file = Image.open(BytesIO(response.content))
        except (requests.exceptions.MissingSchema, requests.exceptions.URLRequired, ) as e:
            # print("Image {} is not valid URL, trying as path ...".format(image1_path, e))
            image1_file = Image.open(image1_file)

        try:
            response = requests.get(image2_file)
            image2_file = Image.open(BytesIO(response.content))
        except (requests.exceptions.MissingSchema, requests.exceptions.URLRequired) as e:
            # print("Image {} is not valid URL, trying as path ...".format(image2_path, e))
            image2_file = Image.open(image2_file)

        try:
            if ImageChops.difference(image1_file, image2_file).getbbox():
                return False
        except ValueError:
            return False
        return True

    def app_asset_prefix(self):
        return os.path.join(self.assets_dir, self.application_asset_dirname)

    def new_wait(self, driver=None, timeout=60, ignored_exceptions=None):
        if driver is None:
            driver = self.driver
        if ignored_exceptions is None:
            ignored_exceptions = self.webdriver_wait_ignored_exceptions
        return WebDriverWait(driver,
                             timeout=timeout,
                             ignored_exceptions=ignored_exceptions)

    def wait_text(self, driver=None, locator=None, timeout=60, ignored_exceptions=None):
        if driver is None:
            driver = self.driver
        if ignored_exceptions is None:
            ignored_exceptions = self.webdriver_wait_ignored_exceptions
        wait_until = time() + timeout
        while True:
            try:
                return driver.find_element(*locator).text
            except ignored_exceptions as e:
                self.log.error("wait_text: Caught exception!")

            if time() > wait_until:
                raise TimeoutException("Couldn't get element text.")

    def wait_attribute(self, driver=None, locator=None, attribute_name=None, timeout=60, ignored_exceptions=None):
        if driver is None:
            driver = self.driver
        if ignored_exceptions is None:
            ignored_exceptions = self.webdriver_wait_ignored_exceptions
        wait_until = time() + timeout
        while True:
            try:
                return driver.find_element(*locator).get_attribute(attribute_name)
            except ignored_exceptions:
                self.log.error("wait_attribute: Caught exception!")

            if time() > wait_until:
                raise TimeoutException("Couldn't get element text.")


# app state exceptions:

class AppException(Exception):
    "Base taciturn app handler exception"
    pass


class AppEndOfListException(AppException):
    "Raise whenever a list end is encountered"
    pass


class AppUserPrivilegeSuspendedException(AppException):
    "Raise whenever a user privilege has been suspended"
    pass


class AppUnexpectedStateException(AppException):
    "App is in an unexpected state"
    pass


