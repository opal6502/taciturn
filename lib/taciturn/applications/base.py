
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


import os
import sys
from abc import ABC

from time import time, sleep
from datetime import datetime

from http.cookiejar import MozillaCookieJar
import urllib.parse

from io import BytesIO
from hashlib import sha256

from selenium import webdriver
from selenium.webdriver import Chrome, Firefox, Remote
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from PIL import Image, ImageChops
import requests

from taciturn.config import get_config, get_options, get_logger, get_session


FILE_DOWNLOAD_RETRIES=10


class BaseApplicationHandler(ABC):
    application_name = None

    application_url = None
    application_login_url = None

    application_asset_dirname = None
    default_profile_image = None

    webdriver_user_agent = None
    webdriver_wait_ignored_exceptions = (StaleElementReferenceException, NoSuchElementException)
    webdriver_maximize_window = True
    webdriver_window_dimensions = (1920, 1080)

    def __init__(self, driver=None):
        self.config = get_config()
        self.log = get_logger()
        self.options = get_options()
        self.session = get_session()

        self.assets_dir = self.config['assets_dir']
        self.screenshots_dir = self.config['screenshots_dir']
        self.temp_file_ttl = self.config['temp_file_ttl']

        self.driver = driver
        if self.driver is None:
            self._webdriver_init()

        if self.options.cookies:
            self.load_cookies(self.options.cookies[0])

    def _webdriver_init(self):
        # init Selenium webdriver:

        # driver name is passed by command line option or config:
        if self.options.driver:
            webdriver_type = self.options.driver[0]
        else:
            webdriver_type = self.options.driver or self.config['selenium_webdriver']

        self.log.info(f"Starting Selenium with '{webdriver_type}' web driver")

        if webdriver_type is None or webdriver_type == 'chrome':
            from selenium.webdriver.chrome.options import Options

            opts = Options()
            opts.page_load_strategy = 'normal'
            opts.add_argument("--disable-popup-blocking")
            self._webdriver_chrome_set_window(opts)
            self._webdriver_chrome_set_user_agent(opts)

            self.driver = Chrome(options=opts)
        elif webdriver_type == 'chrome_headless':
            from selenium.webdriver.chrome.options import Options

            opts = Options()
            opts.page_load_strategy = 'normal'
            opts.add_argument("--headless")
            opts.add_argument("--disable-popup-blocking")
            self._webdriver_chrome_set_window(opts)
            self._webdriver_chrome_set_user_agent(opts)

            self.driver = Chrome(options=opts)
        elif webdriver_type == 'firefox':
            from selenium.webdriver.firefox.options import Options
            from selenium.webdriver import FirefoxProfile

            profile = FirefoxProfile()
            self._webdriver_firefox_set_user_agent(profile)

            opts = Options()
            self._webdriver_firefox_set_window(opts)

            self.driver = Firefox(profile)
        elif webdriver_type == 'firefox_headless':
            from selenium.webdriver.firefox.options import Options
            from selenium.webdriver import FirefoxProfile

            profile = FirefoxProfile()
            self._webdriver_firefox_set_user_agent(profile)

            opts = Options()
            self._webdriver_firefox_set_window(opts)
            opts.headless = True

            self.driver = Firefox(profile, options=opts)
        # XXX this htmlunit stuff has not at all been tested by me, but it should be a decent start?
        elif webdriver_type == 'htmlunit':
            self.driver = Remote(desired_capabilities=webdriver.DesiredCapabilities.HTMLUNIT)
        elif webdriver_type == 'htmlunitwithjs':
            self.driver = Remote(desired_capabilities=webdriver.DesiredCapabilities.HTMLUNITWITHJS)
        else:
            self.log.critical(f"Webdriver '{webdriver_type}' not supported, check config!")
            sys.exit(1)

        self.driver.set_window_position(0, 0)
        if self.webdriver_maximize_window:
            self.driver.maximize_window()
        else:
            self.driver.set_window_size(*self.webdriver_window_dimensions)

    # helper methods to set options/properties properly by browser type:

    def _webdriver_chrome_set_window(self, chrome_opts):
        if self.webdriver_maximize_window:
            chrome_opts.add_argument("--start-maximized")
        else:
            x, y = self.webdriver_window_dimensions
            chrome_opts.add_argument(f'--window-size={x},{y}')

    def _webdriver_firefox_set_window(self, firefox_opts):
        if self.webdriver_maximize_window:
            pass
        else:
            x, y = self.webdriver_window_dimensions
            firefox_opts.add_argument(f'--width={x}')
            firefox_opts.add_argument(f'--height={x}')

    def _webdriver_chrome_set_user_agent(self, chrome_opts):
        if self.webdriver_user_agent:
            chrome_opts.add_argument("user-agent={}".format(self.webdriver_user_agent))

    def _webdriver_firefox_set_user_agent(self, firefox_profile):
        if self.webdriver_user_agent:
            firefox_profile.set_preference('general.useragent.override', self.webdriver_user_agent)

    def goto_path(self, page_path):
        self.driver.get(self.application_url+'/'+page_path)

    def load_cookies(self, cookie_file):
        self.log.info(f"Loading cookies from {cookie_file}")
        cookiejar = MozillaCookieJar(cookie_file)
        cookiejar.load()
        for c in cookiejar:
            self.driver.get_cookie({'name': c.name, 'value': c.value})

    def quit(self):
        self.log.info("Quitting: quitting webdriver and closing db session.")
        self.driver.quit()
        self.session.close()
        del self.driver
        del self.session

    def element_scroll_to(self, element, y_offset=None):
        self.driver.execute_script('arguments[0].scrollIntoView();', element)
        if y_offset is not None:
            scroll_position = self.driver.execute_script('return document.documentElement.scrollTop;')
            self.driver.execute_script('window.scrollTo(0, arguments[0]);', scroll_position - y_offset)

    def element_rect_bottom(self, element):
        return self.driver.execute_script(self._element_rect_script('bottom'), element)

    def element_rect_top(self, element):
        return self.driver.execute_script(self._element_rect_script('top'), element)

    def _element_rect_script(self, side):
        return f"var rect = arguments[0].getBoundingClientRect(); return rect.{side};"

    def _delete_old_temp_files(self):
        self.log.info(f"Cleaning up old tempfiles for '{self.application_name}', older than '{self.temp_file_ttl}'.")
        asset_prefix = self._asset_path_prefix()
        for f in os.listdir(asset_prefix):
            full_filename = os.path.join(asset_prefix, f)
            if os.path.isfile(full_filename):
                file_timestamp = datetime.fromtimestamp(os.path.getctime(full_filename))
                if (file_timestamp + self.temp_file_ttl) < datetime.now():
                    self.log.debug(f"Temp file '{full_filename}' expired, deleting.")
                    os.remove(full_filename)
                else:
                    time_left = (file_timestamp + self.temp_file_ttl) - datetime.now()
                    self.log.debug(f"Temp file '{full_filename}' not expired, '{time_left}' left.")

    def _asset_path_prefix(self, file_name=None):
        if file_name is None:
            return os.path.join(self.assets_dir, 'application', self.application_name)
        else:
            return os.path.join(self.assets_dir, 'application', self.application_name, file_name)

    def temp_download_file(self, file_url, prefix=None, retries=FILE_DOWNLOAD_RETRIES):
        # first, remove stale tempfiles:
        self._delete_old_temp_files()

        # properly parse the url and get the extension:
        parsed_link = urllib.parse.urlparse(file_url)
        parsed_path, parsed_ext = os.path.splitext(parsed_link.path)

        if prefix:
            filename_prefix = prefix
        else:
            filename_prefix = self.application_name

        filename_hash = sha256(str(datetime.now()).encode('utf-8')).hexdigest()

        if parsed_ext:
            filename = f'{filename_prefix}-{filename_hash}{parsed_ext}'
        else:
            filename = f'{filename_prefix}-{filename_hash}'

        filename_with_path = self._asset_path_prefix(filename)

        for try_n in range(1, retries+1):
            try:
                self.log.debug(f"Downloading temp file: '{file_url}' (try {try_n} of {retries})")
                image_request = requests.get(file_url, stream=True)
                if image_request.status_code == 200:
                    with open(filename_with_path, 'wb') as f:
                        for chunk in image_request:
                            f.write(chunk)
                    break
                else:
                    self.log.error(f"Got HTTP response {image_request.status_code} "
                                   f"while downloading temp file: '{file_url}'")
                    if try_n >= retries:
                        raise ConnectionError(f"Got unexpected response code: {image_request.status_code} "
                                              f"while downloading temp file: '{file_url}'")
                    sleep(60)
                    continue
            except (requests.exceptions.ConnectionError, ConnectionError) as e:
                self.log.exception(f"Exception occurred while downloading image. (try {try_n} of {retries})")
                if try_n >= retries:
                    raise e
                sleep(60)
                continue

        return filename_with_path

    def is_default_image(self, image_url):
        return self.image_cmp(
            image_url,
            self._asset_path_prefix(self.default_profile_image))

    def image_cmp(self, image1_url_or_path, image2_url_or_path):
        image1_file = self.open_image_url_or_file(image1_url_or_path)
        image2_file = self.open_image_url_or_file(image2_url_or_path)

        try:
            if ImageChops.difference(image1_file, image2_file).getbbox():
                return False
        except ValueError:
            return False
        return True

    def open_image_url_or_file(self, image_url_or_path, retries=FILE_DOWNLOAD_RETRIES):
        for try_n in range(1, retries+1):
            try:
                response = requests.get(image_url_or_path)
                return Image.open(BytesIO(response.content))
            except requests.exceptions.ConnectionError as e:
                # connection error occurred:
                self.log.exception(f"Exception occurred while fetching image: "
                                   f"'{image_url_or_path}', try {try_n} of {retries}.")
                if try_n >= retries:
                    raise e
                sleep(60)
                continue
            except (requests.exceptions.MissingSchema, requests.exceptions.URLRequired):
                # try url as path:
                return Image.open(image_url_or_path)

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
                self.log.exception("BaseApplicationHandler.wait_text: Caught exception!")

            if time() > wait_until:
                raise ApplicationHandlerException("Couldn't get element text.")

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
                self.log.error("BaseApplicationHandler.wait_attribute: Caught exception!")

            if time() > wait_until:
                raise ApplicationHandlerException("Couldn't get element text.")

    def kill_javascript_alert(self):
        try:
            self.new_wait(timeout=3).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            alert.accept()
        except TimeoutException:
            pass
        finally:
            self.driver.switch_to.default_content()


# app state exceptions:

class ApplicationHandlerException(Exception):
    "Base taciturn app handler exception"
    pass
