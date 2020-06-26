
from sqlalchemy.orm import Session
from sqlalchemy import and_, not_

from taciturn.db.base import Whitelist, Blacklist, Application
from taciturn.config import load_config

config = load_config()
engine = config['database_engine']
session = Session(bind=engine)

# grab the twitter entries without @'s and @ them!

non_at_entries = session.query(Whitelist).filter(and_(not_(Whitelist.name.like('@%')),
                                                           Whitelist.application_id == Application.id,
                                                           Application.name == 'twitter'))

for e in non_at_entries.all():
    print("changing '{0}' to '@{0}'".format(e.name))

    new_e = Whitelist(id=e.id,
                      name='@'+e.name,
                      established=e.established,
                      user_id=e.user_id,
                      application_id=e.application_id)
    session.delete(e)
    session.add(new_e)

session.commit()