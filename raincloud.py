"""
raincloud v2 api, contains SCTrack and SCSet classes with:
* resolve_url, which has loads of important metadata most importantly streaming url
* SCSet has tracks attribute which is a list of SCTracks
* SCTrack has stream_url attribute, with methods stream_download
 ／l、
（ﾟ､ ｡ ７
  l  ~ヽ
  じしf_,)ノ
"""

import requests
import os
import re
from mutagen.id3 import APIC, ID3, TIT2, TPE1
import mutagen
from tqdm import tqdm
from io import BytesIO

from bs4 import BeautifulSoup


def scrape_client_id(src_url: str) -> str:
    """Attempts to pull client_id from soundcloud URL using BeautifulSoup. Method adapted from https://github.com/3jackdaws/soundcloud-lib/tree/master"""
    html_text: str = requests.get(src_url).text
    soup = BeautifulSoup(html_text, "html.parser")

    scripts = soup.findAll("script", attrs={"src": True})
    parsed_cids: list[str] = []
    for script in tqdm(scripts, desc="Searching for client_id..."):
        script_text: str = requests.get(script["src"]).text
        if "client_id" in script_text:
            parsed: str = re.findall(r"client_id=([a-zA-Z0-9]+)", script_text)
            if parsed:
                parsed_cids.append(parsed[0])

    return sorted(parsed_cids, key=lambda v: len(v))[-1]


class SCClientIDError(Exception):
    """For error handling"""

    pass


class TrackSetMismatchError(Exception):
    """Also for error handling"""

    pass


class SCBase:
    """The base class for SC tracks, playlists. Attribute is resolved url, arguments client ID and URL. There's like no reason for a user to import this tbh it's only for inheritance"""

    def __init__(self, client_id: str, sc_url: str):
        self.client_id = client_id

        self.params = {
            "client_id": client_id,
            "url": sc_url,
        }  # parameters to make request to resolve URL

        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
        }  # anything works rly idk

        self.api_url = "https://api-v2.soundcloud.com"  # resolve endpoint

        self._resolved = None

    @property
    def resolved(self) -> dict:
        # the resolved url, contains a whole bunch of metadata, most importantly the streaming URL for the track
        if self._resolved is None:
            response = requests.get(
                f"{self.api_url}/resolve",
                params=self.params,
                headers=self.default_headers,
            )
            if response.status_code == 401:
                raise SCClientIDError("Invalid client_id: {}".format(self.client_id))
            response.raise_for_status()
            self._resolved = response.json()

        return self._resolved

    @property
    def title(self) -> str:
        return self.resolved["title"]

    @property
    def artist(self) -> str:
        return self.resolved["user"]["username"]

    @property
    def artwork_url(self) -> str:
        return self.resolved["artwork_url"]


class SCTrack(SCBase):
    """A single track and all of its information.
    Arguments
    ----
    client_id: a valid soundcloud client ID
    sc_url: the track URL

    Methods
    ----
    I'm ngl cbf to write the rest of the docstring ima do this later
    """

    def __init__(self, client_id: str, sc_url: str):
        super().__init__(client_id, sc_url)

        if "/sets/" in sc_url and 'in=' not in sc_url:
            raise TrackSetMismatchError(
                "URL provided is detected as a set. Please use SCSet instead."
            )

    @property
    def stream_url(self) -> str:
        assert self.resolved["kind"] == "track"

        # progressive check should be up there
        # new function to get this url, return prog url if possible, else return mp3
        has_prog = False
        for tr in self.resolved["media"]["transcodings"]:
            if tr["format"]["protocol"] == "progressive":
                prog_url = tr["url"]
                has_prog = True
        if has_prog == False:
            for tr in self.resolved["media"]["transcodings"]:
                if "mp3" in tr["preset"]:
                    hls_url = tr["url"]
                if not hls_url:
                    print("No MP3 URL found, download is cooked sadly")

        if has_prog:
            result = requests.get(
                prog_url,
                params={"client_id": self.client_id},
                headers=self.default_headers,
            )
            stream_url = result.json()["url"]
        else:
            result = requests.get(
                hls_url,
                params={"client_id": self.client_id},
                headers=self.default_headers,
            )
            stream_url = result.json()["url"]
        return stream_url

    @property
    def progressive_streaming(self) -> bool:
        return not "playlist" in self.stream_url  # 'playlist' in M3U stream URLs

    def stream_download(self, dst_dir: str, metadata=True):
        filename = self.title + ".mp3"  # title of track
        dst = os.path.join(dst_dir, filename)  # output file
        response = requests.get(self.stream_url, stream=True)

        if self.progressive_streaming:
            total_size = int(response.headers.get("content-length", 0))
            if response.status_code == 200:  # if it works...
                with open(dst, "wb") as output:
                    # cooler progress bar
                    for chunk in tqdm(
                        response.iter_content(chunk_size=8192),
                        total=total_size // 8192,
                        unit="chunk",
                        unit_scale=True,
                        desc="Downloading Progressive",
                    ):
                        if chunk:
                            output.write(chunk)
                print(
                    f"{dst} downloaded, size: {round(os.stat(dst).st_size / (1024*1024), 2)} MB."
                )

        else:
            print("HLS streaming, warning SLOW download")
            m3u_playlist = response.content.decode("utf-8")  # m3u8 file to string
            m3u_urls = re.findall(
                re.compile(r"http.*"), m3u_playlist
            )  # get the streaming links as a list

            # TODO: parallel processing possible?
            with open(dst, "wb") as output:
                # download sequentially from m3u url, TQDM used for progress bar
                for i, url in enumerate(
                    tqdm(m3u_urls, desc="Downloading HLS", unit="chunk")
                ):
                    response = requests.get(url, stream=True)
                    for chunk in response.iter_content(chunk_size=8192):
                        output.write(chunk)

        if metadata:
            cover_img = requests.get(self.artwork_url).content

            # Add title and artist
            # add title and artist
            audio_ez = mutagen.File(dst, easy=True)

            if audio_ez.tags is None:
                audio_ez.add_tags()
            audio_ez["title"] = self.title
            audio_ez["artist"] = self.artist
            audio_ez.save()

            # add cover art - can't use easyID3

            audio = mutagen.File(dst)
            audio["APIC"] = APIC(
                encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover_img
            )
            audio.save()
            return audio_ez["title"], audio_ez["artist"]

    def stream_download_wb(self, metadata: bool = True) -> BytesIO:
        buffer: BytesIO = BytesIO()
        response = requests.get(self.stream_url, stream=True)
        if self.progressive_streaming:
            total_size = int(response.headers.get("content-length", 0))
            if response.status_code == 200:  # if it works...
                # cooler progress bar
                for chunk in tqdm(
                    response.iter_content(chunk_size=8192),
                    total=total_size // 8192,
                    unit="chunk",
                    unit_scale=True,
                    desc="Downloading Progressive",
                ):
                    if chunk:
                        buffer.write(chunk)
                print(
                    f"downloaded, size: {round(len(buffer.getvalue()) / (1024*1024), 2)} MB."
                )

        else:
            print("HLS streaming, warning SLOW download")
            m3u_playlist = response.content.decode("utf-8")  # m3u8 file to string
            m3u_urls = re.findall(
                re.compile(r"http.*"), m3u_playlist
            )  # get the streaming links as a list

            # TODO: parallel processing possible?
            # download sequentially from m3u url, TQDM used for progress bar
            for i, url in enumerate(
                tqdm(m3u_urls, desc="Downloading HLS", unit="chunk")
            ):
                response = requests.get(url, stream=True)
                for chunk in response.iter_content(chunk_size=8192):
                    buffer.write(chunk)

        # reset buffer position to start
        buffer.seek(0)

        # add metadata
        if metadata:
            cover_img = requests.get(self.artwork_url).content

            # Add title and artist
            # add title and artist
            audio_ez = mutagen.File(buffer, easy=True)

            if audio_ez.tags is None:
                audio_ez.add_tags()
            audio_ez["title"] = self.title
            audio_ez["artist"] = self.artist
            # audio_ez["APIC"] = APIC(
            #     encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover_img
            # )
            audio_ez.save(buffer)
        buffer.seek(0)
        return buffer

    def __repr__(self) -> str:
        return "SCTrack('{} - {}')".format(self.artist, self.title)


class SCSet(SCBase):
    """This object can be used for a playlist or album or whatever.
    Arguments
    ----
    client_id: a valid soundcloud client ID
    sc_url: the set URL

    Methods
    ----
    I'm ngl cbf to write the rest of the docstring ima do this later

    Attributes
    ----
    tracks: a list of SCTrack objects corresponding to each track in the set.
    """

    def __init__(self, client_id: str, sc_url: str):
        super().__init__(client_id, sc_url)
        if "/sets/" not in sc_url or 'in=' in sc_url:
            raise TrackSetMismatchError(
                "URL is likely a track. Please use SCTrack instead."
            )

    @property
    def tracks(self) -> list[SCTrack]:
        track_urls = []
        for t in self.resolved["tracks"]:
            try:
                track_urls.append(t["permalink_url"])
            except KeyError:
                track_urls.append(
                    requests.get(
                        f"https://api-v2.soundcloud.com/tracks/{t['id']}",
                        params={"client_id": self.client_id},
                        headers=self.default_headers,
                    ).json()["permalink_url"]
                )
        l = []
        for url in track_urls:
            l.append(SCTrack(self.client_id, url))
        return l

    def __repr__(self) -> str:
        return "SCSet({} Tracks)".format(len(self.tracks))
