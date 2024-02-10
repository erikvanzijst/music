import os
import sys
import time
import pandas as pd
from subprocess import Popen, PIPE
from typing import List
from urllib.parse import urlencode, urlparse, urlunparse, quote

import requests
import streamlit as st
from streamlit_searchbox import st_searchbox


st.set_page_config(layout="wide", page_title="Music search")
root = '../../nuc/Music' if not sys.argv[1:] else sys.argv[1]

st.markdown("""
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        #stDecoration {display:none;}
    </style>
""", unsafe_allow_html=True)


def ensure_vlc():
    status = None
    try:
        status = requests.get('http://:password@localhost:9000/requests/status.xml').status_code
    except IOError:
        pass
    if status != 200:
        with st.spinner('Starting VLC..'):
            p = Popen(['vlc', '--intf=http', '--http-port','9000', '--http-password=password'], cwd=os.getcwd(), stdin=PIPE)
            p.stdin.close()
            time.sleep(1)


def play(fn: str):
    ensure_vlc()
    # https://wiki.videolan.org/VLC_HTTP_requests/
    url = urlunparse(urlparse('http://:password@localhost:9000/requests/status.xml')
                     ._replace(query=urlencode(
                         {'command': 'in_play', 'input': fn} if fn else {'command': 'pl_stop'},
                         quote_via=quote)))
    requests.get(url).raise_for_status()
    

if 'song' not in st.session_state:
    st.session_state['song'] = None


@st.cache_data(ttl=3600, show_spinner=False)
def get_library(root: str) -> pd.DataFrame:
    df = pd.DataFrame(columns=['Name', 'Path'])
    
    for dirp, dirnames, filenames in os.walk(root):
        df_ = pd.DataFrame.from_dict({'Path': [os.path.join(dirp, fn) for fn in filenames],
                                      'Name': filenames})
        df = pd.concat([df, df_])
    return df

f"""
# Music search
"""
ensure_vlc()

with st.spinner(f'Indexing {root}'):
    library = get_library(root)

def search(searchterm: str):
    return list(library[library['Name'].str.contains(searchterm, case=False)].itertuples(index=False, name=None))


if (selected_value := st_searchbox(search, key="searchbox", label=f'{len(library)} songs in {root}')) != st.session_state.song:
    ensure_vlc()
    play(selected_value)
    st.session_state.song = selected_value

st.markdown(f'<iframe src="http://:password@localhost:9000" style="width: 100%; overflow: hidden"></iframe>', unsafe_allow_html=True)
