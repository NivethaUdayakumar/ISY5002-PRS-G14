#!/usr/bin/env python3
"""
make_wildlife_video.py

Joins wildlife clips into one video of a set length (default 40-41 minutes;
change with --min-minutes / --max-minutes).

Folder layout (one subfolder per animal, numbered so they play in order):

    clips/
      01_elephants/   clip1.mp4  clip2.mp4  ...
      02_lions/       ...
      03_cheetahs/
      04_leopards/
      05_rhinos/
      06_buffalo/
      07_okapi/

If the clips folder is missing or empty, clips are downloaded automatically
from Wikimedia Commons (free-licensed; see clips/CREDITS.txt for attribution).
Use --download to replace existing clips with a fresh download.

What it does:
  0. Downloads clips per animal if needed (aiming for the middle of the range).
  1. Measures every clip and trims anything longer than 15 seconds.
  2. Checks the planned total is in range (default 40:00-41:00) BEFORE encoding (so you don't
     wait for nothing). Use --force to build anyway.
  3. Converts every clip to the same size, frame rate and format so they
     join cleanly, then joins them in folder/file-name order.
  4. Optionally adds background music (--music), looped and faded out.

Requires FFmpeg (ffmpeg + ffprobe). Found via PATH, the FFMPEG_DIR environment
variable, or a winget install (Gyan.FFmpeg).

Examples:
    python make_wildlife_video.py --dry-run          # just show the plan
    python make_wildlife_video.py                    # build wildlife.mp4
    python make_wildlife_video.py --music music.mp3  # with soundtrack
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".ogv"}
MAX_CLIP = 15.0          # seconds per clip
MIN_CLIP = 3.0           # skip clips shorter than this when downloading
MIN_TOTAL = 40 * 60      # 40:00 (override with --min-minutes)
MAX_TOTAL = 41 * 60      # 41:00 (override with --max-minutes)
TARGET_TOTAL = (MIN_TOTAL + MAX_TOTAL) / 2  # what the downloader aims for

# (folder name, Commons searches, title must match, title must NOT match)
# Title filters keep out look-alikes such as sea lions, snow leopards,
# rhinoceros beetles or the city of Buffalo.
ANIMALS = [
    ("01_elephants", ["Loxodonta", "african elephant", "elephant"],
     r"elephant|loxodonta|elefant|olifant", r"seal|shrew|elephas|asian|treadmill|99frames"),
    ("02_lions", ['"Panthera leo"', "lion -sea", "lioness"],
     r"\blions?\b|lioness|panthera leo|löwe|leeuw",
     r"sea[ -]?lion|lionfish|mountain lion|lions club|\bking\b|bedrohte|symboltier|lebensr"),
    ("03_cheetahs", ['"Acinonyx jubatus"', "cheetah", "gepard"],
     r"cheetah|acinonyx|gepard", None),
    ("04_leopards", ['"Panthera pardus"', "leopard", "Panthera pardus"],
     r"leopard|panthera pardus",
     r"snow|clouded|gecko|seal|shark|frog|tortoise|moth|leopard cat|slug|lizard|kleff"),
    ("05_rhinos", ["rhinoceros -beetle -iguana", "rhino -beetle", "Ceratotherium",
                   '"Diceros bicornis"', "Nashorn"],
     r"rhino|ceratotherium|diceros|nashorn|neushoorn",
     r"beetle|iguana|viper|hornbill|flying rhino|cyclura|dynastes|tinder|aircraft|poach"),
    ("06_buffalo", ['"Syncerus caffer"', "african buffalo", "cape buffalo"],
     r"syncerus|african buffalo|cape buffalo", None),
    ("07_okapi", ["okapi", "Okapia"], r"okapi", None),
]
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia's robot policy requires contact info in the User-Agent.
USER_AGENT = ("make_wildlife_video/1.0 "
              "(https://github.com/NivethaUdayakumar/ISY5002-PRS-G14; student project) "
              f"Python-urllib/{sys.version_info.major}.{sys.version_info.minor}")
DOWNLOAD_DELAY = 1.0     # seconds between downloads, to stay polite


def fmt(seconds):
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}:{s:02d}"


def find_ffmpeg_dir():
    """Look for an FFmpeg bin folder that isn't on PATH (FFMPEG_DIR or a winget install)."""
    candidates = []
    if os.environ.get("FFMPEG_DIR"):
        candidates.append(Path(os.environ["FFMPEG_DIR"]))
    winget = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if winget.is_dir():
        candidates += sorted(winget.glob("*FFmpeg*/*/bin"), reverse=True)
    for d in candidates:
        if (d / "ffmpeg.exe").exists() or (d / "ffmpeg").exists():
            return d
    return None


def check_tools():
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        found = find_ffmpeg_dir()
        if found:
            os.environ["PATH"] = str(found) + os.pathsep + os.environ.get("PATH", "")
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            sys.exit(f"Error: '{tool}' not found. Install FFmpeg and make sure "
                     f"it is on your PATH, or set FFMPEG_DIR to its bin folder "
                     f"(https://ffmpeg.org/download.html).")


def get_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def http_get(url, params=None, retries=4):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries + 1):
        try:
            return urllib.request.urlopen(req, timeout=60)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == retries:
                raise
            wait = int(e.headers.get("Retry-After") or 0) or 5 * 2 ** attempt
            print(f"  (rate limited, waiting {wait}s)")
            time.sleep(wait)


def search_commons(query, limit=100):
    """Return Commons video results for a search, in relevance order."""
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrnamespace": 6, "gsrlimit": limit,
        "gsrsearch": f"{query} filetype:video",
        "prop": "videoinfo", "viprop": "url|size|derivatives|extmetadata",
        "viextmetadatafilter": "Artist|LicenseShortName",
    }
    with http_get(COMMONS_API, params) as resp:
        pages = json.load(resp).get("query", {}).get("pages", {})
    return [p for p in sorted(pages.values(), key=lambda p: p.get("index", 0))
            if p.get("videoinfo")]


def pick_source(info):
    """Prefer a <=720p transcode, then <=1080p, then the original file."""
    transcodes = [d for d in info.get("derivatives", []) if d.get("transcodekey")]
    for max_h in (720, 1080):
        fits = [d for d in transcodes if (d.get("height") or 0) <= max_h]
        if fits:
            return max(fits, key=lambda d: d.get("height") or 0)["src"]
    return info["url"]


def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def find_candidates(queries, include, exclude):
    """Run each search and keep relevant, long-enough videos (deduplicated)."""
    seen, cands = set(), []
    for q in queries:
        for page in search_commons(q):
            title = page["title"]
            if title in seen:
                continue
            seen.add(title)
            if not re.search(include, title, re.I):
                continue
            if exclude and re.search(exclude, title, re.I):
                continue
            if (page["videoinfo"][0].get("duration") or 0) < MIN_CLIP:
                continue
            cands.append(page)
    return cands


def download_one(sec, limit, credits):
    """Download the next candidate for a section that fits in `limit` seconds.
    Returns the seconds it adds (measured with ffprobe), or 0 if none fit."""
    out_dir = sec["dir"]
    i = 0
    while i < len(sec["cands"]):
        page = sec["cands"][i]
        info = page["videoinfo"][0]
        if min(info["duration"], MAX_CLIP) > limit:
            i += 1      # too long for now; may fit in a later round
            continue
        sec["cands"].pop(i)
        src = pick_source(info)
        ext = Path(urllib.parse.urlparse(src).path).suffix.lower() or ".webm"
        sec["n"] += 1
        name = re.sub(r"[^\w-]+", "_", page["title"].removeprefix("File:").rsplit(".", 1)[0])[:60]
        dst = out_dir / f"{sec['n']:02d}_{name}{ext}"
        time.sleep(DOWNLOAD_DELAY)
        try:
            with http_get(src) as resp, open(dst, "wb") as fh:
                shutil.copyfileobj(resp, fh)
        except Exception as e:
            print(f"  ! Failed {page['title']}: {e}")
            dst.unlink(missing_ok=True)
            continue
        real = get_duration(dst)          # Commons' listed length can be off
        if real is None or real < MIN_CLIP:
            print(f"  ! Unusable after download, skipped: {dst.name}")
            dst.unlink(missing_ok=True)
            continue
        use = min(real, MAX_CLIP)
        sec["used"] += use
        meta = info.get("extmetadata", {})
        credits.append(f"{sec['folder']}/{dst.name}\n"
                       f"  {info['descriptionurl']}\n"
                       f"  by {strip_html(meta.get('Artist', {}).get('value')) or 'unknown'}, "
                       f"{meta.get('LicenseShortName', {}).get('value', 'see page')}\n")
        print(f"  + {sec['folder']}/{dst.name}  ({use:.1f}s, section {fmt(sec['used'])})")
        return use
    return 0


def download_clips(clips_dir):
    """Download Commons clips for each animal so the total lands near TARGET_TOTAL."""
    sections = []
    print("Searching Wikimedia Commons...")
    for folder, queries, include, exclude in ANIMALS:
        cands = find_candidates(queries, include, exclude)
        print(f"  {folder:<14} {len(cands):>3} candidate videos")
        out_dir = clips_dir / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        sections.append({"folder": folder, "dir": out_dir, "cands": cands, "used": 0.0, "n": 0})

    credits = []
    budget = TARGET_TOTAL / len(sections)
    # Pass 1: an equal share per animal.
    for sec in sections:
        print(f"\nDownloading {sec['folder']}...")
        while budget - sec["used"] >= MIN_CLIP:
            if not download_one(sec, budget - sec["used"], credits):
                break
        if sec["used"] < budget - MAX_CLIP:
            print(f"  ! Only {fmt(sec['used'])} of footage found for {sec['folder']}; "
                  f"other animals will make up the difference.")

    # Pass 2: animals with spare footage fill whatever is still missing.
    total = sum(s["used"] for s in sections)
    if TARGET_TOTAL - total >= MIN_CLIP:
        print(f"\nTopping up {fmt(TARGET_TOTAL - total)} from other animals...")
    while TARGET_TOTAL - total >= MIN_CLIP:
        added = 0
        for sec in sections:
            if TARGET_TOTAL - total < MIN_CLIP:
                break
            got = download_one(sec, TARGET_TOTAL - total, credits)
            total += got
            added += got
        if not added:
            print("  ! Ran out of suitable clips on Commons.")
            break

    (clips_dir / "CREDITS.txt").write_text(
        "Clips from Wikimedia Commons. Credit the authors per each licence.\n\n"
        + "\n".join(credits), encoding="utf-8")
    print(f"\nCredits written to {clips_dir / 'CREDITS.txt'}")


def collect_sections(clips_dir):
    sections = []
    for folder in sorted(p for p in clips_dir.iterdir() if p.is_dir()):
        files = sorted(f for f in folder.iterdir()
                       if f.is_file() and f.suffix.lower() in VIDEO_EXTS)
        if files:
            sections.append((folder.name, files))
    return sections


def build_plan(sections):
    """Return list of (section, [(file, seconds_to_use), ...]) and total."""
    plan, total = [], 0.0
    for name, files in sections:
        items = []
        for f in files:
            d = get_duration(f)
            if d is None or d <= 0.5:
                print(f"  ! Skipping unreadable/too-short file: {f}")
                continue
            use = min(d, MAX_CLIP)
            items.append((f, use))
            total += use
        plan.append((name, items))
    return plan, total


def print_plan(plan, total):
    print("\nPlan")
    print("-" * 44)
    for name, items in plan:
        sec = sum(u for _, u in items)
        print(f"  {name:<20} {len(items):>3} clips   {fmt(sec):>6}")
    print("-" * 44)
    print(f"  {'TOTAL':<20} {sum(len(i) for _, i in plan):>3} clips   {fmt(total):>6}")
    if total < MIN_TOTAL:
        print(f"\n  Too short by {fmt(MIN_TOTAL - total)}. "
              f"Add about {int((MIN_TOTAL - total) // MAX_CLIP) + 1} more clip(s).")
    elif total > MAX_TOTAL:
        print(f"\n  Too long by {fmt(total - MAX_TOTAL)}. "
              f"Remove about {int((total - MAX_TOTAL) // MAX_CLIP) + 1} clip(s).")
    else:
        print(f"\n  Total is within {fmt(MIN_TOTAL)}-{fmt(MAX_TOTAL)}.")


def normalize_clip(src, dst, seconds, width, height, fps):
    vf = (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
          f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
          f"setsar=1,fps={fps},format=yuv420p")
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-t", f"{seconds:.3f}", "-i", str(src),
        "-f", "lavfi", "-t", f"{seconds:.3f}",
        "-i", "anullsrc=r=48000:cl=stereo",
        "-vf", vf,
        "-map", "0:v:0", "-map", "1:a:0",   # silent track keeps all clips uniform
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", str(dst)]
    subprocess.run(cmd, check=True)


def concat_clips(clip_paths, out_path, workdir):
    list_file = workdir / "list.txt"
    with open(list_file, "w", encoding="utf-8") as fh:
        for p in clip_paths:
            safe = p.resolve().as_posix().replace("'", "'\\''")
            fh.write(f"file '{safe}'\n")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", str(list_file), "-c", "copy", str(out_path)], check=True)


def add_music(video, music, out_path, total):
    fade_start = max(total - 3, 0)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(video), "-stream_loop", "-1", "-i", str(music),
        "-map", "0:v", "-map", "1:a",
        "-af", f"afade=t=in:st=0:d=2,afade=t=out:st={fade_start:.2f}:d=3",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-t", f"{total:.3f}", str(out_path)], check=True)


def main():
    global MIN_TOTAL, MAX_TOTAL, TARGET_TOTAL
    ap = argparse.ArgumentParser(description="Join wildlife clips into one video of a set length.")
    ap.add_argument("--clips", default="clips", help="folder with one subfolder per animal (default: clips)")
    ap.add_argument("--output", default="wildlife.mp4", help="output file (default: wildlife.mp4)")
    ap.add_argument("--music", help="optional background music file (looped, faded out at the end)")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--download", action="store_true",
                    help="delete the clips folder and download fresh clips from Wikimedia Commons "
                         "(done automatically when the folder is missing or empty)")
    ap.add_argument("--dry-run", action="store_true", help="only show the plan, don't encode")
    ap.add_argument("--force", action="store_true", help="build even if the total is outside the length range")
    ap.add_argument("--min-minutes", type=float, default=MIN_TOTAL / 60,
                    help=f"shortest allowed length (default {MIN_TOTAL // 60})")
    ap.add_argument("--max-minutes", type=float, default=MAX_TOTAL / 60,
                    help=f"longest allowed length (default {MAX_TOTAL // 60})")
    args = ap.parse_args()

    MIN_TOTAL, MAX_TOTAL = args.min_minutes * 60, args.max_minutes * 60
    if MAX_TOTAL < MIN_TOTAL:
        sys.exit("Error: --max-minutes must be at least --min-minutes.")
    TARGET_TOTAL = (MIN_TOTAL + MAX_TOTAL) / 2

    # Clip titles can contain characters the Windows console can't print.
    sys.stdout.reconfigure(errors="replace")
    check_tools()
    clips_dir = Path(args.clips)
    if args.download or not clips_dir.is_dir() or not collect_sections(clips_dir):
        if args.download and clips_dir.is_dir():
            # Empty the folder rather than deleting it, so it works even if
            # the folder is open in Explorer or a terminal.
            for child in clips_dir.iterdir():
                shutil.rmtree(child) if child.is_dir() else child.unlink()
        download_clips(clips_dir)

    sections = collect_sections(clips_dir)
    if not sections:
        sys.exit(f"Error: no video clips found in subfolders of '{clips_dir}'.")

    print("Measuring clips...")
    plan, total = build_plan(sections)
    print_plan(plan, total)

    if args.dry_run:
        return
    if not (MIN_TOTAL <= total <= MAX_TOTAL) and not args.force:
        sys.exit("\nStopped. Adjust your clips, or re-run with --force to build anyway.")

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        normalized, n = [], 0
        count = sum(len(i) for _, i in plan)
        for name, items in plan:
            for src, use in items:
                n += 1
                print(f"[{n}/{count}] {name}/{src.name}  ({use:.1f}s)")
                dst = workdir / f"{n:04d}.mp4"
                normalize_clip(src, dst, use, args.width, args.height, args.fps)
                normalized.append(dst)

        print("\nJoining clips...")
        joined = workdir / "joined.mp4"
        concat_clips(normalized, joined, workdir)

        out = Path(args.output)
        if args.music:
            print("Adding music...")
            add_music(joined, Path(args.music), out, total)
        else:
            shutil.move(str(joined), out)

    final = get_duration(out) or 0
    print(f"\nDone: {out}  (length {fmt(final)})")
    if not (MIN_TOTAL <= final <= MAX_TOTAL):
        print(f"Warning: final length is outside {fmt(MIN_TOTAL)}-{fmt(MAX_TOTAL)}.")


if __name__ == "__main__":
    main()
