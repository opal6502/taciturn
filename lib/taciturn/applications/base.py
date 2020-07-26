
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


from taciturn.config import get_config, get_options, get_logger, get_session

from selenium.webdriver import Chrome, Firefox, Remote
from selenium import webdriver

from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from abc import ABC

# for default image compare processing:
from PIL import Image, ImageChops
import requests
from io import BytesIO

import os, sys
import urllib.parse
from time import time, sleep
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

    def __init__(self, driver=None):
        self.config = get_config()
        self.log = get_logger()
        self.options = get_options()
        self.session = get_session()

        self.assets_dir = self.config['assets_dir']
        self.screenshots_dir = self.config.get('screenshots_dir')

        self.driver = driver
        if self.driver is None:
            self._init_webdriver()

        if self.options.cookies:
            self.load_cookies(self.options.cookies[0])

    def _init_webdriver(self):
        # init Selenium webdriver:

        # driver is usually passed by command line or config:
        if self.options.driver:
            webdriver_type = self.options.driver[0]
        else:
            webdriver_type = self.options.driver or self.config['selenium_webdriver']

        self.log.info(f"Starting Selenium with '{webdriver_type}' web driver")

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
            self.log.critical(f"Webdriver '{webdriver_type}' not supported, check config!")
            sys.exit(1)

    def goto_path(self, page_path):
        self.driver.get(self.application_url+'/'+page_path)

    def load_cookies(self, cookie_file):
        self.log.info(f"Loading cookies from {cookie_file}")
        cookiejar = MozillaCookieJar(cookie_file)
        cookiejar.load()
        for c in cookiejar:
            self.driver.get_cookie({'name': c.name, 'value': c.value})

    def quit(self):
        self.log.info("Quitting.")
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
        pass

    def _asset_path_prefix(self, file_name=None):
        if file_name is None:
            return os.path.join(self.assets_dir, 'application', self.application_name)
        else:
            return os.path.join(self.assets_dir, 'application', self.application_name, file_name)

    def temp_download_file(self, file_url, prefix=None, retries=10):
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
                image_request = requests.get(file_url, stream=True)
            except requests.exceptions.ConnectionError as e:
                if try_n >= retries:
                    raise e
                continue

        if image_request.status_code == 200:
            with open(filename_with_path, 'wb') as f:
                for chunk in image_request:
                    f.write(chunk)
        else:
            raise ConnectionError(f"Got unexpected response code: {image_request.status_code}")

        return filename_with_path

    def is_default_image(self, image_url):
        return self.image_cmp(
            image_url,
            self._asset_path_prefix(self.default_profile_image))

    def image_cmp(self, image1_url_or_path, image2_url_or_path):
        image1_file = self.open_image_file_or_url(image1_url_or_path)
        image2_file = self.open_image_file_or_url(image2_url_or_path)

        try:
            if ImageChops.difference(image1_file, image2_file).getbbox():
                return False
        except ValueError:
            return False
        return True

    def open_image_file_or_url(self, image_url_or_path, retries=10):
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
                else:
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


class ApplicationHandlerUnexpectedStateException(ApplicationHandlerException):
    "App is in an unexpected state"
    pass

