"""Step 10a: real provider calls -> LLMCallEvent via LangChain callback."""

import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from langchain_core.messages import HumanMessage

from tradingagents.contracts.llm_event import CallStatus, RoutePath, UsageSource
from tradingagents.cost.agent_context import agent_scope, current_agent, with_agent_scope
from tradingagents.cost.callback import CostTrackingCallback

pytestmark = pytest.mark.unit


class FakeMessage:
    def __init__(self, content="", usage_metadata=None, response_metadata=None):
        self.content = content
        self.usage_metadata = usage_metadata or {}
        self.response_metadata = response_metadata or {}


class FakeGeneration:
    def __init__(self, text="", message=None):
        self.text = text
        self.message = message


class FakeLLMResult:
    def __init__(self, llm_output=None, generations=None):
        self.llm_output = llm_output or {}
        self.generations = generations or []


def _emit(callback, model="deepseek-flash"):
    langchain_run_id = uuid4()
    callback.on_chat_model_start(
        {"kwargs": {"model_name": model}},
        [[HumanMessage(content="Analyse NVDA")]],
        run_id=langchain_run_id,
    )
    callback.on_llm_end(
        FakeLLMResult(
            llm_output={
                "token_usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                }
            },
            generations=[[FakeGeneration(text="ok")]],
        ),
        run_id=langchain_run_id,
    )


def test_tc_p6_cap_001_chat_model_usage_event():
    """TC-P6-CAP-001: provider usage becomes one structured event."""
    events = []
    callback = CostTrackingCallback(
        run_id="run-1",
        on_event=events.append,
        agent_name="market",
        provider="deepseek",
    )
    langchain_run_id = uuid4()

    callback.on_chat_model_start(
        {"kwargs": {"model_name": "deepseek-flash"}},
        [[HumanMessage(content="Analyse NVDA")]],
        run_id=langchain_run_id,
    )
    callback.on_llm_end(
        FakeLLMResult(
            llm_output={
                "token_usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                }
            },
            generations=[[FakeGeneration(text="ok")]],
        ),
        run_id=langchain_run_id,
    )

    assert len(events) == 1
    event = events[0]
    assert event.run_id == "run-1"
    assert event.call_id == str(langchain_run_id)
    assert event.agent_name == "market"
    assert event.model == "deepseek-flash"
    assert event.provider == "deepseek"
    assert event.prompt_tokens == 10
    assert event.completion_tokens == 5
    assert event.total_tokens == 15
    assert event.status is CallStatus.SUCCESS
    assert event.usage_source is UsageSource.PROVIDER
    assert event.route_path is RoutePath.DIRECT
    assert event.latency_ms >= 0
    assert event.cache_hit is False


def test_tc_p6_cap_002_fallback_estimation():
    """TC-P6-CAP-002: missing provider usage falls back to the estimator."""
    events = []
    callback = CostTrackingCallback(
        run_id="run-1",
        on_event=events.append,
        agent_name="market",
        provider="deepseek",
    )
    langchain_run_id = uuid4()

    callback.on_chat_model_start(
        {"kwargs": {"model_name": "deepseek-flash"}},
        [[HumanMessage(content="Analyse NVDA")]],
        run_id=langchain_run_id,
    )
    callback.on_llm_end(
        FakeLLMResult(
            llm_output={},
            generations=[
                [
                    FakeGeneration(
                        text="OK",
                        message=FakeMessage(content="OK", usage_metadata={}),
                    )
                ]
            ],
        ),
        run_id=langchain_run_id,
    )

    event = events[0]
    assert event.usage_source is UsageSource.ESTIMATED
    assert event.prompt_tokens > 0
    assert event.completion_tokens > 0
    assert event.total_tokens == event.prompt_tokens + event.completion_tokens


def test_tc_p6_cap_003_error_event():
    """TC-P6-CAP-003: provider failure still emits an auditable event."""
    events = []
    callback = CostTrackingCallback(
        run_id="run-1",
        on_event=events.append,
        agent_name="market",
        provider="deepseek",
    )
    langchain_run_id = uuid4()

    callback.on_chat_model_start(
        {"kwargs": {"model_name": "deepseek-flash"}},
        [[HumanMessage(content="Analyse NVDA")]],
        run_id=langchain_run_id,
    )
    callback.on_llm_error(RuntimeError("boom"), run_id=langchain_run_id)

    event = events[0]
    assert event.status is CallStatus.FAILURE
    assert event.total_tokens == 0
    assert event.latency_ms >= 0


def test_tc_p6_cap_004_plain_llm_and_model_extraction():
    """TC-P6-CAP-004: non-chat calls and alternate usage keys work too."""
    events = []
    callback = CostTrackingCallback(
        run_id="run-1",
        on_event=events.append,
        agent_name="news",
        provider="deepseek",
    )
    langchain_run_id = uuid4()

    callback.on_llm_start(
        {"kwargs": {"model": "deepseek-v4-pro"}},
        ["Summarise the news"],
        run_id=langchain_run_id,
    )
    callback.on_llm_end(
        FakeLLMResult(
            llm_output={
                "usage": {
                    "input_tokens": 4,
                    "output_tokens": 2,
                    "total_tokens": 6,
                }
            },
            generations=[[FakeGeneration(text="summary")]],
        ),
        run_id=langchain_run_id,
    )

    event = events[0]
    assert event.model == "deepseek-v4-pro"
    assert event.agent_name == "news"
    assert event.prompt_tokens == 4
    assert event.completion_tokens == 2
    assert event.total_tokens == 6
    assert event.usage_source is UsageSource.PROVIDER


def test_tc_p6_cap_005_default_and_scope():
    """TC-P6-CAP-005: a scope overrides the callback's default agent name."""
    events = []
    callback = CostTrackingCallback(
        run_id="run-1",
        on_event=events.append,
        agent_name="default-agent",
        provider="deepseek",
    )

    assert current_agent() is None
    _emit(callback)
    with agent_scope("market_analyst"):
        assert current_agent() == "market_analyst"
        _emit(callback)

    assert [event.agent_name for event in events] == [
        "default-agent",
        "market_analyst",
    ]


def test_tc_p6_cap_006_nested_scope_restores():
    """TC-P6-CAP-006: nested scopes attribute inner and restore outer."""
    events = []
    callback = CostTrackingCallback(
        run_id="run-1",
        on_event=events.append,
        agent_name="default-agent",
        provider="deepseek",
    )

    with agent_scope("outer"):
        _emit(callback)
        with agent_scope("inner"):
            _emit(callback)
        _emit(callback)

    assert [event.agent_name for event in events] == ["outer", "inner", "outer"]


def test_tc_p6_cap_007_threads_do_not_leak_agent_context():
    """TC-P6-CAP-007: parallel threads keep their own agent names."""
    events = []
    lock = threading.Lock()

    def on_event(event):
        with lock:
            events.append(event)

    callback = CostTrackingCallback(
        run_id="run-1",
        on_event=on_event,
        agent_name="default-agent",
        provider="deepseek",
    )

    def run(name):
        with agent_scope(name):
            _emit(callback)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run, ["market", "news"]))

    assert {event.agent_name for event in events} == {"market", "news"}


def test_tc_p6_cap_008_with_agent_scope_wrapper():
    """TC-P6-CAP-008: graph nodes can be wrapped without touching their body."""
    events = []
    callback = CostTrackingCallback(
        run_id="run-1",
        on_event=events.append,
        agent_name="default-agent",
        provider="deepseek",
    )

    def node(state):
        _emit(callback)
        return state

    wrapped = with_agent_scope("trader", node)
    assert wrapped({}) == {}
    assert wrapped.__name__ == "node"
    assert events[0].agent_name == "trader"
