
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


from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Sequence
from sqlalchemy.orm import relationship

from taciturn.db.base import ORMBase

from taciturn.datetime import datetime_now_tz


class ListQueues(ORMBase):
    __tablename__ = 'listqs'

    id = Column(Integer, Sequence('listqs_id_seq'), primary_key=True)

    taciturn_user_id = Column(Integer, ForeignKey('taciturn_user.id', ondelete='CASCADE'))
    taciturn_user = relationship('TaciturnUser', backref='listqs_for_taciturn_user')

    established = Column(DateTime(timezone=True), nullable=False, default=datetime_now_tz)
    listq_name = Column(String(200), nullable=False)


class ListQueueEntry(ORMBase):
    __tablename__ = 'listq_entry'

    id = Column(Integer, Sequence('listq_entry_id_seq'), primary_key=True)
    type = Column(String(100))

    listq_id = Column(Integer, ForeignKey('listqs.id', ondelete='CASCADE'))
    listqs_id = relationship('ListQueues', backref='entry_for_listq')

    reads_left = Column(Integer, nullable=True)
    last_read = Column(DateTime(timezone=True), nullable=True)

    established = Column(DateTime(timezone=True), nullable=False, default=datetime_now_tz)

    __mapper_args__ = {
        'polymorphic_identity': 'employee',
        'polymorphic_on': type
    }


class FollowerTargetListqEntry(ListQueueEntry):
    __tablename__ = 'listq_follower_target'

    id = Column(Integer, ForeignKey('listq_entry.id', ondelete='CASCADE'), primary_key=True)

    target_name = Column(String(100), nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'follower_target',
    }


class TrackDataListqEntry(ListQueueEntry):
    __tablename__ = 'listq_track_data'

    id = Column(Integer, ForeignKey('listq_entry.id', ondelete='CASCADE'), primary_key=True)

    track_artist = Column(String(300), nullable=False)
    track_title = Column(String(300), nullable=False)
    track_album = Column(String(300), nullable=True)
    track_label = Column(String(300), nullable=True)
    track_url = Column(String(2048), nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'track_data',
    }


class UrlListqEntry(ListQueueEntry):
    __tablename__ = 'listq_url'

    id = Column(Integer, ForeignKey('listq_entry.id', ondelete='CASCADE'), primary_key=True)

    url = Column(String(2048), nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'url',
    }
