#!/usr/bin/env python3
"""Download CC-CEDICT and an HSK word list into data/dictionary.db.

Checksums are verified when known. Big data files are never committed.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "data" / "dictionary.db"
DEFAULT_CACHE = REPO_ROOT / "data" / "cache"

# Official CC-CEDICT download (UTF-8 gzipped).
CEDICT_URL = "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz"
CEDICT_SHA256 = ""

# MIT-licensed complete HSK list (SPEC §3 example dataset; repo moved under drkameleon).
HSK_URL = (
    "https://raw.githubusercontent.com/drkameleon/complete-hsk-vocabulary/main/complete.json"
)
HSK_SHA256 = ""

CEDICT_LINE = re.compile(
    r"^(?P<trad>\S+)\s+(?P<simp>\S+)\s+\[(?P<pinyin>[^\]]+)\]\s+/(?P<defs>.+)/$"
)
NEW_LEVEL = re.compile(r"^new-(\d+)$")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, expected_sha: str = "") -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        digest = sha256_file(dest)
        if expected_sha and digest != expected_sha:
            dest.unlink()
        else:
            print(f"using cached {dest} ({digest[:12]}…)")
            return dest

    print(f"downloading {url}")
    urllib.request.urlretrieve(url, dest)  # noqa: S310 — fixed URLs above
    digest = sha256_file(dest)
    print(f"  sha256={digest}")
    if expected_sha and digest != expected_sha:
        raise SystemExit(f"checksum mismatch for {dest}: got {digest}, want {expected_sha}")
    return dest


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE cedict (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            simplified TEXT NOT NULL,
            traditional TEXT NOT NULL,
            pinyin TEXT NOT NULL,
            definitions TEXT NOT NULL
        );
        CREATE INDEX ix_cedict_simplified ON cedict(simplified);
        CREATE TABLE hsk (
            word TEXT PRIMARY KEY,
            level INTEGER NOT NULL
        );
        CREATE INDEX ix_hsk_level ON hsk(level);
        """
    )
    return conn


def load_cedict(conn: sqlite3.Connection, gz_path: Path) -> int:
    count = 0
    with gzip.open(gz_path, "rt", encoding="utf-8") as f:
        rows: list[tuple[str, str, str, str]] = []
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = CEDICT_LINE.match(line)
            if not m:
                continue
            rows.append(
                (
                    m.group("simp"),
                    m.group("trad"),
                    m.group("pinyin"),
                    m.group("defs").replace("/", "; "),
                )
            )
            if len(rows) >= 1000:
                conn.executemany(
                    "INSERT INTO cedict (simplified, traditional, pinyin, definitions)"
                    " VALUES (?,?,?,?)",
                    rows,
                )
                count += len(rows)
                rows.clear()
        if rows:
            conn.executemany(
                "INSERT INTO cedict (simplified, traditional, pinyin, definitions)"
                " VALUES (?,?,?,?)",
                rows,
            )
            count += len(rows)
    conn.commit()
    return count


def _hsk_level_from_entry(item: dict[str, object]) -> int | None:
    """Prefer HSK 3.0 ('new-N'); fall back to old-N; ignore unknown shapes."""
    level_field = item.get("level")
    candidates: list[int] = []
    if isinstance(level_field, list):
        for entry in level_field:
            if not isinstance(entry, str):
                continue
            m = NEW_LEVEL.match(entry)
            if m:
                candidates.append(int(m.group(1)))
            elif entry.startswith("old-"):
                try:
                    candidates.append(int(entry.split("-", 1)[1]))
                except ValueError:
                    continue
    elif isinstance(level_field, int):
        candidates.append(level_field)
    if not candidates:
        return None
    # new-* preferred: if any new-N was parsed they are in candidates first when listed first;
    # take the minimum new level if present, else minimum overall.
    new_only = [
        int(m.group(1))
        for entry in (level_field if isinstance(level_field, list) else [])
        if isinstance(entry, str) and (m := NEW_LEVEL.match(entry))
    ]
    if new_only:
        return min(new_only)
    return min(candidates)


def load_hsk_json(conn: sqlite3.Connection, path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    best: dict[str, int] = {}

    def add(word: str, level: int) -> None:
        word = word.strip()
        if not word or not (1 <= level <= 9):
            return
        if word not in best or level < best[word]:
            best[word] = level

    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            word = str(item.get("simplified") or item.get("word") or "")
            level = _hsk_level_from_entry(item)
            if level is not None:
                add(word, level)
    elif isinstance(data, dict):
        if "words" in data and isinstance(data["words"], list):
            for item in data["words"]:
                if isinstance(item, dict):
                    word = str(item.get("simplified") or item.get("word") or "")
                    level = _hsk_level_from_entry(item) or int(item.get("level") or 0)
                    add(word, level)
        else:
            for key, value in data.items():
                try:
                    level = int(key)
                except ValueError:
                    continue
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            add(item, level)
                        elif isinstance(item, dict):
                            word = str(item.get("simplified") or item.get("word") or "")
                            add(word, int(item.get("level") or level))

    conn.executemany("INSERT OR REPLACE INTO hsk (word, level) VALUES (?,?)", best.items())
    conn.commit()
    return len(best)


def load_hsk_fallback(conn: sqlite3.Connection) -> int:
    """Tiny seed so the app can start offline if the GitHub fetch fails."""
    seed = [
        ("你好", 1),
        ("我", 1),
        ("你", 1),
        ("是", 1),
        ("的", 1),
        ("谢谢", 1),
        ("中国", 1),
        ("人", 1),
        ("吃", 1),
        ("喝", 1),
        ("银行", 2),
        ("重要", 3),
        ("不对", 2),
        ("一个", 1),
        ("一天", 1),
    ]
    conn.executemany("INSERT OR REPLACE INTO hsk (word, level) VALUES (?,?)", seed)
    conn.commit()
    return len(seed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--skip-download", action="store_true", help="Use cache only")
    args = parser.parse_args()

    cache: Path = args.cache
    cache.mkdir(parents=True, exist_ok=True)
    cedict_gz = cache / "cedict.txt.gz"
    hsk_json = cache / "hsk_complete.json"

    try:
        if args.skip_download and not cedict_gz.exists():
            raise SystemExit("no cached CC-CEDICT; run without --skip-download")
        if not args.skip_download:
            download(CEDICT_URL, cedict_gz, CEDICT_SHA256)
        else:
            print(f"using cached {cedict_gz}")
    except Exception as exc:
        print(f"CC-CEDICT download failed: {exc}", file=sys.stderr)
        return 1

    conn = init_db(args.out)
    n_cedict = load_cedict(conn, cedict_gz)
    print(f"loaded {n_cedict} CC-CEDICT entries")

    hsk_count = 0
    try:
        if not args.skip_download:
            download(HSK_URL, hsk_json, HSK_SHA256)
        if hsk_json.exists():
            hsk_count = load_hsk_json(conn, hsk_json)
    except Exception as exc:
        print(f"HSK download/parse failed ({exc}); using seed list", file=sys.stderr)
        hsk_count = load_hsk_fallback(conn)

    if hsk_count == 0:
        hsk_count = load_hsk_fallback(conn)

    print(f"loaded {hsk_count} HSK entries")
    conn.close()
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
