import os
import shutil
import sys
import time
import sqlite3
from pathlib import Path
from subprocess import Popen, PIPE
from tempfile import TemporaryDirectory
from urllib.parse import urlparse, urlunparse, quote

import streamlit as st
from streamlit_javascript import st_javascript
from streamlit_searchbox import st_searchbox

DB = 'music.db'
st.set_page_config(layout="wide", page_title="Music search")
fs_root = '.' if not sys.argv[1:] else sys.argv[1]
base_url = urlparse(st_javascript("await fetch('').then(r => window.parent.location.href)"))._replace(path='')


@st.cache_data(show_spinner=False)
def is_warm() -> float:
    return time.time()


def index(root: str) -> None:
    cnt = 0
    bar = st.progress(0, f'Crawling files {root}')
    files = list(os.walk(root))
    total = sum(len(filenames) for _, _, filenames in files)

    with sqlite3.connect(DB) as conn:
        conn.execute('create virtual table if not exists songs USING fts5(name, path)')
        conn.execute('create table if not exists played (path varchar, at datetime default current_timestamp)')
        existing = {row[0] for row in conn.execute('select path from songs')}

        for dirp, dirnames, filenames in files:
            cnt += len(filenames)
            bar.progress(cnt / total, f'Indexing {root}')
            for filename, p in [(fn, str(Path(os.path.join(dirp, fn)).relative_to(root))) for fn in filenames]:
                if p not in existing:
                    conn.execute('insert into songs (name, path) values (?, ?)', (filename, p))
                existing.discard(p)
        if existing:
            bar.progress(1.0, f'Dropping {len(existing)} removed songs...')
            conn.executemany('delete from songs where path = ?', [(p,) for p in existing])
        bar.empty()


st.markdown("""
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)


def player():
    if 'song' not in st.session_state:
        st.session_state['song'] = None

    with sqlite3.connect(DB) as conn:
        if time.time() - is_warm() < .05:
            index(fs_root)
        count = conn.execute("select count(*) from songs").fetchall()[0][0]

        def fts(term: str):
            return conn.execute('select name, path from songs where path match ? ORDER BY rank',
                                (' OR '.join([t.replace('"', '""') + '*' for t in term.split()]),)).fetchall()

        if (selected_value := st_searchbox(fts, key="searchbox",
                                           label=f'{count} songs in {fs_root}')) != st.session_state.song:
            with sqlite3.connect(DB) as conn:
                conn.execute('insert into played (path) values (?)', (selected_value,))
            st.session_state.song = selected_value
        url = urlunparse(base_url._replace(path=quote(f'/music/{st.session_state.song}'))) if st.session_state.song else ''
        st.markdown(f"""<audio id="player" controls autoplay="true" src="{url}" style="width: 100%;"></audio>""",
                    unsafe_allow_html=True)


def download():
    if 'url' not in st.session_state:
        st.session_state['url'] = None
    if 'dl_log' not in st.session_state:
        st.session_state['dl_log'] = ''

    url = st.text_input('Paste a YouTube URL:', placeholder='https://www.youtube.com/watch?v=dQw4w9WgXcQ')
    placeholder = st.empty()
    log = st.code(st.session_state.dl_log)
    info = st.empty()

    if url and url != st.session_state.url:
        print(f'{url}')
        info.empty()
        st.session_state.dl_log = ''
        with TemporaryDirectory() as tmpdir:
            proc = Popen(['yt-dlp', '--extract-audio', '--format', 'bestaudio', '-x', '-o', '%(title)s',
                          '--audio-format', 'mp3', url], cwd=tmpdir, stdin=PIPE, stdout=PIPE)
            try:
                proc.stdin.close()
                stdout: str = ''
                with placeholder.container():
                    with st.spinner():
                        while line := proc.stdout.readline().replace(b'\r', b'\n').decode('UTF-8'):
                            log.text(stdout := (stdout + line))
            finally:
                with info:
                    if retval := proc.wait():
                        st.error(f'Download failed ({retval})')
                    else:
                        os.makedirs(os.path.join(fs_root, 'youtube'), exist_ok=True)
                        with sqlite3.connect(DB) as conn:
                            for fn in os.listdir(tmpdir):
                                dst = shutil.copy(os.path.join(tmpdir, fn), os.path.join(fs_root, 'youtube'))
                                dst = str(Path(dst).relative_to(fs_root))
                                print(f'Indexing {dst}')
                                conn.execute('insert into songs (name, path) values (?, ?)', (fn, dst))
                        st.success(f"Song{'s' if len(os.listdir(tmpdir)) > 1 else ''} "
                                   f"downloaded successfully and added to library!")

        st.session_state.url = url


pages = {
    "Player": player,
    "Download": download,
}
selected_page = st.sidebar.selectbox(' ', options=pages.keys())
pages[selected_page]()
