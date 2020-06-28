
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


import os
from importlib.machinery import SourceFileLoader
import datetime
import copy
from itertools import chain

import pprint

from sqlalchemy import create_engine

if 'TACITURN_ROOT' not in os.environ:
    raise RuntimeError("Environment variable TACITURN_ROOT must be defined.")

taciturn_root = os.environ['TACITURN_ROOT']

default_config = {
    'taciturn_root': taciturn_root,
    'cookie_dir': os.path.join(taciturn_root, 'cookies'),
    'database_url': 'sqlite:///' + os.path.join(taciturn_root, 'db', 'taciturn.sqlite'),
    'asset_root': os.path.join(taciturn_root, 'assets'),

    'default_config1': 'foo',
    'default_site_config1': 'foo_default',

    'orm_connect_args': {'timeout': 60},

    # selenium webdriver type:  'htmlunit', 'htmlunitjs', 'chrome', 'chrome_headless', 'firefox'
    'selenium_webdriver': 'chrome_headless',

    'app:*': {
        'daily_max_follows': 400,
        'round_max_follows': 30,
        'daily_max_unfollows': 400,
        'round_max_unfollows': 30,

        # 5 seconds to 5 minutes:
        'action_timeout': (1000*5, 1000*60*2),

        'follow_back_hiatus': datetime.timedelta(days=7),
        'unfollow_hiatus': datetime.timedelta(days=30*3),
        'mutual_expire_hiatus': datetime.timedelta(days=30*3),

        'ignore_no_image': True,
        'ignore_verified': False,
    },
    'app:instagram': {
        'daily_max_follows': 300,
        'round_max_follows': 30
    },
    'app:youtube': {
        'video_watch_timeout': (2*60, 5*60),
        'like_every_video': True
    },
    'app:twitter': {

    },
    'app:soundcloud': {
        'daily_max_follows': 40,
        'round_max_follows': 40,
        'daily_max_unfollows': 40,
        'round_max_unfollows': 40
    }
}

supported_applications = (
    'twitter',
    'instagram',
    'facebook',
    'soundcloud',
    'youtube'
)

config_cache = None


def load_config(filename=None):
    global config_cache
    if config_cache is not None:
        return config_cache

    try:
        site_config_file = filename or os.path.join(taciturn_root, 'conf', 'site_config.py')
        # print("Loading site config at {} ...".format(site_config_file))
        site_config_module = SourceFileLoader('site_config', site_config_file).load_module()
    except (ImportError, SyntaxError) as e:
        raise RuntimeError("Could not lode site config: {}: {}".format(site_config_file, e))

    if not hasattr(site_config_module, 'site_config'):
        raise RuntimeError("Site config file must provide a 'site_config' dictionary")

    site_config = site_config_module.site_config

    new_config = {k: v for k, v in default_config.items() if not isinstance(v, dict)}
    new_config.update({k: v for k, v in site_config.items() if not isinstance(v, dict)})

    default_section_keys = set(filter(
        lambda k: isinstance(default_config[k], dict) and k.endswith(':*'),
        default_config.keys()))

    site_section_keys = set(filter(
        lambda k: isinstance(site_config[k], dict) and k.endswith(':*'),
        site_config.keys()))

    for default_section in default_section_keys:
        for section in chain(default_config.keys(), site_config.keys()):
            if section.endswith(':*'): continue
            if section.startswith(default_section[:-1]):
                if section not in new_config: new_config[section] = dict()
                new_config[section].update(copy.deepcopy(default_config[default_section]))

    for site_section in site_section_keys:
        for section in chain(default_config.keys(), site_config.keys()):
            if section.endswith(':*'): continue
            if section.startswith(site_section[:-1]):
                if section not in new_config: new_config[section] = dict()
                new_config[section].update(copy.deepcopy(site_config[site_section]))

    default_section_keys = set(filter(
        lambda k: isinstance(default_config[k], dict) and not k.endswith(':*'),
        default_config.keys()))

    for section in default_section_keys:
        if section not in new_config: new_config[section] = dict()
        new_config[section].update(copy.deepcopy(default_config[section]))

    # pprint.pp(new_config)
    # print('='*72)

    site_section_keys = set(filter(
        lambda k: isinstance(site_config[k], dict) and not k.endswith(':*'),
        site_config.keys()))

    for section in site_section_keys:
        if section not in new_config: new_config[section] = dict()
        new_config[section].update(copy.deepcopy(site_config[section]))

    # finally load database:
    if 'database_url' in new_config:
        if 'orm_connect_args' in new_config:
            new_config['database_engine'] = create_engine(new_config['database_url'],
                                                          connect_args=new_config['orm_connect_args'])
        else:
            new_config['database_engine'] = create_engine(new_config['database_url'])
    else:
        print("load_config: warning: no database_url provided, no 'database_engine' created")

    # pprint.pp(new_config)
    # print('='*72)
    config_cache = new_config
    return new_config

