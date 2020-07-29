
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


from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException
)

from taciturn.applications.base import ApplicationHandlerException
from taciturn.applications.follower import FollowerApplicationHandler

INSTAGRAM_ACTION_RETRIES = 20


class InstagramHandler(FollowerApplicationHandler):
    application_name = 'instagram'

    application_url = "https://instagram.com"
    application_login_url = application_url

    # sent an iPhone user agent to enable mobile functionality!
    webdriver_user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X) AppleWebKit/536.26 " \
                             "(KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25"

    application_asset_dirname = 'instagram'
    default_profile_image = 'default-profile-pic.jpg'

    button_text_following = ('Following', 'Requested')
    button_text_not_following = ('Follow',)

    _flist_lighbox_prefix = '//div[@role="presentation"]/div[@role="dialog"]'
    flist_prefix_xpath = _flist_lighbox_prefix + '/div/div[2]/ul/div/li[{}]'

    def __init__(self, app_account, handler_stats=None, driver=None):
        super().__init__(app_account, handler_stats, driver)
        self.log.info("Starting Instagram app handler.")

    def login(self):
        login_optional_wait_args = dict(ignored_exceptions=[StaleElementReferenceException, NoSuchElementException],
                                        timeout=5)
        login_optional_wait = self.new_wait(**login_optional_wait_args)

        self.driver.get(self.application_login_url)

        # possible occurrence:  an initial login button is sometimes present:
        try:
            locator = (By.XPATH, '//*[@id="react-root"]/section/main/article//div[2]/button')
            first_login_button = login_optional_wait.until(EC.element_to_be_clickable(locator))
            first_login_button.click()
        except TimeoutException:
            pass

        # enter username and password:
        login_form_locator = (By.XPATH, '//form')
        login_name_field_locator = (By.NAME, 'username')
        login_password_field_locator = (By.NAME, 'password')
        login_button_locator = (By.XPATH, '//button/div')

        login_form_wait = self.new_wait(timeout=10)

        login_form_wait.until(EC.element_to_be_clickable(login_form_locator))
        login_form_wait.until(EC.element_to_be_clickable(login_name_field_locator))\
                                    .send_keys(self.app_username)
        login_form_wait.until(EC.element_to_be_clickable(login_password_field_locator))\
                                    .send_keys(self.app_password)
        login_form_wait.until(EC.element_to_be_clickable(login_button_locator))\
                                    .click()

        # sometimes prompted with extra security, check if bypass necessary:

        # possible occurrence:  suspicious login attempt, text security code:
        try:
            suspicious_login_locator = (By.XPATH, '//*[@id="react-root"]/section/div/div/div[2]'
                                                  '/h2[text()="We Detected An Unusual Login Attempt"]')
            suspicious_login_phone_locator = (By.XPATH, '//*[@id="react-root"]/section/div/div/div[3]'
                                                        '/form/div/div/label')
            security_code_send_button_locator = (By.XPATH, '//*[@id="react-root"]/section/div/div/div[3]'
                                                           '/form/span/button[text()="Send Security Code"]')
            security_code_input_locator = (By.XPATH, '//input[@id="security_code"]')
            security_code_submit_button_locator = (By.XPATH, '//*[@id="react-root"]/section/div/div/div[2]'
                                                             '/form/span/button[text()="Submit"]')
            security_code_incorrect_locator = (By.XPATH, '//*[@id="form_error"]'
                                                         '/p[text()="Please check the code we sent you and try again."]')
            login_optional_wait.until(EC.presence_of_element_located(suspicious_login_locator))
            security_code_phone = login_optional_wait.\
                until(EC.presence_of_element_located(suspicious_login_phone_locator)).text
            self.log.warning("Suspicious login detected, requesting security code.")
            self.log.warning(f"Sending security code to {security_code_phone}, check for message.")
            login_optional_wait.until(EC.element_to_be_clickable(security_code_send_button_locator))\
                                            .click()
            while True:
                security_code = input("Enter 6-digit security code: ")
                login_optional_wait.until(EC.element_to_be_clickable(security_code_input_locator))\
                    .send_keys(security_code)
                login_optional_wait.until(EC.element_to_be_clickable(security_code_submit_button_locator))\
                    .click()
                # check for input failure:
                try:
                    login_optional_wait.until(EC.presence_of_element_located(security_code_incorrect_locator))
                    self.log.warning("Code not accepted, try again.")
                    login_optional_wait.until(EC.element_to_be_clickable(security_code_input_locator)) \
                        .send_keys(Keys.COMMAND + 'a' + Keys.BACKSPACE)
                    continue
                except TimeoutException:
                    break

            # apparently succeeded:
            self.log.warning("Security code accepted.")
        except TimeoutException:
            self.log.info("No suspicious login prompt, skipping")

        # possible occurrence:  bypass prompt to save our login info, if present:
        try:
            locator = (By.XPATH, '//button[contains(.,"Not Now")]')
            not_now_link = login_optional_wait.until(EC.element_to_be_clickable(locator))
            not_now_link.click()
        except TimeoutException:
            self.log.debug("No save login prompt, skipping.")

        # possible occurrence:  sometimes prompted with an "add instagram to home screen?" choice:
        try:
            hs_dialog_locator = (By.XPATH, '/html/body/div[4]/div/div/div/div[2]/h2')
            hs_cancel_button_locator = (By.XPATH, '//button[text()="Cancel"]')
            hs_dialog_text = login_optional_wait.until(EC.presence_of_element_located(hs_dialog_locator))\
                                .text
            if hs_dialog_text == "Add Instagram to your Home screen?":
                login_optional_wait.until(EC.element_to_be_clickable(hs_cancel_button_locator))\
                                       .click()
        except TimeoutException:
            self.log.debug("No home screen dialog, skipping.")

        self.driver.refresh()

        # possible occurrence:  sometimes prompted with notifications on/off choice:
        try:
            dialog_locator = (By.XPATH, '//div[@role="dialog"]')
            notify_text_locator = (By.XPATH, '//h2[contains(.,"Turn on Notifications")]')
            notify_button_locator = (By.XPATH, '//button[contains(.,"Not Now")]')
            dialog_element = login_optional_wait.until(EC.presence_of_element_located(dialog_locator))
            dialog_wait = self.new_wait(dialog_element, **login_optional_wait_args)
            dialog_wait.until(EC.presence_of_element_located(notify_text_locator))
            dialog_wait.until(EC.element_to_be_clickable(notify_button_locator))\
                                    .click()
        except TimeoutException:
            self.log.debug("No notification dialog, skipping.")

        # verify login:
        try:
            self._header_logo_image()
        except TimeoutException:
            raise ApplicationHandlerException("Couldn't verify Instagram login.")

    def _header_logo_image(self):
        locator = (By.XPATH, '//*[@id="react-root"]/section/nav[1]'
                             '/div/div/header/div/h1/div/a/img[@alt="Instagram"]')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    def goto_homepage(self):
        self.driver.get(self.application_url)

    def goto_profile_page(self, user_name=None):
        if user_name is not None:
            self.driver.get('{}/{}'.format(self.application_url, user_name))
        else:
            self.driver.get(self.application_url)
            # regular browser selector or mobile browser selector:
            profile_link_locator = (By.XPATH, '//*[@id="react-root"]/section/main/section'
                                              '/div[3]/div[1]/div/div[2]/div[1]/a | '
                                              '//*[@id="react-root"]/section/nav[2]/div/div/div[2]/div/div/div[5]/a')
            self.new_wait().until(EC.element_to_be_clickable(profile_link_locator))\
                                        .click()

    def goto_following_page(self, user_name=None):
        self.goto_profile_page(user_name)

        followers_link_locator = (By.XPATH, '//a[contains(.," following")]')
        self.new_wait().until(EC.element_to_be_clickable(followers_link_locator))\
                                    .click()

    def goto_followers_page(self, user_name=None):
        self.goto_profile_page(user_name)

        followers_link_locator = (By.XPATH, '//a[contains(.," followers")]')
        self.new_wait().until(EC.element_to_be_clickable(followers_link_locator))\
                                    .click()

    def has_unfollow_confirm(self):
        return True

    def unfollow_confirm_button(self):
        locator = (By.XPATH, self._flist_lighbox_prefix + '//button[contains(.,"Unfollow")]')
        return self.new_wait().until(EC.element_to_be_clickable(locator))

    # flist methods:

    def flist_current_locator(self):
        locator = By.XPATH, self.flist_prefix_xpath.format(self.flist_get_position())
        # self.log.debug(f"flist_current_locator: {locator}"))
        return locator

    def _flist_first_from_either(self):
        locator = (By.XPATH, self._flist_lighbox_prefix + '/div/div[2]/ul/div/li[1]')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    def flist_first_from_following(self):
        super().flist_first_from_following()
        return self._flist_first_from_either()

    def flist_first_from_followers(self):
        super().flist_first_from_followers()
        return self._flist_first_from_either()

    def flist_next(self, flist_entry):
        locator = (By.XPATH, './following-sibling::li[1]')
        flist_next_entry = self.flist_wait_find_at_current(locator=locator,
                                                           flist_entry=flist_entry)
        super().flist_next(None)
        return flist_next_entry

    def _flist_last(self):
        locator = (By.XPATH, self._flist_lighbox_prefix + '/div/div[2]/ul/div/li[last()]')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    def flist_is_last(self, flist_entry):
        flist_last_element = self._flist_last()
        return flist_entry == flist_last_element

    def flist_is_empty(self, flist_entry):
        return False

    def flist_username(self, flist_entry):
        # ./div/div[1]/div[2]/div[1]/a
        # locator = (By.XPATH, './div/div[1]/div[2]/div[1]/a | ./div/div[2]/div[1]/div/div/a')
        locator = (By.CSS_SELECTOR, 'div > div > div > div > a, div > div > div > div > div > a')
        return self.flist_wait_find_at_current(locator=locator,
                                               flist_entry=flist_entry,
                                               timeout=10,
                                               text=True)

    def flist_image_is_default(self, flist_entry):
        # locator = (By.XPATH, './div/div[1]/div[1]/*[self::a or self::span]/img')
        locator = (By.CSS_SELECTOR, 'div > div > div > a > img, div > div > div > span > img')
        image_src = self.flist_wait_find_at_current(locator=locator,
                                                    flist_entry=flist_entry,
                                                    timeout=10,
                                                    get_attribute='src')
        return self.is_default_image(image_src)

    def flist_is_verified(self, flist_entry):
        # locator = (By.XPATH, './div/div[2]/div[1]/div/div/span[@title="Verified"]')
        locator = (By.CSS_SELECTOR, 'div > div > div > div > div > span[title="Verified"]')
        try:
            self.flist_wait_find_at_current(locator=locator,
                                            flist_entry=flist_entry,
                                            timeout=0)
            return True
        except TimeoutException:
            return False

    def _flist_button_locator(self):
        # locator = (By.XPATH, './div/div[2]/button | ./div/div[3]/button')
        return (By.CSS_SELECTOR, 'div > div > button')

    def flist_button(self, flist_entry):
        locator = self._flist_button_locator()
        return self.flist_wait_find_at_current(locator=locator,
                                               flist_entry=flist_entry,
                                               clickable=True)

    def flist_button_text(self, flist_entry):
        locator = self._flist_button_locator()
        return self.flist_wait_find_at_current(locator=locator,
                                               flist_entry=flist_entry,
                                               text=True)

    def flist_header_overlap_y(self):
        locator = (By.XPATH, self._flist_lighbox_prefix + '/div/div[2]')
        element = self.new_wait().until(EC.presence_of_element_located(locator))
        return self.element_rect_top(element)

    def flist_is_blocked_notice(self):
        return False

    def flist_is_action_limit_notice(self):
        locator = (By.XPATH, '/html/body/div[5]/div/div/div/div[1]/h3[text()="Try Again Later"]')
        try:
            self.driver.find_element(*locator)
            return True
        except (NoSuchElementException, TimeoutException):
            return False

    def _post_image_upload_button(self):
        locator = (By.XPATH, '//div[@data-testid="new-post-button"]')
        return self.new_wait().until(EC.element_to_be_clickable(locator))

    def _post_image_next_button(self):
        locator = (By.XPATH, '//button[text() = "Next"]')
        return self.new_wait(timeout=10).until(EC.element_to_be_clickable(locator))

    def _post_image_input(self):
        # inputs seen on the instagram page:
        # 1.  //*[@id="react-root"]/section/main/div/form/input
        # 2.  //*[@id="react-root"]/section/nav[1]/div/div/form/input
        locator = (By.XPATH, '//*[@id="react-root"]/section/main/div/form/input')
        return self.new_wait().until(EC.element_to_be_clickable(locator))

    def post_image(self, image_filename, post_body, retries=INSTAGRAM_ACTION_RETRIES):
        expand_image_locator = (By.XPATH, '//button/span[contains(@class, "createSpriteExpand") and text()="Expand"]')
        caption_input_locator = (By.XPATH, '//textarea[@aria-label="Write a caption…"]')
        share_button_locator = (By.XPATH, '//button[text() = "Share"]')
        next_button_element = None

        # submit image, part 1: get instagram to accept our image:
        for try_n in range(1, retries+1):
            try:
                self._post_image_input()\
                    .send_keys(image_filename)
                self._post_image_upload_button()\
                    .click()
                # next button must be present if operation is successful:
                next_button_element = self._post_image_next_button()
                break
            except TimeoutException:
                self.log.warning(f"Image post not accepted (try {try_n} of {retries})")
                self.driver.refresh()
        else:
            raise ApplicationHandlerException(f"Couldn't submit image after {retries} tries.")

        # submit image, part 2: click on expand button, to adjust image aspect ratio, if present:
        try:
            resize_image_element = self.driver.find_element(*expand_image_locator)
            self.element_scroll_to(resize_image_element)
            resize_image_element.click()
        except (NoSuchElementException, TimeoutException):
            pass

        # submit image, part 2: click next, send post body, click submit
        next_button_element.click()
        self.new_wait().until(EC.element_to_be_clickable(caption_input_locator))\
            .send_keys(post_body)
        self.new_wait().until(EC.element_to_be_clickable(share_button_locator))\
            .click()

        # submit image, part 3: verify post sent by checking 'Instagram' header image:
        try:
            self._header_logo_image()
        except TimeoutException:
            raise ApplicationHandlerException("Couldn't verify new Instagram image post.")
