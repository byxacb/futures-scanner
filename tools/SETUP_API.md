# API Key 配置指南（用户必读）

## ⚠️ 安全须知

1. **永远不要把 API Key 粘贴到聊天里**——一旦出现在对话历史，等于公开
2. **永远不要 commit `.env` 到 git**——`tools/.gitignore` 已经排除它
3. **重置已暴露的 key**——如果不小心暴露过，立刻去服务商后台作废+重新生成

---

## 配置步骤（小米 MiMo via token-plan 代理）

### 1. 在服务商后台重置/确认你的 key
登录服务商，确保使用的 key 没有暴露过。

### 2. 复制模板并填写
```bash
cd /Users/bianyawen/Desktop/期货/tools
cp .env.example .env
```

### 3. 用编辑器（VSCode / nano / vim）打开 `.env`，**取消注释**下面 3 行并填入真实值

```
ANTHROPIC_API_KEY=tp-你的真实key
ANTHROPIC_BASE_URL=https://token-plan-cn.xiaomimimo.com/anthropic
ANTHROPIC_MODEL=mimo-v2.5-pro
```

⚠️ `=` 两侧不要加空格，整行不要加引号

### 4. 验证
```bash
cd /Users/bianyawen/Desktop/期货
pip install httpx  # 如果没装过
python3 -c "
import sys; sys.path.insert(0, 'tools')
from news.sentiment import analyze_sentiment
r = analyze_sentiment(
    symbol='rb',
    headlines=['央行宣布降准0.5个百分点 释放长期资金约1万亿元', '钢联：螺纹社库连续3周下降'],
    variety_name='螺纹钢',
    provider='anthropic',
)
print(r)
"
```

预期输出大致：
```
SentimentResult(symbol='rb', score=0.6, confidence=0.8, summary='降准+库存下降双利好...', ...)
```

如果报 401 / 403：检查 key 是否正确、是否已激活
如果报超时：检查 base_url 拼写、网络
如果返回 JSON 解析失败：先用一条简单提问试试 LLM 是否在工作

---

## 切换 provider（备用方案）

如果 MiMo 不稳定，可以临时切换：

### 切到 DeepSeek
```
DEEPSEEK_API_KEY=sk-...
```
然后改 `tools/config.example.toml` 的 `provider = "deepseek"`

或在代码中显式指定：
```python
analyze_sentiment(..., provider="deepseek")
```

---

## 成本估算

新闻情绪分析每天调用 ≈ 5 个品种 × 2 次（盘前/盘后）= 10 次
每次输入 ~500 tokens + 输出 ~300 tokens ≈ 800 tokens
**月成本约 24 万 tokens**

- MiMo via token-plan: 看服务商定价（通常 ~10-20 元/月）
- DeepSeek: 24 万 × ~1元/百万 ≈ <1 元/月
- Claude 官方 Sonnet: 24 万 × ~3美元/百万 input + 15美元/百万 output ≈ $2-5/月

→ 比赛期间任意一个都够用。

---

## 安全自查清单（每次配完跑一遍）

- [ ] `.env` 在 `tools/.gitignore` 中（已默认配置好）
- [ ] `git status` 看不到 `.env`
- [ ] `grep -r "tp-" tools/*.py tools/**/*.py` 应该空（key 不在代码里）
- [ ] `grep -r "sk-" tools/*.py tools/**/*.py` 应该空
- [ ] `.env.example` 里的 key 是占位符（带 # 注释或假值）
