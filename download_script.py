import html
import os
import sys
from pathlib import Path

from flask import Flask, request, send_from_directory
from yt_dlp import YoutubeDL

app = Flask(__name__)
DOWNLOAD_DIR = Path("music_downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      max-width: 900px;
      margin: 40px auto;
      padding: 0 20px;
      background: #f5f6fb;
      color: #1f2937;
    }}
    main {{
      background: white;
      padding: 30px;
      border-radius: 16px;
      box-shadow: 0 6px 20px rgba(0,0,0,0.08);
    }}
    h1, h2 {{ margin-top: 0; }}
    input, button {{
      font-size: 16px;
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid #cbd5e1;
    }}
    input[type=text] {{ width: 72%; }}
    button {{
      background: #4f46e5;
      color: white;
      border: none;
      cursor: pointer;
      margin-right: 8px;
    }}
    ul {{ line-height: 1.8; }}
    .error {{ color: #b91c1c; }}
    a {{ color: #4338ca; }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(title)}</h1>
    {body}
  </main>
</body>
</html>"""


def search_songs(query: str):
    search_opts = {
        "quiet": True,
        "extract_flat": "in_playlist",
        "default_search": "ytsearch",
        "skip_download": True,
    }
    with YoutubeDL(search_opts) as ydl:
        results = ydl.extract_info(f"ytsearch15:{query}", download=False)
    entries = results.get("entries", []) if isinstance(results, dict) else []
    return [entry for entry in entries if entry]


def get_song_url(song):
    if not song:
        return ""
    return (
        song.get("webpage_url")
        or song.get("url")
        or (f"https://www.youtube.com/watch?v={song.get('id')}" if song.get("id") else "")
    )


@app.get("/")
def index():
    return page(
        "🎵 הורדת מוזיקה",
        """
        <form action="/search" method="get">
          <input type="text" name="q" placeholder="חפש זמר, שיר או אמן" required>
          <button type="submit">חיפוש</button>
        </form>
        <p>הקלד שם של זמר או שיר כדי לחפש ולבחור שירים להורדה.</p>
        """,
    )


@app.get("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return page("שגיאה", '<p class="error">נא להזין טקסט לחיפוש.</p>'), 400

    try:
        songs = search_songs(query)
    except Exception as exc:
        return page("שגיאה", f'<p class="error">שגיאה בחיפוש: {html.escape(str(exc))}</p>'), 500

    if not songs:
        return page("אין תוצאות", f'<p>לא נמצאו תוצאות עבור {html.escape(query)}.</p><p><a href="/">חזור</a></p>')

    items = "".join(
        f'<li><label><input type="checkbox" name="url" value="{html.escape(get_song_url(song), quote=True)}"> '
        f'{html.escape(song.get("title", "ללא כותרת"))}</label></li>'
        for song in songs
    )

    return page(
        "תוצאות חיפוש",
        f"""
        <h2>תוצאות עבור: {html.escape(query)}</h2>
        <form action="/download" method="post">
          <ol>{items}</ol>
          <button type="submit">הורד את המסומנים</button>
        </form>
        <p><a href="/">חיפוש חדש</a></p>
        """,
    )


@app.post("/download")
def download():
    urls = request.form.getlist("url")
    if not urls:
        return page("שגיאה", '<p class="error">נא לבחור לפחות שיר אחד.</p><p><a href="/">חזרה</a></p>'), 400

    DOWNLOAD_DIR.mkdir(exist_ok=True)
    download_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    try:
        with YoutubeDL(download_opts) as ydl:
            ydl.download(urls)
    except Exception as exc:
        return page("שגיאה", f'<p class="error">שגיאה בהורדה: {html.escape(str(exc))}</p><p><a href="/">חזרה</a></p>'), 500

    mp3_files = sorted(DOWNLOAD_DIR.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
    links = "".join(
        f'<li><a href="/files/{html.escape(file.name, quote=True)}">{html.escape(file.name)}</a></li>'
        for file in mp3_files[: len(urls)]
    )

    return page(
        "ההורדה הושלמה ✅",
        f"""
        <p>הקבצים מוכנים להורדה:</p>
        <ul>{links}</ul>
        <p><a href="/">חיפוש נוסף</a></p>
        """,
    )


@app.get("/files/<path:filename>")
def serve_file(filename: str):
    return send_from_directory(str(DOWNLOAD_DIR), filename, as_attachment=True)


def cli_search_mode(query: str):
    songs = search_songs(query)
    for index, song in enumerate(songs, 1):
        print(f"[{index}] {song.get('title')}")


def cli_download_mode(query: str, selection: str):
    songs = search_songs(query)
    if not songs:
        print("לא נמצאו שירים.")
        return

    selected = []
    selection = selection.strip().lower()
    if selection in ["all", "הכל"]:
        selected = songs
    elif "-" in selection:
        try:
            start, end = map(int, selection.split("-"))
            selected = songs[start - 1:end]
        except ValueError:
            print("פורמט בחירה לא תקין. השתמש: all / 1-5 / 1,3,4")
            return
    else:
        try:
            indices = [int(i.strip()) - 1 for i in selection.split(",")]
            selected = [songs[i] for i in indices if 0 <= i < len(songs)]
        except ValueError:
            print("פורמט בחירה לא תקין. השתמש: all / 1-5 / 1,3,4")
            return

    DOWNLOAD_DIR.mkdir(exist_ok=True)
    urls = [get_song_url(song) for song in selected if get_song_url(song)]
    if not urls:
        print("לא נמצאו קישורי שירים להורדה.")
        return

    download_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    with YoutubeDL(download_opts) as ydl:
        ydl.download(urls)


if __name__ == "__main__":
    # GitHub Actions / CLI usage still works if arguments are passed.
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "search":
            query = sys.argv[2] if len(sys.argv) > 2 else ""
            cli_search_mode(query)
        elif mode == "download":
            query = sys.argv[2] if len(sys.argv) > 2 else ""
            selection = sys.argv[3] if len(sys.argv) > 3 else "all"
            cli_download_mode(query, selection)
        else:
            print("Use: python download_script.py search <artist> or python download_script.py download <artist> <selection>")
    else:
        port = int(os.environ.get("PORT", "8080"))
        app.run(host="0.0.0.0", port=port)
