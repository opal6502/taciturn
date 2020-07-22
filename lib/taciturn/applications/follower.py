
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


from taciturn.applications.base import (
    BaseApplicationHandler,
    AppUnexpectedStateException,
    AppEndOfListException,
    AppUserPrivilegeSuspendedException
)

from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from taciturn.db.followers import (
    Follower,
    Following,
    Unfollowed
)

from sqlalchemy import and_

from abc import abstractmethod
from datetime import datetime
from time import time


class FollowerApplicationHandler(BaseApplicationHandler):
    button_text_following = None
    button_text_not_following = None

    flist_prefix_xpath = None

    def __init__(self, app_account, handler_stats, driver=None):
        super().__init__(app_account, handler_stats, driver)

        config_name = 'app:'+self.application_name
        self.follow_back_hiatus = self.config[config_name]['follow_back_hiatus']
        self.unfollow_hiatus = self.config[config_name]['unfollow_hiatus']
        self.mutual_expire_hiatus = self.config[config_name]['mutual_expire_hiatus']

        self.flist_postition = 1  # using xpath indexing, starts from 1!
        self.flist_mode = None  # 'follower' or 'following'!

    @abstractmethod
    def goto_following_page(self, user_name=None):
        pass

    @abstractmethod
    def goto_followers_page(self, user_name=None):
        pass

    @abstractmethod
    def has_unfollow_confirm(self):
        "returns true or false if application has a lighbox with button to confirm unfollow"
        pass

    @abstractmethod
    def unfollow_confirm_button(self):
        pass

    # Database methods for FollowerApplicationHandler:

    def db_get_unfollowed(self, flist_username):
        return self.session.query(Unfollowed)\
                .filter(and_(Unfollowed.name == flist_username,
                             Unfollowed.user_id == self.app_account.user_id,
                             Unfollowed.application_id == self.app_account.application_id,
                        )).one_or_none()

    def db_get_follower(self, flist_username):
        return self.session.query(Follower)\
                .filter(and_(Follower.name == flist_username,
                             Follower.user_id == self.app_account.user_id,
                             Follower.application_id == self.app_account.application_id,
                        )).one_or_none()

    def db_get_following(self, flist_username):
        return self.session.query(Following)\
                .filter(and_(Following.name == flist_username,
                             Following.user_id == self.app_account.user_id,
                             Following.application_id == self.app_account.application_id,
                        )).one_or_none()

    def db_new_following(self, flist_username):
        return Following(name=flist_username,
                         established=datetime.now(),
                         application_id=self.app_account.application_id,
                         user_id=self.app_account.user_id)

    def db_new_unfollowed(self, flist_username):
        return Unfollowed(name=flist_username,
                          established=datetime.now(),
                          application_id=self.app_account.application_id,
                          user_id=self.app_account.user_id)

    def db_new_follower(self, flist_username):
        return Follower(name=flist_username,
                        established=datetime.now(),
                        application_id=self.app_account.application_id,
                        user_id=self.app_account.user_id)

    # Follower list 'flist' processing methods:

    def flist_wait_find_at_current(self,
                                   flist_entry=None,
                                   locator=None,
                                   timeout=60,
                                   text=False,
                                   get_attribute=None):

        end_time = time() + timeout
        while True:
            try:
                if get_attribute is not None:
                    return flist_entry.find_element(*locator).get_attribute(get_attribute)
                elif text is True:
                    return flist_entry.find_element(*locator).text
                else:
                    return flist_entry.find_element(*locator)
            except StaleElementReferenceException:
                flist_entry = self.new_wait()\
                    .until(EC.presence_of_element_located(self.flist_current_locator()))
            except NoSuchElementException:
                pass

            if time() > end_time:
                raise TimeoutException("Couldn't get element.")

    def flist_current_locator(self):
        if self.flist_mode == 'follower':
            locator = By.XPATH, self.flist_prefix_xpath.format('Followers', self.flist_get_position())
        if self.flist_mode == 'following':
            locator = By.XPATH, self.flist_prefix_xpath.format('Following', self.flist_get_position())
        else:
            locator = By.XPATH, self.flist_prefix_xpath.format(self.flist_get_position())
        self.log.debug("flist_current_locator: {}".format(locator))
        return locator

    def flist_reset_postition(self):
        self.flist_position = 1

    def flist_increment_position(self):
        self.flist_position += 1

    def flist_get_position(self):
        return self.flist_position

    @abstractmethod
    def flist_first_from_following(self):
        "get the first flist entry in a following flist; should set self.flist_mode = 'follower'"
        self.flist_reset_postition()
        self.flist_mode = 'follower'

    @abstractmethod
    def flist_first_from_followers(self):
        "get the first flist entry in a followers flist; should set self.flist_mode == 'following'"
        self.flist_reset_postition()
        self.flist_mode = 'following'

    @abstractmethod
    def flist_next(self, flist_entry):
        "get the next flist entry after flist_entry"
        self.flist_increment_position()

    @abstractmethod
    def flist_is_last(self, flist_entry):
        "return true if flist_entry is the last in the list"
        pass

    @abstractmethod
    def flist_is_empty(self, flist_entry):
        "return true if flist_entry is empty, used by twitter as end of list"
        pass

    @abstractmethod
    def flist_username(self, flist_entry):
        "returns the username text for flist_entry"
        pass

    @abstractmethod
    def flist_image_is_default(self, flist_entry):
        "returns true/false if the image is default"
        pass

    @abstractmethod
    def flist_is_verified(self, flist_entry):
        "returns true/false if the entry has a verified tag"
        pass

    @abstractmethod
    def flist_button(self, flist_entry):
        "returns the button element for flist_entry"
        pass

    @abstractmethod
    def flist_button_text(self, flist_entry):
        "returns the button text for flist_entry"
        pass

    @abstractmethod
    def flist_header_overlap_y(self):
        "returns the overlap y dimension of any elements overlapping the flist"
        pass

    @abstractmethod
    def flist_is_blocked_notice(self):
        "check if there's a notification that our follow request was blocked"
        pass

    @abstractmethod
    def flist_is_action_limit_notice(self):
        "check if there'a a notification that our account cannot follow now"
        pass

    def flist_button_is_following(self, flist_button_text):
        return flist_button_text in self.button_text_following

    def flist_button_is_not_following(self, flist_button_text):
        return flist_button_text in self.button_text_not_following

    def flist_button_wait_following(self, flist_entry):
        self.log.debug("Waiting for entry to be in following state.")
        # self.log.debug("self.button_text_following = {}".format(self.button_text_following))

        def _button_text_in_following(d):
            try:
                # self.log.debug("_button_text_in_following: getting button text ...")
                text = self.flist_button_text(flist_entry)
                result = text in self.button_text_following
                # self.log.debug("_button_text_in_following: text = '{}'".format(text))
                # self.log.debug("_button_text_in_following: result = {}".format(result))
            except Exception as e:
                self.log.exception("_button_text_in_following: exception occurred.")
                raise e
            return result

        return self.new_wait(timeout=90).until(_button_text_in_following)

    def flist_button_wait_not_following(self, flist_entry):
        self.log.debug("Waiting for entry to be in non-following state.")
        # self.log.debug("self.button_text_not_following = {}".format(self.button_text_not_following))

        def _button_text_in_not_following(d):
            try:
                # self.log.debug("_button_text_in_following: getting button text ...")
                text = self.flist_button_text(flist_entry)
                result = text in self.button_text_not_following
                # self.log.debug("_button_text_in_following: text = '{}'".format(text))
                # self.log.debug("_button_text_in_following: result = {}".format(result))
            except Exception as e:
                self.log.exception("_button_text_in_following: exception occurred.")
                raise e
            return result

        return self.new_wait(timeout=90).until(_button_text_in_not_following)

    def start_following(self, target_account, quota=None, unfollow_hiatus=None):
        "A generalized start_following method, made to be application-agnostic."
        self.log.info("Starting user following session.")
        self.log.debug("Following quota = {}".format(quota or 'n/a'))
        self.goto_followers_page(target_account)

        unfollow_hiatus = unfollow_hiatus or self.unfollow_hiatus
        header_overlap_y = self.flist_header_overlap_y()
        flist_entry = self.flist_first_from_followers()
        self.stats.reset_operation_count()
        self.stats.reset_failure_count()

        while quota is None or self.stats.get_operation_count() < quota:
            self.scrollto_element(flist_entry, y_offset=header_overlap_y)

            if self.flist_is_empty(flist_entry):
                raise AppEndOfListException("List end encountered, stopping.")

            # get flist info fields, skipping where possible:
            flist_username = self.flist_username(flist_entry)
            if self.in_blacklist(flist_username):
                self.log.info("User '{}' is in blacklist, skip.".format(flist_username))
                if self.flist_is_last(flist_entry):
                    raise AppEndOfListException("List end encountered, stopping.")
                flist_entry = self.flist_next(flist_entry)
                continue

            flist_button_text = self.flist_button_text(flist_entry)
            if self.flist_button_is_following(flist_button_text):
                self.log.info("User '{}' already following, skip.".format(flist_username))
                if self.flist_is_last(flist_entry):
                    raise AppEndOfListException("List end encountered, stopping.")
                flist_entry = self.flist_next(flist_entry)
                continue

            if self.flist_image_is_default(flist_entry):
                self.log.info("User '{}' has no image, skip.".format(flist_username))
                if self.flist_is_last(flist_entry):
                    raise AppEndOfListException("List end encountered, stopping.")
                flist_entry = self.flist_next(flist_entry)
                continue

            flist_unfollowed_row = self.db_get_unfollowed(flist_username)
            is_hiatus_expired = flist_unfollowed_row is not None \
                                and datetime.now() < flist_unfollowed_row.established + unfollow_hiatus
            if is_hiatus_expired:
                time_remaining = (flist_unfollowed_row.established + unfollow_hiatus) - datetime.now()
                self.log.info("User '{}' was followed/unfollowed too recently, can follow again after '{}'"
                                  .format(flist_username, time_remaining))
                if self.flist_is_last(flist_entry):
                    raise AppEndOfListException("List end encountered, stopping.")
                flist_entry = self.flist_next(flist_entry)
                continue

            # skip checks complete, now try to follow:

            if self.flist_button_is_not_following(flist_button_text):
                # check to see if we're already following this user in the db:
                # if it's already there, it's a good idea to put it in the unfollowed
                # list, because apparently we followed/unfollowed recently without
                # properly recording it?
                flist_following_row = self.db_get_following(flist_username)
                if flist_following_row is not None:
                    new_unfollowed_row = self.db_new_unfollowed(flist_username)

                    self.session.add(new_unfollowed_row)
                    self.session.delete(flist_following_row)
                    self.session.commit()

                    if self.flist_is_last(flist_entry):
                        raise AppEndOfListException("List end encountered, stopping.")
                    flist_entry = self.flist_next(flist_entry)
                    continue

                # check for follow limit popover ...
                if self.flist_is_action_limit_notice():
                    raise AppUserPrivilegeSuspendedException("Following limit encountered, stopping.")

                # ok, try clicking follow button ...
                self.last_action_pause()
                self.flist_button(flist_entry).click()
                self.last_action_mark()

                # check for follower fail conditions ...

                # check for follow blocked popover ...
                if self.flist_is_blocked_notice():
                    self.log.info("User '{}' blocks us, skipping ...".format(flist_username))
                    if self.flist_is_last(flist_entry):
                        raise AppEndOfListException("List end encountered, stopping.")
                    flist_entry = self.flist_next(flist_entry)
                    continue

                # check for follow limit popover ...
                if self.flist_is_action_limit_notice():
                    raise AppUserPrivilegeSuspendedException("Following limit encountered, stopping.")

                # verify that follow button indicates success:
                try:
                    self.log.debug("Waiting for user '{}' to be in following state."
                                     .format(flist_username))
                    self.flist_button_wait_following(flist_entry)
                except TimeoutException:
                    self.stats.one_operation_failed()
                    raise AppUserPrivilegeSuspendedException("Following seems to be restricted.")

                # follow verified, create database entry:

                new_following_row = self.db_new_following(flist_username)

                # if there was an unfollowed entry, remove it now:
                if flist_unfollowed_row is not None:
                    self.session.delete(flist_unfollowed_row)

                self.session.add(new_following_row)
                self.session.commit()
                self.log.info("Follow for user {} added to database.".format(flist_username))

                self.stats.one_operation_successful()

            elif self.flist_button_is_following(flist_button_text):
                # make sure following entry is in the database ...
                already_following_row = self.db_get_following(flist_username)
                if already_following_row is None:
                    new_following_row = self.db_new_following(flist_username)
                    self.session.add(new_following_row)
                    self.session.commit()
            else:
                self.log.critical("Entry button for user '{}' says '{}'?".format(flist_username, flist_button_text))
                raise AppUnexpectedStateException(
                    "Entry button for user '{}' says '{}'?".format(flist_username, flist_button_text))

            if self.flist_is_last(flist_entry):
                raise AppEndOfListException("List end encountered, stopping.")
            flist_entry = self.flist_next(flist_entry)

    def start_unfollowing(self, quota=None, follow_back_hiatus=None, mutual_expire_hiatus=None):
        self.log.info("Starting unfollow session.")
        self.log.debug("Unfollow quota = {}".format(quota or 'n/a'))
        self.goto_following_page()

        follow_back_hiatus = follow_back_hiatus or self.follow_back_hiatus
        mutual_expire_hiatus = follow_back_hiatus or self.mutual_expire_hiatus

        header_overlap_y = self.flist_header_overlap_y()
        flist_entry = self.flist_first_from_following()
        self.stats.reset_operation_count()
        self.stats.reset_failure_count()

        while quota is None or self.stats.get_operation_count() < quota:
            self.scrollto_element(flist_entry, y_offset=header_overlap_y)

            # twitter end-of-list detection:
            if self.flist_is_empty(flist_entry):
                raise AppEndOfListException("List end encountered, stopping.")

            # get flist info fields, skipping where possible:
            flist_username = self.flist_username(flist_entry)

            if self.in_whitelist(flist_username):
                self.log.info("User '{}' is in whitelist, skipping.".format(flist_username))
                if self.flist_is_last(flist_entry):
                    raise AppEndOfListException("List end encountered, stopping.")
                flist_entry = self.flist_next(flist_entry)
                continue

            flist_following_row = self.db_get_following(flist_username)

            if flist_following_row is None:
                self.log.warning("No following entry for user '{}', creating record and skipping."
                                   .format(flist_username))
                new_following = self.db_new_following(flist_username)
                self.session.add(new_following)
                self.session.commit()
                if self.flist_is_last(flist_entry):
                    raise AppEndOfListException("List end encountered, stopping.")
                flist_entry = self.flist_next(flist_entry)
                continue
            else:
                # get follower_row, can be None if user doesn't follow us:
                follower_row = self.db_get_follower(flist_username)

                follow_back_expired = datetime.now() > (flist_following_row.established + follow_back_hiatus)
                mutual_follow_expired = datetime.now() > (flist_following_row.established + mutual_expire_hiatus)

                if not mutual_follow_expired and follower_row:
                    time_remaining = (flist_following_row.established + mutual_expire_hiatus) - datetime.now()
                    self.log.info("Mutual expire hiatus for user '{}' not reached: '{}' left."
                                    .format(flist_username, time_remaining))
                    if self.flist_is_last(flist_entry):
                        raise AppEndOfListException("List end encountered, stopping.")
                    flist_entry = self.flist_next(flist_entry)
                    continue
                elif not follow_back_expired:
                    time_remaining = (flist_following_row.established + follow_back_hiatus) - datetime.now()
                    self.log.info("Follow back hiatus for user '{}' not reached: '{}' left."
                                    .format(flist_username, time_remaining))
                    if self.flist_is_last(flist_entry):
                        raise AppEndOfListException("List end encountered, stopping.")
                    flist_entry = self.flist_next(flist_entry)
                    continue

                if mutual_follow_expired and follower_row:
                    self.log.info("Mutual follow expired for user '{}', unfollowing."
                                    .format(flist_username))
                elif follow_back_expired:
                    self.log.info("Follow expired for user '{}', unfollowing."
                                    .format(flist_username))
                else:
                    AppUnexpectedStateException("Unfollow in unexpected state, please examine!")

                # check for follow/unfollow limit popover ...
                if self.flist_is_action_limit_notice():
                    raise AppUserPrivilegeSuspendedException("Following limit encountered, stopping.")

                self.last_action_pause()
                self.flist_button(flist_entry).click()
                self.last_action_mark()

                if self.has_unfollow_confirm():
                    unfollow_confirm_button = self.unfollow_confirm_button()
                    unfollow_confirm_button.click()

                try:
                    self.flist_button_wait_not_following(flist_entry)
                except TimeoutException:
                    self.stats.one_operation_failed()
                    raise AppUserPrivilegeSuspendedException("Unfollowing seems to be restricted.")

                # update database:
                new_unfollowed_row = self.db_new_unfollowed(flist_username)
                self.session.add(new_unfollowed_row)
                self.session.delete(flist_following_row)
                self.session.commit()

                self.stats.one_operation_successful()

            if self.flist_is_last(flist_entry):
                raise AppEndOfListException("List end encountered, stopping.")
            flist_entry = self.flist_next(flist_entry)

    def update_following(self):
        self.log.info("Updating following data.")
        self.goto_following_page()

        flist_entry = self.flist_first_from_following()
        entries_added = 0

        while True:
            if self.flist_is_empty(flist_entry):
                raise AppEndOfListException("List end encountered, stopping.")

            self.scrollto_element(flist_entry)

            flist_username = self.flist_username(flist_entry)
            flist_following_row = self.db_get_following(flist_username)
            if flist_following_row is None:
                self.log.info("Adding user '{}' to following list in db.".format(flist_username))
                new_following_row = self.db_new_following(flist_username)
                self.session.add(new_following_row)
                self.session.commit()
                entries_added += 1
            else:
                self.log.info("User '{}' already in following list in db.".format(flist_username))

            if self.flist_is_last(flist_entry):
                raise AppEndOfListException("List end encountered, stopping.")

            flist_entry = self.flist_next(flist_entry)

    def update_followers(self):
        self.log.info("Updating followers data.")
        self.goto_followers_page()

        flist_entry = self.flist_first_from_followers()
        entries_added = 0

        while True:
            if self.flist_is_empty(flist_entry):
                raise AppEndOfListException("List end encountered, stopping.")

            self.scrollto_element(flist_entry)

            flist_username = self.flist_username(flist_entry)
            flist_follower_row = self.db_get_follower(flist_username)
            if flist_follower_row is None:
                self.log.info("Adding '{}' to followers list in db.".format(flist_username))
                new_follower_row = self.db_new_follower(flist_username)
                self.session.add(new_follower_row)
                self.session.commit()
                entries_added += 1
            else:
                self.log.info("User '{}' already in followers list in db.".format(flist_username))

            if self.flist_is_last(flist_entry):
                raise AppEndOfListException("List end encountered, stopping.")

            flist_entry = self.flist_next(flist_entry)
