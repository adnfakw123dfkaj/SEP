# TradingAgents 增强需求文档（最终实施版）

| 项目 | 内容 |
|---|---|
| 版本 | v1.0（Final Draft，待组内确认） |
| 日期 | 2026-11-16 |
| 状态 | 六人分工版；已按“完成项目优先”裁剪 |
| 适用范围 | `adnfakw123dfkaj/SEP` 仓库中的 `tradingagents/` 子项目 |
| 机器可读版本 | `docs/req/requirements.yaml`（超集/备份；本文件是本期实施基线） |
| 语言约定 | 正文中文；需求 ID、类型名、代码符号保留英文 |

> **先说明取舍**：本文件不是“把所有能想到的需求都做一遍”，而是六人小组在课程周期内**能完成、能验收、能并行开发**的最终需求集。共保留 **14 条需求**，分为 **6 个高度解耦的部分**。不符合“可机器验收 + 可行实现 + 本期必要”三项的，全部进入第 5 节舍弃清单。

---

## 0. 当前基线与为什么做这些需求

### 0.1 实测基线

| 运行 | 分析师 | 耗时 | 结果 |
|---|---|---:|---|
| NVDA / 2026-11-10 | market | 约 425 秒（7.1 分钟） | Sell |
| NVDA / 2026-11-14 | market + social | 约 550 秒（9.2 分钟） | Underweight |

实测还发现：

- Reddit 返回 `HTTP 403`；情感分析只能以低置信度输出。
- StockTwits 可用，Yahoo 新闻可用。
- 运行产物**不汇总 token 和费用**，无法回答“单次分析烧了多少 token”。
- 多空辩论是自由文本，没有统一字段、证据引用和收敛规则，难以评估。
- 默认四分析师全跑、工具轮次上限高，导致慢且 token 不可控。

### 0.2 本期目标

1. **能完成**：优先保证一个可演示、可测试、可解释的最小闭环。
2. **能验收**：每条需求都有 metric + threshold + verification。
3. **能并行**：六个部分文件所有权清晰，接口先冻结，减少互相等待。
4. **能说明**：报告有证据、运行有清单、成本/延迟可测量。

### 0.3 明确不做（Won't）

自动交易、真实下单、模型微调/强化学习、全市场覆盖、全量人工复核、复杂 Web 前端、完整 MCP 工具平面、哈希链审计、生产级告警系统。这些不是“以后再说”的模糊项，而是本期明确不做，避免范围蔓延。

---

## 1. 需求工程方法与格式

### 1.1 奥斯本头脑风暴

- **发散阶段**：不批评、追求数量、允许组合，记录速度/成本/辩论/证据/韧性/安全/治理等想法。
- **收敛阶段**：按“痛点影响、实现可行性、机器可验收性、架构显著性、风险”筛选。
- **本期原则**：完成项目优先，不为高分引入高复杂度组件。

### 1.2 需求类型与 ID

| 类型 | ID 前缀 | 判定 |
|---|---|---|
| 功能行为 | `REQ-FR-*` | 系统做什么 |
| 不变量 | `REQ-INV-*` | 零容忍、确定性代码强制、0 escapes |
| 质量属性 | `REQ-QUAL-*` | 可测量的输出质量，必须 metric + threshold |
| 性能 | `REQ-PER-*` | 延迟、吞吐、资源 |
| 成本 | `REQ-COST-*` | token、费用、算力预算 |
| 治理 | `REQ-GOV-*` | 谁决定/记录/审计/保留 |
| 安全 | `REQ-SEC-*` | 注入、访问、机密性、完整性 |

本期没有单独的 `ARCH-EA-*` 条目：架构约束要么是既有实现（作为回归测试保留），要么已并入功能/安全需求，避免为“架构”而架构。

### 1.3 MoSCoW

| 优先级 | 定义 |
|---|---|
| **Must** | 本期必须完成；缺失则项目不能验收 |
| **Should** | 重要；时间不足时按顺序裁剪，并记录原因 |
| **Could** | 本期不做，或仅在 Must/Should 全部完成后考虑 |
| **Won't** | 明确不做；见第 5 节 |

### 1.4 Fit criterion 格式

每条需求至少包含：

- `metric`：可计算的指标名；
- `threshold`：数值阈值或布尔断言；
- `verification`：可执行命令/脚本；退出码 0 且报告达标才算通过。

功能/不变量允许布尔型或 rate 型断言；非功能必须给出 metric + threshold + verification。

---

## 2. 最终需求总览

| ID | 类型 | MoSCoW | 摘要 | Part |
|---|---|---|---|---|
| `REQ-FR-001` | 功能 | Must | Quick/Standard/Deep 三档运行模式 | 1 |
| `REQ-FR-002` | 功能 | Should | 预检 ticker/数据可用性，失败快速退出 | 1 |
| `REQ-FR-003` | 功能 | Must | 结构化辩论协议与收敛早停 | 2 |
| `REQ-QUAL-001` | 质量 | Must | 辩论质量代理指标 | 2 |
| `REQ-FR-004` | 功能 | Must | 证据链报告与运行清单 | 3 |
| `REQ-QUAL-002` | 质量 | Should | 报告数字忠实度与引用支持 | 3 |
| `REQ-INV-001` | 不变量 | Should | 原子且幂等的决策记录 | 3 |
| `REQ-FR-005` | 功能 | Must | 缓存、检查点与降级 | 4 |
| `REQ-INV-002` | 不变量 | Should | 时点完整性（无前视） | 4 |
| `REQ-INV-003` | 不变量 | Must | 确定性评级权威 | 5 |
| `REQ-SEC-001` | 安全 | Must | 不可信输入/输出安全 | 5 |
| `REQ-INV-004` | 不变量 | Must | 密钥不泄露 | 5 |
| `REQ-PER-001` | 性能 | Must | 分档端到端延迟 | 6 |
| `REQ-COST-001` | 成本 | Must | 分档 token 预算与成本报告 | 6 |

统计：Must 10，Should 4，Could 0，Won't 见第 5 节。

### 2.1 实现状态（按当前代码对齐）

下表按仓库当前代码的实际状态标注（模块是否存在、是否接入运行路径、离线验收测试是否通过）。离线验收：`pytest tests/req tests/security -m "not integration"` 全部通过（139 passed）。

| 需求 | 实现状态 | 说明 |
|---|---|---|
| `REQ-FR-001` | implemented | `profiles.py`、`preflight.py`；档位与预检已接入组合根/CLI |
| `REQ-FR-002` | implemented | 预检在构图前执行，失败快速退出 |
| `REQ-FR-003` | implemented | `agents/debate/`，结构化辩论已接入研究者适配层 |
| `REQ-QUAL-001` | implemented | `agents/debate/quality.py`，质量指标参与质量门禁 |
| `REQ-FR-004` | implemented | `evidence/` + `contracts/{evidence,manifest}.py`；manifest 与 claim 级证据写入报告树 |
| `REQ-QUAL-002` | implemented | `evidence/fidelity.py`，经 `cost/quality_floor` 在运行中评估 |
| `REQ-INV-001` | implemented | `records/`，`IdempotentStore` 接入 `record_decision`，原子写 |
| `REQ-FR-005` | implemented | `cache/` 已接入 `dataflows/router`，checkpoint/resume 与 fallback 事件接入图 |
| `REQ-INV-002` | implemented | `dataflows/date_window.py` 覆盖各带日期 vendor 与记忆 as-of |
| `REQ-INV-003` | implemented | `rating_authority.commit_rating` 接入组合根提交门 |
| `REQ-SEC-001` | implemented | `security/`（sanitize、validate、tool_guard），工具按角色白名单 |
| `REQ-INV-004` | implemented | `security/redaction` + `net.get_scrubbed`，密钥脱敏 |
| `REQ-PER-001` | implemented | 延迟基准工具 `scripts/bench_latency.py`（测量工具，不改运行路径） |
| `REQ-COST-001` | partial | 已在运行路径接线：调用前硬预算拦截、按档位裁剪输入、按 agent 记账与成本报告；未接线：`cost/router.py` 的摘要/便宜模型/审批渐进路由与质量门禁回滚（已实现且有单测，仅 `cost/runner.py` 与 `token_audit.py` 使用）。运行时超预算为**硬停为 REVIEW**，非渐进降级 |

---

## 3. 六人分工与解耦设计

### 3.1 六个部分

| Part | 建议负责人 | 需求 | 主要职责 | 主要目录/文件 |
|---|---|---|---|---|
| **Part 1** | 组员 A | `REQ-FR-001`、`REQ-FR-002` | 配置、档位、CLI、预检、组合根（integration owner） | `contracts/profile.py`、`profiles.py`、`preflight.py`、`default_config.py`、`cli/` |
| **Part 2** | 组员 B | `REQ-FR-003`、`REQ-QUAL-001` | 辩论 Schema、提示模板、校验、收敛、质量代理 | `contracts/debate.py`、`agents/debate/`、`agents/researchers/` 适配层 |
| **Part 3** | 组员 C | `REQ-FR-004`、`REQ-QUAL-002`、`REQ-INV-001` | 证据引用、manifest、报告、记录原子性/幂等 | `contracts/manifest.py`、`contracts/evidence.py`、`evidence/`、`records/`、`reporting.py` |
| **Part 4** | 组员 D | `REQ-FR-005`、`REQ-INV-002` | 缓存、checkpoint/resume、降级、时点完整性 | `contracts/cache.py`、`cache/`、`resilience.py`、`graph/checkpointer.py`、`dataflows/date_window.py` |
| **Part 5** | 组员 E | `REQ-INV-003`、`REQ-SEC-001`、`REQ-INV-004` | 评级权威、输入/输出安全、密钥脱敏 | `contracts/rating.py`、`agents/rating.py`、`security/`、`llm_clients/api_key_env.py` |
| **Part 6** | 组员 F | `REQ-PER-001`、`REQ-COST-001` | 延迟基准、token 估算/预算/路由/成本报告 | `contracts/llm_event.py`、`cost/`、`scripts/bench_latency.py`、`scripts/token_audit.py` |

> 负责人先按 A–F 占位，组内可调整；**契约所有权不随人员调整而改变**。

### 3.2 先冻结的共享契约

第 1 周由各 owner 提交，组内评审后冻结。每个契约一个文件，避免多人编辑同一文件。

| 契约 | Owner | 关键字段 |
|---|---|---|
| `ProfileConfig` | Part 1 | name、analysts、debate_rounds、risk_rounds、max_tool_rounds、quick_model、deep_model、token_budget、timeout_s、cache_ttl |
| `PreflightResult` | Part 1 | ticker、resolved、tradable、data_available、reason、checked_at |
| `DebateTurn` | Part 2 | claim、stance、evidence_refs、assumptions、rebuttal_to、confidence、open_questions、requested_evidence、round |
| `RunManifest` | Part 3 | run_id、ticker、date、profile、analysts、models、provider、prompt_version、config_hash、vendor_versions、cache_hits、token_usage_by_agent、cost_estimate、fallback_events、security_events、rating、timestamps、status |
| `EvidenceRef` | Part 3 | kind、id、source、snapshot_hash、retrieved_at |
| `CacheKey` / TTL | Part 4 | key、data_class、as_of、ttl_seconds、provenance |
| `RatingResult` | Part 5 | rating、reason_codes、provenance、review_required |
| `LLMCallEvent` | Part 6 | call_id、provider、model、prompt_tokens、completion_tokens、latency_ms、status、retry_count、timestamp |

### 3.3 文件所有权规则

- 每个 Part 只编辑自己拥有的目录；**不直接改别人的文件**。
- 需要别人的字段时，通过契约对象传入，不复制内部逻辑。
- `graph/setup.py`、`graph/trading_graph.py` 是组合根，由 **Part 1** 统一修改；其他 Part 提供 adapter/feature flag，PR 需相关 owner 评审。
- 契约变更必须：PR + owner 批准 + 更新契约测试。
- 每个 Part 提供 **stub/fake**，保证别人不等待：例如 Part 5 先提供 `sanitize(text) -> str` 的空实现，Part 6 先提供 `estimate_tokens(text) -> int` 的近似实现。

### 3.4 依赖矩阵（为什么能并行）

| Part | 可立即开始 | 依赖的契约 | 依赖处理 |
|---|---|---|---|
| Part 1 | 是 | 自己的 `ProfileConfig`/`PreflightResult` | 先定义并冻结 |
| Part 2 | 是 | `DebateTurn`、`EvidenceRef`、`sanitize()` | 用字符串 ref 和 stub sanitize |
| Part 3 | 是 | `RunManifest`、`EvidenceRef`、`RatingResult`、`LLMCallEvent` | 用 stub rating/llm event |
| Part 4 | 是 | `ProfileConfig`、`CacheKey`、`RunManifest` | 用默认 profile 和 stub manifest |
| Part 5 | 是 | `RatingResult`、`RunManifest` | 用 stub manifest |
| Part 6 | 是 | `ProfileConfig`、`LLMCallEvent`、`RunManifest` | 用默认 profile 和 stub manifest |

**结论**：第 1 周冻结契约后，六个 Part 可以同时开工；第 3–4 周只做集成，不互相等实现。

### 3.5 每周节奏

- 周一：15 分钟契约/接口同步；确认本周不跨文件修改。
- 周三：各自跑自己的验收脚本；失败不阻塞别人，记录到 issue。
- 周五：Part 1 合并集成分支；跑全量测试 + 最小演示。
- 每次合并必须附：测试输出、验收指标、OpenCode 会话摘要（用于课程证据）。

---

## 4. 详细需求

> 每条需求包含：类型/优先级/负责 Part、陈述、为什么需要、实现方案、验收标准、取舍、依赖与风险。

---

### Part 1 — 配置、档位与输入闸门

#### `REQ-FR-001` 运行档位与默认值缩减

- **类型**：Functional
- **优先级**：Must
- **负责 Part**：1
- **陈述**：系统应提供 Quick、Standard、Deep 三种运行档位。每个档位固定分析师集合、辩论轮数、风控轮数、最大工具轮数、模型分层、token 预算、超时和缓存 TTL。用户可用 `--profile` 覆盖，但运行清单必须记录档位和所有覆盖项。
- **为什么需要**：当前默认四分析师全跑、工具轮次上限高；实测 1 个分析师约 7 分钟、2 个约 9 分钟，4 个更慢。档位化让“快/标准/深”变成可测试的配置矩阵，是延迟和成本目标的前提。
- **实现方案**：
  - 新增 `tradingagents/profiles.py`：`ProfileConfig` dataclass + 三套预设。
  - `default_config.py` 读取 `run_profile`，保留 `TRADINGAGENTS_*` 覆盖。
  - `cli/main.py` 增加 `--profile`，交互式 CLI 提供默认档位。
  - `graph/setup.py`、`graph/analyst_execution.py` 按 profile 选择分析师和轮数。
  - 非法覆盖（如 Quick 选 4 个分析师）启动前拒绝。
  - `RunManifest` 写入 profile 与覆盖项。
- **验收标准**：
  - `profile_matrix_match_rate == 1.0`；`pytest tests/req/test_profiles.py::test_profile_matrix`
  - `manifest_profile_coverage == 1.0`；`pytest tests/req/test_profiles.py::test_manifest_profile`
  - `invalid_profile_override_rejection_rate == 1.0`；`pytest tests/req/test_profiles.py::test_invalid_override`
  - 三个档位的分析师集合/轮数与文档一致，测试 100% 通过。
- **取舍**：Quick 减少分析师和工具轮次，换来速度和成本，但降低覆盖面；报告必须标注“未运行”的分析师并下调置信度。Standard/Deep 覆盖更全，但延迟和 token 更高。
- **依赖与风险**：依赖 Part 3 的 `RunManifest` 契约、Part 6 的 token 预算。风险是默认值需要基线校准；第 1 周先用本文件目标值，基准后再微调。

#### `REQ-FR-002` 预检 ticker 与数据可用性

- **类型**：Functional
- **优先级**：Should
- **负责 Part**：1
- **陈述**：在代理图运行前，系统应校验 ticker 能解析为真实工具，且核心价格数据在分析日期附近可取得；失败时返回明确错误并停止，不启动分析师，不消耗 LLM token。
- **为什么需要**：无效或无数 ticker 会浪费分析师和辩论的 token；其他小组的分析也把“输入范围/工具有效性”列为缺口。预检成本低、收益直接。
- **实现方案**：
  - 新增 `tradingagents/preflight.py`：`validate_request(ticker, trade_date, profile) -> PreflightResult`。
  - 复用现有 `dataflows/symbols.py` 和 `resolve_instrument_identity`；用短窗口价格查询判断数据可用性。
  - CLI 在构建图之前调用；失败时输出 `invalid ticker` / `no data` 两种明确结果。
  - 结果缓存 7 天（身份）/ 15 分钟（价格可用性）。
- **验收标准**：
  - 对无效/无数据符号，分析师节点调用次数 `== 0`；`pytest tests/req/test_preflight.py::test_no_analyst_calls`
  - 50 个有效 ticker 预检通过率 `== 1.0`；`pytest tests/req/test_preflight.py::test_valid_tickers`
  - 预检失败时 LLM token 消耗 `== 0`；`pytest tests/req/test_preflight.py::test_zero_llm_tokens`
  - 预检 p95（缓存命中）`<= 2s`；`python scripts/bench_preflight.py --assert-p95 2`
- **取舍**：预检可能拒绝真实但交投清淡或供应商暂时不可用的工具；用“invalid”与“data unavailable”区分，并允许第二次供应商回退。
- **依赖与风险**：依赖 Part 1 自己的 `PreflightResult`；Part 3 manifest 记录结果。风险是供应商抖动导致误判；失败时提示重试而非永久拒绝。

---

### Part 2 — 结构化辩论

#### `REQ-FR-003` 结构化辩论协议与收敛早停

- **类型**：Functional
- **优先级**：Must
- **负责 Part**：2
- **陈述**：研究辩论的每一轮应使用结构化记录，至少包含 `claim`、`stance`、`evidence_refs`、`assumptions`、`rebuttal_to`、`confidence`、`open_questions`、`requested_evidence`、`round`。系统应校验字段；缺失/无效时重试一次，仍失败则标记 `invalid` 并降级到主持人总结。辩论在达到最大轮数或满足收敛条件时停止。
- **为什么需要**：当前多空辩论是自由文本，缺少统一字段和证据引用，难以比较、评估和审计。项目 brief 明确点出“讨论相当随意”，这是本期最核心的增强之一。
- **实现方案**：
  - 新增 `tradingagents/agents/debate/`：`schemas.py`（`DebateTurn`）、`prompts.py`、`validator.py`、`convergence.py`。
  - 修改 `bull_researcher.py` / `bear_researcher.py`，只调用 debate 适配层，不在原文件里堆逻辑。
  - `graph/conditional_logic.py` 调用 `convergence.should_stop()`。
  - 每轮保存结构化 turn，并导出 JSON transcript。
  - 格式失败重试一次；仍失败则由 manager 用现有自由文本总结，并标记质量指标不可用。
- **验收标准**：
  - `debate_turn_schema_valid_rate == 1.0`（30 次运行）；`pytest tests/req/test_debate_protocol.py::test_schema_valid --runs 30`
  - `max_rounds_enforced_rate == 1.0`；`pytest tests/req/test_debate_protocol.py::test_max_rounds`
  - `early_stop_decision_correct_rate == 1.0`（固定 fixtures）；`pytest tests/req/test_debate_protocol.py::test_convergence_fixtures`
  - `transcript_export_schema_valid_rate == 1.0`；`pytest tests/req/test_debate_protocol.py::test_export_schema`
- **取舍**：结构化输出提高可评估性，但增加输出 token，并可能限制模型自由推理；用一次重试和主持人总结兜底。若格式失败率过高，回退自由文本，但不假装 QUAL-001 已通过。
- **依赖与风险**：依赖 Part 5 的 `sanitize()`（可先 stub）、Part 3 的 `EvidenceRef`（先用字符串）。风险是模型不遵守 JSON；用结构化输出 + 确定性校验 + 降级。

#### `REQ-QUAL-001` 辩论质量代理指标

- **类型**：Quality
- **优先级**：Must
- **负责 Part**：2
- **陈述**：结构化辩论必须满足可机器检查的质量代理指标：每轮至少有一个 `evidence_ref` 或显式 `no_new_evidence`；反驳必须指向有效先前轮次；无证据断言比例 <=5%；重复主张比例 <=10%。
- **为什么需要**：“更有效/不随意”不能直接机器校验。用证据覆盖、反驳覆盖、无证据断言率、重复主张率四个确定性指标，把主观要求变成可验收标准。
- **实现方案**：
  - 新增 `agents/debate/quality.py`：解析 turns、校验引用存在、用规范化文本 + 相似度检测重复主张。
  - 对 golden fixtures 和 30 份真实 transcript 运行。
  - 在报告中输出四个指标，便于人工抽查。
- **验收标准**：
  - `turns_with_evidence_or_no_new_evidence_rate == 1.0`；`pytest tests/req/test_debate_quality.py::test_evidence_coverage --transcripts 30`
  - `rebuttal_coverage >= 0.90`；`pytest tests/req/test_debate_quality.py::test_rebuttal_coverage --transcripts 30`
  - `unsupported_claim_rate <= 0.05`；`pytest tests/req/test_debate_quality.py::test_unsupported_claim_rate --transcripts 30`
  - `duplicate_claim_rate <= 0.10`；`pytest tests/req/test_debate_quality.py::test_duplicate_claim_rate --transcripts 30`
- **取舍**：这些是代理指标，不代表“说服力”或“洞察力”；可能奖励结构化而牺牲创造性。它们是必要非充分条件，本期不引入人工盲评。
- **依赖与风险**：依赖 `REQ-FR-003`。风险是重复检测阈值误判；用 golden fixtures 校准，阈值可调但需记录。

---

### Part 3 — 证据链、报告与记录

#### `REQ-FR-004` 证据链报告与运行清单

- **类型**：Functional
- **优先级**：Must
- **负责 Part**：3
- **陈述**：报告中的每个实质性事实或数字断言应带 `evidence_ref`。每次运行应生成 `manifest.json`，至少包含 run_id、ticker、date、profile、analysts、models、provider、prompt/config 版本、vendor 版本、cache hits、按 agent 的 token 用量、费用估算、fallback/security 事件、最终评级、时间戳和状态。
- **为什么需要**：当前报告没有“每个断言可追溯”的强制要求，也没有统一运行清单；审计、回放、成本归因和问题定位困难。manifest 也是延迟/成本验收的证据载体。
- **实现方案**：
  - 新增 `tradingagents/contracts/evidence.py`（`EvidenceRef`）和 `contracts/manifest.py`（`RunManifest`）。
  - 新增 `tradingagents/evidence/`：引用注册表、工具调用 ID、快照 hash、news/social ID。
  - 工具调用返回 `call_id` + `snapshot_hash`；报告渲染脚注。
  - `manifest_writer` 在最终节点写出 JSON；Part 1/4/5/6 只填自己的字段。
  - 校验器：数字断言必须有引用；缺失时阻断或标记 unsupported。
- **验收标准**：
  - `numeric_claims_with_evidence_ref_rate == 1.0`；`pytest tests/req/test_evidence_manifest.py::test_numeric_refs --reports 30`
  - `qualitative_claims_with_evidence_ref_rate >= 0.95`；`pytest tests/req/test_evidence_manifest.py::test_qualitative_refs --reports 30`
  - `manifest_schema_valid_rate == 1.0`；`pytest tests/req/test_evidence_manifest.py::test_manifest_schema --runs 30`
  - `manifest_token_sum_relative_error <= 0.05`；`pytest tests/req/test_evidence_manifest.py::test_token_sum`
  - `manifest_replay_success_rate == 1.0`；`pytest tests/req/test_evidence_manifest.py::test_replay`
- **取舍**：引用和 manifest 增加输出 token、渲染时间和存储；用“实质断言”而非“每句话”作为引用单位。manifest 只存结构化元数据，不复制原始数据。
- **依赖与风险**：依赖 Part 5 `RatingResult`、Part 6 `LLMCallEvent`、Part 1 profile。风险是引用粒度过细导致 token 上升；用模板和字段约束控制。

#### `REQ-QUAL-002` 报告数字忠实度与引用支持

- **类型**：Quality
- **优先级**：Should
- **负责 Part**：3
- **陈述**：报告中的数字断言必须与 verified market snapshot 一致；至少 95% 的引用指向真实来源；无证据断言比例 <=5%；报告必须通过结构化 Schema 校验。
- **为什么需要**：LLM 报告可能产生幻觉或数字错误。当前报告有数据一致性说明，但没有系统化、可机器校验的忠实度门槛。
- **实现方案**：
  - 新增 `tradingagents/evidence/fidelity.py`：数字断言抽取器、snapshot 比对器、引用支持检查器、Schema 校验器。
  - 在 CI 中对 30 份报告运行，保存报告和失败样例。
  - 抽取器用 golden fixtures 校准召回率。
- **验收标准**：
  - `numeric_claim_contradiction_rate <= 0.02`；`pytest tests/req/test_report_faithfulness.py::test_numeric --reports 30`
  - `citation_support_rate >= 0.95`；`pytest tests/req/test_report_faithfulness.py::test_citations --reports 30`
  - `unsupported_claim_rate <= 0.05`；`pytest tests/req/test_report_faithfulness.py::test_unsupported --reports 30`
  - `report_schema_valid_rate == 1.0`；`pytest tests/req/test_report_faithfulness.py::test_schema --reports 30`
  - `numeric_claim_detection_recall >= 0.95`；`pytest tests/req/test_report_faithfulness.py::test_extractor_recall`
- **取舍**：自动抽取可能漏检/误判；本期不引入人工盲评作为硬门槛。高影响场景通过降低阈值或人工抽查兜底，但不把人工评审写进验收。
- **依赖与风险**：依赖 `REQ-FR-004`。风险是抽取器召回不足导致“假通过”；用 recall 指标和 golden fixtures 控制。

#### `REQ-INV-001` 原子且幂等的决策记录

- **类型**：Invariant
- **优先级**：Should
- **负责 Part**：3
- **陈述**：决策记录（state JSON + 报告树 + manifest）作为一个原子单元写入；中断的写入要么留下先前的完整记录，要么留下新的完整记录，绝不留下残缺记录。相同 `(ticker, trade_date, run_signature)` 的重跑不得在记忆日志中追加第二条决策条目。
- **为什么需要**：残缺记录是静默数据丢失；重复记录会污染回测和审计。其他小组的分析把 D-04/D-05、幂等性列为缺陷；这是一个中等成本、高价值的 invariant。
- **实现方案**：
  - 新增 `tradingagents/records/`：staging 目录 + 原子 rename + fsync；记录完整集合的 hash。
  - `record_id = hash(ticker, trade_date, run_signature)`；记忆日志 append 前检查幂等键。
  - `run_signature` 包含 profile、模型、分析师集合等会影响结果的设置。
  - 故障注入测试：写入中途 kill 进程。
- **验收标准**：
  - 故障注入 100 次，残缺记录 `== 0`；`pytest tests/req/test_records.py::test_fault_injection`
  - 相同 key 运行 N 次，日志条目 `== 1`；`pytest tests/req/test_records.py::test_idempotent_append`
  - 不同 signature 产生独立版本，且“最新决策”投影唯一；`pytest tests/req/test_records.py::test_signature_versions`
  - 记录完整集合 hash 校验通过率 `== 1.0`；`pytest tests/req/test_records.py::test_record_hash`
- **取舍**：staging + rename 增加 I/O；幂等键过严会抑制合法重跑，因此明确把 `run_signature` 纳入 key，并单独定义“最新决策”投影。
- **依赖与风险**：依赖 `REQ-FR-004` 的 manifest schema。风险是 Windows 目录 rename 语义；用同卷 staging + 原子操作，并测试目标平台。

---

### Part 4 — 数据韧性与时点完整性

#### `REQ-FR-005` 缓存、检查点与降级

- **类型**：Functional
- **优先级**：Must
- **负责 Part**：4
- **陈述**：Standard/Deep 默认启用节点级 checkpoint；中断后从最后成功节点恢复，已完成节点的 LLM 调用不得重复。数据请求按数据类 TTL 缓存并记录 provenance；数据源不可用时优先使用未过期缓存，否则标记 `<unavailable>` 并降低置信度；不得编造数据。LLM 失败时有限重试，仍失败则降级到更便宜模型或返回 `REVIEW`。
- **为什么需要**：长运行失败会浪费时间和 token；重复运行重复抓取相同数据；Reddit/StockTwits 不稳定。缓存和恢复是“慢”和“token-burning”的直接缓解。
- **实现方案**：
  - 新增 `tradingagents/cache/`：TTL 控制器、provenance、按数据类策略。
  - 复用 `graph/checkpointer.py` 和 LangGraph checkpoint。
  - 新增 `tradingagents/resilience.py`：重试 -> 新鲜缓存 -> 标记不可用并降置信度 -> REVIEW。
  - 工具调用按参数 + 数据版本幂等去重。
  - manifest 记录 `fallback_events`。
- **验收标准**：
  - `resume_reuse_rate >= 0.90`；`pytest tests/req/test_checkpoint_resume.py::test_resume`
  - `duplicate_completed_node_llm_calls == 0`；`pytest tests/req/test_checkpoint_resume.py::test_no_duplicate_calls`
  - `cache_hit_rate >= 0.70`（TTL 内重复运行）；`pytest tests/req/test_cache.py::test_hit_rate`
  - `stale_cache_use_count == 0`；`pytest tests/req/test_cache.py::test_no_stale`
  - `fabricated_data_placeholder_count == 0`；`pytest tests/req/test_fallback.py::test_no_fabrication`
  - `typed_fallback_event_coverage == 1.0`；`pytest tests/req/test_fallback.py::test_typed_events`
- **取舍**：checkpoint/缓存增加存储和调试复杂度；TTL 过旧会引入 stale-data 风险。按数据类设 TTL，并在历史运行中禁止使用未来缓存。
- **依赖与风险**：依赖 Part 1 `ProfileConfig`、Part 3 manifest、Part 6 `LLMCallEvent`。风险是缓存与回测日期冲突；用 `as_of` 和 TTL 双重约束。

#### `REQ-INV-002` 时点完整性（无前视）

- **类型**：Invariant
- **优先级**：Should
- **负责 Part**：4
- **陈述**：任何日期晚于分析日期的数据项不得进入任何代理输入。覆盖价格、技术指标、新闻、基本面、内部人、社交和记忆教训。历史窗口内丢弃无日期项；社交来源在历史运行中返回“不可用”而非实时帖子。
- **为什么需要**：前视会让回测和评估失效。系统已有 `date_window` 的部分实现，但需要把它固化为回归不变量，防止新数据源或新路径绕过。
- **实现方案**：
  - 建立数据路径清单；对每个路径加日期过滤/测试。
  - 对社交、新闻、基本面、内部人、记忆分别增加历史窗口测试。
  - 用属性测试/固定 fixtures 注入未来日期数据，断言 prompt 中不出现。
  - manifest 记录每个数据源的 as-of 日期。
- **验收标准**：
  - `future_dated_items_in_prompt == 0`；`pytest tests/req/test_point_in_time.py::test_no_future_items`
  - 所有带日期工具都有对应测试，覆盖率 `== 1.0`；`pytest tests/req/test_point_in_time.py::test_tool_coverage`
  - 历史社交运行返回不可用标记率 `== 1.0`；`pytest tests/req/test_point_in_time.py::test_social_unavailable`
  - 100 个历史日期的属性测试通过率 `== 1.0`；`pytest tests/req/test_point_in_time.py::test_property_dates`
- **取舍**：历史日期下扣留社交/基本面会降低信号和置信度；接受这一点，因为数据泄漏会让评估失真。
- **依赖与风险**：依赖 Part 4 缓存/降级。风险是时区和“分析日期”边界定义不清；统一用 UTC 日期边界，并在测试中固定。

---

### Part 5 — 安全与评级权威

#### `REQ-INV-003` 确定性评级权威

- **类型**：Invariant
- **优先级**：Must
- **负责 Part**：5
- **陈述**：最终提交的评级只能由确定性校验组件产生，且只能是 `{Buy, Overweight, Hold, Underweight, Sell, REVIEW}` 之一。LLM 输出仅为建议。提交前必须存在 verified market snapshot ID、evidence manifest、model/prompt/config 版本；任一缺失则不得提交，状态为 `REVIEW`。持久化评级值也必须落在该允许集合内。
- **为什么需要**：AI 不能是最终权威；自由文本可能覆盖结构化评级；持久化值可能被写坏。这是零容忍不变量。
- **实现方案**：
  - 在 `agents/rating.py` 使用枚举和确定性校验器；`RatingResult` 契约。
  - 在 `graph/trading_graph.py` 增加 commit gate；越界值记录为 `REVIEW`。
  - 校验 snapshot ID、manifest、版本 pin；持久化前再次校验。
  - 模糊/变异测试注入“not a Sell”等对抗文本。
- **验收标准**：
  - `invalid_rating_escapes == 0`（10,000 个变异输出）；`pytest tests/req/test_rating_invariant.py::test_fuzz --cases 10000`
  - `committed_rating_allowed_set_rate == 1.0`；`pytest tests/req/test_rating_invariant.py::test_allowed_set`
  - `commit_with_missing_provenance_count == 0`；`pytest tests/req/test_rating_invariant.py::test_requires_provenance`
  - 对抗文本改变评级次数 `== 0`；`pytest tests/req/test_rating_invariant.py::test_adversarial_text`
- **取舍**：确定性权威降低模型自由度，REVIEW 会增加后续处理；接受，因为不可审计的评级是安全失败。
- **依赖与风险**：依赖 Part 3 manifest、Part 5 自己的 `RatingResult`。风险是“确定性”边界不清；明确 LLM 只建议，commit gate 是唯一写入口。

#### `REQ-SEC-001` 不可信输入/输出安全

- **类型**：Security
- **优先级**：Must
- **负责 Part**：5
- **陈述**：新闻、社交帖子和用户输入在进入 prompt 前必须消毒；模型输出在成为状态前必须通过结构/取值校验；可疑或无效内容被丢弃/记录，不能影响最终评级；不得出现越权工具调用或“角色偏离”。
- **为什么需要**：智能体读取外部文本并调用工具，提示注入可能导致错误评级或越权动作。仅靠 prompt 写“不要听信”不构成防御。
- **实现方案**：
  - 新增 `tradingagents/security/`：`sanitize.py`、`validate_output.py`、`security_log.py`。
  - Sanitizer：控制字符/指令模式清理、定界符包裹、长度上限。
  - Output validator：JSON Schema、枚举、引用检查。
  - 工具调用 guard：只允许当前角色绑定的工具；越权调用拒绝并记录。
  - 可疑内容直接丢弃/记录（本期不做完整隔离队列/复核 UI）。
- **验收标准**：
  - `injection_block_or_drop_rate >= 0.99`（200 条注入）；`python scripts/security_regression.py --injections 200 --assert-block-rate 0.99`
  - `benign_false_positive_rate <= 0.05`（200 条正常）；`python scripts/security_regression.py --benign 200 --assert-fp 0.05`
  - `injected_influence_on_rating_count == 0`；`python scripts/security_regression.py --assert-influence 0`
  - `unauthorized_tool_calls == 0`；`pytest tests/security/test_prompt_injection.py::test_no_unauthorized_tool_calls`
  - `security_event_log_coverage == 1.0`；`pytest tests/security/test_prompt_injection.py::test_log_coverage`
- **取舍**：强消毒可能误伤正常语义；用 5% 误报上限和日志抽查控制。本期丢弃完整 quarantine queue/reviewer，以降低复杂度。
- **依赖与风险**：依赖 `REQ-INV-003`。风险是检测规则过严/过松；用固定红队集 + 正常集双向校准。

#### `REQ-INV-004` 密钥不泄露

- **类型**：Invariant
- **优先级**：Must
- **负责 Part**：5
- **陈述**：API key、访问令牌和凭据不得出现在日志、报告、manifest、prompt、模型上下文或错误消息中。系统只能从环境变量或密钥存储读取密钥，并在持久化前脱敏。
- **为什么需要**：密钥泄露是灾难性事件，也会污染课程会话记录。当前 `.env` 已改为 `${SEP_API_KEY}` 引用环境变量；需要把它固化为可测试的不变量。
- **实现方案**：
  - 新增 `security/redaction.py`：日志 filter、报告/manifest 写入前 scrub、prompt allowlist。
  - CI 增加 gitleaks 或等价 secret scan。
  - 合成密钥测试：把假 key 注入日志/错误/报告，断言全部被脱敏。
- **验收标准**：
  - `secret_findings_in_artifacts == 0`；`pytest tests/security/test_secret_redaction.py::test_artifacts`
  - `synthetic_secret_redaction_rate == 1.0`；`pytest tests/security/test_secret_redaction.py::test_redaction`
  - `ci_secret_scan_findings == 0`；`gitleaks detect --no-git --source .`
  - `secret_occurrences_in_model_payload == 0`；`pytest tests/security/test_secret_redaction.py::test_prompt_payload`
- **取舍**：脱敏可能让错误信息变短；接受，因为保密性优先。只针对密钥模式和已登记 env 名，避免过度误伤。
- **依赖与风险**：依赖 Part 3 报告/manifest 写入点。风险是第三方 SDK 异常文本带 key；在异常处理层统一脱敏。

---

### Part 6 — 性能与成本

#### `REQ-PER-001` 分档端到端延迟

- **类型**：Performance
- **优先级**：Must
- **负责 Part**：6
- **陈述**：在参考环境（4 vCPU / 16 GB RAM，provider 网络延迟 <=100 ms）上，端到端 p95 延迟应满足：Quick <=300 秒、Standard <=720 秒、Deep <=1800 秒。冷/热缓存各至少 15 次；p99 <=1.2 × p95；基准失败/超时率 <=1%；Quick/Standard 相对基线改善 >=30%。
- **为什么需要**：当前 1 个分析师约 425 秒、2 个约 550 秒，速度是核心痛点。没有量化目标就无法判断档位、缓存、早停和模型分层是否有效。
- **实现方案**：
  - 新增 `scripts/bench_latency.py`：记录硬件、网络、provider、模型、缓存状态。
  - 复用 Part 1 档位、Part 4 缓存/checkpoint、Part 2 早停、模型分层（quick 做分析/研究，deep 做 manager）。
  - 输出 p50/p95/p99、失败率、阶段耗时、相对基线改善。
- **验收标准**：
  - `quick_p95 <= 300`；`python scripts/bench_latency.py --profile quick --cold 15 --warm 15 --assert-p95 300`
  - `standard_p95 <= 720`；`python scripts/bench_latency.py --profile standard --cold 15 --warm 15 --assert-p95 720`
  - `deep_p95 <= 1800`；`python scripts/bench_latency.py --profile deep --cold 15 --warm 15 --assert-p95 1800`
  - `p99_over_p95 <= 1.2`；`python scripts/bench_latency.py --assert-p99-ratio 1.2`
  - `benchmark_failure_rate <= 0.01`；`python scripts/bench_latency.py --assert-failure-rate 0.01`
  - `quick_standard_improvement >= 0.30`；`python scripts/bench_latency.py --baseline reports/baseline.json --assert-improvement 0.30`
- **取舍**：更快可能需要减少分析师/工具轮次/上下文，降低覆盖；必须与 `REQ-QUAL-001/002` 同时通过，不能单独以速度换质量。
- **依赖与风险**：依赖 Part 1/2/4。风险是外部 provider 抖动；固定参考环境、记录网络、取 p95，必要时多轮重测。

#### `REQ-COST-001` 分档 token 预算与成本报告

- **类型**：Cost
- **优先级**：Must
- **负责 Part**：6
- **陈述**：单次运行 p95 token 用量（输入 + 输出，含重试）应满足：Quick <=80,000、Standard <=150,000、Deep <=300,000。系统应在每次 provider 调用前估算 token，超出该档 hard 上限时**阻断调用并结束为 `budget_exceeded` / `REVIEW`（不得静默继续）**；按档位裁剪注入的输入（工具输出与报告注入到 prompt 的字符上限）以控制用量；实际用量按 agent/model 拆分记录；每次运行产出 token/费用报告。
- **为什么需要**：应用被描述为 token-burning，当前产物不汇总 token/费用。没有预算和成本报告，无法控制成本，也无法验证优化效果。
- **实现方案（按实际代码）**：
  - `cost/estimator.py`：确定性、离线的 `estimate_tokens()`（近似，用于调用前预警，非 provider tokenizer）。
  - `cost/budget.py`：分档 soft/hard 上限（Quick 64k/80k、Standard 120k/150k、Deep 240k/300k），可被 `ProfileConfig` 覆盖。
  - `graph/trading_graph.py`：把 quick/deep LLM 包成 `GuardedLLM`，每次调用前 `_check_budget_before_call` 估算“已用 + 本次 + 输出上限”，超 hard 上限抛 `BudgetExceededError`；运行结束据 `finish_cost_run` 附成本报告，硬停时状态为 `budget_exceeded`、评级 `REVIEW`。
  - `profiles.py` + `GuardedToolNode`/`agents/context.py`：按档位截断工具输出与报告注入（`max_tool_output_chars`、`report_prompt_chars`、`max_output_tokens`），这是实际生效的“省 token”手段。
  - `cost/callback.py` + `cost/monitor.py` + `cost/agent_context.py`：从 provider 回调收集 `LLMCallEvent`，按 agent 汇总 token、估算费用，产出 `CostReport`。
  - `scripts/token_audit.py` / `scripts/bench_latency.py`：对录制 JSONL 或真实运行做 p95/覆盖率/费用/质量门的断言。
  - **说明（实现现状）**：`cost/router.py` 的“直接/摘要/便宜模型/审批”路由、`summarize_context` 摘要压缩、`select_cheaper_model` 换便宜模型、`apply_quality_floor` 质量门禁回滚，均已在 `cost/` 实现并有单测，但**尚未接入 `graph`/`cli` 运行路径**；当前运行时超预算的行为是**直接硬停为 REVIEW**，而非渐进降级。这些渐进路径目前仅由 `cost/runner.py`（验收用 facade）与 `token_audit.py` 使用。
- **验收标准（离线单测；脚本/真实基准为 integration）**：
  - `quick_p95_tokens <= 80000`；`pytest tests/req/test_token_cost.py::test_quick_p95_tokens`
  - `standard_p95_tokens <= 150000`；`pytest tests/req/test_token_cost.py::test_standard_p95_tokens`
  - `deep_p95_tokens <= 300000`；`pytest tests/req/test_token_cost.py::test_deep_p95_tokens`
  - `token_report_coverage == 1.0`；`pytest tests/req/test_token_cost.py::test_report_coverage`
  - `silent_over_budget_runs == 0`、硬停为 REVIEW；`pytest tests/req/test_token_cost.py::test_no_silent_over_budget`、`::test_hard_stop_blocks_call_over_budget`、`::test_budget_exceeded_record_is_review`
  - `routed_run_quality_floor_pass_rate == 1.0`；`pytest tests/req/test_token_cost.py::test_routed_quality_floor`
  - 真实基准（需配额）：`python scripts/token_audit.py --profile quick --runs 30 --assert-p95 80000`
- **取舍**：token 上限通过裁剪输入与硬停实现；硬停会让该次运行作废（REVIEW），而不是继续降级（摘要/便宜模型/审批的渐进路由已实现但未接入）。Quick 的成本优势以覆盖面为代价。
- **依赖与风险**：依赖 Part 1 profile、Part 3 manifest、provider adapter 的 usage。风险是不同 provider 的 token 计数差异；以 provider usage 为准，估算仅用于调用前预警。

---

## 5. 舍弃需求与原因

> 以下需求不进入本期实施。原因分为：不可机器验收、实现/运维过重、与完成项目目标冲突、已有实现或价值不足、明显超出课程范围。

| 来源/原 ID | 需求 | 舍弃原因 | 处置 |
|---|---|---|---|
| 其他文档 `REQ-FR-01` | 完整意图分类（偏题/模糊分类） | 需要额外 LLM/分类器，增加延迟和成本；本期用 `REQ-FR-002` 预检覆盖最关键的 ticker 有效性 | 舍弃；保留预检 |
| 其他文档 `REQ-FR-03` | 模糊请求澄清/人工路径 | 需要 UI/队列/人工 SLA，课程周期内过重 | 舍弃 |
| 其他文档 `ARCH-EA-02` | MCP 工具平面/工具白名单 | 新组件、维护成本高；本期只在安全需求里加越权工具调用 guard | 舍弃完整工具平面 |
| 其他文档 `ARCH-EA-03` | 提示词版本化产物 | 价值高但工程量大；本期 manifest 只记录 config hash/prompt version 字符串 | 舍弃完整版本库 |
| 其他文档 `SEC-03` | 隔离队列 + 复核人 | 需要队列、负责人、SLA；本期改为“丢弃/记录，不影响评级” | 舍弃完整 quarantine |
| 其他文档 `GOV-01` | 完整 provenance 记录 | 大部分并入 `REQ-FR-004` manifest | 合并 |
| 其他文档 `GOV-02` | 哈希链、12 个月保留 | 审计工程量大；本期只做原子 + 幂等记录 | 舍弃哈希链/保留期 |
| 其他文档 `GOV-03` | 操作者告警/看门狗 | 需要告警通道和运维；课程演示不需要 | 舍弃 |
| 其他文档 `GOV-04` | 阻塞式 CI 审批闸门 | 需要测试审批流程、AI 使用日志 schema、分支保护；过重 | 舍弃；保留普通测试 |
| 其他文档 `QUAL-03` | 多评审语义评估 | 人工/LLM judge 不可稳定机器校验；本期用 `REQ-QUAL-002` 的确定性检查 | 舍弃 |
| 其他文档 `QUAL-04` | REVIEW 率 <=2% | 可能诱导放宽校验；缺少基线；与完成项目目标冲突 | 舍弃 |
| 其他文档 `UNCLEAR-01` | 决策质量回测代理 | 没有可机器校验的 fit criterion；回测 alpha 不稳定 | 舍弃 |
| 旧文档 `REQ-GOV-002` | 人工复核检查点 | 依赖人力和 SLA，过重 | 舍弃 |
| 旧文档 `ARCH-EA-01/02` | Provider 适配器、决策/解释分离 | 前者已存在（保留导入守卫测试）；后者作为设计原则，不单列需求 | 不计数 |
| 旧文档 `REQ-QUAL-003` | 报告可读性/清晰度 | 跨中英文自动指标不可靠，不能机器验收 | 舍弃 |
| 旧文档 `REQ-QUAL-004` | 辩论更有说服力 | 主观，无稳定机器指标 | 舍弃 |
| 旧文档 `REQ-FR-009` | 每句话必须引用 | 输出 token 成本过高；改为实质断言引用 | 舍弃 |
| 旧文档 `REQ-QUAL-005` | 零数字错误 | 无法保证检测完整；保留 `REQ-QUAL-002` 的 <=2% 阈值 | 舍弃绝对保证 |
| 旧文档 `REQ-PER-002` | 无限重试直到成功 | 违反成本/延迟/可用性 | 舍弃 |
| 旧文档 `REQ-GOV-003` | 所有运行强制人工复核 | 运营成本过高 | 舍弃 |
| 项目 brief 外 | 自动交易、微调/RL、全市场覆盖、复杂 Web 前端 | 超出课程范围或无法在周期内验收 | Won't |

---

## 6. 实施路线图

> 假设课程周期 4 周；如果实际少于 2 周，按第 6.3 节裁剪。

### 6.1 四周计划

| 周 | 目标 | 交付物 |
|---|---|---|
| **第 1 周** | 契约冻结 + 基线 | 8 个契约文件、基线延迟/token 报告、测试骨架、六个 Part 的 stub |
| **第 2 周** | 并行实现 | Part 1 档位/预检；Part 2 辩论 schema/质量；Part 3 manifest/证据；Part 4 缓存/checkpoint；Part 5 评级/安全/脱敏；Part 6 token/基准 |
| **第 3 周** | 集成 + 首次验收 | 组合根接线、全量测试、30 次基准、200+200 安全回归、报告演示 |
| **第 4 周** | 修复 + 最终验收 | 性能/成本达标、缺陷修复、演示、文档、OpenCode 会话证据整理 |

### 6.2 关键路径

1. 契约冻结（第 1 周周一）→ 所有 Part 解除阻塞。
2. `RunManifest`（Part 3）→ `REQ-FR-004`、`REQ-COST-001`、`REQ-PER-001` 的证据基础。
3. `RatingResult`（Part 5）→ `REQ-INV-003`、报告评级。
4. `ProfileConfig`（Part 1）→ 性能/成本/缓存都依赖。
5. 组合根接线（Part 1）→ 第 3 周集成。

### 6.3 时间不足时的裁剪顺序

先裁剪 **Should**，再裁 Must 中“锦上添花”的部分：

1. `REQ-QUAL-002` 报告数字忠实度（保留基本数字检查，不做完整抽取器）。
2. `REQ-INV-001` 原子/幂等记录（保留普通写入 + 唯一键检查）。
3. `REQ-INV-002` 时点完整性（保留现有 `date_window` 测试，不扩展所有路径）。
4. `REQ-FR-002` 预检（保留简单 ticker 非空/格式检查）。

**不要裁剪**：`REQ-FR-001`、`REQ-FR-003`、`REQ-QUAL-001`、`REQ-FR-004`、`REQ-FR-005`、`REQ-INV-003`、`REQ-SEC-001`、`REQ-INV-004`、`REQ-PER-001`、`REQ-COST-001`。这些是“能演示 + 能验收 + 对应项目痛点”的最小闭环。

---

## 7. 验收与证据计划

| 验证类型 | 命令/工具 | 证据 | 覆盖 |
|---|---|---|---|
| 单元/集成 | `pytest tests/req` | 测试报告 | 全部 |
| 配置矩阵 | `pytest tests/req/test_profiles.py` | 三档矩阵 | `REQ-FR-001` |
| 预检 | `pytest tests/req/test_preflight.py` | 失败/成功样例 | `REQ-FR-002` |
| 辩论 Schema/质量 | `pytest tests/req/test_debate_*.py` | transcript、指标 | `REQ-FR-003`、`REQ-QUAL-001` |
| Manifest/证据 | `pytest tests/req/test_evidence_manifest.py` | manifest JSON、引用报告 | `REQ-FR-004` |
| 报告忠实度 | `pytest tests/req/test_report_faithfulness.py` | 抽取/比对报告 | `REQ-QUAL-002` |
| 记录原子/幂等 | `pytest tests/req/test_records.py` | 故障注入日志 | `REQ-INV-001` |
| 缓存/恢复 | `pytest tests/req/test_checkpoint_resume.py`、`test_cache.py` | resume 日志、命中率 | `REQ-FR-005` |
| 时点完整性 | `pytest tests/req/test_point_in_time.py` | 属性测试、未来数据 fixtures | `REQ-INV-002` |
| 评级不变量 | `pytest tests/req/test_rating_invariant.py` | 10k 模糊测试 | `REQ-INV-003` |
| 安全回归 | `python scripts/security_regression.py` | 200+200 报告 | `REQ-SEC-001` |
| 密钥扫描 | `pytest tests/security/test_secret_redaction.py`、`gitleaks` | 0 findings | `REQ-INV-004` |
| 延迟基准 | `python scripts/bench_latency.py` | p95/p99、改善比例 | `REQ-PER-001` |
| Token/成本 | `python scripts/token_audit.py` | 分档 token、费用、超预算 | `REQ-COST-001` |

**Agentic software engineering 证据**：

- 每个 Part 的代码修改通过 OpenCode 会话完成，保留会话记录；
- 每次人类干预（需求变更、架构选择、拒绝智能体方案）记录到 `docs/agent-log.md`；
- 提交、测试输出、基准报告、验收截图共同构成“人类指导 + 智能体实现 + 人类监督”的证据；
- 不对生成代码做非智能体手工修改；如需修改，通过新的 OpenCode 指令完成。

---

## 8. 风险与开放问题

| 风险/问题 | 影响 | 缓解 |
|---|---|---|
| 4 周时间不足 | 无法完成全部 Must | 第 6.3 节裁剪 Should；优先最小闭环 |
| Provider 延迟/限流 | 性能/成本验收不稳定 | 固定参考环境、p95、多轮重测、重试/降级 |
| Reddit 403 | 情感分析置信度低 | 保留 `<unavailable>` + 降置信度；不阻塞运行 |
| Token 上限过紧 | 报告质量下降 | 质量门禁 + 摘要保留受保护证据 + 审批加预算 |
| 模型不遵守 JSON | 辩论结构失败 | 结构化输出 + 一次重试 + 主持人总结兜底 |
| 契约变更频繁 | 并行开发冲突 | 第 1 周冻结；变更需 owner 批准 + 契约测试 |
| Part 3/5 负担偏重 | 进度不均 | 允许把 Should 项延后；Part 1 协助集成，不抢契约所有权 |
| 评分/验收需要真实 API 配额 | 基准/安全回归无法跑 | 提前申请配额；用录制数据做确定性测试，真实调用只做少量基准 |
| 课程要求人工复核/治理 | 当前 Won't 可能不满足 | 如果教师明确要求，重新评估 `REQ-GOV-*`，不要临时硬塞 |

**需要组内确认的 3 件事**：

1. **实际开发周期**：4 周、3 周还是更短？如果 <2 周，按 6.3 节裁剪。
2. **谁负责哪个 Part**：本文件用 A–F 占位；请确认六人分工，尤其是 Part 3/5 工作量较大。
3. **是否需要保留人工复核/完整审计**：本文件按“完成项目优先”舍弃；如果课程评分明确要求治理/人工复核，需要把相关需求加回并重新分配。

---

## 9. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-11-16 | 合并两份需求文档；按“完成项目优先”裁剪为 14 条；划分 6 个解耦 Part；补充实现方案、验收命令、舍弃清单和风险 |
