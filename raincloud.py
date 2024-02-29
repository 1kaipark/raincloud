import argparse
from lib.Downloader import Downloader
import os

client_id_filepath = os.path.join('lib', 'client_id.txt')
with open(client_id_filepath, 'r') as client_id_txt:
	client_id = client_id_txt.read().strip()

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description = "simple soundcloud downloader")
	parser.add_argument('sc_url', type = str, help = "soundcloud URL")
	parser.add_argument('--cid', type = str, default = client_id, help = "soundcloud client ID, can be obtained via F12 on refresh.")
	parser.add_argument('--nm', default = False, action = 'store_true', help = 'just download mp3, no metadata')
	parser.add_argument('--a', default = False, action = 'store_true', help = 'include artist (SC username) in file export')

	args = parser.parse_args()

	os.makedirs('dls', exist_ok = True)

	downloader = Downloader(args.cid)

	res_0 = downloader.get_resolved(args.sc_url)

	urls = []
	if res_0.kind == 'track':
	    urls.append(res_0.permalink_url)
	else:
	    urls = downloader.playlist_to_tracks(res_0)

	for track_url in urls:
		res = downloader.get_resolved(track_url)
		stream_url = downloader.get_streaming_url(res)
		filename = f"{res.user.username} - {res.title}" if args.a else res.title

		dest = os.path.join('dls', f"{filename}.mp3")
		downloader.stream_download(stream_url, dest)

		if args.nm == False:
			title, artist = downloader.add_metadata(res, dest)
			print(f"metadata: {title}, {artist}.")

# os.makedirs('dls', exist_ok=True)
# filepath = os.path.join('dls', f"{title}.mp3")
