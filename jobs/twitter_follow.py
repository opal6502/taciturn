
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
    appnames = ['twitter']

    def __init__(self, options, config=None):
        super().__init__(options, config)
        if options.target is None:
            self.log.error('you must specify a target account with -t account.')
            sys.exit(1)
        self.target_account = options.target[0]

    def run(self):
        daily_max_follows = self.options.max or self.config['app:twitter']['daily_max_follows']
        round_max_follows = self.options.quota or self.config['app:twitter']['round_max_follows']
        day_length = self.config['day_length']
        twitter_account = self.get_account('twitter')

        self.log.info('config: taciturn user = {}'.format(self.username))
        self.log.info('config: twitter user = {}'.format(twitter_account.name))
        self.log.info('config: daily_max_follows = {}'.format(daily_max_follows))
        self.log.info('config: round_max_follows = {}'.format(round_max_follows))

        twitter_handler = TwitterHandler(self.log, self.options, self.session, twitter_account)
        twitter_handler.login()

        TaskExecutor(call=lambda: twitter_handler.start_following(self.target_account, quota=round_max_follows),
                     name=self.__jobname__,
                     retries=1,
                     quota=round_max_follows,
                     max=daily_max_follows,
                     stop_no_quota=self.stop_no_quota,
                     period=day_length).run()


job = TwitterFollowJob
