
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

from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException
)

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from sqlalchemy import and_

from taciturn.applications.base import AppUnexpectedStateException
from taciturn.applications.follower import FollowerApplicationHandler

from taciturn.db.followers import (
    Follower,
    Following,
    Unfollowed
)

from taciturn.db.base import (
    User,
    Application,
)

from time import sleep
from datetime import datetime


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

    def __init__(self, app_account, driver=None):
        super().__init__(app_account, driver)
        self.log.info('Starting instagram app handler.')

    def login(self):
        login_optional_wait_args = dict(ignored_exceptions=[StaleElementReferenceException, TimeoutException],
                                        timeout=5)
        login_optional_wait = self.new_wait(**login_optional_wait_args)

        self.driver.get(self.application_login_url)

        # possible occurrence:  an initial login button is sometimes present:
        try:
            locator = (By.XPATH, '//*[@id="react-root"]/section/main/article//div[2]/button')
            exceptions = [StaleElementReferenceException, TimeoutException]
            first_login_button = login_optional_wait.until(EC.presence_of_element_located(locator))
            first_login_button.click()
        except TimeoutException:
            pass

        # enter username and password:
        login_form_locator = (By.XPATH, '//form')
        login_name_field_locator = (By.NAME, 'username')
        login_password_field_locator = (By.NAME, 'password')
        login_button_locator = (By.XPATH, '//button/div')

        login_form_wait = self.new_wait(timeout=10)

        login_form_wait.until(EC.presence_of_element_located(login_form_locator))
        login_form_wait.until(EC.presence_of_element_located(login_name_field_locator))\
                                    .send_keys(self.app_username)
        login_form_wait.until(EC.presence_of_element_located(login_password_field_locator))\
                                    .send_keys(self.app_password)
        login_form_wait.until(EC.presence_of_element_located(login_button_locator))\
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
            self.log.warning("Sending security code to {}, check for message.".format(security_code_phone))
            login_optional_wait.until(EC.presence_of_element_located(security_code_send_button_locator))\
                                            .click()
            while True:
                security_code = input("Enter 6-digit security code: ")
                login_optional_wait.until(EC.presence_of_element_located(security_code_input_locator))\
                    .send_keys(security_code)
                login_optional_wait.until(EC.presence_of_element_located(security_code_submit_button_locator))\
                    .click()
                # check for input failure:
                try:
                    login_optional_wait.until(EC.presence_of_element_located(security_code_incorrect_locator))
                    self.log.warning("Code not accepted, try again.")
                    login_optional_wait.until(EC.presence_of_element_located(security_code_input_locator)) \
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
            not_now_link = login_optional_wait.until(EC.presence_of_element_located(locator))
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
                login_optional_wait.until(EC.presence_of_element_located(hs_cancel_button_locator))\
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
            dialog_wait.until(EC.presence_of_element_located(notify_button_locator))\
                                    .click()
        except TimeoutException:
            self.log.debug("No notification dialog, skipping.")

        # verify login:
        self._header_logo_image()

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
            self.new_wait().until(EC.presence_of_element_located(profile_link_locator))\
                                        .click()

    def goto_following_page(self, user_name=None):
        self.goto_profile_page(user_name)

        followers_link_locator = (By.XPATH, '//a[contains(.," following")]')
        self.new_wait().until(EC.presence_of_element_located(followers_link_locator))\
                                    .click()

    def goto_followers_page(self, user_name=None):
        self.goto_profile_page(user_name)

        followers_link_locator = (By.XPATH, '//a[contains(.," followers")]')
        self.new_wait().until(EC.presence_of_element_located(followers_link_locator))\
                                    .click()

    def has_unfollow_confirm(self):
        return True

    def unfollow_confirm_button(self):
        locator = (By.XPATH, self._flist_lighbox_prefix + '//button[contains(.,"Unfollow")]')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    # flist methods:

    def flist_current_locator(self):
        locator = By.XPATH, self.flist_prefix_xpath.format(self.flist_get_position())
        self.log.debug("flist_current_locator: {}".format(locator))
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
                                               flist_entry=flist_entry)

    def flist_button_text(self, flist_entry):
        locator = self._flist_button_locator()
        return self.flist_wait_find_at_current(locator=locator,
                                               flist_entry=flist_entry,
                                               text=True)

    def flist_header_overlap_y(self):
        locator = (By.XPATH, self._flist_lighbox_prefix + '/div/div[2]')
        element = self.new_wait().until(EC.presence_of_element_located(locator))
        offset_script = """
        var rect = arguments[0].getBoundingClientRect();
        return rect.top;
        """
        interior_top = self.driver.execute_script(offset_script, element)
        return int(interior_top)

    def flist_is_blocked_notice(self):
        return False

    def flist_is_action_limit_notice(self):
        locator = (By.XPATH, '/html/body/div[5]/div/div/div/div[1]/h3[text()="Try Again Later"]')
        try:
            self.new_wait(timeout=0).until(EC.presence_of_element_located(locator))
            return True
        except TimeoutException:
            return False





    # old methods:

    def old_start_following(self, target_account, quota=None, unfollow_hiatus=None):
        self.driver.get("{}/{}".format(self.application_url, target_account))
        sleep(5)

        self.e.followers_link().click()

        followers_list_offset = self.e.followers_lightbox_interior_top()
        unfollow_hiatus = unfollow_hiatus or self.unfollow_hiatus
        followed_count = 0
        follower_entry_n = 1

        # give the followers tab a very good chance to load ...
        for try_n in range(1, self.default_load_retries + 1):
            try:
                first_follower_entry = self.e.first_follower_entry(follower_entry_n)
                self.e.follower_username(first_follower_entry)
                break
            except (StaleElementReferenceException, TimeoutException, NoSuchElementException) as e:
                print("first_follower_entry, try {} of {}, raised exception: {}" \
                      .format(try_n, self.default_load_retries, e))
                if try_n >= self.default_load_retries:
                    raise e

        entry_button_text = None
        follower_entry = None
        entry_username = None

        while quota is None or followed_count < quota:

            for try_n in range(1, self.default_load_retries + 1):
                try:
                    follower_entry = self.e.follower_entry_n(follower_entry_n)
                    # follower_entry = self.e.follower_entry_n(follower_entry_n)
                    self.scrollto_element(follower_entry, offset=followers_list_offset)
                    entry_username = self.e.follower_username(follower_entry).text

                    entry_button = self.e.follower_button(follower_entry)
                    entry_button_text = entry_button.text
                    break
                except (StaleElementReferenceException, TimeoutException) as e:
                    print("first_follower_entry, try {} of {}, raised exception: {}" \
                          .format(try_n, self.default_load_retries, e))
                    if try_n >= self.default_load_retries:
                        raise e

            print("start_following: entry_username =", entry_username)
            print("start_following: entry_button_text =", entry_button_text)

            entry_image_src = self.e.follower_image(follower_entry).get_attribute('src')

            # sleep(0.1)

            # already following, skip:
            if entry_button_text in BUTTON_TEXT_FOLLOWING:
                print("start_following: already following, skip ...")
                # XXX cross reference with database here?
                if self.e.is_followers_end(follower_entry_n):
                    print("End of list encountered, returning. A")
                    return followed_count
                follower_entry_n += 1
                # follower_entry = self.e.follower_entry_n(follower_entry)
                continue

            entry_is_default_image = self.is_default_image(entry_image_src)
            if entry_is_default_image:
                print("start_following: image is default, skip ...")
                if self.e.is_followers_end(follower_entry_n):
                    print("End of list encountered, returning. A")
                    return followed_count
                follower_entry_n += 1
                # follower_entry = self.e.follower_entry_n(follower_entry)
                continue

            print("start_following: entry_button_text default? ", entry_is_default_image)

            # prepare to follow ...

            # first, check if we recently unfollowed this user ...

            unfollowed = self.session.query(Unfollowed).filter(
                                            and_(Unfollowed.name == entry_username,
                                                 Unfollowed.user_id == self.app_account.user_id,
                                                 Unfollowed.application_id == Application.id,
                                                 Application.name == self.application_name))\
                                            .one_or_none()
            if unfollowed is not None and datetime.now() < unfollowed.established + unfollow_hiatus:
                time_remaining = (unfollowed.established + unfollow_hiatus) - datetime.now()
                print("Followed/unfollowed too recently, can follow again after", time_remaining)
                # follower_entry = self.e.follower_entry_n(follower_entry_n)
                if self.e.is_followers_end(follower_entry_n):
                    print("End of list encountered, returning. A")
                    return followed_count
                follower_entry_n += 1
                continue

            # XXX if we've been blocked, most likely they won't even
            # show up in following lists for us to click on?

            # if user is in blacklist ...

            if self.in_blacklist(entry_username):
                print("{} is in blacklist, skip ...")
                # follower_entry = self.e.follower_entry_n(follower_entry_n)
                if self.e.is_followers_end(follower_entry_n):
                    print("End of list encountered, returning. A")
                    return followed_count
                follower_entry_n += 1
                continue

            # check if follow button is in a 'follow me' sort of state:

            if entry_button_text in BUTTON_TEXT_NOT_FOLLOWING:

                # ok, getting ready to click 'Follow' ...

                # check if we already have a following entry in the database,
                # delete it as it must be wrong ...

                already_following = self.session.query(Following) \
                    .filter(and_(Following.name == entry_username,
                                 Following.user_id == self.app_account.user_id,
                                 Following.application_id == self.app_account.application_id)) \
                    .one_or_none()
                # if we find a record, it's contradicting what twitter is telling us, so delete it:
                # XXX this probably means a locked account has refused our request, and we should
                # add it to unfollowed for a long timeout ...
                if already_following is not None and unfollowed is None:
                    print("Warning: user '{}' already recorded as following?"
                          "  Moving record to unfollowed.".format(entry_username))
                    new_unfollowed = Unfollowed(name=already_following.name,
                                                established=datetime.now(),
                                                user_id=already_following.user_id,
                                                application_id=already_following.application_id)
                    self.session.add(new_unfollowed)
                    self.session.delete(already_following)
                    self.session.commit()
                    if self.e.is_followers_end(follower_entry_n):
                        print("End of list encountered, returning. A")
                        return followed_count
                    follower_entry_n += 1
                    continue

                print("Clicking 'Follow' button ...")
                for try_n in range(1, self.default_load_retries + 1):
                    try:
                        entry_button.click()
                        break
                    except (StaleElementReferenceException, TimeoutException) as e:
                        print("first_follower_entry, try {} of {}, raised exception: {}" \
                              .format(try_n, self.default_load_retries, e))
                        if try_n >= self.default_load_retries:
                            raise e

                # now, if instagram is limiting our follows, the button will revert back to 'Follow' after a few
                # seconds ...

                try:
                    WebDriverWait(entry_button, 30).until(
                        lambda e: e.text in BUTTON_TEXT_FOLLOWING)
                except TimeoutException:
                    print("Not able to follow '{}', looks like following has been suspended.".format(entry_username))
                    return followed_count

                new_following = Following(name=entry_username,
                                          application_id=self.app_account.application_id,
                                          user_id=self.app_account.user_id,
                                          established=datetime.now())

                # if there was an unfollowed entry, remove it now:
                if unfollowed is not None:
                    self.session.delete(unfollowed)

                self.session.add(new_following)
                self.session.commit()
                print("Follow added to database.")

                followed_count += 1

                if self.e.is_followers_end(follower_entry_n):
                    print("End of list encountered, returning. A")
                    return followed_count
                
                follower_entry_n += 1
                # sleep(5)
                self.sleepmsrange(self.action_timeout)

        return followed_count

    def old_update_followers(self):
        self.goto_user_page()

        self.e.followers_link().click()

        followers_list_offset = self.e.followers_lightbox_interior_top()
        entries_added = 0
        follower_entry_n = 1

        # give the followers tab a very good chance to load ...
        first_follower_entry = self.e.follower_entry_n(follower_entry_n)
        WebDriverWait(first_follower_entry, 60*3).until(lambda e: self.e.follower_username(e))

        while True:
            # follower_entry = self.e.follower_entry_n(follower_entry_n)
            try:
                follower_entry = WebDriverWait(self.driver, 60*3)\
                    .until(lambda x: self.e.follower_entry_n(follower_entry_n))
                # follower_entry = self.e.follower_entry_n(follower_entry_n)
                self.scrollto_element(follower_entry, offset=followers_list_offset)
                entry_username = self.e.follower_username(follower_entry).text
                print("update_followers: entry_username =", entry_username)

                entry_button = self.e.follower_button(follower_entry)
                entry_button_text = entry_button.text
            except (StaleElementReferenceException, NoSuchElementException, TimeoutException) as e:
                print("Retrying self.e.follower_entry_n(follower_entry_n), got: {}".format(e))
                sleep(1)
                # follower_entry = self.e.follower_entry_n(follower_entry_n)
                continue

            # check to see if entry is in the database:
            self.scrollto_element(follower_entry)
            follower_username = self.e.follower_username(follower_entry).text
            print("Scanning {} ...".format(follower_username))

            following_db = self.session.query(Follower)\
                                    .filter(and_(Follower.user_id == self.app_account.user_id,
                                                 Follower.application_id == self.app_account.application_id,
                                                 Follower.name == follower_username
                                            )).one_or_none()

            if following_db is None:
                print("No entry for '{}', creating.".format(follower_username))
                new_follower = Follower(name=follower_username,
                                        established=datetime.now(),
                                        application_id=self.app_account.application_id,
                                        user_id=self.app_account.user_id)
                self.session.add(new_follower)
                self.session.commit()
                entries_added += 1

            for try_n in range(1, self.default_load_retries+1):
                try:
                    if self.e.is_followers_end(follower_entry_n):
                        print("List end encountered, stopping.")
                        return entries_added
                except (StaleElementReferenceException, TimeoutException, NoSuchElementException) as e:
                    print("is_followers_end, try {} of {}, raised exception: {}"\
                                .format(try_n, self.default_load_retries, e))
                    if try_n >= self.default_load_retries:
                        raise e

            follower_entry_n += 1

        # return entries_added

    def old_start_unfollowing(self, quota=None, follow_back_hiatus=None, mutual_expire_hiatus=None):
        self.driver.get("{}/{}".format(self.application_url, self.app_username))
        sleep(5)

        self.e.following_link().click()

        followers_list_offset = self.e.followers_lightbox_interior_top()

        follow_back_hiatus = follow_back_hiatus or self.follow_back_hiatus
        mutual_expire_hiatus = mutual_expire_hiatus or self.mutual_expire_hiatus

        unfollow_count = 0
        unfollow_entry_n = 1

        # give the followers tab a very good chance to load ...
        # first_unfollow_entry = self.e.follower_entry_n(unfollow_entry_n)
        # WebDriverWait(first_unfollow_entry, 60*3).until(lambda e: self.e.follower_username(e))

        print("Waiting for list to load ...")

        # give the followers tab a very good chance to load ...
        for try_n in range(1, self.default_load_retries + 1):
            try:
                first_unfollow_entry = self.e.follower_entry_n(unfollow_entry_n)
                self.e.follower_username(first_unfollow_entry)
                break
            except (StaleElementReferenceException, NoSuchElementException, TimeoutException) as e:
                print("first_follower_entry, try {} of {}, raised exception: {}"
                        .format(try_n, self.default_load_retries, e))
                if try_n >= self.default_load_retries:
                    raise e

        while quota is None or unfollow_count < quota:

            print("Scanning entry #{} in followers list ...".format(unfollow_entry_n))

            for try_n in range(1, self.default_load_retries + 1):
                try:
                    print("start_unfollow: follower_entry_n(unfollow_entry_n)")
                    unfollow_entry = self.e.follower_entry_n(unfollow_entry_n)
                    print("start_unfollow: scrollto_element(unfollow_entry, offset=followers_list_offset)")
                    self.scrollto_element(unfollow_entry, offset=followers_list_offset)
                    print("start_unfollow: follower_username(unfollow_entry).text")
                    unfollow_username = self.e.follower_username(unfollow_entry).text

                    print("start_unfollow: follower_button(unfollow_entry)")
                    entry_button = self.e.follower_button(unfollow_entry)
                    print("start_unfollow: entry_button.text")
                    entry_button_text = entry_button.text

                    break
                except (StaleElementReferenceException, NoSuchElementException, TimeoutException) as e:
                    print("first_follower_entry, try {} of {}, raised exception: {}" \
                          .format(try_n, self.default_load_retries, e))
                    if try_n >= self.default_load_retries:
                        raise e

            print("start_unfollow: entry_username =", unfollow_username)

            # if in whitelist, skip ...
            if self.in_whitelist(unfollow_username):
                print("'{}' in whitelist, skipping ...".format(unfollow_username))
                if self.e.is_followers_end(unfollow_entry_n):
                    print("End of list encountered, returning. A")
                    return unfollow_count
                unfollow_entry_n += 1
                continue

            print("Getting entry for '{}' in db ...".format(unfollow_username))

            # get following entry from db ...
            following_db = self.session.query(Following)\
                .filter(and_(Following.name == unfollow_username,
                             Following.user_id == self.app_account.user_id,
                             Following.application_id == self.app_account.application_id,
                             Application.name == self.application_name
                             )).one_or_none()

            # if entry not in db, add with timestamp and skip ...
            if following_db is None:
                print("No entry for '{}', creating.".format(unfollow_username))
                new_following = Following(name=unfollow_username,
                                          established=datetime.now(),
                                          application_id=self.app_account.application_id,
                                          user_id=self.app_account.user_id)
                self.session.add(new_following)
                self.session.commit()
                print("Skipping newly scanned follower ...")
                if self.e.is_followers_end(unfollow_entry_n):
                    print("End of list encountered, returning. B")
                    return unfollow_count
                else:
                    unfollow_entry_n += 1
                    continue
            # follow in db, check and delete, if now > then + hiatus time ...
            else:
                # since, on instagram, there's no indication on the page for if a user in the following
                # list follows back, we have to rely on the database:
                print("Checking if '{}' follows back in db ...".format(unfollow_username))
                follows_me = self.session.query(Follower).filter(
                                                    and_(Follower.name == unfollow_username,
                                                         Follower.user_id == self.app_account.user_id,
                                                         Follower.application_id == self.app_account.application_id,
                                                         Application.name == self.application_name))\
                                                    .one_or_none()

                follow_back_expired = datetime.now() > following_db.established + follow_back_hiatus
                mutual_follow_expired = datetime.now() > following_db.established + mutual_expire_hiatus

                if not mutual_follow_expired and follows_me:
                    time_remaining = (following_db.established + mutual_expire_hiatus) - datetime.now()
                    print("Mutual expire hiatus not reached!  {} left!".format(time_remaining))
                    unfollow_entry_n += 1
                    continue
                elif not follow_back_expired:
                    time_remaining = (following_db.established + follow_back_hiatus) - datetime.now()
                    print("Follow hiatus not reached!  {} left!".format(time_remaining))
                    unfollow_entry_n += 1
                    continue

                if mutual_follow_expired and follows_me:
                    print("Mutual follow expired, unfollowing ...")
                elif follow_back_expired:
                    print("Follow expired, unfollowing ...")
                else:
                    AppUnexpectedStateException("Unfollow in unexpected state, please examine!")

                list_following_button = self.e.follower_button(unfollow_entry)
                list_following_button_text = list_following_button.text
                if list_following_button_text not in BUTTON_TEXT_FOLLOWING:
                    raise AppUnexpectedStateException(
                        "Unfollow button for '{}' says '{}'?".format(unfollow_username,
                                                                     list_following_button_text))
                list_following_button.click()
                lb_following_button = self.e.unfollow_lightbox_button()
                lb_following_button.click()

                # we need to wait and make sure button goes back to unfollowed state ...
                WebDriverWait(unfollow_entry, 60).until(
                    lambda e: self.e.follower_button(e).text in BUTTON_TEXT_NOT_FOLLOWING)

                # create a new unfollow entry, check if one already exists:
                unfollowed = self.session.query(Unfollowed).filter(
                    and_(Unfollowed.name == unfollow_username,
                         Unfollowed.user_id == self.app_account.user_id,
                         Unfollowed.application_id == Application.id,
                         Application.name == self.application_name)) \
                    .one_or_none()
                if unfollowed is None:
                    new_unfollowed = Unfollowed(name=following_db.name,
                                                established=datetime.now(),
                                                user_id=following_db.user_id,
                                                application_id=following_db.application_id)
                    self.session.add(new_unfollowed)

                self.session.delete(following_db)

                self.session.commit()
                if self.e.is_followers_end(unfollow_entry_n):
                    print("End of list encountered, returning. C")
                    return unfollow_count
                else:
                    self.sleepmsrange(self.action_timeout)
                    unfollow_entry_n += 1

        return unfollow_count

    def old_update_following(self):
        self.goto_user_page()

        self.e.following_link().click()

        followers_list_offset = self.e.followers_lightbox_interior_top()
        entries_added = 0
        follower_entry_n = 1

        # give the followers tab a very good chance to load ...
        first_follower_entry = self.e.follower_entry_n(follower_entry_n)
        WebDriverWait(first_follower_entry, 60*3).until(lambda e: self.e.follower_username(e))

        while True:
            # follower_entry = self.e.follower_entry_n(follower_entry_n)
            try:
                follower_entry = WebDriverWait(self.driver, 60*3)\
                    .until(lambda x: self.e.follower_entry_n(follower_entry_n))
                # follower_entry = self.e.follower_entry_n(follower_entry_n)
                self.scrollto_element(follower_entry, offset=followers_list_offset)
                entry_username = self.e.follower_username(follower_entry).text
                print("update_followers: entry_username =", entry_username)

                entry_button = self.e.follower_button(follower_entry)
                entry_button_text = entry_button.text
            except (StaleElementReferenceException, TimeoutException, NoSuchElementException) as e:
                print("Retrying self.e.follower_entry_n(follower_entry_n), got: {}".format(e))
                sleep(1)
                # follower_entry = self.e.follower_entry_n(follower_entry_n)
                continue

            # check to see if entry is in the database:
            self.scrollto_element(follower_entry)
            follower_username = self.e.follower_username(follower_entry).text
            print("Scanning {} ...".format(follower_username))

            following_db = self.session.query(Following)\
                                    .filter(and_(Following.name == follower_username,
                                                 Following.user_id == self.app_account.user_id,
                                                 Following.application_id == self.app_account.application_id
                                            )).one_or_none()

            if following_db is None:
                print("No entry for '{}', creating.".format(follower_username))
                new_following = Following(name=follower_username,
                                         established=datetime.now(),
                                         application_id=self.app_account.application_id,
                                         user_id=self.app_account.user_id)
                self.session.add(new_following)
                self.session.commit()
                entries_added += 1
            else:
                print("Entry for '{}' is already in the database!".format(follower_username))

            for try_n in range(1, self.default_load_retries+1):
                try:
                    if self.e.is_followers_end(follower_entry_n):
                        print("List end encountered, stopping.")
                        return entries_added
                except (StaleElementReferenceException, TimeoutException, NoSuchElementException) as e:
                    print("is_followers_end, try {} of {}, raised exception: {}"\
                                .format(try_n, self.default_load_retries, e))
                    if try_n >= self.default_load_retries:
                        raise e

            follower_entry_n += 1

        # return entries_added

    def post_image(self, image_filename, post_body, retries=20):
        # here, we have to set the input form to image_filename, then click submit ...

        for try_n in range(1, retries+1):
            self.goto_homepage()

            try:
                self.driver.implicitly_wait(10)
                form_element = self.driver.find_element(By.XPATH, '(//form[@role="presentation" and @method="POST"])[1]')
                image_input = self.driver.find_element(By.XPATH, './/input')
                image_input.send_keys(image_filename)

                print("Submitting image ...")

                # click the button, but then make sure main window is in Selenium focus ...
                image_submit_button = self.driver.find_element(
                    By.XPATH, '//div[@data-testid="new-post-button"]')
                image_submit_button.click()

                # Experiment, try waiting for the Next link before continuing ...
                self.driver.find_element(By.XPATH, '//button[text() = "Next"]')

            except (NoSuchElementException, StaleElementReferenceException) as e:
                print("Exception (1): ", e)
                if try_n == retries:
                    raise e
                continue
            finally:
                self.driver.implicitly_wait(self.implicit_default_wait)

            # XXX I do want to click the resize button, if present!
            try:
                self.driver.implicitly_wait(0)
                expand_button = self.driver.find_element(
                    By.XPATH, '//button/span[contains(@class, "createSpriteExpand") and text()="Expand"]')
                self.scrollto_element(expand_button)
                expand_button.click()
            except NoSuchElementException as e:
                print("Exception (2): ", e)
                pass
            finally:
                self.driver.implicitly_wait(self.implicit_default_wait)

            try:
                self.driver.implicitly_wait(5)
                next_button = self.driver.find_element(By.XPATH, '//button[text() = "Next"]')
                next_button.click()

                caption_input = self.driver.find_element(By.XPATH, '//textarea[@aria-label="Write a caption…"]')
                caption_input.send_keys(post_body)

                share_button = self.driver.find_element(By.XPATH, '//button[text() = "Share"]')
                share_button.click()
            except (NoSuchElementException, StaleElementReferenceException) as e:
                print("Exception (3): ", e)
                if try_n == retries:
                    raise e
                continue
            finally:
                self.driver.implicitly_wait(self.implicit_default_wait)

            try:
                self.driver.implicitly_wait(30)
                # wait for the header image to be present, to verify submission ...
                self.e.instagram_header_img()
                break
            except (NoSuchElementException, StaleElementReferenceException) as e:
                print("Exception (4): ", e)
                if try_n == retries:
                    raise e
                continue
            finally:
                self.driver.implicitly_wait(self.implicit_default_wait)


class InstagramHandlerWebElements:
    # follower_xpath_prefix = '//div[@role="dialog"]/div/div[2]/ul/div'
    _followers_lighbox_prefix = '//div[@role="presentation"]/div[@role="dialog"]'
    implicit_default_wait = 60

    def instagram_header_img(self):
        return self.driver.find_element(By.XPATH,
                                        '//*[@id="react-root"]/section/nav[1]'
                                        '/div/div/header/div/h1/div/a/img[@alt="Instagram"]')

    def followers_lightbox(self):
        return self.driver.find_element(By.XPATH, self._followers_lighbox_prefix)

    def followers_lightbox_interior_top(self):
        lightbox = self.followers_lightbox()
        e = lightbox.find_element(By.XPATH, './div/div[2]')
        print("followers_lightbox_top: got element.")

        offset_script = """
        var rect = arguments[0].getBoundingClientRect();
        return rect.top;
        """
        interior_top = self.driver.execute_script(offset_script, e)

        print("followers_lightbox_top: got interior_top =", interior_top)
        return int(interior_top)

    def first_follower_entry(self):
        lightbox = self.followers_lightbox()
        return lightbox.find_element(By.XPATH, './div/div[2]/ul/div/li[1]')

    def follower_entry_n(self, n):
        # lightbox = self.followers_lightbox()
        return self.driver.find_element(By.XPATH, self._followers_lighbox_prefix
                                      +'/div/div[2]/ul/div/li[{}]'.format(n))
                                     #+'/div/div[2]/ul/div/li')[n - 1]

    def follower_entry_last(self):
        return self.driver.find_element(By.XPATH, self._followers_lighbox_prefix
                                        +'/div/div[2]/ul/div/li[last()]')
                                        # +'/div/div[2]/ul/div/li')[-1]

    def follower_entries_len(self):
        return len(self.driver.find_elements(By.XPATH, self._followers_lighbox_prefix
                                        # /div/div[2]/ul/div/li[last()]
                                        +'/div/div[2]/ul/div/li'))

    def is_followers_end(self, n):
        print("is_followers_end: called ...")

        def _compare_elements_n(x):
            len_e = self.follower_entries_len()
            print("is_followers_end: _compare_elements_n: {} == {}".format(n, len_e))
            return n == len_e

        try:
            print("is_followers_end: waiting ...")
            self.driver.implicitly_wait(60*5)
            r = WebDriverWait(self.driver, timeout=60*5,
                                 ignored_exceptions=(StaleElementReferenceException,))\
                            .until_not(_compare_elements_n)

            print("is_followers_end: returning", r)
            return r
        except TimeoutException:
            print("is_followers_end: TimeoutException ...")
            return True
        finally:
            self.driver.implicitly_wait(self.implicit_default_wait)

    def is_followers_end_entry(self, follower_entry, retry=20):

        def _compare_elements_entries(x):
            print("is_followers_end_entry: find_element(By.XPATH, './following-sibling::li[last()]')")
            entry_end = self.driver.find_element(By.XPATH, './following-sibling::[last()]')
            entry_text = self.follower_username(follower_entry).text
            print("is_followers_end_entry: entry_text =", entry_text)
            entry_end_text = self.follower_username(entry_end).text
            print("is_followers_end_entry: entry_end_text =", entry_end_text)
            print("is_followers_end_entry: _compare_elements: '{}' == '{}'".format(entry_text, entry_end_text))
            return entry_text == entry_end_text

        for try_n in range(1, retry+1):
            try:
                # self.driver.implicitly_wait(30)
                print("is_followers_end_entry: setting up web driver wait ...")
                r = WebDriverWait(self.driver,
                                  timeout=30,
                                  ignored_exceptions=(StaleElementReferenceException,))\
                            .until_not(_compare_elements_entries)
                print("is_followers_end_entry: returning", r)
                return r
            except (StaleElementReferenceException) as e:
                print("is_followers_end_entry: TimeoutException ...")
                return True
            # finally:
            #     self.driver.implicitly_wait(self.implicit_default_wait)

    @staticmethod
    def next_follower_entry(follower_entry, retries=20):
        print("in next_follower_entry:")
        for try_n in range(1, retries+1):
            try:  # following-sibling::div
                print('next_follower_entry: searching for: ./following-sibling::li[1]')
                return follower_entry.find_element(By.XPATH, './following-sibling::li[1]')
            except (StaleElementReferenceException, NoSuchElementException) as e:
                print('next_follower_entry: caught exception:', e)
                if try_n == retries:
                    raise e
                else:
                    print("next_follower_entry, caught exception try {} of {}: {}".format(try_n, retries, e))


    def followers_link(self):
        return self.driver.find_element(
            By.XPATH,
            "//a[contains(.,' followers')]")

    def following_link(self):
        return self.driver.find_element(
            By.XPATH,
            "//a[contains(.,' following')]")

    @staticmethod
    def follower_username(follower_entry):
        # /html/body/div[5]/div/div/div[2]/ul/div/li[7]/div/div[1]/div[2]/div[1]/a
        # /html/body/div[4]/div/div/div[2]/ul/div/li[1]/div/div[2]/div[1]/div/div/a
        return follower_entry.find_element(
            By.XPATH, './div/div[1]/div[2]/div[1]/a | '
                      './div/div[2]/div[1]/div/div/a')

    @staticmethod
    def follower_image(follower_entry):
        # /html/body/div[5]/div/div/div[2]/ul/div/li[7]/div/div[1]/div[1]/a/img
        # not sure why the <a> is a <span> sometimes, private accounts, maybe?
        return follower_entry.find_element(
            By.XPATH, './div/div[1]/div[1]/*[self::a or self::span]/img')

    @staticmethod
    def follower_button(follower_entry):
        # /html/body/div[5]/div/div/div[2]/ul/div/li[7]/div/div[2]/button
        # /html/body/div[4]/div/div/div[2]/ul/div/li[7]/div/div[3]/button
        return follower_entry.find_element(By.XPATH, './div/div[2]/button |'
                                                     './div/div[3]/button')

    @staticmethod
    def follower_is_verified(follower_entry):
        try:
            follower_entry.find_element(By.XPATH,
                                        './div/div[2]/div[1]/div/div/span[@title="Verified"]')
        except NoSuchElementException:
            return False
        return True

    def follow_click_verify_cb(self, n):
        def follow_click_verify(x):
            return self.follower_button(n).text in ('Following', 'Requested')
        return follow_click_verify

    def unfollow_lightbox_button(self):
        # /html/body/div[5]/div/div/div/div[3]/button[1]
        return self.driver.find_element(By.XPATH, self._followers_lighbox_prefix +
                                                  "//button[contains(.,'Unfollow')]")

    def image_upload_input(self):
        # user-agent mobile only!
        # form input for image upload!
        # //*[@id="react-root"]/form/input  -- this is the first of many forms on the page?
        # //input[@id="ext_upload_input"] -- this is another significant form?
        pass

    def image_upload_button(self):
        # user-agent mobile only!
        # //*[@id="react-root"]/section/nav[2]/div/div/div[2]/div/div/div[3]
        pass