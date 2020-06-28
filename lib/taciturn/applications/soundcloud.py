
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

    def __init__(self, options, db_session, app_account, elements=None):
        super().__init__(options, db_session, app_account, SoundcloudHandlerWebElements)

        self.follow_back_hiatus = self.config['app:soundcloud']['follow_back_hiatus']
        self.unfollow_hiatus = self.config['app:soundcloud']['unfollow_hiatus']
        self.action_timeout = self.config['app:soundcloud']['action_timeout']

        self.init_webdriver()

        if options.cookies:
            self.load_cookies(options.cookies[0])

        # self.goto_homepage()

    def goto_homepage(self):
        self.driver.get(self.application_url)

    def goto_user_page(self):
        # navigate using the ui ... to accommodate google user email login ;)
        self.e.header_profile_menu().click()
        self.e.header_profile_menu_profile_link().click()

    def login(self):
        self.goto_homepage()

        sign_in_button = self.driver.find_element(
            By.CSS_SELECTOR, r'button.frontHero__loginButton:first-child')
        sign_in_button.click()

        # switch to login iframe:
        login_iframe = self.driver.find_element(By.XPATH, '//iframe[@class="webAuthContainer__iframe"]')
        self.driver.switch_to.frame(login_iframe)

        user_google_button = self.driver.find_element(
            By.CSS_SELECTOR, r'button.google-plus-signin')
        user_google_button.click()

        # switch to google login popup:

        main_window = self.driver.current_window_handle
        google_login_popup = None
        for wh in self.driver.window_handles:
            if wh != main_window:
                google_login_popup = wh

        self.driver.switch_to.window(google_login_popup)

        # enter google username:
        google_name_field = self.driver.find_element(By.XPATH, '//input[@id="identifierId"]')
        google_name_field.send_keys(self.app_account.name)

        # click 'Next' button:
        # //*[@id="identifierNext"]/div/span/span[text() = "Next"]
        google_next_button = self.driver.find_element(By.XPATH, '//*[@id="identifierNext"]/div/span/span[text() = "Next"]')
        google_next_button.click()

        # enter password:
        # //input[@name="password"]
        google_password_field = self.driver.find_element(By.XPATH, '//input[@name="password"]')
        google_password_field.send_keys(self.app_account.password)

        # click the 'Next' button:
        # //*[@id="passwordNext"]/div/span/span[text() = "Next"]
        google_next_button = self.driver.find_element(By.XPATH, '//*[@id="passwordNext"]/div/span/span[text() = "Next"]')
        google_next_button.click()

        # switch back to the main window:
        self.driver.switch_to.window(main_window)

        # use the 'Messages' element to verify login!
        # //*[@id="app"]/header/div/div[3]/div[2]/a[3]/div/span[contains(.,"Messages")]
        self.driver.find_element(
            By.XPATH, r'//*[@id="app"]/header/div/div[3]/div[2]/a[3]/div/span[contains(.,"Messages")]')

        print("Logged in!")

        # self.goto_user_page()

    def start_following(self, target_account, quota=None, unfollow_hiatus=None):
        self.driver.get(self.application_url+'/'+target_account+'/followers')

        # scan the header menu overhang:
        header_menu_offset = self.e.followers_header_overlap()
        # get the first follower entry:
        follower_entry = self.e.get_first_follower_entry()
        followed_count = 0

        while quota is None or followed_count < quota:
            self.scrollto_element(follower_entry, offset=header_menu_offset)

            entry_username = self.e.get_follower_username(follower_entry)

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

            entry_image = self.e.get_follower_image(follower_entry)
            entry_button = self.e.get_follower_button(follower_entry)
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

                WebDriverWait(self.driver, timeout=90)\
                    .until(lambda x: self.e.get_follower_button(follower_entry).text in BUTTON_TEXT_FOLLOWING)

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

            follower_entry = self.e.next_follower_entry(follower_entry)

        return followed_count

    def start_unfollowing(self, quota=None, follow_back_hiatus=None):
        pass

    def update_following(self):
        pass

    def update_followers(self):
        pass


class SoundcloudHandlerWebElements(ApplicationWebElements):

    def header_profile_menu(self):
        return self.driver.find_element(
                                By.XPATH,
                                '//*[@id="app"]/header/div/div[3]/div[2]/a[1]/div[2]/div/span')

    def header_profile_menu_profile_link(self):
        return self.driver.find_element(
                                By.XPATH,
                                '//*[@id="dropdown-button-350"]/div/ul[1]/li[1]/a[text() = "Profile"]')

    def followers_header_overlap(self):
        # followers menu section:
        # //*[@id="content"]/div/div/div[1]
        followers_menu_section = self.driver.find_element(By.XPATH, '//*[@id="content"]/div/div/div[1]')
        offset_script = """
        var rect = arguments[0].getBoundingClientRect();
        return rect.bottom;
        """
        followers_menu_bottom = self.driver.execute_script(offset_script, followers_menu_section)
        return int(followers_menu_bottom)

    def get_first_follower_entry(self):
        # //*[@id="content"]/div/div/div[2]/div/div/ul/li[contains(@class, "badgeList__item")][1]
        return self.driver.find_element(
            By.XPATH,'//*[@id="content"]/div/div/div[2]/div/div/ul/li[contains(@class, "badgeList__item")][1]')

    def get_last_follower_entry(self):
        return self.driver.find_element(
            By.XPATH,'//*[@id="content"]/div/div/div[2]/div/div/ul/li[contains(@class, "badgeList__item")][last()]')

    @staticmethod
    def get_follower_username(follower_entry):
        return follower_entry.find_element(By.XPATH, './div/div[2]/a')\
                   .get_attribute('href').rsplit('/', 1)[-1]

    @staticmethod
    def get_follower_button(follower_entry):
        return follower_entry.find_element(By.XPATH, './div/div[3]/button')

    @staticmethod
    def get_follower_image(follower_entry):
        image_element = follower_entry.find_element(By.XPATH, './div/div[1]/a/div/span')
        image_value = image_element.value_of_css_property('background-image')
        print("get_follower_image: image_value =", image_value)
        if image_value.startswith('url("https://'):
            return image_value[5:-2]
        return None

    @staticmethod
    def next_follower_entry(follower_entry):
        return follower_entry.find_element(By.XPATH, './following-sibling::li[1]')

    def is_last_follower_entry(self, follower_entry):
        last_entry = self.get_last_follower_entry()
        last_username = self.get_follower_username(last_entry)
        current_username = self.get_follower_username(follower_entry)
        print("is_last_follower_entry: {} == {}".format(current_username, last_username))
        return current_username == last_username