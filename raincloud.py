from soundcloud import SoundCloud
import requests

import os

from mutagen.id3 import ID3, APIC
import mutagen

class Downloader:
    def __init__(self, client_id):
        self.client = SoundCloud(client_id)

    def get_resolved(self, track_url):
        res = self.client.resolve(track_url)
        if res.streamable:
            return res
        else:
            return "weird error bro rip"
        
    def get_streaming_url(self, track):
        has_prog = False

        for tr in track.media.transcodings:
            if tr.format.protocol == 'progressive':
                prog_url = tr.url
                has_prog = True
                break
        if not has_prog:
            print("no progressive streaming found -- download likely broken. will try anyways")
            hls_url = tr.url

        headers = self.client.get_default_headers()
        if has_prog:
            json = requests.get(prog_url, params={"client_id": self.client.client_id}, headers=headers)
            stream_url = json.json()["url"]
        else:
            json = requests.get(hls_url, params={"client_id": self.client.client_id}, headers=headers)
            stream_url = json.json()["url"]

        return stream_url

    def stream_download(self, stream_url, title):
        stream = requests.get(stream_url)

        os.makedirs('dls', exist_ok=True)
        filepath = os.path.join('dls', f"{title}.mp3")

        with open(filepath, 'wb') as output:
            output.write(stream.content)
            print(f"{title}.mp3, size: {round(os.stat(filepath).st_size / (1024*1024), 2)} mb.")

        return stream_url, filepath

    def add_metadata(self, track, filepath):
        # get cover img, save to 'imgpath'
        cover_img = requests.get(track.artwork_url).content
        os.makedirs('dls', exist_ok=True)
        imgpath = os.path.join('dls', f"coverart.jpg")
        with open(imgpath, 'wb') as img:
            img.write(cover_img)
        
        # add title and artist
        audio_ez = mutagen.File(filepath, easy = True)

        if audio_ez.tags is None:
            audio_ez.add_tags()
        audio_ez['title'] = track.title
        audio_ez['artist'] = track.user.username
        audio_ez.save()

        # add cover art - can't use easyID3

        audio = mutagen.File(filepath)
        with open(imgpath, 'rb') as coverart:
            audio['APIC'] = APIC(
                encoding = 3,
                mime = 'image/jpeg',
                type = 3,
                desc = u'Cover',
                data = coverart.read()
            )
        audio.save()

        os.remove(imgpath)


########################################################################


client_id = open("client_id.txt", "r").read()
downloader = Downloader(client_id)
track_url = input("paste pure SC link here (everything before the '?'): ")
res = downloader.get_resolved(track_url)

_, filepath = downloader.stream_download(downloader.get_streaming_url(res), res.title)
downloader.add_metadata(res, filepath)
