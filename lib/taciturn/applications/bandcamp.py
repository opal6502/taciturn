
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


from time import sleep

from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from taciturn.applications.music import MusicScrapingHandler, ScrapeException


class BandcampHandler(MusicScrapingHandler):
    application_name = 'bandcamp'
    application_url = "https://bandcamp.com"

    _album_locator = (By.XPATH, '//*[@id="name-section"]/h3/span[1]/a/span')

    def track_scrape_artist(self):
        if self.track_has_album_field():
            locator = (By.XPATH, '//*[@id="name-section"]/h3/span[2]/a')
        else:
            locator = (By.XPATH, '//*[@id="name-section"]/h3/span/a')
        return self.new_wait().until(EC.presence_of_element_located(locator)).text

    def track_scrape_title(self):
        locator = (By.XPATH, '//*[@id="name-section"]/h2[@class="trackTitle"]')
        return self.new_wait().until(EC.presence_of_element_located(locator)).text

    def track_scrape_album(self):
        try:
            return self.new_wait(timeout=2).until(EC.presence_of_element_located(self._album_locator)).text
        except TimeoutException:
            return None

    def track_has_album_field(self):
        try:
            self.driver.find_element(*self._album_locator)
        except NoSuchElementException:
            return False
        return True

    def track_scrape_art_url(self):
        small_image_locator = (By.XPATH, '//*[@id="tralbumArt"]/a/img')
        large_image_locator = (By.XPATH, '//img[@id="popupimage_image"]')

        self.new_wait().until(EC.element_to_be_clickable(small_image_locator))\
            .click()

        large_image_element = self.new_wait().until(EC.element_to_be_clickable(large_image_locator))
        large_image_url = large_image_element.get_attribute('src')

        large_image_element.click()

        return large_image_url

    def artist_scrape_all_tracks(self, artist_url):
        self.driver.get(artist_url)

        discography_link_locator = (By.XPATH, 'xpath=//a[contains(text(),"discography")]')

        # If there's a 'discography' link, click on it.  If not, we must already be on the right page.
        try:
            discography_link_element = self.driver.find_element(*discography_link_locator)
            self.element_scroll_to(discography_link_element)
            discography_link_element.click()
        except NoSuchElementException:
            pass

        # now, we should be in artist discog view ...
        # start by scanning all discog entries ...

        # //ol[@id="music-grid"]/li[N]/a/div/img      --
        # xpath=//span[contains(.,"Digital Track")]   -- present on track page

        all_tracks = list()

        discog_entries_locator = (By.CSS_SELECTOR, '.music-grid-item a')
        is_track_locator = (By.XPATH, '//span[contains(.,"Digital Track")]')
        # track_list_locator = (By.CSS_SELECTOR, '.track_row_view .track-title')
        track_links_locator = (By.XPATH, '//table[@id="track_table"]/tbody/tr/td[3]/div/a')

        open_tab_chord = self.open_tab_chord()

        scraper_wait = self.new_wait(timeout=30)
        discog_entries_elements = scraper_wait.until(EC.presence_of_all_elements_located(discog_entries_locator))
        main_window = self.driver.current_window_handle

        for discog_entry in discog_entries_elements:
            self.element_scroll_to(discog_entry)

            discog_entry.send_keys(open_tab_chord)
            self.driver.switch_to_window(self.driver.window_handles[1])
            sleep(5)

            # determine if it's a single track or album
            try:
                self.new_wait(timeout=2).until(EC.presence_of_element_located(is_track_locator))
                self.log.debug("This looks like a track page!")
                is_track_page = True
            except (NoSuchElementException, TimeoutException):
                self.log.debug("This looks like an album page!")
                is_track_page = False

            if is_track_page is True:
                # if track, just scrape data:
                track_data = self.scrape_page_track_data(download_image=False)
                self.log.debug(f"Scraped track data: {track_data!r}")
                all_tracks.append(track_data)
            else:
                # if album, iterate over each individual track and scrape:
                track_links = scraper_wait.until(EC.presence_of_all_elements_located(track_links_locator))

                for track_link in track_links:
                    # open track in new tab:
                    self.element_scroll_to(track_link)
                    # open link in new tab:
                    track_link.send_keys(open_tab_chord)
                    self.driver.switch_to_window(self.driver.window_handles[2])
                    sleep(1)

                    track_data = self.scrape_page_track_data(download_image=False)
                    self.log.debug(f"Scraped track data: {track_data!r}")
                    all_tracks.append(track_data)

                    self.driver.close()
                    self.driver.switch_to_window(self.driver.window_handles[1])

            self.driver.close()
            self.driver.switch_to_window(self.driver.window_handles[0])

        return all_tracks