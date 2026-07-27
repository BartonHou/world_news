# 互动世界地图：新闻 + 梗图执行计划

> 本文件是执行版 `plan.md`。原始愿景稿保留在 `plan.original.md`。
> 这版不追求“先做得漂亮”，而是先验证产品最核心的不确定性。

---

## 0. 核心判断

这个产品最关键的问题不是地图能不能做出来，而是下面这件事是否成立：

> 我们能不能稳定产出“某个国家今天最值得看的新闻 + 一个真的有意思的本地梗/趋势 + 一个跨文化也看得懂的解释”？

如果这个输出本身不成立，地图做得再好也只是空壳。

所以整份计划的原则只有一句：

> 优先验证最不确定的部分，延后实现确定但昂贵的部分。

---

## 1. 产品定位

做一个可交互的世界地图。用户悬停到任意国家时，立刻看到这个国家今天在讨论什么、笑什么、争什么。

一句话定位：

> 一张实时地图，告诉你全世界正在讨论什么、笑什么、吵什么。

英文定位：

> A live map of what the world is talking, laughing, and arguing about.

---

## 2. MVP 要解决的问题

用户不是来读长篇报道的，而是想快速获得三个东西：

- 这个国家今天最重要的一件事
- 这个国家网上正在流行的一个梗或趋势
- 为什么这件事或这个梗值得看

MVP 成功的标准不是“信息很多”，而是“用户愿意继续点下一个国家”。

---

## 3. 明确不做的事

为了避免计划失控，MVP 阶段明确不做这些事：

- 不做实时新闻终端，刷新频率按 6 到 12 小时算，不按分钟算
- 不做完整新闻网站，一个国家只要 1 条强内容，不追求覆盖 10 条
- 不做全量 195 个国家，先做 20 个重点国家
- 不把“国家情绪”当成核心卖点，Mood Layer 延后
- 不在 hover 时实时请求外部 API 或 LLM

---

## 4. 用户体验定义

### 悬停时看到的信息

- 国家名和国旗
- 1 条头条新闻
- 1 句 AI 摘要
- 1 个梗图/趋势
- 1 段简短解释
- 3 个关键词
- 来源链接
- 更新时间

### 点击国家后的侧边面板

- 更完整的新闻上下文
- 梗/趋势来源与说明
- “为什么这在本地会火”
- 低置信度提示
- 原始来源列表

---

## 5. 路线图：先验证，再建设

### Phase 0：可分享性验证

目标：验证“新闻 + 梗解释”是否真的有趣。

范围：

- 只做 3 个国家：美国、日本、巴西
- 不做 UI
- 不做数据库
- 不做缓存
- 只写一个探针脚本，输出 JSON

脚本工作：

1. 每个国家拉取 3 到 5 条新闻候选
2. 每个国家拉取约 5 到 10 条趋势/梗候选
3. 用 LLM 生成新闻摘要与梗解释
4. 在终端打印标准化 JSON 结果

通过门槛：

- 3 个国家里，至少 2 个国家的结果值得截图或分享
- 如果做不到，继续调 prompt 和数据源，不进入下一阶段

预估时间：

- 2 到 3 天

---

### Phase 1：真实数据静态原型

目标：验证地图交互本身是否好玩。

范围：

- 用真实数据，但只输出静态 JSON
- 前端直接读 `public/data/*.json`
- 先不接数据库
- 先不接 Redis

要完成的内容：

- 世界地图渲染
- hover 高亮
- 跟随鼠标的 tooltip
- 点击后的国家详情面板
- 空状态设计：没有足够信号时明确提示

通过门槛：

- 你自己愿意连续看多个国家
- 2 到 3 个试用者会自然继续探索，而不是只看一个国家就退出

预估时间：

- 约 1 周

---

### Phase 2：自动刷新与基础运维

目标：让产品不依赖手工维护。

范围：

- 定时刷新任务
- 手动刷新单个国家
- 部署与数据更新自动化

推荐做法：

- GitHub Actions 定时跑脚本
- 更新静态 JSON
- 自动触发前端重新部署

只有在你明确需要“历史记录、时间轴、后台查询”时，再引入数据库。

---

### Phase 3：增强层与产品打磨

这个阶段只在前 3 个阶段有效时再做。

可加入：

- Mood Layer
- 分享卡片
- 移动端优化
- SEO
- 事件埋点
- 历史时间线

---

## 6. 为什么这套顺序更合理

旧顺序的问题是先做地图、样式和完整架构，最后才验证“内容到底值不值得看”。

这版顺序的优势：

- 先解决最大风险：梗和解释是否成立
- 在内容没验证前，不提前建设数据库和缓存
- 用静态 JSON 跑通 MVP，成本最低
- 接受“部分国家数据不足”，而不是强行做满覆盖

---

## 7. MVP 国家范围

首批 20 个国家：

- United States
- Canada
- United Kingdom
- France
- Germany
- Japan
- South Korea
- China
- India
- Brazil
- Mexico
- Argentina
- Australia
- Russia
- Ukraine
- Turkey
- Indonesia
- Philippines
- South Africa
- Nigeria

每个国家的最小输出结构：

- 1 条 top news
- 1 个 meme/trend
- 1 段 explanation
- 3 个 keywords
- source links
- updated timestamp

Mood 不是 MVP 必须项。

---

## 8. 数据源策略

在真正开工前，必须先确认数据源在 2026 年仍然可用。

### 新闻源候选

- Google News RSS
- GDELT
- NewsAPI

### 梗 / 趋势候选

- GIPHY API
- YouTube Data API
- Google Trends 非官方抓取
- 公开 RSS 或本地文化站点

### MVP 推荐组合

优先顺序：

1. Google News RSS 负责新闻
2. `meme` 不从新闻里挑，而是单独走趋势/文化源
3. Google Trends 只做弱趋势发现
4. Wikipedia pageviews 提供非新闻型文化候选
5. GIPHY 或 YouTube 以后再作为补充信号

当前判断：

- Reddit 不再作为 Phase 0 的主路径
- 原因不是“理论上没价值”，而是现实里匿名抓取容易 `403`，稳定性太差
- 如果未来一定要接 Reddit，应该走官方 OAuth 能力，而不是把它挂在 MVP 主链路上
- `top_news` 和 `meme` 必须是两条独立 pipeline
- 新闻负责“今天这个国家发生了什么”
- meme 负责“本地人在刷什么、笑什么、转什么、执着什么”
- 不能继续用新闻上下文硬拯救 meme 候选，否则结果会天然无聊、机构化
- source 也不能一刀切：像 `ja.wikipedia`、`pt.wikipedia` 还能近似本地文化流，`en.wikipedia` 这种全球语言源会被世界级体育和国际名人淹没，必须按国家选择性开启

### 必须先验证的风险

- GIPHY 的申请流程与额度
- YouTube 的 daily quota
- Google Trends 是否稳定可抓
- Wikimedia pageviews 是否足够有趣、是否会被百科型词条污染
- NewsAPI 免费层是否允许当前用途

---

## 9. Mood Layer 为什么延后

把一个国家今天的情绪压缩成一个 emoji，风险很高：

- 信息量低
- 很容易冒犯
- 很难验证是否准确

所以 Mood Layer 不应出现在 MVP 的第一版里。

如果以后要加，必须同时返回：

- `label`
- `emoji`
- `reason`
- `confidence`

并且不能脱离新闻和梗单独展示。

---

## 10. 成本原则

成本控制原则很简单：

- 慢刷新
- 强缓存
- hover 零请求

粗略估算：

- 20 个国家
- 每国 2 到 3 次 AI 处理
- 每天刷新 2 次

这类成本在 MVP 阶段应当是可控的。

绝对不要做的事：

- 每次 hover 都调用后端
- 每个国家都做高频实时更新
- 在内容尚未验证时就引入复杂基础设施

---

## 11. 轻量架构

### Phase 0 到 Phase 1

```txt
抓取脚本
  ↓
数据归一化
  ↓
可插拔 Filter Pipeline
  ↓
候选 shortlist
  ↓
LLM 生成摘要 / 梗解释
  ↓
写入静态 JSON
  ↓
前端读取 JSON 渲染地图
```

### Phase 2 以后

```txt
定时任务
  ↓
抓取与清洗
  ↓
LLM 生成
  ↓
Postgres（可选，用于历史）
  ↓
导出 JSON / API
  ↓
前端消费
```

架构原则：

- 起步时越简单越好
- 没有历史需求时，不引入数据库
- 先导出静态数据，后提供 API

### Filter Pipeline 设计

MVP 不再把“有趣程度”完全交给模型猜，而是在 LLM 之前先做一层可控筛选。

目标：

- 先挡掉明显无聊、重复、低信息量的候选
- 再把剩下的候选交给 LLM 做摘要和解释
- 让调优点集中在 filter，而不是每次重写 prompt
- 对多语言、短标题、裸人名这类边界候选，允许 AI helper 做小范围辅助

设计原则：

- filter 必须可插拔，单条规则可独立开启、关闭、调整分值
- 分成 `news filters` 和 `trend filters` 两套
- 每条 filter 只做一件事：`drop`、`penalize` 或 `boost`
- 每个候选都要留下 filter 诊断，方便复盘“为什么它被选中 / 被压掉”
- 硬 filter 负责挡垃圾，AI helper 只负责补语义，不负责接管整套排序

推荐实现形态：

```txt
candidate
  ↓
filter_1
  ↓
filter_2
  ↓
filter_3
  ↓
score / drop / diagnostics
```

对于趋势候选，再加一层轻量 AI helper：

```txt
candidate
  ↓
hard filters
  ↓
borderline shortlist
  ↓
AI helper
  ↓
score adjustment / normalized title / diagnostics
```

这个 AI helper 只处理三类问题：

- 裸人名标题：例如只出现 `桑田真澄`、`村上宗隆`
- 过短或过本地化的标题：例如本地缩写、梗词、难以直读的搜索词
- 多语言语义补全：把标题改写成全球用户能看懂的一句话

第一批推荐 filter：

- 压低常规政治拉扯
- 压低普通体育比分与例行赛报
- 压低年度复读机话题
- 压低纯股价、纯关税、纯 generic search query
- 压低只剩一个人名、没有故事上下文的标题
- 提升本地生活信号
- 提升文化冲突、创作者冲突、价格异常、奇怪社会现象

关于裸人名的处理规则：

- `Chiquinho Scarpa` 这种如果上下文本身很有故事，可以保留
- `桑田真澄`、`村上宗隆` 这类如果只是名字，不应直接上卡
- 最终展示标题应该被改写成“这个人因为什么事而上热搜”，而不是把人名裸露给用户

---

## 12. 数据结构

```json
{
  "iso2": "JP",
  "iso3": "JPN",
  "country_name": "Japan",
  "flag": "🇯🇵",
  "top_news": {
    "headline": "Example headline",
    "summary": "Short global-audience summary.",
    "why_it_matters": "Why this story matters.",
    "source_name": "Example News",
    "source_url": "https://example.com",
    "published_at": "2026-07-06T12:00:00Z"
  },
  "meme": {
    "title": "Example meme or trend",
    "platform": "GoogleTrends",
    "explanation": "Why people are sharing this.",
    "media_url": "https://example.com/media.gif",
    "source_url": "https://example.com/post",
    "confidence": 0.78
  },
  "keywords": ["anime", "election", "baseball"],
  "trend_score": 82,
  "updated_at": "2026-07-06T12:05:00Z",
  "fetch_diagnostics": {
    "news": {
      "filters": []
    },
    "trends": {
      "filters": []
    }
  }
}
```

如果后续加入 Mood：

```json
{
  "mood": {
    "label": "chaotic",
    "emoji": "🔥",
    "reason": "Several top posts are political and humorous.",
    "confidence": 0.72
  }
}
```

---

## 13. Prompt 策略

Phase 0 最重要的不是页面，而是候选质量、filter 和 prompt 的组合。

顺序应该是：

1. 先抓到还算像样的候选
2. 用 filter 压掉明显无聊的东西
3. 用 AI helper 处理多语言、裸人名、短标题
4. 最后再让主 prompt 生成国家卡片

### 新闻摘要 Prompt

```txt
You are an editorial summarizer for a global interactive news map.
Given 3-5 recent news headlines and article snippets from one country, return a concise JSON object.
Rules:
- Do not sensationalize. Do not invent facts.
- Prefer the story that is most important, widely covered, or nationally relevant.
- Write for a global audience; explain local context when necessary.
- Keep the summary under 35 words. Output valid JSON only.
Input:
Country: {{country}}
Articles: {{articles}}
Return:
{ "top_headline": "", "summary": "", "why_it_matters": "",
  "keywords": ["","",""], "confidence": 0.0 }
```

### 梗解释 Prompt

```txt
You are a cross-cultural meme explainer.
Given a trending meme, search trend, GIF title, video title, or hashtag from a country,
explain it to someone outside that culture.
Rules:
- Be concise. Explain why people find it funny, controversial, or relatable.
- Do not over-explain obvious jokes. Avoid offensive stereotypes.
- If political, explain neutrally. If the input is unclear, say confidence is low.
- Output valid JSON only.
Input:
Country: {{country}}  Platform: {{platform}}
Meme title or text: {{meme_text}}  Context: {{context}}
Return:
{ "meme_title": "", "plain_english_explanation": "", "why_people_are_sharing_it": "",
  "tone": "funny | angry | ironic | wholesome | chaotic | political | sad",
  "local_context": "", "confidence": 0.0 }
```

### Trend AI Helper Prompt

这个 prompt 不负责选最终国家卡，而是负责给 filter 管道补语义。

```txt
You are helping a rule-based filter understand multilingual trend candidates.
For each candidate, decide whether the raw title is too opaque, just a bare person name, or generic.
If the context reveals a genuinely interesting story, provide a clearer display title.
Return score adjustments and normalized titles in valid JSON only.
```

### Mood Prompt

只在 Phase 3 使用。

```txt
You classify the internet mood of a country based on recent news and meme signals.
Input: Country: {{country}}  News summary: {{news_summary}}
       Meme explanation: {{meme_explanation}}  Keywords: {{keywords}}
Choose one label from: funny, angry, sad, chaotic, wholesome, political, shocked,
proud, sports-crazy, pop-culture, serious, uncertain.
Return valid JSON only:
{ "mood_label": "", "mood_emoji": "", "reason": "", "confidence": 0.0 }
```

---

## 14. API 设计

Phase 0 到 Phase 1 不需要 API，前端直接读静态文件。

需要后端后，再补这些接口：

- `GET /api/countries`
- `GET /api/countries/:iso2`
- `POST /api/refresh-country/:iso2`
- `GET /api/layers/news`
- `GET /api/layers/memes`
- `GET /api/layers/mood`（Phase 3）

---

## 15. 前端组件建议

```txt
src/
  app/page.tsx
  components/
    WorldMap.tsx
    CountryTooltip.tsx
    CountryPanel.tsx
    LayerSwitcher.tsx
    SearchCountry.tsx
    NewsCard.tsx
    MemeCard.tsx
    SourceList.tsx
    EmptyState.tsx
  lib/
    countries.ts
    mapUtils.ts
    data.ts
  types/
    country.ts
```

推荐技术栈：

- Next.js
- TypeScript
- Tailwind CSS
- react-simple-maps
- Framer Motion

原则：

- 地图交互优先
- tooltip 立即出现
- 缺数据时也要优雅

---

## 16. 安全性与可信度

从第一天开始就要做的约束：

- 永远展示原始来源链接
- 明确标注 AI 生成摘要
- 低置信度梗解释必须提示
- 避免国家刻板印象
- 政治内容中性解释
- 过滤仇恨、成人、极端暴力内容

建议在产品里放这段免责声明：

> 本产品基于公开网络信号与 AI 生成摘要展示不同国家可能正在流行的话题。结果可能不完整或存在误差，完整信息请以原始来源为准。

---

## 17. 成功指标

最关键的产品信号不是点击率，而是探索深度。

优先关注：

- 单次会话查看了多少个国家
- 用户是否会点击原本没打算看的国家
- 面板打开次数
- 来源链接点击率
- 回访率
- 分享行为

---

## 18. 风险与对应措施

| 风险 | 处理方式 |
|---|---|
| 某些国家缺少足够的梗数据 | 先只做 20 国，并允许空状态 |
| AI 误读本地文化语境 | 输出 confidence，并保守解释 |
| 数据源收费或限流 | 在 Phase 0 前先逐个验证 |
| 运行成本膨胀 | 低频刷新，静态缓存，禁止 hover 请求 |
| 新闻选择存在偏差 | 显示来源，优先多方共同覆盖的议题 |

---

## 19. 立即执行项

按顺序只做这三件事：

1. 验证数据源是否可用
2. 写 Phase 0 的 probe 脚本
3. 看真实输出，再决定是否进入地图阶段

如果第 2 步的输出不够有趣，就不要提前做 UI。

这份计划里最重要的不是地图，而是第一张真正成立的国家卡片。
