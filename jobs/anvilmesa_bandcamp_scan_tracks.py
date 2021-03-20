
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

from taciturn.applications.bandcamp import BandcampHandler
from taciturn.listq import ListQueue


class BandcampScrapeArtistTracks(TaciturnJob):
    __jobname__ = 'anvilmesa_bandcamp_scan_tracks'
    __appnames__ = []

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

        self.username = self.options.user[0]
        self.artist_link = 'https://anvilmesa.bandcamp.com/music'

        self.taciturn_user = self.get_taciturn_user(self.username)

    def run(self):
        # Step 1: scrape the bandcamp track info:

        self.log.info("Job: starting Bandcamp application handler.")

        bandcamp_handler = BandcampHandler()

        all_tracks = bandcamp_handler.artist_scrape_all_tracks(self.artist_link)

        import pprint

        print("All tracks:")
        pprint.pprint(all_tracks)

        # now, add all tracks to a listq:
        anvilmesa_user = self.get_taciturn_user('anvilmesa')
        amfan1_user = self.get_taciturn_user('amfan1')
        amfan2_user = self.get_taciturn_user('amfan2')
        amfan3_user = self.get_taciturn_user('amfan3')

        tracks_listq = ListQueue(anvilmesa_user, 'anvilmesa_bandcamp_discog')
        amfan1_listq = ListQueue(amfan1_user, 'amfan1_bandcamp_discog')
        amfan2_listq = ListQueue(amfan2_user, 'amfan2_bandcamp_discog')
        amfan3_listq = ListQueue(amfan3_user, 'amfan3_bandcamp_discog')

        print("Clearing listq contents!")
        tracks_listq.clear()
        amfan1_listq.clear()
        amfan2_listq.clear()
        amfan3_listq.clear()

        for track_data in all_tracks:
            print(f"Adding {track_data!r} to listq.")
            tracks_listq.append(track_data.to_listq_entry())
            amfan1_listq.append(track_data.to_listq_entry())
            amfan2_listq.append(track_data.to_listq_entry())
            amfan3_listq.append(track_data.to_listq_entry())

        print("Done.")

job = BandcampScrapeArtistTracks
