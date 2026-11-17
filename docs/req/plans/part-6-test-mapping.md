# Part 6 测试代码与需求映射

- 测试代码目录：`tradingagents/tests/part6/`
- 对应测试规格：`docs/req/plans/part-6-test-cases.md`
- 对应需求：`REQ-PER-001`、`REQ-COST-001`
- 当前状态：**TDD 红阶段**。测试已写好，但被测模块尚未实现，因此 collection 报 `ModuleNotFoundError`，这是预期结果。

---

## 1. `test_contracts.py` — 契约

| 测试函数 | TC ID | 为什么这样写 | 对应指标 |
|---|---|---|---|
| `test_tc_p6_con_001_event_required_fields` | `TC-P6-CON-001` | 先固定事件字段，后面聚合、manifest、审计都依赖它；字段缺失时应在入口失败，而不是让报表出现空值 | 事件 schema |
| `test_tc_p6_con_002_token_sum_consistency` | `TC-P6-CON-002` | 如果 total 与 input+output 不一致，费用和 p95 会同时错；用 Pydantic 校验把错误挡在入口 | token 一致性 |
| `test_tc_p6_con_003_status_and_route_enums` | `TC-P6-CON-003` | status/route 是机器分支依据；必须封闭枚举，防止 `"direct "`、`"Direct"` 等脏值进入报告 | 枚举闭包 |
| `test_tc_p6_con_004_token_estimate_structure` | `TC-P6-CON-004` | 估算结果也要自洽；否则路由会把错误的估算当成预算依据 | token 估算结构 |
| `test_tc_p6_con_005_budget_structure` | `TC-P6-CON-005` | 预算必须是 CNY 且 soft<=hard；否则路由边界无意义 | 预算 schema |
| `test_tc_p6_con_006_cost_report_structure` | `TC-P6-CON-006` | 报告要能被 manifest/审计直接消费，必须包含币种、价格表来源、峰谷/缓存策略 | 成本报告 schema |

## 2. `test_estimator.py` — token 估算

| 测试函数 | TC ID | 为什么这样写 | 对应指标 |
|---|---|---|---|
| `test_tc_p6_est_001_normal_prompt` | `TC-P6-EST-001` | 先保证普通输入能返回非负且自洽的估算；这是路由的最低前提 | 估算基本正确性 |
| `test_tc_p6_est_002_empty_and_tiny_input` | `TC-P6-EST-002` | 空输入不能被算成负数或异常；真实运行会出现空上下文/空工具结果 | 边界输入 |
| `test_tc_p6_est_003_long_context_grows` | `TC-P6-EST-003` | 长上下文必须估算更大，否则摘要/预算路由会失效 | 单调性 |
| `test_tc_p6_est_004_unknown_model_falls_back` | `TC-P6-EST-004` | 自定义/新模型可能没有精确 tokenizer；应回退并降低置信度，而不是崩溃 | 回退与置信度 |
| `test_tc_p6_est_005_is_deterministic` | `TC-P6-EST-005` | 同一输入重复估算必须稳定，否则测试和预算决策不可复现 | 确定性 |
| `test_tc_p6_est_006_respects_output_cap` | `TC-P6-EST-006` | 输出上限是硬约束；估算超过上限会导致预算误判 | 输出上限 |

## 3. `test_budget.py` — 分档预算

| 测试函数 | TC ID | 为什么这样写 | 对应指标 |
|---|---|---|---|
| `test_tc_p6_bud_001_profile_hard_limits` | `TC-P6-BUD-001` | 三档硬上限是验收门槛，必须在预算对象里可直接读取 | Quick/Standard/Deep 硬上限 |
| `test_tc_p6_bud_002_soft_and_hard_boundaries` | `TC-P6-BUD-002` | 路由依赖 soft/hard 边界；`80` 应算达到 soft，`100` 应算达到 hard，避免差一错误 | 边界语义 |
| `test_tc_p6_bud_003_unknown_profile_rejected` | `TC-P6-BUD-003` | 未知 profile 静默回退会掩盖配置错误；必须明确失败 | 配置错误 |
| `test_tc_p6_bud_004_invalid_budget_rejected` | `TC-P6-BUD-004` | 负数、0、soft>hard 都不能进入路由 | 非法预算 |
| `test_tc_p6_bud_005_currency_is_cny` | `TC-P6-BUD-005` | 官方价格页是 CNY；如果这里写成 USD，整份费用报告会错 | 币种 |
| `test_tc_p6_bud_006_soft_limit_comes_from_profile_config` | `TC-P6-BUD-006` | soft 阈值必须由 Part 1 的 ProfileConfig 提供，不能在 Part 6 硬编码 | 配置来源 |

## 4. `test_router.py` — 路由与受保护证据

| 测试函数 | TC ID | 为什么这样写 | 对应指标 |
|---|---|---|---|
| `test_tc_p6_rtr_001_within_soft_goes_direct` | `TC-P6-RTR-001` | 预算内不应做无意义摘要/换模型；直接路径是基准行为 | direct |
| `test_tc_p6_rtr_002_between_soft_and_hard_summarizes` | `TC-P6-RTR-002` | 你已确认 soft→hard 优先摘要；测试固定这个顺序 | summarize 优先 |
| `test_tc_p6_rtr_003_over_hard_fails_fast` | `TC-P6-RTR-003` | 超硬上限必须 hard_fail，不能先调用再发现 | hard_fail |
| `test_tc_p6_rtr_004_summary_preserves_protected_evidence` | `TC-P6-RTR-004` | 摘要只能压缩普通上下文，不能删除快照、引用、风控约束、评级输入 | 受保护证据 |
| `test_tc_p6_rtr_005_route_records_path_and_reason` | `TC-P6-RTR-005` | 审计需要知道“为什么走这条路”，不能只记录结果 | 路由证据 |
| `test_tc_p6_rtr_006_over_hard_is_not_silent` | `TC-P6-RTR-006` | 超预算必须显式失败；静默继续会直接违反成本需求 | 不静默超支 |
| `test_tc_p6_rtr_007_after_summary_uses_cheaper_model` | `TC-P6-RTR-007` | 摘要后仍高于 soft、低于 hard 时，才进入便宜模型路径 | 路由顺序 |
| `test_tc_p6_rtr_008_summary_reduces_context` | `TC-P6-RTR-008` | 摘要必须是“真压缩”，不能只改字段名；同时保留受保护证据 | 摘要有效性 |
| `test_tc_p6_rtr_009_cheaper_model_is_actually_cheaper` | `TC-P6-RTR-009` | 便宜模型必须真的单价更低，不能只是名字叫 cheap | 便宜模型选择 |

## 5. `test_monitor.py` — 聚合、峰谷、百分位

| 测试函数 | TC ID | 为什么这样写 | 对应指标 |
|---|---|---|---|
| `test_tc_p6_mon_001_aggregates_by_agent` | `TC-P6-MON-001` | 成本要按 agent 拆分，否则无法知道谁在烧 token | by_agent |
| `test_tc_p6_mon_002_aggregates_by_model` | `TC-P6-MON-002` | 按模型拆分才能比较 quick/deep 成本 | by_model |
| `test_tc_p6_mon_003_retry_tokens_are_included` | `TC-P6-MON-003` | 重试也花钱；不计入会低估真实成本 | retry tokens |
| `test_tc_p6_mon_004_cost_math_uses_phase_and_cache_miss` | `TC-P6-MON-004` | 费用公式必须用 cache miss 价 + 峰谷价，除以 1M；这是官方计费规则 | 费用数学 |
| `test_tc_p6_mon_005_missing_usage_falls_back` | `TC-P6-MON-005` | provider 不给 usage 时仍要出报告；标记 estimated，不能丢运行 | usage 回退 |
| `test_tc_p6_mon_006_price_table_provenance` | `TC-P6-MON-006` | 报告必须能追溯到价格表版本/来源，否则历史费用不可复现 | 价格表 provenance |
| `test_tc_p6_mon_007_report_coverage` | `TC-P6-MON-007` | 100% 运行有报告是验收条件；覆盖率必须可计算 | 报告覆盖 |
| `test_tc_p6_mon_008_empty_event_set` | `TC-P6-MON-008` | 空运行应输出 0，而不是崩溃或 NaN | 空集合 |
| `test_tc_p6_mon_009_nearest_rank_percentile` | `TC-P6-MON-009` | 你已确认 nearest-rank；p50/p95 必须按同一规则，否则 p95 不可比 | percentile |
| `test_tc_p6_mon_010_price_phase_weekday_and_weekend` | `TC-P6-MON-010` | 峰谷判断是费用公式的输入；固定时间戳避免时区歧义 | 峰谷判断 |
| `test_tc_p6_mon_011_peak_costs_more_than_off_peak` | `TC-P6-MON-011` | 同样 token 在高峰必须更贵；这是峰谷价是否真正生效的端到端检查 | 峰谷费用 |
| `test_tc_p6_mon_012_holidays_are_ignored` | `TC-P6-MON-012` | 你已确认忽略节假日；测试锁定 `holiday_policy=ignore`，避免以后偷偷加逻辑 | 节假日策略 |
| `test_tc_p6_mon_013_reports_are_isolated_by_run_id` | `TC-P6-MON-013` | 共享 monitor 时 report 必须按 run_id 过滤，否则后一次报告会累积前一次 token | 多 run 隔离 |

## 6. `test_failure.py` — 硬失败/重试/质量门禁

| 测试函数 | TC ID | 为什么这样写 | 对应指标 |
|---|---|---|---|
| `test_tc_p6_fail_001_hard_fail_writes_record` | `TC-P6-FAIL-001` | 硬失败不是“什么都不留”；必须写记录、非零退出、可审计 | 硬失败记录 |
| `test_tc_p6_fail_002_hard_fail_has_no_committed_rating` | `TC-P6-FAIL-002` | 已确认硬失败用 `REVIEW`，不能偷偷给 Buy/Sell | 最终评级 |
| `test_tc_p6_fail_003_hard_fail_does_not_call_provider` | `TC-P6-FAIL-003` | 硬失败必须在调用前发生；否则“硬失败”仍会花钱 | 调用前停止 |
| `test_tc_p6_fail_004_provider_failure_is_recorded` | `TC-P6-FAIL-004` | provider 失败/重试仍要记账，否则失败运行的 token 会消失 | 失败记账 |
| `test_tc_p6_fail_005_quality_floor_reverts_route` | `TC-P6-FAIL-005` | 路由后质量不达标必须回滚，不能用低质量换低成本 | 质量门禁 |
| `test_tc_p6_fail_006_missing_usage_still_has_coverage` | `TC-P6-FAIL-006` | usage 缺失不能降低报告覆盖率 | 覆盖率 |

## 7. `test_integration.py` — 组合门面

| 测试函数 | TC ID | 为什么这样写 | 对应指标 |
|---|---|---|---|
| `test_tc_p6_int_001_quick_run_writes_manifest_fields` | `TC-P6-INT-001` | 验证 direct 运行的 manifest 字段能被 Part 3 直接消费 | manifest 集成 |
| `test_tc_p6_int_002_soft_route_uses_summarize` | `TC-P6-INT-002` | 验证 soft→hard 的摘要路径在组合层真实生效 | 摘要集成 |
| `test_tc_p6_int_003_hard_fail_has_no_provider_call` | `TC-P6-INT-003` | 验证组合层在硬失败时不会先调用 provider | 硬失败集成 |
| `test_tc_p6_int_004_cache_hit_is_visible` | `TC-P6-INT-004` | 缓存命中必须进入 manifest 并降低 token | 缓存收益 |
| `test_tc_p6_int_005_quality_floor_failure_reverts_route` | `TC-P6-INT-005` | 验证质量门禁在组合层会回滚路由并记录 | 质量门禁集成 |
| `test_tc_p6_int_006_runner_creates_a_fresh_monitor_per_run` | `TC-P6-INT-006` | 同一个 runner 连续运行必须使用独立 monitor，防止第二次报告累积第一次 token | monitor 生命周期 |

## 8. `test_benchmark.py` — 延迟报告

| 测试函数 | TC ID | 为什么这样写 | 对应指标 |
|---|---|---|---|
| `test_tc_p6_ben_001_report_schema` | `TC-P6-BEN-001` | 15+15 的报告要包含 p50/p95/p99/failure/baseline/improvement | 报告 schema |
| `test_tc_p6_ben_002_quick_standard_relative_improvement` | `TC-P6-BEN-002` | 你已确认只做相对改善；Quick/Standard ≥30% 是主延迟门槛 | 相对改善 |
| `test_tc_p6_ben_003_deep_is_record_only` | `TC-P6-BEN-003` | Deep 3+3 样本不足，只记录不阻断 | Deep 记录 |
| `test_tc_p6_ben_004_p99_is_recorded_not_blocking` | `TC-P6-BEN-004` | p99 只记录，不阻断；测试锁住这个决定 | p99 |
| `test_tc_p6_ben_005_failure_rate_blocks` | `TC-P6-BEN-005` | 失败率 >1% 阻断，避免基准本身不可用 | 失败率 |
| `test_tc_p6_ben_006_absolute_p95_is_recorded` | `TC-P6-BEN-006` | 绝对 p95 只记录；测试防止以后误改为阻断 | 绝对 p95 |
| `test_tc_p6_ben_007_improvement_formula` | `TC-P6-BEN-007` | 改善公式必须明确：100→69 是 31%，100→71 是 29% | 改善公式 |
| `test_tc_p6_ben_008_absolute_p95_warns_without_blocking` | `TC-P6-BEN-008` | 绝对 p95 超目标只 warning，不阻断；区分“慢”与“不可用” | 绝对 p95 warning |
| `test_tc_p6_ben_009_policy_table_controls_profile_defaults` | `TC-P6-BEN-009` | 用策略表锁定 Quick 必须改善、Deep 只记录，避免调用方写错 flag | 分档策略 |

## 9. `test_audit.py` — token/成本审计

| 测试函数 | TC ID | 为什么这样写 | 对应指标 |
|---|---|---|---|
| `test_tc_p6_aud_001_token_p95_caps` | `TC-P6-AUD-001` | 三档 token p95 上限是成本验收核心 | token p95 |
| `test_tc_p6_aud_002_report_coverage` | `TC-P6-AUD-002` | 少一份报告就无法审计；覆盖率必须 100% | 报告覆盖 |
| `test_tc_p6_aud_003_no_silent_over_budget` | `TC-P6-AUD-003` | 静默超预算必须为 0，否则成本控制形同虚设 | 静默超预算 |
| `test_tc_p6_aud_004_cost_error` | `TC-P6-AUD-004` | 费用误差 ≤5%；用独立 ground truth 验证公式/取价 | 费用误差 |
| `test_tc_p6_aud_005_routed_quality_floor` | `TC-P6-AUD-005` | 路由运行必须通过质量门禁，不能低成本低质量 | 质量门禁 |
| `test_tc_p6_aud_006_price_table_provenance` | `TC-P6-AUD-006` | 报告必须记录 CNY、价格表版本和来源 | 价格表 provenance |
| `test_tc_p6_aud_007_real_deepseek_price_table` | `TC-P6-AUD-007` | 把官方价格页的 CNY 单价写进测试，防止实现用错价/用 USD | 真实价格表 |
| `test_tc_p6_aud_008_cost_error_uses_worst_run` | `TC-P6-AUD-008` | 费用误差取最坏运行，避免 1 次 6% 被 9 次 0% 平均掉 | 费用误差口径 |

---

## 10. Step 10a 回调采集测试（8 个，实施层）

这些不是 69 条需求验收用例的一部分，而是验证“真实 provider 调用 -> `LLMCallEvent`”的集成管道。

| 测试函数 | TC ID | 为什么这样写 | 对应 |
|---|---|---|---|
| `test_tc_p6_cap_001_chat_model_usage_event` | `TC-P6-CAP-001` | 真实 provider usage 必须变成结构化事件；字段缺失会让后续成本报表失真 | 事件采集 |
| `test_tc_p6_cap_002_fallback_estimation` | `TC-P6-CAP-002` | provider 不返回 usage 时，必须回退估算并标记 `usage_source=estimated`，不能丢事件 | usage 回退 |
| `test_tc_p6_cap_003_error_event` | `TC-P6-CAP-003` | provider 失败也要有可审计事件，失败运行的 token/latency 才能解释 | 失败事件 |
| `test_tc_p6_cap_004_plain_llm_and_model_extraction` | `TC-P6-CAP-004` | 非 chat 调用、`usage` 键、`model` 键也要兼容，避免只支持一种 provider 形态 | 兼容性 |
| `test_tc_p6_cap_005_default_and_scope` | `TC-P6-CAP-005` | scope 外使用默认 agent，scope 内覆盖；保证真实 graph 可以按节点归因 | agent 默认/覆盖 |
| `test_tc_p6_cap_006_nested_scope_restores` | `TC-P6-CAP-006` | 嵌套 scope 必须恢复外层，避免父节点被内层 agent 永久覆盖 | 嵌套恢复 |
| `test_tc_p6_cap_007_threads_do_not_leak_agent_context` | `TC-P6-CAP-007` | 并行分析师在不同线程运行时，agent 名不能串 | 并行隔离 |
| `test_tc_p6_cap_008_with_agent_scope_wrapper` | `TC-P6-CAP-008` | 节点包装器不改变函数名/返回值，只负责设置 scope | 节点接线 |

对应实现：`tradingagents/cost/callback.py`、`tradingagents/cost/agent_context.py`。

## 11. Step 10b CLI 测试（4 个，实施层）

| 测试函数 | TC ID | 为什么这样写 | 对应 |
|---|---|---|---|
| `test_tc_p6_cli_001_bench_latency_passes` | `TC-P6-CLI-001` | 离线样本应能生成通过报告，并写 JSON 文件 | 延迟 CLI |
| `test_tc_p6_cli_002_bench_latency_fails` | `TC-P6-CLI-002` | 门槛失败时返回非零，但仍写报告，便于审计 | 延迟 CLI 失败 |
| `test_tc_p6_cli_003_token_audit_passes_with_alias` | `TC-P6-CLI-003` | 验证 `--events-jsonl` 别名和 token audit 通过路径 | token CLI |
| `test_tc_p6_cli_004_token_audit_fails` | `TC-P6-CLI-004` | 静默超预算必须让 CLI 返回非零 | token CLI 失败 |

对应实现：`tradingagents/cost/cli.py`、`scripts/bench_latency.py`、`scripts/token_audit.py`。

## 12. 当前状态

- 需求验收测试：69 个，全部通过。
- 实施层回调测试：8 个，全部通过。
- 实施层 CLI 测试：4 个，全部通过。
- 合计：**81 passed**。
- 已实现模块：
  - `contracts/llm_event.py`、`contracts/cost.py`
  - `cost/estimator.py`、`budget.py`、`router.py`、`monitor.py`
  - `cost/report.py`、`enforcement.py`、`runner.py`
  - `cost/benchmark.py`、`audit.py`、`pricing.py`
  - `cost/callback.py`、`agent_context.py`、`cli.py`
  - `scripts/bench_latency.py`、`scripts/token_audit.py`
- 尚未完成：
  - 用现有 graph + callback 的真实 smoke
  - 与 Part 1/3/4 的最终接线
  - Quick/Standard 15+15、Deep 3+3 真实基准
