
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

from taciturn.job import TaciturnJob, TaskExecutor
from taciturn.applications.twitter import TwitterHandler

import sys


class TwitterFollowJob(TaciturnJob):
    __jobname__ = 'twitter_follow'

    def init_job(self, options, config=None):
        super().init_job(options, config)
        self.appnames = ['twitter']

        if options.target is None:
            print("twitter_follow: you must specify a target account with -t account.")
            sys.exit(1)
        self.target_account = options.target[0]

    def run(self):
        daily_max_follows = self.options.max or self.config['app:twitter']['daily_max_follows']
        round_max_follows = self.options.quota or self.config['app:twitter']['round_max_follows']
        day_length = self.config['day_length']

        if self.options.stop is not None and self.options.stop[0] is True:
            stop_no_quota = True
        else:
            stop_no_quota = False

        twitter_account = self.get_account('twitter')
        twitter_handler = TwitterHandler(self.options, self.session, twitter_account)

        twitter_handler.login()

        TaskExecutor(call=lambda: twitter_handler.general_start_following(self.target_account, quota=round_max_follows),
                     name=self.__jobname__,
                     quota=round_max_follows,
                     max=daily_max_follows,
                     stop_no_quota=stop_no_quota,
                     period=day_length).run()


job = TwitterFollowJob()
