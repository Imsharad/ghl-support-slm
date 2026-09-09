import pytest

from tools.training.check_cuda_host import cuda_requirement, validate_host

LOCK = {"package": [{"name": "cuda-toolkit", "version": "13.0.3.0"}]}
GPU = "580.95.05, 24564, NVIDIA GeForce RTX 4090\n"
SPACE = 30 * 1024**3


def test_compatible_host_reports_necessary_conditions_only():
    result = validate_host(LOCK, "Linux", "x86_64", GPU, SPACE)
    assert result["driver"] == "580.95.05"
    assert result["minimum_driver_major"] == 580
    assert "Not a CUDA kernel" in result["limitations"]


@pytest.mark.parametrize("system,machine,gpu,space,match", [
    ("Darwin", "arm64", GPU, SPACE, "Linux x86_64"),
    ("Linux", "x86_64", GPU.replace("580.95.05", "570.195.03"), SPACE, "requires driver"),
    ("Linux", "x86_64", GPU + GPU, SPACE, "exactly one GPU"),
    ("Linux", "x86_64", GPU.replace("24564", "8192"), SPACE, "14 GiB"),
    ("Linux", "x86_64", GPU, 24 * 1024**3, "25 GiB"),
])
def test_incompatible_host_fails_before_install(system, machine, gpu, space, match):
    with pytest.raises(ValueError, match=match):
        validate_host(LOCK, system, machine, gpu, space)


def test_unreviewed_or_ambiguous_cuda_fails():
    with pytest.raises(ValueError, match="exactly one"):
        cuda_requirement({"package": []})
    with pytest.raises(ValueError, match="unreviewed"):
        cuda_requirement({"package": [{"name": "cuda-toolkit", "version": "14.0"}]})
    with pytest.raises(ValueError, match="at least 25"):
        validate_host(LOCK, "Linux", "x86_64", GPU, SPACE, min_free_gib=0)
