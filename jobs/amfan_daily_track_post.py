
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

# this is the job used to automate Anvil Mesa Fan posts!


import sys

from taciturn.job import TaciturnJob, TaskExecutor

from taciturn.applications.music import TrackData, Genres
from taciturn.applications.twitter import TwitterHandler

from taciturn.listq import ListQueue


class AnvilMesaDailyTrackPost(TaciturnJob):
    __jobname__ = 'amfan1_daily_track_post'
    __appnames__ = ['twitter']
    genre = 'techno'

    def __init__(self):
        super().__init__()

        if self.options.user is None:
            self.log.critical("You must provide a user with the '-u user' option")

        self.username = self.options.user

        is_correct_user = self.options.user is not None and self.options.user[0].startswith('amfan')

        if not is_correct_user:
            self.log.critical("This job is for the users 'amfanN' only.")

        if self.options.user is None or not is_correct_user:
            self.log.critical("Job: insufficient configuration.")
            sys.exit(1)

        self.help_me_string = '𝘐 𝘳𝘦𝘢𝘭𝘭𝘺 𝘯𝘦𝘦𝘥 𝘺𝘰𝘶𝘳 𝘩𝘦𝘭𝘱!  ☑️ 𝘭𝘪𝘬𝘦 ☑️ 𝘤𝘰𝘮𝘮𝘦𝘯𝘵 ☑️ 𝘴𝘩𝘢𝘳𝘦'
        self.genre_tags = Genres.tags_string(self.genre)

    def run(self):
        self.log.info(f"Anvil Mesa Daily Track Post ({self.username}), initializing.")

        anvilmesa_user = self.get_taciturn_user(self.username)
        tracks_listq = ListQueue(anvilmesa_user, f'{self.username}_bandcamp_discog')

        listq_entry = tracks_listq.read_random()
        track_data = TrackData.from_listq_entry(listq_entry)
        track_url = track_data.url

        author_string = str(track_data)

        twitter_post_body = f"{track_url}"

        # login to twitter:
        self.log.info("Job: starting Twitter application handler.")

        twitter_account = self.get_account('twitter')
        twitter_handler = TwitterHandler(twitter_account)
        twitter_handler.login()

        TaskExecutor(call=lambda: twitter_handler.post_tweet(twitter_post_body, notruncate=True),
                     job_name=self.job_name(),
                     driver=twitter_handler.driver,
                     retries=10
                     ).run()

        twitter_handler.quit()

        self.log.info("Job: made tweet.")

        self.log.info("Job: made a daily Anvil Mesa Fan track post!")


job = AnvilMesaDailyTrackPost
