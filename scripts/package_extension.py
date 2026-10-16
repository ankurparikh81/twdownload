#!/usr/bin/env python3
"""Packages the Chrome extension into a clean, store-ready ZIP archive."""

import json
import os
import sys
import zipfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTENSION_DIR = os.path.join(PROJECT_ROOT, "extension")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
MANIFEST_PATH = os.path.join(EXTENSION_DIR, "manifest.json")


def validate_manifest():
    if not os.path.exists(MANIFEST_PATH):
        raise FileNotFoundError(f"Manifest not found at {MANIFEST_PATH}")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    version = data.get("version", "1.0.0")
    print(f"Validated manifest: {data.get('name')} v{version}")
    return version


def package_extension():
    version = validate_manifest()
    os.makedirs(DIST_DIR, exist_ok=True)
    zip_filename = f"twdownload-extension-v{version}.zip"
    zip_path = os.path.join(DIST_DIR, zip_filename)

    # Excluded files
    excluded_names = {".DS_Store", "Thumbs.db", "README.md"}

    print(f"Creating zip bundle: {zip_path}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(EXTENSION_DIR):
            for file in files:
                if file in excluded_names or file.endswith(".tmp"):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, EXTENSION_DIR)
                zipf.write(full_path, rel_path)
                print(f"  + {rel_path}")

    # Also make a generic twdownload-extension.zip symlink / copy for convenience
    generic_zip = os.path.join(DIST_DIR, "twdownload-extension.zip")
    if os.path.exists(generic_zip):
        os.remove(generic_zip)
    import shutil
    shutil.copyfile(zip_path, generic_zip)

    size_kb = os.path.getsize(zip_path) / 1024
    print(f"\nDone! Package generated successfully:")
    print(f"  File: {zip_path} ({size_kb:.1f} KB)")
    print(f"  Ready for Chrome Web Store Developer Console upload.\n")
    return zip_path


if __name__ == "__main__":
    try:
        package_extension()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
