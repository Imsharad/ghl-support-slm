import pytest
from tools.training.runpod_deadline import verify_identity


def test_deadline_targets_only_exact_pod_and_persistent_volume():
    pod = {"id": "test-pod", "name": "test-name", "networkVolumeId": "test-volume"}
    verify_identity(pod, "test-pod", "test-name", "test-volume")
    verify_identity(None, "test-pod", "test-name", "test-volume")
    for field in pod:
        changed = dict(pod, **{field: "different"})
        with pytest.raises(ValueError, match="identity"):
            verify_identity(changed, "test-pod", "test-name", "test-volume")
