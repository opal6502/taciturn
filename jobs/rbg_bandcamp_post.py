
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


from taciturn.job import TaciturnJob

from taciturn.applications.bandcamp import BandcampHandler
from taciturn.applications.bandcamp import GENRE_TAGS

from taciturn.applications.facebook import FacebookHandler
from taciturn.applications.instagram import InstagramHandler
from taciturn.applications.twitter import TwitterHandler

import sys


class RootBeerGuyJob(TaciturnJob):
    __jobname__ = 'rbg_bandcamp_post'
    __appnames__ = ['bandcamp', 'facebook', 'instagram', 'twitter']

    def __init__(self):
        super().__init__()

        self.username = self.options.user[0]
        self.target_link = self.options.link[0]
        self.genre = self.options.genre[0]

        if self.username != 'rbg':
            self.log.critical("This job is for user 'rbg' only!")
            sys.exit(1)
        if self.target_link is None:
            self.log.critical("You must provide a bandcamp link with the -l flag")
            sys.exit(1)
        if self.genre not in GENRE_TAGS:
            self.log.critical(f"You must provide a genre with the -g flag, "
                              f"choose one from: {', '.join(GENRE_TAGS.keys())}")
            sys.exit(1)

        if self.options.genre is None or self.options.genre[0] not in GENRE_TAGS:
            raise RuntimeError("You must provide a genre with the -g flag, choose one from: {}"
                               .format(', '.join(GENRE_TAGS.keys())))
        self.genre = self.options.genre[0]

    def run(self):
        help_us_string = '𝕎𝕖 𝕣𝕖𝕒𝕝𝕝𝕪 𝕟𝕖𝕖𝕕 𝕪𝕠𝕦𝕣 𝕙𝕖𝕝𝕡! ☑️ 𝕝𝕚𝕜𝕖 ☑️ 𝕔𝕠𝕞𝕞𝕖𝕟𝕥 ☑️ 𝕤𝕙𝕒𝕣𝕖'

        bandcamp_account = self.get_account('bandcamp')
        bandcamp_handler = BandcampHandler(bandcamp_account)
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
        fb_post_link = facebook_handler.pagepost_create('RBGuy9000',
                                                        self.target_link,
                                                        facebook_post_body)

        print("Made facebook post.")

        twitter_account = self.get_account('twitter')
        twitter_handler = TwitterHandler(twitter_account, driver=shared_driver)

        twitter_post_body = "{}\n\n{}\n\n{}\n\n{}".format(author_string,
                                                          self.target_link,
                                                          help_us_string,
                                                          genre_tags)

        twitter_handler.login()
        twitter_handler.post_tweet(twitter_post_body, img_local_path)

        print("Made tweet.")

        # close the shared driver:
        shared_driver.quit()

        # then, create the instagram post, let it have its own driver and mobile user-agent:

        if False:
            instagram_account = self.get_account('instagram')
            instagram_handler = InstagramHandler(self.options, self.session, instagram_account)

            instagram_post_body = "{}\n\n{}\n\n{}\n\n{}".format(author_string,
                                                                self.target_link,
                                                                help_us_string,
                                                                genre_tags)

            instagram_handler.login()
            instagram_handler.post_image(img_local_path, instagram_post_body)

            print("Made instagram post.")

            instagram_handler.quit()

            print("Made a full Root Beer Guy post!")

        print("Made a partial Root Beer Guy post!")


job = RootBeerGuyJob()
