
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

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from taciturn.applications.music import MusicScrapingHandler


class BandcampHandler(MusicScrapingHandler):
    application_name = 'bandcamp'
    application_url = "https://bandcamp.com"

    def music_scrape_artist(self):
        locator = (By.XPATH, '//*[@id="name-section"]/h3/span[@itemprop="byArtist"]/a')
        return self.new_wait().until(EC.presence_of_element_located(locator)).text

    def music_scrape_title(self):
        locator = (By.XPATH, '//*[@id="name-section"]/h2[@class="trackTitle"]')
        return self.new_wait().until(EC.presence_of_element_located(locator)).text

    def music_scrape_album(self):
        locator = (By.XPATH, '//*[@id="name-section"]/h3/span[1]/a/span[@class="fromAlbum" and @itemprop="name"]')
        try:
            return self.new_wait(timeout=2).until(EC.presence_of_element_located(locator)).text
        except TimeoutError:
            return None

    def music_scrape_art_url(self):
        small_image_locator = (By.XPATH, '//*[@id="tralbumArt"]/a/img')
        large_image_locator = (By.XPATH, '//img[@id="popupimage_image"]')

        self.new_wait().until(EC.element_to_be_clickable(small_image_locator))\
            .click()

        large_image_element = self.new_wait().until(EC.element_to_be_clickable(large_image_locator))
        large_image_url = large_image_element.get_attribute('src')

        large_image_element.click()

        return large_image_url

