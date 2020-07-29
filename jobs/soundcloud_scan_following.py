
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


from taciturn.applications.soundcloud import SoundcloudHandler

from taciturn.job import (
    TaciturnJob,
    TaskExecutor,
    ApplicationHandlerStats
)


class SoundcloudScanFollowingJob(TaciturnJob):
    __jobname__ = 'soundcloud_scan_following'
    __appnames__ = ['soundcloud']

    def run(self):
        scan_stats = ApplicationHandlerStats()
        soundcloud_account = self.get_account('soundcloud')
        soundcloud_handler = SoundcloudHandler(soundcloud_account, scan_stats)

        self.log.info("config: taciturn user = {}".format(self.username))
        self.log.info("config: soundcloud user = {}".format(soundcloud_account.name))

        soundcloud_handler.login()

        TaskExecutor(call=lambda: soundcloud_handler.update_following(),
                     job_name=self.job_name(),
                     handler_stats=scan_stats)\
                .run()


job = SoundcloudScanFollowingJob
