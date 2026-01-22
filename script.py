import os, sys
import random

from download import download_reel
from upload_video import get_authenticated_service, upload_video


DEFAULT_DIR = "default"


if __name__ == "__main__":
    # download_reel
    if len(sys.argv) < 2:
        print("Usage: python save_reel.py <instagram_reel_url> [output_dir]")
        sys.exit(1)
    url = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DIR
    download_reel(url, outdir)
    youtube = get_authenticated_service()

    contents = os.listdir(outdir)
    downloaded_file_name = outdir + '/' + contents[0]
    n = random.randint(1, 1000)
    upload_video(youtube,
                 file=downloaded_file_name,
                 title=f'default-test{n}',
                 description=f'default-description{n}',
                 category=23,
                 keywords=f'defaultkeyword{n}',
                 privacy='private'
                 )

    print("Directory contents:", downloaded_file_name)

