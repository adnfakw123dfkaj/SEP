# Part 2 实现计划书 — 结构化辩论

## 1. 基本信息

| 项 | 内容 |
|---|---|
| 负责组员 | 组员 B（待确认） |
| 覆盖需求 | `REQ-FR-003`（Must）、`REQ-QUAL-001`（Must） |
| 核心目标 | 把自由文本多空辩论升级为可校验、可早停、可机器评估的结构化辩论 |
| 提供接口 | `DebateTurn`、`run_debate_turn()`、`should_stop()`、`export_transcript()`、`score_debate()` |
| 依赖接口 | `sanitize(text)`（Part 5，可先 stub）、`EvidenceRef`（Part 3，可先用字符串）、`ProfileConfig`（Part 1） |
| 不负责 | 评级、manifest 写入、缓存、成本路由、报告渲染；只产出辩论数据和指标 |

## 2. 目标与非目标

### 目标

- 每轮辩论都有统一字段：`claim`、`stance`、`evidence_refs`、`assumptions`、`rebuttal_to`、`confidence`、`open_questions`、`requested_evidence`、`round`。
- 格式失败可重试一次；仍失败则标记 `invalid`，由 manager 总结，不阻塞整次运行。
- 支持收敛早停：连续一轮没有新证据且立场不变时停止。
- 用确定性代理指标验收“辩论更有效/不随意”。

### 非目标

- 不做人工盲评/语义说服力评分（已在最终需求中舍弃）。
- 不改变评级权威、最终交易决策或风险辩论的既有语义。
- 不实现新的 LLM provider；沿用现有适配器。

## 3. 交付物

- 代码：
  - `tradingagents/contracts/debate.py`：`DebateTurn`、`Stance`、`DebateTranscript`。
  - `tradingagents/agents/debate/schemas.py`、`prompts.py`、`validator.py`、`convergence.py`、`quality.py`、`export.py`。
  - `tradingagents/agents/researchers/bull_researcher.py`、`bear_researcher.py`：改为调用 debate adapter，保留原有角色语义。
  - `graph/conditional_logic.py`：调用 `convergence.should_stop()`。
- 测试：
  - `tests/contracts/test_debate_contract.py`
  - `tests/req/test_debate_protocol.py`
  - `tests/req/test_debate_quality.py`
  - `tests/fixtures/debate/*.json`（golden cases）
- 文档/证据：
  - 辩论 transcript 示例（JSON + Markdown）。
  - 质量指标报告。
  - 格式失败/重试/降级样例。

## 4. 辩论契约（第 1 周冻结）

```text
DebateTurn:
  turn_id: str
  round: int
  speaker: "bull" | "bear"
  claim: str
  stance: "bullish" | "bearish" | "neutral"
  evidence_refs: list[EvidenceRef | str]
  assumptions: list[str]
  rebuttal_to: str | null
  confidence: float  # 0..1
  open_questions: list[str]
  requested_evidence: list[str]
```

约束：

- `round` 单调递增；`speaker` 与轮次交替。
- `rebuttal_to` 必须指向同一 transcript 中已存在的 `turn_id`。
- 每轮至少一个 `evidence_refs`，或显式 `no_new_evidence: true`。
- `confidence` 超出 0–1 视为无效。

## 5. 工作分解

### Week 1：契约与提示草稿

- 定义 `DebateTurn`、`DebateTranscript`，写契约测试。
- 起草 bull/bear 提示模板：要求 JSON、字段说明、证据引用格式。
- 用 stub `sanitize()` 和字符串 evidence refs 跑通一个固定示例。
- 准备 5 个 golden cases：正常、缺字段、引用不存在、重复主张、收敛/不收敛。
- 交付：契约 + 提示草稿 + golden fixtures。

### Week 2：结构化轮次与校验

- 实现 `validator.py`：字段、枚举、round、rebuttal_to、引用格式。
- 实现 `run_debate_turn()`：调用模型、解析 JSON、失败重试一次。
- 实现 `convergence.py`：无新证据 + 立场不变 -> 早停。
- 修改 bull/bear researcher 为 adapter 调用。
- 接入 `graph/conditional_logic.py`；最大轮数兜底。
- 交付：30 次运行中 schema 100% 通过。

### Week 3：质量代理指标

- 实现 `quality.py`：证据覆盖、反驳覆盖、无证据断言率、重复主张率。
- 实现对 30 份 transcript 的批量检查；输出报告。
- 与 Part 3 对齐 `EvidenceRef` 真实对象（先用字符串也可）。
- 做 golden case 回归；修正提示词以减少缺字段。
- 交付：质量指标报告 + golden 回归通过。

### Week 4：调优与收尾

- 降低格式失败率；记录失败样例与重试策略。
- 跑 `REQ-FR-003`、`REQ-QUAL-001` 全部验收命令。
- 补文档：如何新增辩论字段、如何调整收敛阈值。
- 准备演示：同一 ticker 的结构化 vs 自由文本对比。
- 交付：验收报告 + 演示脚本。

## 6. 验收与测试

| 需求 | 验收命令 | 证据 |
|---|---|---|
| `REQ-FR-003` | `pytest tests/req/test_debate_protocol.py::test_schema_valid --runs 30` | 30 份 transcript |
| `REQ-FR-003` | `pytest tests/req/test_debate_protocol.py::test_max_rounds` | 轮数记录 |
| `REQ-FR-003` | `pytest tests/req/test_debate_protocol.py::test_convergence_fixtures` | 早停决策表 |
| `REQ-FR-003` | `pytest tests/req/test_debate_protocol.py::test_export_schema` | JSON schema 报告 |
| `REQ-QUAL-001` | `pytest tests/req/test_debate_quality.py --transcripts 30` | 四项指标报告 |
| `REQ-QUAL-001` | `pytest tests/req/test_debate_quality.py::test_golden_cases` | golden 回归 |

## 7. 风险与回退

| 风险 | 缓解 | 回退 |
|---|---|---|
| 模型不遵守 JSON | 结构化输出 + 一次重试 + 明确字段示例 | 标记 `invalid`，manager 自由文本总结；QUAL-001 标记不可用 |
| 结构化输出增加 token | 限制每轮字数；只保留必要字段；早停 | 减少最大轮数；Quick 只用 1 轮 |
| 与研究员现有提示冲突 | 用 adapter 包住，不重写角色语义 | 保留旧提示，新增 `debate_protocol` feature flag |
| 重复主张检测误判 | golden fixtures 校准阈值；报告保留原文 | 阈值可调，但需记录变更 |
| 收敛过早导致辩论不足 | 至少 1 轮；只在无新证据且立场不变时停 | 关闭早停，只保留最大轮数 |

## 8. Definition of Done

- 30 次运行中辩论 turn schema 100% 通过；失败有明确降级。
- 最大轮数和收敛早停按规则执行。
- 四项质量指标达到阈值，golden cases 100% 通过。
- 报告/transcript 可导出 JSON，Part 3 可直接消费。
- OpenCode 会话记录、测试输出、示例 transcript 已归档。

## 9. 集成交接清单

- [ ] `DebateTurn` / `DebateTranscript` 契约冻结。
- [ ] 提供 `run_debate_turn(state, speaker) -> DebateTurn`。
- [ ] 提供 `should_stop(transcript, max_rounds) -> bool`。
- [ ] 提供 `export_transcript(transcript) -> dict`。
- [ ] 提供 `score_debate(transcript) -> QualityMetrics`。
- [ ] 在 `tests/contracts/` 增加辩论契约测试。
- [ ] 告知 Part 3：transcript 中 evidence_refs 的字符串格式。
