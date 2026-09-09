from tools.candidate04_development_local import commands


def test_all_models_same_local_conditions_and_development_only():
    plans = list(commands("python"))
    assert len(plans) == 10
    for command in plans:
        assert command[:4] == ["python", "-u", "-m", "eval.run"]
        assert command[command.index("--device") + 1] == "mps"
        assert command[command.index("--split") + 1] == "dev"
        assert command[command.index("--input") + 1] in (
            "eval/v3/development-boundaries-01.jsonl", "data/processed/v3-candidate04/val.jsonl")
        assert "--check-complete" in command
        assert "candidate04-mps" in command[command.index("--output") + 1]
    assert sum("--adapter" not in command for command in plans) == 2
    for step in (30, 60, 90, 120):
        assert sum(command[-1].endswith(f"checkpoint-{step}") for command in plans) == 2
