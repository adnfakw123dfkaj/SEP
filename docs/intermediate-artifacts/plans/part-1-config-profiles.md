# Part 1 实现计划书 — 配置、档位与输入闸门

## 1. 基本信息

| 项 | 内容 |
|---|---|
| 负责组员 | 组员 A（待确认） |
| 覆盖需求 | `REQ-FR-001`（Must）、`REQ-FR-002`（Should） |
| 核心目标 | 用三档运行模式控制速度/深度；在进入图之前拦截无效输入；作为组合根负责最终接线 |
| 提供接口 | `ProfileConfig`、`PreflightResult`、组合根/feature flag |
| 依赖接口 | `RunManifest`（Part 3）、`LLMCallEvent`（Part 6） |
| 不负责 | 辩论内部、证据/报告内部、缓存内部、安全内部、成本路由内部；只接线和调用 adapter |

## 2. 目标与非目标

### 目标

- 实现 Quick / Standard / Deep 三档，默认值可测试、可覆盖、可记录。
- 在 LLM 调用前校验 ticker 和核心数据可用性，失败快速退出且不消耗 token。
- 提供统一的组合根，让其他 Part 通过 adapter/feature flag 接入，不互相改文件。

### 非目标

- 不实现辩论质量评分、证据链、缓存、安全过滤、token 路由的内部逻辑。
- 不修改 provider SDK 调用方式；只调用现有 `llm_clients` 适配层。
- 不引入 Web UI；CLI 足够。

## 3. 交付物

- 代码：
  - `tradingagents/contracts/profile.py`：`ProfileConfig`、三套预设。
  - `tradingagents/contracts/preflight.py`：`PreflightResult`。
  - `tradingagents/profiles.py`：档位解析、校验、覆盖合并。
  - `tradingagents/preflight.py`：ticker/数据可用性预检。
  - `cli/main.py`：`--profile` 参数与交互式默认档位。
  - `tradingagents/default_config.py`：读取 `run_profile`。
  - `graph/setup.py`、`graph/trading_graph.py`：组合根接线与 feature flag。
- 测试：
  - `tests/contracts/test_profile_contract.py`
  - `tests/req/test_profiles.py`
  - `tests/req/test_preflight.py`
  - `scripts/bench_preflight.py`
- 文档/证据：
  - 档位矩阵表（本文件第 4 节）。
  - 预检失败样例（invalid / no-data）。
  - 第 1 周基线测量记录。

## 4. 档位默认值（第 1 周冻结）

| 配置 | Quick | Standard | Deep |
|---|---|---|---|
| analysts | `market` | `market, news, fundamentals` | `market, social, news, fundamentals` |
| max_debate_rounds | 1 | 1 | 2 |
| max_risk_discuss_rounds | 1 | 1 | 2 |
| max_tool_rounds | 6 | 10 | 15 |
| quick model | `deepseek-flash` | `deepseek-flash` | `deepseek-flash` |
| deep model | `deepseek-v4-pro` | `deepseek-v4-pro` | `deepseek-v4-pro` |
| token budget | 80k | 150k | 300k |
| timeout | 300s | 720s | 1800s |
| cache TTL | 价格 15m / 新闻 60m / 基本面 24h | 同左 | 同左 |

> 这些是目标默认值；第 1 周基线测量后可微调，但必须同步更新契约测试和需求验收阈值。

## 5. 工作分解

### Week 1：契约与骨架

- 定义 `ProfileConfig`、`PreflightResult`，写契约测试。
- 定义三套档位默认值；确定非法覆盖规则。
- CLI 增加 `--profile` 骨架；图构建暂时只读取 profile 字段。
- 测量当前基线：market-only、market+social、默认四分析师各 1 次，记录耗时/token（如果可获取）。
- 交付：契约文件 + 测试骨架 + 基线记录。

### Week 2：核心实现

- 实现 `profiles.py`：解析、校验、覆盖合并、错误信息。
- 接入 `default_config.py`、`graph/setup.py`、`graph/analyst_execution.py`。
- 实现 `preflight.py`：ticker 解析、价格数据检查、invalid vs no-data 区分。
- 实现 `--profile` CLI 流程；非法覆盖启动前拒绝。
- 写 `tests/req/test_profiles.py`、`tests/req/test_preflight.py`。
- 交付：Quick 档位可端到端跑通最小示例。

### Week 3：组合根与集成

- 在 `graph/setup.py` 建立组合根：按 feature flag 接入 Part 2/3/4/5/6 的 adapter。
- 让 `RunManifest` 记录 profile 和覆盖项（与 Part 3 对齐）。
- 与其他 Part 做一次联合 smoke：Quick + 档位 + 预检 + 空 adapter。
- 修复集成冲突；确保其他 Part 不需要改你的文件。
- 交付：集成分支上的 Quick 档位闭环。

### Week 4：收尾

- 跑 `REQ-FR-001`、`REQ-FR-002` 全部验收命令。
- 补文档：如何新增档位、如何接入新 Part。
- 准备演示：无效 ticker 快速失败、Quick/Standard 对比。
- 交付：验收报告 + 演示脚本。

## 6. 验收与测试

| 需求 | 验收命令 | 证据 |
|---|---|---|
| `REQ-FR-001` | `pytest tests/req/test_profiles.py::test_profile_matrix` | 三档矩阵报告 |
| `REQ-FR-001` | `pytest tests/req/test_profiles.py::test_manifest_profile` | manifest 样例 |
| `REQ-FR-001` | `pytest tests/req/test_profiles.py::test_invalid_override` | 错误信息样例 |
| `REQ-FR-002` | `pytest tests/req/test_preflight.py::test_no_analyst_calls` | 调用计数 |
| `REQ-FR-002` | `pytest tests/req/test_preflight.py::test_valid_tickers` | 50 个 ticker 报告 |
| `REQ-FR-002` | `python scripts/bench_preflight.py --assert-p95 2` | 预检耗时 |

## 7. 风险与回退

| 风险 | 缓解 | 回退 |
|---|---|---|
| 默认值不合理，Quick 仍慢 | 第 1 周基线校准；减少 tool rounds/新闻条数 | 调低 Quick 分析师/轮数，记录变更 |
| 预检误拒真实 ticker | invalid vs data-unavailable 区分；第二供应商回退 | 预检只做格式/非空检查，数据问题交给运行时 |
| `graph/setup.py` 多人修改冲突 | Part 1 独占组合根；其他 Part 只提供 adapter | 用 feature flag 关闭未就绪 Part |
| 档位矩阵与 Part 6 预算不一致 | `ProfileConfig` 是唯一来源；Part 6 只读 | 以 Part 1 契约为准，改 Part 6 配置 |

## 8. Definition of Done

- 三档可在 CLI 选择并运行；manifest 记录 profile/覆盖项。
- 无效/无数据 ticker 在图运行前失败，分析师节点调用为 0。
- `REQ-FR-001` 和 `REQ-FR-002` 的验收命令全部通过。
- 其他 Part 能用 stub 接入，不需要修改 Part 1 的文件。
- OpenCode 会话记录、测试输出、演示脚本已归档。

## 9. 集成交接清单

- [ ] `ProfileConfig` 契约冻结并通知全组。
- [ ] `PreflightResult` 契约冻结。
- [ ] 提供 `build_profile(name, overrides) -> ProfileConfig`。
- [ ] 提供 `validate_request(ticker, date, profile) -> PreflightResult`。
- [ ] 提供 feature flag 表（见集成计划）。
- [ ] 在 `tests/contracts/` 增加 profile/preflight 契约测试。
