
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

from taciturn.job import TaciturnJob, RoundTaskExecutor, ApplicationHandlerStats
from taciturn.applications.soundcloud import SoundcloudHandler

import sys


class SoundcloudFollowJob(TaciturnJob):
    __jobname__ = 'soundcloud_follow'
    __appnames__ = ['soundcloud']

    def __init__(self):
        super().__init__()
        if self.options.target is None:
            self.log.error("you must specify a target account with '-t account'.")
            sys.exit(1)
        self.target_account = self.options.target[0]

    def run(self):
        daily_max_follows = self.options.max or self.config['app:soundcloud']['daily_max_follows']
        round_max_follows = self.options.quota or self.config['app:soundcloud']['round_max_follows']
        day_length = self.config['day_length']
        soundcloud_account = self.get_account('soundcloud')

        self.log.info(f"config: taciturn user = '{self.username}'")
        self.log.info(f"config: soundcloud user = '{soundcloud_account.name}'")
        self.log.info(f"config: target account = '{self.target_account}'")
        self.log.info(f"config: daily_max_follows = {daily_max_follows}")
        self.log.info(f"config: round_max_follows = {round_max_follows}")

        unfollow_stats = ApplicationHandlerStats()
        soundcloud_handler = SoundcloudHandler(soundcloud_account, unfollow_stats)
        soundcloud_handler.login()

        RoundTaskExecutor(call=lambda: soundcloud_handler.start_following(self.target_account, quota=round_max_follows),
                          job_name=self.job_name(),
                          driver=soundcloud_handler.driver,
                          handler_stats=unfollow_stats,
                          retries=1,
                          quota=round_max_follows,
                          max=daily_max_follows,
                          stop_no_quota=self.stop_no_quota,
                          period=day_length)\
                    .run()


job = SoundcloudFollowJob
