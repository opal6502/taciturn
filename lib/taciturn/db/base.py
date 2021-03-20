
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


from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from sqlalchemy import (
    Column,
    Integer,
    Sequence,
    String,
    DateTime,
    ForeignKey,
    BigInteger
)

ORMBase = declarative_base()


class Application(ORMBase):
    "An application, like twitter, instagram, facebook, youtube ..."
    __tablename__ = 'application'

    id = Column(Integer, Sequence('application_id_seq'), primary_key=True)

    established = Column(DateTime, nullable=False)
    name = Column(String(100), unique=True, nullable=False)


class TaciturnUser(ORMBase):
    "An user of an application!"
    __tablename__ = 'taciturn_user'

    id = Column(Integer, Sequence('taciturn_user_id_seq'), primary_key=True)
    # application_id = Column(Integer, ForeignKey('application.id'))
    # application = relationship('Application', backref='users')

    # XXX need to create a constraint where every app & user pair must be unique!
    established = Column(DateTime, nullable=False)
    name = Column(String(500), unique=True, nullable=False)

    # a user will just be a way of grouping app accounts:
    # password = Column(String(500), nullable=False)


class AppAccount(ORMBase):
    # an account for an application, a user may have many
    __tablename__ = 'app_account'

    id = Column(Integer, Sequence('app_account_id_seq'), primary_key=True)
    application_id = Column(Integer, ForeignKey('application.id'))
    application = relationship('Application', backref='app_accounts')
    taciturn_user_id = Column(Integer, ForeignKey('taciturn_user.id'))
    taciturn_user = relationship('TaciturnUser', backref='app_accounts',
                                                 single_parent=True,
                                                 cascade="all, delete-orphan")

    established = Column(DateTime, nullable=False)

    name = Column(String(500), nullable=False)
    password = Column(String(500), nullable=False)


class Whitelist(ORMBase):
    "Accounts to never unfollow!"
    __tablename__ = 'whitelist'

    id = Column(Integer, Sequence('whitelist_id_seq'), primary_key=True)
    application_id = Column(Integer, ForeignKey('application.id'))
    application = relationship('Application', backref='whitelist_for_taciturn_user')
    taciturn_user_id = Column(Integer, ForeignKey('taciturn_user.id'))
    taciturn_user = relationship('TaciturnUser', backref='whitelist',
                                                 single_parent=True,
                                                 cascade="all, delete-orphan")

    established = Column(DateTime, nullable=False)
    name = Column(String(100), nullable=False)


class Blacklist(ORMBase):
    "Accounts to never follow or deal with!"
    __tablename__ = 'blacklist'

    id = Column(Integer, Sequence('blacklist_id_seq'), primary_key=True)
    application_id = Column(Integer, ForeignKey('application.id'))
    application = relationship('Application', backref='blacklist_for_taciturn_user')
    taciturn_user_id = Column(Integer, ForeignKey('taciturn_user.id'))
    taciturn_user = relationship('TaciturnUser', backref='blacklist',
                                                 single_parent=True,
                                                 cascade="all, delete-orphan")

    established = Column(DateTime, nullable=False)
    name = Column(String(100), nullable=False)


class JobId(ORMBase):
    "where the latest job_id is kept"
    __tablename__ = 'jobid'

    id = Column(Integer, Sequence('jobid_id_seq'), primary_key=True)
    job_id = Column(BigInteger, nullable=False)

