# Part 4 完成情况记录：数据韧性与时点完整性

更新日期：2026-11-21
计划书：[part-4-resilience.md](plans/part-4-resilience.md)

## 完成概况

Part 4 已完成核心数据缓存、供应商失败降级、fallback 事件记录和时点保护的可运行实现，并通过全项目自动测试。由于 ProfileConfig 和 Part 3 完整 manifest 流程尚未在仓库中落地，以下两项集成仍保留为明确的后续事项，不据此宣称 Part 4 所有原始计划项均已完成。

## 已完成

### 缓存契约与控制器

- `CacheKey`、`CacheEntry`、`TTLPolicy` 契约已实现，缓存条目保存来源信息与过期时间。
- 本地文件缓存支持过期拒绝、原子写入、跨进程文件锁，以及同一个 key 并发 `get_or_fetch` 去重。
- 默认 TTL 覆盖价格/技术指标 15 分钟、新闻/社交 60 分钟、基本面 24 小时、身份 7 天；价格策略提供盘后 24 小时选项。
- 不可用和无数据标记不会被当作有效数据缓存。

### 数据路径与降级

- 共享 vendor router 已接入缓存。key 包含请求参数、请求日期、供应商配置和实现标识，避免不同日期或供应商配置误命中。
- Reddit 与 StockTwits 的 sentiment 路径已单独接入 60 分钟缓存，按标的、历史窗口与筛选状态区分；不可用结果不保留在缓存中。
- 已实现 `RetryPolicy`、`FallbackRouter`、typed `FailureEvent` 和 `FallbackDecision`。无可用数据时明确返回 unavailable/REVIEW 信息，不编造数据。
- CLI 与程序化 graph 运行会收集 fallback events，将其放入最终 state，并在日志目录写出 Part 4 run manifest。

### 检查点与时点完整性

- 沿用已有 SQLite LangGraph checkpointer；Part 4 验收测试模拟节点成功后进程中断，再恢复执行，并验证已完成节点没有重复运行。
- 历史日期测试覆盖 100 个日期；日期窗口边界、未来数据过滤和历史 live-only 数据 withholding 也有测试。
- 新增数据路径与缓存策略文档：[part-4-data-paths.md](part-4-data-paths.md)。

## 验证结果

使用仓库内 Python 3.12 虚拟环境运行全项目测试：

```text
1716 passed, 33 skipped, 24 warnings
```

被跳过的测试按项目 pytest 配置和测试条件跳过。全套测试中需要绑定本机 loopback 的 ChatGPT 登录回调测试，需在允许本机回环套接字的环境运行；授权后通过。Part 4 专项测试、相关数据 router、checkpoint 生命周期及 graph 集成测试均通过。

主要新增/更新测试：

- `tradingagents/tests/contracts/test_cache_contract.py`
- `tradingagents/tests/req/test_cache.py`
- `tradingagents/tests/req/test_fallback.py`
- `tradingagents/tests/req/test_checkpoint_resume.py`
- `tradingagents/tests/req/test_point_in_time.py`
- `tradingagents/tests/test_data_router_cache.py`
- `tradingagents/tests/test_cli_display.py`

## 未完成与依赖

1. **Standard/Deep profile 默认 checkpoint**：当前仓库没有可用的 ProfileConfig；现有 checkpoint 仍按 `checkpoint_enabled` 配置启用，默认关闭。待 Part 1 提供 profile 配置入口后，可按 profile 设置默认值。
2. **统一 Part 3 manifest**：Part 4 已写出自身包含 fallback events 的 JSON manifest；RunManifest 的完整模型/成本/供应商版本等记录及其统一写入流程仍需与 Part 3 集成。
3. **TTL 市场状态判断**：盘后 TTL 策略有实现，但当前按简单美东工作日和交易时段判断，没有接入交易所节假日日历。
4. **运行指标证据**：尚未归档重复运行网络调用基线、生产缓存命中率报告、故障注入日志和演示录屏/会话记录；单元测试验证了缓存命中、过期、并发和故障降级行为。

## 实现文件

- `tradingagents/tradingagents/contracts/cache.py`
- `tradingagents/tradingagents/cache/__init__.py`
- `tradingagents/tradingagents/resilience.py`
- `tradingagents/tradingagents/dataflows/router.py`
- `tradingagents/tradingagents/agents/analysts/sentiment_analyst.py`
- `tradingagents/tradingagents/graph/trading_graph.py`
- `tradingagents/cli/run.py`
- `tradingagents/tradingagents/contracts/manifest.py`
