"""Prepare or reassemble checksum-bound artifact chunks without overwriting files."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare(source, destination, chunk_bytes=16 * 1024 * 1024):
    if chunk_bytes <= 0 or not source.is_file():
        raise ValueError("Need a file and positive chunk size")
    destination.mkdir(parents=True, exist_ok=False)
    chunks = []
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        while block := handle.read(chunk_bytes):
            name = f"part-{len(chunks):05d}"
            with (destination / name).open("xb") as output:
                output.write(block)
            digest.update(block)
            chunks.append({"name": name, "bytes": len(block),
                           "sha256": hashlib.sha256(block).hexdigest()})
    manifest = {"schema": 1, "name": source.name, "bytes": sum(c["bytes"] for c in chunks),
                "sha256": digest.hexdigest(), "chunks": chunks}
    with (destination / "manifest.json").open("x") as handle:
        json.dump(manifest, handle, indent=2)
    return manifest


def assemble(directory, output):
    manifest = json.loads((directory / "manifest.json").read_text())
    chunks = manifest["chunks"]
    if manifest.get("schema") != 1 or not chunks:
        raise ValueError("Invalid chunk manifest")
    for index, chunk in enumerate(chunks):
        if chunk["name"] != f"part-{index:05d}":
            raise ValueError("Invalid chunk order or path")
        path = directory / chunk["name"]
        if path.is_symlink() or path.stat().st_size != chunk["bytes"] or sha256(path) != chunk["sha256"]:
            raise ValueError("Chunk checksum mismatch")
    if output.exists():
        raise ValueError("Preserve existing artifact")
    temporary = output.with_name(output.name + ".partial")
    with temporary.open("xb") as handle:
        for chunk in chunks:
            with (directory / chunk["name"]).open("rb") as source:
                shutil.copyfileobj(source, handle)
    if temporary.stat().st_size != manifest["bytes"] or sha256(temporary) != manifest["sha256"]:
        raise ValueError("Assembled checksum mismatch; partial file preserved")
    # An exclusive final-file create avoids overwriting a concurrently created target.
    output.hardlink_to(temporary)
    temporary.unlink()
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "assemble"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    result = prepare(args.source, args.destination) if args.mode == "prepare" else assemble(args.source, args.destination)
    print(json.dumps({key: result[key] for key in ("name", "bytes", "sha256")}))


if __name__ == "__main__":
    main()
