# 门禁复验报告（master `f9327bc`）

- 日期：2026-11-17
- 复验对象：`origin/master` → `f9327bc Merge pull request #3`
- 复验分支：临时分支 `validate-part6`（merge latest master + Part 6 代码/测试/approval/AI log/ownership claim）
- 目的：确认 G5 baseline 修复是否生效，并报告剩余问题。

---

## 1. 复验结论

| 门禁 | 结果 |
|---|---|
| G1 测试审批 | **pass** |
| G2 静态分析 | **pass** |
| G3 Schema | **pass** |
| G4 语义评测 | **pass / skipped** |
| G5 回归 | **fail（仍有一条 baseline ID 不匹配）** |
| G6 AI 使用日志 | **pass** |
| G7 所有权 | **pass（默认 CI）** |

测试结果：

```text
tradingagents 全量应用测试: 1513 passed, 56 skipped, 13 deselected
tests/gates 门禁自测:        84 passed
Part 6 测试:                 81 passed
```

G4、G6 已确认修复；G5 仍失败。

---

## 2. 剩余问题：pytest 参数 ID 回退为 `text6`

### baseline 中的 key

```text
tradingagents/tests/test_rating_integrity.py::test_ratings_that_disagree_with_no_line_of_the_decisions_own_need_review[Street views:\n- Goldman rating: Buy\n\nWeighing all of this, the Portfolio Manager's rating: Underweight.]
```

### 当前 pytest 实际生成的 nodeid

```text
tradingagents/tests/test_rating_integrity.py::test_ratings_that_disagree_with_no_line_of_the_decisions_own_need_review[text6]
```

该测试实际存在且 **passed**。  
区别不是 `\n` 转义形式，而是 pytest 对某些特殊/非 ASCII 参数回退成了 `text6` 占位 ID。

### 为什么 `_norm_id` 没解决

`check_regression._norm_id` 目前只把：

- `\\n` 与真实换行
- `\\r` 与真实回车
- `\\t` 与真实制表符

归一成同一 token。  
但 `text6` 是 pytest 自动生成的占位 ID，和参数原文之间没有转义对应关系，因此 `_norm_id` 无法把它们视为同一测试。

### 证据

把 baseline 中的这条 key 从参数原文替换为 `[text6]` 后，G5 立即通过：

```json
{
  "gate": "G5",
  "status": "pass",
  "violations": []
}
```

说明测试没有缺失，只是 baseline key 与当前 pytest 的占位 ID 不一致。

---

## 3. 建议修复

### 方案 A（推荐）：给参数化测试加显式稳定 ID

在 `tradingagents/tests/test_rating_integrity.py` 的 `test_ratings_that_disagree_with_no_line_of_the_decisions_own_need_review` 上增加显式 `ids=`，例如：

```python
@pytest.mark.parametrize("text", [
    "Trader's proposed rating: Buy\n\nPortfolio Manager's rating: Hold",
    ...
    "Street views:\n- Goldman rating: Buy\n\nWeighing all of this, the Portfolio Manager's rating: Underweight.",
    ...
], ids=[
    "trader_hold",
    "research_manager_underweight",
    ...
    "street_views_underweight",
    ...
])
```

这样 nodeid 不再依赖 pytest 的自动 ID 生成，也不会因版本/特殊字符回退为 `text6`。

### 方案 B：用 CI 相同环境重新生成 baseline

确保 baseline 在 CI 的 Python 3.12 / 相同 pytest / pytest-json-report 版本下生成，这样会记录 `[text6]`。

缺点：`text6` 依赖参数顺序，后续插入参数可能再次漂移。

### 方案 C：快速修复 baseline

直接把该条 key 的 `[Street views:...]` 改成 `[text6]`。  
能立即通过，但不如方案 A 稳定。

---

## 4. 已确认修复的部分

- **G4**：非 eval-relevant 变更返回 `skipped`，不再 `TypeError`。
- **G6**：`collect_context.new_log_entries()` 已用 YAML 解析，G6 pass。
- **G2**：`run_static_checks` 包含 `dependencies`；ruff/pyright/pip-audit/heavy checks 通过。
- **G3**：`requirements.yaml` schema 校验通过。
- **G7**：workflow 使用 `-m "not integration"`；Part 6 claimed 后默认 CI pass。

---

## 5. 结论

G5 只剩 **pytest 参数 ID 回退 `text6`** 与 baseline 原文不一致的问题。  
采用方案 A（显式 `ids=`）或方案 B（CI 环境重录 baseline）后，本组 Part 6 在默认 CI 下应可通过全部门禁。

---

## 6. 后续复验：`18e57b7` 已修复，全部门禁通过

门禁作者在 `18e57b7`（PR #4）中修复了 G5：

- `tradingagents/tests/test_rating_integrity.py` 增加显式参数 ID；
- `docs/req/regression-baseline.json` 同步更新；
- `check_regression.py` 增加参数 ID 归一化；
- 新增对应门禁自测。

本组在临时验证分支重新 merge `origin/master` 后复验：

| 门禁 | 结果 |
|---|---|
| G1 | pass |
| G2 | pass |
| G3 | pass |
| G4 | pass / skipped |
| G5 | **pass** |
| G6 | pass |
| G7 | pass |

测试结果：

```text
tradingagents 全量应用测试: 1513 passed, 56 skipped, 13 deselected
tests/gates 门禁自测:        93 passed
Part 6 测试:                 81 passed
```

默认 CI 下 Part 6 已可通过全部门禁。  
备注：G7 当前统计的是 master 的 `test_latency.py` / `test_token_cost.py`；本组 `tests/part6/` 作为额外测试保留。
