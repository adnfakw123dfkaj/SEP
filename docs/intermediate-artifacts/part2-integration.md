# Part 2 集成交接摘要

依据与完成状态见[追踪矩阵](part2-traceability.md)；定量证据见[验收摘要](part2-acceptance.md)。以下事项只登记，不授权修改冻结文件。

## 状态透传与日志出口

- **跨 Part 集成待办**：Research Manager 重建 `investment_debate_state` 时可能丢失 `turns` 和 `quality_available`。集成方需核对节点更新/合并后的最终状态，并保留必要的结构化辩论字段与开关；本阶段未修改 Research Manager 或共享状态。
- **跨 Part 集成待办**：最终日志是否保存 transcript，由集成人核对真实图运行和实际落盘结果。当前验收脚本在路由返回 `Research Manager` 时结束，手工导出的 30 份记录不能证明最终日志出口已接通。
- Manager 的自由文本总结、评级、报告、manifest、缓存和成本均未纳入本次 Part 2 端到端完成结论。

## Part 3 证据引用交接

当前 `DebateTurn.evidence_refs` 是 `list[str]`，采用 `"<namespace>:<key>"`，例如 `"market:price"`、`"fundamentals:valuation"`。本次 120 条发言中的引用均为此类字符串。契约和本地校验不等于 Part 3 已验证引用来源及事实保真。

**跨 Part 集成待办**：应正式告知 Part 3 当前字符串格式、样本位置、字段约束和未来迁移边界，并取得接收确认。本文是交接说明，不代表负责人已经获通知或接受接口。

未来改用 Part 3 `EvidenceRef` 对象时，需要双方先协调并审批唯一 `tradingagents/tradingagents/contracts/debate.py` 的兼容方案，再同步调用方、校验、导出、评分和契约测试。不得复制或分叉 DebateTurn；`schemas.py` 继续只重新导出。本阶段不改 `contracts/evidence.py`，不把其他 Part 文件纳入可修改范围。

## 自由文本回退边界

实际开关在 `investment_debate_state["enable_structured_debate"]`：字段不存在视为 true；显式 false 时，两名研究员走原自由文本路径，保留 `history`、`bull_history`、`bear_history`、`current_response`、`count` 和原响应前缀。

关闭结构化，或路由入口没有结构化 `turns` 时，路由沿用 `count >= 2 * max_debate_rounds` 上限；返回值仍为 `Bull Researcher`、`Bear Researcher`、`Research Manager`。关闭不会主动清空旧的结构字段，也不会把新自由文本发言转换成结构化 transcript；旧字段不得当成本次文本路径的新增评分证据。计划旧称 `debate_protocol` 不是当前实现的开关名。

`test_max_rounds` 覆盖关闭、缺省开启及无结构化历史时的计数回退；这不是同 ticker 的真实结构化/自由文本对比演示。

## 成功批次与异常路径的边界

历史批次使用合成本地报告调用真实 LLM 的记录，30 份均在 4 次发言到达两轮上限；没有自然出现重试、invalid 或实际早停。由于收敛至少需两个完整双方轮次，这一两轮配置不能单独展示低于上限的早停。

异常格式、一次重试、再次失败降级与质量不可用，由 `test_retry_then_degrade` 等离线故障注入断言覆盖；早停由 `convergence.json` 在更高上限下离线验证。这些是有效的确定性证据，不冒充真实模型失败样例。`sanitize()` 仍是原样返回的本地 stub，未接入正式安全实现。
