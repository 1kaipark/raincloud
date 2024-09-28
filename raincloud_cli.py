import argparse
from raincloud import SCTrack, SCSet
from raincloud.shared import test_client_id, scrape_client_id
from raincloud.exceptions import TrackSetMismatchError
import os

client_id_filepath = "client_id.txt"
with open(client_id_filepath, "r") as client_id_txt:
    client_id = client_id_txt.read().strip()

if not test_client_id(client_id):
    client_id = scrape_client_id()
    with open(client_id_filepath, 'w+') as h:
        h.write(client_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="simple soundcloud downloader")
    parser.add_argument("sc_url", type=str, help="soundcloud URL")
    parser.add_argument(
        "--cid",
        type=str,
        default=client_id,
        help="soundcloud client ID, can be obtained via F12 on refresh.",
    )
    parser.add_argument(
        "--nm",
        default=False,
        action="store_true",
        help="just download mp3, no metadata",
    )
    args = parser.parse_args()

    os.makedirs("dls", exist_ok=True)
    client_id: str = args.cid
    download_completed: bool = False

    while not download_completed:
        try:
            sc = SCTrack(client_id, args.sc_url)
            stream_url = sc.stream_url
            dt = sc.stream_download(metadata=(not args.nm))
            dt.write_to_file()
            download_completed = True

        except TrackSetMismatchError as e:
            cont = input("Playlist/set detected. Would you like to download all? (Y/n)")
            if cont.lower() == "y":
                set = SCSet(client_id, args.sc_url)
                for track in set.tracks:
                    dt = track.stream_download()
                    dt.write_to_file()
            else:
                ...
            download_completed = True
            
