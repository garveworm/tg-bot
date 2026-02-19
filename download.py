import sys
from yt_dlp import YoutubeDL


def download_reel(url: str, outdir: str = "."):
    ydl_opts = {
        # Best video+audio merged
        "format": "bv*+ba/b",
        # Output name: author - title - id.mp4
        "outtmpl": f"{outdir}/%(uploader)s - %(title).80s - %(id)s.%(ext)s",
        # mp4 container when possible
        "merge_output_format": "mp4",
        # Less chatter; set to "verbose": True to debug
        "quiet": False,
        # If Instagram throttles, retries help
        "retries": 5,
        "fragment_retries": 5,
        "noprogress": False,
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
