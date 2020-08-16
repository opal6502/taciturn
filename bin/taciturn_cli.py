#!python

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


import sys
import argparse

from taciturn.config import set_options
from taciturn.job import TaciturnJobLoader


def run_job(job_name):
    loader = TaciturnJobLoader()
    job = loader.load_job(job_name)
    job.run()


def parse_arguments(args=None):
    if args is None:
        args = sys.argv[1:]

    ap = argparse.ArgumentParser(description='Taciturn CLI tool.')
    ap.add_argument('-u', '--user', type=str, nargs=1,
                    help='specify a taciturn user for job')
    ap.add_argument('-j', '--job', type=str, nargs=1, required=True,
                    help="job to run, with arguments for job")
    ap.add_argument('-t', '--target', type=str, nargs=1, default=None,
                    help="Target account")
    ap.add_argument('-L', '--listq', action='store_true',
                    help="Pull target accounts for 'user' from a listq.")
    ap.add_argument('-m', '--max', type=int,
                    help="Maximum follows per 24-hour period, divided into quota rounds")
    ap.add_argument('-q', '--quota', type=int,
                    help="Quota of follows per each round in a 24-hour period")
    ap.add_argument('-s', '--stop', action='store_true',
                    help="Stop job if round quota can't be fulfilled")
    ap.add_argument('-H', '--haltlogin', action='store_true',
                    help="Halt after login, debug any authentication errors, useful only in headed browser mode")
    ap.add_argument('-D', '--driver', type=str, nargs=1, default=None,
                    help="Webdriver to use: htmlunit htmlunitjs chrome chrome_headless firefox firefox_headless")
    ap.add_argument('-C', '--cookies', type=str, nargs=1, default=None,
                    help="Load a cookies.txt file")
    ap.add_argument('-l', '--link', type=str, nargs=1, default=None,
                    help="Specify a bandcamp link to post, for the 'rbg_bandcamp_post' job")
    ap.add_argument('-g', '--genre', type=str, nargs=1, default=None,
                    help="Specify a musical genre, for the 'rbg_bandcamp_post' job")
    ap.add_argument('-I', '--noinstagram', action='store_true',
                    help="Do not post to instagram, for the 'rbg_bandcamp_post' job")

    pa = ap.parse_args(args)

    return pa


if __name__ == '__main__':
    options = parse_arguments()
    set_options(options)

    if options.job is not None:
        run_job(options.job[0])
    else:
        print("You must specify a job with -j job-name")
        sys.exit(1)
