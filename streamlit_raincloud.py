import streamlit as st
from raincloud import SCTrack, SCSet
from raincloud.shared import scrape_client_id, test_client_id
from shortcuts.file_io import choose_directory
import os

st.header("RAINCLOUD")

ph = st.empty()

if not os.path.exists("client_id.txt"):
    with open("client_id.txt", "w+") as f:
        with ph.container():
            st.info("scraping client_id...")
            f.write(scrape_client_id())
        ph.empty()

client_id: str = open("client_id.txt").read()
if not test_client_id(client_id):
    with ph.container():
        st.info("scraping client_id...")
        client_id = scrape_client_id()
    ph.empty()
        
    with open("client_id.txt", "w+") as f:
        f.write(client_id)

soundcloud_url = st.text_input(label="SC URL to download...", key='sc_url')

def clear_url_entry():
    st.session_state['sc_url'] = ''

if soundcloud_url:
    with ph.container():
        st.info('downloading track...')
        t = SCTrack(client_id, soundcloud_url)
        dt = t.stream_download()
    ph.empty()
    st.success('Sucessfully downloaded track {} ({} mb)'.format(t.title, dt.size))
    st.download_button(label="Download", data=dt.fileobj, file_name=f"{t.title}.mp3", on_click=clear_url_entry)


