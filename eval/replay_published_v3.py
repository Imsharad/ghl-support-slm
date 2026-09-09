"""Verify reported arithmetic from published model-labelled grades, without a key.

Does not validate judge correctness or independently reconstruct the blind mapping.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eval.analyze_partial_v3 import describe, sensitivity
from eval.v3_metrics import summarize_pairs, validate_pairs
from train.repro import sha256_file


def replay(result: dict) -> dict:
    rows, missing = result['pairs'], result['skipped']
    hypothetical = [{**row, 'preferred': 'tie', **{
        model: dict.fromkeys(('pass', 'critical', 'credential_violation'), False)
        for model in ('base', 'tuned')}} for row in missing]
    validate_pairs(rows + hypothetical, intents={r['intent'] for r in rows + missing})
    stats = summarize_pairs(rows)
    verdict = stats.pop('verdict')
    stats['observed_macro_cluster_ci95_points'] = stats.pop('primary_cluster_ci95_points')
    stats['observed_macro_difference_points'] = stats.pop('difference_percentage_points')
    computed = {
        'observed': describe(rows), 'observed_macro_analysis': stats,
        'observed_numeric_gates_only': verdict,
        'by_judge': {role: describe([r for r in rows if r['judge_source'] == role])
                     for role in sorted({r['judge_source'] for r in rows})},
        'missing_case_sensitivity': sensitivity(rows, missing),
    }
    for key, value in computed.items():
        if value != result[key]:
            raise ValueError(f'published summary does not replay: {key}')
    return computed


def main() -> None:
    final = ROOT / 'eval/results/v3/final01'
    path = final / 'partial-mixed-analysis-001/analysis.json'
    result = json.loads(path.read_text())
    bindings = result['bindings']
    if sha256_file(final / 'SEAL.json') != bindings['seal_sha256']:
        raise ValueError('final seal changed')
    for model in ('base', 'tuned'):
        for filename, key in [(f'{model}-raw.jsonl', 'raw_sha256'),
                              (f'{model}-raw.jsonl.manifest.json', 'manifest_sha256')]:
            if sha256_file(final / filename) != bindings[key][model]:
                raise ValueError(f'final evidence changed: {filename}')
    computed = replay(result)
    print(json.dumps({'arithmetic_verified': True, 'observed': computed['observed'],
                      'numeric_gate': computed['observed_numeric_gates_only'],
                      'limitation': 'Checks published arithmetic and raw-file hashes, not judge correctness or private blind mapping.'}, indent=2))


if __name__ == '__main__':
    main()
