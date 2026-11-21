# Part 2 需求与计划追踪

复核日期：2026-11-20。依据仅为本仓库 `docs/req/plans/part-2-debate.md`（最高优先级）、`test-cases/part2-debate.md`、`docs/gate-intro.md`，并核对现有实现、审批与证据。本文不扩大 Part 2 的修改范围。

下表路径缩写：`P=tradingagents/tradingagents/`，`T=tradingagents/tests/`，`E=part2-live-acceptance-2026-11-20/`；均相对仓库根目录。证据口径见[验收摘要](part2-acceptance.md)，集成责任见[交接摘要](part2-integration.md)。

状态仅使用：真实运行证据完成、离线确定性证据完成、两类证据共同完成、跨 Part 集成待办、缺失。“真实运行证据完成”指现有调用记录的旁证，不代表服务商侧不可伪造证明。

## 需求映射

| 需求与行为 | 生产文件 | 已审批测试/证据 | 状态 |
|---|---|---|---|
| REQ-FR-003：统一字段、枚举、置信度、字符串引用与历史关系 | `P/contracts/debate.py`；`P/agents/debate/schemas.py`、`validator.py` | `test_schema_valid`；`T/contracts/test_debate_contract.py`；E 中 120 条响应的契约复核 | 两类证据共同完成 |
| REQ-FR-003：单个 JSON、至多两次模型函数调用、失败占位 | `P/agents/debate/prompts.py`、`adapter.py`、`stubs.py` | `test_retry_then_degrade`；提示及 stub 契约测试。真实批次仅观测到首次成功 | 离线确定性证据完成 |
| REQ-FR-003：最大轮数、研究员接入与三种路由值 | `P/agents/researchers/bull_researcher.py`、`bear_researcher.py`；`P/graph/conditional_logic.py::should_continue_debate`；`convergence.py` | `test_max_rounds`；E 中 30 份均为 4 次发言后到 Research Manager 入口 | 两类证据共同完成 |
| REQ-FR-003：完整双方轮次收敛、未完成轮次不早停 | `P/agents/debate/convergence.py` | `test_convergence_fixtures`；既有收敛/不收敛样本；真实批次未出现实际早停 | 离线确定性证据完成 |
| REQ-FR-003：有序导出及 JSON 往返 | `P/agents/debate/export.py`；`contracts/debate.py` | `test_export_schema`、契约往返测试；E 中 30/30 导出复核 | 两类证据共同完成 |
| REQ-QUAL-001：四项确定性指标与边界 | `P/agents/debate/quality.py`；包 `__init__.py` 导出 | `test_evidence_coverage`、`test_rebuttal_coverage`、`test_unsupported_claim_rate`、`test_duplicate_claim_rate`；30 份逐项复算 | 两类证据共同完成 |
| REQ-QUAL-001：空记录、不可用或 invalid 时四项为 None | `P/agents/debate/quality.py`；两名研究员设置可用性 | `test_evidence_coverage`、`test_retry_then_degrade` 及契约测试 | 离线确定性证据完成 |
| 两条需求：Manager 后的 transcript 透传、最终日志落盘及 Part 3 消费 | 集成方负责的状态与日志出口；本阶段不修改 | 当前脚本在 Manager 入口结束，不能证明后续链路 | 跨 Part 集成待办 |

## Week 1–4 逐项矩阵

| 计划项 | 核验结果 | 状态 |
|---|---|---|
| Week 1：DebateTurn、Stance、DebateTranscript 与契约测试 | 唯一字段源在 `contracts/debate.py`；重新导出对象同一性、字段及枚举断言通过 | 离线确定性证据完成 |
| Week 1：Bull/Bear 提示草稿 | `prompts.py` 请求单个 JSON，Schema 来自唯一契约；角色与引用格式有断言 | 离线确定性证据完成 |
| Week 1：本地 sanitize stub 与字符串引用 | `sanitize(text)` 原样返回；不代表正式安全处理。模型样本中引用均为字符串 | 两类证据共同完成 |
| Week 1：五个 golden fixture | `normal.json`、`missing_fields.json`、`bad_rebuttal.json`、`duplicate_claims.json`、`convergence.json`；均由现有契约测试读取 | 离线确定性证据完成 |
| Week 2：字段、round、speaker、rebuttal_to 校验 | `validator.py` 与协议/契约断言；120 条真实批次记录复核通过 | 两类证据共同完成 |
| Week 2：JSON 解析、失败只重试一次、两次调用上限 | 注入格式错误、缺字段、错误角色/round、异常及无效响应对象；调用计数断言 | 离线确定性证据完成 |
| Week 2：第二次失败的 invalid 降级 | 完整占位、`no_new_evidence=true`、`quality_available=false`、转 Manager 路由有断言；未执行 Manager 总结 | 离线确定性证据完成 |
| Week 2：最大轮数 | 双方各一次为一轮，配置 2 时恰好 4 次；真实批次与离线驱动一致 | 两类证据共同完成 |
| Week 2：收敛早停 | 比较相邻两个完整双方轮次；单方未完成、立场变化或有新证据均不早停 | 离线确定性证据完成 |
| Week 2：两名研究员与路由接入 | 保留文本历史、响应前缀、计数；路由值不变；30 份接入记录及离线断言 | 两类证据共同完成 |
| Week 2：30 次运行 Schema 100% | E 中 30 份、120 条均可按当前契约复核；联网真实性限于旁证 | 真实运行证据完成 |
| Week 3：四项指标及 golden 回归 | 生产评分与独立算式一致；缺证据、错误引用、规范化重复等断言通过 | 两类证据共同完成 |
| Week 3：阈值边界 | 反驳 27/30、26/30；无证据 2/40、3/40；重复 3/30、4/30，含通过和失败边界 | 离线确定性证据完成 |
| Week 3：30 份批量指标及报告 | E 保留原数据；本次仅归纳复核结果，不复制模型内容到 docs | 两类证据共同完成 |
| Week 3：与 Part 3 对齐 EvidenceRef | 目前只使用字符串；对象迁移及负责人确认仍待交接 | 跨 Part 集成待办 |
| Week 3–4：提示调优降低失败率的前后对照 | 只有本批 0/120 无效的记录，缺少调优前后可比样本，不能据此证明改善幅度 | 缺失 |
| Week 4：失败样例与重试策略 | 异常样例来自现有离线故障注入，真实批次没有自然失败；两类来源不混淆 | 离线确定性证据完成 |
| Week 4：当前有效验收与测试结果 | 本次 66 项离线测试通过；30 份成功路径已复核。旧命令差异见下节 | 两类证据共同完成 |
| Week 4：新增字段/收敛维护 README | `P/agents/debate/README.md` 存在，注明相似度 0.95、重复率上限 0.10 | 离线确定性证据完成 |
| Week 4：AI 使用日志、人工审核留痕 | `docs/ai-use-log.yaml` 的 `part2-debate` 条目存在；审核表述是仓库留痕，未提供独立平台审查记录 | 离线确定性证据完成 |
| Week 4：同一 ticker 的结构化/自由文本演示与演示脚本 | E 中脚本仅驱动结构化辩论，离线自由文本回退测试不等于该演示 | 缺失 |

## 计划书第 6 节：实际测试接口

本地 `master` 与 `origin/master` 均指向 `131f25a`；本次未获取远端更新，不能称其代表 GitHub 当前最新 master。读取这一本地 master 与当前分支后，两个需求测试文件的函数名一致。测试内容的补齐位于 Part 2 四个实现提交中。

| 计划书旧接口 | 本次实际使用的已审批接口 | 状态 |
|---|---|---|
| `test_schema_valid --runs 30` | `tests/req/test_debate_protocol.py::test_schema_valid`；函数内部构造 30 条离线发言，另行复核 E 的 30 份记录 | 两类证据共同完成 |
| `test_max_rounds`、`test_convergence_fixtures`、`test_export_schema` | 同名现有函数；分别验证上限、早停决策、JSON 导出 | 离线确定性证据完成 |
| `test_debate_quality.py --transcripts 30` | `test_evidence_coverage`、`test_rebuttal_coverage`、`test_unsupported_claim_rate`、`test_duplicate_claim_rate`；E 的 30 份指标由本次只读复算核验 | 两类证据共同完成 |
| `test_golden_cases` | 当前 master 和分支均无此函数；使用已审批契约测试中五个样本的断言及上述四个质量测试 | 离线确定性证据完成 |
| `test_live_schema_valid`、`test_live_metrics`、`test_quality_golden_determinism` | 当前仍标记 integration，函数体仅导入模块。本次没有运行，也不计为有效验收通过 | 缺失 |

当前 Part 2 测试没有定义计划书的 `--runs`、`--transcripts` 专用参数；实际命令不带这两个旧选项，不修改计划书或测试名。第九个点名测试是 `test_retry_then_degrade`；完整命令见[验收摘要](part2-acceptance.md#离线异常与边界验收)。

审批文件 `docs/approvals/part2-debate.json` 覆盖两个需求测试、契约测试和上述五个 fixture。实际 fixture 目录是 `T/fixtures/debate/`；用例文档中的旧 `fixtures/transcripts/` 路径未沿用，也未另建。

## 计划书第 7 节：风险与回退

| 风险/措施 | 核验与边界 | 状态 |
|---|---|---|
| 模型不遵守 JSON：重试一次、invalid、质量不可用 | 离线注入验证；真实批次全部首次成功。Manager 自由文本总结仍未做端到端验证 | 离线确定性证据完成 |
| token 增加：观测用量及早停保障 | 有自报用量旁证和离线轮数/早停断言，不据此宣称成本优化完成 | 两类证据共同完成 |
| 限制每轮字数、只保留必要历史 | 未取得字数限制/历史裁剪策略及效果的验证证据；测试脚本的输出上限不等于生产策略 | 缺失 |
| Quick 只用一轮及成本配置联动 | 配置、profile 和成本路由由对应 Part 集成；本阶段未验证联动 | 跨 Part 集成待办 |
| 研究员提示冲突、旧文本回退 | 实际字段为 `investment_debate_state.enable_structured_debate`，缺省 true；false 回退有离线断言。未实现计划旧名 `debate_protocol` 的别名 | 离线确定性证据完成 |
| 重复主张误判 | 固定规范化、相似度常量及五个 golden 样本；不把词面代理指标当成语义说服力证明 | 离线确定性证据完成 |
| 过早收敛 | 至少两个完整双方轮次才有上一轮立场可比较；不完整轮次不能早停；上限始终兜底 | 离线确定性证据完成 |

## 计划书第 8 节：Definition of Done

| 完成定义 | 证据与限制 | 状态 |
|---|---|---|
| 30 次运行 turn Schema 100%，失败明确降级 | 120 条记录确定性复核；失败降级由离线注入覆盖 | 两类证据共同完成 |
| 最大轮数及收敛早停按规则执行 | 真实批次 30/30 到上限；实际早停只有离线 fixture 证据 | 两类证据共同完成 |
| 四项指标达标、golden 回归 | 30 份全部达标；四项边界与五个样本契约回归通过 | 两类证据共同完成 |
| transcript 可导出 JSON | 30/30 往返一致，离线导出测试通过 | 两类证据共同完成 |
| Part 3 可直接消费、最终日志保留 transcript | 尚无跨 Part 消费和最终落盘结果 | 跨 Part 集成待办 |
| 会话/测试摘要及样本归档 | 本次四份摘要索引已有 E 目录，不复制完整记录 | 两类证据共同完成 |
| 计划原文的完整 OpenCode 会话导出 | 未见该产物；本阶段仅写摘要，不导出完整会话或控制台输出 | 缺失 |

## 计划书第 9 节：公开接口与交接

| 交接项 | 当前实际接口/位置 | 状态 |
|---|---|---|
| DebateTurn / DebateTranscript 契约 | `P/contracts/debate.py` 唯一定义，`schemas.py` 只重新导出；契约断言通过 | 离线确定性证据完成 |
| run_debate_turn | `adapter.py::run_debate_turn(state, speaker, complete) -> DebateTurn`；比计划简写多一个必需的可注入模型函数 | 两类证据共同完成 |
| should_stop | `convergence.py::should_stop(transcript, max_rounds) -> bool` | 两类证据共同完成 |
| export_transcript | `export.py::export_transcript(transcript) -> dict` | 两类证据共同完成 |
| score_debate | `quality.py::score_debate(transcript) -> QualityMetrics`；接收契约或 mapping，不修改输入 | 两类证据共同完成 |
| tests/contracts 契约测试 | `T/contracts/test_debate_contract.py` 纳入本次 66 项通过结果 | 离线确定性证据完成 |
| 正式告知 Part 3 字符串格式与迁移边界 | [交接摘要](part2-integration.md)已成文，尚无 Part 3 负责人接收/确认记录 | 跨 Part 集成待办 |


