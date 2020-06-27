

from taciturn.job import TaciturnJob

from taciturn.applications.soundcloud import SoundcloudHandler

from time import sleep
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
            options.print_help()
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

        daily_max_follows = self.options.max or self.config['app:soundcloud']['daily_max_follows']
        round_max_follows = self.options.quota or self.config['app:soundcloud']['round_max_follows']

        rounds_per_day = daily_max_follows // round_max_follows
        print("rounds_per_day:", rounds_per_day)
        round_timeout = (24*60*60) / rounds_per_day

        soundcloud_handler.login()

        for round_n in range(1, rounds_per_day+1):
            print("instagram_follow: beginning round {} for {} at instagram ...".format(round_n, self.username))

            followed_count = soundcloud_handler.start_following(self.target_account, quota=round_max_follows)

            if followed_count < round_max_follows:
                print("soundcloud_follow: couldn't fulfill quota:"
                      " expected {} follows, actual {}.".format(round_max_follows, followed_count))
                if self.stop_no_quota:
                    print("Quota unfulfilled, stopping following.")
                    break
            elif followed_count == round_max_follows and round_n < rounds_per_day:
                print("Followed {} users, round complete."
                      "  Sleeping for {} hours".format(followed_count, round_timeout / (60*60)))

            sleep(round_timeout)

        print("Job complete.")
        soundcloud_handler.quit()


job = SoundcloudFollowJob()
