from soundcloud import SoundCloud
import requests

import os


def get_resolved(client, track_url):
    res = client.resolve(track_url)
    if res.streamable:
        return res
    else:
        return "weird error bro rip"
    
def get_streaming_url(client, track):
    has_prog = False
    for tr in track.media.transcodings:
        if tr.format.protocol == 'progressive':
            prog_url = tr.url
            has_prog = True
    if has_prog == False:
        print("no progressive streaming found -- download likely broken. will try anyways")
        hls_url = tr.url

    if has_prog:
        headers = client.get_default_headers()
        json = requests.get(prog_url, params={"client_id": client.client_id}, headers=headers)
        stream_url = json.json()["url"]

    else:
        headers = client.get_default_headers()
        json = requests.get(hls_url, params={"client_id": client.client_id}, headers=headers)
        stream_url = json.json()["url"]

    return stream_url

def stream_download(client, stream_url, title):
    stream = requests.get(stream_url)

    os.makedirs('dls', exist_ok=True)
    filepath = os.path.join('dls', f"{title}.mp3")

    with open(filepath, 'wb') as output:
        output.write(stream.content)
        print("prolly worked")

    return stream_url


########################################################################

client_id = open("client_id.txt", "r").read()
client = SoundCloud(client_id)
track_url = input("paste pure SC link here (everything before the '?'): ")
res = get_resolved(client, track_url)

stream_download(client, get_streaming_url(client, res), res.title)
