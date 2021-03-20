
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


import random
from time import sleep

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    ElementNotInteractableException
)

from taciturn.applications.base import ApplicationHandlerException
from taciturn.applications.login import LoginApplicationHandler
from taciturn.applications.google import GoogleLoginMixin

YOUTUBE_COMMENT_RETRIES=20
YOUTUBE_HEADER_PADDING=60


class YoutubeHandler(LoginApplicationHandler, GoogleLoginMixin):
    application_name = 'facebook'

    application_url = "https://youtube.com"
    application_login_url = "https://accounts.google.com/ServiceLogin"

    def __init__(self, app_account, handler_stats=None, driver=None):
        super().__init__(app_account, handler_stats, driver)

    def login(self):
        self._google_login_headed_mode()
        # self._google_login()
        self.driver.get(self.application_url)

    def goto_homepage(self):
        self._sidebar_home_link().click()

    def goto_profile_page(self):
        self._avatar_button().click()

        your_channel_link_locator = (By.XPATH, '//*[@id="label" and text() = "Your channel"]')
        self.new_wait().until(EC.element_to_be_clickable(your_channel_link_locator))\
            .click()

    def _avatar_button(self):
        locator = (By.XPATH, '//button[@id="avatar-btn"]')
        return self.new_wait().until(EC.element_to_be_clickable(locator))

    def _sidebar_home_link(self):
        locator = (By.XPATH, '//*[@id="endpoint"]/span[text() = "Home"]')
        return self.new_wait().until(EC.element_to_be_clickable(locator))

    def _sidebar_subscriptions_link(self):
        locator = (By.XPATH, '//*[@id="endpoint"]/span[text() = "Subscriptions"] | '
                             '//*[@id="endpoint"]/*[local-name() = "paper-item"]'
                             '/*[local-name() = "yt-formatted-string"][text()="Subscriptions"]')
        return self.new_wait().until(EC.element_to_be_clickable(locator))

    def _subscriptions_first_dayframe(self):
        locator = (By.XPATH, '//div[@id="primary"]/*[local-name() = "ytd-section-list-renderer"]'
                             '/div[@id="contents"]/*[local-name() = "ytd-item-section-renderer"][1]')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    def _subscriptions_next_dayframe(self, current_dayframe):
        locator = (By.XPATH, './following-sibling::*[local-name() = "ytd-item-section-renderer"][1]')
        return self.new_wait(current_dayframe).until(EC.presence_of_element_located(locator))

    def _subscriptions_dayframe_first_entry(self, current_dayframe):
        locator = (By.XPATH, './/*[local-name() = "ytd-grid-video-renderer"][1]')
        return self.new_wait(current_dayframe).until(EC.presence_of_element_located(locator))

    def _subscriptions_dayframe_next_entry(self, current_entry):
        locator = (By.XPATH, './following-sibling::*[local-name() = "ytd-grid-video-renderer"][1]')
        return self.new_wait(current_entry).until(EC.presence_of_element_located(locator))

    def _subscriptions_dayframe_is_last_entry(self, current_dayframe, current_entry):
        locator = (By.XPATH, './/*[local-name() = "ytd-grid-video-renderer"][last()]')
        last_entry = self.new_wait(current_dayframe).until(EC.presence_of_element_located(locator))
        return current_entry == last_entry

    def _subscriptions_dayframe_entry_title(self, current_entry):
        locator = (By.XPATH, './/a[@id="video-title"]')
        return self.new_wait(current_entry).until(EC.presence_of_element_located(locator))

    def _subscriptions_dayframe_entry_is_live_now(self, current_entry):
        locator = (By.XPATH, './/*[text() = "LIVE NOW"]')
        try:
            current_entry.find_element(*locator)
            return True
        except NoSuchElementException:
            return False

    def _video_thumbs_up_button(self):
        locator = (By.XPATH, '//div[@id="top-level-buttons"]/*[local-name() = "ytd-toggle-button-renderer"][1]')
        return self.new_wait().until(EC.element_to_be_clickable(locator))

    def _video_thumbs_up_is_pressed(self):
        locator = (By.XPATH, '//div[@id="top-level-buttons"]/*[local-name() = "ytd-toggle-button-renderer"][1]'
                             '/a/*[local-name() = "yt-icon-button"]/button')
        button_element = self.new_wait(timeout=15).until(EC.presence_of_element_located(locator))
        return button_element.get_attribute("aria-pressed") == "true"

    def _video_comment_input(self):
        locator = (By.XPATH, '//div[@id="contenteditable-root" and @contenteditable="true"]')
        return self.new_wait(timeout=15).until(EC.presence_of_element_located(locator))

    def _video_comment_input_anchor(self):
        locator = (By.XPATH, '//*[text()="Add a public comment..."]')
        return self.new_wait(timeout=15).until(EC.presence_of_element_located(locator))

    def _video_comment_submit_button(self):
        locator = (By.XPATH, '//*[local-name() = "paper-button"][@aria-label="Comment"]')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    def _video_description_section(self):
        locator = (By.XPATH, '//*[local-name() = "ytd-video-secondary-info-renderer"]')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    def _video_is_comment_disabled(self):
        locator = (By.XPATH, '//span[text()="Comments are turned off. "]')
        try:
            self.driver.find_element(*locator)
            return True
        except NoSuchElementException:
            return False

    def _video_is_scheduled(self):
        locator = (By.XPATH, '//*[@id="date"]'
                             '/*[local-name() = "yt-formatted-string" and starts-with(text(), "Scheduled for")]')
        try:
            self.driver.find_element(*locator)
            return True
        except NoSuchElementException:
            return False

    def _video_is_unavailable(self):
        locator = (By.XPATH, '//*[@id="reason" and text() = "Video unavailable"]')
        try:
            self.driver.find_element(*locator)
            return True
        except NoSuchElementException:
            return False

    def _video_mute_button(self):
        locator = (By.XPATH, '//*[@id="movie_player"]//span[@class="ytp-volume-area"]/button')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    def _video_like_and_comment(self, comments_list, stop_if_like_encountered=False, header_overlap=0):
        # header_overlap = self._header_overlap_y() + YOUTUBE_HEADER_PADDING
        for try_n in range(1, YOUTUBE_COMMENT_RETRIES + 1):
            if (video_url := self.driver.current_url) != 'about:blank':
                self.log.info(f"Video url: {video_url}")
                break
            # self.log.info(f"Couldn't get video url, got '{video_url}' (try {try_n} of {YOUTUBE_COMMENT_RETRIES})")
            sleep(1)
            if try_n >= YOUTUBE_COMMENT_RETRIES:
                raise YoutubeVideoActionFailedException(f"Couldn't get video url after {try_n} tries")

        # mute video:
        for try_n in range(1, YOUTUBE_COMMENT_RETRIES + 1):
            try:
                mute_button_element = self._video_mute_button()
                mute_button_title = mute_button_element.get_attribute('title')
                if mute_button_title == "Mute (m)":
                    self.log.info("Muting sound.")
                    self.element_scroll_to(mute_button_element, y_offset=header_overlap)
                    mute_button_element.click()
                break
            except (ElementClickInterceptedException, ElementNotInteractableException, TimeoutException):
                if try_n >= YOUTUBE_COMMENT_RETRIES:
                    raise YoutubeVideoActionFailedException(f"Couldn't mute video after {try_n} tries")
                self.log.warn(f"Failed to mute video (try {try_n} of {YOUTUBE_COMMENT_RETRIES})")
                sleep(1)
                continue

        is_thumbs_up_pressed = False
        for try_n in range(1, YOUTUBE_COMMENT_RETRIES + 1):
            try:
                is_thumbs_up_pressed = self._video_thumbs_up_is_pressed()
                break
            except TimeoutException:
                if try_n >= YOUTUBE_COMMENT_RETRIES:
                    raise YoutubeVideoActionFailedException(f"Couldn't scrape like status after {try_n} tries")
                self.log.warn(f"Failed to scrape like status (try {try_n} of {YOUTUBE_COMMENT_RETRIES})")
                sleep(1)
                continue
        if is_thumbs_up_pressed:
            self.log.info("Already liked, skipping.")
            if stop_if_like_encountered:
                self.log.info("Stop if like active, halting.")
                raise YoutubeStopIfLikedException
            raise YoutubeAlreadyLikedException
        else:
            for try_n in range(1, YOUTUBE_COMMENT_RETRIES+1):
                try:
                    thumbs_up_element = self._video_thumbs_up_button()
                    self.element_scroll_to(thumbs_up_element, y_offset=header_overlap)
                    self.log.info("Liking video.")
                    thumbs_up_element.click()
                    break
                except ElementClickInterceptedException:
                    if try_n >= YOUTUBE_COMMENT_RETRIES:
                        raise YoutubeVideoActionFailedException(f"Couldn't like video after {try_n} tries")
                    self.log.warn(f"Failed to like video (try {try_n} of {YOUTUBE_COMMENT_RETRIES})")
                    sleep(1)
                    continue
            if self._video_is_unavailable():
                self.log.info("Video is unavailable.")
                raise YoutubeCommentDisabledException
            if self._video_is_scheduled():
                self.log.info("Video is scheduled to premiere later.")
                raise YoutubeCommentDisabledException
            if comments_list is not None:
                if self._video_is_comment_disabled():
                    self.log.info("Commenting disabled for video, skipping.")
                    raise YoutubeCommentDisabledException
                self.log.info("Adding comment.")
                # description_element = self._video_description_section()
                # self.element_scroll_to(description_element)
                for try_n in range(1, YOUTUBE_COMMENT_RETRIES+1):
                    try:
                        comment_anchor_element = self._video_comment_input_anchor()
                    except (TimeoutException, ElementClickInterceptedException):
                        if try_n >= YOUTUBE_COMMENT_RETRIES:
                            raise YoutubeVideoActionFailedException(f"Couldn't scrape comment entry after {try_n} tries")
                        self.log.warn(f"Failed to scrape comment entry field (try {try_n} of {YOUTUBE_COMMENT_RETRIES})")
                        sleep(1)
                        continue

                for try_n in range(1, YOUTUBE_COMMENT_RETRIES+1):
                    try:
                        self.element_scroll_to(comment_anchor_element, y_offset=header_overlap)
                        comment_anchor_element.click()
                        break
                    except (TimeoutException, ElementClickInterceptedException):
                        if try_n >= YOUTUBE_COMMENT_RETRIES:
                            raise YoutubeVideoActionFailedException(f"Couldn't click comment entry after {try_n} tries")
                        self.log.warn(f"Failed to click comment entry field (try {try_n} of {YOUTUBE_COMMENT_RETRIES})")
                        sleep(1)
                        continue
                for try_n in range(1, YOUTUBE_COMMENT_RETRIES+1):
                    try:
                        input_element = self._video_comment_input()
                        self.element_scroll_to(input_element, y_offset=header_overlap)
                        video_input_element = self._video_comment_input()
                        video_input_element.send_keys(Keys.COMMAND + 'a')
                        video_input_element.send_keys(Keys.BACKSPACE)
                        video_input_element.send_keys(random.choice(comments_list))
                        break
                    except (TimeoutException, ElementClickInterceptedException):
                        if try_n >= YOUTUBE_COMMENT_RETRIES:
                            raise YoutubeVideoActionFailedException(f"Couldn't enter comment for video after {try_n} tries")
                        self.log.warn(f"Failed to enter comment for video (try {try_n} of {YOUTUBE_COMMENT_RETRIES})")
                        sleep(1)
                        continue
                for try_n in range(1, YOUTUBE_COMMENT_RETRIES+1):
                    try:
                        comment_submit_button = self._video_comment_submit_button()
                        self.element_scroll_to(comment_submit_button, y_offset=header_overlap)
                        comment_submit_button.click()
                        break
                    except (ElementClickInterceptedException, TimeoutException, ElementNotInteractableException):
                        # self.log.exception("An exception occurred!")
                        if try_n >= YOUTUBE_COMMENT_RETRIES:
                            raise YoutubeVideoActionFailedException(f"Couldn't submit comment for video after {try_n} tries")
                        self.log.warn(f"Failed to submit comment for video (try {try_n} of {YOUTUBE_COMMENT_RETRIES})")
                        sleep(1)
                        continue
            sleep(10)

    def _search_submit(self, search_string):
        input_locator = (By.XPATH, '//div[@id="search-input"]/input')
        submit_locator = (By.XPATH, '//button[@id="search-icon-legacy"]')
        input_element = self.new_wait().until(EC.presence_of_element_located(input_locator))
        submit_element = self.new_wait().until(EC.presence_of_element_located(submit_locator))

        input_element.send_keys(search_string)
        submit_element.click()

    def _search_result_first_entry(self):
        locator = (By.XPATH, '//*[local-name() = "ytd-search"]/div[@id="container"]'
                             '/*/*/*/div[@id="contents"]/*[local-name() = "ytd-item-section-renderer"][1]')

    def _search_result_next_entry(self):
        pass

    def _search_result_first_section(self):
        locator = (By.XPATH, '//div[@id="contents"]/*[local-name() = "ytd-item-section-renderer"]')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    def _search_result_next_section(self, current_contents):
        locator = (By.XPATH, './following-sibling::*[local-name() = "ytd-item-section-renderer"][1]')
        return self.new_wait(current_contents).until(EC.presence_of_element_located(locator))

    def _search_result_first(self, current_contents):
        locator = (By.XPATH, './/*[local-name() = "ytd-video-renderer"][1]')
        return self.new_wait(current_contents).until(EC.presence_of_element_located(locator))

    def _search_result_next(self, current_result):
        next_video_locator = (By.XPATH, './following-sibling::*[local-name() = "ytd-video-renderer"][1]')
        horiz_card_locator = (By.XPATH, './following-sibling::*[local-name() = "ytd-horizontal-card-list-renderer"][1]')
        # ytd-horizontal-card-list-renderer
        try:
            horiz_card_element = current_result.find_element(*horiz_card_locator)
            return self.new_wait(horiz_card_element).until(EC.presence_of_element_located(next_video_locator))
        except NoSuchElementException:
            return self.new_wait(current_result).until(EC.presence_of_element_located(next_video_locator))

    def _search_result_is_last(self, current_section, current_result):
        locator = (By.XPATH, './/following-sibling::*[local-name() = "ytd-video-renderer"][last()]')
        last_result = self.new_wait(current_section).until(EC.presence_of_element_located(locator))
        return current_result == last_result

    def _search_result_title(self, current_result):
        locator = (By.XPATH, './/a[@id="video-title"]')
        return self.new_wait(current_result).until(EC.presence_of_element_located(locator))

    def _header_overlap_y(self):
        locator = (By.XPATH, '//div[@id="masthead-container"]')
        header_element = self.new_wait().until(EC.presence_of_element_located(locator))
        return header_element.size['height']

    def start_search_like_and_comment(self, search_string, quota=100, comments_list=None):
        self._search_submit(search_string)

        open_tab_chord = self.open_tab_chord()
        header_overlap = self._header_overlap_y() + YOUTUBE_HEADER_PADDING

        current_section = self._search_result_first_section()
        for try_n in range(1, YOUTUBE_COMMENT_RETRIES+1):
            try:
                current_result = self._search_result_first(current_section)
                break
            except TimeoutException:
                if try_n >= YOUTUBE_COMMENT_RETRIES:
                    raise ApplicationHandlerException(f"Couldn't find document section containing videos after {try_n} tries")
                self.log.warn("Section has no videos, trying next.")
                current_section = self._search_result_next_section(current_section)
                continue

        self.stats.reset_operation_count()
        self.stats.reset_failure_count()

        while self.stats.get_operation_count() < quota:
            self.element_scroll_to(current_result, y_offset=header_overlap)
            result_title = self._search_result_title(current_result)
            title_text = result_title.text
            self.log.info(f"Scanning video '{title_text}'")
            result_title.send_keys(open_tab_chord)
            self.driver.switch_to_window(self.driver.window_handles[1])

            try:
                self._video_like_and_comment(comments_list, header_overlap=header_overlap)
            except YoutubeStopIfLikedException:
                break
            except YoutubeCommentDisabledException:
                pass
            except YoutubeVideoActionFailedException as e:
                self.log.warn(f"Video action failed: {e}")
            else:
                self.stats.one_operation_successful()

            self.driver.close()
            self.driver.switch_to_window(self.driver.window_handles[0])

            if self._search_result_is_last(current_section, current_result):
                self.log.debug("Got last result!")
                current_section = self._search_result_next_section(current_section)
                current_result = self._search_result_first(current_section)
            else:
                current_result = self._search_result_next(current_result)

    def start_subscriptions_like_and_comment(self, quota=600, comments_list=None, stop_if_like_encountered=False):
        self._sidebar_subscriptions_link().click()
        open_tab_chord = self.open_tab_chord()

        header_overlap = self._header_overlap_y() + YOUTUBE_HEADER_PADDING

        current_dayframe = self._subscriptions_first_dayframe()
        current_video_entry = self._subscriptions_dayframe_first_entry(current_dayframe)

        self.stats.reset_operation_count()
        self.stats.reset_failure_count()

        def _set_next_video():
            nonlocal current_dayframe, current_video_entry
            if self._subscriptions_dayframe_is_last_entry(current_dayframe, current_video_entry):
                current_dayframe = self._subscriptions_next_dayframe(current_dayframe)
                current_video_entry = self._subscriptions_dayframe_first_entry(current_dayframe)
            else:
                current_video_entry = self._subscriptions_dayframe_next_entry(current_video_entry)

        while self.stats.get_operation_count() < quota:
            self.element_scroll_to(current_video_entry, y_offset=header_overlap)

            if self._subscriptions_dayframe_entry_is_live_now(current_video_entry):
                self.log.info("Video is LIVE NOW, skipping.")
                _set_next_video()
                continue

            # open video link in new tab ...
            current_video_title = self._subscriptions_dayframe_entry_title(current_video_entry)
            current_video_title_text = current_video_title.text

            self.log.info(f"Processing video: '{current_video_title_text}'")

            current_video_title.send_keys(open_tab_chord)
            self.driver.switch_to_window(self.driver.window_handles[1])

            try:
                self._video_like_and_comment(comments_list, stop_if_like_encountered, header_overlap=header_overlap)
            except YoutubeStopIfLikedException:
                break
            except YoutubeVideoActionFailedException as e:
                self.log.warn(f"Video action failed: {e}")
            except (YoutubeCommentDisabledException, YoutubeAlreadyLikedException):
                pass
            else:
                self.log.debug("Like/comment successful.")
                self.stats.one_operation_successful()

            # close tab ...
            self.driver.close()
            self.driver.switch_to_window(self.driver.window_handles[0])

            # get next frame and entry ...
            _set_next_video()

        self.log.info(f"Finished processing {self.stats.get_operation_count()} videos.")


class YoutubeSearchResultsParser():

    def __init__(self, driver):
        self.driver = driver
        self.current_section = None
        self.current_shelf = None
        self.current_entry = None
        self.in_shelf = False

    def _search_results_first_section(self):
        locator = (By.XPATH, '//*[local-name() = "ytd-search"]/div[@id="container"]'
                             '/*/*/*/div[@id="contents"]/*[local-name() = "ytd-item-section-renderer"][1]')
        return self.new_wait().until(EC.presence_of_element_located(locator))

    def _search_results_next_section(self, current_section):
        locator = (By.XPATH, './following-sibling::*[local-name() = "ytd-item-section-renderer"][1]')
        return self.new_wait(current_section).until(EC.presence_of_element_located(locator))

    def _search_results_first_result_entry(self, current_section):
        locator = (By.XPATH, './*[1]')
        return self.new_wait(current_section).until(EC.presence_of_element_located(locator))

    def _search_results_next_result_entry(self, current_entry):
        locator = (By.XPATH, './following-sibling::*[1]')
        return self.new_wait(current_entry).until(EC.presence_of_element_located(locator))

    def _search_results_is_last_entry_in_group(self, current_entry):
        locator = (By.XPATH, './*[last()]')
        last_entry = self.new_wait(current_entry).until(EC.presence_of_element_located(locator))
        return current_entry == last_entry

    def _search_results_is_ad_section(self, current_section):
        locator = (By.XPATH, './/h3[@id="title-text"]/yt-formatted-string/span[text() = "Suggested Products"]')
        try:
            current_section.find_element(*locator)
            return True
        except NoSuchElementException:
            return False

    def _search_results_next_result(self):
        if self.current_section is None:
            self.current_section = self._search_results_first_section()
            self.current_entry = self._search_results_first_result_entry(self.current_section)
        else:
            # check if we're at the end of a shelf or section:
            if self._search_results_is_last_entry_in_group(self.current_entry):
                if self.in_shelf:
                    self.current_entry = self._search_results_next_result_entry(self.current_shelf)
                    self.in_shelf = False
                else:
                    self.current_section = self._search_results_next_section(self.current_section)
                    self.current_entry = self._search_results_first_result_entry(self.current_section)
            else:
                self.current_entry = self._search_results_next_result_entry(self.current_entry)

        # scan self.current_section to see if it's an advertisement section
        if self._search_results_is_ad_section(self.current_section):
            self.current_section = self._search_results_next_section(self.current_section)
            self.current_entry = self._search_results_first_result_entry(self.current_section)
        if self.current_entry.tag_name in ('ytd-horizontal-card-list-renderer',
                                           'ytd-channel-renderer'):
            if self._search_results_is_last_entry_in_group(self.current_entry):
                self.current_section = self._search_results_next_section(self.current_section)
                self.current_entry = self._search_results_first_result_entry(self.current_section)
            else:
                self.current_entry = self._search_results_next_result_entry(self.current_entry)

        if self.current_entry.tag_name == 'ytd-video-renderer':
            # process a regular video entry
            return self.current_entry
        elif self.current_entry.tag_name == 'ytd-shelf-renderer':
            # scan the shelf
            self.in_shelf = True
            self.current_entry = self._search_results_first_shelf_entry(self.current_entry)
            return self.current_entry


class YoutubeHandlerException(Exception):
    pass


class YoutubeAlreadyLikedException(YoutubeHandlerException):
    pass


class YoutubeStopIfLikedException(YoutubeHandlerException):
    pass


class YoutubeCommentDisabledException(YoutubeHandlerException):
    pass


class YoutubeVideoActionFailedException(YoutubeHandlerException):
    pass