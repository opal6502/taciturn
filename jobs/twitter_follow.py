
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
from taciturn.db.base import User, Application, AppAccount

from sqlalchemy import and_

from time import sleep


class TwitterFollowJob(TaciturnJob):
    __jobname__ = 'twitter_follow'

    def init_job(self, options, config=None):
        super().init_job(options, config)

        self.appname = 'twitter'
        self.username = options.user[0]

        account = self.session.query(AppAccount).filter(and_(AppAccount.application_id == Application.id,
                                                             AppAccount.user_id == User.id,
                                                             User.name == self.username,
                                                             Application.name == self.appname
                                                             )).one_or_none()
        if account is None:
            raise

        self.target_account = options.target[0]
        self.daily_max_follows = options.max or self.config['app:twitter']['daily_max_follows']
        self.round_max_follows = options.quota or self.config['app:twitter']['round_max_follows']
        self.rounds_per_day = self.daily_max_follows / self.round_max_follows
        self.stop_no_quota = options.stop


    def run(self):
        # this script will handle following a total of X followers in Y rounds per day

        # get user from database:
        user = self.session.query(User)\
            .filter(and_(User.name == self.username,
                         Application.name == self.appname,
                         Application.id == User.application_id)).one()

        twitter_handler = TwitterHandler(self.session, user.name, user.password)

        # figure out what to do for the next 24 hours:

        rounds_per_day = self.daily_max_follows // self.round_max_follows
        print("rounds_per_day:", rounds_per_day)
        round_timeout = 24*60*60 / rounds_per_day

        twitter_handler.login()

        for round_n in range(1, rounds_per_day+1):
            print("twitter_follow: beginning round {} for {} at twitter ...".format(round_n, user.name))

            followed_count = twitter_handler.start_following(self.target_account, quota=self.round_max_follows)

            if followed_count < self.round_max_follows:
                print("twitter_follow: couldn't fulfill quota:"
                      " expected {} follows, actual {}.".format(self.round_max_follows, followed_count))
                if self.stop_no_quota:
                    print("Quota unfulfilled, stopping following.")
                    break

            sleep(round_timeout)

        print("Job complete.")
        twitter_handler.quit()


job = TwitterFollowJob()
