"""A changed reconstructed answer must never be accepted against a frozen hash."""
import pytest
from data.restore_v1 import verify_splits
from data.prepare import sha256_jsonl


def test_changed_response_is_rejected_against_original_digest():
    rows = {name: [{'id': name, 'response': 'original'}] for name in ('train', 'val', 'test')}
    expected = {name: sha256_jsonl(values) for name, values in rows.items()}
    verify_splits(rows, expected)
    rows['val'][0]['response'] = 'changed supervision'
    with pytest.raises(ValueError, match='val: reconstruction differs'):
        verify_splits(rows, expected)
