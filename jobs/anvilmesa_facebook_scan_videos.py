
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

from taciturn.applications.facebook import FacebookHandler

from taciturn.listq import ListQueue
from taciturn.db.listq import UrlListqEntry


class ScrapeFacebookPageVideos(TaciturnJob):
    __jobname__ = 'anvilmesa_facebook_scan_videos'
    __appnames__ = ['facebook']

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
        self.artist_page = 'xANVILMESAx'

        self.taciturn_user = self.get_taciturn_user(self.username)

    def run(self):
        self.log.info("Job: starting Facebook application handler.")

        facebook_account = self.get_account('facebook')
        facebook_handler = FacebookHandler(facebook_account)
        facebook_handler.login()
        video_url_list = facebook_handler.scan_page_videos(self.artist_page)

        import pprint
        pprint.pprint(video_url_list)

        # now, add all tracks to a listq:
        anvilmesa_user = self.get_taciturn_user('anvilmesa')
        videos_listq = ListQueue(anvilmesa_user, 'anvilmesa_facebook_videos')

        print("Clearing listq contents!")
        videos_listq.clear()

        for video_url in video_url_list:
            print(f"Adding {video_url} to listq.")
            new_url_entry = UrlListqEntry(url=video_url)
            videos_listq.append(new_url_entry)

        print("Done.")


job = ScrapeFacebookPageVideos