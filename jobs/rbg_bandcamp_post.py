
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

# this is the job used to automate RBGuy9000 posts!


import sys

from taciturn.job import TaciturnJob

from taciturn.applications.music import Genres

from taciturn.applications.bandcamp import BandcampHandler
from taciturn.applications.facebook import FacebookHandler
from taciturn.applications.instagram import InstagramHandler
from taciturn.applications.twitter import TwitterHandler


class RootBeerGuyJob(TaciturnJob):
    __jobname__ = 'rbg_bandcamp_post'
    __appnames__ = ['bandcamp', 'facebook', 'instagram', 'twitter']

    def __init__(self):
        super().__init__()

        self.driver_name = self.options.driver[0] if self.options.driver is not None \
            else self.config['selenium_webdriver']
        if self.driver_name != 'firefox':
            self.log.critical("This job can only be run with the 'firefox' webdriver.")
            sys.exit(1)

        if self.options.user is None:
            self.log.critical("You must provide a user with the '-u user' option, and this user must be 'rbg'")
        if self.options.link is None:
            self.log.critical("You must provide bandcamp track link with the '-l url' option")
        if self.options.genre is None:
            self.log.critical(f"You must provide genre name with the '-g genre' option, choose one from: "
                              f"{Genres.all_string()}")

        if (self.options.user is None or
            self.options.link is None or
            self.options.genre is None):
            self.log.critical("Job: insufficient configuration.")
            sys.exit(1)

        self.username = self.options.user[0]
        self.bandcamp_track_link = self.options.link[0]
        self.genre = self.options.genre[0]
        self.no_instagram = self.options.noinstagram

        is_name_correct = self.username == 'rbg'
        is_genre_correct = Genres.in_(self.genre)

        if not is_name_correct:
            self.log.critical("This job is for user 'rbg' only!")
        if not is_genre_correct:
            self.log.critical(f"You must provide a genre with the -g flag, "
                              f"choose one from: {Genres.all_string()}")

        if not is_name_correct or not is_genre_correct:
            self.log.critical("Job: configuration error")
            sys.exit(1)

        self.genre_tags = Genres.tags_string(self.genre)
        self.help_us_string = '𝕎𝕖 𝕣𝕖𝕒𝕝𝕝𝕪 𝕟𝕖𝕖𝕕 𝕪𝕠𝕦𝕣 𝕙𝕖𝕝𝕡! ☑️ 𝕝𝕚𝕜𝕖 ☑️ 𝕔𝕠𝕞𝕞𝕖𝕟𝕥 ☑️ 𝕤𝕙𝕒𝕣𝕖'

    def run(self):
        # Step 1: scrape the bandcamp track info:

        self.log.info("Job: starting Bandcamp application handler.")

        bandcamp_handler = BandcampHandler()
        shared_driver = bandcamp_handler.driver

        parsed_track = bandcamp_handler.music_scrape_track_data(self.bandcamp_track_link)

        self.log.debug(f"Bandcamp track: artist = {parsed_track.artist}")
        self.log.debug(f"Bandcamp track: title = {parsed_track.title}")
        self.log.debug(f"Bandcamp track: album = {parsed_track.album or 'n/a'}")
        self.log.debug(f"Bandcamp track: label = {parsed_track.label or 'n/a'}")
        self.log.debug(f"Bandcamp track: downloaded art = {parsed_track.img_local}")

        img_local_path = parsed_track.img_local
        author_string = str(parsed_track)
        facebook_post_body = f"{author_string}\n\n{self.help_us_string}\n\n{self.genre_tags}"
        others_post_body = f"{author_string}\n\n{self.bandcamp_track_link}\n\n" \
                           f"{self.help_us_string}\n\n{self.genre_tags}"

        self.log.info("Job: track info scraped from Bandcamp.")

        # Step 2: create the facebook post:

        self.log.info("Job: starting Facebook application handler.")

        facebook_account = self.get_account('facebook')
        facebook_handler = FacebookHandler(facebook_account, driver=shared_driver)
        facebook_handler.login()
        facebook_handler.page_post_create('RBGuy9000', facebook_post_body, self.bandcamp_track_link)

        self.log.info("Job: made Facebook post.")

        # Step 3: make tweet:

        self.log.info("Job: starting Twitter application handler.")

        twitter_account = self.get_account('twitter')
        twitter_handler = TwitterHandler(twitter_account, driver=shared_driver)
        twitter_handler.login()
        twitter_handler.post_tweet(others_post_body, img_local_path)

        self.log.info("Job: made tweet.")

        self.log.debug("Job: closing shared web driver.")
        shared_driver.quit()  # close shared driver

        # Step 4: create the instagram post, let it have its own driver and mobile user-agent:

        if not self.no_instagram:
            self.log.info("Job: starting Instagram application handler.")

            instagram_account = self.get_account('instagram')
            instagram_handler = InstagramHandler(instagram_account)
            instagram_handler.login()
            instagram_handler.post_image(img_local_path, others_post_body)

            self.log.info("Job: made Instagram post.")

            instagram_handler.quit()
        else:
            self.log.warning("Job: skipping Instagram post")

        self.log.info("Job: made a Root Beer Guy post!")


job = RootBeerGuyJob
