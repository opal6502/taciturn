
from taciturn.applications.twitter import TwitterHandler
from taciturn.applications.bandcamp import GENRE_TAGS

title_string = "Mercury Bow\nby Anvil Mesa"
facebook_link = 'https://www.facebook.com/RBGuy9000/posts/129588192116831'
help_us_string = '𝕎𝕖 𝕣𝕖𝕒𝕝𝕝𝕪 𝕟𝕖𝕖𝕕 𝕪𝕠𝕦𝕣 𝕙𝕖𝕝𝕡! ☑️ 𝕝𝕚𝕜𝕖 ☑️ 𝕔𝕠𝕞𝕞𝕖𝕟𝕥 ☑️ 𝕤𝕙𝕒𝕣𝕖'
genre_tags = ' '.join(GENRE_TAGS['metal'])

my_tweet_text = "{}\n\n{}\n\n{}\n\n{}".format(title_string, facebook_link, help_us_string, genre_tags)

print("Tweet text, length {} chars:".format(len(my_tweet_text)))
print('"{}"'.format(my_tweet_text))

truncated_tweet_text = TwitterHandler.truncate_tweet(my_tweet_text)

print()
print("Truncated tweet text, length {} chars:".format(len(truncated_tweet_text)))
print('"{}"'.format(truncated_tweet_text))
