
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

from taciturn.applications.instagram import InstagramHandler

# from time import sleep
import traceback


class InstagramUpdateFollowersJob(TaciturnJob):
    __jobname__ = 'instagram_update_followers'

    def init_job(self, options, config=None):
        super().init_job(options, config)

        self.appnames = ['instagram']
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
        instagram_account = self.get_account('instagram')
        instagram_handler = InstagramHandler(self.session, instagram_account)

        instagram_handler.login()

        round_retries = 5

        for retry_n in range(1, round_retries + 1):
            try:
                instagram_handler.update_followers()
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
            print("instagram_scan_followers: failed after {} retries!".format(retry_n))

        print("Job complete.")
        instagram_handler.quit()


job = InstagramUpdateFollowersJob()
