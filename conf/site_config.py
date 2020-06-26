
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

# Taciturn site config!

# setup:

import os

if 'TACITURN_ROOT' not in os.environ:
    raise RuntimeError("Environment variable TACITURN_ROOT must be defined.")

taciturn_root = os.environ['TACITURN_ROOT']

# application settings:
# 'daily_max_follows': total follows per day
# 'round_max_follows': max followers per round, before sleeping
# 'daily_max_unfollows': total unfollows per day
# ''

site_config = {
    'default_site_config1': 'foo_site',

    # 'app:*': {
    #     'some_dir': os.path.join(taciturn_root, 'some_dir')
    #     'daily_max_follows': 200,
    #     'round_max_follows': 50,
    #     'daily_max_unfollows': 200,
    #     'round_max_unfollows': 50,
    # },

}
