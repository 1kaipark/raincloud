from raincloud.shared import scrape_client_id
from raincloud import SCTrack
import argparse

parser = argparse.ArgumentParser(
    prog="Stream URL Fetcher",
    description="fetches SC stream URL from browser URL"
)
parser.add_argument('url')
args = parser.parse_args()
cid = open('client_id.txt').read()
t = SCTrack(cid, args.url)

print(t.stream_url)
