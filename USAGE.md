# Polymarket Agents · 使用备忘

> 项目位置：`/Users/zz/workspace/polymarket-agents`（独立目录，与交易系统 polymarket15BTC 隔离）
> 远程 fork：`https://github.com/jugerword/agents`（upstream = Polymarket/agents）
> 后端：MiniMax（M3 LLM + embo-01 embeddings），无需 OpenAI key

## 一、日常命令

**快速入口**（已写入 ~/.zshrc，新开终端生效）：
```bash
pa --help                          # 所有命令列表
pa get-all-markets --limit 5       # 拉真实市场（需外网代理，默认已走 HTTP 代理）
pa get-relevant-news "bitcoin"     # 新闻检索（NewsAPI）
pa create-local-markets-rag        # 拉全部市场 → 建立本地向量库 local_db/
pa query-local-markets-rag --help  # RAG 语义检索用法
```

**手动方式**（不用别名）：
```bash
cd /Users/zz/workspace/polymarket-agents
env -u PYTHONPATH PYTHONPATH="." .venv/bin/python scripts/python/cli.py <命令>
```

## 二、测试

```bash
cd /Users/zz/workspace/polymarket-agents
env -u PYTHONPATH PYTHONPATH="." .venv/bin/python -m pytest tests/ -v   # 15 个用例，离线
```

## 三、环境要点（重要）

| 项 | 说明 |
|---|---|
| `.env` | 6 个变量已填（钱包私钥 / MiniMax key / base URL / Tavily / NewsAPI），**已被 .gitignore 排除，勿推 github** |
| 代理 | HTTP 代理 `127.0.0.1:7890` 正常；**SOCKS5（all_proxy）已确认失效**，已在 ~/.zshrc 中 unset。若手动开 shell 时仍有 all_proxy，命令前缀加 `all_proxy=` |
| `PYTHONPATH` | shell 全局 PYTHONPATH 被污染，所有命令用 `env -u PYTHONPATH` 前缀 |
| MiniMax | LLM 走 `https://api.minimax.cn/v1`；RAG 用 `MiniMaxEmbeddings`（国内 API 直连，不读代理） |
| 交易 | `run-autonomous-trader` 仅跑决策流程，`execute_market_order` 因 TOS 被注释，**不会下真单** |

## 四、RAG 用法

```bash
pa create-local-markets-rag                          # 建库（写 local_db/）
pa query-local-markets-rag --query "btc 15分钟涨跌"  # 语义检索市场
```

- Embedding 模型：`embo-01`（MiniMax，1536 维）
- 强制切换：`.env` 里 `EMBEDDING_PROVIDER=openai|minimax`，`EMBEDDING_MODEL` 自定义模型名

## 五、代码状态（8 个自定义 commit）

```
6bfdd26 测试套件 + README 更新
19312b4 检查修复（embedding 分派 / news 端点 / 注解 / env 模板）
cb69d86 langchain-chroma 迁移
6b75463 MiniMaxEmbeddings 适配器
6ed364c cron 类名冲突 + embedding 可配置
b1c8df2 CLI 惰性初始化
5897b22 search.py key 笔误 + 惰性化
797b12c 默认模型 MiniMax-M3
```

## 六、已知坑

- `get-all-markets` 慢时：是代理波动，重试即可
- RAG 建库体积大时：拉全部市场 + embedding 会花少量 MiniMax 额度
- 换机器部署：`cp .env.example .env` 再填 key；`uv venv --python 3.11 .venv` 建环境
