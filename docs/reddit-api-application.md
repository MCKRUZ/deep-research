# Reddit API Access Application — copy-paste answers

**Intake form (2026):** https://support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14868593862164
(Reddit's "API Access Request" / "Data Access Request" ticket. Self-service app
creation ended Nov 2025; this manual request is the only route now.)

**Use-case type to pick:** Developer / non-commercial (NOT Researcher — that branch
demands university + IRB ethics docs; NOT Enterprise — that's a paid contract).

> Honest odds: personal/non-commercial scripts are the lowest-approval category.
> The answers below are written to maximize odds: concrete, read-only, narrow,
> with a privacy policy and a deletion statement. Generic/vague applications get
> auto-rejected ("not in compliance / lacks necessary details").

---

## Field answers

**App name**
```
deep-research
```

**Use-case description** (the field that decides it — concrete, names what/how/where)
```
deep-research is a personal, non-commercial command-line tool I built for my own
use. It reads public posts and comments from a small set of technical subreddits
and synthesizes them into cited research summaries that I read privately. It is
strictly read-only — it never posts, comments, votes, messages, or moderates.
Reddit content is fetched on demand only when I run a research query, processed
in memory to extract the relevant discussion, and discarded once the summary is
generated. Nothing is stored, cached, republished, redistributed, sold, or used
to train models. It runs locally on my own hardware, for an audience of one (me).
```

**Data / API actions requested** (scope it to read-only; do not over-request)
```
Read-only access: search posts (search), read post and comment listings
(comments, hot, top, new) and subreddit metadata (about). No write actions.
OAuth scope: read.
```

**Subreddits you will access**
```
Primarily: r/LocalLLaMA, r/MachineLearning, r/LLMDevs, r/ClaudeAI,
r/ChatGPTCoding, r/artificial, r/OpenAI. Occasionally other public technical
subreddits relevant to a specific research question.
```

**Expected request volume**
```
Very low and bursty — typically under 200 requests per day, and only when I
actively run a query (often none on a given day). Far below the 100 queries/min
free tier.
```

**Platform / app type**
```
Script app — personal, server-side, runs on my own machine. Not distributed to
any other users.
```

**Website / About URL**
```
https://gist.github.com/MCKRUZ/7ff05d0ed8932c491eedef1f6fa56edf
```

**Redirect URI** (required even though unused for read-only)
```
http://localhost:8080
```

**Privacy policy URL**
```
https://gist.github.com/MCKRUZ/7ff05d0ed8932c491eedef1f6fa56edf
```

**Commercial use?**
```
No. Personal, non-commercial, no monetization of any kind.
```

**Data deletion / 48-hour compliance** (Reddit requires you address this)
```
The tool retains no Reddit data. Content is fetched live per query, used
transiently to produce a summary, and never persisted or cached — so removed or
deleted content is never retained. Every query operates on current live data.
```

---

## Privacy policy (host this — see step in the walkthrough)

```
Privacy Policy — deep-research

deep-research is a personal, non-commercial tool operated by Matthew Kruczek for
individual use only.

- Data accessed: public Reddit posts and comments via the Reddit API, read-only.
- Use: content is fetched on demand, processed in memory to produce a research
  summary read solely by the operator, then discarded.
- Storage: no Reddit data is persisted, cached, shared, sold, or used for model
  training.
- Deletion: because no data is stored, deleted or removed Reddit content is not
  retained; each query uses live data.
- Contact: matthewkruczek@yahoo.com

Last updated: 2026-06-01
```
