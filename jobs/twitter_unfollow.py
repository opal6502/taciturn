
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


from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException
)

from taciturn.job import TaciturnJob

from taciturn.applications.twitter import TwitterHandler

from datetime import timedelta
from time import sleep, time
import traceback


class TwitterUnfollowJob(TaciturnJob):
    __jobname__ = 'twitter_unfollow'

    def init_job(self, options, config=None):
        super().init_job(options, config)

        self.appnames = ['twitter']
        self.accounts = dict()
        self.username = options.user[0]

        self.load_accounts()

        # self.target_account = options.target[0]
        self.stop_no_quota = options.stop

        self.options = options

    def run(self):
        # this script will handle following a total of X followers in Y rounds per day

        # get user from database:
        twitter_account = self.get_account('twitter')
        twitter_handler = TwitterHandler(self.options, self.session, twitter_account)

        # figure out what to do for the next 24 hours:

        daily_max_unfollows = self.options.max or self.config['app:twitter']['daily_max_unfollows']
        round_max_unfollows = self.options.quota or self.config['app:twitter']['round_max_unfollows']
        day_length = self.config['day_length']
        round_retries = 5

        rounds_per_day = daily_max_unfollows // round_max_unfollows
        print("rounds_per_day:", rounds_per_day)
        round_timeout = day_length.total_seconds() / rounds_per_day

        twitter_handler.login()

        total_job_time = 0
        unfollowed_total = 0
        failed_rounds = 0

        for round_n in range(1, rounds_per_day+1):
            print("twitter_unfollow: beginning round {} for {} at twitter ...".format(round_n, self.username))

            start_epoch = time()
            unfollowed_count = 0

            for retry_n in range(1, round_retries+1):
                try:
                    unfollowed_count = twitter_handler.start_unfollowing(quota=round_max_unfollows)
                except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
                    print("Round failed try {} of {}, selenium exception occurred: {}".format(retry_n, round_retries, e))
                    traceback.print_exc()
                    # if this is the last try and it failed, re-raise the exception!
                    if retry_n >= round_retries:
                        raise e
                    continue
                else:
                    break
            else:
                print("twitter_unfollow: round failed after {} tries!".format(retry_n))
                failed_rounds += 1

            job_time = time() - start_epoch
            sleep_time = round_timeout - job_time
            if sleep_time < 0:
                sleep_time = 0

            if unfollowed_count < round_max_unfollows:
                print("twitter_unfollow: couldn't fulfill quota:"
                      " expected {} unfollows, actual {}.".format(round_max_unfollows, unfollowed_count))
                if self.stop_no_quota:
                    print("Quota unfulfilled, stopping unfollowing.")
                    break
            elif unfollowed_count == round_max_unfollows and round_n < rounds_per_day:
                print("Unfollowed {} users, round complete."
                      "  Sleeping for {} hours".format(unfollowed_count, timedelta(seconds=sleep_time)))

            total_job_time += job_time
            unfollowed_total += unfollowed_count
            if round_n >= rounds_per_day:
                break
            sleep(sleep_time)

        print("Ran {} rounds, unfollowing {} accounts, {} rounds failed"
                .format(round_n, unfollowed_total, failed_rounds))
        print("Job total time:", timedelta(seconds=total_job_time))

        print("Job complete.")
        twitter_handler.quit()


job = TwitterUnfollowJob()
