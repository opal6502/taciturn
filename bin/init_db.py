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


from datetime import datetime

from sqlalchemy.orm import Session

from taciturn.config import get_config, supported_applications

from taciturn.db.base import (
    ORMBase,
    Application,
    JobId
)

import taciturn.db.followers
import taciturn.db.listq


print('> Taciturn database init script!')

print('> Loading config ... ', end='')
conf = get_config()
print('done.')

print('> Database URL:', conf['database_url'])

print('> Connecting to database ...', end='')
engine = conf['database_engine']
session = Session(bind=engine)
print(' done.')

print('> Loading tables ...', end='')
ORMBase.metadata.create_all(engine)
print(' done.')

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
    print(' already done.')
elif job_id_rows == 0:
    new_jobid_row = JobId(id=1, job_id=0)
    session.add(new_jobid_row)
    print(' done.')
else:
    print('Warning: multiple rows found in job id, should only be one!')

print('Database has been initialized.')

session.flush()
session.commit()