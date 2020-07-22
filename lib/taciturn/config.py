
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
import logging
from itertools import chain

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

if 'TACITURN_ROOT' not in os.environ:
    raise RuntimeError("Environment variable TACITURN_ROOT must be defined.")

taciturn_root = os.environ['TACITURN_ROOT']

default_config = {
    'taciturn_root': taciturn_root,
    'cookie_dir': os.path.join(taciturn_root, 'cookies'),
    'screenshots_dir': os.path.join(taciturn_root, 'screenshots'),
    'assets_dir': os.path.join(taciturn_root, 'assets'),

    'log_dir': os.path.join(taciturn_root, 'log'),
    'log_individual_jobs': True,
    'log_file': 'taciturn.log',   # if log_individual_jobs is false, all job output will go here
    'log_level': logging.DEBUG,
    'log_format': '%(asctime)s - {job_name} - %(levelname)s - %(message)s',

    'database_url': 'sqlite:///' + os.path.join(taciturn_root, 'db', 'taciturn.sqlite'),
    'orm_connect_args': {'timeout': 60},

    'asset_root': os.path.join(taciturn_root, 'assets'),

    'day_length': datetime.timedelta(hours=8),

    # selenium webdriver type:  'chrome', 'chrome_headless', 'firefox', 'firefox_headless'
    'selenium_webdriver': 'chrome_headless',

    'app:*': {
        'daily_max_follows': 400,
        'round_max_follows': 100,
        'daily_max_unfollows': 400,
        'round_max_unfollows': 100,

        # 5 seconds to 2 minutes:
        'action_timeout': (1000*5, 1000*60*2),

        'follow_back_hiatus': datetime.timedelta(days=7),
        'unfollow_hiatus': datetime.timedelta(days=30*3),
        'mutual_expire_hiatus': datetime.timedelta(days=30*3),

        'ignore_no_image': True,
        'ignore_verified': False,
    },
    'app:instagram': {
        # instagram supposedly has a max 500 daily actions!
        'daily_max_follows': 500,
        'round_max_follows': 125,
        'daily_max_unfollows': 500,
        'round_max_unfollows': 125,
    },
    'app:youtube': {
        'video_watch_timeout': (2*60, 5*60),
        'like_every_video': True
    },
    'app:twitter': {
        'daily_max_follows': 400,
        'round_max_follows': 100,
        'daily_max_unfollows': 800,
        'round_max_unfollows': 200,
    },
    'app:soundcloud': {
        'daily_max_follows': 40,
        'round_max_follows': 40,
        'daily_max_unfollows': 40,
        'round_max_unfollows': 40,

        # for development:
        'action_timeout': (1000*5, 1000*30),
    },
}

supported_applications = (
    'twitter',
    'instagram',
    'facebook',
    'soundcloud',
    # 'youtube'
)

global_config = None


def get_config(filename=None):
    global global_config
    if global_config is not None:
        return global_config

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
    global_config = new_config
    return new_config


# get database session:

global_session_maker = None


def get_session():
    global global_session_maker
    if global_session_maker is None:
        config = get_config()
        global_session_maker = sessionmaker(bind=config['database_engine'])
    return global_session_maker()


# command-line options config:

global_options = None


def get_options():
    global global_options
    return global_options


def set_options(options):
    global global_options
    global_options = options


# logger configuration:

global_logger = None


def init_logger(job_name, logger_name='taciturn_log'):
    global global_logger
    config = get_config()
    # initialize logging here:
    if config['log_individual_jobs'] is True:
        log_file_path = os.path.join(config['log_dir'], '{}.log'.format(job_name))
    else:
        log_file_path = os.path.join(config['log_dir'], config['log_file'])

    log_level = config.get('log_level') or logging.INFO
    global_logger = logging.getLogger(logger_name)
    global_logger.setLevel(log_level)

    lf = logging.Formatter(config['log_format'].format(job_name=job_name))

    fh = logging.FileHandler(log_file_path)
    fh.setLevel(log_level)
    fh.setFormatter(lf)

    sh = logging.StreamHandler()
    sh.setLevel(log_level)
    sh.setFormatter(lf)

    global_logger.addHandler(sh)
    global_logger.addHandler(fh)

    return global_logger


def get_logger():
    if global_logger is None:
        raise RuntimeError("Logger has not been initialized")
    return global_logger
