
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

from abc import ABC, abstractmethod

from sqlalchemy import and_
from sqlalchemy.sql.expression import func
from sqlalchemy.inspection import inspect

from sqlalchemy.orm.exc import NoResultFound

from taciturn.config import get_session, get_logger
from taciturn.db.listq import ListQueues, ListQueueEntry

from taciturn.datetime import datetime_now_tz


class ListQueue:
    _random_older_offset_fraction = 0.40

    def __init__(self, owner_account, queue_name, create=True):
        self._log = get_logger()
        self._session = get_session()

        self._taciturn_user_id = owner_account.id
        self._queue_name = queue_name
        self._create = create

        assert 0.1 < self._random_older_offset_fraction < 1.0

        self._id = self._get_or_create_queue()
        self._log.debug(f"listq '{self._queue_name}' initialized with id {self._id}.")

    def _get_queue_id(self):
        return self._session.query(ListQueues.id)\
            .filter(and_(ListQueues.listq_name == self._queue_name,
                         ListQueues.taciturn_user_id == self._taciturn_user_id))\
            .one_or_none()

    def _get_or_create_queue(self):
        if (queue_id_row := self._get_queue_id()) is not None:
            self._log.info(f"Loading listq '{self._queue_name}'.")
            return queue_id_row.id
        if not self._create:
            raise ListQueueException(f"Won't create listq '{self._queue_name}'.")

        self._log.info(f"Creating listq '{self._queue_name}'.")

        new_row = ListQueues(listq_name=self._queue_name,
                             taciturn_user_id=self._taciturn_user_id,
                             established=datetime_now_tz())
        self._session.add(new_row)
        self._session.commit()

        new_row_id = inspect(new_row).identity
        return new_row_id

    def _if_empty_exception(self):
        self_len = len(self)
        if self_len == 0:
            raise ListQueueEmpty("Listq is empty.")
        return self_len

    def __len__(self):
        return self._query_entries().count()

    def _query_entries(self):
        return self._session.query(ListQueueEntry).filter(ListQueueEntry.listq_id == self._id)

    def _query_entries_order_by_date(self, desc=False):
        if desc:
            return self._query_entries().order_by(ListQueueEntry.established.desc())
        else:
            return self._query_entries().order_by(ListQueueEntry.established)

    def _query_entries_order_by_read(self, desc=False):
        if desc:
            return self._query_entries().order_by(ListQueueEntry.last_read.desc())
        else:
            return self._query_entries().order_by(ListQueueEntry.last_read)

    def _get_listq_entry_by_index(self, index=None):
        listq_len = self._if_empty_exception()
        listq_entry = None

        if index is None:
            listq_entry = self._query_entries_order_by_date().first()
        elif isinstance(index, int):
            if index > listq_len:
                raise IndexError(f"Listq index {index} longer than listq length of {listq_len}.")
            elif index < 0 and index < -listq_len-1:
                raise IndexError(f"Listq negative index {index} less than negative index limit {-listq_len-1}.")
            elif index >= 0:
                listq_entry = self._query_entries_order_by_date().offset(index).first()
            elif index < 0:
                listq_entry = self._query_entries_order_by_date(desc=True).offset(index).first()
        else:
            raise TypeError(f"Listq index must be an 'int', not a '{type(index)}'.")

        assert listq_entry is not None
        return listq_entry

    def _process_read(self, listq_entry):
        reads_left = listq_entry.reads_left

        if reads_left is not None:
            if reads_left > 1:
                listq_entry.reads_left -= 1
                listq_entry.last_read = datetime_now_tz()
                self._session.commit()
            elif reads_left == 1:
                self._session.delete(listq_entry)
                self._session.commit()
            else:
                assert reads_left >= 1
        else:
            # when reads_left is None:
            listq_entry.last_read = datetime_now_tz()
            self._session.commit()

    def append(self, listq_entry, reads_left=None):
        listq_entry.listq_id = self._id

        self._session.add(listq_entry)
        self._session.commit()

    def pop(self, index=None):
        self._if_empty_exception()

        pop_entry = self._get_listq_entry_by_index(index)

        self._session.delete(pop_entry)
        self._session.commit()

        return pop_entry

    def read(self, index=None):
        self._if_empty_exception()

        read_row = self._get_listq_entry_by_index(index)
        self._process_read(read_row)

        return read_row

    def read_random(self):
        self._if_empty_exception()

        row_count = len(self)
        fraction_limit = floor(row_count * self._random_older_offset_fraction)

        # if the list is too small for the fraction_offset to make a difference:
        if row_count - fraction_limit <= 2:
            listq_entry = self._query_entries().order_by(func.random()).first()
            self._process_read(listq_entry)
            return listq_entry

        oldest_portion_subquery = self._session.query(ListQueueEntry.id)\
            .limit(fraction_limit)\
            .order_by(ListQueueEntry.last_read)\
            .subquery()
        listq_entry = self._session.query(ListQueueEntry).filter(ListQueueEntry.id.in_(oldest_portion_subquery))\
            .order_by(func.random())\
            .first()
        self._process_read(listq_entry)
        return listq_entry

    def clear(self):
        all_listq_entries = self._query_entries()
        all_listq_entries.delete()
        self._session.commit()


# make a container class listq-compatible:

class ListqEntry(ABC):
    @abstractmethod
    def to_listq_entry(self):
        pass


class ListQueueException(Exception):
    pass


class ListQueueEmpty(ListQueueException):
    pass


class ListQueueNoSuchTag(ListQueueException):
    pass
