# Part 6 测试用例规格（TDD 基线）

| 项目 | 内容 |
|---|---|
| 版本 | v0.2（待审核；全部用例 READY） |
| 日期 | 2026-11-16 |
| 负责 Part | Part 6 — 性能与成本 |
| 覆盖需求 | `REQ-PER-001`（Must）、`REQ-COST-001`（Must） |
| 文档性质 | 测试用例规格；**不包含 pytest 实现代码** |
| 目的 | 先固定“什么算通过”，再面向这些用例开发，避免实现跑偏 |

> 本文档按 TDD 顺序编写：先契约，再单元，再失败路径，再集成，最后真实基准/审计。  
> 当前 69 个用例全部 READY，没有 PENDING；如果后续出现新歧义，再单独标记，不自行决定。

---

## 0. 已确认的测试约定

| 项 | 约定 |
|---|---|
| 测试形式 | 先交 Markdown 规格；确认后再落地为 pytest |
| 延迟验收 | Quick/Standard **只做相对基线改善**；绝对 p95 只记录，不阻断 |
| Deep 验收 | Deep 3+3 只记录 p50/p95/max，不阻断 |
| p99 | 只记录，不阻断 |
| 失败率 | 基准失败/超时率 **≤1% 阻断** |
| 基准样本量 | Quick/Standard：15 冷 + 15 热；Deep：3 冷 + 3 热 |
| 超预算行为 | 默认**硬失败**：下一次 LLM 调用前停止，非零退出；写 manifest/cost report，`status=budget_exceeded`；`final_rating="REVIEW"` |
| 路由优先级 | soft→hard 之间：**摘要优先**；摘要不足再考虑便宜模型 |
| percentiles | **nearest-rank**：p95 = 排序后第 `ceil(0.95n)` 个值 |
| 价格表 | 真实来源：DeepSeek 官方定价（CNY/百万 tokens）；单元/公式测试用**合成 CNY 价格**；真实验收用 `provider usage × 价格表` |
| 币种 | **CNY（元）**；报告统一使用 CNY |
| 峰谷价 | **按调用时间自动判断**：北京时间周一至周五 9:00–12:00、14:00–18:00 为高峰；其余为空闲；**忽略中国法定节假日**（节假日按工作日/时段规则处理） |
| 缓存价 | **一律按 cache miss**；不区分 cache hit/miss 输入价 |
| 价格表版本 | 记录 `source_url`、`retrieved_at`、`model_version`、`currency` |
| 测试分层 | L1/L2 离线单元/契约；L3/L4 手动真实基准，不进 CI |
| 代码约束 | 当前阶段不写实现代码，也不写 pytest 代码 |

### 测试层级

| 层级 | 内容 | 是否联网 | 是否耗 token | 运行时机 |
|---|---|---|---|---|
| L1 | 契约/纯单元 | 否 | 否 | 每次提交/CI |
| L2 | 集成（fake provider / fixture） | 否 | 否 | 每次提交/CI |
| L3 | 真实端到端基准 | 是 | 是 | 手动/nightly |
| L4 | 真实验收报告审计 | 是 | 是 | 手动/最终验收 |

---

## 1. 已确认与待确认项（对应 PENDING 用例）

| 编号 | 问题 | 已确认决定 | 影响的测试 |
|---|---|---|---|
| Q1 | Deep 3+3 的验收方式 | 只记录 p50/p95/max，不阻断 | `TC-P6-BEN-003` READY |
| Q2 | p99 <= 1.2 × p95 是否阻断 | 只记录，不阻断 | `TC-P6-BEN-004` READY |
| Q3 | 基准失败/超时率是否阻断 | **≤1% 阻断** | `TC-P6-BEN-005` READY |
| Q4 | soft→hard 之间路由优先级 | **摘要优先**；摘要不足再便宜模型 | `TC-P6-RTR-002/007/009`、`TC-P6-INT-002` READY |
| Q5 | 硬失败时 `final_rating` | **`"REVIEW"`** | `TC-P6-FAIL-002` READY |
| Q6 | 真实价格表单价来源 | **DeepSeek 官方 CNY 定价**；峰谷按时间；cache miss | `TC-P6-AUD-007` READY |
| Q7 | p50/p95 计算方法 | **nearest-rank** | `TC-P6-MON-009` READY |
| Q8 | 中国法定节假日如何判断 | **忽略节假日**，只按工作日/时段 | `TC-P6-MON-012` READY |

> Q1–Q8 已全部确认；当前没有 PENDING 用例。价格页：`https://api-docs.deepseek.com/zh-cn/quick_start/pricing/`，2026-11-16 读取。

---

## 2. 测试夹具（fixtures）

| 夹具 | 内容 | 用途 |
|---|---|---|
| `profile_quick/standard/deep` | 来自 Part 1 的 `ProfileConfig` 或等价 stub：预算、超时、模型 | 预算/路由 |
| `budget_synthetic` | soft=80、hard=100（合成值） | 路由边界；不代表真实 profile 阈值 |
| `price_table_synthetic` | 合成 CNY 价格：modelA=1 CNY/1M（cache miss）、modelB=2 CNY/1M；含 peak/off_peak | 成本数学 |
| `peak_clock` | 固定时间戳：工作日高峰/空闲、周末 | 峰谷价判断 |
| `events_success` | 多条 `LLMCallEvent`，含不同 agent/model/tokens/timestamp | 聚合/成本/峰谷 |
| `events_retry` | 含 `retry_count>0` 的事件 | 重试计数 |
| `events_missing_usage` | usage 缺失或为 null | 估算回退 |
| `quality_pass` / `quality_fail` | Part 2/3 质量指标的 stub | 路由质量门禁 |
| `baseline_report` | 已知 p95 的基线 JSON | 相对改善 |
| `latency_report` | 15+15 / 3+3 的基准输出样例 | 报告 schema/相对改善 |
| `token_report` | token audit 输出样例 | p95/覆盖率/超预算 |
| `manifest_stub` | Part 3 `RunManifest` 的最小结构 | 集成字段 |

---

## 3. 覆盖矩阵（需求指标 → 测试用例）

### `REQ-PER-001` 分档端到端延迟

| 指标 | 测试用例 | 阻塞性 |
|---|---|---|
| 基准报告 schema 完整 | `TC-P6-BEN-001` | 是 |
| Quick/Standard 相对基线改善 ≥30% | `TC-P6-BEN-002` | 是 |
| Deep 3+3 记录 | `TC-P6-BEN-003` | 否（只记录） |
| p99 / p95 比率 | `TC-P6-BEN-004` | 否（只记录） |
| 基准失败/超时率 | `TC-P6-BEN-005` | 是（≤1%） |
| 绝对 p95 记录（Quick/Standard/Deep） | `TC-P6-BEN-006` | 否（只记录） |
| 绝对 p95 超限 warning | `TC-P6-BEN-008` | 否（warning） |
| Quick/Deep 策略表 | `TC-P6-BEN-009` | 是 |

### `REQ-COST-001` 分档 token 预算与成本报告

| 指标 | 测试用例 | 阻塞性 |
|---|---|---|
| Quick/Standard/Deep token p95 上限 | `TC-P6-AUD-001` | 是 |
| 100% 运行有 token/费用报告 | `TC-P6-AUD-002` | 是 |
| 静默超预算 = 0 | `TC-P6-AUD-003` | 是 |
| 费用估算误差 ≤5% | `TC-P6-AUD-004` | 是 |
| 路由运行质量门禁 100% | `TC-P6-AUD-005` | 是 |
| 价格表版本/币种/来源 | `TC-P6-AUD-006` | 是 |
| LLM 调用事件契约 | `TC-P6-CON-001..003` | 是 |
| token 估算正确性 | `TC-P6-EST-001..006` | 是 |
| 预算策略正确性 | `TC-P6-BUD-001..005` | 是 |
| 路由行为正确性 | `TC-P6-RTR-001..007` | 是 |
| 成本聚合/报告 | `TC-P6-MON-001..008` | 是 |
| 硬失败/回退/质量门禁 | `TC-P6-FAIL-001..006` | 是 |
| manifest 集成 | `TC-P6-INT-001..005` | 是 |

---

## 4. L1 契约测试

| ID | 目的 | 输入/步骤 | 期望 | 追溯 | 状态 |
|---|---|---|---|---|---|
| `TC-P6-CON-001` | `LLMCallEvent` 必填字段完整 | 构造一条成功事件 | 含 event_id/run_id/call_id/agent/model/provider/tokens/latency/status/route/usage_source/timestamp；类型正确 | COST | READY |
| `TC-P6-CON-002` | token 求和一致 | 构造 prompt=10、completion=5 | `total_tokens == 15`；负数/不一致被拒绝 | COST | READY |
| `TC-P6-CON-003` | 状态/路由枚举合法 | 构造 success/retry/failure、direct/summarize/cheaper_model/hard_fail | 合法值通过；越界值被拒绝 | COST/PER | READY |
| `TC-P6-CON-004` | `TokenEstimate` 结构 | 构造估算结果 | input/output/total/confidence 存在；total=input+output；非负 | COST | READY |
| `TC-P6-CON-005` | `Budget` 结构 | 构造 Quick 预算 | profile/soft_limit/hard_limit/currency=CNY；soft<=hard | COST | READY |
| `TC-P6-CON-006` | `CostReport` 结构 | 构造一次运行报告 | run_id/profile/total/by_agent/by_model/by_tool/cost/currency/price_table_version/price_table_source/peak_policy/cache_policy/coverage/over_budget/route_paths/quality_floor_pass 存在 | COST | READY |

---

## 5. L1 单元测试 — token 估算

| ID | 目的 | 输入/步骤 | 期望 | 追溯 | 状态 |
|---|---|---|---|---|---|
| `TC-P6-EST-001` | 普通 prompt 估算 | 固定 messages + 固定 tokenizer/fixture | 估算值在预期区间内；非负；total=input+output | COST | READY |
| `TC-P6-EST-002` | 空/极短输入 | 空字符串、单字符 | 返回 0 或最小合理值；不崩溃；不返回负数 | COST | READY |
| `TC-P6-EST-003` | 长上下文 | 长文本/多轮消息 | 估算随长度单调增长；不超过配置上限太多 | COST | READY |
| `TC-P6-EST-004` | 未知模型回退 | 未知 model id | 使用回退估算；`confidence=low`；不崩溃 | COST | READY |
| `TC-P6-EST-005` | 确定性 | 同一输入重复 10 次 | 结果一致（同一 fixture） | COST | READY |
| `TC-P6-EST-006` | 输出上限 | 超长输出估算 | 不超过模型/配置允许的输出上限；超限被截断或标记 | COST | READY |

---

## 6. L1 单元测试 — 预算策略

| ID | 目的 | 输入/步骤 | 期望 | 追溯 | 状态 |
|---|---|---|---|---|---|
| `TC-P6-BUD-001` | 三档硬上限 | Quick/Standard/Deep profile | 硬上限分别为 80k/150k/300k；币种 CNY | COST | READY |
| `TC-P6-BUD-002` | soft/hard 边界 | 合成预算 soft=80、hard=100；估算 79/80/99/100/101 | 79 未超 soft；80 达到 soft；99 未超 hard；100 达到 hard；101 超 hard | COST | READY |
| `TC-P6-BUD-003` | 非法 profile | 未知 profile 名 | 明确错误；不静默使用默认值 | COST | READY |
| `TC-P6-BUD-004` | 非法预算 | 负数/0/soft>hard | 明确错误；不进入路由 | COST | READY |
| `TC-P6-BUD-005` | 币种 | 构造预算 | `currency == "CNY"`；报告沿用 CNY | COST | READY |
| `TC-P6-BUD-006` | soft 阈值来源 | 从一个带 `soft_token_limit` 的 ProfileConfig 构造 Budget | `budget.soft_limit` 来自配置，不是硬编码；缺省时有显式默认值 | COST | READY |

---

## 7. L1 单元测试 — 路由

> Q4 已确认：soft→hard 之间**优先摘要**；摘要不足再考虑便宜模型。

| ID | 目的 | 输入/步骤 | 期望 | 追溯 | 状态 |
|---|---|---|---|---|---|
| `TC-P6-RTR-001` | 预算内直接调用 | 估算 < soft | `route_path=direct`；允许调用 provider | COST | READY |
| `TC-P6-RTR-002` | soft 与 hard 之间 | soft < 估算 < hard | `route_path=summarize`；允许调用 provider；记录路径 | COST | READY |
| `TC-P6-RTR-003` | 超过 hard | 估算 > hard | 在调用 provider 前返回 hard_fail；不产生 LLM 调用 | COST | READY |
| `TC-P6-RTR-004` | 受保护证据 | 触发摘要路径 | 市场快照、evidence_refs、风控约束、评级输入不被删除 | COST | READY |
| `TC-P6-RTR-005` | 路由记录 | 任一路径 | 事件/报告中记录 `route_path` 和预算快照 | COST | READY |
| `TC-P6-RTR-006` | 不静默超支 | 估算 > hard | 不调用 provider；返回明确错误；记录 `budget_exceeded` | COST | READY |
| `TC-P6-RTR-007` | 便宜模型路径 | 摘要后仍高于 soft、但低于 hard | 选择 `cheaper_model`；模型在允许列表；记录路径 | COST | READY |
| `TC-P6-RTR-008` | 摘要确实减少 token | 同一输入分别走 direct 与 summarize | summarize 后的估算 input tokens 严格小于 direct；受保护证据集合不变 | COST | READY |
| `TC-P6-RTR-009` | 便宜模型确实更便宜 | 合成价格表：modelB 单价低于 modelA | 选择 cheaper_model 时记录 modelB；费用低于 modelA；质量门禁仍生效 | COST | READY |

---

## 8. L1 单元测试 — 成本监控与聚合

| ID | 目的 | 输入/步骤 | 期望 | 追溯 | 状态 |
|---|---|---|---|---|---|
| `TC-P6-MON-001` | 按 agent 聚合 | 3 个 agent 的 events | 每个 agent 的 prompt/completion/total 正确；总和一致 | COST | READY |
| `TC-P6-MON-002` | 按 model 聚合 | 两个 model 的 events | 每个 model 的 token/费用正确 | COST | READY |
| `TC-P6-MON-003` | 重试计入 | 含 retry 的 events | 重试 token 计入总量；`retry_count` 正确 | COST | READY |
| `TC-P6-MON-004` | 费用数学 | 合成价格表 + events | 费用 = input_tokens × cache_miss_price(phase) + output_tokens × output_price(phase)，除以 1M；CNY；误差 0（合成数据） | COST | READY |
| `TC-P6-MON-005` | usage 缺失回退 | 事件 usage=null | 使用估算；标记 `usage_source=estimated`；不崩溃 | COST | READY |
| `TC-P6-MON-006` | 价格表版本/来源 | 使用两版价格表 | 报告记录 `price_table_version`、`price_table_source`、`retrieved_at`；不同版本结果可区分 | COST | READY |
| `TC-P6-MON-007` | 报告覆盖率 | N 次运行，其中全部有报告 | `token_report_coverage == 1.0` | COST | READY |
| `TC-P6-MON-008` | 空事件集 | 0 条事件 | 报告 token=0、cost=0；不崩溃；标记空运行 | COST | READY |
| `TC-P6-MON-009` | p50/p95 计算 | 已知 1..100 的样本 | nearest-rank：p50=第 50 个值=50；p95=第 95 个值=95；与基准报告一致 | PER | READY |
| `TC-P6-MON-010` | 峰谷时段判断 | 固定时间戳：工作日 09:00/12:00/14:00/18:00；周六 | 09:00、14:00 为 peak；12:00、18:00、周六为 off_peak | COST | READY |
| `TC-P6-MON-011` | 峰谷价用于费用 | 同一 token 用量，两个时间戳分别 peak/off_peak | peak 费用高于 off_peak；金额与 CNY 单价表一致 | COST | READY |
| `TC-P6-MON-012` | 法定节假日判断 | 已知工作日节假日日期 | 不特殊处理；按工作日/时段规则（工作日峰段=peak，周末=off_peak）；记录 `holiday_policy=ignore` | COST | READY |
| `TC-P6-MON-013` | 多 run 隔离 | 同一 monitor 记录 r1/r2，分别 report | `report("r1")` 只含 r1 事件；`report("r2")` 只含 r2 事件；互不污染 | COST | READY |

---

## 9. L1/L2 失败路径测试

| ID | 目的 | 输入/步骤 | 期望 | 追溯 | 状态 |
|---|---|---|---|---|---|
| `TC-P6-FAIL-001` | 硬失败写记录 | 估算 > hard | 非零退出码；写 manifest + cost report；`status=budget_exceeded`；记录估算/实际/上限 | COST | READY |
| `TC-P6-FAIL-002` | 硬失败不产最终评级 | 同上 | `final_rating="REVIEW"`；不存在已提交的 Buy/Sell 等最终评级 | COST | READY |
| `TC-P6-FAIL-003` | 硬失败后无调用 | 同上 | 失败后 provider 调用次数不增加 | COST | READY |
| `TC-P6-FAIL-004` | Provider 错误/重试 | fake provider 返回 429/500 | 重试计数正确；最终失败被记录；token 用量仍可汇总 | COST/PER | READY |
| `TC-P6-FAIL-005` | 质量门禁失败回滚 | 路由后 quality=fail | 回滚到更高预算/direct；记录 `cost_route_reverted`；不静默接受低质量 | COST | READY |
| `TC-P6-FAIL-006` | usage 缺失仍出报告 | 事件 usage=null | 报告仍生成；标记 estimated；coverage 不下降 | COST | READY |

---

## 10. L2 集成测试（fake provider，不联网）

| ID | 目的 | 输入/步骤 | 期望 | 追溯 | 状态 |
|---|---|---|---|---|---|
| `TC-P6-INT-001` | Quick 端到端字段 | fake provider + Quick profile | manifest 含 token/cost/route；无真实网络 | COST | READY |
| `TC-P6-INT-002` | soft 路由集成 | fake provider + 合成 soft 阈值 | 触发 `summarize`；记录路径；受保护证据保留 | COST | READY |
| `TC-P6-INT-003` | 硬失败集成 | fake provider + 超硬上限 | 无 provider 调用；manifest status=budget_exceeded；无最终评级 | COST | READY |
| `TC-P6-INT-004` | 缓存命中 | Part 4 cache stub + 重复运行 | 第二次运行 token/latency 降低；cache_hit 被记录 | PER/COST | READY |
| `TC-P6-INT-005` | 质量门禁 | quality_pass / quality_fail stub | pass 正常；fail 回滚并记录 | COST | READY |
| `TC-P6-INT-006` | 每 run 独立 monitor | 同一个 runner 连续跑 r1/r2 | 第二次报告只含 r2 token，不累积 r1 | COST | READY |

---

## 11. L3/L4 真实基准与审计

### 11.1 延迟基准

| ID | 目的 | 输入/步骤 | 期望 | 追溯 | 状态 |
|---|---|---|---|---|---|
| `TC-P6-BEN-001` | 基准报告 schema | 运行 `bench_latency.py`（Quick/Standard 15+15，Deep 3+3） | 报告含 profile、cold/warm、p50/p95/p99、failure_rate、baseline、improvement；JSON 可解析 | PER | READY |
| `TC-P6-BEN-002` | Quick/Standard 相对改善 | 与 `baseline_report` 比较 | Quick、Standard 的 p95 改善均 ≥30% | PER | READY |
| `TC-P6-BEN-003` | Deep 记录 | Deep 3+3 | 记录 p50/p95/max；**不阻断**（样本不足） | PER | READY |
| `TC-P6-BEN-004` | p99 比率 | 从报告计算 p99/p95 | 记录比率；**不阻断** | PER | READY |
| `TC-P6-BEN-005` | 失败/超时率 | 统计基准运行 | 失败/超时率 **≤1% 阻断** | PER | READY |
| `TC-P6-BEN-006` | 绝对 p95 记录 | 从报告读取 Quick/Standard/Deep p95 | 记录数值；不阻断（已确认只做相对改善） | PER | READY |
| `TC-P6-BEN-007` | 相对改善公式 | baseline p95=100；current=69/71 | 69 视为改善 31%，通过；71 视为改善 29%，不通过 | PER | READY |
| `TC-P6-BEN-008` | 绝对 p95 warning | Deep p95 > 1800；require_improvement=False | 返回 warning，不抛异常；p95/p99 仍只记录 | PER | READY |
| `TC-P6-BEN-009` | 策略表 | Quick/Deep 默认策略 | Quick 要求 ≥30%；Deep 不要求；策略按 profile 查表 | PER | READY |

### 11.2 token/成本审计

| ID | 目的 | 输入/步骤 | 期望 | 追溯 | 状态 |
|---|---|---|---|---|---|
| `TC-P6-AUD-001` | 三档 token p95 上限 | 运行 `token_audit.py` | Quick p95 ≤80k；Standard ≤150k；Deep ≤300k | COST | READY |
| `TC-P6-AUD-002` | 报告覆盖 | 统计 30 次/可用样本 | 100% 运行有 token/费用报告 | COST | READY |
| `TC-P6-AUD-003` | 静默超预算 | 检查所有运行 | silent over-budget = 0 | COST | READY |
| `TC-P6-AUD-004` | 费用误差 | 报告费用 vs provider usage × 价格表（按事件时间选峰谷、cache miss） | **最坏一次运行**的相对误差 ≤5%；CNY；标注估算 | COST | READY |
| `TC-P6-AUD-005` | 路由质量门禁 | 检查路由运行 | 100% 通过 Part 2/3 质量门槛；否则回滚记录 | COST | READY |
| `TC-P6-AUD-006` | 价格表版本/币种/来源 | 检查报告 | `currency=CNY`；`price_table_version`、`price_table_source`、`retrieved_at` 存在 | COST | READY |
| `TC-P6-AUD-007` | 真实价格表 | 使用官方 DeepSeek 定价页（2026-11-16 读取） | Flash cache-miss 输入 1/2 元、输出 4/8 元；Pro 输入 4.5/9 元、输出 13.5/27 元；记录 source_url/retrieved_at/model_version | COST | READY |
| `TC-P6-AUD-008` | 费用误差取最坏运行 | 9 次 0% + 1 次 6% | `cost_relative_error == 0.06`；验收失败，不能被平均值掩盖 | COST | READY |

---

## 12. 追溯矩阵（摘要）

| 需求 | 关键指标 | 测试用例 |
|---|---|---|
| `REQ-PER-001` | 报告 schema | `TC-P6-BEN-001` |
| `REQ-PER-001` | Quick/Standard 相对改善 | `TC-P6-BEN-002` |
| `REQ-PER-001` | Deep 记录 | `TC-P6-BEN-003` |
| `REQ-PER-001` | p99 比率 | `TC-P6-BEN-004` |
| `REQ-PER-001` | 失败率 | `TC-P6-BEN-005` |
| `REQ-PER-001` | 绝对 p95 | `TC-P6-BEN-006` |
| `REQ-COST-001` | token p95 上限 | `TC-P6-AUD-001` |
| `REQ-COST-001` | 报告覆盖 | `TC-P6-AUD-002`、`TC-P6-MON-007` |
| `REQ-COST-001` | 静默超预算 | `TC-P6-AUD-003`、`TC-P6-RTR-006`、`TC-P6-FAIL-001` |
| `REQ-COST-001` | 费用误差 | `TC-P6-AUD-004`、`TC-P6-MON-004` |
| `REQ-COST-001` | 质量门禁 | `TC-P6-AUD-005`、`TC-P6-FAIL-005`、`TC-P6-INT-005` |
| `REQ-COST-001` | 价格表/币种/来源 | `TC-P6-AUD-006`、`TC-P6-MON-006` |
| `REQ-COST-001` | 事件/预算/路由/聚合 | `TC-P6-CON-*`、`TC-P6-EST-*`、`TC-P6-BUD-*`、`TC-P6-RTR-*`、`TC-P6-MON-*` |
| `REQ-COST-001` | soft 阈值来自配置 | `TC-P6-BUD-006` |
| `REQ-COST-001` | 摘要确实减少 token | `TC-P6-RTR-008` |
| `REQ-COST-001` | 便宜模型确实更便宜 | `TC-P6-RTR-009` |
| `REQ-COST-001` | 峰谷价 | `TC-P6-MON-010`、`TC-P6-MON-011` |
| `REQ-COST-001` | 节假日 | `TC-P6-MON-012` |
| `REQ-COST-001` | 多 run 隔离 | `TC-P6-MON-013`、`TC-P6-INT-006` |
| `REQ-PER-001` | percentile 计算 | `TC-P6-MON-009` |
| `REQ-PER-001` | 相对改善公式 | `TC-P6-BEN-007` |
| `REQ-PER-001` | 绝对 p95 warning | `TC-P6-BEN-008` |
| `REQ-PER-001` | 分档策略表 | `TC-P6-BEN-009` |
| `REQ-COST-001` | 真实价格表 | `TC-P6-AUD-007` |
| `REQ-COST-001` | 费用误差取最坏运行 | `TC-P6-AUD-004`、`TC-P6-AUD-008` |

---

## 13. TDD 执行顺序

1. **契约**：`TC-P6-CON-001..006` 先红后绿。
2. **估算**：`TC-P6-EST-001..006`。
3. **预算**：`TC-P6-BUD-001..006`。
4. **路由**：`TC-P6-RTR-001..009`。
5. **监控/成本**：`TC-P6-MON-001..013`。
6. **失败路径**：`TC-P6-FAIL-001..006`。
7. **集成（fake provider）**：`TC-P6-INT-001..006`。
8. **真实基准/审计**：`TC-P6-BEN-*`、`TC-P6-AUD-*`，手动/nightly。

每步完成标准：

- 新增测试先失败（红）；
- 实现后通过（绿）；
- 不破坏已有测试；
- 失败信息能直接指向 metric/threshold；
- 每个测试有对应需求 ID。

---

## 14. 测试完成定义（DoD）

- `REQ-PER-001`、`REQ-COST-001` 的每个指标都有至少一个测试用例。
- READY 用例全部有确定性输入、期望和追溯 ID。
- PENDING 用例集中列出，等待确认，不混入“必须通过”。
- L1/L2 不联网、不耗 token；L3/L4 手动运行并有报告。
- 测试用例可在确认后直接翻译为 pytest（函数名建议 `test_tc_p6_...`）。
- 没有“看起来对但无法判定”的断言。

---

## 15. 确认状态

当前**没有 PENDING 测试用例**。Q1–Q8 已确认：

- Q1 Deep 3+3：只记录，不阻断。
- Q2 p99：只记录，不阻断。
- Q3 失败率：≤1% 阻断。
- Q4 soft→hard：摘要优先；不足再便宜模型。
- Q5 硬失败 `final_rating`：`"REVIEW"`。
- Q6 价格表：DeepSeek 官方 CNY 定价；峰谷按时间；cache miss。
- Q7 p50/p95：nearest-rank。
- Q8 节假日：**忽略节假日**，只按工作日/时段；记录 `holiday_policy=ignore`。

价格页：`https://api-docs.deepseek.com/zh-cn/quick_start/pricing/`，2026-11-16 读取。  
注意：价格页可能调整；最终报告必须记录 `source_url`、`retrieved_at`、`model_version`、`price_table_version`。
