"""Part 4 checkpoint guarantees using a deterministic two-node graph."""
from langgraph.graph import END, StateGraph

from tradingagents.graph.checkpointer import get_checkpointer, thread_id


def _workflow(calls, fail):
    def completed_node(state):
        calls.append("completed")
        return {"value": state["value"] + 1}

    def interrupted_node(state):
        calls.append("interrupted")
        if fail[0]:
            raise RuntimeError("injected interruption")
        return {"value": state["value"] + 10}

    builder = StateGraph(dict)
    builder.add_node("completed", completed_node)
    builder.add_node("interrupted", interrupted_node)
    builder.set_entry_point("completed")
    builder.add_edge("completed", "interrupted")
    builder.add_edge("interrupted", END)
    return builder.compile


def _crash_then_resume(tmp_path):
    calls, fail = [], [True]
    compile_graph = _workflow(calls, fail)
    config = {"configurable": {"thread_id": thread_id("TEST", "2026-01-01", "sig")}}
    with get_checkpointer(tmp_path, "TEST") as saver:
        graph = compile_graph(checkpointer=saver)
        try:
            graph.invoke({"value": 0}, config=config)
        except RuntimeError:
            pass
        else:
            raise AssertionError("expected injected interruption")
    fail[0] = False
    with get_checkpointer(tmp_path, "TEST") as saver:
        result = compile_graph(checkpointer=saver).invoke(None, config=config)
    return result, calls


def test_resume_reuse(tmp_path):
    result, calls = _crash_then_resume(tmp_path)
    assert result["value"] == 11
    assert calls.count("completed") == 1


def test_no_duplicate_calls(tmp_path):
    _result, calls = _crash_then_resume(tmp_path)
    assert calls == ["completed", "interrupted", "interrupted"]
