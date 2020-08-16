
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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException
)

from taciturn.applications.base import ApplicationHandlerException
from taciturn.applications.follower import FollowerApplicationHandler, ApplicationHandlerEndOfListException


class TwitterHandler(FollowerApplicationHandler):
    application_name = 'twitter'

    application_url = "https://twitter.com"
    application_login_url = "https://twitter.com/login"

    application_asset_dirname = 'twitter'
    default_profile_image = 'default_profile_reasonably_small.png'

    button_text_following = ('Following', 'Pending', 'Cancel', 'Unfollow')
    button_text_not_following = ('Follow',)

    def __init__(self, app_account, handler_stats=None, driver=None):
        super().__init__(app_account, handler_stats, driver)
        self.log.info("Starting Twitter app handler.")

    def login(self):
        self.goto_login_page()

        self._login_enter_forms()

        # This is handy when for manually dealing with suspicious login attempts in-session, which
        # you do have to do sometimes:
        if self.haltlogin:
            self.log.warning("Halting login!")
            from time import sleep
            sleep(90000)

        # could be prompted with unusual activity here:

        # //*[@id="react-root"]/div/div/div[2]/main/div/div/div[1]/span/text()
        # "There was unusual login activity on your account. To help keep your account safe, please enter your phone number or email address to verify it’s you."

        unusual_activity_prompt_text = "There was unusual login activity on your account. To help keep your account " \
                                       "safe, please enter your phone number or email address to verify it’s you."
        unusual_activity_prompt_xpath = f'//*[@id="react-root"]/div/div/div[2]/main/div/div/div[1]' \
                                        f'/span[text()="{unusual_activity_prompt_text}"]'
        unusual_activity_prompt_locator = (By.XPATH, unusual_activity_prompt_xpath)

        try:
            self.driver.find_element(*unusual_activity_prompt_locator)
            self.log.warning("Got unusual activity login, attempting login again, this won't work unless your "
                             "account login is an email address!  It's a good idea to change it to an email address "
                             "if you haven't already!")
            self._login_enter_forms()
        except NoSuchElementException:
            pass

        # could be prompted with aReCAPTCHA here:

        recaptcha_prompt_text = "Let’s check one thing first. Please confirm you’re not a robot by " \
                                "passing a Google reCAPTCHA challenge."
        recaptcha_prompt_xpath = f'//*[@id="react-root"]/div/div/div[2]/main/div/div' \
                                 f'/div[2]/div[1]/span[text()="{recaptcha_prompt_text}"]'
        recaptcha_prompt_locator = (By.XPATH, recaptcha_prompt_xpath)

        try:
            self.driver.find_element(*recaptcha_prompt_locator)
            raise ApplicationHandlerException("Being prompted to pass a reCAPTCHA challenge.")
        except NoSuchElementException:
            pass

        # use this to verify login ...
        self._home_profile_link_element()
        # refresh, because sometimes login isn't fully processed ...
        self.driver.refresh()

        self.log.info("Logged in.")

    def _login_enter_forms(self):
        login_wait = self.new_wait(timeout=10)

        username_input_selector = (By.XPATH, '//div[@aria-hidden="false"]//form[@action="/sessions"]'
                                             '//input[@name="session[username_or_email]"]')
        login_wait.until(EC.presence_of_element_located(username_input_selector))\
            .send_keys(self.app_username)

        password_input_selector = (By.XPATH, '//div[@aria-hidden="false"]//form[@action="/sessions"]'
                                             '//input[@name="session[password]"]')
        login_wait.until(EC.presence_of_element_located(password_input_selector))\
            .send_keys(self.app_password)

        login_button_selector = (By.XPATH, '//div[@aria-hidden="false"]//form[@action="/sessions"]'
                                           '//span/span[contains(.,"Log in")]')
        login_wait.until(EC.presence_of_element_located(login_button_selector))\
            .click()

    def _is_stale_login_lightbox_present(self):
        lightbox_text_locator = (By.XPATH, '//*[@id="react-root"]//span[text()="Don’t miss what’s happening"]')
        try:
            if self.new_wait(timeout=3).until(EC.presence_of_element_located(lightbox_text_locator)):
                return True
        except TimeoutException:
            return False

    def _home_profile_link_element(self):
        # //*[@id="react-root"]/div/div/div[2]/header/div/div/div/div[1]/div[2]/nav/a[7]
        # nav aria-label="Primary"
        # a aria-label="Profile"
        profile_link_locator = (By.XPATH, '//nav[@aria-label="Primary"]/a[@aria-label="Profile"]')
        return self.new_wait(timeout=10).until(EC.presence_of_element_located(profile_link_locator))

    def goto_homepage(self):
        homepage_link = self.application_url + '/home'
        while True:
            self.log.info(f"Going to home page: {homepage_link}")
            self.driver.get(homepage_link)

            if self._is_stale_login_lightbox_present():
                self.driver.refresh()
                continue
            else:
                break

    def goto_profile_page(self, user_name=None):
        while True:
            if user_name is None:
                self.driver.get(self.application_url + '/home')
                profile_link = self._home_profile_link_element().get_attribute('href')
                self.log.info(f"Going to page: {profile_link}")
                self.driver.get(profile_link)
            else:
                user_profile_link = '{}/{}'.format(self.application_url, user_name)
                self.log.info(f"Going to page: {user_profile_link}")
                self.driver.get(user_profile_link)

            if self._is_stale_login_lightbox_present():
                self.driver.refresh()
                continue
            else:
                break

    def goto_following_page(self, user_name=None):
        while True:
            if user_name is None:
                self.log.info("Going to user following page.")
                self.goto_profile_page()
                locator = (By.XPATH, '//*[@id="react-root"]//div[1]/a/span[2]/span[text()="Following"]')
                self.new_wait(timeout=10)\
                       .until(EC.presence_of_element_located(locator)).click()
            else:
                user_following_link = '{}/{}/following'.format(self.application_url, user_name)
                self.log.info(f"Going to page: {user_following_link}")
                self.driver.get(user_following_link)

            if self._is_stale_login_lightbox_present():
                self.driver.refresh()
                continue
            else:
                break

    def goto_followers_page(self, user_name=None):
        while True:
            if user_name is None:
                self.log.info("Going to user followers page.")
                self.goto_profile_page()
                locator = (By.XPATH, '//*[@id="react-root"]//div[2]/a/span[2]/span[text()="Followers"]')
                self.new_wait(timeout=10)\
                       .until(EC.presence_of_element_located(locator)).click()
            else:
                user_followers_link = '{}/{}/followers'.format(self.application_url, user_name)
                self.log.info(f"Going to page: {user_followers_link}")
                self.driver.get(user_followers_link)

            if self._is_stale_login_lightbox_present():
                self.driver.refresh()
                continue
            else:
                break

    def post_tweet(self, tweet_body, tweet_image=None):
        self.log.info("Posting new tweet.")

        post_wait = self.new_wait(timeout=90)
        compose_tweet_button = (By.XPATH, '//a[@href="/compose/tweet" and @role="button"]')
        post_wait.until(EC.presence_of_element_located(compose_tweet_button))\
            .click()

        tweet_text_input_locator = (By.XPATH, '//div[@aria-label="Tweet text"]')
        tweet_text_input_element = post_wait.until(EC.presence_of_element_located(tweet_text_input_locator))
        truncated_tweet_body = self.truncate_tweet(tweet_body)
        tweet_text_input_element.send_keys(truncated_tweet_body)
        tweet_text_input_element.send_keys(Keys.ESCAPE)

        if tweet_image is not None:
            tweet_image_input_locator = (By.XPATH, '//div[@aria-label="Add photos or video"]'
                                                   '/following-sibling::input[@type="file"]')
            tweet_image_input_element = post_wait.until(EC.presence_of_element_located(tweet_image_input_locator))
            tweet_image_input_element.send_keys(tweet_image)

            self.log.debug("Waiting for tweet image attachment.")
            tweet_image_attached_locator = (By.XPATH, '//div[@aria-label="Media" and @role="group"]//img')
            post_wait.until(EC.presence_of_element_located(tweet_image_attached_locator))
            self.log.debug("Tweet image attachment verified.")

        submit_tweet_button_locator = (By.XPATH, '//div[@role="button"]//span[text()="Tweet"]/../../../div')
        submit_tweet_button_element = post_wait.until(EC.presence_of_element_located(submit_tweet_button_locator))
        self.element_scroll_to(submit_tweet_button_element)
        submit_tweet_button_element.click()

        # wait for the lightbox (x) to dissapear, to verify tweet sent ...
        tweet_lightbox_xbutton_locator = (By.XPATH, '//div[@aria-label="Close" and @role="button"]/div[@dir="auto"]')
        tweet_lightbox_xbutton_element = post_wait.until(EC.presence_of_element_located(tweet_lightbox_xbutton_locator))
        post_wait.until(EC.staleness_of(tweet_lightbox_xbutton_element))
        self.log.info("Tweet submitted.")

    def truncate_tweet(self, tweet_text):
        # scan the tweet and determine length including links, and truncate at the last word:
        # all links are 23 chars long!
        scan_position = 0
        last_scanned_space = 0
        tweet_limit = 240
        effective_tweet_length = 0
        link_prefixes = ('http://', 'https://')
        max_prefix_length = max(map(lambda p: len(p), link_prefixes))
        while scan_position <= len(tweet_text) and effective_tweet_length <= tweet_limit:
            if tweet_text[scan_position].isspace():
                last_scanned_space = scan_position
                scan_position += 1
                effective_tweet_length += 1
                # try to scan consecutive spaces so we mark the leftmost last consecutive space:
                while scan_position <= len(tweet_text) and effective_tweet_length <= tweet_limit:
                    if tweet_text[scan_position].isspace():
                        scan_position += 1
                        effective_tweet_length += 1
                    else:
                        break
            elif not tweet_text[scan_position].isspace():
                # try to scan for links:
                for prefix in link_prefixes:
                    # we have a link, scan its entire length, but add only 23 to effective tweet length:
                    if tweet_text[scan_position:scan_position+len(prefix)].startswith(prefix):
                        while scan_position <= len(tweet_text) and effective_tweet_length <= tweet_limit:
                            if tweet_text[scan_position].isspace():
                                scan_position += 1
                                effective_tweet_length += 23
                                break
                            elif not tweet_text[scan_position].isspace() and scan_position >= len(tweet_text):
                                scan_position += 1
                                effective_tweet_length += 23
                                break
                            else:
                                scan_position += 1
                        else:
                            effective_tweet_length += 23
                else:
                    scan_position += 1
                    if self.is_twitter_single_char_value(tweet_text[scan_position]):
                        effective_tweet_length += 1
                    else:
                        effective_tweet_length += 2

        # debug:
        self.log.debug(f"truncate_tweet: len(tweet_text) = {len(tweet_text)}")
        self.log.debug(f"truncate_tweet: scan_position = {scan_position}")
        self.log.debug(f"truncate_tweet: effective_tweet_length = {effective_tweet_length}")
        self.log.debug(f"truncate_tweet: last_scanned_space = {last_scanned_space}")

        if effective_tweet_length <= tweet_limit:
            return tweet_text
        elif last_scanned_space > 0:
            # truncate at last word!
            return tweet_text[:last_scanned_space]
        else:
            raise ValueError("Couldn't truncate body string for twitter!")

    @staticmethod
    def is_twitter_single_char_value(c):
        # code ranges gotten from: https://developer.twitter.com/en/docs/basics/counting-characters
        ord_c = ord(c)
        if (0x0000 <= ord_c <= 0x10FF or
            0x2000 <= ord_c <= 0x200D or
            ord_c == 0x200E or
            ord_c == 0x200F or
            0x2010 <= ord_c <= 0x201F or
            0x2032 <= ord_c <= 0x2037):
            return True
        return False

    def has_unfollow_confirm(self):
        return True

    def unfollow_confirm_button(self):
        locator = (By.XPATH, '//*[@id="react-root"]//span/span[text() = "Unfollow"]')
        return self.new_wait(timeout=10).until(EC.presence_of_element_located(locator))

    # XXX NEW 0.2a flist METHODS!

    def flist_first_from_following(self):
        super().flist_first_from_following()
        # //div[@id='react-root']/div/div/div[2]/main/div/div/div/div/div/div[2]/section/div/div/div[3]/div/div/div/div[2]/div
        locator = (By.XPATH, '//section[starts-with(@aria-labelledby, "accessible-list-")]'
                             '/div[@aria-label="Timeline: Following"]/div/div[1]')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    def flist_first_from_followers(self):
        super().flist_first_from_followers()
        locator = (By.XPATH, '//section[starts-with(@aria-labelledby, "accessible-list-")]'
                             '/div[@aria-label="Timeline: Followers"]/div/div[1]')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    def flist_next(self, flist_entry, retries=10):
        super().flist_next(None)
        flist_next_locator = (By.XPATH, './following-sibling::div[1]')
        for try_n in range(1, retries+1):
            try:
                flist_next_element = self.new_wait(flist_entry)\
                    .until(EC.presence_of_element_located(flist_next_locator))
                self.flist_button(flist_next_element)   # scan username
                return flist_next_element
            except TimeoutException:
                self.log.warning(f"Couldn't scan flist next (try {try_n} of {retries})")
                # sleep(10) -- default new_wait timeout is 60 seconds!
                continue
        raise ApplicationHandlerEndOfListException("Unable to scan next flist element.")

    def flist_is_last(self, flist_entry):
        return False

    def flist_is_empty(self, flist_entry):
        # need to thoroughly check for absence of a proper entry, here we check by username ...
        username_locator = self._flist_username_locator()
        try:
            self.new_wait(flist_entry, timeout=20)\
                .until(EC.presence_of_element_located(username_locator))
            return False
        except TimeoutException:
            pass
        # then, try to check for an empty node, will raise TimeoutException if not found:
        empty_locator = (By.XPATH, './div/div[not(node())]')
        self.new_wait(flist_entry, timeout=30)\
                .until(EC.presence_of_element_located(empty_locator))
        return True

    def flist_username(self, flist_entry):
        locator = self._flist_username_locator()
        return self.new_wait(flist_entry).until(EC.presence_of_element_located(locator)).text

    def _flist_username_locator(self):
        return (By.XPATH, './/div/span[starts-with(text(), "@")] | '
                          './/span/span[starts-with(text(), "@")]')
        # return (By.XPATH, './div/div/div/div[2]/div/div[1]/a/div/div[2]/div/span[starts-with(text(), "@")] | '
        #              './div/div/div/div[2]/div/div[1]/a/div/div/div[1]/span/span[starts-with(text(), "@")]')

    def flist_image_is_default(self, flist_entry):
        locator = (By.XPATH, './div/div/div/div[1]/div/a/div[1]/div[2]/div/img')
        image_src = self.new_wait(flist_entry, timeout=90)\
            .until(EC.presence_of_element_located(locator)).get_attribute('src')
        return self.is_default_image(image_src)

    def flist_is_verified(self, flist_entry):
        locator = (By.XPATH, './div/div/div/div[2]/div[1]/div[1]/a/div/div[1]/div[2]/'
                             '*[local-name()="svg" and @aria-label="Verified account"]')
        try:
            self.driver.find_element(*locator)
            return True
        except (NoSuchElementException, TimeoutException):
            return False

    def flist_button(self, flist_entry):
        locator = (By.XPATH, './div/div/div/div[2]/div/div[2]/div/div/span/span')
        return self.new_wait(flist_entry).until(EC.element_to_be_clickable(locator))

    def flist_button_text(self, flist_entry):
        return self.flist_button(flist_entry).text

    def flist_header_overlap_y(self):
        header_locator = (By.XPATH, '(//div[@data-testid="primaryColumn"]/div/div)[1]')
        header_element = self.new_wait().until(EC.presence_of_element_located(header_locator))
        element_y = header_element.size['height']
        self.log.debug(f"flist_header_overlap_y = {element_y}")
        return element_y

    def flist_is_blocked_notice(self):
        popover = self._flist_bottom_notify_popover()
        if popover is None:
            return False
        popover_text = popover.text
        if (popover_text is not None and
                popover_text == 'You have been blocked from following this user at their request.'):
            # halt and wait until the blocked notice disappers, so it doesn't confuse us later:
            self.new_wait().until(EC.staleness_of(popover))
            return True
        return False

    def flist_is_action_limit_notice(self):
        popover = self._flist_bottom_notify_popover()
        if popover is None:
            return False
        popover_text = popover.text
        if (popover_text is not None and
                popover_text == 'You are unable to follow more people at this time.'):
            return True
        return False

    def _flist_bottom_notify_popover(self):
        locator = (By.XPATH, '//*[@id="react-root"]/div/div/div[1]/div[2]/div/div/div/div/div[1]/span | '
                             '//*[@id="react-root"]/div/div/div[1]/div[2]/div/div/div[1]/span')
        try:
            return self.driver.find_element(*locator)
        except (NoSuchElementException, StaleElementReferenceException):
            # self.log.exception("_flist_bottom_notify_popover: Got exception!")
            return None
