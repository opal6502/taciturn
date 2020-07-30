
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


from datetime import datetime

from taciturn.config import get_config


config = get_config()
timezone = config['timezone']


def datetime_now_tz():
    return timezone.localize(datetime.now())


def datetime_fromtimestamp_tz(timstamp):
    return timezone.localize(datetime.fromtimestamp(timstamp))
