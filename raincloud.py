import argparse
from lib.raincloud import Downloader
import os

client_id_filepath = os.path.join('lib', 'client_id.txt')
with open(client_id_filepath, 'r') as client_id_txt:
	client_id = client_id_txt.read().strip()

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description = "simple soundcloud downloader")
	parser.add_argument('track_url', type = str, help = "soundcloud URL")
	parser.add_argument('--cid', type = str, default = client_id, help = "soundcloud client ID, can be obtained via F12 on refresh.")
	parser.add_argument('--nm', default = False, action = 'store_true', help = 'just download mp3, no metadata')
	parser.add_argument('--a', default = False, action = 'store_true', help = 'include artist (SC username) in file export')

	args = parser.parse_args()

	downloader = Downloader(args.cid)
	res = downloader.get_resolved(args.track_url)
	stream_url = downloader.get_streaming_url(res)
	filename = f"{res.user.username} - {res.title}" if args.a else res.title
	_, filepath = downloader.stream_download(stream_url, filename)

	if args.nm == False:
		title, artist = downloader.add_metadata(res, filepath)
		print(f"metadata: {title}, {artist}.")
