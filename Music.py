import html
import os
import shutil
import sys
import time
import sqlite3
from pathlib import Path
from subprocess import Popen, PIPE
from tempfile import TemporaryDirectory
from typing import Literal
from urllib.parse import urlparse, urlunparse, quote

import eyed3
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, ColumnsAutoSizeMode
from streamlit_javascript import st_javascript
from streamlit_searchbox import st_searchbox

DB = 'music.db'
extensions = {'.mp3', '.flac', '.ogg', '.oga', '.mogg', '.opus', '.vox', '.webm', '.m4a', '.wav', '.wma', '.aac', '.aax', '.m4b'}
st.set_page_config(layout="wide", page_title="🎵 Music")
fs_root = '.' if not sys.argv[1:] else sys.argv[1]
base_url = urlparse(st_javascript("await fetch('').then(r => window.parent.location.href)"))._replace(path='')
ranking_sql = """
    with playcounts as (
            select s.path, s.name, case when pc.cnt is null then 0 else pc.cnt end as playcnt
            from songs s
            left join (select path, count(*) as cnt from played group by path) pc on s.path = pc.path),
        countranks as (
            select playcnt, row_number() over (order by playcnt desc) as rank
            from playcounts
            group by playcnt)
    select pc.name as 'Song', pc.playcnt as 'Count', cr.rank as 'Rank'
    from playcounts pc
    join countranks cr on cr.playcnt = pc.playcnt
    """


@st.cache_data(show_spinner=False)
def is_warm() -> float:
    return time.time()


def align(content: str, direction: Literal['right', 'center'], nowrap=False, unsafe_allow_html=False):
    st.markdown(f'<div style="text-align: {direction}; width: 100%; {"white-space: nowrap;" if nowrap else ""}">'
                f'{content if unsafe_allow_html else html.escape(content)}</div>',
                unsafe_allow_html=True)


def index(root: str) -> None:
    bar = st.progress(0, f'Crawling files {root} ...')
    paths = [str(p) for p in (Path(parent, fn).relative_to(root)
                              for parent, _, fns in os.walk(root)
                              for fn in fns)
             if p.suffix.lower() in extensions]

    with sqlite3.connect(DB) as conn:
        conn.execute('create virtual table if not exists songs using fts5(name, path)')
        conn.execute('create table if not exists played (path varchar not null, at datetime default current_timestamp)')
        conn.execute('create table if not exists tags (path varchar not null, tag varchar not null, primary key (path, tag))')
        conn.execute('delete from songs')

        for idx, p in enumerate(paths, 1):
            bar.progress(idx / len(paths), f'Indexing {idx}/{len(paths)} ...')
            conn.execute('insert into songs (name, path) values (?, ?)', (os.path.basename(p), p))
        bar.empty()


@st.cache_data(show_spinner=False)
def get_rank(path: str) -> int:
    with sqlite3.connect(DB) as conn:
        return int(pd.read_sql_query(f"{ranking_sql} where path = ?", conn, params=[path]).iloc[0]['Rank'])


@st.cache_data(show_spinner=False)
def get_last_played() -> pd.DataFrame:
    with sqlite3.connect(DB) as conn:
        return pd.read_sql_query("""
                select s.name as 'Song'
                from played p
                join songs s on s.path = p.path
                order by p.at desc""", conn)


@st.cache_data(show_spinner=False)
def get_most_played() -> pd.DataFrame:
    with sqlite3.connect(DB) as conn:
        return pd.read_sql_query(f'{ranking_sql} order by rank, path', conn)[['Count', 'Song']]


@st.cache_data(show_spinner=False)
def get_starred() -> pd.DataFrame:
    with sqlite3.connect(DB) as conn:
        return pd.read_sql_query(f'''
            select s.name as 'Song'
            from tags t
            join songs s on s.path = t.path
            left join (select path, max(at) as at from played group by path) p on p.path = t.path
            where t.tag = ?
            order by p.at desc, t.path
            ''', conn, params=['star'])


def star(path: str):
    with sqlite3.connect(DB) as conn:
        conn.execute('insert into tags (path, tag) values (?, ?) on conflict do nothing' if st.session_state.star else
                     'delete from tags where path = ? and tag = ?', [path, 'star'])
        get_starred.clear()


def stats():
    # with st.expander('Stats'):
        last, star, most = st.columns(3)

        with last:
            st.write('🕒 Last played')
            AgGrid(get_last_played(), columns_auto_size_mode=ColumnsAutoSizeMode.FIT_ALL_COLUMNS_TO_VIEW, height=600)
        with last:
            st.write('🏆 Most played')
            AgGrid(get_most_played(), columns_auto_size_mode=ColumnsAutoSizeMode.FIT_ALL_COLUMNS_TO_VIEW, height=600)
        with star:
            st.write('⭐ Starred')
            AgGrid(get_starred(), columns_auto_size_mode=ColumnsAutoSizeMode.FIT_ALL_COLUMNS_TO_VIEW, height=600)


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

        with st.container(border=True):
            if (selected_value := st_searchbox(fts, key="searchbox",
                                               label=f'{count} songs')) != st.session_state.song:
                conn.execute('insert into played (path) values (?)', (selected_value,))
                st.session_state.song = selected_value
                for f in [get_rank, get_last_played, get_most_played]:
                    f.clear()

            url = urlunparse(base_url._replace(path=quote(f'/music/{st.session_state.song}'))) if st.session_state.song else ''
            st.markdown(f"""<audio id="player" controls autoplay="true" src="{url}" style="width: 100%;"></audio>""",
                        unsafe_allow_html=True)
            c1, c2 = st.columns([2, 1])
            if st.session_state.song:
                tag = eyed3.load(os.path.join(fs_root, st.session_state.song))
                starred = bool(conn.execute('select path from tags where tag = ? and path = ?', ['star', st.session_state.song]).fetchone())
                c1.toggle(f'[{"⭐" if starred else "✩"}]  {os.path.basename(st.session_state.song)}',
                          key='star', value=starred, on_change=star, args=(st.session_state.song,))

                with c2:
                    align(f'[🏆 #{get_rank(st.session_state.song)}] [{(tag.info.sample_freq / 1000) if tag else "?"}kHz]',
                          'right')
            else:
                c1.markdown('')


def downloader():
    with st.expander('Download'):
        if 'dl_url' not in st.session_state:
            st.session_state['dl_url'] = None
        if 'dl_log' not in st.session_state:
            st.session_state['dl_log'] = ''
        if 'dl_status' not in st.session_state:
            st.session_state['dl_status'] = lambda: st.empty()

        dl_url = st.text_input('Paste a YouTube URL:', placeholder='https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        placeholder = st.empty()
        log = st.code(st.session_state.dl_log, language='text')

        if dl_url and dl_url != st.session_state.dl_url:
            st.session_state.dl_log = ''
            with TemporaryDirectory() as tmpdir:
                proc = Popen(['yt-dlp', '--extract-audio', '--format', 'bestaudio', '-x', '-o', '%(title)s',
                              '--audio-format', 'mp3', dl_url], cwd=tmpdir, stdin=PIPE, stdout=PIPE)
                try:
                    proc.stdin.close()
                    with placeholder.container(), st.spinner():
                        while line := proc.stdout.readline().replace(b'\r', b'\n').decode('UTF-8'):
                            st.session_state.dl_log += line
                            log.text(st.session_state.dl_log)
                finally:
                    if retval := proc.wait():
                        st.session_state.dl_status = lambda: st.error(f'Download failed ({retval})')
                    else:
                        os.makedirs(os.path.join(fs_root, 'youtube'), exist_ok=True)
                        with sqlite3.connect(DB) as conn:
                            for fn in os.listdir(tmpdir):
                                dst = shutil.copy(os.path.join(tmpdir, fn), os.path.join(fs_root, 'youtube'))
                                dst = str(Path(dst).relative_to(fs_root))
                                conn.execute('insert into songs (name, path) values (?, ?)', (fn, dst))
                        msg = f"Song{'s' if len(os.listdir(tmpdir)) > 1 else ''} downloaded successfully and added to library!"
                        st.session_state.dl_status = lambda: st.success(msg)

            st.session_state.dl_url = dl_url
        st.session_state.dl_status()


player()
downloader()
stats()

align('<a href="https://github.com/erikvanzijst/music">'
      '<img src="https://badgen.net/static/github/code?icon=github">'
      '</a>', 'center', unsafe_allow_html=True)
