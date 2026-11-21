# Part 5 实现计划书 — 安全与评级权威

## 1. 基本信息

| 项 | 内容 |
|---|---|
| 负责组员 | 组员 E（待确认） |
| 覆盖需求 | `REQ-INV-003`（Must）、`REQ-SEC-001`（Must）、`REQ-INV-004`（Must） |
| 核心目标 | AI 只能是建议；评级写入必须确定性校验；外部文本不能劫持代理；密钥不泄露 |
| 提供接口 | `RatingResult`、`commit_rating()`、`sanitize(text)`、`validate_output()`、`redact()`、`security_log()` |
| 依赖接口 | `RunManifest`（Part 3）、`DebateTurn`（Part 2）、`ProfileConfig`（Part 1） |
| 不负责 | 报告渲染、manifest 写入、缓存、成本路由；只提供安全/评级原语 |

## 2. 目标与非目标

### 目标

- 最终评级只由确定性代码写入；允许集合外 -> `REVIEW`；缺 provenance -> 不提交。
- 不可信输入在进入 prompt 前消毒；模型输出在成为状态前校验；越权工具调用拒绝。
- 任何日志/报告/manifest/prompt/错误中不出现密钥。
- 用固定红队集和正常集双向校准，避免过度消毒。

### 非目标

- 不做完整隔离队列/复核人 UI（已舍弃）。
- 不做完整哈希链审计（已舍弃）。
- 不替代 Part 3 的 manifest 写入；只提供 security events 和 rating。

## 3. 交付物

- 代码：
  - `tradingagents/contracts/rating.py`：`Rating` 枚举、`RatingResult`。
  - `tradingagents/agents/rating.py`：确定性校验、commit gate。
  - `tradingagents/security/sanitize.py`：输入消毒、定界符、控制模式清理。
  - `tradingagents/security/validate_output.py`：schema/枚举/引用校验。
  - `tradingagents/security/redaction.py`：日志/报告/manifest 脱敏。
  - `tradingagents/security/security_log.py`：安全事件记录。
  - `tradingagents/llm_clients/api_key_env.py`：只从 env/secret store 读取。
- 测试：
  - `tests/contracts/test_rating_contract.py`
  - `tests/req/test_rating_invariant.py`
  - `tests/security/test_prompt_injection.py`
  - `tests/security/test_secret_redaction.py`
  - `scripts/security_regression.py`
- 文档/证据：
  - 安全事件日志样例。
  - 红队集/正常集报告。
  - 评级模糊测试报告。

## 4. 安全/评级契约（第 1 周冻结）

```text
Rating: "Buy" | "Overweight" | "Hold" | "Underweight" | "Sell" | "REVIEW"

RatingResult:
  rating: Rating
  reason_codes: list[str]
  provenance: {snapshot_id, manifest_id, model, prompt_version, config_hash}
  review_required: bool

SecurityEvent:
  event_id, kind, source, action, severity, timestamp, detail_redacted
```

规则：

- `commit_rating()` 是唯一写入口；LLM 文本不能直接赋值。
- 允许集合外的值 -> `REVIEW`，并记录原因。
- 缺 `snapshot_id` / `manifest_id` / 版本 -> 不提交。
- `sanitize()` 不改变事实性数字/链接；只处理控制模式和指令性内容。

## 5. 工作分解

### Week 1：契约与 API 骨架

- 定义 `Rating`、`RatingResult`、`SecurityEvent`，写契约测试。
- 定义 `sanitize(text) -> str`、`validate_output(obj, schema) -> ValidationResult`、`redact(text) -> str`。
- 建立安全事件日志字段。
- 准备 20 条红队样例、20 条正常样例，后续扩充到 200+200。
- 交付：契约 + API 骨架 + 初始样例。

### Week 2：评级权威与输入/输出安全

- 实现 `agents/rating.py`：枚举、确定性校验、commit gate。
- 接入 `graph/trading_graph.py` 的最终节点（与 Part 1 组合根协作）。
- 实现 sanitizer：定界符包裹、控制模式、长度上限。
- 实现 output validator：JSON schema、枚举、引用检查。
- 实现越权工具调用 guard。
- 交付：评级模糊测试通过；注入样例被阻断/丢弃。

### Week 3：脱敏与安全回归

- 实现 `redaction.py`：日志 filter、报告/manifest scrub、prompt allowlist。
- 写合成密钥测试：假 key 注入日志/错误/报告。
- 扩充红队/正常集到 200+200；实现 `scripts/security_regression.py`。
- 安全事件写入 manifest（Part 3 契约）。
- 交付：`REQ-SEC-001`、`REQ-INV-004` 验收通过。

### Week 4：对抗测试与收尾

- 对抗文本测试：“not a Sell”、工具越权、提示泄露、密钥拼接。
- 跑 `REQ-INV-003`、`REQ-SEC-001`、`REQ-INV-004` 全部验收命令。
- 补文档：如何新增安全规则、如何更新红队集。
- 准备演示：注入被阻断、评级被强制 REVIEW、密钥扫描 0 findings。
- 交付：验收报告 + 演示脚本。

## 6. 验收与测试

| 需求 | 验收命令 | 证据 |
|---|---|---|
| `REQ-INV-003` | `pytest tests/req/test_rating_invariant.py::test_fuzz --cases 10000` | 0 escapes 报告 |
| `REQ-INV-003` | `pytest tests/req/test_rating_invariant.py::test_requires_provenance` | 缺 provenance 拒绝 |
| `REQ-INV-003` | `pytest tests/req/test_rating_invariant.py::test_adversarial_text` | 对抗文本报告 |
| `REQ-SEC-001` | `python scripts/security_regression.py --injections 200 --benign 200` | 红队/正常集报告 |
| `REQ-SEC-001` | `pytest tests/security/test_prompt_injection.py::test_no_unauthorized_tool_calls` | 工具调用日志 |
| `REQ-INV-004` | `pytest tests/security/test_secret_redaction.py` | 脱敏报告 |
| `REQ-INV-004` | `gitleaks detect --no-git --source .` | 0 findings |

## 7. 风险与回退

| 风险 | 缓解 | 回退 |
|---|---|---|
| 消毒过严破坏正常语义 | 200 条正常集 + ≤5% 误报上限 | 降低规则强度，记录为安全债 |
| 消毒过松漏注入 | 200 条红队集 + 回归 bank | 增加规则；高风险输入一律丢弃 |
| 评级 commit 与图节点冲突 | Part 5 提供唯一入口；Part 1 组合根接入 | feature flag 关闭 commit gate，退回旧 rating.py |
| 脱敏误伤错误信息 | 只针对密钥模式和登记 env 名 | 保留请求 ID 便于排查 |
| 第三方 SDK 异常带 key | 异常处理层统一 redact | 记录为 bug，加测试 |

## 8. Definition of Done

- 10,000 个变异输出中越界评级 escapes = 0。
- 缺 provenance 的提交 = 0；非法值 100% 转 REVIEW。
- 200+200 安全回归达到阻断率/误报率阈值；越权工具调用 = 0。
- 日志/报告/manifest/prompt 中密钥 findings = 0；CI secret scan 0。
- OpenCode 会话记录、测试输出、红队报告已归档。

## 9. 集成交接清单

- [ ] `Rating` / `RatingResult` / `SecurityEvent` 契约冻结。
- [ ] 提供 `commit_rating(candidate, provenance) -> RatingResult`。
- [ ] 提供 `sanitize(text) -> str`。
- [ ] 提供 `validate_output(obj, schema) -> ValidationResult`。
- [ ] 提供 `redact(text) -> str`。
- [ ] 提供 `security_log.emit(event)`。
- [ ] 在 `tests/contracts/` 增加评级/安全契约测试。
- [ ] 告知 Part 2/4：sanitize 的输入输出格式和失败行为。
