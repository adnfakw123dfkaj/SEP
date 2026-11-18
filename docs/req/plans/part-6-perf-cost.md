# Part 6 实现计划书 — 性能与成本

## 1. 基本信息

| 项 | 内容 |
|---|---|
| 负责组员 | 组员 F（待确认） |
| 覆盖需求 | `REQ-PER-001`（Must）、`REQ-COST-001`（Must） |
| 核心目标 | 让“慢”和“烧 token”变成可测量、可预算、可验收的指标 |
| 提供接口 | `LLMCallEvent`、`estimate_tokens()`、`BudgetPolicy`、`CostRouter`、`CostMonitor`、基准脚本 |
| 依赖接口 | `ProfileConfig`（Part 1）、`RunManifest`（Part 3）、provider adapter usage |
| 不负责 | 辩论/报告/缓存/安全内部；只测量、预算、路由和报告 |

## 2. 目标与非目标

### 目标

- 建立可重复的延迟基准：Quick/Standard/Deep，冷/热缓存各 15 次，p95/p99/失败率。
- 建立 token 预算与成本报告：按 agent/model/tool 拆分，超预算路由/审批，不静默超支。
- 给 Part 1/3 提供数据：profile 预算、manifest token/cost、fallback/路由事件。

### 非目标

- 不做实时计费系统；估算 + provider usage 足够。
- 不做跨 provider 价格优化；价格表可配置即可。
- 不修改业务提示词/辩论/报告；只通过路由和摘要影响成本。

## 3. 交付物

- 代码：
  - `tradingagents/contracts/llm_event.py`：`LLMCallEvent`。
  - `tradingagents/cost/estimator.py`：token 估算。
  - `tradingagents/cost/budget.py`：分档预算策略。
  - `tradingagents/cost/router.py`：直接/摘要/便宜模型/审批。
  - `tradingagents/cost/monitor.py`：实际用量、费用、quality floor。
  - `tradingagents/cost/pricing.py`：价格表。
  - `scripts/bench_latency.py`、`scripts/token_audit.py`。
- 测试：
  - `tests/contracts/test_llm_event_contract.py`
  - `tests/req/test_latency.py`（或脚本断言）
  - `tests/req/test_token_budget.py`
- 文档/证据：
  - 基线报告（Phase 0）。
  - 30 次延迟报告。
  - token/费用报告。
  - 超预算路由样例。

## 4. 预算与指标（第 1 周冻结）

| Profile | token 目标（p95） | token 上限（验收） | 延迟目标 p95 | 延迟验收 p95 |
|---|---:|---:|---:|---:|
| Quick | 20k | 25k | 4 min | 5 min |
| Standard | 50k | 60k | 10 min | 12 min |
| Deep | 120k | 150k | 25 min | 30 min |

规则：

- token = provider 返回的 input + output，含重试；不含本地工具解析。
- 费用 = 价格表 × token；误差 ≤5%。
- 超预算路径：摘要 -> 便宜模型 -> 审批/降级；不得静默继续。
- 路由后质量必须满足 Part 2/3 的质量门槛，否则回滚预算。

## 5. 工作分解

### Week 1：契约与基线

- 定义 `LLMCallEvent`，与 provider adapter 对齐字段。
- 建立 `scripts/bench_latency.py` 骨架：profile、cold/warm、p95/p99、失败率。
- 建立 `scripts/token_audit.py` 骨架：按 agent/model 拆分。
- 跑 Phase 0 基线：market-only、market+social、默认四分析师各 1-3 次。
- 定义价格表和费用计算。
- 交付：契约 + 基线报告 + 脚本骨架。

### Week 2：估算、预算、路由

- 实现 `estimate_tokens()`：基于 tokenizer/历史统计；给出输入/输出上限。
- 实现 `BudgetPolicy`：读取 `ProfileConfig` 的 token/timeout。
- 实现 `CostRouter`：直接/摘要/便宜模型/审批；摘要必须保留受保护证据。
- 实现 `CostMonitor`：记录实际 usage、费用、路由事件。
- 与 Part 3 对齐 manifest 的 `token_usage_by_agent`、`cost_estimate`。
- 交付：一次运行产出 token/费用报告。

### Week 3：基准与质量门禁

- 跑 30 次基准（Quick/Standard/Deep 各 10 或按需求 15+15）。
- 跑 token audit：p95、超预算、费用误差。
- 加 quality floor：路由运行必须通过 Part 2/3 的质量阈值。
- 与 Part 1/4 联调：profile、缓存、早停对延迟的影响。
- 交付：`REQ-PER-001`、`REQ-COST-001` 首次验收。

### Week 4：调优与收尾

- 调整预算/路由阈值；记录与基线的对比。
- 修复超预算/质量回退问题。
- 补文档：如何新增 profile 预算、如何更新价格表、如何跑基准。
- 准备演示：Quick vs Standard 延迟/成本对比；超预算被路由。
- 交付：验收报告 + 演示脚本。

## 6. 验收与测试

| 需求 | 验收命令 | 证据 |
|---|---|---|
| `REQ-PER-001` | `python scripts/bench_latency.py --profile quick --cold 15 --warm 15 --assert-p95 300` | Quick 延迟报告 |
| `REQ-PER-001` | `python scripts/bench_latency.py --profile standard --cold 15 --warm 15 --assert-p95 720` | Standard 延迟报告 |
| `REQ-PER-001` | `python scripts/bench_latency.py --profile deep --cold 15 --warm 15 --assert-p95 1800` | Deep 延迟报告 |
| `REQ-PER-001` | `python scripts/bench_latency.py --assert-p99-ratio 1.2 --assert-failure-rate 0.01` | p99/失败率 |
| `REQ-PER-001` | `python scripts/bench_latency.py --baseline reports/baseline.json --assert-improvement 0.30` | 改善比例 |
| `REQ-COST-001` | `python scripts/token_audit.py --profile quick --runs 30 --assert-p95 25000` | Quick token 报告 |
| `REQ-COST-001` | `python scripts/token_audit.py --profile standard --runs 30 --assert-p95 60000` | Standard token 报告 |
| `REQ-COST-001` | `python scripts/token_audit.py --profile deep --runs 30 --assert-p95 150000` | Deep token 报告 |
| `REQ-COST-001` | `python scripts/token_audit.py --runs 30 --assert-report-coverage 1.0 --assert-silent-over-budget 0` | 覆盖率/超预算 |
| `REQ-COST-001` | `python scripts/token_audit.py --assert-cost-error 0.05 --assert-routed-quality 1.0` | 费用/质量 |

## 7. 风险与回退

| 风险 | 缓解 | 回退 |
|---|---|---|
| Provider 延迟波动大 | 固定环境、记录网络、p95、多轮重测 | 放宽阈值并记录，不伪造数据 |
| token 计数 provider 差异 | 以 provider usage 为准；估算只做预警 | 费用报告标注“估算” |
| 预算过紧导致质量下降 | 质量门禁 + 回滚预算 + 审批 | 提高预算，记录 tradeoff |
| 路由摘要丢失关键证据 | 受保护证据白名单（snapshot/引用/风控约束） | 禁用摘要，改用便宜模型 |
| 基准运行消耗配额 | 用录制数据做确定性测试；真实调用只跑必要 30 次 | 减少样本，延长周期 |

## 8. Definition of Done

- 三档 p95 延迟达到阈值，p99/失败率达标，Quick/Standard 改善 ≥30%。
- 三档 p95 token 达到上限，100% 运行有 token/费用报告，静默超预算 = 0。
- 超预算路由运行通过质量门禁，否则回滚并记录。
- `LLMCallEvent` 被 Part 3 manifest 正确消费。
- OpenCode 会话记录、基准报告、token 报告已归档。

## 9. 集成交接清单

- [ ] `LLMCallEvent` 契约冻结。
- [ ] 提供 `estimate_tokens(messages, model) -> TokenEstimate`。
- [ ] 提供 `BudgetPolicy.for_profile(profile) -> Budget`。
- [ ] 提供 `CostRouter.route(context, budget) -> RouteDecision`。
- [ ] 提供 `CostMonitor.record(event)` / `summarize(run_id) -> CostReport`。
- [ ] 提供 `scripts/bench_latency.py` 和 `scripts/token_audit.py` 的使用说明。
- [ ] 在 `tests/contracts/` 增加 LLMCallEvent 契约测试。
