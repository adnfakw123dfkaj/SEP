# 门禁复验 Bug 报告（master `306893d`）

- 日期：2026-11-17
- 复验对象：`origin/master` → `306893d Fix faults of repo blocking gate`
- 复验方式：临时验证分支 `validate-part6`
  - merge `origin/master`；
  - 放入 Part 6 代码与测试；
  - 修复本组 10 个 ruff 问题；
  - 添加 `docs/approvals/part6-cost-control.json`；
  - 添加 `docs/ai-use-log.yaml` 新条目；
  - 在 `test-cases/ownership.yaml` 认领 `part6`；
  - 本地运行门禁脚本与全量测试。
- 目的：报告复验后仍存在的门禁实现/基线问题，供门禁作者修复。

---

## 1. 复验结论

| 门禁 | 结果 | 说明 |
|---|---|---|
| G1 测试审批 | **pass** | approval 覆盖 12 个测试文件，且早于实现提交 |
| G2 静态分析 | **pass** | ruff、pyright、pip-audit、contract/security/api_surface/permission 全部通过 |
| G3 Schema | **pass** | master 已采用本组 `requirements.yaml` 结构，校验通过 |
| G4 语义评测 | **fail（workflow crash）** | 非 eval-relevant 变更缺少 `metrics` 参数 |
| G5 回归 | **fail（baseline 不同步）** | baseline 含当前测试集不存在的参数化用例 |
| G6 AI 使用日志 | **fail（collector 解析错误）** | `collect_new_entries` 把 YAML 当 JSON |
| G7 所有权 | **pass（默认 CI）** | Part 6 已认领；nightly integration 仍有 skip 风险 |

测试结果：

```text
tradingagents 全量应用测试: 1513 passed, 56 skipped, 13 deselected
tests/gates 门禁自测:        71 passed
Part 6 测试:                 81 passed
```

G2/G3 的修复已验证有效；G4/G5/G6 仍需处理。

---

## 2. Bug 1：G4 在非 eval-relevant 变更上崩溃

### 位置

- `.github/workflows/gates.yml` 的 `gate-semantic-eval` job
- `scripts/gates/run.py` 的 G4 调用
- `scripts/gates/check_semantic_eval.py` 的 `check()`

### 复现

G4 workflow 构造 payload：

```python
files = json.load(open("/tmp/changed.json"))["changed_files"]
payload = {"changed_files": files}
if g.is_eval_relevant(files):
    payload["metrics"] = run_fixed_set()
json.dump(payload, open("/tmp/g4.json", "w"))
```

当变更不涉及 prompt/model 时，`payload` 没有 `metrics` 键。

随后 `run.py` 只把 payload 中存在的键传给 `check`：

```python
func, keys = _GATES[gate]
kwargs = {k: payload[k] for k in keys if k in payload}
result = func(**kwargs)
```

而 `check_semantic_eval.check` 的签名是：

```python
def check(changed_files, metrics, changed_config_keys=None):
```

因此抛：

```text
TypeError: check() missing 1 required positional argument: 'metrics'
```

### 期望

非 eval-relevant 变更应返回：

```json
{"gate": "G4", "status": "skipped", "violations": []}
```

### 建议修复（二选一）

1. 在 workflow 中始终写入 metrics：

```python
payload = {"changed_files": files, "metrics": None}
if g.is_eval_relevant(files):
    payload["metrics"] = run_fixed_set()
```

2. 或给 `check` 一个默认值：

```python
def check(changed_files, metrics=None, changed_config_keys=None):
```

### 验证

手工把 `metrics` 设为 `null` 后：

```text
gate G4: skipped
exit 0
```

---

## 3. Bug 2：G5 baseline 含当前不存在的测试

### 位置

- `docs/req/regression-baseline.json`
- `scripts/gates/check_regression.py`
- `tradingagents/tests/test_rating_integrity.py`

### 复现

全量应用测试 **1513 passed**，但 G5 报：

```text
previously-passing test deleted without approval:
tradingagents/tests/test_rating_integrity.py::test_ratings_that_disagree_with_no_line_of_the_decisions_own_need_review[Street views:\n- Goldman rating: Buy\n\nWeighing all of this, the Portfolio Manager's rating: Underweight.]
```

当前 `pytest-json-report` 结果中没有这个参数化用例。它不是 Part 6 的改动；Part 6 没有修改 `test_rating_integrity.py`，全量测试也没有失败。

### 判断

`docs/req/regression-baseline.json` 与当前 master 的测试集不同步。  
可能是 baseline 在某个旧提交/旧参数集上生成，后来测试参数变化但 baseline 未重新生成。

### 建议修复

1. 用当前 master 重新生成 `docs/req/regression-baseline.json`；或
2. 在 `docs/approvals/` 中为这条历史 ID 增加 deletion approval。

推荐方案 1，避免 baseline 继续漂移。

---

## 4. Bug 3：G6 collector 把 YAML 当 JSON

### 位置

- `scripts/gates/collect_context.py` 的 `new_log_entries()`
- `.github/workflows/gates.yml` 的 `gate-ai-use-log` job

### 复现

`new_log_entries()` 使用：

```python
data = json.loads(path.read_text(encoding="utf-8"))
```

但 `docs/ai-use-log.yaml` 是 YAML，不是 JSON。  
G6 workflow 在收集阶段直接失败：

```text
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

本组手工用 `yaml.safe_load` 解析当前文件和 `git show <since>:docs/ai-use-log.yaml` 后，`check_ai_use_log.check()` **返回 pass**。  
说明 G6 的判定逻辑已修复，但 collector 仍然错误。

### 建议修复

```python
import yaml

data = yaml.safe_load(path.read_text(encoding="utf-8"))
...
base = yaml.safe_load(base_text)
```

确保 `new_log_entries()` 对当前文件与 base 版本都使用 YAML 解析。

### 验证

手工 YAML 解析后，G6：

```json
{"gate": "G6", "status": "pass", "violations": []}
```

---

## 5. G7：默认 CI 通过，nightly integration 仍有 skip 风险

### 现状

- Part 6 已认领（`enabled: true`）。
- 默认 CI（pyproject `addopts` 排除 integration）：
  - `test_token_cost.py` 的 2 个非 integration 测试通过；
  - `test_latency.py` 的 3 个 integration 测试被 deselect；
  - G7 pass。
- nightly / `-m integration`：
  - `test_latency.py` 依赖 `tradingagents.profiles`；
  - Part 1 尚未实现，3 个测试 skip；
  - 已认领 Part 的 skip 会导致 G7 fail。

### 建议

1. 若 Part 6 的验收以本组 `tradingagents/tests/part6/` 为准，请更新 `ownership.yaml` 的 Part 6 测试列表，或提供“参考测试不计入 G7”的机制；
2. 或明确 nightly integration 的例外规则：前置 Part 未实现时，相关 integration skip 不算 claimed Part 失败；
3. 或让 `test_latency.py` 不依赖 `tradingagents.profiles`，改为独立的 Part 6 延迟 fixture。

---

## 6. 已验证通过的部分

为避免重复排查，以下已经确认不是问题：

- **G1**：approval 覆盖 12 个测试文件，且 `approved_at` 早于首次实现提交。
- **G2**：`ruff check tradingagents` 通过；pyright 0 errors；pip-audit 0 vulnerabilities；`run_static_checks.py` 返回：

```json
{"contract": true, "security": true, "api_surface": true, "permission": true}
```

- **G3**：`docs/req/requirements.yaml` 通过新 schema；master 已采用本组结构。
- **G6 判定逻辑**：手工 YAML 解析后 pass。
- **G7 默认 CI**：Part 6 claimed 后 pass。

---

## 7. 复现命令摘要

在临时验证分支：

```powershell
# G2
ruff check tradingagents
pyright
pip-audit
python scripts/gates/run_static_checks.py

# G3
python scripts/gates/run.py g3 --input g3-input.json

# G4（会 crash）
python scripts/gates/run.py g4 --input g4-input.json

# G5
python scripts/gates/run.py g5 --input g5-input.json

# G6（workflow collector 会 crash；手工 YAML 解析后判定通过）
python scripts/gates/collect_context.py log-entries --path docs/ai-use-log.yaml --since origin/master

# G7
python scripts/gates/run.py g7 --input g7-input.json
```

---

## 8. 希望门禁作者确认/修复

1. G4：workflow 始终写入 `metrics: None`，或 `check` 默认 `metrics=None`。
2. G5：重新生成 regression baseline，或为历史测试 ID 提供 deletion approval。
3. G6：`collect_context.new_log_entries()` 改用 `yaml.safe_load`。
4. G7：明确 Part 6 的测试来源与 nightly integration skip 规则。

修复后本组会重新 merge、跑完整 PR 门禁并提交结果。
