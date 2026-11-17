import check_semantic_eval as g4

GOOD_METRICS = {
    "faithfulness": 0.90, "relevance": 0.90,
    "numeric_consistency": 0.99, "review_rate": 0.01,
}


def test_prompt_change_is_eval_relevant():
    assert g4.is_eval_relevant(["prompts/prompt_v1.yaml"])


def test_analyst_prompt_change_is_eval_relevant():
    assert g4.is_eval_relevant(["tradingagents/agents/analysts/market_analyst.py"])


def test_model_config_change_is_eval_relevant():
    assert g4.is_eval_relevant(["README.md"], changed_config_keys=["temperature"])


def test_non_eval_change_skips():
    result = g4.check(["README.md"], metrics=None)
    assert result.applicable is False
    assert result.status == "skipped"


def test_all_thresholds_pass():
    result = g4.check(["prompts/prompt_v1.yaml"], GOOD_METRICS)
    assert result.passed


def test_one_threshold_below_blocks_and_names_metric():
    metrics = dict(GOOD_METRICS, faithfulness=0.78)
    result = g4.check(["prompts/prompt_v1.yaml"], metrics)
    assert not result.passed
    assert any("faithfulness" in v.detail for v in result.violations)


def test_review_rate_over_max_blocks():
    metrics = dict(GOOD_METRICS, review_rate=0.05)
    result = g4.check(["prompts/prompt_v1.yaml"], metrics)
    assert not result.passed
    assert any("review_rate" in v.detail for v in result.violations)


def test_prompt_change_without_eval_run_blocks():
    result = g4.check(["prompts/prompt_v1.yaml"], metrics=None)
    assert not result.passed
    assert any("not run" in v.reason for v in result.violations)
