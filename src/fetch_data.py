import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from src.config import RAW, SLUG, SNAPSHOT, SOURCE, TABLES


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_csvs(directory):
    expected = json.loads(SNAPSHOT.read_text())["csv_sha256"]
    actual = {name: sha256(directory / name) for name in TABLES.values()}
    mismatches = [name for name, digest in actual.items() if digest != expected[name]]
    if mismatches:
        raise ValueError(f"CSV fingerprints differ from the verified Olist v2 snapshot: {mismatches}")
    return actual


def main():
    parser = argparse.ArgumentParser(description="Fetch the public Olist CSV archive.")
    parser.add_argument("--archive", type=Path, help="Use a previously downloaded Kaggle ZIP.")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    if all((RAW / name).is_file() for name in TABLES.values()):
        verify_csvs(RAW)
        print("Verified all nine local Olist v2 CSVs.")
        return
    with TemporaryDirectory(dir=RAW) as temporary:
        staging = Path(temporary)
        archive = args.archive or staging / "olist.zip"
        effective_url = None
        if args.archive is None:
            result = subprocess.run(
                ["curl", "-fLsS", "--retry", "2", "--max-time", "900", "--output", str(archive),
                 "--write-out", "%{url_effective}", SOURCE],
                check=False, stdout=subprocess.PIPE, text=True,
            )
            if result.returncode:
                parser.exit(1, "Kaggle download failed. See data/README.md for the local ZIP option.\n")
            # Keep the public path only. Redirect query parameters can contain signed credentials.
            effective_url = result.stdout.partition("?")[0]
        with ZipFile(archive) as zipped:
            for name in TABLES.values():
                with zipped.open(name) as source, (staging / name).open("wb") as target:
                    shutil.copyfileobj(source, target)
        manifest = {
            "dataset": SLUG,
            "source": SOURCE,
            "acquisition": "Kaggle API" if args.archive is None else "local ZIP",
            "download_path": effective_url,
            "archive_sha256": sha256(archive),
            "csv_sha256": verify_csvs(staging),
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        for name in (*TABLES.values(), "manifest.json"):
            (staging / name).replace(RAW / name)
        print("Extracted and hashed all nine Olist CSVs.")


if __name__ == "__main__":
    main()
