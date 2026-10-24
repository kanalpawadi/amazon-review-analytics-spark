"""
Build a reduced (sampled) version of the Amazon Reviews 2023 dataset.

Sampling is done by USER: a user is kept if md5(user_id) falls in the chosen
percentage, and then ALL reviews of that user are kept. This keeps each
reviewer's full history, which the fake-review module (reviewer behaviour)
and the ALS recommender (user histories) both need. A plain random sample of
reviews would break those histories.

Metadata is then filtered to only the products that appear in the sample.

The input files are streamed straight from the URL (or read from a local
path), so the full dataset is never stored on disk.

Usage:
    python scripts/make_sample.py                      # 1% of Electronics
    python scripts/make_sample.py --percent 5          # 5% of Electronics
    python scripts/make_sample.py --category Books
    python scripts/make_sample.py --max-lines 100000   # quick test run
"""
import argparse
import gzip
import hashlib
import json
import os
import time
import urllib.request

BASE_URL = "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw"


def open_source(path_or_url):
    """Return a binary stream of the gzipped file (URL or local path)."""
    if path_or_url.startswith("http"):
        return urllib.request.urlopen(path_or_url, timeout=120)
    return open(path_or_url, "rb")


def keep_user(user_id, percent):
    """Deterministic: the same user is always in or out of the sample."""
    bucket = int(hashlib.md5(user_id.encode("utf-8")).hexdigest()[:8], 16) % 10000
    return bucket < percent * 100


def sample_reviews(src, out_path, percent, max_lines):
    asins = set()
    users = set()
    read = kept = 0
    start = time.time()
    with open_source(src) as raw, gzip.open(raw, "rt", encoding="utf-8") as fin, \
            gzip.open(out_path, "wt", encoding="utf-8") as fout:
        for line in fin:
            read += 1
            review = json.loads(line)
            if keep_user(review["user_id"], percent):
                fout.write(line)
                kept += 1
                asins.add(review["parent_asin"])
                users.add(review["user_id"])
            if read % 1_000_000 == 0:
                print(f"  reviews read: {read:,}  kept: {kept:,}  "
                      f"({time.time() - start:.0f}s)", flush=True)
            if max_lines and read >= max_lines:
                break
    print(f"Reviews done: read {read:,}, kept {kept:,} "
          f"from {len(users):,} users on {len(asins):,} products")
    return asins


def sample_meta(src, out_path, asins, max_lines):
    read = kept = 0
    start = time.time()
    with open_source(src) as raw, gzip.open(raw, "rt", encoding="utf-8") as fin, \
            gzip.open(out_path, "wt", encoding="utf-8") as fout:
        for line in fin:
            read += 1
            if json.loads(line)["parent_asin"] in asins:
                fout.write(line)
                kept += 1
            if read % 500_000 == 0:
                print(f"  products read: {read:,}  kept: {kept:,}  "
                      f"({time.time() - start:.0f}s)", flush=True)
            if max_lines and read >= max_lines:
                break
    print(f"Metadata done: read {read:,}, kept {kept:,}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--category", default="Electronics")
    parser.add_argument("--percent", type=float, default=1.0,
                        help="percentage of users to keep (default 1)")
    parser.add_argument("--reviews-src", help="local path or URL (default: official URL)")
    parser.add_argument("--meta-src", help="local path or URL (default: official URL)")
    parser.add_argument("--out-dir", default="data/sample")
    parser.add_argument("--max-lines", type=int, default=0,
                        help="stop after this many input lines (for testing)")
    args = parser.parse_args()

    cat = args.category
    reviews_src = args.reviews_src or f"{BASE_URL}/review_categories/{cat}.jsonl.gz"
    meta_src = args.meta_src or f"{BASE_URL}/meta_categories/meta_{cat}.jsonl.gz"
    tag = f"{args.percent:g}pct"
    os.makedirs(args.out_dir, exist_ok=True)
    reviews_out = os.path.join(args.out_dir, f"{cat}_{tag}.jsonl.gz")
    meta_out = os.path.join(args.out_dir, f"meta_{cat}_{tag}.jsonl.gz")

    print(f"Sampling {args.percent}% of users from {cat}")
    asins = sample_reviews(reviews_src, reviews_out, args.percent, args.max_lines)
    sample_meta(meta_src, meta_out, asins, args.max_lines)
    for path in (reviews_out, meta_out):
        print(f"{path}: {os.path.getsize(path) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
