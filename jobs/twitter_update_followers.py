
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


from taciturn.job import TaciturnJob

from taciturn.applications.twitter import TwitterHandler

from time import sleep


class TwitterFollowJob(TaciturnJob):
    __jobname__ = 'twitter_scan_followers'

    def init_job(self, options, config=None):
        super().init_job(options, config)

        self.appnames = ['twitter']
        self.accounts = dict()
        self.username = options.user[0]

        # pre-load accounts for all apps this job uses:
        self.load_accounts()

        self.target_account = options.target[0]
        self.stop_no_quota = options.stop

        self.options = options

    def run(self):
        # this script will handle following a total of X followers in Y rounds per day

        # get user from database:
        twitter_account = self.get_account('twitter')
        twitter_handler = TwitterHandler(self.session, twitter_account)

        twitter_handler.login()
        twitter_handler.update_followers()

        print("Job complete.")
        twitter_handler.quit()


job = TwitterFollowJob()
