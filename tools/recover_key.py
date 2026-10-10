"""Inspect an explicitly provided emulator snapshot and validate candidates locally."""

import argparse
import json
import mmap
import os
from pathlib import Path
import re

import tinytuya

PATTERN = re.compile(rb'"localKey"\s*:\s*"([^"\\]{16})"')


def collect_candidates(memory, device_id):
    """Bound inspection to short regions around the requested device ID."""
    candidates = set()
    for encoding in ("utf-8", "utf-16-le"):
        needle = device_id.encode(encoding)
        offset = 0
        while (position := memory.find(needle, offset)) != -1:
            offset = position + len(needle)
            start = max(0, position - 512)
            end = min(len(memory), position + len(needle) + 512)
            region = bytes(memory[start:end])
            if encoding == "utf-16-le":
                if (position - start) % 2:
                    region = region[1:]
                region = region[: len(region) // 2 * 2].decode(encoding, errors="ignore").encode("utf-8")
            for match in PATTERN.finditer(region):
                try:
                    key = match[1].decode("latin1")
                except UnicodeError:
                    continue
                candidates.add(key)
    return sorted(candidates)


def validate_candidate(device_id, host, key):
    """Only a status read; never write a parameter or print library responses."""
    device = tinytuya.Device(
        device_id,
        host,
        key,
        version=3.3,
        connection_timeout=4,
        connection_retry_limit=1,
        connection_retry_delay=1,
    )
    try:
        result = device.status()
        if not isinstance(result, dict) or "Error" in result:
            return False
        dps = result.get("dps", {})
        return isinstance(dps, dict) and type(dps.get("1")) is bool
    except Exception:
        return False
    finally:
        device.close()


def save_credentials(output, device_id, host, key):
    """Do not overwrite existing files; restrict access before writing secrets."""
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump({"device_id": device_id, "host": host, "local_key": key, "version": "3.3"}, stream)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new private file")
    if not args.device_id.strip():
        parser.error("Device ID is required")
    with args.snapshot.open("rb") as stream:
        if not os.fstat(stream.fileno()).st_size:
            parser.error("Snapshot is empty")
        with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as memory:
            candidates = collect_candidates(memory, args.device_id)
    print(f"Found {len(candidates)} candidate(s) near the requested device ID.")
    if len(candidates) > 8:
        parser.error("Too many candidates; no network validation performed")
    for key in candidates:
        if validate_candidate(args.device_id, args.host, key):
            save_credentials(args.output, args.device_id, args.host, key)
            print("Validated credentials saved to the requested private file; no key printed.")
            return
    parser.exit(1, "No locally validated key found. No output file written.\n")


if __name__ == "__main__":
    main()
