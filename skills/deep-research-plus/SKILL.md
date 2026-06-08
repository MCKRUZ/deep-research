---
name: deep-research-plus
description: 'Thorough, citation-verified research that wraps Claude Code''s built-in deep-research workflow and adds community-sentiment (Reddit), a polished self-contained HTML report, and an organized on-disk output folder. Use when the user wants a deep multi-source report — "research X", "go deep on Y", "compare A vs B vs C", survey/landscape a topic — especially when practitioner/community sentiment or a saved HTML deliverable matters. Not for single-fact lookups answerable in one search.'
---

# Deep Research Plus

## What this is

A thin orchestration skill. It does **not** re-implement search or verification — it
delegates the heavy lifting to Claude Code's **built-in `deep-research` workflow**
(deterministic 5-angle fan-out → fetch 15 sources → 3-vote adversarial verification →
synthesis), then adds four things the built-in lacks:

1. **Community sentiment** via `reddit_search` (Bifrost/Apify) — the built-in is WebSearch-only.
2. **A polished, self-contained HTML report** rendered from `report-template.html`.
3. **A deterministic on-disk output folder** (`research/YYYY-MM-DD-<slug>/`).
4. **User-facing scoping** — the workflow can't talk to the user; this skill does.

## When to use

- "Research X", "go deep on Y", "compare A vs B vs C", "survey the state of Z",
  landscape/market scans, technical deep-dives needing many reconciled sources —
  **especially** when you also want real-world community sentiment or a saved HTML report.
- **Skip** for a single fact — one `WebSearch` answers it; just answer directly.

## The flow: Scope → Delegate → Sentiment → Synthesize → Render → Save

### 1. Scope (you do this — the workflow can't)

Ask at most **3 clarifying questions** that most reduce ambiguity (intent, depth,
boundaries). If the user said "just go" / "you decide", or the request is already
specific, skip asking. Compress to a single **refined question string** — this is what
you hand the workflow. Pick a 3–6 word kebab-case **`<slug>`** from it now (for the folder).

### 2. Delegate to the built-in workflow

Call the **Workflow** tool with `name: "deep-research"` and `args: "<refined question>"`.
(A skill instructing this call is an explicit, legitimate Workflow opt-in.) Wait for it
to complete and take its structured result. **Do not re-implement search/verify** — the
workflow owns that, including the adversarial pass.

It returns this shape (happy path):

```jsonc
{
  question, summary,                                  // summary = 3–5 sentence answer
  findings: [{ claim, confidence:"high|medium|low",
               sources:[url], evidence, vote:"3-0" }],
  caveats, openQuestions:[string],
  refuted: [{ claim, vote, source }],
  sources: [{ url, quality:"primary|secondary|blog|forum|unreliable", angle, claimCount }],
  stats:   { angles, sourcesFetched, claimsExtracted, claimsVerified,
             confirmed, killed, afterSynthesis, urlDupes, budgetDropped, agentCalls }
}
```

Read whatever JSON comes back and adapt — don't hard-code field access. Handle the
workflow's degraded returns honestly:

- `findings: []` with a "no claims"/"all refuted"/"synthesis failed" `summary` →
  report that outcome plainly, still surface `refuted` and `sources` for transparency,
  and flag the report banner as a warning. **Never fabricate findings to fill a gap.**
- `{ error: ... }` (e.g. no question) → fix the input and re-invoke.

**Fallback (only if the built-in workflow is unavailable** — older/newer Claude Code
without it): run the same contract yourself — decompose into 4–6 angles, parallel
`Task` sub-agents to search→fetch→extract cited claims, a skeptical verification pass,
then synthesize. Mirror the schema above so the rest of this skill is unchanged.

### 3. Community sentiment (in parallel with step 2 when possible)

Run `reddit_search` (Bifrost/Apify — bypasses Reddit's bot block, needs no Reddit creds)
on the topic. Pull the most relevant posts/threads with upvotes. Optionally widen with
Hacker News (WebSearch + the HN Algolia API) and GitHub issues. Capture: the prevailing
sentiment, notable agreements/disputes, and concrete gotchas practitioners report.
Treat this as **signal, not verified fact** — label it as sentiment and keep it separate
from the workflow's citation-verified findings.

### 4. Synthesize (don't concatenate)

Weave the workflow's verified `findings` into a coherent Markdown report that directly
answers the refined question. Then add a clearly-labelled **Community sentiment** section
from step 3. Preserve every `[n]` citation, built from the workflow's `sources`. Carry
the workflow's `caveats` and `openQuestions` through. Keep verified findings and
unverified sentiment visibly distinct.

`report.md` structure:

- H1 title + the workflow's executive `summary`.
- Body sections that integrate across findings (with `[n]` citations).
- **Community sentiment** (labelled as unverified signal).
- **Caveats** and **Open questions**.
- **Sources** list (`[n]` → title + URL), built only from `sources` actually used; mark
  any `quality: forum/blog/unreliable` source as such.
- **Verification** note from `stats`: e.g. "24 verified · 21 confirmed · 3 refuted".

### 5. Render the HTML report

Clone `report-template.html` (in this skill folder) and fill its slots — keep it one
self-contained, print-friendly file (no external assets):

- `{{TITLE}}`, `{{QUERY}}` (refined question), `{{DATE}}`.
- `{{TIER}}` — describe the run from `stats`, e.g. `deep · 5 angles · 15 sources`.
- Verification banner: `{{VERIFY_CLASS}}` = `warn` if `stats.killed > 0`, any finding is
  low-confidence, or `findings` is empty; else `ok`. `{{VERIFY_TEXT}}` e.g.
  "24 verified · 21 confirmed · 3 refuted".
- `{{SUMMARY}}`, `{{BODY}}` (`<section><h2>…</h2><p>…</p></section>` blocks; cite inline
  with `<a class="cite" href="#s3">3</a>`), `{{SOURCES}}`
  (`<li id="s1"><span class="num">1</span><span class="title">…</span>
<span class="tag web">web</span><span class="url">…</span></li>`; tag class
  `web`/`academic`/`code`/`forum` by source).

### 6. Save (output protocol)

Reports always go to a predictable location — never the cwd ad hoc. Each topic gets its
own folder:

1. **Project root** = git repo root (`git rev-parse --show-toplevel`); else the cwd.
2. **Research base** = a `research/` folder at that root (create if missing). If the
   project already has `_research/` or `docs/research/`, use that instead. **No project**
   (home/temp, no repo) → use `~/research/`.
3. **Per-topic folder:** `<base>/YYYY-MM-DD-<slug>/` (the slug from step 1).
4. Write **`report.md`** and **`report.html`** there; any extra artifacts go beside them.
5. Tell the user the **exact path(s)** written, and offer to open the HTML.

## Tool map (this environment)

- **Core search/verify:** the built-in `deep-research` workflow (delegated in step 2).
- **Community sentiment:** `reddit_search` (Bifrost/Apify); also HN (Algolia API) + GitHub issues.
- **Synthesis gap-filling / fallback search:** `WebSearch` → `WebFetch`; `firecrawl`
  (Bifrost) for JS-rendered/auth-walled/whole-site; `context7` for library/API signatures;
  `microsoft_learn` for .NET/Azure and as an Azure-OpenAI mirror; `YouTube` (Bifrost) for
  conference talks; `sequential_thinking` (Bifrost) for tangled trade-offs.

## Common mistakes

- Re-implementing search/verify instead of delegating to the built-in workflow.
- Letting Reddit sentiment masquerade as verified fact — keep it labelled and separate.
- Fabricating findings when the workflow returns an empty/all-refuted result — report the
  real outcome instead.
- Hard-coding the workflow's return fields — read the JSON and adapt.
- Saving to the cwd ad hoc instead of `research/YYYY-MM-DD-<slug>/`.
- A "Sources" list containing URLs that weren't actually in the workflow's `sources`.
- Skipping scope on an ambiguous request — produces shallow, off-target reports.
