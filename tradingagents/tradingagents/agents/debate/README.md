## 如何新增一个 DebateTurn 字段

1. 在 `tradingagents/contracts/debate.py` 的 `DebateTurn` 中定义字段、类型、默认值与约束。这是唯一的字段定义来源；`schemas.py` 只重新导出，无需复制字段或修改 `contracts/__init__.py`。
2. `prompts.py` 从契约生成 JSON Schema。新增字段后，核对 Bull / Bear 提示仍要求输出完整的单个 JSON 对象；若新增必填字段，同步补齐 `adapter.py` 中 `invalid` 占位对象的值。涉及历史关系的约束放在 `validator.py`，涉及质量计算的口径放在 `quality.py`。
3. 同步验证契约测试、协议测试和质量测试，覆盖正常发言、首次失败后重试、再次失败后的完整占位对象。固定样本统一使用 `tests/fixtures/debate/`，并按测试审批范围处理后续样本变更。

## 如何调整收敛判断

在 `convergence.py` 的 `should_stop(transcript, max_rounds)` 中调整规则。当前达到 `2 * max_rounds` 次发言即停止；提前停止要求至少已有两个完整的 Bull / Bear 轮次，最新一轮双方均 `no_new_evidence=true`，且双方各自的 `stance` 与自己上一轮相同。单方刚发言时不提前停止，`invalid` 发言不参与收敛。

修改后用 `test_convergence_fixtures` 核对现有 `convergence.json`，并用 `test_max_rounds` 核对永不收敛、最大轮数为 2 时恰好 4 次发言。路由接入点是 `conditional_logic.py` 的 `should_continue_debate()`，返回值保持 `Bull Researcher`、`Bear Researcher`、`Research Manager`；关闭结构化辩论或没有结构化发言时沿用原来的计数上限。

重复主张指标由 `quality.py` 计算：先 casefold、统一连续空白和 Unicode 标点，再进行相等或标准库相似度比较。相似度常量 `CLAIM_SIMILARITY_THRESHOLD` 为 **0.95**，重复主张率验收阈值为 **≤ 0.10**。调整时同步更新代码注释与质量边界断言，并核对固定样本的确定性结果。
