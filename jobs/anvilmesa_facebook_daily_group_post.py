
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

# this is the job used to automate anvilmesa group posts!


import sys
import csv

from taciturn.job import TaciturnJob

from taciturn.applications.base import ApplicationHandlerException
from taciturn.applications.facebook import FacebookHandler, ApplicationFacebookPostLimitException

from taciturn.listq import ListQueue


class AnvilMesaDailyTrackPost(TaciturnJob):
    __jobname__ = 'anvilmesa_facebook_daily_group_post'
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

        if self.options.inputfile is None:
            self.log.critical("You must provide a groups CSV file with the -f option")
            sys.exit(1)

        # parse the CSV file!
        groups_file = self.options.inputfile[0]
        self.log.info(f"Scanning group info from file '{groups_file}'")
        self.facebook_group_list = list()
        with open(groups_file, newline='') as csv_infile:
            csv_reader = csv.reader(csv_infile)
            for row in csv_reader:
                self.log.info(f"Adding group '{row[3]}'")
                self.facebook_group_list.append(row[3])

    def run(self):
        self.log.info("Anvil Mesa Daily Facebook Groups Post, initializing.")

        anvilmesa_user = self.get_taciturn_user('anvilmesa')
        videos_listq = ListQueue(anvilmesa_user, 'anvilmesa_facebook_videos')

        video_url = videos_listq.read_random().url
        self.log.info(f"Posting video url: {video_url}")

        facebook_account = self.get_account('facebook')
        facebook_handler = FacebookHandler(facebook_account)
        facebook_handler.login()

        for facebook_group_url in self.facebook_group_list:
            self.log.info(f"Posting to group at '{facebook_group_url}'")

            try:
                facebook_handler.group_post_create(facebook_group_url, '', post_link=video_url)
            except ApplicationFacebookPostLimitException:
                self.log.warn("Encountered Facebook group post limit.")
                break
            except ApplicationHandlerException:
                self.log.error("Failed to make post for group!")
            facebook_handler.last_action_mark()

            if facebook_group_url != self.facebook_group_list[-1]:
                facebook_handler.last_action_pause()

        self.log.info("Job: finished daily Anvil Mesa Facebook group posting!")

        facebook_handler.quit()


job = AnvilMesaDailyTrackPost
