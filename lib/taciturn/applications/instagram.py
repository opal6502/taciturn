
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

from sqlalchemy import and_

from taciturn.applications.base import (
    FollowerApplicationHandler,
    ApplicationWebElements,
    AppLoginException,
    AppUnexpectedStateException,
    AppRetryLimitException)

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

BUTTON_TEXT_FOLLOWING = ('Following', 'Requested')
BUTTON_TEXT_NOT_FOLLOWING = ('Follow',)


class InstagramHandler(FollowerApplicationHandler):
    application_name = 'instagram'

    application_url = "https://instagram.com"
    application_login_url = application_url

    application_asset_dirname = 'instagram'
    default_profile_image = 'default-profile-pic.jpg'

    follow_random_wait = (10, 60)

    def __init__(self, db_session, app_account, elements=None):
        super().__init__(db_session, app_account, InstagramHandlerWebElements)

        self.follow_back_hiatus = self.config['app:instagram']['follow_back_hiatus']
        self.unfollow_hiatus = self.config['app:instagram']['unfollow_hiatus']
        self.action_timeout = self.config['app:instagram']['action_timeout']
        self.mutual_expire_hiatus = self.config['app:instagram']['mutual_expire_hiatus']

        self.goto_homepage()

    def goto_homepage(self):
        self.driver.get(self.application_url)

    def goto_user_page(self):
        self.driver.get("{}/{}/".format(self.application_url, self.app_username))

    def login(self):
        # enter username and password:

        login_form = self.driver.find_element(By.XPATH, '//form')
        name_field = login_form.find_element(By.NAME, 'username')
        password_field = login_form.find_element(By.NAME, 'password')
        login_button = login_form.find_element(By.XPATH, '//button/div')

        # perform login:
        name_field.send_keys(self.app_username)
        password_field.send_keys(self.app_password)
        login_button.click()

        # sometimes prompted with extra security, check if bypass necessary:

        not_now_link = self.driver.find_element(By.XPATH, "//button[contains(.,'Not Now')]")
        if not_now_link:
            not_now_link.click()

        # sometimes prompted with notifications on/off choice:

        notif_dialog = self.driver.find_element(By.XPATH, "//div[@role='dialog']")
        if notif_dialog:
            notif_text = notif_dialog.find_element(By.XPATH, "//h2[contains(.,'Turn on Notifications')]")
            notif_button = notif_dialog.find_element(By.XPATH, "//button[contains(.,'Not Now')]")
            notif_button.click()

        # verify that the main section exists, and contains a link with our username:

        main_section = self.driver.find_element(By.XPATH, "//main/section")
        username_link = main_section.find_element(
            By.XPATH,
            "//a[contains(text(),'{}')]".format(self.app_username))

        if not username_link:
            raise AppLoginException("Could not login!")

        return True

    def start_following(self, target_account, quota=None, unfollow_hiatus=None):
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
                first_follower_entry = self.e.follower_entry_n(follower_entry_n)
                self.e.follower_username(first_follower_entry)
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
                follower_entry_n += 1
                # follower_entry = self.e.follower_entry_n(follower_entry)
                continue

            entry_is_default_image = self.is_default_image(entry_image_src)
            if entry_is_default_image:
                print("start_following: image is default, skip ...")
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
                follower_entry_n += 1
                continue

            # XXX if we've been blocked, most likely they won't even
            # show up in following lists for us to click on?

            # if user is in blacklist ...

            if self.in_blacklist(entry_username):
                print("{} is in blacklist, skip ...")
                # follower_entry = self.e.follower_entry_n(follower_entry_n)
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
                if already_following is not None:
                    print("Warning: user '{}' already recorded as following?"
                          "  Moving record to unfollowed.".format(entry_username))
                    new_unfollowed = Unfollowed(name=already_following.name,
                                                established=datetime.now(),
                                                user_id=already_following.user_id,
                                                application_id=already_following.application_id)
                    self.session.add(new_unfollowed)
                    self.session.delete(already_following)
                    self.session.commit()
                    follower_entry_n += 1
                    continue

                print("Clicking 'Follow' button ...")

                entry_button.click()

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
                follower_entry_n += 1
                # sleep(5)
                self.sleepmsrange(self.action_timeout)

        return followed_count

    def update_followers(self):
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

    def start_unfollow(self, quota=None, follow_back_hiatus=None, mutual_expire_hiatus=None):
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

        # give the followers tab a very good chance to load ...
        for try_n in range(1, self.default_load_retries + 1):
            try:
                first_unfollow_entry = self.e.follower_entry_n(unfollow_entry_n)
                self.e.follower_username(first_unfollow_entry)
            except (StaleElementReferenceException, NoSuchElementException, TimeoutException) as e:
                print("first_follower_entry, try {} of {}, raised exception: {}" \
                      .format(try_n, self.default_load_retries, e))
                if try_n >= self.default_load_retries:
                    raise e

        while quota is None or unfollow_count < quota:

            for try_n in range(1, self.default_load_retries + 1):
                try:
                    unfollow_entry = self.e.follower_entry_n(unfollow_entry_n)
                    self.scrollto_element(unfollow_entry, offset=followers_list_offset)
                    unfollow_username = self.e.follower_username(unfollow_entry).text

                    entry_button = self.e.follower_button(unfollow_entry)
                    entry_button_text = entry_button.text
                except (StaleElementReferenceException, NoSuchElementException, TimeoutException) as e:
                    print("first_follower_entry, try {} of {}, raised exception: {}" \
                          .format(try_n, self.default_load_retries, e))
                    if try_n >= self.default_load_retries:
                        raise e

            print("start_unfollow: entry_username =", unfollow_username)

            # if in whitelist, skip ...
            if self.in_whitelist(unfollow_username):
                print("'{}' in whitelist, skipping ...".format(unfollow_username))
                if self.e.is_followers_end():
                    print("End of list encountered, returning.")
                    return unfollow_count
                else:
                    unfollow_entry_n += 1
                    continue

            # get following entry from db ...
            following_db = self.session.query(Following) \
                .filter(and_(Following.user_id == self.app_account.user_id,
                             Following.application_id == self.app_account.application_id,
                             Following.name == unfollow_username
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
                if self.e.is_followers_end():
                    print("End of list encountered, returning.")
                    return unfollow_count
                else:
                    unfollow_entry_n += 1
                    continue
            # follow in db, check and delete, if now > then + hiatus time ...
            else:
                # since, on instagram, there's no indication on the page for if a user in the following
                # list follows back, we have to rely on the database:
                follows_me = self.session.query(Follower).filter(
                                                    and_(Follower.name == unfollow_username,
                                                         Follower.user_id == self.app_account.user_id,
                                                         Follower.application_id == self.app_account.application_id,
                                                         Application.name == self.application_name))\
                                                    .one_or_none()

                # check both follow back, or mutual follow expires ...
                if (datetime.now() > following_db.established + follow_back_hiatus) or \
                        (follows_me is not None and datetime.now() > following_db.established + mutual_expire_hiatus):
                    if follows_me is not None:
                        print("Mutual follow expired, unfollowing ...")
                    else:
                        print("Follow expired, unfollowing ...")
                    list_following_button = self.e.follower_button(unfollow_entry)
                    list_following_button_text = list_following_button.text
                    if list_following_button_text != 'Unfollow':
                        raise AppUnexpectedStateException(
                            "Unfollow button for '{}' says '{}'?".format(unfollow_username,
                                                                        list_following_button_text))
                    list_following_button_text.click()
                    lb_following_button = self.e.unfollow_lightbox_button()
                    lb_following_button.click()

                    # we need to wait and make sure button goes back to unfollowed state ...
                    WebDriverWait(unfollow_entry, 60).until(
                        lambda e: self.e.follower_button(e).text in BUTTON_TEXT_NOT_FOLLOWING)

                    # create a new unfollow entry:
                    new_unfollowed = Unfollowed(name=following_db.name,
                                                established=datetime.now(),
                                                user_id=following_db.user_id,
                                                application_id=following_db.application_id)

                    self.session.add(new_unfollowed)
                    self.session.delete(following_db)

                    self.session.commit()
                    if self.e.is_followers_end():
                        print("End of list encountered, returning.")
                        return unfollow_count
                    else:
                        self.sleepmsrange(self.action_timeout)
                # report that follow back, or mutual follow has not expired ...
                else:
                    if follows_me is not None:
                        time_remaining = (following_db.established + mutual_expire_hiatus) - datetime.now()
                        print("Mutual expire hiatus not reached!  {} left!".format(time_remaining))
                    else:
                        time_remaining = (following_db.established + follow_back_hiatus) - datetime.now()
                        print("Follow hiatus not reached!  {} left!".format(time_remaining))

                unfollow_entry_n += 1

        return unfollow_count

    def update_following(self):
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


class InstagramHandlerWebElements(ApplicationWebElements):
    # follower_xpath_prefix = '//div[@role="dialog"]/div/div[2]/ul/div'
    _followers_lighbox_prefix = '//div[@role="presentation"]/div[@role="dialog"]'

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

    def follower_entry_n(self, n=1):
        # lightbox = self.followers_lightbox()
        return self.driver.find_element(By.XPATH, self._followers_lighbox_prefix\
                                     +'/div/div[2]/ul/div/li[{}]'.format(n))

    def follower_entry_last(self):
        return self.driver.find_element(By.XPATH, self._followers_lighbox_prefix
                                        +'/div/div[2]/ul/div/li[last()]')

    def is_followers_end(self, n=1):
        entry_n = WebDriverWait(self.driver, 90).until(lambda x: self.follower_entry_n(n))
        entry_end = WebDriverWait(self.driver, 90).until(lambda x: self.follower_entry_last())
        if self.follower_username(entry_n).text == self.follower_username(entry_end).text:
            return True
        return False

    def next_follower_entry(self, follower_entry):
        return follower_entry.find_element(By.XPATH, './following-sibling::li[1]')

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

    def follow_click_verify_cb(self, n=1):
        def follow_click_verify(x):
            return self.follower_button(n).text in ('Following', 'Requested')
        return follow_click_verify

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