
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


from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from taciturn.applications.base import FollowerApplicationHandler

BUTTON_TEXT_FOLLOWING = ('Following', 'Pending', 'Cancel', 'Unfollow')
BUTTON_TEXT_NOT_FOLLOWING = ('Follow',)


class TwitterHandler(FollowerApplicationHandler):
    application_name = 'twitter'

    application_url = "https://twitter.com"
    application_login_url = "https://twitter.com/login"

    application_asset_dirname = 'twitter'
    default_profile_image = 'default_profile_reasonably_small.png'

    def __init__(self, app_account, driver=None):
        super().__init__(app_account, driver)
        self.log.info('Starting twitter app handler.')

    def login(self):
        self.goto_login_page()

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

        # use this to verify login ...
        self._home_profile_link_element()
        # refresh, because sometimes login isn't fully processed ...
        self.driver.refresh()

        self.log.info('Logged in.')

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
            self.log.info("Going to home page: {}".format(homepage_link))
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
                self.log.info("Going to page: {}".format(profile_link))
                self.driver.get(profile_link)
            else:
                user_profile_link = '{}/{}'.format(self.application_url, user_name)
                self.log.info("Going to page: {}".format(user_profile_link))
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
                self.log.info("Going to page: {}".format(user_following_link))
                self.driver.get(user_following_link)

            if self._is_stale_login_lightbox_present():
                self.driver.refresh()
                continue
            else:
                break

    def goto_followers_page(self, user_name=None):
        while True:
            if user_name is None:
                self.log.info('Going to user followers page.')
                self.goto_profile_page()
                locator = (By.XPATH, '//*[@id="react-root"]//div[2]/a/span[2]/span[text()="Followers"]')
                self.new_wait(timeout=10)\
                       .until(EC.presence_of_element_located(locator)).click()
            else:
                user_followers_link = '{}/{}/followers'.format(self.application_url, user_name)
                self.log.info('Going to page: {}'.format(user_followers_link))
                self.driver.get(user_followers_link)

            if self._is_stale_login_lightbox_present():
                self.driver.refresh()
                continue
            else:
                break

    def post_tweet(self, tweet_body, tweet_image=None):
        if len(tweet_body) <= 60:
            tweet_body_preview = tweet_body
        else:
            tweet_body_preview = tweet_body[:60]
        if tweet_image is not None:
            tweet_attachment = '[with attachment]'
        else:
            tweet_attachment = ''
        self.log.info('Posting tweet for message: "{}..." {}'
                        .format(tweet_body_preview, tweet_attachment))

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

            self.log.debug('Waiting for tweet image attachment.')
            tweet_image_attached_locator = (By.XPATH, '//div[@aria-label="Media" and @role="group"]//img')
            post_wait.until(EC.visibility_of_element_located(tweet_image_attached_locator))
            self.log.debug('Tweet image attachment verified.')

        submit_tweet_button_locator = (By.XPATH, '//div[@role="button"]//span[text()="Tweet"]')
        submit_tweet_button_element = post_wait.until(EC.presence_of_element_located(submit_tweet_button_locator))
        self.scrollto_element(submit_tweet_button_element)
        submit_tweet_button_element.click()

        # wait for the lightbox (x) to dissapear, to verify tweet sent ...
        tweet_lightbox_xbutton_locator = (By.XPATH, '//div[@aria-label="Close" and @role="button"]/div[@dir="auto"]')
        tweet_lightbox_xbutton_element = post_wait.until(EC.presence_of_element_located(tweet_lightbox_xbutton_locator))
        post_wait.until(EC.staleness_of(tweet_lightbox_xbutton_element))
        self.log.info('Tweet submitted.')

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
                    effective_tweet_length += 1

        # debug:
        self.log.debug("truncate_tweet: len(tweet_text) =", len(tweet_text))
        self.log.debug("truncate_tweet: scan_position =", scan_position)
        self.log.debug("truncate_tweet: effective_tweet_length =", effective_tweet_length)
        self.log.debug("truncate_tweet: last_scanned_space =", last_scanned_space)

        if effective_tweet_length <= tweet_limit:
            return tweet_text
        elif last_scanned_space > 0:
            # truncate at last word!
            return tweet_text[:last_scanned_space]
        else:
            raise ValueError("Couldn't truncate body string for twitter!")

    def has_unfollow_confirm(self):
        return True

    def unfollow_confirm_button(self):
        locator = (By.XPATH, '//*[@id="react-root"]//span/span[text() = "Unfollow"]')
        return self.new_wait(timeout=10).until(EC.presence_of_element_located(locator))

    # XXX NEW 0.2a flist METHODS!

    def flist_first_from_following(self):
        locator = (By.XPATH, '//section[starts-with(@aria-labelledby, "accessible-list-")]'
                             '/div[@aria-label="Timeline: Following"]/div/div/div[1]')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    def flist_first_from_followers(self):
        locator = (By.XPATH, '//section[starts-with(@aria-labelledby, "accessible-list-")]'
                             '/div[@aria-label="Timeline: Followers"]/div/div/div[1]')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    def flist_next(self, flist_entry):
        locator = (By.XPATH, './following-sibling::div[1]')
        return self.new_wait(flist_entry).until(EC.presence_of_element_located(locator))

    def flist_is_last(self, flist_entry):
        return False

    def flist_is_empty(self, flist_entry):
        # need to thoroughly check for absence of a proper entry, here we check by username ...
        username_locator = self._flist_username_locator()
        try:
            self.new_wait(flist_entry, timeout=10)\
                .until(EC.presence_of_element_located(username_locator))
            return False
        except TimeoutException as e:
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
        image_src = self.new_wait(flist_entry).until(EC.presence_of_element_located(locator)).get_attribute('src')
        return self.is_default_image(image_src)

    def flist_is_verified(self, flist_entry):
        locator = (By.XPATH, './div/div/div/div[2]/div[1]/div[1]/a/div/div[1]/div[2]/'
                             '*[local-name()="svg" and @aria-label="Verified account"]')
        try:
            self.new_wait(timeout=0).until(EC.presence_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    def flist_button(self, flist_entry):
        locator = (By.XPATH, './div/div/div/div[2]/div/div[2]/div/div/span/span')
        return self.new_wait(flist_entry).until(EC.presence_of_element_located(locator))

    def flist_button_is_following(self, flist_button_text):
        return flist_button_text in BUTTON_TEXT_FOLLOWING

    def flist_button_is_not_following(self, flist_button_text):
        return flist_button_text in BUTTON_TEXT_NOT_FOLLOWING

    def flist_button_wait_following(self, flist_button):
        self.log.debug('Waiting for entry to be in following state.')
        return self.new_wait(flist_button).until(lambda e: e.text in BUTTON_TEXT_FOLLOWING)

    def flist_button_wait_not_following(self, flist_button):
        self.log.debug('Waiting for entry to be in non-following state.')
        return self.new_wait(flist_button).until(lambda e: e.text in BUTTON_TEXT_NOT_FOLLOWING)

    def flist_header_overlap_y(self):
        header_locator = (By.XPATH, '(//div[@data-testid="primaryColumn"]/div/div)[1]')
        header_element = self.new_wait().until(EC.presence_of_element_located(header_locator))
        element_y = header_element.size['height']
        self.log.debug("flist_header_overlap_y = {}".format(element_y))
        return element_y

    def flist_is_blocked_notice(self):
        popover = self._flist_bottom_notify_popover()
        if popover is None:
            return False
        popover_text = popover.text
        if popover_text is not None \
                and popover_text == 'You have been blocked from following this user at their request.':
            # halt and wait until the blocked notice disappers, so it doesn't confuse us later:
            self.new_wait().until(EC.staleness_of(popover))
            return True
        return False

    def flist_is_follow_limit_notice(self):
        popover = self._flist_bottom_notify_popover()
        if popover is None:
            return False
        popover_text = popover.text
        if popover_text is not None \
                and popover_text == 'You are unable to follow more people at this time.':
            return True
        return False

    def _flist_bottom_notify_popover(self):
        locator = (By.XPATH, '//*[@id="react-root"]//div[@role="alert"]/div[1]/span')
        try:
            return self.new_wait(timeout=0).until(EC.presence_of_element_located(locator))
        except TimeoutException:
            return None


class TwitterHandlerWebElements():
    # //*[@id="react-root"]/div/div/div[2]/main/div/div/div/div[1]/div/div[2]/section/div/div/div/div[N]
    # /section aria-labeledby="accessible-list-0" /div aria-label="Timeline: Followers"
    _follower_entries_xpath_prefix = '//section[starts-with(@aria-labelledby, "accessible-list-")]'\
                                     '/div[@aria-label="Timeline: Followers"]/div/div/div'

    _follower_first_follower_entry = '//section[starts-with(@aria-labelledby, "accessible-list-")]/div[@aria-label="Timeline: Followers"]/div/div/div[1]'
    _following_first_follwing_entry = '//section[starts-with(@aria-labelledby, "accessible-list-")]/div[@aria-label="Timeline: Following"]/div/div/div[1]'

    implicit_default_wait = 60

    # def _follower_entry_xpath_prefix(self, n=1):
    #   return self.follower_xpath_prefix + '/div[{}]'.format(n)

    def first_following_entry(self, retries=10):
        for try_n in range(1, retries+1):
            try:
                self.driver.implicitly_wait(0)
                return self.driver.find_element(By.XPATH, self._following_first_follwing_entry)
            except (StaleElementReferenceException, NoSuchElementException) as e:
                print('first_following_entry: caught exception:', e)
                if try_n == retries:
                    raise e
                else:
                    print("first_following_entry, caught exception try {} of {}: {}".format(try_n, retries, e))
            finally:
                self.driver.implicitly_wait(self.implicit_default_wait)

    def first_follower_entry(self, retries=10):
        for try_n in range(1, retries+1):
            try:
                self.driver.implicitly_wait(0)
                return self.driver.find_element(By.XPATH, self._follower_first_follower_entry)
            except (StaleElementReferenceException, NoSuchElementException) as e:
                print('first_follower_entry: caught exception:', e)
                if try_n == retries:
                    raise e
                else:
                    print("first_follower_entry, caught exception try {} of {}: {}".format(try_n, retries, e))
            finally:
                self.driver.implicitly_wait(self.implicit_default_wait)

    def next_follower_entry(self, follower_entry):
        selector = './following-sibling::div[1]'
        # may as well allow a generous wait, 5 minutes, make sure the element is probably fully populated, too:
        WebDriverWait(follower_entry, 60*5)\
            .until(lambda e: e.find_element(By.XPATH, selector) and self.follower_username(e))
        return follower_entry.find_element(By.XPATH, selector)

    def follower_entries(self):
        return self.driver.find_elements(By.XPATH, self._follower_entries_xpath_prefix)

    def followers_endcap(self):
        # empty div at the end of a followers list:
        # //*[@id="react-root"]/div/div/div[2]/main/div/div/div/div[1]/div/div[2]/section/div/div/div/div[11]/div/div
        pass

    @staticmethod
    def follower_image(follower_entry):
        # prefix + /div/div/div/div[1]/div/a/div[1]/div[2]/div/img
        return follower_entry.find_element(
            By.XPATH, './div/div/div/div[1]/div/a/div[1]/div[2]/div/img')

    @staticmethod
    def follower_username(follower_entry, retries=10):
        # ./div/div/div/div[2]/div/div[1]/a/div/div[2]/div/span
        # Another path seen on twitter:
        # ./div/div/div/div[2]/div/div[1]/a/div/div/div[1]/span/span
        for try_n in range(1, retries+1):
            try:
                return follower_entry.find_element(
                    By.XPATH, './div/div/div/div[2]/div/div[1]/a/div/div[2]/div/span[starts-with(text(), "@")] | '
                              './div/div/div/div[2]/div/div[1]/a/div/div/div[1]/span/span[starts-with(text(), "@")]')
            except (StaleElementReferenceException, NoSuchElementException) as e:
                print('first_follower_entry: caught exception:', e)
                if try_n == retries:
                    raise e
                else:
                    print("first_follower_entry, caught exception try {} of {}: {}".format(try_n, retries, e))

    @staticmethod
    def follower_button(follower_entry):
        # prefix + /div/div/div/div[2]/div/div[2]/div/div/span/span
        return follower_entry.find_element(
            By.XPATH, './div/div/div/div[2]/div/div[2]/div/div/span/span')

    def follower_is_verified(self, follower_entry):
        # prefix + /div/div/div/div[2]/div[1]/div[1]/a/div/div[1]/div[2]/svg
        # <svg aria-label="Verified account" ...> </svg>
        # //*[local-name() = 'svg']  -- needed for svg in xpath
        try:
            self.driver.implicitly_wait(0)
            WebDriverWait(follower_entry, 0.5, poll_frequency=1).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    './div/div/div/div[2]/div[1]/div[1]/a/div/div[1]/div[2]/'
                    '*[local-name() = "svg" and @aria-label="Verified account"]'
                )))
            return True
        except NoSuchElementException:
            return False
        finally:
            self.driver.implicitly_wait(self.implicit_default_wait)

    def follower_follows_me(self, follower_entry):
        # //*[@id="react-root"]/div/div/div[2]/main/div/div/div/div[1]/div/div[2]/section/div/div/div/div[12]/div/div/div/div[2]/div[1]/div[1]/a/div/div[2]/div[2]/span
        try:
            self.driver.implicitly_wait(0)
            follower_entry.find_element(
                By.XPATH,
                './div/div/div/div[2]/div[1]/div[1]/a/div/div[2]/div[2]/span[text() = "Follows you"]'
            )
            return True
        except NoSuchElementException:
            return False
        finally:
            self.driver.implicitly_wait(self.implicit_default_wait)

    def login_username_input(self):
        # //*[@id="react-root"]/div/div/div[2]/main/div/div/div/div[2]/div/div[2]/div/div/div/div[1]/section/form/div/div[1]/div/label/div/div[2]/div/input
        # form action="/sessions"
        # xpath=//input[@name="session[username_or_email]"]
        return self.driver.find_element(
            By.XPATH,
            '//div[@aria-hidden="false"]//form[@action="/sessions"]//input[@name="session[username_or_email]"]')

    def login_password_input(self):
        # form action="/sessions"
        # xpath = // input[@name="session[password]"]
        # //div[@aria-hidden="false"]
        # //form[@action="/sessions"]//input[@name="session[password]"]
        return self.driver.find_element(
            By.XPATH, '//div[@aria-hidden="false"]//form[@action="/sessions"]//input[@name="session[password]"]')

    def login_button(self):
        # //*[@id="react-root"]/div/div/div[2]/main/div/div/div/div[2]/div/div[2]/div/div/div/div[1]/section/form/div/div[3]/div/div/span/span
        # //div[@role="button"]/div/span/span[contains(.,'Log in')]
        return self.driver.find_element(
            By.XPATH, '//div[@aria-hidden="false"]//form[@action="/sessions"]//span/span[contains(.,"Log in")]')

    def home_profile_link(self):
        # //*[@id="react-root"]/div/div/div[2]/header/div/div/div/div[1]/div[2]/nav/a[7]
        # nav aria-label="Primary"
        # a aria-label="Profile"
        return self.driver.find_element(
            By.XPATH, '//nav[@aria-label="Primary"]/a[@aria-label="Profile"]')

    def followers_tab_link(self):
        # //*[@id="react-root"]/div/div/div[2]/main/div/div/div/div[1]/div/div[1]/div[2]/nav/div[2]/div[2]/a/div/span
        # nav[@role="navigation"]
        # span[contains(.,"Followers")]
        # XXX there's a non-visible element on the page that we need to skip, hence the (...)[2]
        return self.driver.find_element(
            By.XPATH,
            '(//nav[@role="navigation"]//a[@role="tab" and @aria-selected="true"]'
            '/div/span[text() = "Followers"])[2]')

    def followers_tab_overlap(self, retries=10):
        # get the y dimension of the overlapping tab, because it will obscure clicks!
        # //*[@id="react-root"]/div/div/div[2]/main/div/div/div/div[N]/div/div
        # //div[@data-testid="primaryColumn"]/div/div
        for try_n in range(1, retries+1):
            try:
                tab_element = self.driver.find_element(
                    By.XPATH,
                    '(//div[@data-testid="primaryColumn"]/div/div)[1]'
                )
                return tab_element.size['height']
            except (StaleElementReferenceException, NoSuchElementException) as e:
                print('next_follower_entry: caught exception:', e)
                if try_n == retries:
                    raise e
                else:
                    print("next_follower_entry, caught exception try {} of {}: {}".format(try_n, retries, e))

    def follow_click_verify_cb(self, follower_entry):
        def follow_click_verify(x):
            print("follow_click_verify_cb: rescanning button text.")
            b = self.follower_button(follower_entry)
            t = b.text
            print("follow_click_verify_cb: button text =", t)
            r = t in BUTTON_TEXT_FOLLOWING
            print("follow_click_verify, text: ", t)
            print("follow_click_verify, result: ", r)
            return r
        return follow_click_verify

    def bottom_notify_popover_text(self):
        # grab the text from the popover that sometimes appears at the bottom!
        # need to be quick because it shows up in the dom for only a few seconds.
        # Seems best to just grab the text!?
        # //*[@id="react-root"]/div/div/div[1]/div[2]/div/div/div[1]/span
        # notification strings, verbatim:
        #  'You are unable to follow more people at this time.'
        try:
            self.driver.implicitly_wait(0)
            return self.driver.find_element(
                By.XPATH,
                '//*[@id="react-root"]/div/div/div[1]/div[2]/div/div/div[1]/span'
            ).text
        except NoSuchElementException:
            # print("bottom_notify_popover_text: NoSuchElementException")
            return None
        finally:
            self.driver.implicitly_wait(self.implicit_default_wait)

    def is_follower_limit_notify_present(self):
        text = self.bottom_notify_popover_text()
        if text is not None and text == 'You are unable to follow more people at this time.':
            return True
        return False

    def is_follower_blocked_notify_present(self):
        text = self.bottom_notify_popover_text()
        if text is not None and text == 'You have been blocked from following this user at their request.':
            return True
        return False

    def blocked_notice_gone_cb(self):
        def check_block_notice(x):
            try:
                self.driver.implicitly_wait(0)
                text = self.bottom_notify_popover_text()
                if text is not None and text == 'You have been blocked from following this user at their request.':
                    return False
            except NoSuchElementException:
                return True
            finally:
                self.driver.implicitly_wait(self.implicit_default_wait)
            return True
        return check_block_notice

    # Scan for account restrictions:
    def account_restricted(self):
        # we get redirected to: https://twitter.com/account/access

        # header text:
        # /html/body/div[2]/div/div[1]
        # <div class="PageContainer">/<div class="Section">/<div class="PageHeader Edge">
        #    'We've temporarily limited some of your account features.'

        # description text:
        # /html/body/div[2]/div/div[3]/div[2]
        # <div class="PageContainer">/<div class="Section">/<div class="TextGroup">/<div class="TextGroup-text">
        # Your account appears to be in violation of Twitter's <a href="https://help.twitter.com/using-twitter/twitter-follow-limit" target="_blank">following policy</a>. Your ability to follow, like, and Retweet will be limited for the following period of time:
        # </div>
        # restricted words: follow, like, and Retweet

        # duration text:
        # /html/body/div[2]/div/div[4]/div
        # <div class="PageContainer">/<div class="Section">/<div class="TextGroup TimeRemaining">/<div class="TextGroup-header">
        # '3 days and 0 hours.'
        pass

    def is_loading_followers_progressbar_present(self):
        # <div aria-valuemax="1" aria-valuemin="0" aria-label="Loading Followers" role="progressbar" class="css-1dbjc4n r-1awozwy r-1777fci">
        #    <div class="css-1dbjc4n r-17bb2tj r-1muvv40 r-127358a r-1ldzwu0" style="height: 26px; width: 26px;">
        #       <svg height="100%" viewBox="0 0 32 32" width="100%">
        #          <circle cx="16" cy="16" fill="none" r="14" stroke-width="4" style="stroke: rgb(23, 191, 99); opacity: 0.2;"></circle>
        #          <circle cx="16" cy="16" fill="none" r="14" stroke-width="4" style="stroke: rgb(23, 191, 99); stroke-dasharray: 80; stroke-dashoffset: 60;"></circle>
        #       </svg>
        #    </div>
        # </div>
        try:
            self.driver.implicitly_wait(0)
            return self.driver.find_element(
                By.XPATH,
                '//div[@aria-label="Loading Followers" and @role="progressbar"]/div/*[local-name() = "svg"]'
            ).text
        except NoSuchElementException:
            # print("bottom_notify_popover_text: NoSuchElementException")
            return None
        finally:
            self.driver.implicitly_wait(self.implicit_default_wait)

    def is_followers_end(self, follower_entry, retries=10):
        def dump_debug_html():
            with open('is_followers_end.html', 'w') as fh:
                fh.write(follower_entry.get_attribute('innerHTML'))

        for try_n in range(1, retries+1):

            # first, try to read a non-empty node:
            try:
                self.driver.implicitly_wait(10)
                dump_debug_html()
                # use follower_username to detect a non-empty element:
                self.follower_username(follower_entry)
                print("is_followers_end (non-empty): False")
                return False
            except (NoSuchElementException, StaleElementReferenceException, TimeoutException) as e:
                # print('is_followers_end: caught exception:', e)
                if try_n == retries:
                    dump_debug_html()
                    print("is_followers_end (non-empty): False")
                    return False
            finally:
                 self.driver.implicitly_wait(self.implicit_default_wait)

            # then, try to read an empty node:
            try:
                self.driver.implicitly_wait(30)
                el = follower_entry.find_element(By.XPATH, './div/div[not(node())]')
                dump_debug_html()
                print("is_followers_end (is-empty): True")
                return True
            except (NoSuchElementException, StaleElementReferenceException, TimeoutException) as e:
                # print('is_followers_end: caught exception:', e)
                if try_n == retries:
                    dump_debug_html()
                    print("is_followers_end (is-empty): False")
                    return False
            finally:
                 self.driver.implicitly_wait(self.implicit_default_wait)
        dump_debug_html()
        print("is_followers_end (out): False")
        return False

    # def verify_unfollow_lightbox(self):
    #     # //*[@id="react-root"]/div/div/div[1]/div[2]/div/div/div/div[2]/div[2]/div[1]/span
    #     e = self.driver.find_element(
    #             By.XPATH,
    #             '//*[@id="react-root"]/div/div/div[1]/div[2]/div/div/div/div[2]'
    #             '/div[2]/div[1]/span[starts-with(text(), "Unfollow")]')
    #     return

    def unfollow_lightbox_button(self):
        return self.driver.find_element(
            By.XPATH,
            '//*[@id="react-root"]/div/div/div[1]/div[2]/div/div'
            '/div/div[2]/div[2]/div[3]/div[2]/div/span/span[text() = "Unfollow"]')
