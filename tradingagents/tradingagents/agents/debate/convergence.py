"""研究辩论的最大轮数与完整双方轮次收敛判断。"""

from .validator import validate_turns


def should_stop(transcript, max_rounds: int) -> bool:
    """达到上限停止；早停必须比较相邻两个完整双方轮次。"""
    if isinstance(max_rounds, bool) or not isinstance(max_rounds, int) or max_rounds < 0:
        raise ValueError("max_rounds must be a nonnegative integer")
    turns = validate_turns(transcript)
    if len(turns) >= 2 * max_rounds:
        return True
    # 只有双方都完成当前轮次，且各自都有上一轮立场可比较时才考虑收敛。
    if len(turns) < 4 or len(turns) % 2:
        return False
    previous, latest = turns[-4:-2], turns[-2:]
    if {turn.speaker for turn in previous} != {"bull", "bear"}:
        return False
    if {turn.speaker for turn in latest} != {"bull", "bear"}:
        return False
    if any(turn.status != "ok" for turn in previous + latest):
        return False
    if not all(turn.no_new_evidence for turn in latest):
        return False
    previous_stances = {turn.speaker: turn.stance for turn in previous}
    return all(turn.stance == previous_stances[turn.speaker] for turn in latest)


__all__ = ["should_stop"]
