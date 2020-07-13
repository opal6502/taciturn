
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


from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException
)

from taciturn.job import TaciturnJob

from taciturn.applications.bandcamp import BandcampHandler
from taciturn.applications.bandcamp import GENRE_TAGS

from taciturn.applications.facebook import FacebookHandler
from taciturn.applications.instagram import InstagramHandler
from taciturn.applications.twitter import TwitterHandler

from time import sleep
import traceback


class RootBeerGuyJob(TaciturnJob):
    __jobname__ = 'soundcloud_update_followers'

    def init_job(self, options, config=None):
        super().init_job(options, config)

        self.appnames = ['bandcamp', 'facebook', 'instagram', 'twitter']
        self.accounts = dict()

        self.username = options.user[0]
        if self.username != 'rbg':
            raise RuntimeError("This job is for user 'rbg' only!")

        if self.options.link is None:
            raise RuntimeError("You must provide a bandcamp link with the -l flag")
        self.target_link = options.link[0]

        if self.options.genre is None or self.options.genre[0] not in GENRE_TAGS:
            raise RuntimeError("You must provide a genre with the -g flag, choose one from: {}"
                               .format(', '.join(GENRE_TAGS.keys())))
        self.genre = self.options.genre[0]

        # pre-load accounts for all apps this job uses:
        self.load_accounts()

        self.stop_no_quota = options.stop

        self.options = options

    def run(self):
        help_us_string = '𝕎𝕖 𝕣𝕖𝕒𝕝𝕝𝕪 𝕟𝕖𝕖𝕕 𝕪𝕠𝕦𝕣 𝕙𝕖𝕝𝕡! ☑️ 𝕝𝕚𝕜𝕖 ☑️ 𝕔𝕠𝕞𝕞𝕖𝕟𝕥 ☑️ 𝕤𝕙𝕒𝕣𝕖'

        bandcamp_account = self.get_account('bandcamp')
        bandcamp_handler = BandcampHandler(self.options, self.session, bandcamp_account)
        # just share this first-initialized driver with all app handlers:
        shared_driver = bandcamp_handler.driver

        # first, scan the bandcamp page:

        parsed_track = bandcamp_handler.parse_track_from_page(self.target_link)
        author_string = bandcamp_handler.author_string(parsed_track)
        genre_tags = ' '.join(GENRE_TAGS[self.genre])
        img_local_path = parsed_track.img_local

        # then, create the facebook post:

        facebook_account = self.get_account('facebook')
        facebook_handler = FacebookHandler(self.options, self.session, facebook_account, shared_driver)

        facebook_post_body = "{}\n\n{}\n\n{}".format(author_string,
                                                     help_us_string,
                                                     genre_tags)

        facebook_handler.login()
        fb_post_link = facebook_handler.pagepost_create('RBGuy9000', self.target_link, facebook_post_body)

        print("Made facebook post.")
        # print("new page post link =", fb_post_link)

        # then, create the twitter post:

        twitter_account = self.get_account('twitter')
        twitter_handler = TwitterHandler(self.options, self.session, twitter_account, shared_driver)

        twitter_post_body = "{}\n\n{}\n\n{}\n\n{}".format(author_string,
                                                          fb_post_link,
                                                          help_us_string,
                                                          genre_tags)

        twitter_handler.login()
        twitter_handler.post_tweet(twitter_post_body, img_local_path)

        print("Made tweet.")

        # close the shared driver:
        shared_driver.quit()

        # then, create the instagram post, let it have its own driver and mobile user-agent:

        instagram_account = self.get_account('instagram')
        instagram_handler = InstagramHandler(self.options, self.session, instagram_account)

        instagram_post_body = "{}\n\n{}\n\n{}\n\n{}".format(author_string,
                                                            fb_post_link,
                                                            help_us_string,
                                                            genre_tags)

        instagram_handler.login()
        instagram_handler.post_image(img_local_path, instagram_post_body, image_domain='bandcamp.com')

        print("Made instagram post.")

        instagram_handler.quit()

        print("Made a full Root Beer Guy post!")




job = RootBeerGuyJob()
