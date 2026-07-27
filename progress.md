# Progress

更新时间：2026-07-07

## 当前状态

- `Phase 0` 已经跑通，并且有可复现输出
- `Phase 1` 已启动，已经有一个可直接读取静态 JSON 的前端原型
- 地图从“假 SVG 大陆”切换成了真实参考底图 + 国家级高亮交互

## 已完成

### 1. 规划与文档

- 整理并重写了 [plan.md](/home/barton/world_news/plan.md)
- 保留了原始愿景稿 [plan.original.md](/home/barton/world_news/plan.original.md)
- 补充了 [PHASE0.md](/home/barton/world_news/PHASE0.md) 说明当前 probe 的真实实现

### 2. Phase 0 Probe

- 完成 [scripts/probe.py](/home/barton/world_news/scripts/probe.py)
- 完成 [scripts/filter_config.py](/home/barton/world_news/scripts/filter_config.py)
- 新闻源：`Google News RSS`
- meme 源改版：**Reddit `.rss`（国家/文化子版）为主源**，Google Trends / Wikipedia pageviews 降为兜底
  - 起因：Google Trends + Wikipedia 本质是新闻驱动信号，拉出来全是新闻，不是网络文化
  - 实测 Reddit `.json` 全 403，但 `.rss` 可用（200）；限流很凶（连发 429，恢复窗口 ~20-30s）
  - 解决：全局 `reddit_throttle()` 强制请求间隔 25s（国家间的 LLM 延时可抵扣），429 再退避重试；一个子版够量就不抓第二个
  - 子版映射：US→AskAnAmerican/memes，JP→japan/japanlife，BR→brasil
  - 加了 `reddit_boilerplate` drop 过滤（置顶/每周固定帖/版务帖），reddit/youtube 平台 +5 boost
  - 效果：meme 层现在是真文化了（如 US「美国小学生都做火山/太阳系手工吗」、JP「少年黑客批量退订 4.6 万动画账号」、BR「Lukaku 领跳 Laranjão 舞」）
- YouTube 地区热门源已**激活**（`youtube_key.txt` 已就位，已加入 `.gitignore`）：拉音乐/电影预告/游戏/K-pop 等
  - 实测 US=Morgan Wallen/Avatar/Roblox、JP=Snow Man THE FIRST TAKE/生化危机/Minecraft、BR=Anitta/EA FC27
  - 已加**来源配额** `TREND_SOURCE_QUOTAS={"reddit":3,"youtube":3}`：保证 shortlist 里两源各至少 3 条（有的话），其余按分数填，最后按排名还原顺序
  - 效果：US=4yt+4reddit、JP=5yt+3reddit、BR=5yt+3reddit；主卡片来源自然分布（US/BR 命中 reddit，JP 命中 youtube），feed 里讨论帖 + 视频两种味道都保留
- `meme` 与 `top_news` 已拆成两条独立 pipeline
- 加入了可插拔 filter pipeline
- 加入了 AI helper，用于处理裸人名、多语言短标题、标题归一化
- 已输出最新结果到 [outputs/phase0/probe-results.json](/home/barton/world_news/outputs/phase0/probe-results.json)
- 校准修复：硬 drop 的候选不再通过兜底逻辑漏回 LLM 清单（news + trend 均已修）
- 校准修复：BR 本地信号 `"ge"` 子串误匹配改为 `"ge.globo"`
- 新增批量短解释：`attach_short_explanations()` 用一次 LLM 调用给整份候选清单各生成 ≤16 词短解释，写入 `raw_candidates[*].short_explanation`（每国现在约 4 次 LLM 调用）
- 主卡片解释已压短：news summary ≤22 词、meme 三段解释分别 ≤28/18/16 词

### 3. 安全与本地配置

- 加入了 [`.gitignore`](/home/barton/world_news/.gitignore)
- `key.txt` 已被忽略
- `scripts/probe.py` 支持从环境变量或 `key.txt` 读取 `OPENAI_API_KEY`

### 4. Phase 1 静态原型

- 新增静态数据导出脚本 [scripts/export_phase1_data.py](/home/barton/world_news/scripts/export_phase1_data.py)
- 已生成前端数据：
  - [public/data/countries.json](/home/barton/world_news/public/data/countries.json)
  - [public/data/countries/US.json](/home/barton/world_news/public/data/countries/US.json)
  - [public/data/countries/JP.json](/home/barton/world_news/public/data/countries/JP.json)
  - [public/data/countries/BR.json](/home/barton/world_news/public/data/countries/BR.json)
  - [public/data/layers/news.json](/home/barton/world_news/public/data/layers/news.json)
  - [public/data/layers/memes.json](/home/barton/world_news/public/data/layers/memes.json)
- 新增静态原型页面 [index.html](/home/barton/world_news/index.html)
- 新增前端逻辑 [public/app.js](/home/barton/world_news/public/app.js)
- 新增样式 [public/styles.css](/home/barton/world_news/public/styles.css)

## 地图交互现状

- 已彻底弃用参考底图 `MapChart_Map.png`（文件保留但不再被任何代码引用）
- 已弃用手画多边形，改为真实世界地理数据 [public/data/world.geo.json](/home/barton/world_news/public/data/world.geo.json)（180 国，ISO3 id）
- 全部 180 国以等距圆柱投影渲染为 SVG，有数据的国家点亮并可交互，其余作为暗色底图
- 有数据国家：hover 高亮 + 发光，点击选中，另有质心脉冲标记方便发现小国（如日本）
- 视觉切换为暗色主题（符合 plan “dark mode first”）
- tooltip 跟随鼠标，靠右自动翻转
- 点击国家打开右侧详情面板，支持 `News / Meme` layer 切换
- Selected Country 面板改为「统一卡片流」（不再分主卡片 + More signals 两种样式）：
  - 一列样式一致的卡片：tone/来源标签 + 标题 + 一句短解释 + Trend source/Original link
  - AI 精选那条排第一并高亮（`is-primary`），其余候选依次排列
  - 每张卡片的解释统一用 `short_explanation`（≤16 词），主卡片长三段式已废弃
  - 初始 5 张，滚到底分批加载（`FEED_BATCH=5`），`loadMoreFeed()` 预留真实 fetch 接口位
  - 内容撑不满滚动框时自动补齐，保证剩余缓存可达
  - 修复：Google Trends 所有候选共用同一 feed `source_url`，改用唯一的 `external_url` 匹配 AI 精选，避免张冠李戴/重复

## 覆盖范围

- 已从 3 国扩展到 **plan §7 的完整 20 国 MVP**：US CA GB FR DE JP KR CN IN BR MX AR AU RU UA TR ID PH ZA NG
- 每国配好了：Google News 参数(hl/gl/ceid)、Reddit 子版映射、wiki_project、地图 iso3/坐标
- 国旗改为 `iso2_to_flag()` 从 iso2 自动生成，不再手敲
- 一次全量重跑结果：**20/20 国的 Reddit 子版全部返回 200**（无 404，子版名都对），每国都有 Reddit+YouTube 混合候选
  - CN 特例：YouTube 地区热门为空（中国封锁），优雅回退为纯 Reddit(8 条)
- 地图自动点亮全部 20 国（markers 遍布各大洲），前端 `countries.json` 20 国齐全，`has_meme` 全为真

## 当前已知问题

- 当前前端是零依赖静态原型，还不是正式的 Next.js 应用结构
- 地理数据为 110m 精度，够用；如需更细可换 50m GeoJSON
- 母语子版优化(已做)：JP `japan`→`newsokur`(日语)、KR `korea`→`hanguk`(韩语)，本地梗味明显提升
  - 实测 newsokur 12/12 日语帖、hanguk 10/12 韩语帖；补了母语置顶帖过滤(質問スレ/雑談スレ/설문/사용법 等)
  - JP 主卡片示例：高达 RG Alex Zero 新品、"中国偽ドラえもん观光名所"；KR：韩国职场文化吐槽
- CN 仍是结构性缺口：Reddit 在中国被封，r/China(英语)/r/China_irl(政治向海外中文)都不代表真实中国网络文化(微博/B站/小红书/抖音才是，但都没有好用的免费 API)
- 每次全量刷新 ~12-18 分钟（Reddit 25s 节流 × 20 国），Phase 2 定时任务要考虑这个时长

## 最近一次结果判断

- `JP`：已经比较接近目标，`米騒動` 这类信号是对路的
- `BR`：比之前明显好，`Chiquinho Scarpa` 这类本地文化人物事件可用
- `US`：比之前强，但还需要更本地、更轻一点的 meme 源

## 下一步候选

### 路线 A：继续打磨当前原型

- 微调 `US / JP / BR` 的国家高亮路径
- 优化 tooltip、标签位置和面板排版
- 继续提升 `US` 的 meme 候选质量

### 路线 B：开始进入正式前端结构

- 把当前静态原型迁到真正的前端项目结构
- 用 `public/data/*.json` 继续喂给前端
- 再决定是否引入真实地图数据或地图库

## 本地运行

导出前端静态数据：

```bash
python3 scripts/export_phase1_data.py
```

运行当前静态原型：

```bash
python3 -m http.server 8766
```

然后打开：

```txt
http://127.0.0.1:8766/
```
