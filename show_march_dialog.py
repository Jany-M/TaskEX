#!/usr/bin/env python
"""Find and display the latest march dialog screenshot"""
import os
import glob
from pathlib import Path

# Find all march dialog screenshots
temp_dir = "temp"
pattern = os.path.join(temp_dir, "march_dialog_*.png")
files = glob.glob(pattern)

if not files:
    print("❌ No march dialog screenshots found")
    print(f"   Looked in: {temp_dir}/march_dialog_*.png")
else:
    # Get the most recent file
    latest_file = max(files, key=os.path.getctime)
    print(f"✓ Latest march dialog screenshot:")
    print(f"  {latest_file}")
    print(f"\nFile size: {os.path.getsize(latest_file)} bytes")
    print(f"Modified: {Path(latest_file).stat().st_mtime}")
    print(f"\n➜ Check this image in {temp_dir}/ to see where the March button actually is")
    print(f"   (You can drag the file to your browser or image viewer)")
