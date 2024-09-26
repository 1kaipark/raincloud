"""
Some shared stuff
----
scrape_client_id: uses BeautifulSoup to extract a valid SC client_id from any SC url, using js

DownloadedTrack: a dataclass for storing bytes with filename, size, and a method 'write_to_file' to write bytes to disk easily.

 ／l、
（ﾟ､ ｡ ７
  l  ~ヽ
  じしf_,)ノ
"""

import requests
from bs4 import BeautifulSoup
import re
import tqdm

from dataclasses import dataclass
from io import BytesIO
import os

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

@dataclass
class DownloadedTrack:
    """A container class used to store a file as bytes. This is returned by SCTrack.stream_download().
    
    Attributes
    ----
    fileobj: the file object, in bytes
    filename: given by the user, is literally the filename (not path) with extension
    size: the size in MB of the file

    Methods
    ----
    write_to_file: writes to a specified directory provided as input ('dir' param defaults to os.getcwd())
    """
    fileobj: bytes
    filename: str
    size: float
    
    @classmethod
    def from_bytesio(cls, trackbuffer: BytesIO, filename: str):
        fsize: float = trackbuffer.getbuffer().nbytes/1000000
        return cls(fileobj = trackbuffer.getvalue(), filename=filename, size=fsize)

    def write_to_file(self, dir: str = os.getcwd()) -> None:
        with open(os.path.join(dir, self.filename), 'w+b') as h:
            h.write(self.fileobj)

    def __repr__(self) -> str:
        return "DownloadedTrack({}, {} mb)".format(self.filename, round(self.size, 2))