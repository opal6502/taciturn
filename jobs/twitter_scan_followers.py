
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

from taciturn.job import TaciturnJob, TaskExecutor

from taciturn.applications.twitter import TwitterHandler

from time import sleep
import traceback


class TwitterUpdateFollowersJob(TaciturnJob):
    __jobname__ = 'twitter_update_followers'
    __appnames__ = ['twitter']

    def run(self):
        # this script will handle following a total of X followers in Y rounds per day

        # get user from database:
        twitter_account = self.get_account('twitter')
        twitter_handler = TwitterHandler(twitter_account)

        twitter_handler.login()

        TaskExecutor(call=lambda: twitter_handler.update_followers())\
            .run()


job = TwitterUpdateFollowersJob()
