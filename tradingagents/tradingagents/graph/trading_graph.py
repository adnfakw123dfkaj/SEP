import hashlib
import json
import logging
import os
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import tradingagents
from tradingagents.agents.context import build_instrument_context, resolve_instrument_identity
from tradingagents.agents.debate.export import resolve_evidence_refs
from tradingagents.agents.rating import is_review, run_rating
from tradingagents.contracts import ALLOWED_RATINGS, Provenance, RunManifest
from tradingagents.dataflows.config import run_config, run_config_context, set_config
from tradingagents.dataflows.date_window import get_current_date, is_historical
from tradingagents.dataflows.symbols import safe_ticker_component
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.evidence import evidence_scope
from tradingagents.llm_clients import create_tier_client, tier_provider
from tradingagents.memory import TradingMemoryLog, settlement
from tradingagents.memory.reflection import Reflector
from tradingagents.preflight import validate_request
from tradingagents.profiles import resolve_run_profile
from tradingagents.rating_authority import commit_rating
from tradingagents.records import FileRatingStore, write_run_manifest
from tradingagents.records.idempotency import record_id
from tradingagents.reporting import write_report_tree
from tradingagents.resilience import FallbackLLM, fallback_event_scope
from tradingagents.security import drain_events, validate_output

from .checkpointer import checkpoint_step, clear_checkpoint, get_checkpointer, thread_id
from .conditional_logic import ConditionalLogic
from .propagation import Propagator
from .setup import GraphSetup

logger = logging.getLogger(__name__)


def _validate_trade_date(trade_date) -> str:
    """The run date as a canonical ``YYYY-MM-DD`` string no later than today."""
    value = str(trade_date)
    try:
        canonical = datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d") == value
    except ValueError:
        canonical = False
    if not canonical:
        raise ValueError(f"trade_date must be a date in YYYY-MM-DD format, got {trade_date!r}")
    if value > get_current_date():
        raise ValueError(f"trade_date cannot be in the future: {value}")
    return value


# Config keys that do not change what a run writes: where it keeps its files,
# whether it checkpoints, and how often it retries a provider.
_NOT_IN_SIGNATURE = frozenset({
    "results_dir", "data_cache_dir", "memory_log_path", "checkpoint_enabled", "llm_max_retries",
})


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts: tuple[str, ...] | None = None,
        debug=False,
        config: dict[str, Any] = None,
        callbacks: list | None = None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: Analyst types to include. When omitted and
                ``run_profile`` names a preset, the profile's analyst set is used.
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
            callbacks: Optional list of callback handlers (e.g., for tracking LLM/tool stats)
        """
        self.debug = debug
        self.config = dict(config or DEFAULT_CONFIG)
        self.config, resolved_analysts = resolve_run_profile(self.config, selected_analysts)
        if (
            config is not None
            and "checkpoint_enabled" not in config
            and self.config.get("run_profile") in ("standard", "deep")
        ):
            self.config["checkpoint_enabled"] = True
        self.selected_analysts = tuple(
            resolved_analysts
            if resolved_analysts is not None
            else ("market", "social", "news", "fundamentals")
        )
        self.callbacks = callbacks or []

        set_config(self.config)

        os.makedirs(self.config["data_cache_dir"], exist_ok=True)
        os.makedirs(self.config["results_dir"], exist_ok=True)

        extra = {"callbacks": self.callbacks} if self.callbacks else {}
        self.deep_thinking_llm = create_tier_client(self.config, "deep", **extra).get_llm()
        self.quick_thinking_llm = create_tier_client(self.config, "quick", **extra).get_llm()
        if (
            self.config.get("llm_fallback_to_quick", True)
            and self.deep_thinking_llm is not self.quick_thinking_llm
        ):
            self.deep_thinking_llm = FallbackLLM(
                self.deep_thinking_llm,
                self.quick_thinking_llm,
            )

        self.memory_log = TradingMemoryLog(self.config)
        rating_root = self.config.get("rating_store_dir")
        if not rating_root:
            log_path = self.config.get("memory_log_path")
            rating_root = (
                Path(log_path).expanduser().parent / "rating_records"
                if log_path
                else Path(self.config["data_cache_dir"]) / "rating_records"
            )
        self.rating_store = FileRatingStore(rating_root)

        self.conditional_logic = ConditionalLogic(
            max_debate_rounds=self.config["max_debate_rounds"],
            max_risk_discuss_rounds=self.config["max_risk_discuss_rounds"],
        )
        # An analyst takes two graph steps per tool round, plus its first turn
        # and its wrap-up; a limit past the recursion limit would end the run
        # there instead.
        max_tool_rounds, max_recur_limit = self.config["max_tool_rounds"], self.config["max_recur_limit"]
        if 2 * max_tool_rounds + 2 >= max_recur_limit:
            raise ValueError(
                f"max_tool_rounds={max_tool_rounds} needs max_recur_limit above {2 * max_tool_rounds + 2}"
            )
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.conditional_logic,
            max_tool_rounds,
        )

        self.propagator = Propagator(
            max_recur_limit=max_recur_limit,
        )
        self.reflector = Reflector(self.quick_thinking_llm)

        # Set up the graph: keep the workflow for recompilation with a checkpointer.
        self.workflow = self.graph_setup.setup_graph(self.selected_analysts, memory_node=self._memory_step)
        self.graph = self.workflow.compile()
        self._checkpointer_ctx = None
        self._resuming = False
        self.last_evidence_registry = None

    def resolve_instrument_context(self, ticker: str, asset_type: str = "stock",
                                   trade_date: str | None = None) -> str:
        """Resolve ticker identity once and return the full instrument context.

        Deterministic yfinance lookup (cached, fail-open) injected into a
        context string so every agent anchors to the real company instead of
        hallucinating one from the price chart (#814). Both the propagate()
        path and the CLI call this so the resolved identity reaches the whole
        graph regardless of entry point.
        """
        identity = resolve_instrument_identity(ticker)
        return build_instrument_context(ticker, asset_type, identity, trade_date)

    def _memory_as_of(self, trade_date) -> str | None:
        """Point-in-time cutoff for past-context lessons (#1251).

        A historical/backtest run (trade date before today) filters lessons to
        those already resolved by the trade date. A current-date run returns
        None, disabling the filter so live behavior and pre-migration entries
        (which have no stored resolution date) are unaffected.
        """
        return str(trade_date) if is_historical(trade_date) else None

    def run_signature(self, asset_type: str = "stock", portfolio=None) -> str:
        """Public stable key for checkpointing and idempotent decision records."""
        return self._run_signature(asset_type, portfolio)

    def _config_hash(self) -> str:
        """Stable hash of the settings that affect a run's output."""
        return hashlib.sha256(
            json.dumps(
                {k: v for k, v in self.config.items() if k not in _NOT_IN_SIGNATURE},
                sort_keys=True,
                default=str,
            ).encode()
        ).hexdigest()[:16]

    def _run_signature(self, asset_type: str, portfolio=None) -> str:
        """Run inputs that must invalidate a checkpoint if changed.

        Keyed into the checkpoint thread ID so a resume under a different analyst
        selection, debate/risk depth, or asset mode starts fresh instead of
        silently continuing the previous graph (#1089). The rest of the config
        counts too (provider, models, endpoint, language, vendors, limits): a
        resume must not carry reports that other settings produced. Only where
        the run keeps its files and how it retries are left out.
        """
        settings = {k: v for k, v in self.config.items() if k not in _NOT_IN_SIGNATURE}
        digest = hashlib.sha256(json.dumps(settings, sort_keys=True, default=str).encode()).hexdigest()[:12]
        return "|".join([
            "analysts=" + ",".join(self.selected_analysts),
            f"debate={self.config['max_debate_rounds']}",
            f"risk={self.config['max_risk_discuss_rounds']}",
            f"asset={asset_type}",
            # None, an empty book and a changed book are three different runs.
            f"portfolio={portfolio.fingerprint() if portfolio is not None else 'none'}",
            # The layout itself: a checkpoint saved when analysts ran one after
            # another has pending nodes this graph no longer has, and one saved
            # before the Memory Log step would resume without the lessons.
            "analysts=parallel",
            "memory=parallel",
            f"settings={digest}",
        ])

    def propagate(self, company_name, trade_date, asset_type: str = "stock", portfolio=None):
        """Run the trading agents graph for a company on a specific date.

        ``asset_type`` selects between the stock pipeline (default) and the
        crypto pipeline (``"crypto"``) shipped in #567 — the CLI auto-detects
        from the ticker; programmatic callers pass it explicitly. When
        ``checkpoint_enabled`` is set in config, the graph is recompiled with
        a per-ticker SqliteSaver so a crashed run can resume from the last
        successful node on a subsequent invocation with the same ticker+date.

        Returns ``(final_state, signal)`` where ``signal`` is one of the 5-tier
        ratings (Buy / Overweight / Hold / Underweight / Sell) or ``"REVIEW"``
        when the decision had no parseable rating (#1170); guard with
        ``tradingagents.agents.rating.is_review`` before mapping it to the
        PortfolioRating enum.
        """
        trade_date = _validate_trade_date(trade_date)
        if self.config.get("preflight_enabled", True):
            preflight = validate_request(company_name, trade_date, config=self.config)
            if not preflight.ok:
                raise ValueError(
                    f"preflight failed for {preflight.ticker}: {preflight.reason}"
                )

        with run_config(self.config), \
                self.checkpoint_scope(company_name, trade_date, asset_type, portfolio) as thread_id_value:
            return self._run_graph(
                company_name, trade_date, asset_type=asset_type,
                checkpoint_thread_id=thread_id_value, portfolio=portfolio,
            )

    def begin_checkpoint(self, company_name, trade_date, asset_type: str = "stock", portfolio=None) -> str | None:
        """Recompile the graph with a per-ticker checkpointer and return the
        ``thread_id`` to inject into the stream/invoke ``config`` (or ``None``
        when checkpointing is disabled).

        Pair every call with :meth:`end_checkpoint` in a ``finally``. Both
        ``propagate`` (via :meth:`checkpoint_scope`) and the CLI stream path use
        this so ``--checkpoint`` actually resumes (#1249); previously the setup
        lived only inside ``propagate`` and the CLI streamed the checkpointer-less
        graph, making the flag a no-op.
        """
        self._resuming = False
        if not self.config.get("checkpoint_enabled"):
            return None
        signature = self._run_signature(asset_type, portfolio)
        self._checkpointer_ctx = get_checkpointer(self.config["data_cache_dir"], company_name)
        saver = self._checkpointer_ctx.__enter__()
        self.graph = self.workflow.compile(checkpointer=saver)

        step = checkpoint_step(
            self.config["data_cache_dir"], company_name, str(trade_date), signature
        )
        self._resuming = step is not None
        if step is not None:
            logger.info("Resuming from step %d for %s on %s", step, company_name, trade_date)
        else:
            logger.info("Starting fresh for %s on %s", company_name, trade_date)
        return thread_id(company_name, str(trade_date), signature)

    def checkpoint_input(self, init_state):
        """The value to stream/invoke: ``None`` to resume an existing checkpoint,
        else the initial state for a fresh run.

        LangGraph resumes an interrupted thread when invoked with ``None``;
        re-passing the initial state instead appends it through the message
        reducer, duplicating messages in the resumed state (#1249).
        """
        return None if self._resuming else init_state

    def end_checkpoint(self):
        """Restore the plain uncheckpointed graph after a checkpointed run."""
        if self._checkpointer_ctx is not None:
            self._checkpointer_ctx.__exit__(None, None, None)
            self._checkpointer_ctx = None
            self.graph = self.workflow.compile()
        self._resuming = False

    @contextmanager
    def checkpoint_scope(self, company_name, trade_date, asset_type: str = "stock", portfolio=None):
        """Context-manager form of begin/end_checkpoint for the propagate path."""
        try:
            yield self.begin_checkpoint(company_name, trade_date, asset_type, portfolio)
        finally:
            self.end_checkpoint()

    def clear_checkpoint_on_success(self, company_name, trade_date, asset_type: str = "stock", portfolio=None):
        """Drop a completed run's checkpoint so a later run starts fresh (#1249)."""
        if self.config.get("checkpoint_enabled"):
            clear_checkpoint(
                self.config["data_cache_dir"], company_name, str(trade_date),
                self._run_signature(asset_type, portfolio),
            )

    def run_settings(self) -> dict:
        """What produces this graph's runs, for the saved report and state log.

        An allowlist: endpoints (a backend_url can carry credentials), keys and
        local paths are never recorded.
        """
        cfg = self.config
        return {
            "version": tradingagents.__version__,
            "llm_provider": cfg.get("llm_provider"),
            "deep_think_provider": tier_provider(cfg, "deep") if cfg.get("llm_provider") else None,
            "deep_think_llm": cfg.get("deep_think_llm"),
            "quick_think_provider": tier_provider(cfg, "quick") if cfg.get("llm_provider") else None,
            "quick_think_llm": cfg.get("quick_think_llm"),
            "analysts": list(self.selected_analysts),
            "max_debate_rounds": cfg.get("max_debate_rounds"),
            "max_risk_discuss_rounds": cfg.get("max_risk_discuss_rounds"),
            "output_language": cfg.get("output_language"),
            "data_vendors": dict(cfg.get("data_vendors") or {}),
            "tool_vendors": dict(cfg.get("tool_vendors") or {}),
        }

    def save_reports(self, final_state, ticker, save_path=None, html=True) -> Path:
        """Write the report tree for a completed run, like the CLI does.

        Programmatic callers get the same on-disk reports the CLI produces. Pass
        an explicit ``save_path`` or let it default under ``results_dir``; the
        report is also written as one HTML page unless ``html`` is False.
        """
        if save_path is None:
            save_path = self.default_report_path(ticker)
        return write_report_tree(final_state, ticker, save_path, settings=self.run_settings(), html=html)

    def default_report_path(self, ticker) -> Path:
        """Where a run's reports go unless told otherwise: under results_dir, stamped now."""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return Path(self.config["results_dir"]) / "reports" / f"{safe_ticker_component(ticker)}_{stamp}"

    def create_run_state(self, company_name, trade_date, asset_type: str = "stock", portfolio=None):
        """Build a run's initial state; propagate() and the CLI both start here.

        Injects the resolved instrument identity for every agent (#814). The
        memory log's lessons are not here: the graph's Memory Log step settles
        and loads them alongside the analysts (see ``_memory_step``).
        """
        trade_date = _validate_trade_date(trade_date)
        return self.propagator.create_initial_state(
            company_name,
            trade_date,
            asset_type=asset_type,
            instrument_context=self.resolve_instrument_context(company_name, asset_type, trade_date),
            portfolio_context=portfolio.render(company_name) if portfolio is not None else "",
        )

    def _memory_step(self, state):
        """The graph's Memory Log step, alongside the analysts (#1428): settle every
        ticker's due decisions (#1445), then return the lessons known by the
        trade date for the Portfolio Manager (#1251).

        Settling fetches prices and asks the model for a reflection per decision,
        so it runs beside the analysts instead of before them. A failure here
        does not end the run: the analysts' work is kept, the lessons already in
        the log are used, and the report says what could not be settled.
        """
        note = ""
        try:
            # Another run settling the same log does the work; this one goes on.
            done = self.settle_all_pending(wait=False)
            if done.failed:
                note = (f"{len(done.failed)} past decision(s) could not be settled this run "
                        "and stay pending.")
        except Exception as exc:
            logger.warning("Settling past decisions failed: %s", exc)
            note = f"Past decisions could not be settled this run ({type(exc).__name__}); they stay pending."
        try:
            past_context = self.memory_log.get_past_context(
                state["company_of_interest"], as_of=self._memory_as_of(state["trade_date"]))
        except Exception as exc:
            logger.warning("Reading the memory log failed: %s", exc)
            past_context = ""
            note = note or f"The memory log could not be read this run ({type(exc).__name__})."
        return {"past_context": past_context, "memory_note": note}

    def settle_pending(self, company_name) -> settlement.Settlement:
        """Settle this ticker's decisions whose holding window has now traded.

        A run settles every due decision alongside its analysts, so its own
        decision stays pending until a later run. A caller that is done
        analyzing a ticker (a backtest sweep, a scheduled job) calls this to
        settle it now. Returns what was settled and what failed.
        """
        with run_config(self.config):
            return settlement.settle_pending(company_name, self.memory_log, self.reflector, self.config)

    def settle_all_pending(self, wait: bool = True) -> settlement.Settlement:
        """Settle every ticker's decisions whose holding window has now traded (#1445).

        For a scheduler whose tickers rotate: a ticker it stops analysing would
        otherwise keep its decisions pending, and their lessons out of later runs.
        With ``wait=False`` a pass already running on the same log is not waited for.
        """
        with run_config(self.config):
            return settlement.settle_all_pending(self.memory_log, self.reflector, self.config, wait=wait)

    def _rating_provenance(self, ticker: str, trade_date: str, final_state: dict) -> Provenance:
        """Build the provenance the rating authority checks before a commit."""
        evidence = final_state.get("evidence") or []
        market_tools = {
            "get_stock_data",
            "get_indicators",
            "get_stock_stats_indicators_window",
        }
        snapshot_verified = any(
            str(ref.get("source", "")).split(":", 1)[0] in market_tools
            for ref in evidence
        )
        snapshot_seed = {
            "ticker": ticker,
            "date": str(trade_date),
            "evidence": [
                ref.get("snapshot_hash")
                for ref in evidence
                if str(ref.get("source", "")).split(":", 1)[0] in market_tools
            ],
        }
        snapshot_id = "snap-" + hashlib.sha256(
            json.dumps(snapshot_seed, sort_keys=True, default=str).encode()
        ).hexdigest()[:32]
        manifest_id = "man-" + hashlib.sha256(
            f"{ticker}|{trade_date}|{self._config_hash()}".encode()
        ).hexdigest()[:32]
        return Provenance(
            snapshot_id=snapshot_id,
            manifest_id=manifest_id,
            model=self.config.get("deep_think_llm")
            or self.config.get("quick_think_llm")
            or "unknown",
            prompt_version=self.config.get("prompt_version") or "v1",
            config_version=self.config.get("config_version") or "v1",
            snapshot_verified=snapshot_verified,
        )

    def record_decision(self, company_name, trade_date, final_state, run_signature: str | None = None):
        """Commit the rating, then write the state log and the memory-log entry.

        The rating authority is the only writer of a committed rating. A run
        without a signature is a legacy/internal call and keeps the old reader.
        """
        decision = final_state.get("final_trade_decision")
        candidate_rating = run_rating(final_state)
        validation = validate_output(
            {
                "final_trade_decision": decision or "",
                "final_rating": candidate_rating,
            },
            {
                "type": "object",
                "required": ["final_trade_decision", "final_rating"],
                "properties": {
                    "final_trade_decision": {"type": "string"},
                    "final_rating": {
                        "type": "string",
                        "enum": sorted(ALLOWED_RATINGS),
                    },
                },
            },
        )
        final_state["output_validation"] = {
            "ok": validation.ok and bool((decision or "").strip()),
            "errors": validation.errors
            if validation.ok
            else validation.errors + ([] if (decision or "").strip() else ["empty decision"]),
        }
        if not final_state["output_validation"]["ok"]:
            final_state["final_rating"] = "REVIEW"

        if decision and run_signature and final_state.get("evidence"):
            provenance = self._rating_provenance(company_name, trade_date, final_state)
            result = commit_rating(
                decision,
                provenance,
                self.rating_store,
                decision_id=record_id(company_name, str(trade_date), run_signature),
            )
            final_state["final_rating"] = result.rating
            final_state["rating_authority"] = {
                "rating": result.rating,
                "review_required": result.review_required,
                "reason_codes": list(result.reason_codes),
                "decision_id": result.decision_id,
            }

        self._log_state(trade_date, final_state)
        if not decision:
            logger.warning("No final decision for %s on %s; nothing added to the memory log",
                           company_name, trade_date)
            return
        self.memory_log.store_decision(
            ticker=company_name, trade_date=trade_date, final_trade_decision=decision,
            rating=run_rating(final_state), run_signature=run_signature,
        )

    def _run_graph(self, company_name, trade_date, asset_type: str = "stock",
                   checkpoint_thread_id: str | None = None, portfolio=None):
        """Execute the graph and write the resulting state to disk and memory log."""
        init_agent_state = self.create_run_state(company_name, trade_date, asset_type, portfolio)
        args = self.propagator.get_graph_args()

        # Inject the checkpoint thread_id (from checkpoint_scope) so the same
        # ticker+date+graph-shape resumes; a different one starts fresh (#1089).
        if checkpoint_thread_id is not None:
            args.setdefault("config", {}).setdefault("configurable", {})["thread_id"] = checkpoint_thread_id

        # None resumes an existing checkpoint; init_agent_state starts fresh (#1249).
        graph_input = self.checkpoint_input(init_agent_state)
        fallback_events = []
        registry = None
        with fallback_event_scope(fallback_events):
            if self.debug:
                # A state repeats the messages before it, so each prints once (#1027).
                final_state, printed = {}, set()
                for messages, state in self.stream_run(graph_input, **args):
                    for msg in messages:
                        key = getattr(msg, "id", None) or (type(msg).__name__, getattr(msg, "content", None))
                        if key not in printed:
                            printed.add(key)
                            msg.pretty_print()
                    if state is not None:
                        final_state.update(state)
                registry = self.last_evidence_registry
            else:
                with evidence_scope() as registry:
                    final_state = self.graph.invoke(graph_input, **args)
                self.last_evidence_registry = registry
        final_state["fallback_events"] = [event.model_dump(mode="json") for event in fallback_events]
        final_state["evidence_refs"] = registry.ids() if registry is not None else []
        final_state["evidence"] = (
            [ref.model_dump(mode="json") for ref in registry.all()]
            if registry is not None
            else []
        )
        final_state["security_events"] = [
            json.dumps(event, sort_keys=True, ensure_ascii=False)
            for event in drain_events()
        ]

        self.record_decision(
            company_name,
            trade_date,
            final_state,
            run_signature=self.run_signature(asset_type, portfolio),
        )

        # Clear checkpoint on successful completion to avoid stale state.
        self.clear_checkpoint_on_success(company_name, trade_date, asset_type, portfolio)

        return final_state, run_rating(final_state)

    def stream_run(self, graph_input, **args):
        """Stream a run as ``(messages, state)`` pairs.

        ``messages`` are the agents' messages, the analysts' included. ``state``
        is the run's state after a top-level step; for a step inside an analyst's
        graph it is that analyst's report once filed, else None.

        Each analyst works in a graph of its own, and the run's state takes the
        analysts' reports only when the slowest has finished, so their messages
        and reports come from their own finished steps ("tasks") as they happen.
        """
        args = {**args, "stream_mode": ["values", "tasks"]}
        # The graph's own config serves every tool call, as in propagate(), even
        # when the process-wide config has changed since. Each step runs in the
        # run's context, so the caller keeps its own between steps.
        context = run_config_context(self.config)
        stream = context.run(self.graph.stream, graph_input, subgraphs=True, **args)
        with evidence_scope() as registry:
            try:
                while (step := context.run(next, stream, None)) is not None:
                    namespace, mode, chunk = step
                    if namespace:
                        result = chunk.get("result") if mode == "tasks" else None
                        if isinstance(result, dict):
                            report = {k: v for k, v in result.items() if k != "messages" and v}
                            if result.get("messages") or report:
                                yield result.get("messages", []), report or None
                    elif mode == "values":
                        yield chunk.get("messages", []), chunk
            finally:
                context.run(stream.close)
                self.last_evidence_registry = registry

    def _debate_transcript(self, ticker, trade_date, final_state):
        """Export the structured debate, resolving any available evidence refs."""
        debate = final_state.get("investment_debate_state") or {}
        turns = debate.get("turns") or []
        if not turns:
            return None
        payload = {
            "transcript_id": f"{ticker}-{trade_date}",
            "turns": turns,
            "quality_available": bool(debate.get("quality_available", True)),
        }
        try:
            return resolve_evidence_refs(payload, self.last_evidence_registry)
        except Exception as exc:  # never lose a completed run to transcript export
            logger.warning("Could not export debate transcript: %s", exc)
            return None

    def _log_state(self, trade_date, final_state):
        """Write a run's final state to JSON under the run's own ticker."""
        entry = {
            "company_of_interest": final_state["company_of_interest"],
            "trade_date": final_state["trade_date"],
            "market_report": final_state["market_report"],
            "sentiment_report": final_state["sentiment_report"],
            "news_report": final_state["news_report"],
            "fundamentals_report": final_state["fundamentals_report"],
            "investment_debate_state": {
                "bull_history": final_state["investment_debate_state"]["bull_history"],
                "bear_history": final_state["investment_debate_state"]["bear_history"],
                "history": final_state["investment_debate_state"]["history"],
                "current_response": final_state["investment_debate_state"][
                    "current_response"
                ],
            },
            "trader_investment_plan": final_state["trader_investment_plan"],
            "risk_debate_state": {
                "aggressive_history": final_state["risk_debate_state"]["aggressive_history"],
                "conservative_history": final_state["risk_debate_state"]["conservative_history"],
                "neutral_history": final_state["risk_debate_state"]["neutral_history"],
                "history": final_state["risk_debate_state"]["history"],
            },
            "investment_plan": final_state["investment_plan"],
            "final_trade_decision": final_state["final_trade_decision"],
            "final_rating": run_rating(final_state),
            "run_settings": self.run_settings(),
            "fallback_events": final_state.get("fallback_events", []),
        }

        # A ticker that would escape the results directory is rejected.
        safe_ticker = safe_ticker_component(final_state["company_of_interest"])
        directory = Path(self.config["results_dir"]) / safe_ticker / "TradingAgentsStrategy_logs"
        directory.mkdir(parents=True, exist_ok=True)
        transcript = self._debate_transcript(safe_ticker, trade_date, final_state)
        if transcript:
            entry["debate_transcript"] = transcript
            final_state["debate_transcript"] = transcript
            (directory / "debate_transcript.json").write_text(
                json.dumps(transcript, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        log_path = directory / f"full_states_log_{trade_date}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            # Reports can be in any language and this file is read by a person.
            json.dump(entry, f, indent=4, ensure_ascii=False)

        rating = run_rating(final_state)
        config_hash = self._config_hash()
        manifest = RunManifest(
            run_id=f"{safe_ticker}-{trade_date}",
            ticker=safe_ticker,
            date=str(trade_date),
            profile=self.config.get("run_profile", "custom"),
            analysts=list(self.selected_analysts),
            models={
                "quick": self.config.get("quick_think_llm", ""),
                "deep": self.config.get("deep_think_llm", ""),
            },
            provider=self.config.get("llm_provider", ""),
            prompt_version=self.config.get("prompt_version", ""),
            config_hash=config_hash,
            cache_hits=max(
                int(final_state.get("cache_hits", 0) or 0),
                sum(
                    1
                    for ref in (final_state.get("evidence") or [])
                    if str(ref.get("source", "")).endswith(":cache")
                ),
            ),
            token_usage_by_agent=dict(final_state.get("token_usage_by_agent", {}) or {}),
            cost_estimate=final_state.get("cost_estimate"),
            security_events=list(final_state.get("security_events", []) or []),
            rating=rating,
            timestamps={"finished": datetime.now(UTC).isoformat()},
            status="review" if is_review(rating) else "completed",
            fallback_events=[],
        )
        manifest.add_fallback_events(final_state.get("fallback_events", []))
        write_run_manifest(directory / "manifests", manifest)
