
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

from taciturn.applications.music import TrackData
from taciturn.listq import ListQueue


class AnvilMesaDailyTrackPost(TaciturnJob):
    __jobname__ = 'anvilmesa_daily_track_post'
    __appnames__ = ['facebook', 'twitter']

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

    def run(self):
        self.log.info("Anvil Mesa Daily Track Post, initializing.")

        anvilmesa_user = self.get_taciturn_user('anvilmesa')
        tracks_listq = ListQueue(anvilmesa_user, 'anvilmesa_bandcamp_discog')

        from time import sleep
        while True:
            listq_entry = tracks_listq.read_random()
            track_data = TrackData.from_listq_entry(listq_entry)

            self.log.info(f"Read track data from listq: {track_data!r}")
            self.log.info("Press enter for next entry.")
            input()


job = AnvilMesaDailyTrackPost
