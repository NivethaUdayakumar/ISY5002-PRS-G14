"""
Copy .jpg images from an input folder into an output folder,
renaming them as "5 (1).jpg", "5 (2).jpg", "5 (3).jpg", ...

The original files are left untouched.

Usage:
    python rename_images.py <input_folder> <output_folder>
    python rename_images.py <input_folder> <output_folder> --prefix 5 --start 1

If you run it with no arguments, it reads from /images and
writes to /images/renamed.
"""

import argparse
import re
import shutil
from pathlib import Path

DEFAULT_INPUT = "images"
DEFAULT_OUTPUT = "renamed"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def natural_key(path: Path):
    """Sort 'img2' before 'img10' (natural order, case-insensitive)."""
    return [int(t) if t.isdigit() else t.lower()
            for t in re.split(r"(\d+)", path.name)]


def next_free_number(output_dir: Path, prefix: str, start: int) -> int:
    """Find the first number not already used in the output folder,
    so existing files there are never overwritten."""
    pattern = re.compile(rf"^{re.escape(prefix)} \((\d+)\)\.jpg$", re.IGNORECASE)
    used = [int(m.group(1)) for f in output_dir.iterdir()
            if (m := pattern.match(f.name))]
    return max(start, max(used, default=0) + 1)


def copy_and_rename(input_dir: Path, output_dir: Path, prefix: str, start: int):
    if not input_dir.is_dir():
        raise SystemExit(f"Input folder not found: {input_dir}")
    if input_dir.resolve() == output_dir.resolve():
        raise SystemExit("Output folder must be different from the input folder.")

    output_dir.mkdir(parents=True, exist_ok=True)

    images = sorted(
        (f for f in input_dir.iterdir()
         if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS),
        key=natural_key,
    )
    if not images:
        print("No .jpg files found in", input_dir)
        return

    number = next_free_number(output_dir, prefix, start)
    for src in images:
        new_name = f"{prefix} ({number}).jpg"
        shutil.copy2(src, output_dir / new_name)  # copy2 keeps file dates
        print(f"{src.name}  ->  {new_name}")
        number += 1

    print(f"\nDone. Copied {len(images)} file(s) to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Copy and rename .jpg files.")
    parser.add_argument("input_folder", nargs="?", help="Folder with the original images")
    parser.add_argument("output_folder", nargs="?", help="Folder for the renamed copies")
    parser.add_argument("--prefix", default="5", help='Name prefix (default: "5")')
    parser.add_argument("--start", type=int, default=1, help="First number (default: 1)")
    args = parser.parse_args()

    input_folder = args.input_folder or DEFAULT_INPUT
    output_folder = args.output_folder or DEFAULT_OUTPUT

    copy_and_rename(Path(input_folder), Path(output_folder), args.prefix, args.start)


if __name__ == "__main__":
    main()
