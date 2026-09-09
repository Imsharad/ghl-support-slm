import json
from pathlib import Path
import pytest
from eval.replay_published_v3 import replay


def test_published_counts_replay_and_changed_headline_is_rejected():
    path = Path(__file__).resolve().parents[2] / 'eval/results/v3/final01/partial-mixed-analysis-001/analysis.json'
    result = json.loads(path.read_text())
    assert replay(result)['observed']['pass_counts'] == {'base': 59, 'tuned': 81}
    result['observed']['pass_counts']['tuned'] += 1
    with pytest.raises(ValueError, match='published summary does not replay: observed'):
        replay(result)
