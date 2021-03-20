#!python

# test clearing a listq!  make sure ORM cascades are working!

from taciturn.config import get_session

from taciturn.db.base import TaciturnUser
from taciturn.listq import ListQueue


session = get_session()

taciturn_user = session.query(TaciturnUser).filter(TaciturnUser.name == 'anvilmesa').one()

am_listq = ListQueue(taciturn_user, 'anvilmesa_bandcamp_discog')

am_listq.clear()
