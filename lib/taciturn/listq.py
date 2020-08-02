
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


from math import floor

from sqlalchemy import and_
from sqlalchemy.sql.expression import func

from taciturn.config import get_session, get_logger
from taciturn.db.listq import ListQueues, ListQueueEntry, LISTQUEUE_STRING_DATA_LENGTH

from taciturn.datetime import datetime_now_tz


class ListQueue:
    _random_older_offset_fraction = 0.40

    def __init__(self, queue_name, owner_account, create=True):
        self._queue_name = queue_name
        self._taciturn_user_id = owner_account.taciturn_user_id
        self._application_id = owner_account.application_id
        self._create = create

        self._log = get_logger()
        self._session = get_session()

        assert 0.1 < self._random_older_offset_fraction < 1.0

        self._id = self._get_or_create_queue()

    def _get_queue_id_row(self):
        return self._session.query(ListQueues)\
            .filter(and_(ListQueues.queue_name == self._queue_name,
                         ListQueues.taciturn_user_id == self._taciturn_user_id,
                         ListQueues.application_id == self._application_id))\
            .one_or_none()

    def _get_or_create_queue(self):
        if (queue_id_row := self._get_queue_id_row()) is not None:
            self._log(f"Loading listq '{self._queue_name}'.")
            return queue_id_row.id
        if not self._create:
            raise ListQueueException(f"Won't create listq '{self._queue_name}'.")

        self._log(f"Creating listq '{self._queue_name}'.")

        new_row = ListQueues(queue_name=self._queue_name,
                             taciturn_user_id=self._taciturn_user_id,
                             application_id=self._application_id,
                             established=datetime_now_tz())
        self._session.add(new_row)
        self._session.commit()

        created_row = self._get_queue_id_row()

        assert created_row is not None
        return created_row.id

    def _query_listq(self):
        return self._session.query(ListQueueEntry).filter_by(id=self._id)

    def _query_order_by_date(self, desc=False):
        if desc:
            return self._query_listq().order_by(ListQueueEntry.established.desc())
        else:
            return self._query_listq().order_by(ListQueueEntry.established)

    def _query_order_by_last_read(self, desc=False):
        if desc:
            return self._session.query(ListQueueEntry)\
                .order_by(ListQueueEntry.last_read_datetime.desc())
        else:
            return self._session.query(ListQueueEntry)\
                .order_by(ListQueueEntry.last_read_datetime)

    def _get_entry_by_index(self, index=None):
        listq_len = self._is_queue_empty()
        pop_row = None

        if index is None:
            pop_row = self._query_order_by_date().first()
        elif isinstance(index, int):
            if index > listq_len:
                raise IndexError(f"Listq index {index} longer than listq length of {listq_len}.")
            elif index < 0 and index < -listq_len-1:
                raise IndexError(f"Listq negative index {index} less than negative index limit {-listq_len-1}.")
            elif index >= 0:
                pop_row = self._query_order_by_date().offset(index).one()
            elif index < 0:
                pop_row = self._query_order_by_date(desc=True).offset(index).one()
        else:
            raise TypeError(f"Listq index must be an 'int', not a '{type(index)}'.")

        assert pop_row is not None
        return pop_row

    def _process_read(self, read_row, recycle=None):
        reads_left = read_row.reads_left

        if reads_left is not None:
            if reads_left > 1:
                read_row.reads_left -= 1
                self._session.flush()
                return read_row
            elif recycle is None and reads_left and reads_left == 1:
                self._session.delete(read_row)
                self._session.flush()
                return read_row
            elif recycle is not None and reads_left == 1:
                read_row.read_count = int(recycle)
                read_row.last_read_datetime = datetime_now_tz()
                self._session.flush()
                return read_row
        else:
            # when reads_left is None:
            read_row.last_read_datetime = datetime_now_tz()
            self._session.flush()
            return read_row

    def __len__(self):
        return self._query_listq().count()

    def _is_queue_empty(self):
        self_len = len(self)
        if self_len == 0:
            raise ListQueueException("Listq is empty.")
        return self_len

    def append(self, data_string, reads_left=None):
        data_string_len = len(data_string)
        if data_string_len > LISTQUEUE_STRING_DATA_LENGTH:
            raise ListQueueException(f"Data string is too long: length is {data_string_len}, "
                                     f"maximum length is {LISTQUEUE_STRING_DATA_LENGTH}.")

        new_row = ListQueueEntry(
            queue_id=self._id,
            data_string=data_string,
            established=datetime_now_tz(),
            reads_left=reads_left,
            last_read_datetime=None
        )

        self._session.add(new_row)
        self._session.commit()

    def pop(self, index=None):
        pop_row = self._get_entry_by_index(index)

        self._session.delete(pop_row)
        self._session.commit()

        return pop_row

    def read(self, index=None, recycle=None):
        read_row = self._get_entry_by_index(index)
        self._process_read(read_row, recycle)

        return read_row

    def read_random(self, recycle=None):
        self._is_queue_empty()

        row_count = self._query_listq().count()
        fraction_offset = row_count - floor(row_count * self._random_older_offset_fraction)

        # if the list is too small for the fraction_offset to make a difference:
        if row_count - fraction_offset < 2:
            self._log.warning(f"Listq doesn't have enough entries to effectively randomize.")
            read_row = self._query_listq().order_by(func.random()).first()
            self._process_read(read_row, recycle)
            return

        oldest_portion_subquery = self._session.query(ListQueueEntry.id)\
            .offset(fraction_offset)\
            .order_by(ListQueueEntry.last_read_datetime)\
            .subquery()

        read_row = self._session.query(ListQueueEntry).filter(ListQueueEntry.id.in_(oldest_portion_subquery))\
            .order_by(func.random())\
            .first()

        self._process_read(read_row, recycle)

        return read_row

    # what I'd really like to do here with read_random(), is select a random row from the older portion of the listq
    # say, perhaps the older 40% of the listq, then randomize that, to make duplicates much less frequent.
    # I need to figure out how to do this in SQL and then SQLAlchemy ...

    # So in SQL terms, I think I want to ...

    # SELECT * FROM listq_entry
    #    WHERE id IN
    #       (SELECT id FROM listq_entry OFFSET
    #               (SELECT count(*) - floor(count(*) * 0.40) FROM listq_entry WHERE id = %(id))
    #        ORDER BY last_read_datetime)
    #    ORDER BY random();

class ListQueueException(Exception):
    pass
