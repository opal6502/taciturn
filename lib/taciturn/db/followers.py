
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


class Follower(ORMBase):
    "Accounts that follow us!"
    __tablename__ = 'follower'

    id = Column(Integer, Sequence('follower_id_seq'), primary_key=True)
    application_id = Column(Integer, ForeignKey('application.id'))
    application = relationship('Application', backref='followers_for_taciturn_user')

    taciturn_user_id = Column(Integer, ForeignKey('taciturn_user.id'))
    taciturn_user = relationship('TaciturnUser', backref='followers')

    established = Column(DateTime, nullable=False)
    name = Column(String(100), nullable=False)


class Following(ORMBase):
    "Accounts we are following!"
    __tablename__ = 'following'

    id = Column(Integer, Sequence('following_id_seq'), primary_key=True)
    application_id = Column(Integer, ForeignKey('application.id'))
    application = relationship('Application', backref='following_for_taciturn_user')
    taciturn_user_id = Column(Integer, ForeignKey('taciturn_user.id'))
    taciturn_user = relationship('TaciturnUser', backref='following')

    established = Column(DateTime, nullable=False)
    name = Column(String(100), nullable=False)


class Unfollowed(ORMBase):
    "Accounts that have been followed once already, then unfollowed!"
    __tablename__ = 'unfollowed'

    id = Column(Integer, Sequence('unfollowed_id_seq'), primary_key=True)
    application_id = Column(Integer, ForeignKey('application.id'))
    application = relationship('Application', backref='unfollowed_for_taciturn_user')
    taciturn_user_id = Column(Integer, ForeignKey('taciturn_user.id'))
    taciturn_user = relationship('TaciturnUser', backref='unfollowed')

    established = Column(DateTime, nullable=False)
    name = Column(String(100), nullable=False)
