
from taciturn.handlers.twitter import TwitterHandler

username = 'AnvilMesa'
password = 'f0rtify%47B'

tw = TwitterHandler(username, password)

tw.login()
tw.start_following("WarpRecords")
