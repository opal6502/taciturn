
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

from taciturn.applications.base import (
    FollowerApplicationHandler,
    ApplicationWebElements,
    AppLoginException
)


class SoundcloudHandler(FollowerApplicationHandler):
    application_name = 'soundcloud'

    application_url = "https://soundcloud.com"
    application_login_url = application_url

    application_asset_dirname = 'soundcloud'
    # default_profile_image = 'default-profile-pic.jpg'

    follow_random_wait = (10, 60)

    def __init__(self, db_session, app_account, elements=None):
        super().__init__(db_session, app_account, SoundcloudHandlerWebElements)

        self.follow_back_hiatus = self.config['app:soundcloud']['follow_back_hiatus']
        self.unfollow_hiatus = self.config['app:soundcloud']['unfollow_hiatus']
        self.action_timeout = self.config['app:soundcloud']['action_timeout']

        # self.goto_homepage()

    def goto_homepage(self):
        self.driver.get(self.application_url)

    def goto_user_page(self):
        self.driver.get("{}/{}/".format(self.application_url, self.app_username))

    def login(self):
        self.goto_homepage()

        # get sign in button:
        # xpath=//div[@id='content']/div/div/div/div/div[2]/button
        # css=.frontHero__loginButton
        sign_in_button = self.driver.find_element(
            By.CSS_SELECTOR, 'button.frontHero__loginButton:first-child')
        sign_in_button.click()

        # xpath=//input[@id='sign_in_up_email']
        username_field = self.driver.find_element(
            By.CSS_SELECTOR, 'input#sign_in_up_email')
        username_field.send_keys(self.app_username)

        # button#sign_in_up_submit
        continue_button = self.driver.find_element(
            By.CSS_SELECTOR, 'button#sign_in_up_submit')
        continue_button.click()

        password_field = self.driver.find_element(
            By.CSS_SELECTOR, 'input#enter_password_field')
        password_field.send_keys(self.app_password)

        # button#enter_password_submit
        continue_button = self.driver.find_element(
            By.CSS_SELECTOR, 'button#enter_password_submit')
        continue_button.click()

        # use the 'Messages' element to verify login!
        # //*[@id="app"]/header/div/div[3]/div[2]/a[3]/div/span[contains(.,"Messages")]
        self.driver.find_element(
            By.XPATH, '//*[@id="app"]/header/div/div[3]/div[2]/a[3]/div/span[contains(.,"Messages")]')

        print("Logged in!")

    def start_following(self, target_account, quota=None, unfollow_hiatus=None):
        pass

    def start_unfollowing(self, quota=None, follow_back_hiatus=None):
        pass

    def update_following(self):
        pass

    def update_followers(self):
        pass


class SoundcloudHandlerWebElements(ApplicationWebElements):
    pass