"""只重新导出唯一契约，不在此处定义字段或模型。"""

from tradingagents.contracts.debate import DebateTranscript, DebateTurn, Stance

__all__ = ["DebateTranscript", "DebateTurn", "Stance"]
