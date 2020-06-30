
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

from taciturn.applications.soundcloud import SoundcloudHandler

from datetime import timedelta
from time import sleep, time
import traceback
import sys


class SoundcloudFollowJob(TaciturnJob):
    __jobname__ = 'soundcloud_follow'

    def init_job(self, options, config=None):
        super().init_job(options, config)

        self.appnames = ['soundcloud']
        self.username = options.user[0]

        # pre-load accounts for all apps this job uses:
        self.load_accounts()

        if options.target is None:
            print("soundcloud_follow: you must specify a target account with -t account.")
            # options.print_help()
            sys.exit(1)

        self.target_account = options.target[0]
        self.stop_no_quota = options.stop

        self.options = options

    def run(self):
        # this script will handle following a total of X followers in Y rounds per day

        # get user from database:
        soundcloud_account = self.get_account('soundcloud')
        soundcloud_handler = SoundcloudHandler(self.options, self.session, soundcloud_account)

        # figure out what to do for the next 24 hours:

        daily_max_follows = self.options.max or self.config['app:twitter']['daily_max_follows']
        round_max_follows = self.options.quota or self.config['app:twitter']['round_max_follows']
        round_retries = 1

        daily_max_follows = self.options.max or self.config['app:soundcloud']['daily_max_follows']
        round_max_follows = self.options.quota or self.config['app:soundcloud']['round_max_follows']

        rounds_per_day = daily_max_follows // round_max_follows
        print("rounds_per_day:", rounds_per_day)
        round_timeout = (24*60*60) / rounds_per_day

        soundcloud_handler.login()

        total_job_time = 0
        followed_total = 0
        failed_rounds = 0

        for round_n in range(1, rounds_per_day+1):
            print("soundcloud_follow: beginning round {} for {} at soundcloud ...".format(round_n, self.username))

            start_epoch = time()
            followed_count = 0

            # for retry_n in range(1, round_retries+1):
            # try:
            followed_count = soundcloud_handler.start_following(self.target_account, quota=round_max_follows)
            # except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
            #     print("Round failed try {} of {}, selenium exception occurred: {}".format(1, round_retries, e))
            #     traceback.print_exc()
            #     # if this is the last try and it failed, re-raise the exception!
            #     # if retry_n >= round_retries:
            #     raise e
            # continue
            # else:
            #    break
            # else:
            #     print("twitter_follow: round failed after {} tries!".format(retry_n))
            #     failed_rounds += 1

            job_time = time() - start_epoch
            sleep_time = round_timeout - job_time

            if followed_count < round_max_follows:
                print("twitter_follow: couldn't fulfill quota:"
                      " expected {} follows, actual {}.".format(round_max_follows, followed_count))
                if self.stop_no_quota:
                    print("Quota unfulfilled, stopping following.")
                    break
            elif followed_count == round_max_follows and round_n < rounds_per_day:
                print("Followed {} users, round complete."
                      "  Sleeping for {} hours".format(followed_count, timedelta(seconds=sleep_time)))

            followed_total += followed_count
            total_job_time += job_time
            if round_n >= rounds_per_day:
                break
            sleep(sleep_time)

        print("Ran {} rounds, following {} accounts, {} rounds failed"
                .format(rounds_per_day, followed_total, failed_rounds))
        print("Job total time:", timedelta(seconds=total_job_time))

        print("Job complete.")
        soundcloud_handler.quit()


job = SoundcloudFollowJob()
