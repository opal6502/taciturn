
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
import urllib.parse

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)

from taciturn.applications.base import ApplicationHandlerException
from taciturn.applications.login import LoginApplicationHandler


FACEBOOK_ACTION_RETRIES=10


class FacebookHandler(LoginApplicationHandler):
    application_name = 'facebook'

    application_url = "https://facebook.com"
    application_login_url = "https://facebook.com/login"

    def __init__(self, app_account, handler_stats=None, driver=None):
        super().__init__(app_account, handler_stats, driver)

    def login(self):
        login_wait = self.new_wait(timeout=10)
        self.driver.get(self.application_login_url)

        email_input_locator = (By.XPATH, '//input[@id="email"]')
        password_input_locator = (By.XPATH, '//input[@id="pass"]')
        login_button_locator = (By.XPATH, '//button[@id="loginbutton"]')

        login_wait.until(EC.element_to_be_clickable(email_input_locator))\
            .send_keys(self.app_username)
        login_wait.until(EC.element_to_be_clickable(password_input_locator))\
            .send_keys(self.app_password)
        login_wait.until(EC.element_to_be_clickable(login_button_locator))\
            .click()

        # check facebook icon to verify login (?) ...
        self._header_facebook_icon()

    def goto_homepage(self):
        self.driver.get(self.application_url)

    def goto_profile_page(self, user_name=None):
        if user_name:
            if self._is_facebook_id(user_name):
                profile_url = f'{self.application_url}/profile.php?id={user_name}'
            else:
                profile_url = f'{self.application_url}/{user_name}'
            self.log.debug(f"Going to page: {profile_url}")
            self.driver.get(profile_url)
        else:
            self._header_profile_tab().click()
            self._header_profile_tab_profile().click()

    def _is_facebook_id(self, user_name):
        return len(user_name) == 20 and user_name.isnumeric()

    def _header_facebook_icon(self):
        locator = (By.XPATH, '//*[starts-with(@id,"mount")]//a[@aria-label="Facebook"]')
        return self.new_wait().until(EC.visibility_of_element_located(locator))

    def _header_profile_tab(self):
        locator = (By.XPATH, '//*[starts-with(@id,"mount")]//div[@aria-label="Account"]/img')
        return self.new_wait().until(EC.element_to_be_clickable(locator))

    def _header_profile_tab_profile(self):
        locator = (By.XPATH, '//div[@aria-label="Account" and @role="dialog"]'
                             '//span[@dir="auto" and text()="See your profile"]')
        return self.new_wait().until(EC.element_to_be_clickable(locator))

    def _page_header_overhang_y(self):
        overhang_correction = 60
        header_element_locator = (By.XPATH, '//*[starts-with(@id,"mount")]/div/div/div[1]/div[3]/div/div'
                                            '/div[1]/div/div[2]/div/div/div[3]/div/div/div')
        header_element = self.new_wait().until(EC.presence_of_element_located(header_element_locator))
        self.element_scroll_to(header_element)

        overhang_y = self.element_rect_bottom(header_element)
        overhang_y_corrected = overhang_y + overhang_correction
        self.log.debug(f"_page_header_overhang_y: value = {overhang_y} + {overhang_correction} "
                       f"= {overhang_y_corrected} (padded value)")

        return overhang_y_corrected

    def _page_post_get_first(self):
        # locator = (By.XPATH, '//div[@aria-posinset="1"]')
        locator = (By.XPATH, '(//div[@aria-label="Page Admin Content"]//div[@role="main"]/div/div[1])[4]')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    def _page_element_rescroll(self, page_element):
        self.driver.execute_script("window.scrollTo(0,0);")
        header_overhang_y = self._page_header_overhang_y()
        self.element_scroll_to(page_element, y_offset=header_overhang_y)

    def _page_post_get_link(self, page_post, retries=FACEBOOK_ACTION_RETRIES):
        post_wait = self.new_wait(timeout=2)

        for try_n in range(1, retries+1):
            try:
                # this bit of voodoo IS REQUIRED for the post link to become visible:
                post_date_locator = (By.XPATH, '(.//span[contains(text(),"·")]/../../following-sibling::span)[1]')
                post_date_element = post_wait.until(EC.element_to_be_clickable(post_date_locator))

                self._page_element_rescroll(post_date_element)
                ActionChains(self.driver).move_to_element(post_date_element).perform()

                post_link_locator = (By.XPATH, '(.//span[contains(text(),"·")]/../../following-sibling::span)[1]//a')
                post_link_element = post_wait.until(EC.presence_of_element_located(post_link_locator))

                post_link_href = post_link_element.get_attribute('href')
                post_link = urllib.parse.urlparse(post_link_href).path

                self.log.debug(f"Got page post link: {post_link}")

                return urllib.parse.urlparse(post_link_href).path
            except TimeoutException:
                pass

        raise ApplicationHandlerException(f"Unable to scrape page post link after {retries} tries.")

    def _page_post_start_new(self, retries=FACEBOOK_ACTION_RETRIES):
        post_wait = self.new_wait(timeout=2)

        for try_n in range(1, retries+1):
            try:
                new_post_button_locator = (By.XPATH, '//*[starts-with(@id,"mount")]//div[@aria-label="Create Post"]'
                                                     '//span[text()="Create Post"]')
                new_post_button_element = post_wait.until(EC.element_to_be_clickable(new_post_button_locator))

                self._page_element_rescroll(new_post_button_element)

                new_post_button_element.click()

                return
            except (TimeoutException, ElementClickInterceptedException):
                pass

        raise ApplicationHandlerException(f"Unable to start new page post after {retries} tries.")

    def _page_post_input(self):
        return self._generic_post_input()

    def _group_post_input(self):
        return self._generic_post_input()

    def _generic_post_input(self):
        # locator = (By.XPATH, '(//div[@role="dialog"])[1]//div[@role="textbox" and @contenteditable="true"] | '
        #                     '(//div[@role="dialog"])[2]//div[@role="textbox" and @contenteditable="true"]')
        # new v0.1a xpath: '//h2[text()="Create Post"]/../../..//div[@role="textbox" and @contenteditable="true"]'
        locator = (By.XPATH, '//span[text()="Create Post"]/../../../../../..'
                             '//div[@role="textbox" and @contenteditable="true"]')
        return self.new_wait().until(EC.element_to_be_clickable(locator))

    def _page_post_wait_link_loading_invisible(self):
        # if the preview loading indicator is visible, give it some time:
        locator = (By.XPATH, '//*[starts-with(@id,"mount")]/div/div/div[1]/div[4]'
                             '//div[@data-visualcompletion="loading-state" and @role="progressbar"]')
        try:
            self.new_wait(timeout=90).until_not(EC.element_to_be_clickable(locator))
        except (NoSuchElementException, StaleElementReferenceException):
            pass

    def _page_post_wait_link_preview_xbutton_visible(self):
        locator = (By.XPATH, '//div[@aria-label="Remove post attachment"]/i')
        return self.new_wait(timeout=90).until(EC.element_to_be_clickable(locator))

    def _page_post_submit_button(self):
        locator = (By.XPATH, '//*[starts-with(@id,"mount")]//span[text()="Post"]')
        return self.new_wait().until(EC.element_to_be_clickable(locator))

    def _page_post_submit_new(self, post_body, post_link=None, retries=FACEBOOK_ACTION_RETRIES):
        # do new post:
        for try_n in range(1, retries+1):
            try:
                self.log.info(f"Submit new Facebook page post: creating new.")

                self._page_post_start_new()
                post_input = self._page_post_input()

                # establish link preview:
                if post_link:
                    self.log.debug("Submit new Facebook page post: inserting post link.")
                    post_input.send_keys(post_link + ' ')

                    # check for the odd "Query Error" dialog lightbox:
                    try:
                        self.log.debug("Checking for 'Query Error' message.")
                        query_error_locator = (By.XPATH, '//span[text()="Query Error"]')
                        self.new_wait(timeout=5).until(EC.presence_of_element_located(query_error_locator))

                        query_error_button_locator = (By.XPATH, '//div[@role="button" and text()="OK"]')
                        self.new_wait(timeout=5).until(EC.element_to_be_clickable(query_error_button_locator))\
                            .click()
                    except TimeoutException:
                        self.log.debug("No 'Query Error' detected!")

                    # wait for preview indicators, after much trying this isn't as robust as a sleep(10)?
                    # self.log.debug("Submit new Facebook page post: waiting for link to be loaded by Facebook.")
                    # self._page_post_wait_link_loading_invisible()
                    # self._page_post_wait_link_preview_xbutton_visible()
                    # self.log.debug("Submit new Facebook page post: looks like link was loaded by Facebook.")
                    sleep(10)

                    post_input.send_keys(Keys.COMMAND + 'a')
                    post_input.send_keys(Keys.BACKSPACE)

                self.log.debug("Submit new Facebook page post: sending post body.")
                post_input.send_keys(post_body)

                self.log.debug("Submit new Facebook page post: submitting new post.")
                self._page_post_submit_button().click()
                sleep(10)

                return
            except (TimeoutException, ElementClickInterceptedException):
                self.log.exception(f"Submit new Facebook page post: caught exception! (try {try_n} of {retries})")
                self.driver.refresh()
                self.kill_javascript_alert()
                continue

        raise ApplicationHandlerException(f"Submit new Facebook page post: "
                                          f"couldn't submit page post after {retries} tries.")

    def _page_post_verify_new(self, previous_first_post_link, retries=FACEBOOK_ACTION_RETRIES):
        self.log.info("Verify new Facebook page post: verifying new page post present.")

        for try_n in range(1, retries+1):
            new_first_post = self._page_post_get_first()
            new_first_post_link = self._page_post_get_link(new_first_post)
            # self.log.debug(f"Verify new Facebook page post: "
            #                f"new link different from previous: '{new_first_post_link}' != '{previous_first_post_link}'")
            if new_first_post_link != previous_first_post_link:
                self.log.info("Verify new Facebook page post: new post verified present.")
                return new_first_post_link
            # sleep(10)
            self.log.info("Verify new Facebook page post: new post not verified present, refreshing.")
            self.driver.refresh()

        raise ApplicationHandlerException(f"New page post didn't show up after {retries} tries.")

    def page_post_create(self, page_path, post_body, post_link=None):
        self.goto_path(page_path)

        # scan first post:
        page_post_first = self._page_post_get_first()
        page_post_first_link = self._page_post_get_link(page_post_first)

        self._page_post_submit_new(post_body, post_link)
        # self.driver.refresh()
        return self._page_post_verify_new(page_post_first_link)

    def _group_post_start_new(self, retries=FACEBOOK_ACTION_RETRIES):
        post_wait = self.new_wait(timeout=2)

        for try_n in range(1, retries+1):
            try:
                new_post_button_locator = (By.XPATH, '//div[@role="button"]'
                                                     '//span[starts-with(text(), "What\'s on your mind")]')
                new_post_button_element = post_wait.until(EC.element_to_be_clickable(new_post_button_locator))
                self.element_scroll_to(new_post_button_element, y_offset=300)
                new_post_button_element.click()
                return
            except (TimeoutException, ElementClickInterceptedException):
                pass

        raise ApplicationHandlerException(f"Unable to start new page post after {retries} tries.")

    def _group_post_submit_button(self):
        locator = (By.XPATH, '//*[starts-with(@id,"mount")]//div[@role="button"]//span[text()="Post"]')
        return self.new_wait().until(EC.element_to_be_clickable(locator))

    def _group_post_message_limit_reached(self):
        locator = (By.XPATH, '//div[starts-with(text(), "We limit how often you can post, '
                             'comment or do other things in a given amount of time")]')
        try:
            self.new_wait(timeout=5).until(EC.presence_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    def _group_post_submit_new(self, post_body, post_link=None, retries=FACEBOOK_ACTION_RETRIES):
        for try_n in range(1, retries+1):
            try:
                self.log.info(f"Submit new Facebook group post: creating new.")
                # start new post:
                self._group_post_start_new()
                post_input = self._group_post_input()
                if post_link:
                    self.log.debug("Submit new Facebook group post: inserting post link.")
                    post_input.send_keys(post_link + ' ')
                    sleep(10)
                    post_input.send_keys(Keys.COMMAND + 'a')
                    post_input.send_keys(Keys.BACKSPACE)

                self.log.debug("Submit new Facebook page post: sending post body.")
                post_input.send_keys(post_body)

                self.log.debug("Submit new Facebook page post: submitting new post.")
                self._group_post_submit_button().click()
                sleep(10)

                # check to see if posting limit has been reached:
                if self._group_post_message_limit_reached():
                    raise ApplicationFacebookPostLimitException

                # wait for input to become invisible:
                self.new_wait().until(EC.invisibility_of_element(post_input))

                return
            except (TimeoutException, ElementClickInterceptedException):
                self.log.exception(f"Submit new Facebook group post: caught exception! (try {try_n} of {retries})")
                self.driver.refresh()
                self.kill_javascript_alert()
                continue

        raise ApplicationHandlerException(f"Submit new Facebook group post: "
                                          f"couldn't submit page post after {retries} tries.")

    def group_post_create(self, group_path_name, post_body, post_link=None):
        if (group_path_name.startswith('http://') or
                group_path_name.startswith('https://')):
            self.driver.get(group_path_name)
        else:
            self.goto_path(f'groups/{group_path_name}')
        self._group_post_submit_new(post_body, post_link)

    def scan_page_videos(self, page_path):
        self.goto_path(f'{page_path}/videos')

        first_video_entry_locator = (By.XPATH, '//span[text()="All Videos"]/../../div/div/div/div[1]')
        video_entry_link_locator = (By.XPATH, '(.//a)[1]')
        video_entry_title_locator = (By.XPATH, '(.//a)[2]/span/span')
        next_video_entry_locator = (By.XPATH, './following-sibling::div[1]')

        # get the first entry:
        video_entry = self.new_wait().until(EC.presence_of_element_located(first_video_entry_locator))
        video_url_list = list()

        while True:
            self.element_scroll_to(video_entry)
            video_wait = self.new_wait(video_entry, timeout=10)

            try:
                video_title = video_wait.until(EC.presence_of_element_located(video_entry_title_locator)).text
                self.log.info(f"Scanning video '{video_title}'")
                video_link_element = video_wait.until(EC.presence_of_element_located(video_entry_link_locator))
                video_link_url = video_link_element.get_attribute('href')
            except TimeoutException:
                self.log.info("End of video list encountered.")
                break

            video_url_list.append(video_link_url)
            sleep(0.33)
            video_entry = video_wait.until(EC.presence_of_element_located(next_video_entry_locator))

        return video_url_list


class ApplicationFacebookPostLimitException(ApplicationHandlerException):
    pass
