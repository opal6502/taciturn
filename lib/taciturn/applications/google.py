
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


from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)

from taciturn.applications.base import BaseApplicationHandler, ApplicationHandlerException

GOOGLE_LOGIN_RETRIES = 10


class GoogleLoginMixin(BaseApplicationHandler):
    google_login_url = 'https://accounts.google.com/Login'

    def __init__(self, driver=None):
        super().__init__(driver)

        # login process is different in headed/headless mode:
        driver_name = self.options.driver[0] if self.options.driver else self.config['selenium_webdriver']
        if driver_name.endswith('_headless'):
            self.headless_mode = True
        else:
            self.headless_mode = False

    def _google_login(self):
        if self.headless_mode:
            self._google_login_headless_mode()
        else:
            self._google_login_headed_mode()
        self.log.info("Logged in via Google.")

    def _google_login_headless_mode(self):
        login_wait = self.new_wait(timeout=10)
        self.log.info("Logging in to Soundcloud through Google, headless browser mode.")
        self.driver.get(self.google_login_url)

        google_login_email_locator = (By.CSS_SELECTOR, '#Email')
        google_login_next_locator = (By.CSS_SELECTOR, '#next')
        google_login_password_locator = (By.CSS_SELECTOR, '#password')
        google_login_submit_locator = (By.CSS_SELECTOR, '#submit')

        login_wait.until(EC.element_to_be_clickable(google_login_email_locator))\
            .send_keys(self.app_account.name)
        login_wait.until(EC.element_to_be_clickable(google_login_next_locator))\
            .click()
        login_wait.until(EC.element_to_be_clickable(google_login_password_locator))\
            .send_keys(self.app_account.password)
        login_wait.until(EC.element_to_be_clickable(google_login_submit_locator))\
            .click()

    def _google_login_headed_mode(self):
        login_wait = self.new_wait(timeout=10)

        self.log.info("Logging in to Soundcloud through Google, headed browser mode.")
        self.driver.get(self.google_login_url)

        google_name_field_locator = (By.XPATH, '//input[@id="identifierId"]')
        google_id_next_button_locator = (By.XPATH, '//*[@id="identifierNext"]//button')
        google_password_field_locator = (By.XPATH, '//input[@name="password"]')
        google_pw_next_button_locator = (By.XPATH, '//*[@id="passwordNext"]//button')

        login_wait.until(EC.element_to_be_clickable(google_name_field_locator))\
            .send_keys(self.app_account.name)
        login_wait.until(EC.element_to_be_clickable(google_id_next_button_locator))\
            .click()

        login_wait.until(EC.element_to_be_clickable(google_password_field_locator))\
            .send_keys(self.app_account.password)
        # this part is troublesome:
        for try_n in range(1, GOOGLE_LOGIN_RETRIES):
            try:
                login_wait.until(EC.element_to_be_clickable(google_pw_next_button_locator))\
                    .click()
                break
            except ElementClickInterceptedException:
                if try_n >= GOOGLE_LOGIN_RETRIES:
                    raise ApplicationHandlerException(f"Couldn't click submit login after {try_n} tries")
                self.log.warn(f"Failed to click submit for login (try {try_n} of {GOOGLE_LOGIN_RETRIES})")
                from time import sleep
                sleep(1)
                continue

        if self.haltlogin:
            self.log.warning("Halting login!")
            from time import sleep
            sleep(90000)
