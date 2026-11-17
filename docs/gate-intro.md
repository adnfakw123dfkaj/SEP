# 门禁说明（Gate 简介）

本文用中文简明说明：门禁的基本情况和工作规则、Part 认领规则与教程、测试用例的修改与删除规则及教程。

---

## 一、门禁的基本情况

本项目在 GitHub 上用一套统一的“阻塞式门禁”（blocking gates）来保证提交质量：不达标就**不允许合并到 master**。

- **规则只有一份，写在 master 上**（`.github/workflows/gates.yml` 与 `scripts/gates/`）。各功能分支不需要自己写规则。
- **两层检查**：
  - **层 1 · 分支自查**：往功能分支 push 时自动跑，用 master 的规则，失败**只告警、不阻断**。
  - **层 2 · PR 阻断**：向 master 提 PR 时再跑一次，用 master 的最新规则、检查 PR 分支的代码，失败**阻断合并**。
- **分支隔离**：每次检查都在独立的 runner 上、只取自己分支的代码，产物各自保存，互不污染。你的改动只在自己的分支/PR 里，合并后才影响别人。
- **防绕过**：PR 检查时，判定脚本取自 master，分支改自己的脚本也绕不过。
- **部署位置**：GitHub Actions；分支 `master`。

### 六个（加所有权共七个）闸门

| 闸门 | 作用 | 规则要点 |
|---|---|---|
| **G1 测试审批** | 改动代码前，测试须先被批准 | 需有 `docs/approvals/*.json` 审批记录，且批准时间早于首次实现提交 |
| **G2 静态分析** | 代码质量与依赖安全 | 每次提交跑 lint、类型检查（pyright）、依赖审计；改动“安全相关路径”时加跑 contract/安全/API/权限检查 |
| **G3 Schema** | 需求登记册合法 | `docs/req/requirements.yaml` 须通过 `req-schema.json` 校验 |
| **G4 语义评测** | 改 prompt/model 前须过质量门槛 | 改动 prompt 或模型配置时，回放固定评测集，任一阈值不达即阻断 |
| **G5 回归** | 新改动不能弄坏旧功能 | 跑全量旧测试，任何回归即阻断（详见“测试修改/删除规则”） |
| **G6 AI 使用日志** | 留痕 | 改了代码或 prompt 的 PR，必须同时更新 `docs/ai-use-log.yaml` |
| **G7 所有权** | 认领承诺 | 见下方“Part 认领规则” |

> 备注：G2 的类型检查目前只严格检查新写的闸门脚本与评测代码（`scripts/gates`、`eval`），历史 `tradingagents/` 包暂排除，后续逐步纳入（见 `pyrightconfig.json`）。

---

## 二、Part 认领规则与教程

### 规则

- 仓库的 14 条需求分成 **6 个 Part**。每个 Part 的测试都已**预先写在 master 上**，无需自己写测试。
- **认领是手动的**：你在自己分支里声明“我负责某个 Part”。机器不会自动分配。
- 认领后（`enabled: true`），该 Part 的测试**必须全部通过、不许 skip**；否则阻断。
- **未认领**的 Part 可以放心 skip（代表“尚未开工”），不影响其他人。

| 状态 | 该 Part 的测试能否 skip？ | 闸门结果 |
|---|---|---|
| 未认领（`enabled: false`） | 可以 | 不计入 |
| 已认领（`enabled: true`） | **skip 即失败** | 有 skip 或失败即阻断 |
| 已认领但收集不到测试结果 | — | 阻断 |

### 教程（以 Part 1 为例）

1. 从 `master` 建分支。
2. 打开 `test-cases/ownership.yaml`，**只改你自己 Part 的那一块**：
   ```yaml
   part1:
     owner: "你的名字"   # 原来是 null
     enabled: true       # 原来是 false
     tests: [ ... ]      # 不要改
   ```
3. 实现这个 Part（Part 1 即 `tradingagents/profiles.py`、`tradingagents/preflight.py`）。
4. 本地跑该 Part 的测试，确保全绿：
   ```bash
   cd tradingagents
   python -m pytest tests/req/test_profiles.py tests/req/test_preflight.py -q
   ```
5. 随 PR 提交，G7 会在 PR 上检查。

> 每个 Part 对应哪些测试文件，见 `test-cases/ownership.yaml` 里各 Part 的 `tests:` 列表（由 `test-cases/partN-*.md` 推导）。**不要修改别人 Part 的那一块。**

---

## 三、测试用例的修改与删除规则和教程

### 规则

实现过程中，你可能会发现某个测试写错了、不全、或过时。总体上允许你修改测试，规则如下：

| 对测试的操作 | 允许？ | 闸门行为 |
|---|---|---|
| 修改测试内容 / 断言 | 允许 | 无额外闸门；保持通过即可 |
| 新增测试 | 允许 | 无额外闸门；新增且通过的测试不算回归 |
| 把原本通过的测试改成 `skipped` | 允许 | 不算回归（只检查“删除”） |
| **删除**原本在 master 上已通过的测试 | 允许，但**需要审批** | 除非审批里 `deletes` 列出了它，否则 G5 阻断 |

**唯一需要审批**的是“删除一个原本已通过的测试”——防止有人删掉测试来掩盖失败的改动。改、加测试都不需要审批。

作用范围：你的测试改动只存在于你自己的分支/PR，合并进 master 后才影响他人；各分支互不污染。若该 Part 已被你认领，改完后它的测试仍需全部通过、不许 skip。

### 教程

**修改 / 新增测试**：直接在你的分支改或加，提交 PR 即可，无需审批。

**删除一个原本已通过的测试**：在 `docs/approvals/` 下加一条审批记录，用 `deletes` 写明被删的测试，删除才会被放行：

```json
{
  "change_id": "chg-2026-11-20-drop-legacy",
  "deletes": ["tradingagents/tests/req/test_point_in_time.py::test_is_historical"],
  "approved_by": "alice",
  "approved_at": "2026-11-20T09:00:00+00:00"
}
```

- 有这条记录：G5 放行。
- 没有这条记录就删除：G5 以 `previously-passing test deleted without approval` 为由阻断合并。

> 文件名建议为 `<change_id>.json`；`collect_context.py approvals` 会读取该目录下所有 `*.json`。
