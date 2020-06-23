
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from sqlalchemy import and_

from time import sleep
from datetime import datetime

from taciturn.applications.base import sleepmsrange

from taciturn.applications.base import (
    FollowerApplicationHandler,
    ApplicationWebElements,
    AppDataAnchorMissingException,
    AppUnexpectedStateException,
    AppLoginException,
    AppWebElementException,
    AppActivityLimitException)

from taciturn.db.followers import (
    Follower,
    Following,
    Unfollowed
)


class TwitterHandler(FollowerApplicationHandler):
    application_name = 'twitter'

    application_url = "https://twitter.com"
    application_login_url = "https://twitter.com/login"

    application_asset_dirname = 'twitter'
    default_profile_image = 'default_profile_reasonably_small.png'

    follow_random_wait = (10, 60)

    def __init__(self, db_session, app_username, app_password, elements=None):
        super().__init__(db_session, app_username, app_password, TwitterHandlerWebElements)
        self.goto_homepage()

        self.follow_back_hiatus = self.config['app:twitter']['follow_back_hiatus']
        self.unfollow_hiatus = self.config['app:twitter']['unfollow_hiatus']
        self.action_timeout = self.config['app:twitter']['action_timeout']

    def goto_homepage(self):
        self.driver.get(self.application_url + '/home')

    def goto_user_page(self):
        self.driver.get("{}/{}/".format(self.application_url, self.app_username))

    def login(self):
        # enter username and password:
        self.driver.get(self.application_login_url)

        self.e.login_username_input().send_keys(self.app_username)
        self.e.login_password_input().send_keys(self.app_password)
        self.e.login_button().click()

        profile_link = self.e.home_profile_link().get_attribute('href')
        profile_link_expected = self.application_url + '/' + self.app_username
        if profile_link != profile_link_expected:
            raise AppLoginException("Couldn't verify login profile link, href '{}' doesn't match '{}'"
                                    .format(profile_link, profile_link_expected))

        print("Logged in to twitter ok!")

    def start_following(self, target_account, quota=None):
        # for a bit of misdirection ;)
        self.goto_homepage()
        sleep(2)
        self.goto_user_page()
        sleep(2)
        self.driver.get("{}/{}".format(self.application_url, target_account))
        sleep(2)

        # ... then get the page we want:
        self.driver.get("{}/{}/followers".format(self.application_url, target_account))

        self.e.followers_tab_link()
        tab_overlap_y = self.e.followers_tab_overlap()

        max_scan_count = 10
        followed_count = 0

        last_username = None
        while quota is None or followed_count < quota:

            # scan, and re-scan for follower entries:
            follower_entries = self.e.follower_entries()
            follower_entry_n = 0

            # skip ahead to next entry:
            if last_username:
                # skip ahead to next entry to be scanned:
                def scan_for_next_entry(fe, name):
                    for n in range(len(fe)):
                        f = fe[n]
                        if self.e.follower_username(f).text == name:
                            if n + 1 <= len(fe):
                                return fe[n + 1], n + 1
                            elif n + 1 > len(fe):
                                return None, 0

                follower_entry, follower_entry_n = scan_for_next_entry(follower_entries, last_username)
                if follower_entry is None:
                    if self.e.is_loading_followers_progressbar_present():
                        print("Followers loading is present, waiting and continuing.")
                        sleep(3)
                        continue
                    if self.e.is_followers_end_present():
                        print("Followers end is present, returning.")
                        return followed_count
                else:
                    raise AppDataAnchorMissingException(
                        "Last entry for '{}' not found in entry scan!".format(last_username))

            # process entries:
            while follower_entry_n < len(follower_entries):
                # get element and scroll to it:
                follower_entry = follower_entries[follower_entry_n]
                self.scrollto_element(follower_entry, offset=tab_overlap_y)

                # extract entry fields, continue'ing asap to avoid unnecessary scanning:
                entry_button = self.e.follower_button(follower_entry)
                # already following, skip:
                if entry_button.text in ('Following', 'Pending'):
                    # XXX cross reference with database here?
                    follower_entry_n += 1
                    continue
                # default image, skip:
                entry_image_src = self.e.follower_image(follower_entry).get_attribute('src')
                if self.is_default_image(entry_image_src):
                    follower_entry_n += 1
                    continue

                entry_username = self.e.follower_username(follower_entry).text
                entry_button_text = entry_button.text

                # try to follow:
                if entry_button_text == 'Follow':
                    # check to see if we're already (supposed to be following) this user:
                    already_following = self.session.query(Following)\
                                            .filter(and_(Following.name == entry_username,
                                                         Following.user_id == self.db_user.id,
                                                         Following.application_id == self.db_app.id)).one_or_none()
                    # if we find a record, it's contradicting what twitter is telling us, so delete it:
                    if already_following:
                        print("Warning: user '{}' already recorded as following?"
                              "  Deleting stale record.".format(entry_username))
                        self.session.delete(already_following)

                    # check to see if we've recently unfollowed this user:
                    already_unfollowed = self.session.query(Unfollowed)\
                                            .filter(and_(Unfollowed.user_id == self.db_user.id,
                                                         Unfollowed.application_id == self.db_app.id,
                                                         Unfollowed.name == entry_username)).one_or_none()
                    # then check if unfollow was recent:
                    if already_unfollowed is not None and \
                            datetime.now() < already_unfollowed.established + self.unfollow_hiatus:
                        print("Already followed and unfollowed this user '{}', "
                              "will follow again after {}".format(entry_username,
                                    already_unfollowed.established + self.unfollow_hiatus))
                        continue

                    print("Clicking 'Follow' button ...")

                    entry_button.click()
                    sleep(1)

                    if self.e.is_follower_limit_notify_present():
                        print("Unable to follow more at this time!")
                        return followed_count

                    WebDriverWait(self.driver, timeout=60).until(self.e.follow_click_verify_cb(entry_button))
                    print("Follow verified.")

                    new_following = Following(name=entry_username,
                                              application_id=self.db_app.id,
                                              user_id=self.db_user.id,
                                              established=datetime.now())

                    self.session.add(new_following)
                    if already_following is not None:
                        self.session.delete(already_unfollowed)
                    self.session.commit()
                    print("Follow added to database.")

                    sleepmsrange(self.action_timeout)

                    followed_count += 1

                elif entry_button_text in ('Following', 'Pending'):
                    # do nothing!
                    pass
                else:
                    raise AppUnexpectedStateException(
                        "Entry button for '{}' says '{}'?".format(entry_username, entry_button.text))

                follower_entry_n += 1

            # give the list scrolling a chance to catch up:
            sleepmsrange(self.action_timeout)

        return followed_count


    def old_start_following(self, target_account, quota=None):
        self.driver.get("{}/{}/followers".format(self.application_url, target_account))

        # verify "Followers" tab present ...
        self.e.followers_tab_link()
        # scan the overlapping tab y-dimension ...
        tab_overlap_y = self.e.followers_tab_overlap()

        # start the account following loop ...
        last_follower_n = 1
        while True:
            # debug sleep:
            sleep(5)

            # # because skipping can cause scrolling to go too fast, we periodically do a catch up:
            # if last_follower_n % 40 == 0:
            #     print("Scroll wait!")
            #     sleep(3)
            #     WebDriverWait(self.driver, timeout=60).until(
            #         lambda x: self.e.follower_entry(last_follower_n))

            # check the follower entry count:
            print("follower entry count: ", self.e.count_follower_entries())

            # scan follower element:
            for n in range(1, self.default_load_retries):
                try:
                    follower_entry_element = self.e.follower_entry(last_follower_n)
                    self.scrollto_element(follower_entry_element, offset=tab_overlap_y)
                    break
                except NoSuchElementException as e:
                    print("start_following, find_element(follower_entry): NoSuchElementException")
                    continue
            else:
                if follower_entry_element is None:
                    raise AppWebElementException(
                        "start_following, find_element(follower_entry): Couldn't scan after {} tries.".format(n))

            # scan follower username:
            follower_username = self.e.follower_username(last_follower_n).text.lstrip('@')

            # check if we can quickly skip this entry:
            follower_button = self.e.follower_button(last_follower_n)
            if follower_button.text in ('Following', 'Pending'):
                print("Skipping {} [{}] state '{}' ...".format(follower_username, last_follower_n, follower_button.text))
                last_follower_n += 1
                continue

            follower_image = self.e.follower_image(last_follower_n).get_attribute('src')
            is_default_image = self.is_default_image(follower_image)
            if is_default_image:
                print("Skipping {} [{}] default image ...".format(follower_username, last_follower_n))
                last_follower_n += 1
                continue

            print("Follower image: ", follower_image)
            print("Follower username: ", follower_username)
            print("Follower button: ", follower_button.text)
            print("Is follower verified?", self.e.follower_is_verified(last_follower_n))
            print("Is image default?", is_default_image)

            # try to click follow:
            if follower_button.text == 'Follow':
                # when we commit to clicking, we want to make sure the entry is fully loaded ?
                # WebDriverWait(self.driver, timeout=60).until(
                #     lambda x: self.e.follower_entry(last_follower_n))

                print("Clicking Follow ...")
                follower_button.click()
                # quickly check for limit popover ...
                if self.e.is_follower_limit_notify_present():
                    raise TwitterFollowLimitException("Follow limit reached!")
                # then ... wait and verify that button text changes to 'Following' or 'Requested' ...
                WebDriverWait(self.driver, timeout=60).until(self.e.follow_click_verify_cb(last_follower_n))
                print("Follow verified.")

                # XXX next, add follower entry to database with 'followed timestamp' = now
                # make note if response was 'followed' or 'pending'


            print('-'*72)

            # finally, increment the follower position:
            last_follower_n += 1

    def update_followers(self):
        self.driver.get("{}/{}/followers".format(self.application_url, self.app_username))

        # verify "Followers" tab present ...
        self.e.followers_tab_link()
        # scan the overlapping tab y-dimension ...
        tab_overlap_y = self.e.followers_tab_overlap()

        # start the account follower scan loop ...
        last_follower_n = 1
        while True:
            # scan follower element:
            for n in range(1, self.default_load_retries):
                try:
                    follower_entry_element = self.e.follower_entry(last_follower_n)
                    self.scrollto_element(follower_entry_element, offset=tab_overlap_y)
                except NoSuchElementException as e:
                    print("start_following, find_element(follower_entry): NoSuchElementException")
                    continue
            else:
                if follower_entry_element is None:
                    raise AppWebElementException(
                        "start_following, find_element(follower_entry): Couldn't scan after {} tries.".format(n))

            follower_username = self.e.follower_username(last_follower_n).text.lstrip('@')
            follower_button = self.e.follower_button(last_follower_n)

            # XXX next, check db for follower, add if not present with 'first scan timestamp' = now ...
            # Strictly speaking this is not necessary, because the ui tells you what followers
            # are mutual, but still it's a nice exercise to do it ourselves, too, because we can
            # and maybe we should, to be more self-reliant?

    def start_unfollow(self, quota=None):
        pass


class TwitterHandlerWebElements(ApplicationWebElements):
    # //*[@id="react-root"]/div/div/div[2]/main/div/div/div/div[1]/div/div[2]/section/div/div/div/div[N]
    # /section aria-labeledby="accessible-list-0" /div aria-label="Timeline: Followers"
    _follower_entries_xpath_prefix = '//section[starts-with(@aria-labelledby, "accessible-list-")]'\
                                     '/div[@aria-label="Timeline: Followers"]/div/div'

    # def _follower_entry_xpath_prefix(self, n=1):
    #   return self.follower_xpath_prefix + '/div[{}]'.format(n)

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
            By.XPATH, './/div/div/div/div[1]/div/a/div[1]/div[2]/div/img')

    @staticmethod
    def follower_username(follower_entry):
        # prefix + /div/div/div/div[2]/div/div[1]/a/div/div[2]/div/span
        return follower_entry.find_element(
            By.XPATH, './/div/div/div/div[2]/div/div[1]/a/div/div[2]/div/span')

    @staticmethod
    def follower_button(follower_entry):
        # prefix + /div/div/div/div[2]/div/div[2]/div/div/span/span
        return follower_entry.find_element(
            By.XPATH, './/div/div/div/div[2]/div/div[2]/div/div/span/span')

    def follower_is_verified(self, follower_entry):
        # prefix + /div/div/div/div[2]/div[1]/div[1]/a/div/div[1]/div[2]/svg
        # <svg aria-label="Verified account" ...> </svg>
        # //*[local-name() = 'svg']  -- needed for svg in xpath
        try:
            self.driver.implicitly_wait(0)
            WebDriverWait(follower_entry, 0.5, poll_frequency=1).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    './/div/div/div/div[2]/div[1]/div[1]/a/div/div[1]/div[2]/'
                    '*[local-name() = "svg" and @aria-label="Verified account"]'
                )))
        except NoSuchElementException:
            return False
        finally:
            self.driver.implicitly_wait(self.implicit_default_wait)
        return True

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

    def followers_tab_overlap(self):
        # get the y dimension of the overlapping tab, because it will obscure clicks!
        # //*[@id="react-root"]/div/div/div[2]/main/div/div/div/div[N]/div/div
        # //div[@data-testid="primaryColumn"]/div/div
        tab_element = self.driver.find_element(
            By.XPATH,
            '(//div[@data-testid="primaryColumn"]/div/div)[1]'
        )
        return tab_element.size['height']

    @staticmethod
    def follow_click_verify_cb(follow_button):
        def follow_click_verify(x):
            t = follow_button.text
            r = t in ('Following', 'Pending')
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
            print("bottom_notify_popover_text: NoSuchElementException")
            return None
        finally:
            self.driver.implicitly_wait(self.implicit_default_wait)

    def is_follower_limit_notify_present(self):
        text = self.bottom_notify_popover_text()
        if text is not None and text == 'You are unable to follow more people at this time.':
            return True
        return False

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
            print("bottom_notify_popover_text: NoSuchElementException")
            return None
        finally:
            self.driver.implicitly_wait(self.implicit_default_wait)

    def is_followers_end_present(self):
        try:
            self.driver.implicitly_wait(0)
            return self.driver.find_element(
                By.XPATH,
                self._follower_entries_xpath_prefix + '[last()]/div/div[not(text())]'
            ).text
        except NoSuchElementException:
            print("bottom_notify_popover_text: NoSuchElementException")
            return None
        finally:
            self.driver.implicitly_wait(self.implicit_default_wait)

# twitter specific exceptions:

class TwitterFollowLimitException(AppActivityLimitException):
    pass