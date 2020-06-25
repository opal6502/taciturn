
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

from taciturn.applications.base import (
    FollowerApplicationHandler,
    ApplicationWebElements,
    AppLoginException,
    AppRetryLimitException)

from time import sleep


BUTTON_TEXT_FOLLOWING = ('Following', 'Requested')


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
        unfollow_hiatus = unfollow_hiatus or self.follow_back_hiatus
        followed_count = 0

        follower_entry = self.e.first_follower_entry()

        while quota is None or followed_count < quota:
            try:
                self.scrollto_element(follower_entry, offset=followers_list_offset)
                entry_username = self.e.follower_username(follower_entry).text
                entry_button_text = self.e.follower_button(follower_entry).text
                entry_image_src = self.e.follower_image(follower_entry).get_attribute('src')

                print("start_following: entry_username =", entry_username)
                print("start_following: entry_button_text =", entry_button_text)

                # already following, skip:1
                if entry_button_text in BUTTON_TEXT_FOLLOWING:
                    print("start_following: already following, skip ...")
                    # XXX cross reference with database here?
                    follower_entry = self.e.next_follower_entry(follower_entry)
                    continue

                entry_is_default_image = self.is_default_image(entry_image_src)
                if entry_is_default_image:
                    print("start_following: image is default, skip ...")
                    follower_entry = self.e.next_follower_entry(follower_entry)
                    continue

                print("start_following: entry_button_text default? ", entry_is_default_image)

            except (NoSuchElementException, StaleElementReferenceException):
                with open("instagram_entry.html", 'w') as entryfile:
                    print("Writing element innerHTML to entry.html!")
                    entryfile.write(follower_entry.get_attribute('innerHTML'))
                raise

            # sleep(5)
            follower_entry = self.e.next_follower_entry(follower_entry)

        return followed_count


    def old_start_following(self, target_username, quota=None):
        # start a follow task, get the next queued account to follow from,
        # load the page, and open the followers list, and go down the line,
        # following and making a db record for each follow ...
        # once we've tried to follow all followers for a target account, we
        # move on to the next target account!

        self.driver.get("{}/{}/".format(self.application_url, target_username))
        sleep(5)

        for retry_n in range(1, self.default_load_retries):
            # first navigate to target account page:
            sleep(5)  # this sleep seems to help the followers list from hanging?

            # find the followers link and click it:
            # <a><span>number</span> followers</a>
            # followers_link = self.driver.find_element(By.XPATH, "//a[contains(.,' followers')]")
            self.e.followers_link().click()

            # wait a minute until the followers list is properly populated:
            try:
                WebDriverWait(self.driver, timeout=60).until(
                    lambda x: self.e.follower_button())
            except TimeoutException:
                if retry_n > self.default_load_retries:
                    raise AppRetryLimitException("Could not load followers list after {} tries!".format(retry_n))
                print("Followers list load wait timeout, retrying ({} of {}) ...".format(
                    retry_n, self.default_load_retries))
                print("Retry timeout, waiting for {}s ...".format(self.default_load_retry_timeout))
                self.driver.get("{}/{}/".format(self.application_url, target_username))
                sleep(self.default_load_retry_timeout)
                continue  # retry followers load!
            break  # followers loaded ok!

        # popover_element = self.driver.switch_to.active_element
        # followers_container = self.driver.find_element(By.XPATH, '//div[@role="dialog"]/div/div[2]/ul/div')
        follower_xpath_prefix = '//div[@role="dialog"]/div/div[2]/ul/div'
        followers_container = self.driver.find_element(By.XPATH, follower_xpath_prefix)
        last_follower_n = 1
        follows_n = 0

        # print("followers_container HTML:", followers_container.get_attribute('outerHTML'))
        # followers_action = ActionChains(self.driver)
        # followers_action.move_to_element(followers_container)

        while True:
            print("In followers loop!")

            if quota is not None and follows_n > quota:
                print("Quota reached!  {} accounts followed!".format(last_follower_n))
                break

            # scrape all follower records and process:
            #while True:
            #    follower_entry = next(followers_list)  # will this work with infinte scrolling?
            # /html/body/div[6]/div/div/div[2]/ul/div/li[1]/div/div[1]/div[2]/div[1]/a

            follower_entry_xpath_prefix = follower_xpath_prefix + '/li[{}]'.format(last_follower_n)

            # try to grab the next element with a generous timeout, we're done scraping followers if this fails:
            try:
                follower_entry_element = self.e.follower_entry(last_follower_n)
                self.driver.execute_script("arguments[0].scrollIntoView(true);", follower_entry_element)
                WebDriverWait(self.driver, timeout=60).until(
                    lambda x: self.e.follower_entry(last_follower_n))
            except TimeoutException:
                print("Could not scan follower entry after timeout!")
                break

            # get the username, user image, and follow button elements, and extract key info:

            follower_username_element = self.e.follower_username(last_follower_n)
            follower_username_text = follower_username_element.text

            # if it's us the followers list, just skip it!
            if follower_username_text == self.app_username:
                last_follower_n += 1
                continue

            follower_image_element = self.e.follower_image(last_follower_n)
            follower_image_href = follower_image_element.get_attribute('src')

            follower_button_element = self.e.follower_button(last_follower_n)
            follower_button_text = follower_button_element.text

            print("Follower image:", follower_image_href)
            if self.is_default_image(follower_image_href):
                print("*** is default image ***")
            print("Follower username:", follower_username_text)
            print("Follower button:", follower_button_text)
            print()

            # now, check if we want to click follow!
            if follower_button_text == 'Follow' \
                    and not self.is_default_image(follower_image_href):
                follower_button_element.click() # -- debug!

                # then ... wait and verify that button text changes to 'Following' or 'Requested' ...
                WebDriverWait(self.driver, timeout=60).until(self.e.follow_click_verify_cb(last_follower_n))

                # XXX record followed new user in database here!
                follows_n += 1
                sleep()

            last_follower_n += 1
            sleep(1)  # give the new content a chance to load

    def update_followers(self):
        self.goto_user_page()

    def start_unfollow(self):
        # start an unfollow task, navigate to our follower list, and scan for
        # non-mutual followers that we've been folloing for longer than mutual
        # duration ... and then unfollow them!
        pass

    def update_following(self):
        pass


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

    def next_follower_entry(self, follower_entry):
        return follower_entry.find_element(By.XPATH, './following-sibling::li[1]')

    def _follower_entry_xpath_prefix(self, n=1):
        return self.follower_xpath_prefix + '/li[{}]'.format(n)

    def followers_link(self):
        return self.driver.find_element(
            By.XPATH,
            "//a[contains(.,' followers')]")

    def follower_entry(self, n=1):
        return self.driver.find_element(
            By.XPATH,
            self._follower_entry_xpath_prefix(n))

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