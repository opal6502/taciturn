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


# initializes the db!

from sqlalchemy.orm import Session

from taciturn.config import load_config, supported_applications

from taciturn.db.base import (
    ORMBase,
    Application,
    User,
    AppAccount,
    Blacklist,
    Whitelist,
    JobId
)

from taciturn.db.followers import (
    Follower,
    Following,
    Unfollowed
)

from datetime import datetime

print('> Taciturn database init script!')

print('> Loading config ... ', end='')
conf = load_config()
print('done.')

print('> Database URL:', conf['database_url'])

print('> Connecting to database ... ', end='')
engine = conf['database_engine']
session = Session(bind=engine)
print('done.')

print('> Loading tables ...', end='')
ORMBase.metadata.create_all(engine)
print('done.')

print('> Initializing rows for supported applications ...')

for app_name in supported_applications:
    print('>    ', app_name)
    if session.query(Application).filter(Application.name == app_name).one_or_none():
        continue
    app = Application(name=app_name, established=datetime.now())
    session.add(app)

print('> ... done!')

print('> Setting up job ids ...', end='')

job_id_rows = session.query(JobId).count()
if job_id_rows == 1:
    print('Already done.')
elif job_id_rows == 0:
    new_jobid_row = JobId(id=1, job_id=1)
    session.add(new_jobid_row)
else:
    print('Warning: multiple rows found in job id, should only be one!')

print('Database has been initialized.')

session.flush()
session.commit()