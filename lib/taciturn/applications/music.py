
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


from abc import abstractmethod

from taciturn.applications.base import BaseApplicationHandler


class MusicScrapingHandler(BaseApplicationHandler):
    tmp_file_prefix = 'music-scraper'

    def music_scrape_track_data(self, track_url):
        self.driver.get(track_url)

        track_artist = self.music_scrape_artist()
        track_title = self.music_scrape_title()
        track_album = self.music_scrape_album()
        track_art_url = self.music_scrape_art_url()

        track_art_file = self.temp_download_file(track_art_url, prefix=self.tmp_file_prefix)

        return TrackData(
            url=track_url,
            artist=track_artist,
            title=track_title,
            album=track_album,
            img_local=track_art_file
        )

    @abstractmethod
    def music_scrape_artist(self):
        pass

    @abstractmethod
    def music_scrape_title(self):
        pass

    @abstractmethod
    def music_scrape_album(self):
        pass

    @abstractmethod
    def music_scrape_art_url(self):
        pass


class TrackData:
    _field_names = {'url', 'title', 'artist', 'album', 'label', 'img_local'}

    def __init__(self, **kwargs):
        # pycharm likes this:
        self.url = None
        self.title = None
        self.artist = None
        self.album = None
        self.label = None
        self.img_local = None

        for k in kwargs:
            if k not in self._field_names:
                raise TypeError(f"Invalid field '{k}'")
        self.__dict__.update(kwargs)

    def __str__(self):
        if self.album is not None:
            track_str = (self.title+'\n'+
                         'from '+self.album+' by '+self.artist)
        else:
            track_str = (self.title+'\n'+
                         'by '+self.artist)
        return track_str


# it's important to order these tags by priority so that when twitter truncates the list, the best possible combo
# is still present, and 30 max for facebook, not sure about instagram:

GENRE_TAGS = {
    'idm': ['#music', '#bandcamp', '#radio', '#electronicmusic', '#electronic', '#idm', '#synthesizer', '#synth',
            '#breakbeat', '#drummachine', '#acid', '#beats', '#song', '#artist', '#dance', '#intelligent',
            '#musicproducer', '#producer', '#musician', '#art',  '#nowplaying', '#musicstreaming', '#musiclover',
            '#love', '#like', '#follow', '#life', '#friends', '#goodmusic', '#indie'],
    'techno': ['#music', '#bandcamp', '#radio', '#electronicmusic', '#electronic', '#techno', '#synthesizer', '#synth',
            '#breakbeat', '#drummachine', '#acid', '#beats', '#song', '#artist', '#dance', '#party',
            '#musicproducer', '#producer', '#musician', '#art',  '#nowplaying', '#musicstreaming', '#musiclover',
            '#love', '#like', '#follow', '#life', '#friends', '#goodmusic', '#indie'],
    'ambient': ['#music', '#bandcamp', '#radio', '#electronicmusic', '#electronic', '#ambient', '#synthesizer', '#synth',
            '#modular', '#atmosphere', '#mood', '#song', '#artist', '#drone', '#soundscape', '#soft',
            '#musicproducer', '#producer', '#musician', '#art',  '#nowplaying', '#musicstreaming', '#musiclover',
            '#love', '#like', '#follow', '#life', '#friends', '#goodmusic', '#indie'],
    'industrial': ['#music', '#bandcamp', '#radio', '#industrialmusic', '#industrial', '#electronic', '#synthesizer',
            '#synth', '#ebm', '#guitar', '#metal', '#distortion', '#song', '#artist', '#dance', '#party',
            '#musicproducer', '#producer', '#musician', '#art',  '#nowplaying', '#musicstreaming', '#musiclover',
            '#love', '#like', '#follow', '#life', '#friends', '#goodmusic', '#indie'],
    'experimental': ['#music', '#bandcamp', '#radio', '#experimentalmusic', '#experimental', '#electronic', '#synthesizer',
            '#tape', '#samples', '#foundsound', '#noise', '#atmosphere', '#song', '#artist', '#intelligent', '#sfx',
            '#musicproducer', '#producer', '#musician', '#art', '#nowplaying', '#musicstreaming', '#musiclover',
            '#love', '#like', '#follow', '#life', '#friends', '#goodmusic', '#indie'],
    'rock': ['#music', '#bandcamp', '#radio', '#rockmusic', '#rock', '#alternative', '#guitar',
            '#classicrock', '#indie', '#foundsound', '#noise', '#atmosphere', '#song', '#artist', '#rocknroll',
             '#guitar', '#rockband', '#producer', '#musician', '#art', '#nowplaying', '#musicstreaming', '#musiclover',
            '#love', '#like', '#follow', '#life', '#friends', '#goodmusic', '#indie'],
    'metal': ['#music', '#bandcamp', '#radio', '#metalmusic', '#metal', '#metalband', '#technicaldeathmetal',
             '#techdeath', '#deathcore', '#doommetal', '#death', '#metalheads', '#thrashmetal', '#thrash', '#blackmetal',
             '#extrememetal', '#guitar', '#band', '#musician', '#art', '#nowplaying', '#musicstreaming', '#musiclover',
             '#love', '#like', '#follow', '#life', '#friends', '#goodmusic', '#indie'],
}


class Genres:
    @staticmethod
    def all():
        return sorted(GENRE_TAGS.keys())

    @staticmethod
    def all_string():
        return ', '.join({f"'{g}'" for g in sorted(GENRE_TAGS.keys())})

    @staticmethod
    def tags_string(genre):
        try:
            return ' '.join(GENRE_TAGS[genre])
        except KeyError:
            raise GenereException(f"No such genre '{genre}'")

    @staticmethod
    def in_(genre):
        return genre in GENRE_TAGS

    @staticmethod
    def not_in_(genre):
        return genre not in GENRE_TAGS


class GenereException(Exception):
    pass
