
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

from taciturn.db.followers import (
    Follower,
    Following,
    Unfollowed
)

from taciturn.config import load_config

# Selenium automation:
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver import Chrome, Firefox, Remote
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

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

    def __init__(self, logger, options, db_session, app_account, driver=None):
        self.log = logger
        self.options = options
        self.session = db_session

        self.app_username = app_account.name
        self.app_password = app_account.password
        self.app_account = app_account

        self.config = load_config()
        self.assets_dir = self.config['assets_dir']
        self.screenshots_dir = self.config.get('screenshots_dir')

        self.driver = driver
        if self.driver is None:
            self._init_webdriver()

        # init white/blacklists:
        self._load_access_lists()

    def _load_access_lists(self):
        # load whitelist:
        # print("_load_access_lists for user '{}' on app '{}'".format(self.app_account.name, self.application_name))
        self.log.info('Loading whitelist.')
        wl = self.session.query(Whitelist.name)\
                        .filter(and_(Whitelist.user_id == self.app_account.user_id,
                                     Whitelist.application_id == Application.id,
                                     Application.name == self.application_name,
                                     Application.id == Whitelist.application_id))
        # print("whitelist = ", wl.all())
        self.whitelist = {w.lower() for w, in wl}

        # load blacklist:
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
            webdriver_type = self.options.driver or self.config.get('selenium_webdriver')

        self.log.info('Starting selenium with {} web driver'.format(webdriver_type))

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

    def sleepmsrange(self, r):
        if isinstance(r, tuple) and len(r) == 2:
            sleep_duration = random.randrange(r[0], r[1]) / 1000
        elif isinstance(r, numbers.Real):
            sleep_duration = r / 1000
        else:
            raise TypeError("sleepmsrange: takes one integer or a two-tuple of millisecond values.")

        duration = timedelta(seconds=sleep_duration)
        self.log.info('Sleeping for {}.'.format(duration))
        time.sleep(sleep_duration)

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
            ignored_exceptions = [StaleElementReferenceException, NoSuchElementException]
        return WebDriverWait(driver,
                             timeout=timeout,
                             ignored_exceptions=ignored_exceptions)


# base classes for application patterns:
#  for example follower based, we can create a common interface for this!

class FollowerApplicationHandler(BaseApplicationHandler):
    def __init__(self, logger, options, db_session, app_account, driver=None):
        super().__init__(logger, options, db_session, app_account, driver)

        config_name = 'app:{}'.format(self.application_name)
        self.follow_back_hiatus = self.config[config_name]['follow_back_hiatus']
        self.unfollow_hiatus = self.config[config_name]['unfollow_hiatus']
        self.action_timeout = self.config[config_name]['action_timeout']
        self.mutual_expire_hiatus = self.config[config_name]['mutual_expire_hiatus']

    @abstractmethod
    def goto_following_page(self, user_name=None):
        pass

    @abstractmethod
    def goto_followers_page(self, user_name=None):
        pass

    # Database methods for FollowerApplicationHandler:

    def db_get_unfollowed(self, flist_username):
        return self.session.query(Unfollowed)\
                .filter(and_(Unfollowed.name == flist_username,
                             Unfollowed.user_id == self.app_account.user_id,
                             Unfollowed.application_id == self.app_account.application_id,
                        )).one_or_none()

    def db_get_follower(self, flist_username):
        return self.session.query(Follower)\
                .filter(and_(Follower.name == flist_username,
                             Follower.user_id == self.app_account.user_id,
                             Follower.application_id == self.app_account.application_id,
                        )).one_or_none()

    def db_get_following(self, flist_username):
        return self.session.query(Follower)\
                .filter(and_(Follower.name == flist_username,
                             Follower.user_id == self.app_account.user_id,
                             Follower.application_id == self.app_account.application_id,
                        )).one_or_none()

    def db_new_following(self, flist_username):
        return Following(name=flist_username,
                         established=datetime.now(),
                         application_id=self.app_account.application_id,
                         user_id=self.app_account.user_id)

    def db_new_unfollowed(self, flist_username):
        return Unfollowed(name=flist_username,
                          established=datetime.now(),
                          application_id=self.app_account.application_id,
                          user_id=self.app_account.user_id)

    def db_new_follower(self, flist_username):
        return Follower(name=flist_username,
                        established=datetime.now(),
                        application_id=self.app_account.application_id,
                        user_id=self.app_account.user_id)

    # Follower list 'flist' processing methods:

    @abstractmethod
    def flist_first(self, flist_name=None):
        "get the first flist entry in an flist"
        # input validation:
        flist_choices = ('Followers', 'Following')
        if flist_name not in flist_choices:
            raise TypeError("flist_name choice not one of {}".format(', '.join(flist_choices)))

    @abstractmethod
    def flist_next(self, flist_entry):
        "get the next flist entry after flist_entry"
        pass

    @abstractmethod
    def flist_is_last(self, flist_entry):
        "return true if flist_entry is the last in the list"
        pass

    @abstractmethod
    def flist_is_empty(self, flist_entry):
        "return true if flist_entry is empty, used by twitter as end of list"
        pass

    @abstractmethod
    def flist_username(self, flist_entry):
        "returns the username text for flist_entry"
        pass

    @abstractmethod
    def flist_image_is_default(self, flist_entry):
        "returns true/false if the image is default"
        pass

    @abstractmethod
    def flist_is_verified(self, flist_entry):
        "returns true/false if the entry has a verified tag"
        pass

    @abstractmethod
    def flist_button(self, flist_entry):
        "returns the button element for flist_entry"
        pass

    @abstractmethod
    def flist_button_is_following(self, flist_button_text):
        "used to verify that flist_entry's button text reflects an application-specific following state"
        pass

    @abstractmethod
    def flist_button_is_not_following(self, flist_button_text):
        "used to verify that flist_entry's button text reflects an application-specific non-following state"
        pass

    @abstractmethod
    def flist_button_wait_following(self, flist_button):
        "used to wait and verify that flist_entry's button text reflects an application-specific following state"
        pass

    @abstractmethod
    def flist_button_wait_not_following(self, flist_button):
        "used to wait and verify that flist_entry's button text reflects an application-specific non-following state"
        pass

    @abstractmethod
    def flist_header_overlap_y(self):
        "returns the overlap y dimension of any elements overlapping the flist"
        pass

    @abstractmethod
    def flist_is_blocked_notice(self):
        "check if there's a notification that our follow request was blocked"
        pass

    @abstractmethod
    def flist_is_follow_limit_notice(self):
        "check if there'a a notification that our account cannot follow now"
        pass

    def start_following(self, target_account, quota=None, unfollow_hiatus=None):
        "A generalized start_following method, made to be application-agnostic."
        self.goto_following_page(target_account)

        unfollow_hiatus = unfollow_hiatus or self.unfollow_hiatus
        header_overlap_y = self.flist_header_overlap_y()
        flist_entry = self.flist_first()
        following_count = 0

        while quota is None or following_count < quota:
            self.scrollto_element(flist_entry, y_offset=header_overlap_y)

            # twitter end-of-list detection, other applications should always return true:
            if self.flist_is_empty(flist_entry):
                return following_count

            # get flist info fields, skipping where possible:

            flist_username = self.flist_username(flist_entry)
            if self.in_blacklist(flist_username):
                self.log.info("{} is in blacklist, skip ...".format(flist_username))
                if self.flist_is_last(flist_entry):
                    self.log.info('List end encountered, stopping.')
                    return following_count
                flist_entry = self.flist_next(flist_entry)
                continue

            flist_button = self.flist_button(flist_entry)
            flist_button_text = flist_button.text
            if self.flist_button_is_following(flist_button_text):
                self.log.info("Already following {}, skip ...".format(flist_username))
                if self.flist_is_last(flist_entry):
                    self.log.info('List end encountered, stopping.')
                    return following_count
                flist_entry = self.flist_next(flist_entry)
                continue

            if self.flist_image_is_default(flist_entry):
                self.log.info("{} has no image, skip ...".format(flist_username))
                if self.flist_is_last(flist_entry):
                    self.log.info('List end encountered, stopping.')
                    return following_count
                flist_entry = self.flist_next(flist_entry)
                continue

            flist_unfollowed_row = self.db_get_unfollowed(flist_username)
            is_hiatus_expired = flist_unfollowed_row is not None \
                                and datetime.now() < flist_unfollowed_row.established + unfollow_hiatus
            if is_hiatus_expired:
                time_remaining = (flist_unfollowed_row.established + unfollow_hiatus) - datetime.now()
                self.log.info("Followed/unfollowed too recently, can follow again after {}".format(time_remaining))
                if self.flist_is_last(flist_entry):
                    self.log.info('List end encountered, stopping.')
                    return following_count
                flist_entry = self.flist_next(flist_entry)
                continue

            # skip checks complete, now try to follow:

            if self.flist_button_is_not_following(flist_button_text):
                # check to see if we're already following this user in the db:
                # if it's already there, it's a good idea to put it in the unfollowed
                # list, because apparently we followed/unfollowed recently without
                # properly recording it?
                flist_following_row = self.db_get_following(flist_username)
                if flist_following_row is not None:
                    new_unfollowed_row = self.db_new_unfollowed(flist_username)

                    self.session.add(new_unfollowed_row)
                    self.session.delete(flist_following_row)
                    self.session.commit()

                    if self.flist_is_last(flist_entry):
                        self.log.info('List end encountered, stopping.')
                        return following_count
                    flist_entry = self.flist_next(flist_entry)
                    continue

                # ok, try clicking follow button ...
                flist_button.click()

                # check for follower fail conditions ...

                # check if there's a blocked or follow limit notification:

                if self.flist_is_blocked_notice():
                    self.log.info("User {} blocks us, skipping ...".format(flist_username))
                    if self.flist_is_last(flist_entry):
                        self.log.info('List end encountered, stopping.')
                        return following_count
                    flist_entry = self.flist_next(flist_entry)
                    continue

                if self.flist_is_follow_limit_notice():
                    self.log.info("Follow limit encountered, stopping.")
                    return following_count

                # verify that follow button indicates success:
                try:
                    self.flist_button_wait_following(flist_button)
                except TimeoutException:
                    self.log.info("Couldn't follow user {}, application limit probably hit, stopping."
                                    .format(flist_username))
                    return following_count

                # follow verified, create database entry:

                new_following_row = self.db_new_following(flist_username)

                # if there was an unfollowed entry, remove it now:
                if flist_unfollowed_row is not None:
                    self.session.delete(flist_unfollowed_row)

                self.session.add(new_following_row)
                self.session.commit()
                self.log.info("Follow for {} added to database.".format(flist_username))

                following_count += 1

                self.sleepmsrange(self.action_timeout)

            elif self.flist_button_is_following(flist_button_text):
                # make sure following entry is in the database ...
                already_following_row = self.db_get_following(flist_username)
                if already_following_row is None:
                    new_following_row = self.db_new_following(flist_username)
                    self.session.add(new_following_row)
                    self.session.commit()
            else:
                self.log.critical("Entry button for '{}' says '{}'?".format(flist_username, flist_button_text))
                raise AppUnexpectedStateException(
                    "Entry button for '{}' says '{}'?".format(flist_username, flist_button_text))

            flist_entry = self.flist_next(flist_entry)

        return following_count

    def start_unfollowing(self, quota=None, follow_back_hiatus=None, mutual_expire_hiatus=None):
        self.goto_following_page()

        follow_back_hiatus = follow_back_hiatus or self.follow_back_hiatus
        mutual_expire_hiatus = follow_back_hiatus or self.mutual_expire_hiatus

        header_overlap_y = self.flist_header_overlap_y()
        flist_entry = self.flist_first()
        unfollow_count = 0

        while quota is None or unfollow_count < quota:
            self.scrollto_element(flist_entry, y_offset=header_overlap_y)

            # twitter end-of-list detection:
            if self.flist_is_empty(flist_entry):
                return unfollow_count

            # get flist info fields, skipping where possible:
            flist_username = self.flist_username(flist_entry)

            if self.in_whitelist(flist_username):
                self.log.info('{} is in whitelist, skipping.'.format(flist_username))
                if self.flist_is_last(flist_entry):
                    self.log.info('List end encountered, stopping.')
                    return unfollow_count
                flist_entry = self.flist_next(flist_entry)
                continue

            flist_following_row = self.db_get_following(flist_username)

            if flist_following_row is None:
                print('No following entry for {}, creating record and skipping.')
                new_following = self.db_new_following(flist_username)
                self.session.add(new_following)
                self.session.commit()
                if self.flist_is_last(flist_entry):
                    self.log.info('List end encountered, stopping.')
                    return unfollow_count
                flist_entry = self.flist_next(flist_entry)
                continue
            else:
                # get follower_row, can be None if user doesn't follow us:
                follower_row = self.db_get_follower(flist_username)

                follow_back_expired = datetime.now() > flist_following_row.established + follow_back_hiatus
                mutual_follow_expired = datetime.now() > flist_following_row.established + mutual_expire_hiatus

                if not mutual_follow_expired and follower_row:
                    time_remaining = (flist_following_row.established + mutual_expire_hiatus) - datetime.now()
                    self.log.info('Mutual expire hiatus for user {} not reached, {} left.'
                                    .format(flist_username, time_remaining))
                    if self.flist_is_last(flist_entry):
                        self.log.info('List end encountered, stopping.')
                        return unfollow_count
                    flist_entry = self.flist_next(flist_entry)
                    continue
                elif not follow_back_expired:
                    time_remaining = (flist_following_row.established + follow_back_hiatus) - datetime.now()
                    self.log.info('Follow back hiatus for user {} not reached, {} left.'
                                    .format(flist_username, time_remaining))
                    if self.flist_is_last(flist_entry):
                        self.log.info('List end encountered, stopping.')
                        return unfollow_count
                    flist_entry = self.flist_next(flist_entry)
                    continue

                if mutual_follow_expired and follower_row:
                    self.log.info('Mutual follow expired for user {}, unfollowing.'
                                    .format(flist_username))
                elif follow_back_expired:
                    self.log.info('Follow expired for user {}, unfollowing.'
                                    .format(flist_username))
                else:
                    AppUnexpectedStateException('Unfollow in unexpected state, please examine!')

                flist_button = self.flist_button(flist_entry)
                flist_button.click()

                try:
                    self.flist_button_wait_not_following(flist_button)
                except TimeoutException:
                    self.log.error('Follow state for {} not changed to unfollwed, account may be restricted, stopping.')
                    return unfollow_count

                # update database:
                new_unfollowed_row = self.db_new_unfollowed(flist_username)
                self.session.add(new_unfollowed_row)
                self.session.delete(flist_following_row)
                self.session.commit()

                unfollow_count += 1
                self.sleepmsrange(self.action_timeout)

            flist_entry = self.flist_next(flist_entry)
        return unfollow_count

    def update_following(self):
        self.goto_following_page()

        flist_entry = self.flist_first()
        entries_added = 0

        while True:
            if self.flist_is_empty(flist_entry):
                self.log.info('List end encountered, stopping.')
                return entries_added

            self.scrollto_element(flist_entry)

            flist_username = self.flist_username(flist_entry)
            flist_following_row = self.db_get_following(flist_username)
            if flist_following_row is None:
                self.log.info('Adding {} to following.'.format(flist_username))
                new_following_row = self.db_new_following(flist_username)
                self.session.add(new_following_row)
                self.session.commit()
                entries_added += 1

            if self.flist_is_last(flist_entry):
                self.log.info('List end encountered, stopping.')
                return entries_added

            flist_entry = self.flist_next(flist_entry)

    def update_followers(self):
        self.goto_followers_page()

        flist_entry = self.flist_first()
        entries_added = 0

        while True:
            if self.flist_is_empty(flist_entry):
                self.log.info('List end encountered, stopping.')
                return entries_added

            self.scrollto_element(flist_entry)

            flist_username = self.flist_username(flist_entry)
            flist_follower_row = self.db_get_follower(flist_username)
            if flist_follower_row is None:
                self.log.info('Adding {} to followers.'.format(flist_username))
                new_follower_row = self.db_new_follower(flist_username)
                self.session.add(new_follower_row)
                self.session.commit()
                entries_added += 1

            if self.flist_is_last(flist_entry):
                self.log.info('List end encountered, stopping.')
                return entries_added

            flist_entry = self.flist_next(flist_entry)


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

