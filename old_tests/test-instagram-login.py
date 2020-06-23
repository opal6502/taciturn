
from taciturn.handlers.instagram import InstagramHandler

username = 'rbguy9000'
password = 'f0rtify%47A'
config = dict()

ig = InstagramHandler(username, password, config)

ig.login()

print("Logged in ok!??")
