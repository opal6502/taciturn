# Taciturn Social Media Automation Framework

Taciturn is a Python/Selenium tool and framework for automating social media tasks.

For current development notes, please see my [Evernote Document](https://www.evernote.com/l/AtC6SBcYqJ9Iu6mm9uSS8M5NUJIUPXLQZ7U) on this.  The current development version is ```v0.4a```!  It has some very useful features but has only been used on my personal development system!

This documentation is pretty minimal, but I can make it better upon request!  This is a good, free tool to help kick-start a the social media presence of a project your believe in!

Also, while this is an extremely useful tool, it does require some programming and system knowledge in order to fully configure and run it!  Comparable tools could literally cost you $5-10+ per month (per service!), but I'm writing a tool to do this as a programming exercise, please tell your friends or donate if you found Taciturn useful.

## Features

Taciturn has some nice features, and I'm trying to make it easy to write more!

There are automated jobs to:

- Targeted follow/unfollow the maximum daily amount from Twitter and Instagram and Soundcloud
- Relatively easy-to-configure time thresholds to maintain mutual follows, unfollow non-mutuals after several days.
- Make automated Tweets
- Make automated Facebook posts
- There is code to make automated Instagram posts, but it is very temperamental and won't run in headless mode
- Scrape data from Bandcamp pages (for my radio station project)
- I'm trying to make the code base as nice as possible using Python OOP to maintain and extend!

Currently, the user interface is pretty raw, so if you're comfortable editing Python structures as a config file, it's really great.  I plan to add a config web UI ... eventually.

Also, if you're comfortable writing python, it's pretty easy to write custom job files, although most everything you want to do will be provided, already.

## Installing

Download or clone the repository, it's recommended that you create your own Python venv.  Install the packages in ```requirements.txt```

You need to edit the ```conf/taciturn.sh``` to set the ```TACITURN_PROJECT_ROOT```, ```TACITURN_ROOT```, ```TACITURN_VENV```  and ```WEBDRIVER_BIN``` environment variables.

Then, you have to initialize the database:

```shell script
cd $TACITURN_ROOT/bin
. ../conf/taciturn.sh    # includes venv activate
python init_db.py        # initalize db schema and define applications:
                         # 'twitter', 'instagram', 'facebook', 'soundcloud'
```

## Administering

The ```bin/taciturn_admin.py``` script is provided to add/remove taciturn users, add/remove application accounts, add/remove names from whitelists/blacklists.  You have to provide a taciturn user before running any jobs.

Run ```'bin/taciturn_admin.py help'``` to get decent command help: 

```shell script
cd $TACITURN_ROOT/bin
. ../conf/taciturn.sh    # includes venv activate
python taciturn_admin.py help     # get help!
```

## Configuring

Taciturn provides a ```conf/site_config.py``` for local settings.  There are settings for how many follows to do per day, and you can break down each quota in a number of rounds, to divide the quota into segments to run over the course of a day.  The day can also be configured, usually 6-12 hours.

## Running from the CLI 

Taciturn is being developed in a Macintosh/UNIX environment, and thus

```shell script
cd $TACITURN_ROOT/bin
. ../conf/taciturn.sh    # includes venv activate
python taciturn_cli.py -u taciturn_user -j twitter_follow -s -t target_account
```

## Running from Jenkins or other CI (recommended)

Ideally, Taciturn jobs will be run from a CI tool such as Jenkins.  A typical Taciturn job script within Jenkins will look like this:

```shell script
cd $TACITURN_ROOT/bin
. ../conf/taciturn.sh    # includes venv activate
python taciturn_cli.py -u taciturn_user -j twitter_follow -s -t target_account
```

## Compatibility

I've been developing Taciturn using the webdrivers for Chrome and Firefox on Macintosh.  I've been using SQLite, and just recently PosgreSQL, for a database.  SQLite should probably be good enough for most people.  I welcome help to increase OS and database compatibility!

# License

[GNU General Public License (GPL)](https://www.gnu.org/licenses/) - free to copy and the source code will always be free!

# Donations

If you found the Taciturn web framework useful, please consider making a donation!

We can receive donations via PayPal at ```taciturnautomation at gmail.com```
