
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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from sqlalchemy import and_

from taciturn.applications.base import (
    FollowerApplicationHandler,
    ApplicationWebElements,
    AppLoginException,
    AppUnexpectedStateException
)

from taciturn.db.followers import (
    Follower,
    Following,
    Unfollowed
)

from taciturn.db.base import (
    User,
    Application,
)

from selenium.common.exceptions import NoSuchElementException

from datetime import datetime
from time import sleep
import os

BUTTON_TEXT_NOT_FOLLOWING = ('Follow',)
BUTTON_TEXT_FOLLOWING = ('Following',)


class SoundcloudHandler(FollowerApplicationHandler):
    application_name = 'soundcloud'

    application_url = "https://soundcloud.com"
    application_login_url = application_url

    application_asset_dirname = 'soundcloud'
    # default_profile_image = 'default-profile-pic.jpg'

    # user_agent = 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'

    follow_random_wait = (10, 60)

    def __init__(self, options, db_session, app_account, driver=None, elements=None):
        super().__init__(options, db_session, app_account, driver, SoundcloudHandlerWebElements)

        self.follow_back_hiatus = self.config['app:soundcloud']['follow_back_hiatus']
        self.unfollow_hiatus = self.config['app:soundcloud']['unfollow_hiatus']
        self.action_timeout = self.config['app:soundcloud']['action_timeout']
        self.mutual_expire_hiatus = self.config['app:soundcloud']['mutual_expire_hiatus']

        if self.options.driver is not None:
            if self.options.driver[0].endswith('_headless'):
                self.headless_mode = True
            else:
                self.headless_mode = False
        elif self.config['selenium_webdriver'].endswith('_headless'):
            self.headless_mode = True
        else:
            self.headless_mode = False

        self.init_webdriver()

        if options.cookies:
            self.load_cookies(options.cookies[0])

        # self.goto_homepage()

    def goto_homepage(self):
        self.driver.get(self.application_url)

    def goto_user_page(self):
        # navigate using the ui ... to accommodate google user email login ;)
        header_profile_menu = self.e.header_profile_menu()
        self.scrollto_element(header_profile_menu)

        with open(self.screenshots_dir+'/soundcloud_page_last.html', 'w') as gh:
            gh.write(self.driver.page_source)
        self.driver.save_screenshot(os.path.join(self.screenshots_dir, 'soundcloud_image_last.png'))

        header_profile_menu.click()
        self.e.header_profile_menu_profile_link().click()

    def goto_following_page(self):
        self.goto_user_page()
        followers_link = self.e.profile_following_link()
        followers_link.click()

    def goto_followers_page(self):
        self.goto_user_page()
        followers_link = self.e.profile_followers_link()
        followers_link.click()

    def login(self):
        if self.headless_mode:
            self.login_headless()
        else:
            self.login_head()

    def login_headless(self):
        self.driver.get('https://accounts.google.com/Login')

        print('Loggin in through google ...')

        self.driver.find_element_by_id("Email").send_keys(self.app_account.name)
        self.driver.find_element_by_id("next").click()
        self.driver.find_element_by_id("password").send_keys(self.app_account.password)
        self.driver.find_element_by_id("submit").click()

        print('Signing into soundcloud ...')

        # goto soundcloud main page:
        self.goto_homepage()

        print('Clicking login ...')

        # click on login:
        sign_in_button = self.driver.find_element(
            By.CSS_SELECTOR, r'button.frontHero__loginButton:first-child')
        sign_in_button.click()

        # switch to login iframe:
        login_iframe = self.driver.find_element(By.XPATH, '//iframe[@class="webAuthContainer__iframe"]')
        self.driver.switch_to.frame(login_iframe)

        print('Clicking google sign in ...')

        with open(self.screenshots_dir+'/soundcloud_page_last.html', 'w') as gh:
            gh.write(self.driver.page_source)
        self.driver.save_screenshot(os.path.join(self.screenshots_dir, 'soundcloud_image_last.png'))

        # click google sign-in button:
        user_google_button = self.driver.find_element(
            By.CSS_SELECTOR, r'button.google-plus-signin')
        user_google_button.click()

        self.driver.switch_to.default_content()

        # use the 'Messages' element to verify login!
        # //*[@id="app"]/header/div/div[3]/div[2]/a[3]/div/span[contains(.,"Messages")]
        self.driver.find_element(
            By.XPATH, r'//*[@id="app"]/header/div/div[3]/div[2]/a[3]/div/span[contains(.,"Messages")]')

        print("Logged in!")

        self.e.close_if_pro_lightbox()

    def login_head(self):
        # go to google login first ...
        print("Non-headless login mode!")
        print('Loggin in through google ...')

        self.driver.get('https://accounts.google.com/Login')

        print('Loggin in through google ...')

        # dump google login to html:
        with open(self.screenshots_dir+'/google_login_last.html', 'w') as gh:
            gh.write(self.driver.page_source)

        google_name_field = self.driver.find_element(By.XPATH, '//input[@id="identifierId"]')
        google_name_field.send_keys(self.app_account.name)

        # click 'Next' button:
        # //*[@id="identifierNext"]/div/span/span[text() = "Next"]
        google_next_button = self.driver.find_element(By.XPATH, '//*[@id="identifierNext"]//span[text()="Next"]')
        google_next_button.click()

        # enter password:
        # //input[@name="password"]
        google_password_field = self.driver.find_element(By.XPATH, '//input[@name="password"]')
        google_password_field.send_keys(self.app_account.password)

        # click the 'Next' button:
        # //*[@id="passwordNext"]/div/span/span[text() = "Next"]
        google_next_button = self.driver.find_element(By.XPATH, '//*[@id="passwordNext"]//span[text()="Next"]')
        google_next_button.click()

        # goto soundcloud main page:
        self.goto_homepage()

        # click on login:
        sign_in_button = self.driver.find_element(
            By.CSS_SELECTOR, r'button.frontHero__loginButton:first-child')
        sign_in_button.click()

        # switch to login iframe:
        login_iframe = self.driver.find_element(By.XPATH, '//iframe[@class="webAuthContainer__iframe"]')
        self.driver.switch_to.frame(login_iframe)

        # click google sign-in button:
        user_google_button = self.driver.find_element(
            By.CSS_SELECTOR, r'button.google-plus-signin')
        user_google_button.click()

        self.driver.switch_to.default_content()

        # use the 'Messages' element to verify login!
        # //*[@id="app"]/header/div/div[3]/div[2]/a[3]/div/span[contains(.,"Messages")]
        self.driver.find_element(
            By.XPATH, r'//*[@id="app"]/header/div/div[3]/div[2]/a[3]/div/span[contains(.,"Messages")]')

        print("Logged in!")

        self.e.close_if_pro_lightbox()

    def start_following(self, target_account, quota=None, unfollow_hiatus=None):
        self.driver.get(self.application_url+'/'+target_account+'/followers')

        # scan the header menu overhang:
        header_menu_offset = self.e.followers_header_overlap()
        # get the first follower entry:
        follower_entry = self.e.first_follower_entry()
        followed_count = 0

        while quota is None or followed_count < quota:
            self.scrollto_element(follower_entry, offset=header_menu_offset)

            entry_username = self.e.follower_username(follower_entry)

            # check to see if we've unfollowed this user within the unfollow_hiatus time:
            unfollowed = self.session.query(Unfollowed).filter(
                and_(Unfollowed.name == entry_username,
                     Unfollowed.user_id == self.app_account.user_id,
                     Unfollowed.application_id == Application.id,
                     Application.name == self.application_name)) \
                .one_or_none()
            if unfollowed is not None and datetime.now() < unfollowed.established + self.unfollow_hiatus:
                time_remaining = (unfollowed.established + self.unfollow_hiatus) - datetime.now()
                print("Followed/unfollowed too recently, can follow again after", time_remaining)
                follower_entry = self.e.next_follower_entry(follower_entry)
                continue

            entry_image = self.e.follower_image(follower_entry)
            entry_button = self.e.follower_button(follower_entry)
            ActionChains(self.driver).move_to_element(entry_button).perform()
            entry_button_text = entry_button.text

            print('start_following: follower_username =', entry_username)
            print('start_following: follower_image =', entry_image)
            print('start_following: follower_button =', entry_button)
            print('start_following: follower_button text =', entry_button_text)
            print('start_following: follower_button title =', entry_button.get_attribute('title'))

            # note because soundcloud uses css gradients for default images,
            # get_follower_image will return None in this case!
            if entry_image is None:
                print("Default image, skip ...")
                follower_entry = self.e.next_follower_entry(follower_entry)
                continue

            if entry_username in self.blacklist:
                print("Account '{}' in blacklist, skip ...")
                follower_entry = self.e.next_follower_entry(follower_entry)
                continue

            if entry_button_text in BUTTON_TEXT_NOT_FOLLOWING:
                print("start_following: checking records before following ...")
                # check to see if we're already (supposed to be following) this user:
                already_following = self.session.query(Following) \
                    .filter(and_(Following.name == entry_username,
                                 Following.user_id == self.app_account.user_id,
                                 Following.application_id == self.app_account.application_id)) \
                    .one_or_none()
                if already_following is not None:
                    print("Warning: not followed user '{}' already recorded as following?"
                          "  Moving to unfollowed.".format(entry_username))
                    self.session.delete(already_following)

                    new_unfollowed = Unfollowed(name=already_following.name,
                                                established=datetime.now(),
                                                user_id=already_following.user_id,
                                                application_id=already_following.application_id)
                    self.session.add(new_unfollowed)
                    self.session.delete(already_following)
                    self.session.commit()

                    follower_entry = self.e.next_follower_entry(follower_entry)
                    continue

                # check to see if we've recently unfollowed this user:
                already_unfollowed = self.session.query(Unfollowed) \
                    .filter(and_(Unfollowed.user_id == self.app_account.user_id,
                                 Unfollowed.application_id == self.app_account.application_id,
                                 Unfollowed.name == entry_username)).one_or_none()
                # then check if unfollow was recent:
                if already_unfollowed is not None and \
                        datetime.now() < already_unfollowed.established + unfollow_hiatus:
                    print("Already followed and unfollowed this user '{}', "
                          "will follow again after {}".format(entry_username,
                                                              already_unfollowed.established + unfollow_hiatus))
                    follower_entry = self.e.next_follower_entry(follower_entry)
                    continue

                print("Clicking 'Follow' button ...")

                entry_button.click()
                sleep(1)

                if self.e.is_following_blocked():
                    raise RuntimeError("Looks like following is blocked, stopping.")
                    # return followed_count

                try:
                    WebDriverWait(self.driver, timeout=90)\
                        .until(lambda x: self.e.follower_button(follower_entry).text in BUTTON_TEXT_FOLLOWING)
                except TimeoutException:
                    print("Follow not verified, apparently we're done.")
                    return followed_count

                print("Follow verified.")

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
                self.sleepmsrange(self.action_timeout)

            elif entry_button_text in BUTTON_TEXT_FOLLOWING:
                # do nothing!
                pass
            else:
                raise AppUnexpectedStateException(
                    "Entry button for '{}' says '{}'?".format(entry_username, entry_button.text))

            if self.e.is_followers_end(follower_entry):
                print("List end encountered, stopping.")
                return followed_count

            follower_entry = self.e.next_follower_entry(follower_entry)
            # sleep(3)

        return followed_count

    def start_unfollowing(self, quota=None, follow_back_hiatus=None, mutual_expire_hiatus=None):
        # print(" GET {}/{}/following".format(self.application_url, self.app_username))
        self.goto_following_page()
        sleep(5)

        following_entry = self.e.first_follower_entry()
        print("following_entry =", following_entry)
        unfollow_count = 0
        follow_back_hiatus = follow_back_hiatus or self.follow_back_hiatus
        mutual_expire_hiatus = mutual_expire_hiatus or self.mutual_expire_hiatus
        header_menu_offset = self.e.followers_header_overlap()

        while quota is None or quota > unfollow_count:
            self.scrollto_element(following_entry, offset=header_menu_offset)
            sleep(0.1)

            following_username = self.e.follower_username(following_entry)
            print("Scanning {} ...".format(following_username))

            # if in whitelist, skip ...
            if self.in_whitelist(following_username):
                print("'{}' in whitelist, skipping ...".format(following_username))
                if self.e.is_followers_end(following_entry):
                    print("List end encountered, stopping.")
                    return unfollow_count
                following_entry = self.e.next_follower_entry(following_entry)
                continue

            # get following entry from db ...
            following_db = self.session.query(Following) \
                .filter(and_(Following.user_id == self.app_account.user_id,
                             Following.application_id == self.app_account.application_id,
                             Following.name == following_username
                             )).one_or_none()

            # if entry not in db, add with timestamp and skip ...
            if following_db is None:
                print("No entry for '{}', creating.".format(following_username))
                new_following = Following(name=following_username,
                                          established=datetime.now(),
                                          application_id=self.app_account.application_id,
                                          user_id=self.app_account.user_id)
                self.session.add(new_following)
                self.session.commit()
                print("Skipping newly scanned follower ...")
                if self.e.is_followers_end(following_entry):
                    print("List end encountered, stopping.")
                    return unfollow_count
                following_entry = self.e.next_follower_entry(following_entry)
                continue
            # follow in db, check and delete, if now > then + hiatus time ...
            else:
                print("Checking if '{}' follows back in db ...".format(following_username))
                follows_me = self.session.query(Follower).filter(
                                                    and_(Follower.name == following_username,
                                                         Follower.user_id == self.app_account.user_id,
                                                         Follower.application_id == self.app_account.application_id,
                                                         Application.name == self.application_name))\
                                                    .one_or_none()

                follow_back_expired = datetime.now() > following_db.established + follow_back_hiatus
                mutual_follow_expired = datetime.now() > following_db.established + mutual_expire_hiatus

                if not mutual_follow_expired and follows_me:
                    time_remaining = (following_db.established + mutual_expire_hiatus) - datetime.now()
                    print("Mutual expire hiatus not reached!  {} left!".format(time_remaining))
                    if self.e.is_followers_end(following_entry):
                        print("List end encountered, stopping.")
                        return unfollow_count
                    following_entry = self.e.next_follower_entry(following_entry)
                    continue
                elif not follow_back_expired:
                    time_remaining = (following_db.established + follow_back_hiatus) - datetime.now()
                    print("Follow hiatus not reached!  {} left!".format(time_remaining))
                    if self.e.is_followers_end(following_entry):
                        print("List end encountered, stopping.")
                        return unfollow_count
                    following_entry = self.e.next_follower_entry(following_entry)
                    continue

                    # we need to wait and make sure button goes back to unfollowed state ...
                try:
                    WebDriverWait(following_entry, 60).until(
                        lambda e: self.e.follower_button(e).text in BUTTON_TEXT_NOT_FOLLOWING)
                except TimeoutException:
                    print("Couldn't unfollow, apparently we're done.")
                    return unfollow_count

                # create a new unfollow entry:
                new_unfollowed = Unfollowed(name=following_db.name,
                                            established=datetime.now(),
                                            user_id=following_db.user_id,
                                            application_id=following_db.application_id)

                self.session.add(new_unfollowed)
                self.session.delete(following_db)

                self.session.commit()
                unfollow_count += 1

                self.sleepmsrange(self.action_timeout)

            if self.e.is_followers_end(following_entry):
                print("List end encountered, stopping.")
                return unfollow_count
            following_entry = self.e.next_follower_entry(following_entry)

    def update_following(self):
        self.goto_following_page()

        header_menu_offset = self.e.followers_header_overlap()
        # get the first follower entry:
        follower_entry = self.e.first_follower_entry()
        entries_added = 0

        while True:
            # check to see if entry is in the database:
            self.scrollto_element(follower_entry)
            follower_username = self.e.follower_username(follower_entry)
            print("Scanning {} ...".format(follower_username))

            following_db = self.session.query(Following)\
                                    .filter(and_(Following.user_id == self.app_account.user_id,
                                                 Following.application_id == self.app_account.application_id,
                                                 Following.name == follower_username
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

            sleep(0.1)

            # check to see if this looks like the end:
            if self.e.is_followers_end(follower_entry):
                print("List end encountered, stopping.")
                return entries_added

            follower_entry = self.e.next_follower_entry(follower_entry)
            sleep(0.4)

    def update_followers(self):
        self.goto_followers_page()

        header_menu_offset = self.e.followers_header_overlap()
        # get the first follower entry:
        follower_entry = self.e.first_follower_entry()
        entries_added = 0

        while True:
            self.scrollto_element(follower_entry, offset=header_menu_offset)

            entry_username = self.e.follower_username(follower_entry)

            print("Scanning {} ...".format(entry_username))

            following_db = self.session.query(Follower)\
                                    .filter(and_(Follower.user_id == self.app_account.user_id,
                                                 Follower.application_id == self.app_account.application_id,
                                                 Follower.name == entry_username
                                            )).one_or_none()

            if following_db is None:
                print("No entry for '{}', creating.".format(entry_username))
                new_follower = Follower(name=entry_username,
                                        established=datetime.now(),
                                        application_id=self.app_account.application_id,
                                        user_id=self.app_account.user_id)
                self.session.add(new_follower)
                self.session.commit()
                entries_added += 1

            # check to see if this looks like the end:
            if self.e.is_followers_end(follower_entry):
                print("List end encountered, stopping.")
                return entries_added

            follower_entry = self.e.next_follower_entry(follower_entry)
            sleep(0.4)


class SoundcloudHandlerWebElements(ApplicationWebElements):

    def header_profile_menu(self):
        return self.driver.find_element(
                                By.XPATH,
                                '//*[@id="app"]/header/div/div[3]/div[2]/a[1]/div[2]/div/span')

    def header_profile_menu_profile_link(self):
        return self.driver.find_element(
                                By.XPATH,
                                '//*[starts-with(@id,"dropdown-button-")]/div/ul[1]/li[1]/a[text()="Profile"]')

    def followers_header_overlap(self, retries=10):
        # followers menu section:
        # //*[@id="content"]/div/div/div[1]
        for try_n in range(1, retries + 1):
            try:
                followers_menu_section = self.driver.find_element(By.XPATH, '//*[@id="content"]/div/div/div[1]')
                offset_script = """
                var rect = arguments[0].getBoundingClientRect();
                return rect.bottom;
                """
                followers_menu_bottom = self.driver.execute_script(offset_script, followers_menu_section)
                return int(followers_menu_bottom)
            except (StaleElementReferenceException, TimeoutException, NoSuchElementException) as e:
                print("followers_header_overlap, try {} of {}, raised exception: {}"
                      .format(try_n, retries, e))
                if try_n >= retries:
                    raise e

    def first_follower_entry(self, retries=10):
        # //*[@id="content"]/div/div/div[2]/div/div/ul/li[contains(@class, "badgeList__item")][1]
        for try_n in range(1, retries + 1):
            try:
                return self.driver.find_element(
                    By.XPATH, '//*[@id="content"]/div/div/div[2]/div/div/ul/li[contains(@class, "badgeList__item")][1]')
            except (StaleElementReferenceException, TimeoutException, NoSuchElementException) as e:
                print("get_first_follower_entry, try {} of {}, raised exception: {}"
                      .format(try_n, retries, e))
                if try_n >= retries:
                    raise e

    def get_last_follower_entry(self, retries=10):
        for try_n in range(1, retries + 1):
            try:
                return self.driver.find_element(
                    By.XPATH,
                    '//*[@id="content"]/div/div/div[2]/div/div/ul/li[contains(@class, "badgeList__item")][last()]')
            except (StaleElementReferenceException, TimeoutException, NoSuchElementException) as e:
                print("get_last_follower_entry, try {} of {}, raised exception: {}"
                      .format(try_n, retries, e))
                if try_n >= retries:
                    raise e

    @staticmethod
    def follower_username(follower_entry):
        return follower_entry.find_element(By.XPATH, './div/div[2]/a')\
                   .get_attribute('href').rsplit('/', 1)[-1]

    @staticmethod
    def follower_button(follower_entry):
        return follower_entry.find_element(By.XPATH, './div/div[3]/button')

    @staticmethod
    def follower_image(follower_entry):
        image_element = follower_entry.find_element(By.XPATH, './div/div[1]/a/div/span')
        image_value = image_element.value_of_css_property('background-image')
        print("get_follower_image: image_value =", image_value)
        if image_value.startswith('url("https://'):
            return image_value[5:-2]
        return None

    @staticmethod
    def next_follower_entry(follower_entry, retries=10):
        for try_n in range(1, retries + 1):
            try:
                return follower_entry.find_element(By.XPATH, './following-sibling::li[1]')
            except (StaleElementReferenceException, TimeoutException, NoSuchElementException) as e:
                print("next_follower_entry, try {} of {}, raised exception: {}"
                      .format(try_n, retries, e))
                if try_n >= retries:
                    raise e

    def is_followers_end(self, follower_entry, retries=10):
        for try_n in range(1, retries + 1):
            try:
                # self.driver.implicitly_wait(0)
                last_entry = self.get_last_follower_entry()
                last_username = self.follower_username(last_entry)
                current_username = self.follower_username(follower_entry)
                print("is_last_follower_entry: {} == {}".format(current_username, last_username))
                return current_username == last_username
            except (StaleElementReferenceException, TimeoutException, NoSuchElementException) as e:
                print("is_last_follower_entry, try {} of {}, raised exception: {}"
                      .format(try_n, retries, e))
                if try_n >= retries:
                    raise e
            # finally:
            #   self.driver.implicitly_wait(self.implicit_default_wait)

    def is_following_blocked(self):
        try:
            # //*[@id="overlay_481"]/div/div/div/p[2]
            self.driver.implicitly_wait(0)
            blocked_p = self.driver.find_element(By.XPATH, '//*[starts-with(@id, "overlay_")]/div/div/div/p[2]')
            # //*[@id="overlay_481"]/div/div/div/p[5]
            blocked_warning = self.driver.find_element(By.XPATH, '//*[starts-with(@id, "overlay_")]/div/div/div/p[5]')
            print('is_following_blocked: block message:', blocked_warning.text)
            return blocked_p.text == "We have temporarily blocked your following facility because your account" \
                                     " has previously gotten this warning many times."
        except (StaleElementReferenceException, TimeoutException, NoSuchElementException) as e:
            return False
        finally:
            self.driver.implicitly_wait(self.implicit_default_wait)

    def profile_followers_link(self):
        # //*[@id="content"]/div/div[4]/div[2]/div/article[1]/table/tbody/tr/td[1]/a/h3[text()="Followers"]
        return self.driver.find_element(
            By.XPATH,
            '//*[@id="content"]/div/div[4]/div[2]/div/article[1]/table/tbody/tr/td[1]/a/h3[text()="Followers"]')

    def profile_following_link(self):
        return self.driver.find_element(
            By.XPATH,
            '//*[@id="content"]/div/div[4]/div[2]/div/article[1]/table/tbody/tr/td[2]/a/h3[text()="Following"]')

    def close_if_pro_lightbox(self):
        try:
            self.driver.implicitly_wait(5)
            pro_text = self.driver.find_element(By.XPATH, '/html/body/div/div/div/div/div[2]/h1')
            if pro_text == 'TRY PRO RISK-FREE':
                pro_x_button = self.driver.find_element(By.XPATH, '/html/body/div/a')
                if pro_x_button.get_attribute('href') == 'javascript:appboyBridge.closeMessage()':
                    pro_x_button.click()
        except (StaleElementReferenceException, TimeoutException, NoSuchElementException) as e:
            return None
        finally:
            self.driver.implicitly_wait(self.implicit_default_wait)

