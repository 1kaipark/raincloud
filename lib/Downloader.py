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
        try:
            if res.streamable:
                return res
            else:
                return "weird error bro rip"
        except AttributeError:
            print("playlist or album detected...")
            return res
        
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

    def stream_download(self, stream_url, dest):
        stream = requests.get(stream_url)

        with open(dest, 'wb') as output:
            output.write(stream.content)
            print(f"{dest}, size: {round(os.stat(dest).st_size / (1024*1024), 2)} mb.")

        return stream_url

    def add_metadata(self, track, dest):
        # get cover img, save to 'imgpath'
        cover_img = requests.get(track.artwork_url).content
        imgpath = "coverart.jpg"
        with open(imgpath, 'wb') as img:
            img.write(cover_img)
        
        # add title and artist
        audio_ez = mutagen.File(dest, easy = True)

        if audio_ez.tags is None:
            audio_ez.add_tags()
        audio_ez['title'] = track.title
        audio_ez['artist'] = track.user.username
        audio_ez.save()

        # add cover art - can't use easyID3

        audio = mutagen.File(dest)
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
        return audio_ez['title'], audio_ez['artist']

    def playlist_to_tracks(self, track):
        track_urls = []
        print("gathering tracks from set...")
        for t in track.tracks:
            try:
                track_urls.append(t.permalink_url)
            except AttributeError:
                track_urls.append(self.client.get_track(t.id).permalink_url)
        print(f"{len(track_urls)} tracks found.")
        return track_urls
