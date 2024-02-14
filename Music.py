import os
import shutil
import sys
import time
import sqlite3
from io import BytesIO
from subprocess import Popen, PIPE
from tempfile import TemporaryDirectory

import pygame
import requests
import streamlit as st
from streamlit_searchbox import st_searchbox

DB = 'music.db'
st.set_page_config(layout="wide", page_title="Music search")
root = '../../nuc/Music/spring2007' if not sys.argv[1:] else sys.argv[1]


class FWrapper(object):
    def __init__(self, path: str):
        self.path = path
        self.fobj = open(path, 'rb')
        self.type = 0

    def close(self):
        return self.fobj.close()

    def seekable(self):
        return True

    def seek(self, pos):
        return self.fobj.seek(pos)

    def size(self):
        return os.fstat(self.fobj.fileno()).st_size

    def read(self, num):
        return self.fobj.read(num)

    def write(self, buf):
        raise NotImplemented('write')


@st.cache_data(show_spinner=False)
def is_warm() -> float:
    return time.time()


def index(root: str) -> None:
    cnt = 0
    bar = st.progress(0, f'Crawling files {root}')
    files = list(os.walk(root))
    total = sum(len(filenames) for _, _, filenames in files)

    with sqlite3.connect(DB) as conn:
        conn.execute('CREATE VIRTUAL TABLE if not exists songs USING fts5(name, path)')
        conn.execute('CREATE TABLE if not exists played (path varchar, at datetime default current_timestamp)')
        existing = {row[0] for row in conn.execute('select path from songs')}

        for dirp, dirnames, filenames in files:
            cnt += len(filenames)
            bar.progress(cnt / total, f'Indexing {root}')
            for filename, p in [(fn, os.path.join(dirp, fn)) for fn in filenames]:
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


def ensure_vlc():
    status = None
    try:
        status = requests.get('http://:password@localhost:9000/requests/status.xml').status_code
    except IOError:
        pass
    if status != 200:
        with st.spinner('Starting VLC..'):
            p = Popen(['vlc', '--intf=http', '--http-port', '9000', '--http-password=password'], cwd=os.getcwd(), stdin=PIPE)
            p.stdin.close()
            time.sleep(1)


def play(path: str):
    if path:
        pygame.mixer.music.load(FWrapper(path))
        pygame.mixer.music.play()
        with sqlite3.connect(DB) as conn:
            conn.execute('insert into played (path) values (?)', (path,))
    else:
        pygame.mixer.music.stop()


def player():
    if 'song' not in st.session_state:
        st.session_state['song'] = None

    st.markdown('# Music search')

    with sqlite3.connect(DB) as conn:
        # if time.time() - is_warm() < .05:
        #     index(root)
        count = conn.execute("select count(*) from songs").fetchall()[0][0]

        def fts(term: str):
            return conn.execute('select name, path from songs where path match ? ORDER BY rank',
                                (' OR '.join([t.replace('"', '""') + '*' for t in term.split()]),)).fetchall()

        if (selected_value := st_searchbox(fts, key="searchbox",
                                           label=f'{count} songs in {root}')) != st.session_state.song:
            play(selected_value)
            st.session_state.song = selected_value

    st.markdown(f'<iframe src="http://:password@localhost:9000" allow="autoplay" style="width: 100%; overflow: hidden"></iframe>',
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
                        os.makedirs(os.path.join(root, 'youtube'), exist_ok=True)
                        with sqlite3.connect(DB) as conn:
                            for fn in os.listdir(tmpdir):
                                dst = shutil.copy(os.path.join(tmpdir, fn), os.path.join(root, 'youtube'))
                                conn.execute('insert into songs (name, path) values (?, ?)', (fn, dst))
                        st.success(f'Song downloaded successfully and added to library!')

        st.session_state.url = url


page_names_to_funcs = {
    "Player": player,
    "Download": download,
}

selected_page = st.sidebar.selectbox(' ', options=page_names_to_funcs.keys())
page_names_to_funcs[selected_page]()
pygame.mixer.pre_init(buffer=4096)
pygame.mixer.init(buffer=4096)
