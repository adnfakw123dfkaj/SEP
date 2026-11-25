# Part 4 实现计划书 — 数据韧性与时点完整性

## 1. 基本信息

| 项 | 内容 |
|---|---|
| 负责组员 | 组员 D（待确认） |
| 覆盖需求 | `REQ-FR-005`（Must）、`REQ-INV-002`（Should） |
| 核心目标 | 减少重复抓取和重复 LLM 调用；失败可恢复、可降级；历史运行不泄漏未来数据 |
| 提供接口 | `CacheKey`、`CacheController`、`FallbackRouter`、checkpoint 集成、时点测试工具 |
| 依赖接口 | `ProfileConfig`（Part 1）、`RunManifest`（Part 3）、`LLMCallEvent`（Part 6） |
| 不负责 | 辩论、评级、报告渲染、成本路由内部；只提供数据/执行韧性能力 |

## 2. 目标与非目标

### 目标

- Standard/Deep 默认 checkpoint；中断后从最后成功节点恢复，不重复已完成 LLM 调用。
- 按数据类 TTL 缓存，记录 provenance；数据源失败时使用新鲜缓存，否则明确不可用，不编造。
- 历史运行严格无前视：任何晚于分析日期的数据不能进入 prompt。
- 降级事件写入 manifest，便于审计。

### 非目标

- 不做分布式缓存/Redis；本地文件缓存即可。
- 不做完整故障转移集群；单机重试/降级即可。
- 不改变数据供应商的选择策略；沿用现有 router。

## 3. 交付物

- 代码：
  - `tradingagents/contracts/cache.py`：`CacheKey`、`CacheEntry`、`TTLPolicy`。
  - `tradingagents/cache/controller.py`：读写、TTL、provenance。
  - `tradingagents/resilience.py`：`FallbackRouter`、`RetryPolicy`、typed failure events。
  - `graph/checkpointer.py`：Standard/Deep 默认启用；恢复逻辑。
  - `dataflows/date_window.py`：补充边界/时区测试；必要时修复遗漏路径。
- 测试：
  - `tests/contracts/test_cache_contract.py`
  - `tests/req/test_checkpoint_resume.py`
  - `tests/req/test_cache.py`
  - `tests/req/test_fallback.py`
  - `tests/req/test_point_in_time.py`
- 文档/证据：
  - TTL 表、数据路径清单。
  - resume 日志、缓存命中率报告、未来数据 fixtures。

## 4. TTL 与数据路径（第 1 周冻结）

| 数据类 | TTL | 说明 |
|---|---|---|
| 价格/技术指标 | 盘中 15 分钟；收盘后 24 小时 | 历史回测按 `as_of` 过滤 |
| 新闻 | 60 分钟 | 历史窗口不可达时标记 unavailable |
| 社交（StockTwits/Reddit） | 60 分钟 | 历史窗口只返回 unavailable，不用实时帖子 |
| 基本面/SEC | 24 小时 | 按 filing date/as-of 过滤 |
| 标的身份 | 7 天 | ticker -> company/asset identity |
| 预检结果 | 价格 15 分钟；身份 7 天 | 与 Part 1 共享 |

数据路径清单必须覆盖：价格、技术指标、新闻、宏观、基本面、内部人、社交、记忆教训。

## 5. 工作分解

### Week 1：契约、TTL 与基线

- 定义 `CacheKey`/`CacheEntry`/`TTLPolicy`，写契约测试。
- 列数据路径清单；确认现有 `date_window` 覆盖情况。
- 测量基线：重复运行同一 ticker/date 的耗时与网络调用次数。
- 设计 `FallbackRouter` 的 typed events。
- 交付：契约 + TTL 表 + 数据路径清单 + 基线。

### Week 2：缓存与恢复

- 实现 `CacheController`：读写、TTL、provenance、并发安全（文件锁）。
- 接入数据 router；缓存命中时返回 provenance。
- 实现 Standard/Deep 默认 checkpoint；恢复时跳过已完成节点。
- 实现幂等工具调用键（参数 + 数据版本）。
- 交付：重复运行缓存命中；kill/resume 成功。

### Week 3：降级与时点完整性

- 实现 `FallbackRouter`：重试 -> 新鲜缓存 -> 不可用 + 降置信度 -> REVIEW。
- 将 `fallback_events` 写入 manifest（Part 3 契约）。
- 对每条数据路径补时点测试：未来日期 fixtures、历史社交 unavailable、记忆教训过滤。
- 属性测试 100 个历史日期。
- 交付：`REQ-INV-002` 验收通过。

### Week 4：压力测试与收尾

- 故障注入：网络超时、HTTP 403、JSON 损坏、进程中断。
- 跑 `REQ-FR-005`、`REQ-INV-002` 全部验收命令。
- 补文档：TTL 调整、缓存清理、如何新增数据源。
- 准备演示：kill 后恢复、Reddit 403 降级、历史无前视。
- 交付：验收报告 + 演示脚本。

## 6. 验收与测试

| 需求 | 验收命令 | 证据 |
|---|---|---|
| `REQ-FR-005` | `pytest tests/req/test_checkpoint_resume.py::test_resume` | 恢复日志 |
| `REQ-FR-005` | `pytest tests/req/test_checkpoint_resume.py::test_no_duplicate_calls` | LLM 调用计数 |
| `REQ-FR-005` | `pytest tests/req/test_cache.py::test_hit_rate` | 命中率报告 |
| `REQ-FR-005` | `pytest tests/req/test_cache.py::test_no_stale` | TTL 报告 |
| `REQ-FR-005` | `pytest tests/req/test_fallback.py::test_no_fabrication` | 降级日志 |
| `REQ-INV-002` | `pytest tests/req/test_point_in_time.py::test_no_future_items` | 未来数据 fixtures |
| `REQ-INV-002` | `pytest tests/req/test_point_in_time.py::test_property_dates` | 属性测试报告 |

## 7. 风险与回退

| 风险 | 缓解 | 回退 |
|---|---|---|
| 缓存过期/陈旧数据 | 按数据类 TTL；历史运行按 `as_of` 禁用未来缓存 | 关闭缓存，只保留 checkpoint |
| 缓存与回测日期冲突 | `as_of` + TTL 双重约束；manifest 记录 | 历史运行强制冷缓存 |
| checkpoint 与图结构变化冲突 | 用 run_signature 作为线程 ID；图变化则新线程 | 关闭 checkpoint，重跑 |
| 文件锁/并发写冲突 | 单机文件锁 + 原子写 | 串行化缓存写 |
| 时区边界不清 | 统一 UTC 日期边界；测试固定 | 以 trade_date 为唯一 as-of |

## 8. Definition of Done

- Standard/Deep resume 复用 ≥90%，已完成节点 LLM 调用重复为 0。
- TTL 内缓存命中 ≥70%，超 TTL 使用为 0，编造数据为 0。
- 降级事件 100% 有 typed event 并进入 manifest。
- 时点属性测试 100 个日期通过，未来数据进入 prompt 为 0。
- OpenCode 会话记录、测试输出、故障注入日志已归档。

## 9. 集成交接清单

- [ ] `CacheKey` / `TTLPolicy` 契约冻结。
- [ ] 提供 `cache.get_or_fetch(key, fetch_fn) -> CacheEntry`。
- [ ] 提供 `fallback.route(failure, context) -> FallbackDecision`。
- [ ] 提供 `enable_checkpoint(profile, graph)` / `resume_graph(...)`。
- [ ] 提供 TTL 表和数据路径清单。
- [ ] 提供时点测试 fixtures（未来日期、历史社交、记忆教训）。
- [ ] 在 `tests/contracts/` 增加缓存契约测试。
