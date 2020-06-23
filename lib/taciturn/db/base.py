
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
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

ORMBase = declarative_base()


class Application(ORMBase):
    "An application, like twitter, instagram, facebook, youtube ..."
    __tablename__ = 'application'

    id = Column(Integer, primary_key=True)

    established = Column(DateTime, nullable=False)
    name = Column(String(100), unique=True, nullable=False)


class User(ORMBase):
    "An user of an application!"
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('application.id'))
    application = relationship('Application', backref='users')

    # XXX need to create a constraint where every app & user pair must be unique!
    established = Column(DateTime, nullable=False)
    name = Column(String(500), nullable=False)

    # a user will just be a way of grouping app accounts:
    # password = Column(String(500), nullable=False)


class AppAccount(ORMBase):
    # an account for an application, a user may have many
    __tablename__ = 'app_account'

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('application.id'))
    application = relationship('Application', backref='app_accounts')
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', backref='app_accounts')

    established = Column(DateTime, nullable=False)

    name = Column(String(500), nullable=False)
    password = Column(String(500), nullable=False)


class Whitelist(ORMBase):
    "Accounts to never unfollow!"
    __tablename__ = 'whitelist'

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('application.id'))
    application = relationship('Application', backref='whitelist_for_user')
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', backref='whitelist')

    established = Column(DateTime, nullable=False)
    name = Column(String(100), unique=True, nullable=False)


class Blacklist(ORMBase):
    "Accounts to never follow or deal with!"
    __tablename__ = 'blacklist'

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('application.id'))
    application = relationship('Application', backref='blacklist__for_user')
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', backref='blacklist')

    established = Column(DateTime, nullable=False)
    name = Column(String(100), unique=True, nullable=False)


# Taciturn data related exceptions:

class DataException(Exception):
    pass


class DataExtraRowException(DataException):
    pass

