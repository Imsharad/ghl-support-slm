from tools.quality.check_submission import collect_hub_urls


def test_v3_urls_require_adapter_and_both_evaluated_weights_but_not_merged():
    required = ('repo', 'adapter', 'base_gguf', 'tuned_gguf')
    hub = {key: 'https://example.org/' + key for key in required}
    failures = []
    assert len(collect_hub_urls(hub, failures, required_fields=required)) == 4
    assert not failures
    hub['tuned_gguf'] = None
    collect_hub_urls(hub, failures, required_fields=required)
    assert any('tuned_gguf' in failure for failure in failures)
