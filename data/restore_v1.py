"""Reconstruct sealed v1 JSONL from pinned raw CSV and recorded group assignments.

Does not rerun embedding clustering, depend on Git history, or rewrite evidence.
All reconstructed split hashes must match the original seal before any write.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data import prepare


def verify_splits(rows: dict, expected: dict) -> None:
    for name in prepare.SPLIT_NAMES:
        if prepare.sha256_jsonl(rows[name]) != expected[name]:
            raise ValueError(f'{name}: reconstruction differs from the original seal; nothing written')


def restore(output: Path) -> None:
    assignment = json.loads((ROOT / 'data/v1_assignment.json').read_text())
    seal = json.loads((ROOT / 'eval/SEAL.json').read_text())
    if assignment['split_sha256'] != seal['split_sha256']:
        raise ValueError('assignment provenance differs from the original seal')
    if prepare.sha256_file(prepare.CSV_PATH) != assignment['raw_sha256']:
        raise ValueError('raw CSV differs from the pinned source; run data/fetch.py')
    mapping = {row[0]: (row[1], row[2]) for row in assignment['rows']}
    if len(mapping) != len(assignment['rows']):
        raise ValueError('duplicate source IDs in assignment')
    cleaned = prepare.load_cleaning()
    collator = prepare.get_collator()
    splits = {name: [] for name in prepare.SPLIT_NAMES}
    for source in prepare.load_csv().to_dict('records'):
        if source['id'] not in mapping:
            continue
        instruction, response, rules, rejected = prepare.apply_cleaning(
            source['instruction'], source['response'], cleaned)
        if rejected:
            raise ValueError(f"sealed source now rejected: {source['id']}")
        n_tokens = prepare.count_tokens(instruction, response, collator)
        if n_tokens is None:
            raise ValueError(f"sealed source now exceeds token budget: {source['id']}")
        group_id, split = mapping[source['id']]
        values = dict(source, group_id=group_id, instruction=instruction,
                      response=response, cleaning=list(dict.fromkeys(rules)), n_tokens=n_tokens)
        splits[split].append({key: values[key] for key in prepare.ROW_KEYS})
    for rows in splits.values():
        rows.sort(key=lambda row: row['id'])
    verify_splits(splits, seal['split_sha256'])
    # Check every existing destination before writing any file.
    for name in prepare.SPLIT_NAMES:
        path = output / f'{name}.jsonl'
        if path.exists() and prepare.sha256_file(path) != seal['split_sha256'][name]:
            raise ValueError(f'refusing to replace different existing file: {path}')
    output.mkdir(parents=True, exist_ok=True)
    for name, rows in splits.items():
        prepare.write_jsonl(output / f'{name}.jsonl', rows)
        print(f'{name}: {len(rows)} rows; original sealed hash verified')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=prepare.PROCESSED_DIR)
    restore(parser.parse_args().output)


if __name__ == '__main__':
    main()
