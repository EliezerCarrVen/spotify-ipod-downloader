import os
import yt_dlp

ydl_opts = {
    'quiet': False,
    'extract_flat': True,
    'cookiefile': 'cookies.txt',
    'remote_components': ['ejs:github'],
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info("https://www.youtube.com/feed/playlists", download=False)
        if 'entries' in info:
            for entry in info['entries'][:2]:
                print(f"Playlist: {entry.get('title')}, URL: {entry.get('url')} or {entry.get('id')}")
                # Now extract first playlist
                url = entry.get('url') or f"https://www.youtube.com/playlist?list={entry.get('id')}"
                print(f"Extracting inner: {url}")
                inner_info = ydl.extract_info(url, download=False)
                entries = inner_info.get('entries', [])
                if not entries:
                    # sometimes entries is a generator
                    entries = list(entries)
                print(f"Inner entries count: {len(entries)}")
                for e in list(entries)[:3]:
                    print(f"  - {e.get('title')}")
except Exception as e:
    print(f"Error: {e}")
