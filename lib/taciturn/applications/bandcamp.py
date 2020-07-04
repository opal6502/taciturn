
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

from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    UnexpectedAlertPresentException
)

from selenium.webdriver.common.by import By

from taciturn.applications.base import (
    BaseApplicationHandler,
    ApplicationWebElements,
    AppDataAnchorMissingException
)

from collections import namedtuple
import os

# named tuple to hold data about a bandcamp track:
BandcampTrackData = namedtuple('BandcampTrackData', ['url', 'title', 'artist', 'album', 'label', 'img_local'])

# it's important to order these tags by priority so that when twitter truncates the list, the best possible combo
# is still present, and 30 max for facebook, not sure about instagram:
GENRE_TAGS = {
    'idm': ['#music', '#bandcamp', '#radio', '#electronicmusic', '#electronic', '#idm', '#synthesizer', '#synth',
            '#breakbeat', '#drummachine', '#acid', '#beats', '#song', '#artist', '#dance', '#intelligent',
            '#musicproducer', '#producer', '#musician', '#art',  '#nowplaying', '#musicstreaming', '#musiclover',
            '#love', '#like', '#follow', '#life', '#friends', '#goodmusic', '#indie'],
    'techno': ['#music', '#bandcamp', '#radio', '#electronicmusic', '#electronic', '#techno', '#synthesizer', '#synth',
            '#breakbeat', '#drummachine', '#acid', '#beats', '#song', '#artist', '#dance', '#party',
            '#musicproducer', '#producer', '#musician', '#art',  '#nowplaying', '#musicstreaming', '#musiclover',
            '#love', '#like', '#follow', '#life', '#friends', '#goodmusic', '#indie'],
    'ambient': ['#music', '#bandcamp', '#radio', '#electronicmusic', '#electronic', '#ambient', '#synthesizer', '#synth',
            '#modular', '#atmosphere', '#mood', '#song', '#artist', '#drone', '#soundscape', '#soft',
            '#musicproducer', '#producer', '#musician', '#art',  '#nowplaying', '#musicstreaming', '#musiclover',
            '#love', '#like', '#follow', '#life', '#friends', '#goodmusic', '#indie'],
    'industrial': ['#music', '#bandcamp', '#radio', '#industrialmusic', '#industrial', '#electronic', '#synthesizer',
            '#synth', '#ebm', '#guitar', '#metal', '#distortion', '#song', '#artist', '#dance', '#party',
            '#musicproducer', '#producer', '#musician', '#art',  '#nowplaying', '#musicstreaming', '#musiclover',
            '#love', '#like', '#follow', '#life', '#friends', '#goodmusic', '#indie'],
    'experimental': ['#music', '#bandcamp', '#radio', '#experimentalmusic', '#experimental', '#electronic', '#synthesizer',
            '#tape', '#samples', '#foundsound', '#noise', '#atmosphere', '#song', '#artist', '#intelligent', '#sfx',
            '#musicproducer', '#producer', '#musician', '#art', '#nowplaying', '#musicstreaming', '#musiclover',
            '#love', '#like', '#follow', '#life', '#friends', '#goodmusic', '#indie'],
    'rock': ['#music', '#bandcamp', '#radio', '#rockmusic', '#rock', '#alternative', '#guitar',
            '#classicrock', '#indie', '#foundsound', '#noise', '#atmosphere', '#song', '#artist', '#intelligent', '#sfx',
            '#musicproducer', '#producer', '#musician', '#art', '#nowplaying', '#musicstreaming', '#musiclover',
            '#love', '#like', '#follow', '#life', '#friends', '#goodmusic', '#indie'],
}


class BandcampHandler(BaseApplicationHandler):
    application_name = 'bandcamp'

    application_url = "https://bandcamp.com"
    application_login_url = "https://bandcamp.com/login"

    implicit_default_wait = 60

    def __init__(self, options, db_session, app_account, elements=None):
        super().__init__(options, db_session, app_account, BandcampHandlerWebElements)

        self.init_webdriver()
        self.goto_homepage()

    def login(self):
        raise NotImplementedError("Why would you need this, anyway?")

    def parse_track_from_page(self, track_url):
        track_title = self.e.track_title()
        track_artist = self.e.track_artist()
        track_album = self.e.track_album()
        # track_label = self.e.track_label()  -- not sure about this one?

        # get the large image:
        track_img_small = self.e.track_img_small()
        track_img_small.click()
        track_img_large = self.e.track_img_large()
        track_img_large_src = track_img_large.get_attribute('src')
        track_img_large.click()

        # download the image to bandcamp assets dir:
        # we want something like this:  taciturn/assets/bandcamp/bandcamp-img-{sha256}.jpg
        track_img_local = self.download_image(track_img_large_src, prefix='bandcamp-img-')
        print("Downloaded album art: {}".format(track_img_local))

        return BandcampTrackData(
            url=track_url,
            title=track_title,
            artist=track_artist,
            album=track_album,
            label=None,
            img_local=track_img_local
        )

    # turns a BandcampTrackData entry to a string formatted like on bandcamp:
    @staticmethod
    def author_string(self, bandcamp_track_data):
        if bandcamp_track_data.album is not None:
            track_str = (bandcamp_track_data.title+'\n'
                         +'from '+bandcamp_track_data.album+' by '+bandcamp_track_data.artist)
        else:
            track_str = (bandcamp_track_data.title+'\n'
                         +'by '+bandcamp_track_data.artist)
        return track_str

    @staticmethod
    def genre_tags(genre):
        return GENRE_TAGS[genre]


class BandcampHandlerWebElements(ApplicationWebElements):
    implicit_default_wait = 60

    def track_title(self):
        return self.driver.find_element(By.XPATH, '//*[@id="name-section"]/h2[@class="trackTitle"]').text

    def track_artist(self):
        return self.driver.find_element(By.XPATH, '//*[@id="name-section"]/h3/span[@itemprop="byArtist"]/a').text

    def track_album(self):
        # this may not be present!
        try:
            self.driver.implicitly_wait(5)
            return self.driver.find_element(
                By.XPATH,
                '//*[@id="name-section"]/h3/span[1]/a/span[@class="fromAlbum" and @itemprop="name"]').text
        except NoSuchElementException:
            return False
        finally:
            self.driver.implicitly_wait(self.implicit_default_wait)

    def track_img_large(self):
        return self.driver.find_element(By.XPATH, '//img[@id="popupimage_image"]')

    def track_img_small(self):
        return self.driver.find_element(By.XPATH, '//*[@id="tralbumArt"]/a/img')