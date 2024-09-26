import streamlit as st
from raincloud import SCTrack, SCSet
from shortcuts.file_io import choose_directory

st.header("RAINCLOUD")
client_id = st.text_input(label='Enter SC Client ID', value=open('client_id.txt').read())

if client_id:
    soundcloud_url = st.text_input(label='SC URL to download...')
    if soundcloud_url:
        t = SCTrack(client_id, soundcloud_url)
        dt = t.stream_download()
        st.download_button(label='Download', data=dt.fileobj, file_name=f'{t.title}.mp3')
