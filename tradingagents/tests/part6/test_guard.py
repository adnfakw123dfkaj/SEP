"""Pre-call budget enforcement must live outside LangChain callbacks."""

import pytest
from langchain_core.messages import HumanMessage

from tradingagents.agents.debate.adapter import run_debate_turn
from tradingagents.agents.structured import invoke_structured
from tradingagents.cost.enforcement import BudgetExceededError
from tradingagents.cost.guard import GuardedLLM, prompt_text
from tradingagents.resilience import FallbackLLM

pytestmark = pytest.mark.unit


class _Inner:
    def __init__(self):
        self.calls = []
        self.bound = None
        self.structured = None

    def invoke(self, input, config=None, **kwargs):
        self.calls.append(input)
        return "ok"

    def bind_tools(self, tools, **kwargs):
        self.bound = tools
        return self

    def with_structured_output(self, schema, **kwargs):
        self.structured = schema
        return self


def _guard(**_kwargs):
    raise BudgetExceededError("projected over hard cap")


def test_guarded_llm_stops_before_inner_invoke():
    inner = _Inner()
    llm = GuardedLLM(inner, model="deepseek-flash", check=_guard)

    with pytest.raises(BudgetExceededError, match="projected over hard cap"):
        llm.invoke("Analyse NVDA")

    assert inner.calls == []


def test_guarded_llm_guards_tool_and_structured_bindings():
    inner = _Inner()
    llm = GuardedLLM(inner, model="deepseek-flash", check=_guard)

    with pytest.raises(BudgetExceededError):
        llm.bind_tools([]).invoke("Analyse NVDA")
    with pytest.raises(BudgetExceededError):
        llm.with_structured_output(dict).invoke("Analyse NVDA")

    assert inner.calls == []


def test_guarded_llm_passes_prompt_text_to_the_guard():
    seen = {}

    def check(*, model, prompt_text):
        seen["model"] = model
        seen["prompt_text"] = prompt_text

    GuardedLLM(_Inner(), model="deepseek-flash", check=check).invoke(
        [HumanMessage(content="Analyse NVDA")]
    )

    assert seen == {"model": "deepseek-flash", "prompt_text": "Analyse NVDA"}
    assert prompt_text("hello") == "hello"


def test_fallback_llm_re_raises_budget_errors_without_fallback():
    class Boom:
        def invoke(self, *args, **kwargs):
            raise BudgetExceededError("hard cap")

    class MustNotRun:
        def invoke(self, *args, **kwargs):
            raise AssertionError("fallback must not run on a budget stop")

    with pytest.raises(BudgetExceededError, match="hard cap"):
        FallbackLLM(Boom(), MustNotRun()).invoke("Analyse NVDA")


def test_structured_fallback_re_raises_budget_errors():
    class Boom:
        def with_structured_output(self, *args, **kwargs):
            return self

        def invoke(self, *args, **kwargs):
            raise BudgetExceededError("hard cap")

    class MustNotRun:
        def with_structured_output(self, *args, **kwargs):
            return self

        def invoke(self, *args, **kwargs):
            raise AssertionError("fallback must not run on a budget stop")

    with pytest.raises(BudgetExceededError, match="hard cap"):
        FallbackLLM(Boom(), MustNotRun()).with_structured_output(dict).invoke("prompt")


def test_invoke_structured_re_raises_budget_errors():
    class Structured:
        def invoke(self, *args, **kwargs):
            raise BudgetExceededError("hard cap")

    with pytest.raises(BudgetExceededError, match="hard cap"):
        invoke_structured(Structured(), "prompt", "Portfolio Manager")


def test_debate_turn_re_raises_budget_errors():
    state = {
        "company_of_interest": "NVDA",
        "asset_type": "stock",
        "trade_date": "2026-11-20",
        "market_report": "",
        "sentiment_report": "",
        "news_report": "",
        "fundamentals_report": "",
        "investment_debate_state": {"turns": [], "count": 0},
    }

    def complete(_prompt):
        raise BudgetExceededError("hard cap")

    with pytest.raises(BudgetExceededError, match="hard cap"):
        run_debate_turn(state, "bull", complete)
