
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

# this is the job used to automate RBGuy9000 posts!


import sys
import random

from taciturn.job import TaciturnJob, ApplicationHandlerStats

from taciturn.applications.youtube import YoutubeHandler


class YoutubeLikeAndCommentSearch(TaciturnJob):
    __jobname__ = 'anvilmesa_youtube_like_and_comment_search'
    __appnames__ = ['youtube']

    def __init__(self):
        super().__init__()

        if self.options.user is None:
            self.log.critical("You must provide a user with the '-u user' option")

        is_correct_user = self.options.user is not None and self.options.user[0] == 'anvilmesa'

        if not is_correct_user:
            self.log.critical("This job is for the user 'anvilmesa' only.")

        if self.options.user is None or not is_correct_user:
            self.log.critical("Job: insufficient configuration.")
            sys.exit(1)

        self.username = self.options.user[0]
        self.taciturn_user = self.get_taciturn_user(self.username)

        if self.options.inputfile is None:
            self.log.critical("You must provide a groups CSV file with the -f option")
            sys.exit(1)

        # read the comments file as a list of strings:
        with open(self.options.inputfile[0], 'r') as comments_file:
            self.comments_list = [l[:-1] for l in comments_file.readlines()]

    def run(self):
        self.log.info("Job: starting YouTube application handler.")

        search_strings = [
            # demos:
            'synth demo',
            'digital synth demo',
            'analog synth demo',
            'modular synth demo',
            'electric organ demo',

            # synth brands:
            'korg synth',
            'roland synth',
            'moog synth',
            'yamaha synth',
            'arp synth',
            'quasimidi synth',
            'vcv synth',
            'buchla synth',

            # daws:
            'ableton live',
            'fruityloops',
            'fl studio',
            'logic pro',
            'motu digital performer',
            'pro tools',
            'cubase',
            'cockos reaper',
            'renoise',
            'tracker daw',

            # softsynths:
            'reaktor',
            'maschine',
            'arturia',
            'native instruments',
            'eurorack',
            'theremin',

            # jam types:
            'synth jam',
            'synthpop jam',
            'industrial jam',
            'ambient jam',
            'modular jam',
            'techno jam',
            'acid jam',
            'live synth jam',
            'live techno jam',
            'psychedelic synth jam',

            # artists:
            'aphex twin',
            'autechre',
            'squarepusher',
            'boards of canada',
            'nine inch nails',
            'skinny puppy',
            'kmfdm',
            'front line assembly',
            'godflesh',
            'cevin key',
            'devo',
            'depeche mode',
            'marilyn manson',
            'tim skold',

            # music genres:
            'techno music',
            'industrial music',
            'idm music',
            'electronic music',

            # record labels:
            'warp records',
            'ghostly international',
            'cleopatra records'
        ]

        search_string = random.choice(search_strings)
        self.log.info(f"Using search term '{search_string}'")

        comment_stats = ApplicationHandlerStats()

        youtube_account = self.get_account('youtube')
        youtube_handler = YoutubeHandler(youtube_account, comment_stats)
        youtube_handler.login()

        youtube_handler.start_search_like_and_comment(search_string, comments_list=self.comments_list)

        print("Done.")


job = YoutubeLikeAndCommentSearch
