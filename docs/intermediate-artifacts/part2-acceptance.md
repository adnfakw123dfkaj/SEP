# Part 2 补充验收摘要

复核日期：2026-11-20。依据：`docs/intermediate-artifacts/plans/part-2-debate.md`、`test-cases/part2-debate.md`、`docs/gate-intro.md`。

## 版本与证据范围

本次离线复核基准为分支 `wsk` 的 `530516be5300e8b357948e6042c9d36367ef6412`（`530516b`）。历史运行文件未记录 Git SHA，`source_files_unchanged` 只是脚本自报布尔值，不能独立把当时源码绑定到此提交；该版本绑定证据为**缺失**。

只读核验根目录的 [part2-live-acceptance-2026-11-20](../part2-live-acceptance-2026-11-20/)：`live_acceptance.py`、`summary.json`、`verification.json` 及 `transcript-01.json` 至 `transcript-30.json`，共 33 个文件。本次未执行该联网脚本，未新增模型调用，未重新生成 transcript。

历史脚本使用**合成本地报告调用真实 LLM**，没有使用真实市场数据；调用现有两名研究员、adapter、路由和评分接口，在 Research Manager 入口结束。

## 真实调用旁证

以下为现有文件中的调用自报/SDK 记录，经算术核对内部一致，不能描述为不可伪造的联网证明：

| 项目 | 汇总 |
|---|---|
| provider / model / 响应模型字段 | `deepseek` / `deepseek-flash`；30 份一致 |
| 历史起止时间（北京时间） | 2026-11-20T17:06:31.039181+08:00 至 2026-11-20T17:12:40.043692+08:00 |
| 批次墙钟耗时 | 369.004511 秒，约 6 分 9 秒 |
| transcript / turn / 模型函数调用 | 30 / 120 / 120；每份各 4 次发言、4 次调用 |
| 重试 / invalid / 低于上限的实际早停 | 0 / 0 / 0 |
| 输入 / 输出 / 合计 tokens | 300,341 / 160,151 / 460,492；逐调用求和一致 |
| 并发与累计耗时 | 首份串行，随后最多 3 份并发；各份耗时之和 1,024.735 秒，调用耗时之和 1,019.576 秒 |
| 单份 / 单次调用耗时范围 | 28.531–42.578 秒 / 5.250–15.578 秒 |

并发累计耗时不等于批次墙钟耗时；每份调用耗时之和不超过该份总耗时，计数、时间范围、token 加法均一致。

## 可独立复核的确定性结果

本次仅凭已有数据，使用当前唯一契约的 Pydantic 校验、离线导出及独立计数/规范化复算，结果如下：

| 检查 | 结果 |
|---|---|
| 数量、编号及标识 | 正好 30 份；NN=01–30 连续且无多余 transcript；每份标识严格为 `live-deepseek-NN`，全局唯一 |
| 逐份 turn / speaker / round / status | 30 份无例外：4；`[bull,bear,bull,bear]`；`[1,2,3,4]`；全部 `ok`；`quality_available=true` |
| 原始模型文本的 JSON 解析 | 120/120，为单个 JSON 对象 |
| 原始 JSON 的 DebateTurn 契约、导出后的 DebateTurn | 各 120/120（100%），含字段、枚举、范围和字符串引用校验 |
| DebateTranscript 契约与历史关系 | 30/30（100%），标识唯一、反驳指向先前发言 |
| 最大轮数和路由 | 30/30；两轮上限恰好 4 次发言；0–3 次前缀均不停止，第 4 次返回 Research Manager |
| JSON 导出往返 | 30/30；`export_transcript` 结果序列化再解析后等于原 transcript，各 turn 等于对应原始响应的契约化结果 |
| 重算与既有 verification | 四项逐份复算一致，重复评分一致、输入未变；既有 `verification.json` 的可复核结论一致 |

`round` 是严格递增的发言序号；配置中的一轮是 Bull/Bear 各一次，不把 `[1,2,3,4]` 误写成四个双方轮次。

| 指标 | 阈值 | 30 份的最小/最大/均值 | 达标份数 |
|---|---|---|---|
| `turns_with_evidence_or_no_new_evidence_rate` | == 1.0 | 1.0 / 1.0 / 1.0 | 30/30 |
| `rebuttal_coverage` | >= 0.90 | 1.0 / 1.0 / 1.0 | 30/30 |
| `unsupported_claim_rate` | <= 0.05 | 0.0 / 0.0 / 0.0 | 30/30 |
| `duplicate_claim_rate` | <= 0.10 | 0.0 / 0.0 / 0.0 | 30/30 |

复算口径：证据覆盖为有引用或显式无新证据的发言占比；反驳覆盖的分母排除首条开场；无证据率仍计入无引用但声明无新证据的发言；重复率按后续重复发言数除以总发言数。规范化使用 casefold、空白及标点合并，标准库相似度阈值 0.95。引用格式均为字符串 `"<namespace>:<key>"`，格式合规不等于来源真实性已由 Part 3 验证。

## 离线异常与边界验收

工作目录：仓库内 `tradingagents/`。执行命令：

```powershell
& ..\.venv311\Scripts\python.exe -m pytest `
  tests/req/test_debate_protocol.py::test_schema_valid `
  tests/req/test_debate_protocol.py::test_max_rounds `
  tests/req/test_debate_protocol.py::test_convergence_fixtures `
  tests/req/test_debate_protocol.py::test_export_schema `
  tests/req/test_debate_protocol.py::test_retry_then_degrade `
  tests/req/test_debate_quality.py::test_evidence_coverage `
  tests/req/test_debate_quality.py::test_rebuttal_coverage `
  tests/req/test_debate_quality.py::test_unsupported_claim_rate `
  tests/req/test_debate_quality.py::test_duplicate_claim_rate `
  tests/contracts/test_debate_contract.py `
  -q -m "not integration"
```

结果：**通过 66、失败 0、排除 0、跳过 0；pytest 报告耗时 3.49 秒，退出码 0**。其中 9 个点名需求测试、57 个参数化展开后的契约测试。点名选择不收集其余 integration 函数，因此此处排除数为 0。执行时关闭字节码和 pytest 缓存写入，未保存完整控制台输出。

| 离线证据 | 覆盖内容 |
|---|---|
| `test_schema_valid`、`test_max_rounds` | 30 条离线发言及错误字段；两轮恰好四次、双方交替、历史及前缀、关闭结构化和空 turns 的计数回退 |
| `test_convergence_fixtures` | 现有收敛/不收敛样本；完整双方轮次、立场变化、有新证据、不完整轮次及 invalid 不早停 |
| `test_export_schema` | round 排序、transcript_id、Schema 与 JSON 往返，保留无效状态 |
| `test_retry_then_degrade` | 首次失败后只重试一次；第二次失败返回完整 invalid，`no_new_evidence=true`、`quality_available=false`，路由至 Manager；不执行 Manager 总结 |
| 四个质量测试 | 覆盖率 1.0 与不足；反驳 27/30 通过、26/30 失败；无证据 2/40 通过、3/40 失败；重复 3/30 通过、4/30 失败；不可用时四项 None |
| 契约测试文件 | 字段、枚举、置信度、引用、重导出、提示与 stub；`normal`、`missing_fields`、`bad_rebuttal`、`duplicate_claims`、`convergence` 五个 golden fixture |

真实批次没有自然产生重试、invalid 或实际早停；两轮上限与收敛最早所需的四次发言重合。异常与早停的有效证据来自上述离线故障注入和更高上限下的固定样本，不冒充真实模型失败样例，也不因真实成功批次没有错误而否定这些测试。

## GitHub G1–G7 结果摘要

本阶段只核本仓库，未联网查询 GitHub，未运行门禁脚本，也未取得远端运行链接、提交关联的门禁日志或结论。以下“缺失”表示**远端结果证据缺失**，不等于判定该门禁已失败。

| 门禁 | GitHub 结果证据状态 | 当前本地旁证及限制 |
|---|---|---|
| G1 测试审批 | 缺失 | `docs/approvals/part2-debate.json` 覆盖两份需求测试、契约测试及五个 fixture；不能据此称远端 G1 通过 |
| G2 静态分析 | 缺失 | 本阶段没有运行完整静态分析/依赖审计；不以离线 pytest 替代 |
| G3 Schema | 缺失 | 本阶段没有运行需求登记册门禁 |
| G4 语义评测 | 缺失 | 没有运行 `eval/`，四项辩论代理指标不替代 G4 |
| G5 回归 | 缺失 | 本次只有指定 66 项离线测试，不是全量回归或 GitHub G5 结论 |
| G6 AI 使用日志 | 缺失 | `change_id="part2-debate"` 的既有条目存在；未改动该日志，不据此断言远端通过 |
| G7 所有权 | 缺失 | 本地 Part 2 为 wsk、enabled=true；本次 9 个离线需求测试无 skip，但没有远端所有权报告 |

## 敏感信息检查

对 33 个验收文件进行常见凭据格式、鉴权头值、口令/secret 字面赋值、会话令牌和私钥块的静态模式扫描，**未发现疑似未脱敏凭据**。脚本中的环境读取和脱敏逻辑名称不等于泄露值；数字 token 用量也不是鉴权令牌。静态规则不能穷尽未知格式的 secret。

四份新摘要只保留必要汇总与相对路径，不复制原始模型文本、完整会话/控制台输出或绝对本机临时路径；未展示或导出项目凭据配置，未修改原始验收文件。

## 结论与集成待办

现有成功路径数据的确定性复核通过，指定离线异常/边界测试全部通过；历史联网调用具有内部一致的旁证，缺少服务商侧独立凭据及当时的提交绑定。**不能据此宣称所有端到端集成均已完成。**

需单列交接：Research Manager 重建状态可能丢失 `turns`、`quality_available`；最终日志是否保存 transcript 由集成人确认；应正式告知 Part 3 当前字符串引用格式和未来对象迁移边界，并取得确认。详见[集成交接摘要](part2-integration.md)；计划中的同 ticker 演示、完整会话导出及远端门禁结果没有被本摘要补造。
