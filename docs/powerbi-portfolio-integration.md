# Power BI — portfolio integration plan

**Not to be actioned until a real report exists.** Nothing in `ooh.html`, `index.html`,
`projects.html` or the README changes before then. Every current claim says the companion
is *prepared*, which is accurate.

---

## Where it goes

`ooh.html` currently runs:

```
  01  Where it came from
  02  The problem
  03  What it does
  04  Evidence
  05  How it is built          ← architecture, pipeline, validation
  06  What it deliberately does not do
```

**Insert the Power BI section as a new `06`, after "How it is built" and before the
limitations**, renumbering the limitations to `07`.

That position is correct because the section's argument depends on the architecture the
reader has just seen — one pipeline, one set of definitions, two surfaces — and because
the limitations should stay last, where they close the page honestly.

No navigation change. No homepage change beyond one stack chip (below).

## The section

**Heading:** `An executive companion, built on the same pipeline`

**Copy** (~110 words, matching the page's register):

> The web app is the monitoring product: it tells you what needs attention today and what
> acting would mean. It answers fixed questions in a fixed order.
>
> Some questions are not fixed. *Is the exposure worse by market or by format? Does that
> change per campaign?* A Power BI companion reads the same star schema exported from the
> same pipeline, and lets the analyst decompose exposure in whatever order they choose —
> campaign, then market, then format, then placement, or any other path.
>
> The two share one set of definitions. Gross shortfall means the same thing in both, and
> a validation table checks that Python, SQL and DAX agree before anything is published.

**Artifacts, in this order:**

1. `pbi-decomposition.gif` — the decomposition tree being drilled. **Lead with this.** It
   is the one capability the web app does not have, and motion shows it better than a
   still.
2. `pbi-01-executive.png` — the executive page.
3. `pbi-02-rootcause.png` — only if it adds something the GIF did not.

Use the existing `.shot` frame with a `figcaption`. Images go in `assets/` on the
portfolio repo, copied from `docs/screenshots/` as the analyzer screenshots already are.

### Capture specification

| Artifact | Capture at | Crop | Notes |
|---|---|---|---|
| `pbi-01-executive.png` | **1600 × 1000** | Full page, including the synthetic-data footnote | The portfolio renders at 760px CSS width, so 1600 gives a clean 2× for retina. Do not crop the footnote out — it is the disclosure |
| `pbi-02-rootcause.png` | **1600 × 1000** | Full page | Capture with the tree **expanded two or three levels**, not at its root. A collapsed tree looks like an empty visual |
| `pbi-03-detection.png` | **1600 × 900** | Full page | Optional; only if a third still earns its place |
| `pbi-decomposition.gif` | **1200 × 750** | Crop to the tree itself, not the whole page | 6–10 seconds, ≤ 4 MB, no cursor trail. Drill exposure → campaign → market → format, pausing ~1s per level so it is readable |

Export each page with Power BI's own **Export → PDF** as a backup if screen capture gives
poor text rendering, then crop the PDF page to PNG.

All four are **lazy-loaded** and sit below the fold, so file size is less critical than
legibility. Prefer sharp over small.

**Alt text** must describe what the visual shows, not that it is a screenshot — e.g.
*"The decomposition tree breaking media-value exposure down by campaign, then market,
then format."*

**Links row:** `[Open the report ↗]` *(only if Publish to web worked)* ·
`[Semantic model & DAX ↗]` → the `docs/` folder on GitHub.

### If Publish to web is unavailable — exactly what changes

| Element | With a public link | Without |
|---|---|---|
| `[Open the report ↗]` button | First in the links row, `btn primary` | **Remove entirely.** Do not disable it, do not leave it greyed, do not link to a sign-in page |
| `[Semantic model & DAX ↗]` | Second | Becomes the only button, promoted to `btn primary` |
| Closing sentence of the copy | — | Append: *"The report runs in Power BI Service; the model, measures and validation are public here."* |
| GIF | Supporting | **Becomes the primary artifact** — it is now the only way a reader sees the thing move. Place it first, full width |
| Everything else | unchanged | unchanged |

**Never ship a link that asks a recruiter to sign in.** A dead link costs more credibility
than a missing one, and the GIF carries the demonstration on its own.

**Stack chips to add:** `Power BI` · `DAX` · `Star schema` — to this section only, not to
the page header.

## What must NOT be repeated from the web app

| Do not rebuild in the Power BI section | Why |
|---|---|
| The Attention Centre queues and action copy | The product's job, not the report's |
| The flight timeline | Already on this page, better told |
| The gross→net waterfall explanation | Already explained in `03`; the report's waterfall is an *example of the model*, not a second teaching moment |
| Any screenshot that looks like the web app | If the two look alike, the reader concludes one is redundant |

The section earns its place only by showing what is *different*: a semantic model, a
measure layer, and free-form decomposition.

## Elsewhere on the portfolio

| Location | Change | When |
|---|---|---|
| `index.html` OOH entry, `.proof` line | Append ` · Power BI` to the stack line | After build |
| `projects.html` OOH entry | Same | After build |
| Experience page toolkit | Add `Power BI` to *Analytics & data* | After build |
| Homepage hero / credibility row | **No change** | — |
| Analyzer README | `Power BI companion: model prepared, report authoring pending` → replace with the live link or the screenshots path | After build |

## Sequence when the report lands

1. Capture screenshots + GIF per the checklist
2. Fill in `docs/powerbi-plan.md` definition-of-done
3. Add section `06` to `ooh.html`, renumber limitations to `07`
4. Add the three stack chips
5. Update the README line
6. Re-run the live QA sweep
7. Then, and only then, the resume lines in `docs/resume-update-backlog.md` marked
   *SAFE AFTER POWER BI EXISTS*
