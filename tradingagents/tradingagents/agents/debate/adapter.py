"""结构化发言适配层：调用、JSON 解析、一次修复重试与无效占位。"""

import json
from collections.abc import Callable, Mapping
from typing import Any

from tradingagents.agents.context import (
    get_instrument_context_from_state,
    get_language_instruction,
    opponent_argument_or_opening,
    report_or_absent,
)

from .prompts import BEAR_PROMPT, BULL_PROMPT
from .schemas import DebateTurn, Stance
from .stubs import sanitize
from .validator import validate_turn, validate_turns


def _response_text(response: Any) -> str:
    if isinstance(response, str):
        return response
    content = (
        response.get("content")
        if isinstance(response, Mapping)
        else getattr(response, "content", None)
    )
    if isinstance(content, str):
        return content
    raise ValueError("completion must return text or an object with text content")


def _build_prompt(state, debate, speaker, previous, round_number, turn_id):
    opponent = "bear analyst" if speaker == "bull" else "bull analyst"
    current_response = debate.get("current_response", "")
    if not current_response and previous:
        current_response = previous[-1].claim
    history = debate.get("history", "") or json.dumps(
        [turn.model_dump(mode="json") for turn in previous], ensure_ascii=False
    )
    instrument = (
        get_instrument_context_from_state(state)
        if "company_of_interest" in state
        else state.get("instrument_context", "")
    )
    context = "\n".join(
        (
            str(instrument),
            f"Asset type: {state.get('asset_type', 'stock')}",
            "Market research report: " + report_or_absent(state.get("market_report", ""), "market"),
            "Social media sentiment report: "
            + report_or_absent(state.get("sentiment_report", ""), "sentiment"),
            "Latest world affairs news: " + report_or_absent(state.get("news_report", ""), "news"),
            "Fundamentals report: "
            + report_or_absent(state.get("fundamentals_report", ""), "fundamentals"),
            "Conversation history of the debate: " + history,
            "Last opponent argument: " + opponent_argument_or_opening(current_response, opponent),
        )
    )
    parameters = {
        "turn_id": turn_id,
        "round": round_number,
        "speaker": speaker,
        "previous_turn_ids": [turn.turn_id for turn in previous],
    }
    return sanitize(
        "\n\n".join(
            (
                BULL_PROMPT if speaker == "bull" else BEAR_PROMPT,
                context,
                "本次发言参数：\n" + json.dumps(parameters, ensure_ascii=False),
                "round 和 speaker 必须与本次参数一致；turn_id 必须在历史中唯一。",
                get_language_instruction(),
            )
        )
    )


def run_debate_turn(
    state: Mapping[str, Any], speaker: str, complete: Callable[[str], Any]
) -> DebateTurn:
    """最多调用 complete 两次；模型失败返回占位，不直接修改 state。"""
    if speaker not in ("bull", "bear"):
        raise ValueError("speaker must be bull or bear")
    debate = state.get("investment_debate_state", {})
    previous = validate_turns(debate.get("turns", []))
    round_number = max(debate.get("count", 0), previous[-1].round if previous else 0) + 1
    turn_id = f"{speaker}-{round_number}"
    existing_ids = {turn.turn_id for turn in previous}
    suffix = 1
    while turn_id in existing_ids:
        turn_id = f"{speaker}-{round_number}-{suffix}"
        suffix += 1
    prompt = _build_prompt(state, debate, speaker, previous, round_number, turn_id)
    retry_prompt = prompt + (
        "\n\n上次输出未通过 JSON 或辩论契约校验。"
        "请重新输出完整的单个 JSON 对象，保持本次 round、speaker 和已有引用约束。"
    )
    for attempt in range(2):
        try:
            text = _response_text(complete(prompt if attempt == 0 else retry_prompt))
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise ValueError("completion must contain one JSON object")
            turn = validate_turn(
                payload,
                previous,
                expected_speaker=speaker,
                expected_round=round_number,
            )
            if turn.status != "ok":
                raise ValueError("completion reported an invalid turn")
            return turn
        except Exception:
            # 不记录模型原文或异常原文，也不把它们复制进重试提示。
            continue

    return DebateTurn(
        turn_id=turn_id,
        round=round_number,
        speaker=speaker,
        claim="本轮结构化发言不可用，请由 Research Manager 基于已有内容总结。",
        stance=Stance.NEUTRAL,
        evidence_refs=[],
        assumptions=[],
        rebuttal_to=None,
        confidence=0.0,
        open_questions=[],
        requested_evidence=[],
        no_new_evidence=True,
        status="invalid",
    )


__all__ = ["run_debate_turn"]
