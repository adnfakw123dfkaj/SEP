# 门禁复验报告（master `f9ebe11`）

- 日期：2026-11-17
- 复验对象：`origin/master` → `f9ebe11 Merge pull request #2 from adnfakw123dfkaj/luochen`
- 复验分支：临时分支 `validate-part6`（merge latest master + Part 6 代码/测试/approval/AI log/ownership claim）
- 目的：确认上一轮 G4/G5/G6 问题是否已修复，并报告剩余问题。

---

## 1. 复验结论

| 门禁 | 结果 | 说明 |
|---|---|---|
| G1 测试审批 | **pass** | approval 覆盖 12 个测试文件，且早于实现提交 |
| G2 静态分析 | **pass** | ruff、pyright、pip-audit、contract/security/api_surface/permission/dependencies 全部通过 |
| G3 Schema | **pass** | `requirements.yaml` 通过新 schema |
| G4 语义评测 | **pass / skipped** | 非 eval-relevant 变更不再 crash；返回 skipped |
| G5 回归 | **fail** | baseline 的 pytest 参数化 ID 与当前 pytest 生成的 ID 不一致 |
| G6 AI 使用日志 | **pass** | YAML collector 已修复；新日志条目被正确识别 |
| G7 所有权 | **pass（默认 CI）** | Part 6 claimed；workflow 已使用 `-m "not integration"` |

测试结果：

```text
tradingagents 全量应用测试: 1513 passed, 56 skipped, 13 deselected
tests/gates 门禁自测:        81 passed
Part 6 测试:                 81 passed
```

G4 和 G6 的修复已验证有效。**只剩 G5 的 baseline 键不一致。**

---

## 2. 剩余 Bug：G5 baseline 与当前 pytest 参数化 ID 不一致

### 现象

全量应用测试 1513 passed，但 G5 报：

```text
previously-passing test deleted without approval:
tradingagents/tests/test_rating_integrity.py::test_ratings_that_disagree_with_no_line_of_the_decisions_own_need_review[Street views:\n- Goldman rating: Buy\n\nWeighing all of this, the Portfolio Manager's rating: Underweight.]
```

### 实际测试状态

该测试在 master 上仍存在，并且当前运行 **passed**。

但 `pytest-json-report` 当前生成的 nodeid 是：

```text
tradingagents/tests/test_rating_integrity.py::test_ratings_that_disagree_with_no_line_of_the_decisions_own_need_review[text6]
```

baseline 里记录的是参数原文：

```text
... [Street views:\n- Goldman rating: Buy\n\nWeighing all of this, the Portfolio Manager's rating: Underweight.]
```

同一个测试、同一参数，只是 pytest 生成的参数 ID 不同。

### 根因

`docs/req/regression-baseline.json` 与当前 CI 环境（Python/pytest/pytest-json-report 版本）生成的参数化 nodeid 不一致。  
pytest 在某些非 ASCII/特殊字符参数上会回退为 `text6` 这类占位 ID；baseline 很可能是在另一个环境或旧测试版本上生成的。

### 证据

把 baseline 中的这条 key 从参数原文替换为 `[text6]` 后，G5 立即通过：

```json
{
  "gate": "G5",
  "status": "pass",
  "violations": []
}
```

说明当前测试并没有缺失，问题只是 baseline key 过期/不规范。

### 建议修复

三选一：

1. **用 CI 相同环境重新生成 baseline**（推荐）
   - Python 3.12 / 与 `tradingagents/pyproject.toml` 一致的 pytest 版本 / 相同 pytest-json-report 版本；
   - 避免参数 ID 代际差异。

2. **规范化 nodeid**
   - 在生成 baseline 和 current outcomes 时，对参数化 ID 做统一规范化；
   - 或使用稳定的测试 ID（例如显式 `ids=`）。

3. **直接更新 baseline 的这一条**
   - 把 `[Street views:...]` 替换为 `[text6]`；
   - 适用于只此一条漂移的情况。

---

## 3. 已验证修复的部分

### G4

`gates.yml` 现在始终写入：

```python
payload = {"changed_files": files, "metrics": None}
```

非 eval-relevant 变更返回：

```json
{"gate": "G4", "status": "skipped", "violations": []}
```

### G6

`collect_context.new_log_entries()` 已改用 YAML 解析；G6 collector 不再崩溃。  
G6 检查结果：

```json
{"gate": "G6", "status": "pass", "violations": []}
```

### G2

`run_static_checks.py` 现在包含 `dependencies`，workflow 也运行 heavy checks：

```json
{"contract": true, "security": true, "api_surface": true, "permission": true, "dependencies": true}
```

`ruff check tradingagents`、`pyright`、`pip-audit` 均通过（pip-audit 仅 informational）。

### G7

workflow 已改为：

```text
pytest tests/req tests/security -m "not integration"
```

Part 6 claimed 后默认 CI **pass**；integration 测试不再影响 G7。

> 备注：本组 `tests/part6/` 仍作为额外测试，不进入 G7 统计；若后续要求以本组测试为准，需要单独调整 ownership 或 workflow。

---

## 4. 复现命令

```powershell
# 全量应用测试
cd tradingagents
python -m pytest tests -q --json-report --json-report-file=app.json

# 门禁自测
cd ..
python -m pytest tests/gates -q

# G5
python scripts/gates/run.py g5 --input g5-input.json

# G2
ruff check tradingagents
pyright
python scripts/gates/run_static_checks.py
```

---

## 5. 结论

- 上一轮的 G4、G6 已修复；G2/G3/G7 也通过。
- **只剩 G5 baseline 参数化 ID 漂移**。
- 修复 G5 后，本组 Part 6 在默认 CI 下应可通过全部门禁。
