import streamlit as st
from raincloud import SCTrack, SCSet
from raincloud.shared import scrape_client_id, test_client_id
from shortcuts.file_io import choose_directory
import os

st.header("RAINCLOUD")

if not os.path.exists('client_id.txt'):
    with open('client_id.txt', 'w+') as f:
        f.write(scrape_client_id())

client_id: str = open('client_id.txt').read()
if not test_client_id(client_id):
    client_id = scrape_client_id()
    with open('client_id.txt', 'w+') as f:
        f.write(client_id)

soundcloud_url = st.text_input(label='SC URL to download...')
if soundcloud_url:
    t = SCTrack(client_id, soundcloud_url)
    dt = t.stream_download()
    st.download_button(label='Download', data=dt.fileobj, file_name=f'{t.title}.mp3')
