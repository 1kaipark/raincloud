import requests

import os

from mutagen.id3 import ID3, APIC
import mutagen

class Downloader:
    def __init__(self, client_id):
        self.client_id = client_id
        self.resolve_url = "https://api-v2.soundcloud.com/resolve"
        self.default_headers = {
            "User-Agent" : "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
        }


    def get_resolved(self, track_url):
        params = {
            "client_id" : self.client_id,
            "url" : track_url
        }

        response = requests.get(self.resolve_url, params = params, headers = self.default_headers)
        return response.json()
        
    def get_streaming_url(self, res):
        has_prog = False
        for tr in res['media']['transcodings']:
            if tr['format']['protocol'] == 'progressive':
                prog_url = tr['url']
                has_prog = True
        if has_prog == False:
            print("no progressive streaming found -- download likely broken. will try anyways")
            hls_url = tr['url']   


        if has_prog:
            result = requests.get(
                prog_url,
                params = {
                    "client_id" : self.client_id
                },
                headers = self.default_headers
            )
            stream_url = result.json()['url']
        else:
            result = requests.get(
                hls_url,
                params = {
                    "client_id" : self.client_id
                },
                headers = self.default_headers
            )
            stream_url = result.json()['url']
        return stream_url

    def stream_download(self, stream_url, dest):
        stream = requests.get(stream_url, stream = True)

        with open(dest, 'wb') as output:
            output.write(stream.content)
            print(f"{dest}, size: {round(os.stat(dest).st_size / (1024*1024), 2)} mb.")

        return stream_url

    def add_metadata(self, res, dest):
        # get cover img, save to 'imgpath'
        cover_img = requests.get(res['artwork_url']).content
        imgpath = "coverart.jpg"
        with open(imgpath, 'wb') as img:
            img.write(cover_img)
        
        # add title and artist
        audio_ez = mutagen.File(dest, easy = True)

        if audio_ez.tags is None:
            audio_ez.add_tags()
        audio_ez['title'] = res['title']
        audio_ez['artist'] = res['user']['username']
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

    def playlist_to_tracks(self, res):
        track_urls = []
        print("gathering tracks from set...")
        for t in res['tracks']:
            try:
                track_urls.append(t['permalink_url'])
            except KeyError:
                track_urls.append(
                    requests.get(
                        f"https://api-v2.soundcloud.com/tracks/{t['id']}", 
                        params = {"client_id": self.client_id}, 
                        headers = self.default_headers
                        ).json()['permalink_url']
                    )
        print(f"{len(track_urls)} tracks found.")
        return track_urls
