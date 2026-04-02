#!/usr/bin/env python3
"""Copy a CALVIN dataset tree from mounted storage to node-local disk."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterator, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy CALVIN data from mounted storage to node-local disk."
    )
    parser.add_argument("--src", required=True, help="Source dataset root.")
    parser.add_argument("--dst", required=True, help="Destination dataset root.")
    parser.add_argument(
        "--workers",
        type=int,
        default=min(32, (os.cpu_count() or 8)),
        help="Number of parallel copy workers.",
    )
    parser.add_argument(
        "--buffer-mb",
        type=int,
        default=8,
        help="Buffered copy chunk size in MiB.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite destination files even if the size already matches.",
    )
    parser.add_argument(
        "--progress-seconds",
        type=float,
        default=5.0,
        help="Progress report interval in seconds.",
    )
    return parser.parse_args()


def format_bytes(num_bytes: float) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{num_bytes:.2f} B"


def format_duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0 or not (seconds < float("inf")):
        return "N/A"

    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:d}h{minutes:02d}m{secs:02d}s"
    if minutes:
        return f"{minutes:d}m{secs:02d}s"
    return f"{secs:d}s"


def iter_files(root: Path) -> Iterator[Path]:
    for path in root.rglob("*"):
        if path.is_file():
            yield path.relative_to(root)


def collect_files(root: Path, progress_seconds: float) -> Tuple[List[Path], int]:
    files: List[Path] = []
    total_bytes = 0
    start_time = time.time()
    last_report = start_time

    print(f"[scan] start root={root}", flush=True)
    for idx, rel_path in enumerate(iter_files(root), start=1):
        src = root / rel_path
        try:
            total_bytes += src.stat().st_size
        except FileNotFoundError:
            continue
        files.append(rel_path)

        now = time.time()
        if idx == 1 or now - last_report >= progress_seconds:
            elapsed = max(now - start_time, 1e-6)
            print(
                f"[scan] files={idx} size={format_bytes(total_bytes)} "
                f"rate={idx / elapsed:.1f} files/s elapsed={elapsed:.1f}s",
                flush=True,
            )
            last_report = now

    elapsed = max(time.time() - start_time, 1e-6)
    print(
        f"[scan] done files={len(files)} total_size={format_bytes(total_bytes)} "
        f"elapsed={elapsed:.1f}s",
        flush=True,
    )
    return files, total_bytes


def disk_free_bytes(path: Path) -> int:
    probe = path
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    usage = shutil.disk_usage(probe)
    return usage.free


def copy_one(
    src_root: Path,
    dst_root: Path,
    rel_path: Path,
    buffer_size: int,
    overwrite: bool,
) -> Tuple[str, int, str]:
    src = src_root / rel_path
    dst = dst_root / rel_path
    size = src.stat().st_size

    if not overwrite and dst.exists() and dst.stat().st_size == size:
        return "skipped", size, str(rel_path)

    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(f"{dst.name}.partial")

    try:
        with src.open("rb") as fsrc, tmp.open("wb") as fdst:
            shutil.copyfileobj(fsrc, fdst, length=buffer_size)
        shutil.copystat(src, tmp, follow_symlinks=False)
        os.replace(tmp, dst)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise

    return "copied", size, str(rel_path)


def print_progress(
    processed: int,
    total_files: int,
    copied_bytes: int,
    skipped_bytes: int,
    total_bytes: int,
    failed: int,
    start_time: float,
) -> None:
    elapsed = max(time.time() - start_time, 1e-6)
    accounted_bytes = copied_bytes + skipped_bytes
    rate = accounted_bytes / elapsed
    remaining_bytes = max(total_bytes - accounted_bytes, 0)
    eta = (remaining_bytes / rate) if rate > 0 else None
    message = (
        f"[copy] files={processed}/{total_files} "
        f"copied={format_bytes(copied_bytes)} "
        f"skipped={format_bytes(skipped_bytes)} "
        f"remaining={format_bytes(remaining_bytes)} "
        f"failed={failed} "
        f"rate={format_bytes(rate)}/s "
        f"elapsed={elapsed:.1f}s "
        f"eta={format_duration(eta)}"
    )
    print(message, flush=True)


def main() -> int:
    args = parse_args()
    src_root = Path(args.src).expanduser().resolve()
    dst_root = Path(args.dst).expanduser().resolve()
    buffer_size = max(args.buffer_mb, 1) * 1024 * 1024

    if not src_root.exists():
        print(f"[copy] source does not exist: {src_root}", file=sys.stderr)
        return 1

    dst_root.mkdir(parents=True, exist_ok=True)
    files, total_bytes = collect_files(src_root, args.progress_seconds)
    total_files = len(files)
    free_bytes = disk_free_bytes(dst_root)

    print(f"[copy] source={src_root}", flush=True)
    print(f"[copy] destination={dst_root}", flush=True)
    print(f"[copy] total_files={total_files}", flush=True)
    print(f"[copy] total_size={format_bytes(total_bytes)}", flush=True)
    print(f"[copy] free_space={format_bytes(free_bytes)}", flush=True)
    print(
        f"[copy] workers={args.workers} buffer={args.buffer_mb} MiB overwrite={args.overwrite}",
        flush=True,
    )

    if total_bytes > free_bytes:
        print(
            "[copy] not enough free space on destination disk.",
            file=sys.stderr,
            flush=True,
        )
        return 1

    processed = 0
    copied_bytes = 0
    skipped_bytes = 0
    failed = 0
    start_time = time.time()
    last_report = 0.0

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(
                copy_one,
                src_root,
                dst_root,
                rel_path,
                buffer_size,
                args.overwrite,
            ): rel_path
            for rel_path in files
        }

        for future in as_completed(futures):
            processed += 1
            rel_path = futures[future]
            try:
                status, size, _ = future.result()
                if status == "copied":
                    copied_bytes += size
                else:
                    skipped_bytes += size
            except Exception as exc:
                failed += 1
                print(f"[copy][error] {rel_path}: {exc}", file=sys.stderr, flush=True)

            now = time.time()
            if processed == total_files or now - last_report >= args.progress_seconds:
                print_progress(
                    processed,
                    total_files,
                    copied_bytes,
                    skipped_bytes,
                    total_bytes,
                    failed,
                    start_time,
                )
                last_report = now

    elapsed = max(time.time() - start_time, 1e-6)
    print(
        f"[copy] done copied={format_bytes(copied_bytes)} "
        f"skipped={format_bytes(skipped_bytes)} failed={failed} "
        f"elapsed={elapsed:.1f}s avg_copy_rate={format_bytes(copied_bytes / elapsed)}/s",
        flush=True,
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
