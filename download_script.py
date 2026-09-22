import sys
import os
from yt_dlp import YoutubeDL

def search_artist(artist_name):
    print(f"--- תוצאות חיפוש עבור: '{artist_name}' ---")
    search_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'default_search': 'ytsearch'
    }
    
    with YoutubeDL(search_opts) as ydl:
        results = ydl.extract_info(f"ytsearch15:{artist_name}", download=False)
        songs = results.get('entries', [])

    if not songs:
        print("לא נמצאו שירים.")
        return

    for idx, song in enumerate(songs, 1):
        print(f"[{idx}] {song.get('title')}")

def download_selected(artist_name, selection):
    search_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'default_search': 'ytsearch'
    }
    
    with YoutubeDL(search_opts) as ydl:
        results = ydl.extract_info(f"ytsearch15:{artist_name}", download=False)
        songs = results.get('entries', [])

    if not songs:
        print("לא נמצאו שירים להורדה.")
        return

    selection = selection.strip().lower()
    selected_songs = []

    if selection in ['all', 'הכל']:
        selected_songs = songs
    elif '-' in selection:
        start, end = map(int, selection.split('-'))
        selected_songs = songs[start-1:end]
    else:
        indices = [int(i.strip()) - 1 for i in selection.split(',')]
        selected_songs = [songs[i] for i in indices if 0 <= i < len(songs)]

    print(f"\nמתחיל להוריד {len(selected_songs)} שירים...")
    os.makedirs("music_downloads", exist_ok=True)

    download_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'music_downloads/%(title)s.%(ext)s',
        'quiet': False
    }

    urls = [f"https://www.youtube.com/watch?v={s['id']}" for s in selected_songs]
    
    with YoutubeDL(download_opts) as ydl:
        ydl.download(urls)

    print("\nההורדה הושלמה בהצלחה!")

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else "search"
    artist = sys.argv[2] if len(sys.argv) > 2 else ""
    selection = sys.argv[3] if len(sys.argv) > 3 else "all"

    if mode == "search":
        search_artist(artist)
    elif mode == "download":
        download_selected(artist, selection)
