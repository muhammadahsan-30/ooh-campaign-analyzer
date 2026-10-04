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

**Links row:** `[Open the report ↗]` *(only if Publish to web worked)* ·
`[Semantic model & DAX ↗]` → the `docs/` folder on GitHub.
If there is no public link, drop the first button entirely. **Never ship a link that
asks a recruiter to sign in.**

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
