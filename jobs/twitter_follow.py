
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
    __jobname__ = 'twitter_follow'

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

        # figure out what to do for the next 24 hours:

        daily_max_follows = self.options.max or self.config['app:twitter']['daily_max_follows']
        round_max_follows = self.options.quota or self.config['app:twitter']['round_max_follows']

        rounds_per_day = daily_max_follows // round_max_follows
        print("rounds_per_day:", rounds_per_day)
        round_timeout = (24*60*60) / rounds_per_day

        twitter_handler.login()

        for round_n in range(1, rounds_per_day+1):
            print("twitter_follow: beginning round {} for {} at twitter ...".format(round_n, self.username))

            followed_count = twitter_handler.start_following(self.target_account, quota=round_max_follows)

            if followed_count < round_max_follows:
                print("twitter_follow: couldn't fulfill quota:"
                      " expected {} follows, actual {}.".format(round_max_follows, followed_count))
                if self.stop_no_quota:
                    print("Quota unfulfilled, stopping following.")
                    break
            elif followed_count == round_max_follows and round_n < rounds_per_day:
                print("Followed {} users, round complete."
                      "  Sleeping for {} hours".format(followed_count, round_timeout / (60*60)))

            sleep(round_timeout)

        print("Job complete.")
        twitter_handler.quit()


job = TwitterFollowJob()
