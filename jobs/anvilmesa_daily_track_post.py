
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

from taciturn.applications.music import TrackData, Genres
from taciturn.applications.bandcamp import BandcampHandler
from taciturn.applications.facebook import FacebookHandler
from taciturn.applications.twitter import TwitterHandler

from taciturn.listq import ListQueue


class AnvilMesaDailyTrackPost(TaciturnJob):
    __jobname__ = 'anvilmesa_daily_track_post'
    __appnames__ = ['facebook', 'twitter']
    genre = 'techno'

    def __init__(self):
        super().__init__()

        if self.options.user is None:
            self.log.critical("You must provide a user with the '-u user' option")

        is_correct_user = self.options.user is not None and self.options.user[0] == 'anvilmesa'

        if not is_correct_user:
            self.log.critical("This job is for the user 'anvilmesa' only.")

        if self.options.user is None or not is_correct_user:
            self.log.critical("Job: insufficient configuration.")
            sys.exit(1)

        self.help_me_string = '𝘐 𝘳𝘦𝘢𝘭𝘭𝘺 𝘯𝘦𝘦𝘥 𝘺𝘰𝘶𝘳 𝘩𝘦𝘭𝘱!  ☑️ 𝘭𝘪𝘬𝘦 ☑️ 𝘤𝘰𝘮𝘮𝘦𝘯𝘵 ☑️ 𝘴𝘩𝘢𝘳𝘦'
        self.genre_tags = Genres.tags_string(self.genre)

    def run(self):
        self.log.info("Anvil Mesa Daily Track Post, initializing.")

        anvilmesa_user = self.get_taciturn_user('anvilmesa')
        tracks_listq = ListQueue(anvilmesa_user, 'anvilmesa_bandcamp_discog')

        listq_entry = tracks_listq.read_random()
        track_data = TrackData.from_listq_entry(listq_entry)
        track_url = track_data.url

        # re-scrape the album art:
        bandcamp_handler = BandcampHandler()
        new_track_data = bandcamp_handler.scrape_page_track_data(track_url)
        bandcamp_handler.quit()

        author_string = str(new_track_data)
        img_local_path = new_track_data.img_local

        facebook_post_body = f"{author_string}\n\n{self.help_me_string}\n\n{self.genre_tags}"
        twitter_post_body = f"{author_string}\n\n{track_url}\n\n{self.help_me_string}\n\n{self.genre_tags}"

        # login to facebook:
        self.log.info("Job: starting Facebook application handler.")

        facebook_account = self.get_account('facebook')
        facebook_handler = FacebookHandler(facebook_account)
        facebook_handler.login()
        facebook_handler.page_post_create('xANVILMESAx', facebook_post_body, track_url)
        facebook_handler.quit()

        self.log.info("Job: made Facebook post.")

        # login to twitter:
        self.log.info("Job: starting Twitter application handler.")

        twitter_account = self.get_account('twitter')
        twitter_handler = TwitterHandler(twitter_account)
        twitter_handler.login()
        twitter_handler.post_tweet(twitter_post_body, img_local_path)

        self.log.info("Job: made tweet.")

        self.log.info("Job: made a daily Anvil Mesa track post!")


job = AnvilMesaDailyTrackPost
