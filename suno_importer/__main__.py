"""Download-only diagnostic CLI; use the Nyquist tool for Audacity integration."""
import argparse
from pathlib import Path
import sys
from .downloader import download

parser = argparse.ArgumentParser(description="Tai MP3 public cua Suno (chua import vao Audacity).")
parser.add_argument("url")
parser.add_argument("--output", type=Path, default=Path("downloads"))
args = parser.parse_args()
try:
    path = download(args.url, args.output)
except (ValueError, OSError) as exc:
    print(f"Download failed: {exc}", file=sys.stderr)
    sys.exit(1)
print(path.resolve())
