# Part 6 性能与成本基线（未优化）

- 日期：2026-11-16
- 状态：baseline 已记录；暂不优化，等待 Part 1–5 到位后做 before/after 对比
- 目的：保留“优化前”真实数据，最终报告与 25k/60k/150k 目标、优化后数据三方对比
- 说明：本文是 tracked 证据摘要；原始 JSON 在 `tradingagents/reports/part6/`，该目录被 `.gitignore` 忽略

## 1. 运行配置

| 项 | 值 |
|---|---|
| Ticker | NVDA |
| Trade date | 2026-11-14 |
| 分析师 | `market` only |
| 下游阶段 | 仍执行 Bull/Bear、Research Manager、Trader、Risk、Portfolio Manager |
| quick model | `deepseek-flash` |
| deep model | `deepseek-flash` |
| max_tool_rounds | 2 |
| max_debate_rounds | 1 |
| max_risk_discuss_rounds | 1 |
| max_tokens | 4096 |
| checkpoint | off |
| 环境 | 本机；DeepSeek 官方 API；CNY 价格表 `deepseek-cny-2026-11-16` |

## 2. 两次真实运行

| 指标 | Run 1 | Run 2（事件明细 baseline） |
|---|---:|---:|
| run_id | `smoke-1794905824` | `smoke-1794906281` |
| 决策 | Sell | Underweight |
| 墙钟时间 | 348.27s | 296.48s |
| LLM 调用数 | 11 | 11 |
| prompt tokens | 104,199 | 90,613 |
| completion tokens | 55,671 | 45,040 |
| total tokens | 159,870 | 135,653 |
| 估算费用 | 0.653766 CNY | 0.541546 CNY |
| Quick soft target | 20,000 | 20,000 |
| Quick hard cap | 25,000 | 25,000 |
| 是否超预算 | 是 | 是 |
| 超出硬上限 | 6.39× | 5.43× |
| by_agent | unknown | unknown |
| by_tool | unknown | unknown |

观察：

- 同一配置两次运行 total tokens 相差约 **17.9%**，费用相差约 **20.7%**，延迟相差约 **17.5%**。
- 因此 baseline 不应只取一次；至少记录两次，最终报告说明 run-to-run variance。

## 3. Run 2 逐次调用（事件明细 baseline）

| # | prompt | completion | total | latency | 推测阶段 |
|---:|---:|---:|---:|---:|---|
| 1 | 2,013 | 141 | 2,154 | 1.5s | Market Analyst 首轮 |
| 2 | 12,005 | 454 | 12,459 | 2.4s | Market Analyst 工具轮 |
| 3 | 13,768 | 8,228 | 21,996 | 46.3s | Market Analyst 报告 |
| 4 | 5,639 | 4,211 | 9,850 | 28.9s | Bull Researcher |
| 5 | 10,008 | 7,054 | 17,062 | 47.7s | Bear Researcher |
| 6 | 5,376 | 4,546 | 9,922 | 30.2s | Research Manager |
| 7 | 7,891 | 743 | 8,634 | 5.1s | Trader |
| 8 | 6,180 | 4,874 | 11,054 | 33.9s | Aggressive Risk |
| 9 | 8,951 | 7,294 | 16,245 | 50.3s | Conservative Risk |
| 10 | 11,518 | 3,861 | 15,379 | 27.9s | Neutral Risk |
| 11 | 7,264 | 3,634 | 10,898 | 21.4s | Portfolio Manager |

*阶段是根据调用顺序推测；`agent_name` 目前为 `unknown`，因为 Part 1 尚未把节点包上 `with_agent_scope`。*

## 4. 阶段汇总（Run 2）

| 阶段 | total tokens | 占比 |
|---|---:|---:|
| Market Analyst（1–3） | 36,609 | 27.0% |
| Debate + Manager（4–7） | 45,468 | 33.5% |
| Risk + PM（8–11） | 53,576 | 39.5% |
| **总计** | **135,653** | **100%** |

关键事实：

- **Market Analyst 单独 36,609**，已经超过 Quick hard cap 25,000。
- 即使 Quick 只跑 market、不做辩论/风控/PM，仍会超过 25k。
- prompt 总计 90,613（66.8%），completion 总计 45,040（33.2%）。
- 说明需要同时做“减少调用/上下文”和“限制输出”，而不是只调 max_tokens。

## 5. 与目标对比

| Profile | soft target | hard cap | baseline (Run 2) | 是否达标 |
|---|---:|---:|---:|---|
| Quick | 20,000 | 25,000 | 135,653 | 否（5.43×） |
| Standard | 50,000 | 60,000 | 未测 | 待测 |
| Deep | 120,000 | 150,000 | 未测 | 待测 |

> 本次只测 Quick 的 market-only 配置；Standard/Deep 需要 Part 1 的档位定义后再测。

## 6. 基线限制（必须在最终报告说明）

- `by_agent` / `by_tool` 为 `unknown`：
  - Part 1 尚未在 graph 节点包 `with_agent_scope`；
  - callback 不知道 tool 名。
- `quality_floor_pass=True` 是 smoke 脚本手动传入，不是真实 Part 2 质量评估。
- `route_paths=["direct"]` 是 callback 默认值，没有真正经过 Part 6 router。
- 没有真实缓存命中；`cache_policy` 固定为 cache miss。
- 未启用 Part 6 的 summarizer / cheaper model 路由。
- 本机环境，不是参考环境；绝对延迟只记录，不做硬门槛。

这些限制让本次数据成为**未优化 baseline**，不是 Part 6 最终验收结果。

## 7. 复现命令

在 `tradingagents/` 目录下：

```powershell
$env:SEP_API_KEY=[Environment]::GetEnvironmentVariable('SEP_API_KEY','User')
..\.venv\Scripts\python.exe scripts\smoke_cost_tracking.py `
  --ticker NVDA `
  --date 2026-11-14 `
  --max-tool-rounds 2 `
  --out reports\part6\smoke_events.json
```

## 8. 后续对比计划

最终报告建议使用三列对比：

| 指标 | Baseline | Optimized | Target |
|---|---:|---:|---:|
| total tokens | 135,653（Run 2） | 待测 | ≤25k Quick |
| prompt tokens | 90,613 | 待测 | - |
| completion tokens | 45,040 | 待测 | - |
| wall time | 296.48s | 待测 | relative improvement |
| cost CNY | 0.541546 | 待测 | - |
| quality | 手动抽查 | 待测 | Part 2/3 指标 |

优化必须等 Part 1/2/4 或明确的实验 harness；当前不修改 25k/60k/150k 目标。
