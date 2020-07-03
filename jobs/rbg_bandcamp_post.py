
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

# from taciturn.applications.bandcamp import BandcampHandler
from taciturn.applications.facebook import FacebookHandler
from taciturn.applications.instagram import InstagramHandler
from taciturn.applications.twitter import TwitterHandler

from time import sleep
import traceback


class RootBeerGuyJob(TaciturnJob):
    __jobname__ = 'soundcloud_update_followers'

    def init_job(self, options, config=None):
        super().init_job(options, config)

        self.appnames = ['facebook', 'instagram', 'twitter']
        self.accounts = dict()
        self.username = options.user[0]

        if self.username != 'rbg':
            raise RuntimeError("This job is for user 'rbg' only!")

        # pre-load accounts for all apps this job uses:
        self.load_accounts()

        self.stop_no_quota = options.stop

        self.options = options

    def run(self):
        facebook_account = self.get_account('facebook')
        facebook_handler = FacebookHandler(self.options, self.session, facebook_account)

        post_link = 'https://revocation.bandcamp.com/track/teratogenesis'

        post_body = """Teratogenesis
from Scion AV Presents 'Teratogenesis' by Revocation

𝕎𝕖 𝕣𝕖𝕒𝕝𝕝𝕪 𝕟𝕖𝕖𝕕 𝕪𝕠𝕦𝕣 𝕙𝕖𝕝𝕡! ☑️ 𝕝𝕚𝕜𝕖 ☑️ 𝕔𝕠𝕞𝕞𝕖𝕟𝕥 ☑️ 𝕤𝕙𝕒𝕣𝕖

#music #metalmusic #goodmusic #metalcore #grindcore #metalband #technicaldeathmetal #like #follow #techdeath #songs #radio #deathcore #doommetal #rock #death #explorepage #metalheads #friends #nowplaying #musicstreaming #deathmetal #brutaldeathmetal #bandcamp #metal #heavymetal #thrashmetal #blackmetal #extrememetal #guitar
        """

        facebook_handler.login()
        fb_post_link = facebook_handler.pagepost_create('RBGuy9000', post_link, post_body)

        print("new page post link =", fb_post_link)


job = RootBeerGuyJob()
