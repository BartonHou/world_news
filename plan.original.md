# Interactive World Map: News + Memes Plan

## 1. Product Vision

Build an interactive world map where users can hover over any country and instantly see what that country is talking about today: the hottest news, latest memes, internet mood, and cultural context.

The product should feel less like a boring news dashboard and more like a live map of global internet culture.

**One-line positioning:**

> A live map of what the world is talking, laughing, and arguing about.

**Chinese positioning:**

> 一张实时地图，告诉你全世界正在讨论什么、笑什么、吵什么。

---

## 2. Core Concept

When a user hovers over a country on the world map, the country is highlighted and a tooltip or floating card appears.

The card shows:

- Country name and flag
- Top news headline
- Short AI-generated summary
- Trending meme or internet trend
- Meme explanation
- Internet mood emoji
- 3 trending keywords
- Source links
- Last updated time

When a user clicks a country, a side panel opens with deeper details.

---

## 3. Product Name Ideas

Possible names:

- GlobeMood
- MemeAtlas
- WorldPulse
- Today on Earth
- Internet Earth
- WorldVibe
- Pulse Atlas
- What’s Hot Where
- Nowhere News
- Global Scroll

Recommended names:

1. **GlobeMood** — best for news + emotion + memes.
2. **MemeAtlas** — best if the product focuses more on internet culture.
3. **Today on Earth** — best if the product feels editorial and mainstream.

---

## 4. Target Users

### Primary Users

- Internet-native users who enjoy memes, trends, and global culture
- News-curious users who want a fast visual way to understand the world
- Creators who want inspiration from global trends
- Students, journalists, researchers, and social media managers

### User Jobs

Users want to:

- Quickly understand what is trending in another country
- Discover cross-cultural memes and internet behavior
- Compare global public moods
- Find story ideas or content inspiration
- Explore the world through a fun visual interface

---

## 5. MVP Scope

Do not launch with every country at first. Start with a controlled MVP of around 20 countries.

### Suggested MVP Countries

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

### MVP Features

For each country, show:

- 1 top news item
- 1 trending meme or internet trend
- 1 short explanation
- 3 keywords
- 1 mood label
- 1 mood emoji
- Source links
- Updated timestamp

### MVP User Interactions

- Hover over a country to highlight it
- Show tooltip on hover
- Click country to open detail panel
- Switch between News Layer, Meme Layer, and Mood Layer
- Search for a country
- Show fallback state when data is missing

---

## 6. Core User Flow

1. User opens the homepage.
2. A dark-mode world map appears.
3. Countries with available data are subtly highlighted.
4. User hovers over Japan.
5. Japan glows or changes color.
6. Tooltip appears with Japan’s top story, meme, mood, and keywords.
7. User clicks Japan.
8. Right-side panel opens with more context, sources, and related trends.
9. User switches from News Layer to Meme Layer.
10. Map recolors based on meme activity or internet mood.

---

## 7. UI / UX Direction

### Visual Style

- Dark mode first
- Editorial but playful
- Map should feel alive, not static
- Smooth hover transitions
- Floating cards with glassmorphism or subtle blur
- Use emoji carefully to make the product feel internet-native

### Suggested Color Logic

For mood layer:

- Funny: yellow / warm tone
- Angry: red
- Sad: blue
- Chaotic: purple
- Wholesome: green
- Political: orange
- Sports: bright accent color

Actual implementation can use neutral map colors first and add mood-based highlighting later.

### Tooltip Design

Tooltip should be compact.

Example:

```txt
🇯🇵 Japan
Mood: 😂 Chaotic funny

Top News:
Japan’s latest headline summarized in one sentence.

Trending Meme:
A short explanation of the meme or trend.

Keywords: anime, election, baseball
Updated 12 min ago
```

### Country Detail Panel

The side panel can include:

- Larger country header
- Top news card
- Meme/trend card
- Internet mood card
- Keyword chips
- Source list
- “Why this is trending” section
- “Explain this like I’m not from here” section

---

## 8. Recommended Tech Stack

### Frontend

- Next.js
- TypeScript
- React
- Tailwind CSS
- D3 geo or react-simple-maps
- Framer Motion for animation
- shadcn/ui for components

### Backend

Choose one:

- Next.js API routes for faster MVP
- Node.js + Express for separate backend
- Python FastAPI if AI/data processing is heavier

### Database / Storage

For MVP:

- Supabase Postgres or PostgreSQL
- Redis or Upstash Redis for caching

### AI Layer

Use an LLM for:

- News summarization
- Meme explanation
- Mood classification
- Keyword extraction
- Translation or cultural context

### Deployment

- Vercel for frontend
- Supabase for database
- Upstash Redis for cache
- Cron jobs through Vercel Cron, GitHub Actions, or a queue worker

---

## 9. High-Level Architecture

```txt
External APIs
   ↓
Data Fetcher / Cron Worker
   ↓
Normalization Layer
   ↓
AI Summarization + Meme Explanation
   ↓
Database
   ↓
Redis Cache
   ↓
API Layer
   ↓
Interactive Map Frontend
```

Important principle:

> Hover interactions should never call external APIs directly.

Instead:

- Backend updates country data every 10–60 minutes.
- Frontend reads cached country data instantly.
- Tooltip should appear immediately on hover.

---

## 10. Data Model

### Country Trend Object

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
    "platform": "Reddit",
    "explanation": "Why people are sharing this.",
    "media_url": "https://example.com/media.gif",
    "source_url": "https://example.com/post",
    "confidence": 0.78
  },
  "mood": {
    "label": "chaotic",
    "emoji": "🔥",
    "reason": "Several top posts are political and humorous."
  },
  "keywords": ["anime", "election", "baseball"],
  "trend_score": 82,
  "updated_at": "2026-07-06T12:05:00Z"
}
```

---

## 11. API Design

### GET `/api/countries`

Returns all supported countries and their latest cached trend summaries.

### GET `/api/countries/:iso2`

Returns detailed country data.

### GET `/api/trending?country=JP`

Returns current news, memes, mood, and keywords for a country.

### POST `/api/refresh-country/:iso2`

Manually refreshes one country.

Should probably be admin-only.

### GET `/api/layers/mood`

Returns mood data for coloring the map.

### GET `/api/layers/news`

Returns news intensity data.

### GET `/api/layers/memes`

Returns meme/trend intensity data.

---

## 12. Data Sources

### News Sources

Possible options:

- GDELT
- NewsAPI
- Google News RSS feeds
- MediaStack
- Event Registry

For MVP, use one or two news sources only.

Recommended MVP setup:

- GDELT for global coverage
- NewsAPI for simpler top-headline retrieval, if available

### Meme / Trend Sources

Possible options:

- Reddit API
- GIPHY API
- YouTube Data API
- Google Trends, if accessible through a third-party source
- TikTok Research API, only if eligible
- Country-specific subreddits
- Public RSS feeds from culture/news sites

Meme detection is harder than news detection, so for MVP it is acceptable to start with:

- Reddit posts
- GIPHY trending/search results
- YouTube trending/search results

---

## 13. Meme Detection Strategy

Memes are noisy, local, and platform-dependent. Do not assume the first viral post is actually representative.

### Basic MVP Strategy

For each country:

1. Pull candidate trends from Reddit, GIPHY, and YouTube.
2. Search using the country name, major cities, local language keywords, and news keywords.
3. Score candidates by:
   - Recency
   - Upvotes/views/engagement
   - Relevance to country
   - Whether multiple sources mention the same topic
4. Use AI to explain the top candidate.
5. Attach confidence score.

### Example Confidence Rules

High confidence:

- Multiple platforms mention the same trend
- Source has strong engagement
- Country relevance is obvious

Medium confidence:

- One strong platform signal
- Country relevance is likely but not certain

Low confidence:

- Trend is generic
- Country connection is unclear
- Source data is weak

---

## 14. Mood Classification

Mood labels should be simple and readable.

Recommended labels:

- funny
- angry
- sad
- chaotic
- wholesome
- political
- shocked
- proud
- sports-crazy
- pop-culture
- serious
- uncertain

### Mood Output Example

```json
{
  "label": "chaotic",
  "emoji": "🔥",
  "reason": "The dominant news and meme topics are political, fast-moving, and heavily debated.",
  "confidence": 0.72
}
```

---

## 15. AI Prompts

### News Summarization Prompt

```txt
You are an editorial summarizer for a global interactive news map.

Given 3-5 recent news headlines and article snippets from one country, return a concise JSON object.

Rules:
- Do not sensationalize.
- Do not invent facts.
- Prefer the story that appears most important, widely covered, or nationally relevant.
- Write for a global audience.
- Explain local context when necessary.
- Keep the summary under 35 words.
- Output valid JSON only.

Input:
Country: {{country}}
Articles:
{{articles}}

Return:
{
  "top_headline": "",
  "summary": "",
  "why_it_matters": "",
  "keywords": ["", "", ""],
  "mood_label": "",
  "mood_emoji": "",
  "confidence": 0.0
}
```

### Meme Explanation Prompt

```txt
You are a cross-cultural meme explainer.

Given a trending meme, Reddit post, GIF title, video title, or hashtag from a country, explain it to someone outside that culture.

Rules:
- Be concise.
- Explain why people find it funny, controversial, or relatable.
- Do not over-explain obvious jokes.
- Avoid offensive stereotypes.
- If the meme is political, explain neutrally.
- If the input is unclear, say that confidence is low.
- Output valid JSON only.

Input:
Country: {{country}}
Platform: {{platform}}
Meme title or text: {{meme_text}}
Context: {{context}}

Return:
{
  "meme_title": "",
  "plain_english_explanation": "",
  "why_people_are_sharing_it": "",
  "tone": "funny | angry | ironic | wholesome | chaotic | political | sad",
  "local_context": "",
  "confidence": 0.0
}
```

### Mood Classification Prompt

```txt
You classify the internet mood of a country based on recent news and meme signals.

Input:
Country: {{country}}
News summary: {{news_summary}}
Meme explanation: {{meme_explanation}}
Keywords: {{keywords}}

Choose one mood label from:
funny, angry, sad, chaotic, wholesome, political, shocked, proud, sports-crazy, pop-culture, serious, uncertain

Return valid JSON only:
{
  "mood_label": "",
  "mood_emoji": "",
  "reason": "",
  "confidence": 0.0
}
```

---

## 16. Frontend Components

Suggested structure:

```txt
src/
  app/
    page.tsx
    api/
  components/
    WorldMap.tsx
    CountryTooltip.tsx
    CountryPanel.tsx
    LayerSwitcher.tsx
    SearchCountry.tsx
    MoodLegend.tsx
    NewsCard.tsx
    MemeCard.tsx
    SourceList.tsx
    EmptyState.tsx
  lib/
    countries.ts
    mapUtils.ts
    api.ts
    mockData.ts
  types/
    country.ts
```

### Component Responsibilities

#### `WorldMap.tsx`

- Render world map from GeoJSON
- Handle hover and click state
- Apply country colors based on active layer
- Pass selected country to tooltip and panel

#### `CountryTooltip.tsx`

- Show compact country trend summary
- Follow cursor or anchor near hovered country
- Hide on mouse leave

#### `CountryPanel.tsx`

- Show detailed country data
- Include news, meme, mood, keywords, and sources

#### `LayerSwitcher.tsx`

- Toggle between:
  - News Layer
  - Meme Layer
  - Mood Layer

#### `MoodLegend.tsx`

- Explain map colors and emoji labels

---

## 17. Pages

### Home Page

Main map experience.

Sections:

- Header
- Layer switcher
- Search bar
- Interactive world map
- Tooltip
- Country detail panel
- Footer/source disclaimer

### Country Detail Page, Optional Later

URL example:

```txt
/country/JP
```

This can show a full history of Japan’s trends.

### About Page

Explain:

- How data is collected
- How summaries are generated
- Limitations
- Source attribution
- Safety/moderation policy

---

## 18. Development Roadmap

### Phase 1: Prototype

Goal: prove the interactive experience.

Tasks:

- Build static world map
- Add hover highlight
- Add tooltip
- Add click-to-open side panel
- Use mock data for 20 countries
- Add dark-mode visual style

Deliverable:

- A polished frontend demo with fake data

### Phase 2: Data API

Goal: replace mock data with backend data.

Tasks:

- Build country data schema
- Add API endpoints
- Store country trend records
- Add cache layer
- Create manual refresh endpoint

Deliverable:

- Frontend reads real backend data

### Phase 3: News Integration

Goal: generate real top-news summaries.

Tasks:

- Connect news API
- Fetch 3-5 articles per country
- Summarize with AI
- Extract keywords
- Add source attribution

Deliverable:

- Each MVP country shows real news

### Phase 4: Meme Integration

Goal: add meme/trend layer.

Tasks:

- Connect Reddit/GIPHY/YouTube sources
- Generate meme candidates
- Score candidates
- Explain selected meme with AI
- Add confidence score

Deliverable:

- Each country has at least one meme/trend card

### Phase 5: Mood Layer

Goal: make the map visually expressive.

Tasks:

- Classify country mood
- Add color legend
- Add layer switcher
- Add trend score

Deliverable:

- Users can switch between news, memes, and mood

### Phase 6: Polish and Launch

Goal: make it shareable.

Tasks:

- Improve animations
- Add mobile layout
- Add share cards
- Add SEO metadata
- Add source and AI disclaimer
- Add analytics

Deliverable:

- Public MVP launch

---

## 19. Suggested Cursor / Claude Code Prompt

Use this to generate the first version of the frontend:

```txt
Build a polished prototype for an interactive world map web app called GlobeMood.

Tech stack:
- Next.js
- TypeScript
- React
- Tailwind CSS
- D3 geo or react-simple-maps
- Framer Motion

Product idea:
A dark-mode interactive world map where users hover over a country to see that country’s hottest news, latest meme, internet mood, and trending keywords.

Requirements:
- Render a world map from GeoJSON.
- Each country should be hoverable.
- On hover, highlight the country with a smooth transition.
- Show a floating tooltip near the cursor.
- Tooltip should display:
  - flag
  - country name
  - top news headline
  - one-sentence summary
  - trending meme title
  - meme explanation
  - mood emoji and label
  - 3 keyword chips
  - updated time
- On click, open a right-side detail panel.
- Add a layer switcher with three modes:
  - News
  - Memes
  - Mood
- Use mock data for 20 countries.
- Use clean component structure:
  - components/WorldMap.tsx
  - components/CountryTooltip.tsx
  - components/CountryPanel.tsx
  - components/LayerSwitcher.tsx
  - components/MoodLegend.tsx
  - lib/mockData.ts
  - types/country.ts
- Make the UI feel modern, dark, editorial, playful, and internet-native.
- Add loading, empty, and error states.
- Make the layout responsive.
```

---

## 20. Safety, Trust, and Quality Notes

Because this product summarizes news and memes, it needs clear safeguards.

### Must-Have Rules

- Always show source links for news.
- Do not present AI summaries as original reporting.
- Add timestamps.
- Add confidence scores for memes.
- Clearly mark uncertain meme explanations.
- Avoid stereotypes when explaining national cultures.
- Avoid showing graphic or hateful meme content directly.
- Add moderation filters for slurs, hate, violence, and adult content.

### Disclaimer Example

```txt
GlobeMood uses public web signals and AI-generated summaries to show what may be trending in different countries. Summaries can be incomplete or imperfect. Always check original sources for full context.
```

---

## 21. Success Metrics

Track:

- Average session duration
- Number of countries hovered per session
- Number of country panels opened
- Layer switch usage
- Share button usage
- Return visits
- Source link clicks
- Most viewed countries
- Tooltip engagement rate

### Strong Signal of Product-Market Fit

Users spend time exploring countries they did not originally search for.

---

## 22. Future Feature Ideas

### Feature Ideas

- Time machine: see what was trending yesterday, last week, or last month
- Compare two countries side by side
- “Explain this meme” deep-dive mode
- Global mood timeline
- Breaking-news pulse animation
- Creator mode for finding content ideas
- Weekly global meme report
- Country leaderboard by chaos/funny/angry score
- Browser extension
- Embeddable map widget for blogs and news sites

### Social Sharing Ideas

- “Today’s internet mood in Japan is chaotic.”
- “The world is arguing here, laughing there.”
- “Guess which country is the funniest today.”
- “Your daily passport to global internet culture.”
- “One map. Every country’s main character moment.”

---

## 23. Main Risks

### Data Quality Risk

Some countries may have limited accessible meme data.

Mitigation:

- Add confidence scores
- Start with 20 countries
- Use multiple sources
- Show “not enough signal” states

### Cultural Misinterpretation Risk

AI may misunderstand local memes.

Mitigation:

- Ask AI to explain uncertainty
- Use local source context
- Avoid definitive claims when confidence is low

### API Cost Risk

Real-time API calls can become expensive.

Mitigation:

- Use cron refreshes
- Cache aggressively
- Do not fetch on every hover
- Limit MVP to 20 countries

### News Bias Risk

Different sources may frame stories differently.

Mitigation:

- Pull multiple sources
- Show source attribution
- Avoid overly opinionated summaries

---

## 24. Recommended First Build

The best first build is not a perfect data system. It is a beautiful prototype.

Start with:

1. Next.js frontend
2. SVG world map
3. 20 countries
4. Mock data
5. Hover tooltip
6. Click side panel
7. Layer switcher
8. Dark-mode design

Once the product feels exciting with fake data, connect real APIs.

---

## 25. Final Product Direction

This should not feel like a traditional news website.

It should feel like:

- Google Maps for global internet culture
- A live dashboard of the world’s mood
- A meme passport
- A social listening tool disguised as a fun map
- A daily habit for curious internet users

Final positioning:

> GlobeMood is an interactive world map that shows what every country is talking about, laughing at, and arguing over today.
