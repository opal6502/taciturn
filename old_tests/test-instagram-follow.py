
from taciturn.handlers.instagram import InstagramHandler

username = 'rbguy9000'
password = 'f0rtify%47A'

ig = InstagramHandler(username, password)

ig.login()
ig.start_following("warprecords")

