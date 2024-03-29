
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


from time import sleep

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.common.action_chains import ActionChains

from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    NoSuchElementException
)

from taciturn.applications.base import ApplicationHandlerException
from taciturn.applications.follower import FollowerApplicationHandler
from taciturn.applications.google import GoogleLoginMixin


class SoundcloudHandler(FollowerApplicationHandler, GoogleLoginMixin):
    application_name = 'soundcloud'

    application_url = "https://soundcloud.com"
    application_login_url = application_url

    application_asset_dirname = 'soundcloud'
    default_profile_image = 'avatars-default-500x500.jpg'

    button_text_following = ('Following',)
    button_text_not_following = ('Follow', 'Follow back')

    def __init__(self, app_account, driver=None):
        super().__init__(app_account, driver)
        self.log.info("Starting Soundcloud app handler.")

        # login process is different in headed/headless mode:
        driver_name = self.options.driver[0] if self.options.driver else self.config['selenium_webdriver']
        if driver_name.endswith('_headless'):
            self.headless_mode = True
        else:
            self.headless_mode = False

    def login(self):
        self._google_login()
        sleep(5)
        self._google_login_soundcloud_submit()
        self._close_if_pro_lightbox()

        # use the 'Messages' element to verify login!
        messages_element_verify_locator = (By.XPATH, '//*[@id="app"]/header'
                                                     '/div/div[3]/div[2]/a[3]/div/span[contains(.,"Messages")]')
        self.new_wait().until(EC.presence_of_element_located(messages_element_verify_locator))

        self.log.info("Logged in.")

    def _google_login_soundcloud_submit(self):
        login_wait = self.new_wait(timeout=10)
        self.goto_homepage()

        alternate_login_button_locator = (By.CSS_SELECTOR, 'button.frontHero__loginButton:first-child')
        login_wait.until(EC.element_to_be_clickable(alternate_login_button_locator)) \
            .click()

        # switch to alternative login iframe:
        login_iframe_locator = (By.XPATH, '//iframe[@class="webAuthContainer__iframe"]')
        login_iframe_element = login_wait.until(EC.presence_of_element_located(login_iframe_locator))
        self.driver.switch_to.frame(login_iframe_element)

        # click google sign-in button:
        sc_google_login_button_locator = (By.CSS_SELECTOR, 'button.google-plus-signin')
        self.new_wait().until(EC.element_to_be_clickable(sc_google_login_button_locator)) \
            .click()

        # switch back from iframe:
        self.driver.switch_to.default_content()

    def _close_if_pro_lightbox(self):
        lb_wait = self.new_wait(timeout=5)
        try_pro_h1_locator = (By.XPATH, '/html/body/div/div/div/div/div[2]/h1')
        try_pro_xbutton_locator = (By.XPATH, '/html/body/div/a')
        try:
            try_pro_h1_element = lb_wait.until(EC.presence_of_element_located(try_pro_h1_locator))
            if try_pro_h1_element.text == 'TRY PRO RISK-FREE':
                try_pro_xbutton_element = lb_wait.until(EC.element_to_be_clickable(try_pro_xbutton_locator))
                if try_pro_xbutton_element.get_attribute('href') == 'javascript:appboyBridge.closeMessage()':
                    try_pro_xbutton_element.click()
        except TimeoutException:
            pass

    def goto_homepage(self):
        self.driver.get(self.application_url)

    def goto_profile_page(self, user_name=None):
        # navigate using the ui ... to accommodate google user email login ;)
        if user_name is None:
            header_profile_menu_locator = (By.XPATH, '//*[@id="app"]/header/div/div[3]/div[2]/a[1]/div[2]/div/span')
            header_profile_menu_profile_link_locator = (By.XPATH, '//*[starts-with(@id,"dropdown-button-")]'
                                                                  '/div/ul[1]/li[1]/a[text()="Profile"]')
            header_profile_menu_element = self.new_wait()\
                .until(EC.element_to_be_clickable(header_profile_menu_locator))
            self.element_scroll_to(header_profile_menu_element)
            header_profile_menu_element.click()
            self.new_wait().until(EC.element_to_be_clickable(header_profile_menu_profile_link_locator))\
                .click()
        else:
            self.driver.get(f'{self.application_url}/{user_name}')

    def goto_following_page(self, user_name=None):
        if user_name is None:
            self.goto_profile_page()
            profile_following_link_locator = (By.XPATH, '//*[@id="content"]/div/div[4]/div[2]/div/article[1]'
                                                        '/table/tbody/tr/td[2]/a/h3[text()="Following"]')
            self.new_wait().until(EC.element_to_be_clickable(profile_following_link_locator))\
                .click()
        else:
            self.driver.get(f'{self.application_url}/{user_name}/following')

    def goto_followers_page(self, user_name=None):
        if user_name is None:
            self.goto_profile_page()
            profile_followers_link_locator = (By.XPATH, '//*[@id="content"]/div/div[4]/div[2]/div/article[1]'
                                                        '/table/tbody/tr/td[1]/a/h3[text()="Followers"]')
            self.new_wait().until(EC.element_to_be_clickable(profile_followers_link_locator))\
                .click()
        else:
            self.driver.get(f'{self.application_url}/{user_name}/followers')

    def has_unfollow_confirm(self):
        return False

    def unfollow_confirm_button(self):
        return False

    # new flist methods:

    def _flist_first_from_either(self):
        sleep(5)
        locator = (By.XPATH, '//*[@id="content"]/div/div/div[2]/div/div/ul/li[contains(@class, "badgeList__item")][1]')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    def flist_first_from_following(self):
        super().flist_first_from_following()
        return self._flist_first_from_either()

    def flist_first_from_followers(self):
        super().flist_first_from_followers()
        return self._flist_first_from_either()

    def flist_next(self, flist_entry):
        super().flist_next(None)
        sleep(0.05)
        locator = (By.XPATH, './following-sibling::li[1]')
        return self.new_wait(flist_entry).until(EC.presence_of_element_located(locator))
        
    def flist_is_last(self, flist_entry):
        locator = (By.XPATH, '//*[@id="content"]/div/div/div[2]/div/div/ul'
                             '/li[contains(@class, "badgeList__item")][last()]')
        last_entry = self.new_wait().until(EC.presence_of_element_located(locator))
        return flist_entry == last_entry
        
    def flist_is_empty(self, flist_entry):
        return False

    def flist_username(self, flist_entry):
        locator = (By.XPATH, './div/div[2]/a')
        return self.new_wait(flist_entry).until(EC.presence_of_element_located(locator))\
                        .get_attribute('href').rsplit('/', 1)[-1]

    def flist_image_is_default(self, flist_entry):
        locator = (By.XPATH, './div/div[1]/a/div/span')
        image_css_value = self.new_wait(flist_entry).until(EC.presence_of_element_located(locator))\
                                .value_of_css_property('background-image')
        if image_css_value.startswith('url("https://'):
            image_url = image_css_value[5:-2]
            return self.is_default_image(image_url)
        else:
            return True

    def flist_is_verified(self, flist_entry):
        return False

    def flist_button(self, flist_entry):
        locator = (By.XPATH, './div/div[3]/button')
        button_element = self.new_wait(flist_entry).until(EC.presence_of_element_located(locator))
        ActionChains(self.driver).move_to_element(button_element).perform()
        return button_element
    
    def flist_button_text(self, flist_entry):
        return self.flist_button(flist_entry).text

    def flist_header_overlap_y(self):
        header_element_locator = (By.XPATH, '//*[@id="content"]/div/div/div[1]')
        header_element = self.new_wait().until(EC.presence_of_element_located(header_element_locator))
        return self.element_rect_bottom(header_element)

    def flist_is_action_limit_notice(self):
        blocked_overlay_locator = (By.XPATH, '//*[starts-with(@id, "overlay_")]/div/div/div/p[2]')
        blocked_message_locator = (By.XPATH, '//*[starts-with(@id, "overlay_")]/div/div/div/p[5]')
        blocked_text = 'We have temporarily blocked'
        try:
            self.driver.find_element(*blocked_overlay_locator)
            blocked_text = self.driver.find_element(*blocked_message_locator).text
            if blocked_text.startswith(blocked_text):
                return True
            else:
                raise ApplicationHandlerException(f"Got unexpected text from blocked notice: '{blocked_text}'")
        except (StaleElementReferenceException, TimeoutException, NoSuchElementException):
            return False

    def flist_is_blocked_notice(self):
        return False
