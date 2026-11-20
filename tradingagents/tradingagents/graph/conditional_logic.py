from tradingagents.agents.state import AgentState


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1):
        """Initialize with configuration parameters."""
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

    def should_continue_debate(self, state: AgentState) -> str:
        """Determine if debate should continue."""

        from tradingagents.agents.debate.convergence import should_stop

        debate = state["investment_debate_state"]
        turns = debate.get("turns", [])
        if debate.get("enable_structured_debate", True) and turns:
            stopped = should_stop(turns, self.max_debate_rounds)
            latest = turns[-1]
            status = latest.get("status") if isinstance(latest, dict) else latest.status
            # 无效发言直接转交现有主持人；它不属于收敛早停。
            if stopped or status == "invalid":
                return "Research Manager"
            speaker = latest.get("speaker") if isinstance(latest, dict) else latest.speaker
            return "Bear Researcher" if speaker == "bull" else "Bull Researcher"

        if (
            state["investment_debate_state"]["count"] >= 2 * self.max_debate_rounds
        ):  # max_debate_rounds turns each for bull and bear
            return "Research Manager"
        if state["investment_debate_state"]["current_response"].startswith("Bull"):
            return "Bear Researcher"
        return "Bull Researcher"

    def should_continue_risk_analysis(self, state: AgentState) -> str:
        """Determine if risk analysis should continue."""
        if (
            state["risk_debate_state"]["count"] >= 3 * self.max_risk_discuss_rounds
        ):  # max_risk_discuss_rounds turns each for the three risk analysts
            return "Portfolio Manager"
        if state["risk_debate_state"]["latest_speaker"].startswith("Aggressive"):
            return "Conservative Analyst"
        if state["risk_debate_state"]["latest_speaker"].startswith("Conservative"):
            return "Neutral Analyst"
        return "Aggressive Analyst"
