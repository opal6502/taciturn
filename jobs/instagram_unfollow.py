
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


from taciturn.job import TaciturnJob, TaskExecutor, RoundTaskExecutor, ApplicationHandlerStats
from taciturn.applications.instagram import InstagramHandler


class InstagramUnfollowJob(TaciturnJob):
    __jobname__ = 'instagram_unfollow'
    __appnames__ = ['instagram']

    def run(self):
        daily_max_unfollows = self.options.max or self.config['app:instagram']['daily_max_unfollows']
        round_max_unfollows = self.options.quota or self.config['app:instagram']['round_max_unfollows']
        day_length = self.config['day_length']
        instagram_account = self.get_account('instagram')

        self.log.info("config: taciturn user = '{}'".format(self.username))
        self.log.info("config: instagram user = '{}'".format(instagram_account.name))
        self.log.info("config: daily_max_unfollows = {}".format(daily_max_unfollows))
        self.log.info("config: round_max_unfollows = {}".format(round_max_unfollows))

        update_followers_stats = ApplicationHandlerStats()
        unfollow_stats = ApplicationHandlerStats()
        twitter_handler = InstagramHandler(instagram_account, update_followers_stats)
        twitter_handler.login()

        TaskExecutor(
                    call=lambda: twitter_handler.update_followers(),
                    job_name=self.job_name(),
                    driver=twitter_handler.driver,
                    handler_stats=update_followers_stats)\
                .run()

        twitter_handler.stats = unfollow_stats
        RoundTaskExecutor(
                    call=lambda: twitter_handler.start_unfollowing(quota=round_max_unfollows),
                    job_name=self.job_name(),
                    driver=twitter_handler.driver,
                    handler_stats=unfollow_stats,
                    retries=1,
                    quota=round_max_unfollows,
                    max=daily_max_unfollows,
                    stop_no_quota=self.stop_no_quota,
                    period=day_length)\
                .run()


job = InstagramUnfollowJob
