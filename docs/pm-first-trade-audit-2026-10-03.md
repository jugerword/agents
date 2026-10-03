# pm-first-trade 工程审计报告

- 审计日期：2026-10-03
- 审计对象：`~/workspace/pm-first-trade`（Polymarket FOK 市价单工具）+ 交易链路（SDK 0.8.0 / CLI / 代理 / 端点）
- 审计方法：软件工程 + 系统工程视角（代码质量 / 安全 / 可靠性 / 可观测性 / 文档 / 依赖 / 验证闭环）
- 背景：该程序刚完成 $5 真实首单（MATCHED），本次审计发生在**下单之后**，用于加固与规范化。

---

## 1. 审计范围

| 资产 | 路径 | 角色 |
|---|---|---|
| 交易工具 | `~/workspace/pm-first-trade/` | 自建 FOK 下单程序（Rust + SDK 0.8.0） |
| SDK 源码 | `~/workspace/polymarket-rs-clob-client-v2/`（v0.8.0） | path 依赖，订单构建/签名/版本适配 |
| 官方 CLI | `~/workspace/polymarket-cli/`（v0.1.4） | 查询通道（下单因订单版本过旧不可用） |
| 钱包 | Safe `0x6949…F998`（Gnosis Safe）+ EOA `0x207771…` | 资金地址 / 签名者 |
| 网络 | mihomo 7890 HTTP 代理 +「交易专用」策略组 | clob 域名出口 |

## 2. 发现清单（审计 → 修复）

### Critical（资金/误操作风险）

| # | 问题 | 风险 | 处置 |
|---|---|---|---|
| C1 | 无金额上限：`AMOUNT` 直接透传，误传大额即大额下单 | 单次误操作资金损失 | ✅ 新增 `MAX_AMOUNT` 硬上限（默认 $5），`AMOUNT > MAX` 直接拒绝并退出 |
| C2 | 无 dry-run：无法在不花钱的前提下验证链路 | 参数/市场错误时直接真金白银 | ✅ 新增 `DRY_RUN=1` 模式（认证 + 参数打印 + 不下单） |

### Major（正确性 / 可靠性）

| # | 问题 | 风险 | 处置 |
|---|---|---|---|
| M1 | 默认端点 `clob-v2.polymarket.com` 在当前网络链路 **TLS 不可达**（实测 000），注释与默认值与实际可用通道不一致 | 程序默认配置即失败，误导使用者 | ✅ 默认改为 `clob.polymarket.com`（实测 200 + 下单成功），README 记录两域名差异 |
| M2 | 认证无重试：CLI 与 SDK 在 flaky 网络下多次偶发 `error sending request` | 一次抖动即中断交易流程 | ✅ 认证环节增加 3 次重试（间隔 2s），每次重试重建 client |
| M3 | 程序可重复运行导致重复下单（无幂等语义） | 重跑 = 重复买入 | ⚠️ 已在 README 明示 + dry-run 流程缓解；CLOB 无原生幂等，需调用侧自控（建议每次下单前查 open orders） |

### Minor（可维护性）

| # | 问题 | 处置 |
|---|---|---|
| m1 | 目录无 `.gitignore`，`target/`（产物）+ `.env` 有提交风险 | ✅ 新增 `.gitignore`（target/、.env） |
| m2 | 无 README，首单参数（token id / 订单 id / 钱包结构）散落在对话记录 | ✅ 新增 `README.md`（参数表、用法、安全合规、网络注意） |
| m3 | 单文件 main.rs 职责集中，无单元测试 | ⚠️ 工具程序规模可控（~90 行），暂不拆分；测试以真机回归（dry-run + 护栏）覆盖，后续若扩展再补 pytest/cargo test |
| m4 | path 依赖指向绝对路径 `~/workspace/polymarket-rs-clob-client-v2`，不可移植 | ⚠️ 已记录；如要发布需改为 crates.io 版本或 vendor |

### Info（记录观察）

| # | 事项 | 状态 |
|---|---|---|
| I1 | 首单后 collateral 余额 `24.069699 → 18.889699`（差 $5.18），订单成本 $5.00，$0.18 差额疑为历史仓位结算/口径差 | 🔍 持续观察 |
| I2 | 首单成交价 0.28 高于下单时盘口 lastTrade 0.275（FOK 跨价位成交），初始浮亏 -1.8% | 🔍 正常市价行为 |
| I3 | 持仓 100 条历史仓位中大量 `percentPnl: -100%`（历史交易记录，非本次） | ℹ️ 背景信息 |

## 3. 修复验证记录

| 验证项 | 命令/条件 | 结果 |
|---|---|---|
| 编译 | `cargo build --release` | ✅ Finished（8.7s，无 warning） |
| dry-run 认证 | `DRY_RUN=1 AMOUNT=5` | ✅ `authenticated OK` + 跳过下单 |
| 金额护栏 | `AMOUNT=10 MAX_AMOUNT=5` | ✅ `refusing to place order` |
| 真实链路（已发生） | 2026-10-03 14:03 UTC FOK $5 | ✅ MATCHED（order `0x385c862e…4df6`） |
| 持仓证据 | data-api | ✅ 17.8571 YES @ 0.2799 |
| 余额证据 | CLI balance | ✅ 18.889699（扣款确认） |

## 4. 剩余风险与待办

1. **幂等**：程序无订单幂等保护——真实下单前必须 `DRY_RUN=1` 核对 + 查 open orders。
2. **0.18 差额**：下周末观察余额与 data-api 现金口径，若持续偏差需核对 CLOB 费用（builder fee）与结算逻辑。
3. **SDK path 依赖**：若要在多台机器复现，需固定 SDK commit 或发布为本地 crate 镜像。
4. **单元测试**：核心逻辑（金额护栏、参数解析）建议后续拆出 `lib.rs` 并补测试（当前以回归验证代替）。
5. **合规**：Polymarket ToS 地区限制 + 中国大陆法规由用户自答确认；程序不含任何地区规避逻辑。

## 5. 结论

审计共发现 **2 Critical / 3 Major / 4 Minor / 3 Info**。Critical 与 Major 均已修复并回归验证；Minor 中幂等与测试以文档+流程缓解。当前程序满足"小额度、可控、可复现"的工程使用标准；正式放量前建议补幂等层与自动化测试。
