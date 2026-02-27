#!/usr/bin/env python
"""
Debug helper: find the latest saved march-dialog screenshot.

Why use this:
- Join Rally debug mode saves march dialog captures when diagnosing March button detection.
- This script quickly prints the newest screenshot so you can inspect button placement.

How to use:
- From project root: `python debug/show_march_dialog.py`
- The script auto-resolves `<project_root>/temp/march_dialog_*.png` regardless of current working directory.
"""
import os
import glob
from pathlib import Path

# Find all march dialog screenshots
project_root = Path(__file__).resolve().parent.parent
temp_dir = project_root / "temp"
pattern = str(temp_dir / "march_dialog_*.png")
files = glob.glob(pattern)

if not files:
    print("❌ No march dialog screenshots found")
    print(f"   Looked in: {temp_dir / 'march_dialog_*.png'}")
else:
    # Get the most recent file
    latest_file = max(files, key=os.path.getctime)
    print(f"✓ Latest march dialog screenshot:")
    print(f"  {latest_file}")
    print(f"\nFile size: {os.path.getsize(latest_file)} bytes")
    print(f"Modified: {Path(latest_file).stat().st_mtime}")
    print(f"\n➜ Check this image in {temp_dir}/ to see where the March button actually is")
    print(f"   (You can drag the file to your browser or image viewer)")
