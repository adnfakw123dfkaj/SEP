# Part 3 实现计划书 — 证据链、报告与记录

## 1. 基本信息

| 项 | 内容 |
|---|---|
| 负责组员 | 组员 C（待确认） |
| 覆盖需求 | `REQ-FR-004`（Must）、`REQ-QUAL-002`（Should）、`REQ-INV-001`（Should） |
| 核心目标 | 让报告“每句重要结论有出处”，每次运行有 manifest，决策记录原子且幂等 |
| 提供接口 | `RunManifest`、`EvidenceRef`、`EvidenceRegistry`、`write_manifest()`、`write_decision_record()`、`score_report()` |
| 依赖接口 | `RatingResult`（Part 5）、`LLMCallEvent`（Part 6）、`ProfileConfig`（Part 1）、`DebateTranscript`（Part 2） |
| 不负责 | 评级计算、token 估算/路由、安全过滤、缓存实现；只消费并记录 |

## 2. 目标与非目标

### 目标

- 报告中数字断言 100% 有 `evidence_ref`；定性断言 ≥95% 有引用。
- 每次运行生成可校验的 `manifest.json`，包含模型、版本、token、费用、降级/安全事件、评级。
- 决策记录（state + report tree + manifest）原子写入；相同运行签名幂等。
- 用确定性指标评估报告数字忠实度与引用支持。

### 非目标

- 不做完整哈希链/12 个月保留/审计服务（已舍弃）。
- 不做人工盲评/可读性评估（已舍弃）。
- 不重写报告内容生成逻辑；只在现有报告上增加引用和清单。

## 3. 交付物

- 代码：
  - `tradingagents/contracts/evidence.py`：`EvidenceRef`、`EvidenceKind`。
  - `tradingagents/contracts/manifest.py`：`RunManifest`（Pydantic）。
  - `tradingagents/evidence/registry.py`：引用注册、工具 `call_id`、snapshot hash、news/social id。
  - `tradingagents/evidence/manifest_writer.py`：写出/校验 manifest。
  - `tradingagents/evidence/fidelity.py`：数字断言抽取、snapshot 比对、引用检查。
  - `tradingagents/records/atomic.py`、`records/idempotency.py`。
  - `tradingagents/reporting.py`、`report_html.py`：引用脚注、manifest 摘要。
- 测试：
  - `tests/contracts/test_manifest_contract.py`
  - `tests/req/test_evidence_manifest.py`
  - `tests/req/test_report_faithfulness.py`
  - `tests/req/test_records.py`
- 文档/证据：
  - `manifest.example.json`
  - 一份带脚注的报告样例
  - 故障注入日志（原子写/幂等）

## 4. Manifest 契约（第 1 周冻结）

必填字段：

```text
run_id, ticker, trade_date, profile, selected_analysts,
quick_model, deep_model, provider,
prompt_version, config_hash, vendor_versions,
cache_hits, token_usage_by_agent, cost_estimate,
fallback_events, security_events,
final_rating, started_at, finished_at, status
```

规则：

- `RunManifest` 是唯一 manifest schema；其他 Part 只填自己的字段，不另建 schema。
- 缺字段 = schema 校验失败；可选字段必须显式 `null` 或空列表。
- `evidence_ref` 格式：`kind:id`，例如 `market_snapshot:<hash>`、`news:<article_id>`、`sec:<accession>`、`social:<source>:<post_id>`、`tool:<name>:<call_id>`。
- 数字断言必须有引用；定性断言至少 1 个引用或标记 `unsupported`。

## 5. 工作分解

### Week 1：契约与样例

- 定义 `EvidenceRef`、`RunManifest`、`DecisionRecord` schema。
- 写 `manifest.example.json` 和契约测试。
- 与 Part 1/5/6 对齐字段：profile、rating、LLMCallEvent。
- 设计报告脚注格式和引用注册表 API。
- 交付：契约 + 样例 + 契约测试。

### Week 2：证据注册与 manifest

- 实现 `EvidenceRegistry`：工具调用返回 `call_id`/`snapshot_hash`；news/social 返回稳定 id。
- 修改报告渲染：数字断言旁加脚注，文末列引用。
- 实现 `manifest_writer`：收集各 Part 字段，写出 `results_dir/runs/<run_id>/manifest.json`。
- 接入最终图节点（与 Part 1 组合根协作）。
- 交付：一次 Quick 运行产出 manifest + 带引用报告。

### Week 3：忠实度与记录完整性

- 实现 `fidelity.py`：数字断言抽取、snapshot 比对、引用支持检查。
- 实现原子记录：staging dir + 原子 rename + 完整集合 hash。
- 实现幂等：`record_id = hash(ticker, date, run_signature)`；记忆日志 append 前检查。
- 故障注入测试：写入中途 kill；重复运行 N 次。
- 交付：`REQ-QUAL-002`、`REQ-INV-001` 验收通过。

### Week 4：集成与收尾

- 与 Part 1/5/6 做 manifest 全字段联调；修复缺字段/类型问题。
- 跑 replay 测试：仅凭 manifest + 引用存储重建报告章节。
- 补文档：如何新增 manifest 字段、如何新增 evidence kind。
- 准备演示：一份报告 + manifest + 一个被拒绝的残缺写入。
- 交付：验收报告 + 演示脚本。

## 6. 验收与测试

| 需求 | 验收命令 | 证据 |
|---|---|---|
| `REQ-FR-004` | `pytest tests/req/test_evidence_manifest.py::test_numeric_refs --reports 30` | 引用覆盖率 |
| `REQ-FR-004` | `pytest tests/req/test_evidence_manifest.py::test_manifest_schema --runs 30` | manifest schema 报告 |
| `REQ-FR-004` | `pytest tests/req/test_evidence_manifest.py::test_token_sum` | token 汇总误差 |
| `REQ-FR-004` | `pytest tests/req/test_evidence_manifest.py::test_replay` | 回放报告 |
| `REQ-QUAL-002` | `pytest tests/req/test_report_faithfulness.py --reports 30` | 数字/引用报告 |
| `REQ-INV-001` | `pytest tests/req/test_records.py::test_fault_injection` | 故障注入日志 |
| `REQ-INV-001` | `pytest tests/req/test_records.py::test_idempotent_append` | 重复运行记录 |

## 7. 风险与回退

| 风险 | 缓解 | 回退 |
|---|---|---|
| Manifest 字段频繁变更 | 第 1 周冻结；字段变更需 owner 批准 + 契约测试 | 保留旧字段可选，新增字段默认 null |
| 报告树在 Windows 上原子 rename 失败 | 同卷 staging + 原子 rename；测试目标平台 | 退化为“临时文件 + 完成标记”，仍保证可解析 |
| 引用过细导致 token 上升 | 只对实质断言引用；数字断言优先 | 降低定性引用阈值（不推荐低于 90%） |
| 数字抽取器漏检导致假通过 | 增加 recall 指标和 golden fixtures | 引入人工抽查，但不写入自动验收 |
| 与其他 Part 的 manifest 字段冲突 | Part 3 独占 schema；其他 Part 只填值 | 用 namespace 字段（如 `cost.*`、`security.*`） |

## 8. Definition of Done

- Quick 运行产出完整 manifest，schema 100% 通过。
- 报告中数字断言 100% 有引用；定性断言 ≥95% 有引用。
- 数字忠实度、引用支持率达到阈值。
- 原子写入故障注入 0 残缺；相同签名重复运行 1 条记录。
- 其他 Part 不需要修改 Part 3 的 schema 即可填字段。
- OpenCode 会话记录、测试输出、样例报告已归档。

## 9. 集成交接清单

- [ ] `RunManifest` / `EvidenceRef` 契约冻结并通知全组。
- [ ] 提供 `registry.add_ref()` / `registry.get_ref()`。
- [ ] 提供 `write_manifest(context) -> Path`。
- [ ] 提供 `write_decision_record(state, report_tree, manifest) -> Path`。
- [ ] 提供 `compute_record_id(ticker, date, run_signature)`。
- [ ] 提供 `score_report(report, snapshot) -> FidelityMetrics`。
- [ ] 在 `tests/contracts/` 增加 manifest/evidence 契约测试。
