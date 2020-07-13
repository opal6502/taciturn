
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

from sqlalchemy import and_

from time import sleep
from datetime import datetime

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

from taciturn.db.base import (
    User,
    Application,
)

BUTTON_TEXT_FOLLOWING = ('Following', 'Pending', 'Cancel', 'Unfollow')
BUTTON_TEXT_NOT_FOLLOWING = ('Follow',)
DEBUG_HALT_EXCEPTION = False


class TwitterHandler(FollowerApplicationHandler):
    application_name = 'twitter'

    application_url = "https://twitter.com"
    application_login_url = "https://twitter.com/login"

    application_asset_dirname = 'twitter'
    default_profile_image = 'default_profile_reasonably_small.png'

    follow_random_wait = (10, 60)

    def __init__(self, logger, options, db_session, app_account, driver=None, elements=None):
        super().__init__(logger, options, db_session, app_account, driver, TwitterHandlerWebElements)
        self.log.info('Starting twitter app handler.')

        self.follow_back_hiatus = self.config['app:twitter']['follow_back_hiatus']
        self.unfollow_hiatus = self.config['app:twitter']['unfollow_hiatus']
        self.action_timeout = self.config['app:twitter']['action_timeout']
        self.mutual_expire_hiatus = self.config['app:twitter']['mutual_expire_hiatus']

        self.init_webdriver()
        self.goto_homepage()

    def goto_homepage(self):
        homepage_link = self.application_url + '/home'
        self.log.info('Going to home page: {}'.format(homepage_link))
        self.driver.get(homepage_link)

    def goto_user_page(self):
        self.driver.get(self.application_url + '/home')
        profile_link = self.e.home_profile_link().get_attribute('href')
        self.log.info('Going to page: {}'.format(profile_link))
        self.driver.get(profile_link)

    def goto_following_page(self, target_account=None):
        if target_account is None:
            self.log.info('Going to our following page.')
            self.goto_user_page()
            locator = (By.XPATH, '//*[@id="react-root"]//div[1]/a/span[2]/span[text()="Following"]')
            self.new_wait(self.driver, timeout=60)\
                   .until(EC.presence_of_element_located(locator)).click()
        else:
            target_link = '{}/{}/following'.format(self.application_url, target_account)
            self.log.info('Going to page: {}'.format(target_link))
            self.driver.get(target_link)

    def goto_followers_page(self, target_account=None):
        if target_account is None:
            self.log.info('Going to our followers page.')
            self.goto_user_page()
            locator = (By.XPATH, '//*[@id="react-root"]//div[2]/a/span[2]/span[text()="Followers"]')
            self.new_wait(self.driver, timeout=60)\
                   .until(EC.presence_of_element_located(locator)).click()
        else:
            target_link = '{}/{}/followers'.format(self.application_url, target_account)
            self.log.info('Going to page: {}'.format(target_link))
            self.driver.get(target_link)

    def login(self):
        # enter username and password:
        self.driver.get(self.application_login_url)

        self.e.login_username_input().send_keys(self.app_username)
        self.e.login_password_input().send_keys(self.app_password)
        self.e.login_button().click()
        # use this to verify login ...
        self.e.home_profile_link()
        
        self.log.info('Logged in.')

    def start_following(self, target_account, quota=None, unfollow_hiatus=None):
        print("start_following: starting up ...")
        # for a bit of misdirection ;)
        # self.goto_homepage()
        # sleep(2)
        # self.goto_user_page()
        # sleep(2)
        self.driver.get("{}/{}".format(self.application_url, target_account))
        sleep(2)

        print("start_following: going to target account ...")

        # ... then get the page we want:
        self.driver.get("{}/{}/followers".format(self.application_url, target_account))

        # self.e.followers_tab_link()
        tab_overlap_y = self.e.followers_tab_overlap()

        unfollow_hiatus = unfollow_hiatus or self.unfollow_hiatus
        # max_scan_count = 10
        followed_count = 0

        follower_entry = self.e.first_follower_entry()
        print("follower_entry =", follower_entry)

        while quota is None or followed_count < quota:

            self.scrollto_element(follower_entry, offset=tab_overlap_y)
            if self.e.is_followers_end(follower_entry):
                print("List end encountered, stopping. (top)")
                if DEBUG_HALT_EXCEPTION:
                    raise RuntimeError("Stopping execution!")
                return followed_count

            # extract entry fields, continue'ing asap to avoid unnecessary work ...

            entry_username = self.e.follower_username(follower_entry).text

            # check to see if we've unfollowed this user within the unfollow_hiatus time:
            unfollowed = self.session.query(Unfollowed).filter(
                                            and_(Unfollowed.name == entry_username,
                                                 Unfollowed.user_id == self.app_account.user_id,
                                                 Unfollowed.application_id == Application.id,
                                                 Application.name == self.application_name))\
                                            .one_or_none()
            if unfollowed is not None and datetime.now() < unfollowed.established + self.unfollow_hiatus:
                time_remaining = (unfollowed.established + self.unfollow_hiatus) - datetime.now()
                print("Followed/unfollowed too recently, can follow again after", time_remaining)
                follower_entry = self.e.next_follower_entry(follower_entry)
                continue

            # self.scrollto_element(follower_entry, offset=tab_overlap_y)

            if self.in_blacklist(entry_username):
                print("{} is in blacklist, skip ...")
                follower_entry = self.e.next_follower_entry(follower_entry)
                continue

            entry_button = self.e.follower_button(follower_entry)
            # already following, skip:1
            if entry_button.text in BUTTON_TEXT_FOLLOWING:
                print("start_following: already following, skip ...")
                # XXX cross reference with database here?
                follower_entry = self.e.next_follower_entry(follower_entry)
                continue
            # default image, skip:
            entry_image_src = self.e.follower_image(follower_entry).get_attribute('src')
            entry_is_default_image = self.is_default_image(entry_image_src)
            if entry_is_default_image:
                print("start_following: image is default, skip ...")
                follower_entry = self.e.next_follower_entry(follower_entry)
                continue

            entry_button_text = entry_button.text

            print("start_following: entry_username =", entry_username)
            print("start_following: entry_button_text =", entry_button_text)
            print("start_following: entry_button_text default? ", entry_is_default_image)

            # try to follow:
            if entry_button_text in BUTTON_TEXT_NOT_FOLLOWING:
                print("start_following: checking records before following ...")
                # check to see if we're already (supposed to be following) this user:
                already_following = self.session.query(Following) \
                    .filter(and_(Following.name == entry_username,
                                 Following.user_id == self.app_account.user_id,
                                 Following.application_id == self.app_account.application_id)) \
                    .one_or_none()
                # if we find a record, it's contradicting what twitter is telling us, so delete it:
                # XXX this probably means a locked account has refused our request, and we should
                # add it to unfollowed for a long timeout ...
                if already_following is not None:
                    print("Warning: not followed user '{}' already recorded as following?"
                          "  Moving to unfollowed.".format(entry_username))

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

                # XXX bug: if the blocked notify shows up, it will stay here for several seconds
                # and followers below that entry will show up as blocked unless we wait for the blocked
                # popover to go away.
                if self.e.is_follower_blocked_notify_present():
                    print("Blocked by user.")
                    WebDriverWait(self.driver, timeout=60).until(self.e.blocked_notice_gone_cb())
                    follower_entry = self.e.next_follower_entry(follower_entry)
                    continue

                if self.e.is_follower_limit_notify_present():
                    print("Unable to follow more at this time!")
                    return followed_count

                # verify follow button indicates follow was successful ...
                for try_n in range(1, self.default_load_retries+1):
                    try:
                        button_text = self.e.follower_button(follower_entry).text
                        if button_text in BUTTON_TEXT_FOLLOWING:
                            print("Follow verified.")
                            break
                    except (NoSuchElementException, StaleElementReferenceException) as e:
                        if try_n == self.default_load_retries:
                            print("Follow button not verified, returning!")
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

            elif entry_button_text in BUTTON_TEXT_FOLLOWING:
                # do nothing!
                pass
            else:
                raise AppUnexpectedStateException(
                    "Entry button for '{}' says '{}'?".format(entry_username, entry_button.text))

            self.sleepmsrange(self.action_timeout)
            follower_entry = self.e.next_follower_entry(follower_entry)

        return followed_count

    def update_followers(self):
        # print(" GET {}/{}/following".format(self.application_url, self.app_username))
        self.goto_followers_page()

        follower_entry = self.e.first_follower_entry()
        print("follower_entry =", follower_entry)
        entries_added = 0

        while True:
            # check to see if this looks like the end:
            if self.e.is_followers_end(follower_entry):
                print("List end encountered, stopping.")
                if DEBUG_HALT_EXCEPTION:
                    raise RuntimeError("Stopping execution!")
                    return entries_added

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

            follower_entry = self.e.next_follower_entry(follower_entry)
            # try:
            #     follower_entry = self.e.next_follower_entry(follower_entry)
            # except NoSuchElementException:
            #     break

    def update_following(self):
        # print(" GET {}/{}/following".format(self.application_url, self.app_username))
        self.goto_following_page()

        following_entry = self.e.first_following_entry()
        print("following_entry =", following_entry)
        entries_added = 0

        while True:
            if self.e.is_followers_end(following_entry):
                print("List end encountered, stopping.")
                if DEBUG_HALT_EXCEPTION:
                    raise RuntimeError("Stopping execution!")
                return entries_added

            # check to see if entry is in the database:
            self.scrollto_element(following_entry)

            following_username = self.e.follower_username(following_entry).text
            print("Scanning {} ...".format(following_username))

            following_db = self.session.query(Following)\
                                    .filter(and_(Following.user_id == self.app_account.user_id,
                                                 Following.application_id == self.app_account.application_id,
                                                 Following.name == following_username
                                            )).one_or_none()

            if following_db is None:
                print("No entry for '{}', creating.".format(following_username))
                new_following = Following(name=following_username,
                                          established=datetime.now(),
                                          application_id=self.app_account.application_id,
                                          user_id=self.app_account.user_id)
                self.session.add(new_following)
                self.session.commit()
                entries_added += 1

            follower_entry = self.e.next_follower_entry(following_entry)

    def start_unfollowing(self, quota=None, follow_back_hiatus=None, mutual_expire_hiatus=None):
        # print(" GET {}/{}/following".format(self.application_url, self.app_username))
        self.goto_following_page()

        following_entry = self.e.first_following_entry()
        print("following_entry =", following_entry)
        unfollow_count = 0
        follow_back_hiatus = follow_back_hiatus or self.follow_back_hiatus
        mutual_expire_hiatus = mutual_expire_hiatus or self.mutual_expire_hiatus
        tab_overlap_y = self.e.followers_tab_overlap()

        print("start_unfollowing, mutual_expire_hiatus =", mutual_expire_hiatus)
        print("start_unfollowing, follow_back_hiatus =", follow_back_hiatus)

        while quota is None or quota > unfollow_count:
            if self.e.is_followers_end(following_entry):
                print("List end encountered, stopping. (top)")
                if DEBUG_HALT_EXCEPTION:
                    raise RuntimeError("Stopping execution!")
                return unfollow_count

            self.scrollto_element(following_entry, offset=tab_overlap_y)

            following_username = self.e.follower_username(following_entry).text
            print("Scanning {} ...".format(following_username))

            # if in whitelist, skip ...
            if self.in_whitelist(following_username):
                print("'{}' in whitelist, skipping ...".format(following_username))
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
                following_entry = self.e.next_follower_entry(following_entry)
                continue
            # follow in db, check and delete, if now > then + hiatus time ...
            else:
                follows_me = self.e.follower_follows_me(following_entry)

                follow_back_expired = datetime.now() > following_db.established + follow_back_hiatus
                mutual_follow_expired = datetime.now() > following_db.established + mutual_expire_hiatus

                if not mutual_follow_expired and follows_me:
                    time_remaining = (following_db.established + mutual_expire_hiatus) - datetime.now()
                    print("Mutual expire hiatus not reached!  {} left!".format(time_remaining))
                    following_entry = self.e.next_follower_entry(following_entry)
                    continue
                elif not follow_back_expired:
                    time_remaining = (following_db.established + follow_back_hiatus) - datetime.now()
                    print("Follow hiatus not reached!  {} left!".format(time_remaining))
                    following_entry = self.e.next_follower_entry(following_entry)
                    continue

                if mutual_follow_expired and follows_me:
                    print("Mutual follow expired, unfollowing ...")
                elif follow_back_expired:
                    print("Follow expired, unfollowing ...")
                else:
                    AppUnexpectedStateException("Unfollow in unexpected state, please examine!")

                list_following_button = self.e.follower_button(following_entry)
                list_following_button_text = list_following_button.text
                if list_following_button_text not in BUTTON_TEXT_FOLLOWING:
                    raise AppUnexpectedStateException(
                        "Unfollow button for '{}' says '{}'?".format(following_username,
                                                                     list_following_button_text))
                list_following_button.click()
                lb_following_button = self.e.unfollow_lightbox_button()
                lb_following_button.click()

                # we need to wait and make sure button goes back to unfollowed state ...
                WebDriverWait(following_entry, 60).until(
                    lambda e: self.e.follower_button(e).text in BUTTON_TEXT_NOT_FOLLOWING)

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

            following_entry = self.e.next_follower_entry(following_entry)

        return unfollow_count

    def post_tweet(self, tweet_body, tweet_image=None):
        compose_tweet_button = self.driver.find_element(By.XPATH, '//a[@href="/compose/tweet" and @role="button"]')
        compose_tweet_button.click()

        tweet_text_input = self.driver.find_element(By.XPATH, '//div[@aria-label="Tweet text"]')
        truncated_tweet_body = self.truncate_tweet(tweet_body)
        tweet_text_input.send_keys(truncated_tweet_body)
        tweet_text_input.send_keys(Keys.ESCAPE)

        if tweet_image is not None:
            tweet_image_input = self.driver.find_element(
                By.XPATH, '//div[@aria-label="Add photos or video"]/following-sibling::input[@type="file"]')
            tweet_image_input.send_keys(tweet_image)

            # //div[@aria-label="Media" and @role="group"]//img
            tweet_image_attached = '//div[@aria-label="Media" and @role="group"]//img'
            WebDriverWait(self.driver, timeout=60)\
                .until(EC.presence_of_element_located((By.XPATH, tweet_image_attached)))

        submit_tweet_button = self.driver.find_element(
            By.XPATH, '//div[@role="button"]//span[text()="Tweet"]')
        self.scrollto_element(submit_tweet_button)
        submit_tweet_button.click()

        # wait for the lightbox (x) to dissapear, to verify tweet sent ...
        tweet_xbutton = self.driver.find_element(
            By.XPATH, '//div[@aria-label="Close" and @role="button"]/div[@dir="auto"]')
        WebDriverWait(self.driver, timeout=60).until(EC.staleness_of(tweet_xbutton))

    @staticmethod
    def truncate_tweet(tweet_text):
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
        print("truncate_tweet: len(tweet_text) =", len(tweet_text))
        print("truncate_tweet: scan_position =", scan_position)
        print("truncate_tweet: effective_tweet_length =", effective_tweet_length)
        print("truncate_tweet: last_scanned_space =", last_scanned_space)

        if effective_tweet_length <= tweet_limit:
            return tweet_text
        elif last_scanned_space > 0:
            # truncate at last word!
            return tweet_text[:last_scanned_space]
        else:
            raise ValueError("Couldn't truncate body string for twitter!")

    # XXX NEW 0.2a flist METHODS!

    def flist_first(self, flist_name='Following'):
        super().flist_first(flist_name)
        locator = (By.XPATH, '//section[starts-with(@aria-labelledby, "accessible-list-")]'
                             '/div[@aria-label="Timeline: {}"]/div/div/div[1]'.format(flist_name))
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
        self.new_wait(timeout=30)\
                .until(EC.presence_of_element_located(empty_locator))
        return True

    def flist_username(self, flist_entry):
        locator = self._flist_username_locator()
        return self.new_wait(flist_entry).until(EC.presence_of_element_located(locator)).text

    def _flist_username_locator(self):
        return (By.XPATH, './div/div/div/div[2]/div/div[1]/a/div/div[2]/div/span[starts-with(text(), "@")] | '
                     './div/div/div/div[2]/div/div[1]/a/div/div/div[1]/span/span[starts-with(text(), "@")]')

    def flist_image_is_default(self, flist_entry):
        locator = (By.XPATH, './div/div/div/div[1]/div/a/div[1]/div[2]/div/img')
        image_src = self.new_wait(flist_entry).until(EC.presence_of_element_located(locator)).get_attribute('src')
        return self.is_default_image(image_src)

    def flist_is_verified(self, flist_entry):
        locator = (By.XPATH, './div/div/div/div[2]/div[1]/div[1]/a/div/div[1]/div[2]/'
                             '*[local-name() = "svg" and @aria-label="Verified account"]')
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

    def flist_header_overlap_y(self):
        header_locator = (By.XPATH, '(//div[@data-testid="primaryColumn"]/div/div)[1]')
        header_element = self.new_wait().until(EC.presence_of_element_located(header_locator))
        return header_element.size['height']

    def flist_is_blocked_notice(self):
        popover = self._bottom_notify_popover()
        if popover is None:
            return False
        popover_text = popover.text
        if popover_text is not None and popover_text == 'You have been blocked from following this user at their request.':
            # halt and wait until the blocked notice disappers, so it doesn't confuse us later:
            self.new_wait().until(EC.staleness_of(popover))
            return True
        return False

    def flist_is_follow_limit_notice(self):
        popover = self._bottom_notify_popover()
        if popover is None:
            return False
        popover_text = popover.text
        if popover_text is not None and popover_text == 'You are unable to follow more people at this time.':
            return True
        return False

    def _bottom_notify_popover(self):
        locator = (By.XPATH, '//*[@id="react-root"]/div/div/div[1]/div[2]/div/div/div[1]/span')
        try:
            return self.new_wait(timeout=0).until(EC.presence_of_element_located(locator))
        except TimeoutException:
            return None


class TwitterHandlerWebElements(ApplicationWebElements):
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

# twitter specific exceptions:

class TwitterFollowLimitException(AppActivityLimitException):
    pass
