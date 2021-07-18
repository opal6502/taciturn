
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

# Facebook data stuff!

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Sequence
from sqlalchemy.orm import relationship

from taciturn.db.base import ORMBase


class FacebookPage(ORMBase):
    "A facebook page"
    __tablename__ = 'facebook_page'

    id = Column(Integer, Sequence('facebook_page_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', backref='pages')
    # application_id = Column(Integer, ForeignKey('application.id')) # -- app will always be 'facebook'?
    # application = relationship('Application', backref='pages')

    established = Column(DateTime, nullable=False)
    name = Column(String(300), nullable=False)


class FacebookPagePost(ORMBase):
    "A facebook page post"
    __tablename__ = 'facebook_page_post'

    id = Column(Integer, Sequence('facebook_page_post_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', backref='page_posts')
    # application_id = Column(Integer, ForeignKey('application.id')) # -- app will always be 'facebook'?
    # application = relationship('Application', backref='page_posts')
    page_id = Column('FacebookPage', ForeignKey('facebook_page.id'))
    page = relationship('FacebookPage', backref='pages')

    established = Column(DateTime, nullable=False)
    name = Column(String(300), nullable=False)


class FacebookGroup(ORMBase):
    "A facebook group"
    __tablename__ = 'facebook_group'

    id = Column(Integer, Sequence('facebook_group_id_seq'), primary_key=True)

    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', backref='pages')
    # application_id = Column(Integer, ForeignKey('application.id')) # -- app will always be 'facebook'?
    # application = relationship('Application', backref='pages')

    established = Column(DateTime, nullable=False)
    url_path = Column(String(300), nullable=False)


class FacebookGroupShare(ORMBase):
    "A record of sharing a page post to a group"
    __tablename__ = 'facebook_group_share'

    id = Column(Integer, Sequence('facebook_group_share_seq'), primary_key=True)

    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', backref='page_posts')
    page_id = Column(Integer, ForeignKey('facebook_page.id'))
    page = relationship('FacebookPage', backref='page')
    post_id = Column(Integer, ForeignKey('facebook_page_post.id'))
    post = relationship('FacebookPagePost', backref='post')
    group_id = Column(Integer, ForeignKey('facebook_group.id'))
    group = relationship('FacebookGroup', backref='group')

    established = Column(DateTime(timezone=False), nullable=False)
    url_path = Column(String(300), nullable=False)
