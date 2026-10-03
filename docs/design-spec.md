# Visual specification — OOH Campaign Analyzer

Proposed redesign of `public/`. **Nothing here is implemented yet.** This document
exists to be argued with before any CSS is written.

The product is and remains the **OOH Campaign Performance Analyzer**. "Monitor" below
names the internal design system only — it is not a product name and does not appear
in the interface. Component-level reasoning lives in `docs/product-audit.md`; where the
two documents disagree, the audit is newer and wins.

Scope note: this is a *presentation* specification. It does not change the analytical
architecture — Python still computes every number, `app.js` still only renders
(`CLAUDE.md`, "Python computes, the browser renders"). Where a surface below needs a
number the payload does not yet carry, it is marked **[needs metric]** and belongs in
`src/metrics.py` with a unit test, never in JavaScript.

Every figure quoted in the wireframes is a real value computed from `data/ooh.db` at
the as-of date 2026-09-10, not a placeholder.

---

## 0. The numbers the design has to carry

Computed from the shipped dataset before any layout was drawn, because the layout
should fit the data rather than the other way round.

| Figure | Value |
|---|---|
| Delivery to plan (portfolio) | **97.1%** — 415.1m verified of 427.7m contracted to date |
| Media value at risk (billed shortfall, 61 flagged) | **$152,435** |
| — of which completed / to reconcile | $101,588 (37 placements) |
| — of which live / already incurred | $50,844 (24 placements) |
| Still preventable over the remaining flight **[needs metric]** | **$60,048** |
| Live issues ≥ $1,000 preventable **[needs metric]** | 11, holding $53,496 |
| Placements monitored | 595 — 205 live, 390 closed |
| On track (≥ −5%) / Flagged (< −5%) | 534 / 61 |
| Gross shortfall (before netting) | **17.1m impressions**, 4.0% of contracted to date |
| — masked by over-delivery elsewhere | 4.5m, **26.3% of gross** |
| Campaigns | 8 — 3 live, 5 closed |
| Spend billed to date | $5.41m |

Two of those are different quantities and **the interface must never add them**:

- **$152,435** is billed shortfall *already incurred*.
- **$60,048** is *additional* exposure that accrues over the remaining flight if the
  24 live issues stay unfixed.

Live campaign pacing, which drives the pacing board:

| Campaign | Client | Flight elapsed | Delivered (of full contract) | Variance to date | Flagged | At risk |
|---|---|---|---|---|---|---|
| 6 | Solstice Retail | 26.8% | 25.6% | −4.5% | 7 | $14,042 |
| 7 | Aurora Beverages | 52.4% | 49.9% | −4.8% | 11 | $17,037 |
| 8 | Nimbus Telecom | 76.2% | 73.8% | −3.1% | 6 | $19,765 |

Exposure concentration, which drives the ranked bars and the callouts:

- Markets: Toronto **$74,205** (49% of all exposure), Vancouver $27,762,
  Montreal $27,132, Edmonton $15,629, Ottawa $4,535, Calgary $3,174
- Formats: digital screen **$83,310**, bulletin $45,552, transit shelter $14,057,
  mall panel $9,515
- Campaign 8: its five worst placements carry **72%** of gross shortfall;
  Toronto alone is **73%** of its net shortfall
- Campaign 7: Toronto is **64%** of net shortfall

---

## 1. Proposed design language

**Name:** Monitor — the *design system's* name, used in code and tokens only. The
product is the OOH Campaign Performance Analyzer everywhere a user can see.

**One sentence:** a quiet graphite-and-paper instrument where the only saturated colour
on screen is either data or a status, so when something turns red it means something.

### Five principles

1. **Chrome is achromatic.** Brand, navigation, buttons and borders are graphite and
   paper. No brand hue competes with the data layer.
2. **One hero number per view.** Exactly one figure is set large. Everything else is a
   supporting tile. (Twelve identical KPI cards is the failure mode being designed out.)
3. **Colour is vocabulary, not decoration.** Five meanings, five colours, fixed
   forever: on track, watch, needs attention, inactive, analytic.
4. **Air before ink.** Thin marks, hairline rules, generous padding. Density comes from
   good alignment, not from removing whitespace.
5. **Never imply more than the data supports.** No sparklines, no forecasts, no
   trend arrows on a dataset with no temporal signal. Honesty is part of the design.

### The one identity change being proposed

The current accent `--amber: #ff7a45` is used for **both** the brand (logo, nav button,
links) **and** for alerts and under-delivery. That is a real problem, not a taste call:
it is the "status colour used for a non-status element" anti-pattern. If the logo, the
primary button and the under-delivery bars are all the same orange, orange stops
meaning "something is wrong."

**Proposal:** brand chrome becomes graphite; the interactive accent becomes blue
(`#2a78d6` light / `#3987e5` dark), which is also the single analytic series colour;
amber is released back to mean *watch* and nothing else. The favicon and the `OA` logo
mark change accordingly.

This is the one proposal in this document that changes the project's existing identity,
so it is called out rather than slipped in.

---

## 2. Navigation structure

**Decision: a sticky top bar with section tabs. Not a sidebar.**

Reasoning, since the brief leaves the choice open:

- The analytical content here is **wide** — the placement table carries 9–11 columns.
  A 240px sidebar is 19% of a 1280px laptop viewport taken permanently from the widest
  content on the page.
- A sidebar's advantage is deep or nested navigation. This product has **seven flat
  sections**. There is nothing to nest.
- On mobile a sidebar becomes a hamburger drawer — an extra tap and an extra component
  to build and make accessible — whereas a tab strip degrades into a scrollable strip
  with no new interaction model.
- Stripe and Vercel both run top navigation over wide data views. The "software, not
  webpage" feeling comes from the **persistent shell, view switching and active state**,
  not from the nav being vertical.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ ◼ OOH Campaign Analyzer  Overview  Attention ⑪  Campaigns  Markets  Inventory    │
│                          Efficiency  Method      │ as of 10 Sep 2026 │  ◐  ↗ Repo │
└──────────────────────────────────────────────────────────────────────────────────┘
     ▲ graphite mark          ▲ active tab: filled pill, aria-current="page"
                                        ▲ count badge on Attention only
```

- Sections are **views**, not scroll anchors: one visible at a time, switched in
  120ms. The shell never re-renders.
- `location.hash` syncs (`#attention`, `#campaign/7`) so sections are linkable and the
  browser Back button works. This is the single cheapest thing that makes a static page
  feel like an application.
- The **as-of chip** is permanent in the bar. Every number in the product is measured to
  that date and it should never be more than one glance away.
- The Attention tab carries a live count badge. It is the only badge in the nav.
- `◐` toggles theme, persisted in `localStorage`.

---

## 3. Page hierarchy — the narrative

The layout is determined by this sequence, as the brief requires:

```
  PORTFOLIO STATUS        Overview, hero band          "is the book healthy?"
         ↓
  WHAT NEEDS ATTENTION    Overview callout → Attention "what do I do today?"
         ↓
  WHICH CAMPAIGNS         Overview pacing board        "who is causing it?"
         ↓
  WHERE IS IT CONCENTRATED Overview exposure bars      "where is the money?"
         ↓
  WHAT CAN STILL BE ACTED ON  Attention Centre         "what is still savable?"
         ↓
  DEEPER INVESTIGATION    Campaign → Market → Inventory → Efficiency → Method
```

| View | Workflow stage | Hero number |
|---|---|---|
| Overview | Monitor | 97.1% delivery to plan |
| Attention Centre | Detect + **Prioritize** | $60,048 still preventable |
| Campaigns | Monitor → Investigate | (per campaign) variance to date |
| Markets | Investigate | Toronto $74,205 |
| Inventory | Investigate | — (table-led view, no hero) |
| Efficiency | Reconcile | $13.03 blended CPM |
| Method | — | — |

---

## 4. Above-the-fold wireframe

Target: 1280 × 800 laptop, no scrolling required to answer all four questions in the
brief. Composed as one band, deliberately **not** a row of four equal cards.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ ◼ OOH Campaign Analyzer  [Overview] Attention ⑪ Campaigns …│ as of 10 Sep 2026 │◐│
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  OOH Campaign Performance Analyzer                                               │
│  Know what's falling behind before the campaign ends.          [Explore ↓]        │
│  Monitor pacing, find under-delivering placements, quantify exposure,            │
│  and act while there is still flight left.                                       │
│                                                                                  │
├──────────────────────────────────────────────────────────────────────────────────┤
│ PORTFOLIO HEALTH                                    595 placements · 8 campaigns │
│                                                                                  │
│                                      │  ▲ 24   Live issues              ›        │
│   97.1%                              │         $50.8K incurred ·                 │
│   Delivery to plan                   │         $60.0K still preventable          │
│                                      │ ─────────────────────────────────────     │
│   415.1m verified of 427.7m          │  ■ 37   Completed shortfalls     ›        │
│   expected by 10 Sep       ⓘ         │         $101.6K to reconcile              │
│                                      │ ─────────────────────────────────────     │
│   ████████████████████████████▌■▏▲▏  │  ● 534  On track                          │
│   ● 534 on track  ■ 37 completed     │         within −5% of plan to date        │
│   ▲ 24 live issues                   │                                           │
│                                      │                                           │
│   …but 17.1m impressions are short   │                                           │
│   across 314 placements. 26% of that │                                           │
│   is masked by over-delivery     ⓘ   │                                           │
│   elsewhere.                         │                                           │
├──────────────────────────────────────────────────────────────────────────────────┤
│  ▲  11 live issues each hold more than $1,000 of preventable exposure —          │
│     $53.5K of the $60.0K total.                      [Review Attention Centre →] │
└──────────────────────────────────────────────────────────────────────────────────┘
          ▽ fold
```

**Why this composition rather than four KPI cards**

- **One hero figure.** 97.1% at 56px is the only number set large. It answers "is the
  portfolio healthy?" in well under a second. Four equal 32px numbers answer nothing
  first, which is the same as answering nothing.
- **The segmented bar sits directly under the hero** because it is the hero's
  decomposition — 97.1% is an average, and the bar immediately shows the average is
  hiding 61 problems. That tension is the product's whole argument, delivered in one
  glance.
- **The "…but" line under the bar is the thesis in one sentence.** 97.1% is a *net*
  number: 17.1m impressions are genuinely short, and 26% of that is cancelled out on
  paper by other sites running hot. Stating it directly beneath the reassuring headline
  is the most important piece of copy on the first screen, and every figure in it is
  computed.
- **Segment order is On track → Completed → Live issue**, which is a colour
  requirement rather than a layout preference: green beside red fails CVD separation
  (§7), and the grey completed segment is what separates them.
- **The right column is a list, not a card grid.** Three states of the same population
  are ordered by urgency and read top to bottom like a queue. Each row is a link into
  the Attention Centre, pre-filtered. A card grid would imply four unrelated metrics.
- **The callout strip is the call to action**, and its content is computed
  (`11`, `$53.5K`, `$60.0K`), never hardcoded copy.
- **Spend to date, blended CPM, rate efficiency and reach are deliberately absent
  from the first screen.** They are secondary (§6) and appear in Efficiency and in
  campaign drill-down. Putting them here would cost the hierarchy and buy nothing a
  visitor needs in the first five seconds.

### Mobile (≤ 480px)

Hero band stacks: hero figure → segmented bar + legend → the four state rows as
full-width tappable cards → callout. Nav collapses to a horizontally scrollable tab
strip. No content is dropped above the fold; only the column structure changes.

---

## 5. Attention Centre wireframe

The visually strongest view in the product, and the one that most needs the two
categories to *look* different rather than being two tabs over identical tables.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  ATTENTION CENTRE                                                                │
│  $60,048 still preventable                                                       │
│  across 24 live issues. Completed shortfalls below are no longer recoverable.    │
│                                                                                  │
│  [ Campaign ▾ ] [ Market ▾ ] [ Format ▾ ] [ 🔍 Search placements ]      [Reset]  │
│  Showing:  Solstice Retail ×   Vancouver ×                                       │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ▲ LIVE — STILL ACTIONABLE                        24 placements · sorted by      │
│                                                   preventable exposure ▾         │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │▌ Montreal · Digital screen · Downtown            $9,678 still preventable  │ │
│  │▌ Solstice Retail — Retail drive                  ────────────────────────  │ │
│  │▌                                                 $2,117 incurred to date   │ │
│  │▌ 46.5% behind plan          41 of 56 days left                             │ │
│  │▌ ██████░░░░░░░░░░░░░░ delivered 15%                                        │ │
│  │▌ ████████░░░░░░░░░░░░ elapsed   27%                                        │ │
│  │▌                                                                           │ │
│  │▌ ⚑ Finishing whole would need 117% of planned daily delivery for the       │ │
│  │▌   remaining 41 days — above what a restored face can sustain, so the gap  │ │
│  │▌   closes with added weight or a make-good, not by catching up.      ⓘ     │ │
│  │▌                                                      [ View placement → ] │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │▌ Vancouver · Digital screen · Downtown           $8,243 still preventable  │ │
│  │  …                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                   [ Show 13 smaller issues ▾ ]   │
├──────────────────────────────────────────────────────────────────────────────────┤
│  ■ COMPLETED — RECONCILIATION REQUIRED            37 placements · $101,588       │
│                                                                                  │
│  Placement              Campaign          Flight      Delivered   Variance  Value│
│  ───────────────────────────────────────────────────────────────────────────────│
│  Toronto · Bulletin     Meridian Bank     28 d        −38.2%      1.2m    $4,106│
│  Scarborough #87        Product launch    closed 24 Aug                          │
│  ───────────────────────────────────────────────────────────────────────────────│
│  Calgary · Mall panel   Vantage Motors    42 d        −31.9%      0.4m    $3,880│
│  Macleod Trail #14      Awareness         closed 24 Oct                          │
└──────────────────────────────────────────────────────────────────────────────────┘
```

**Why the two halves are built from different components**

| | Live | Completed |
|---|---|---|
| Component | **Cards**, one per issue | **Table**, dense rows |
| Ranked by | Preventable exposure | Billed shortfall value |
| Accent | 3px red left rule, white surface, elevation | No rule, sunken surface, no elevation |
| Carries | Dual pacing bars, days left, recovery-pace sentence, action | Precision columns, closed date |
| Default shown | The 11 material issues (≥ $1,000 preventable); the 13 minor ones carry an amber ◆ chip behind a disclosure | All 37, sortable, paginated at 25 |

A card is the right shape for something you are going to *act* on: it has room for the
context sentence that tells you what acting would mean. A table row is the right shape
for something you are going to *reconcile*: a credit conversation needs precise, aligned,
comparable numbers, not prose. Giving them the same component would be the design
asserting they are the same job.

The **sunken, un-elevated, grey-chipped** treatment of the completed half is doing
semantic work: it reads as archive. Nothing in it is red, because nothing in it is
actionable — using alert red for both halves would be the "if everything is red, nothing
is important" failure.

**The recovery-pace sentence is the single most important piece of copy in the product**
and is generated from computed values, with the honest framing the data demands: a
healthy face in this model delivers 0.96–1.05× of plan, so a required pace of 1.17×
cannot be met by the booked face running normally. Required pace on the live set runs
1.06×–2.30× (median 1.35×), so this is the common case, not an edge case. The UI states
it plainly rather than implying recovery is available.

---

## 6. Visual hierarchy — three levels

| Level | Type | Treatment | Contents |
|---|---|---|---|
| **Primary** | 56px hero / 32px tile, semibold, proportional figures | Own band, maximum air | Delivery to plan · Still preventable · Value at risk · Live issue count |
| **Secondary** | 24px value + 11px eyebrow label | Tile in a group, hairline separated | Spend to date · Campaigns live · Placements monitored · Blended CPM · Off rate card · Reach & frequency |
| **Tertiary** | 13px body / 12px caption / mono for formulas | Inline, behind ⓘ, or in Method | Formulas · assumptions · column notes · technical explanation |

Rules this encodes:

- **Only one primary figure per view.** Listed per view in §3.
- Secondary tiles appear in groups of 3–4 with hairline dividers, never as four separate
  elevated cards — grouping is what stops them competing with the hero.
- Tertiary never occupies permanent layout. It lives behind progressive disclosure (§13)
  or in Method.

---

## 7. Colour & status system

Surfaces and the series colour are taken from the validated reference palette instance
rather than invented, so the documented validation holds without re-derivation.

### Tokens

| Role | Light | Dark |
|---|---|---|
| Page plane `--bg` | `#f9f9f7` | `#0d0d0d` |
| Card surface `--surface` | `#fcfcfb` | `#1a1a19` |
| Raised `--surface-raised` | `#ffffff` | `#222221` |
| Sunken `--surface-sunken` | `#f2f2ef` | `#141413` |
| Hairline `--border` | `rgba(11,11,11,.10)` | `rgba(255,255,255,.10)` |
| Rule `--border-strong` | `#e1e0d9` | `#2c2c2a` |
| Ink `--text` | `#0b0b0b` | `#ffffff` |
| Ink 2 `--text-2` | `#52514e` | `#c3c2b7` |
| Ink 3 `--text-3` | `#898781` | `#898781` |
| Accent / series-1 `--accent` | `#2a78d6` | `#3987e5` |

### Status vocabulary — five meanings, fixed

| Meaning | Colour | Glyph | Used for |
|---|---|---|---|
| On track | `#0ca30c` | ● | within −5% of plan to date |
| Needs attention | `#d03b3b` | ▲ | < −5%, live — **material** (≥ $1,000 preventable) |
| Minor live issue | `#fab219` | ◆ | < −5%, live — below the materiality cut |
| Inactive / completed | `#898781` | ■ | < −5%, flight closed |
| Analytic / neutral | `--accent` | — | quantitative bars, links, focus |

**There is no "Watch" tier.** An earlier draft of this spec proposed one at −5% to −2%.
Tested against the data it contains **128 placements and zero real faults** — every
injected fault lands at or below a 0.943 delivery index, every placement in that band
sits between 0.951 and 0.980. It would have put 128 healthy placements on screen as
warnings beside 24 genuine problems. Cut; see `product-audit.md` §3.1.

Amber is therefore reassigned to the materiality split inside the live queue, where it
does real work: 11 of the 24 live issues hold $53,496 of the $60,048 preventable
exposure, and the other 13 hold $6,552 between them.

**Status chips never colour their own text.** A chip is a coloured 8px dot plus a glyph
plus a label in a text token, on a neutral or faintly tinted ground. This keeps every
chip label at full contrast, satisfies "never conveyed by colour alone" through the
glyph, and avoids inventing dark text steps for amber.

### Validation results

Ported the reference validator (the six computable checks, Machado-Oliveira-Fernandes
severity-1.0 transforms, OKLab ΔE×100) to Python — no JS runtime on this machine — and
confirmed the port reproduces the documented reference run exactly (worst adjacent ΔE 9.1
protan, normal-vision 19.6). Run on the three colours that sit **adjacent inside the
segmented health bar**, in stack order:

```
Health bar [on track #0ca30c, completed #898781, live issue #d03b3b]

              light (#fcfcfb)              dark (#1a1a19)
CVD adjacent  PASS  worst ΔE 9.1 deutan    PASS  worst ΔE 9.1 deutan
Normal vision PASS  worst ΔE 18.9          PASS  worst ΔE 18.9
Contrast      3.27 / 3.50 / 4.68           5.19 / 4.85 / 3.62
Lightness band  PASS                       PASS
Chroma floor    FAIL #898781 (C 0.009)     FAIL #898781 (C 0.009)
```

**The segment order is a validation result, not a preference.** Dropping the Watch tier
removed amber from the middle of the bar and put green next to red — which measures
**ΔE 4.1 under deuteranopia**, below the hard floor of 6.0. That is the classic red/green
pair, and amber had been separating them. Ordering the bar On track → Completed → Live
issue puts the grey completed segment between them, and every adjacent pair clears the
target: green/grey 10.7, red/grey 9.1 (deutan). Any future reordering of this bar has to
be re-validated.

The one remaining FAIL is **expected and correct**: the chroma floor is a gate on a
*categorical identity* palette, there so an identity hue does not read as grey.
`#898781` is achromatic precisely because grey *means* inactive here.

A standing obligation on amber: at **1.79:1 on the light surface** it may never carry
meaning alone. The glyph-plus-label chip rule above is that mitigation, and it is
mandatory, not discretionary. (On dark it measures 9.49:1.)

Pacing-board check (grey elapsed track beside a status delivery bar): separation runs
ΔE 15.0–30.0 under deutan, with watch-amber-vs-grey the weakest at 15.0 — right at the
floor, mitigated by the 2px surface gap and by direct % labels on both bars.

---

## 8. Typography

Inter (already loaded). No second face, no display or serif anywhere, including the
hero figure.

| Token | Size / line / tracking | Use |
|---|---|---|
| `--fs-hero` | 56 / 1.0 / −0.03em | the one hero figure per view |
| `--fs-metric-lg` | 32 / 1.1 / −0.02em | primary tiles |
| `--fs-metric` | 24 / 1.2 / −0.015em | secondary tiles, campaign variance |
| `--fs-h2` | 18 / 1.3 / −0.01em | section titles |
| `--fs-h3` | 15 / 1.4 | card titles, campaign names |
| `--fs-body` | 14 / 1.55 | body, table cells |
| `--fs-sm` | 13 / 1.5 | secondary cell text, captions |
| `--fs-xs` | 12 / 1.45 | notes |
| `--fs-micro` | 11 / 1.4 / +0.06em, uppercase | eyebrow labels |

Weights: 400 body, 500 emphasis and table numbers, 600 headings and metric values. **700
is not used.** Nothing needs to shout on a page where hierarchy is carried by size.

**Numerals.** Proportional figures on the hero and on all standalone tile values —
`tabular-nums` gives every digit the width of a `0`, which makes a large number look
loose. `font-variant-numeric: tabular-nums` is applied **only** to table columns, axis
ticks and the pacing-bar percentages, where digits must align vertically.

Formulas and placement IDs use `ui-monospace, 'SF Mono', Menlo, monospace`.

---

## 9. Chart system

### Recommendation: remove Chart.js

The redesign needs: one line chart, several ranked horizontal bars, one segmented bar,
and paired pacing bars. Three of those four are CSS/flexbox, not charts. The fourth is
roughly 60 lines of hand-written SVG.

Chart.js costs a 200KB CDN dependency and its defaults actively fight every mark spec
below (bar thickness, rounded data-ends, hairline solid grid, no legend for a single
series, selective direct labels), so most of the work becomes overriding it. Dropping it
*reduces* the stack, consistent with "do not automatically expand the technology stack."

### Mark specs — fixed across every chart

| Mark | Spec |
|---|---|
| Bar / column | ≤ 24px thick, 4px rounded data-end, square at baseline |
| Line | 2px, round join and cap |
| End marker | ≥ 8px diameter, 2px ring in the surface colour |
| Area fill | series hue at ~10% opacity, never a saturated block |
| Gridlines / axes | hairline 1px, **solid never dashed**, one step off surface |
| Between touching marks | 2px gap in the surface colour, never a stroke |

### The six visualizations, each with its question

| # | Visual | Question | Form | Colour |
|---|---|---|---|---|
| 1 | Portfolio health | How much of the book is healthy vs needs attention? | Segmented bar, 595 placements | 3 status colours |
| 2 | Campaign pacing | Which campaigns are behind where they should be today? | Paired horizontal bars per campaign | Grey elapsed + status delivery |
| 3 | Exposure concentration | Where is the largest financial exposure? | Ranked horizontal bars, toggle campaign / market / format | Single series blue |
| 4 | Market contribution | Which markets drive *this* campaign's shortfall? | Ranked contribution bars, % of net | Single series blue |
| 5 | Delivery trajectory | How has delivery accumulated against the expected flight line? | Two cumulative lines, gap shaded | Grey plan + blue actual, red 10% gap |
| 6 | Cost efficiency | Which inventory is efficient, within comparable groups? | Ranked bars (static only) + separate digital tile | Single series blue |

Single-series bars take no legend — the title names what is plotted. Charts 1, 2 and 5
have two or more series and therefore always carry a legend, with direct labels as
supplement, never as replacement.

**Every chart has a table-view twin**, toggled from `⊞ Table` in the chart header. This
is an accessibility requirement and it also serves the analyst persona directly.

### Chart 2 in detail — the pacing bars

The most intuitive visual in the product, and worth specifying precisely:

```
  Nimbus Telecom · Product launch                     ▲ Needs attention
  Flight    ████████████████████████░░░░░░░  76%   9 Jul → 1 Oct
  Delivery  ███████████████████████░░░░░░░░  74%   −3.1% to date
                                   ▲ delivery bar tinted by status
```

Both bars are percentages of the **same** denominator (the full contract / the full
flight) on a shared 0–100% axis, so the visual gap between bar ends *is* the pacing gap.
This is one scale, not a dual axis. Direct % labels sit at both bar ends so the
comparison never depends on colour or on eyeballing length.

### Chart 5 — and a deliberate limitation

The trajectory chart plots cumulative verified impressions against cumulative expected
impressions across the flight. Both series are observed/calculated, so the chart is
honest.

But: `generate_data.make_delivery()` applies **one health multiplier per placement across
the whole flight**, so the gap between the two lines widens approximately linearly by
construction. The chart therefore gets **no trend annotation, no inflection marker, and
no projection**, and its caption says that delivery shortfall in this dataset is constant
rather than developing. Reading a "trend" off it would be reading the generator.

For the same reason: **no sparklines anywhere in the product**, including in the campaign
rows and the inventory table, however good they would look.

---

## 10. Table system

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Placement ▾            Campaign           Flight     Delivered  Var.   Value │ ← sticky
├──────────────────────────────────────────────────────────────────────────────┤
│ Toronto · Bulletin     Meridian Bank      28 d       1.2m     −38.2%  $4,106 │
│ Scarborough #87        Product launch     closed 24 Aug                      │
├──────────────────────────────────────────────────────────────────────────────┤
│ Calgary · Mall panel   Vantage Motors     42 d       0.4m     −31.9%  $3,880 │
│ Macleod Trail #14      Awareness          closed 24 Oct                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

- **Composite primary cell.** City · Format on line 1, area and site ID on line 2 in
  `--text-2` at 13px. The brief is right that these should not be three visually equal
  columns: they are one identity, and splitting them spends three columns of horizontal
  budget on something the eye reads as a single label.
- **Sticky header** on any table over 12 rows; sortable columns with a persistent
  direction caret and `aria-sort`.
- Numbers right-aligned, `tabular-nums`, compact formatting (`1.2m`, `$4,106`).
- Variance cells carry the status colour as a **dot plus value**, not as coloured text.
- Row hover changes background only — never `transform`, which makes dense rows jitter.
- 48px row height (two lines of content), 12px cell padding. No zebra striping; hairline
  separators do that job more quietly.
- Row click opens the placement drawer (§13).

---

## 11. Campaign row / card system

Used on Overview (compact) and on the Campaigns view (full).

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  NIMBUS TELECOM                                      ▲ Needs attention       │
│  Product launch · 6 markets · 67 placements · 9 Jul → 1 Oct 2026             │
│                                                                              │
│  Flight    ████████████████████████░░░░░░░░  76%          $19,765            │
│  Delivery  ███████████████████████░░░░░░░░░  74%          at risk            │
│                                                                              │
│  −3.1% net · 2.5m gross short, 26% masked    6 flagged     [ Open campaign → ]│
└──────────────────────────────────────────────────────────────────────────────┘
```

- Status chip top right sets the row's whole meaning before any number is read.
- **The gross/net line is the card's most important text.** A campaign reading −3.1%
  looks fine; "2.5m gross short, 26% masked" says it is not. On campaign 1 the contrast
  is starker still — −1.1% net against 1.0m gross and 63% masked — and that single line
  is the difference between reporting a campaign and analysing one.
- The two bars are the scannable core — a reader comparing bar ends across a stacked
  list of 8 campaigns gets the entire portfolio pacing story without reading a digit.
- Spend at risk is the only currency figure, set at `--fs-metric`, right-aligned where
  the eye lands after the bars.
- Live campaigns sort first and carry full elevation; closed campaigns render on the
  sunken surface with a grey chip.

**A naming gap, flagged honestly:** the schema has no campaign name — only
`client_name`, `objective` and dates. The wireframes above read "Nimbus Telecom /
Product launch" because that is all the data supports. A `name` column on `campaigns`
(e.g. "Nimbus Telecom — Autumn Product Launch") would make every list in the product
substantially more scannable. That is a generator change and therefore a decision for
you, not something to invent in the frontend.

---

## 12. Campaign drill-down wireframe

**Decision: a full view, not a drawer, for campaigns.** A drawer is right when you need
to keep the list visible while inspecting one item; it is wrong when the detail is itself
a dense multi-section workspace, because it compresses that workspace into ~480px beside
a list you are no longer reading. Campaign analysis has seven sections and two tables.

**The drawer is used one level down, for a single placement** (§13), where its real
advantage applies: you keep the ranked list in view while stepping through issues.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ ← All campaigns                                                                  │
│                                                                                  │
│ NIMBUS TELECOM                                                 ▲ Needs attention │
│ Product launch · 9 Jul → 1 Oct 2026 · 6 markets · 67 placements · 76% elapsed    │
├──────────────────────────────────────────────────────────────────────────────────┤
│  −3.1%             $767,239          $19,765            6                        │
│  Variance to date  Spend billed      At risk            Flagged placements       │
├──────────────────────────────────────────────────────────────────────────────────┤
│  DELIVERY TRAJECTORY                                              ⓘ  ⊞ Table     │
│   ╭──────────────────────────────────────────────────────────────╮              │
│   │                                               ╭─── expected  │              │
│   │                                      ╭────────╯              │              │
│   │                             ╭────────╯▒▒▒▒▒▒▒▒╭─── actual    │              │
│   │                    ╭────────╯▒▒▒▒▒▒▒▒╭────────╯              │              │
│   │           ╭────────╯▒▒▒▒▒▒▒▒╭────────╯                       │              │
│   │  ╭────────╯────────╯────────╯                                │              │
│   ╰──────────────────────────────────────────────────────────────╯              │
│    9 Jul                                                      10 Sep             │
│    Shortfall in this dataset is constant across the flight, not developing. ⓘ   │
├──────────────────────────────────────────────────────────────────────────────────┤
│  WHAT IS DRIVING THE SHORTFALL?                    [ Market ] [ Format ] [ Site ]│
│                                                                                  │
│  📍 Toronto accounts for 73% of this campaign's net shortfall.                   │
│                                                                                  │
│  Toronto      ██████████████████████████████████████  1.37m    73%              │
│  Calgary      ███████████▌                            0.43m    23%              │
│  Ottawa       ██▊                                     0.10m     5%              │
│  Montreal     ▎                                       0.01m     1%              │
│  Edmonton     ▏                                      −0.00m    −0%              │
│  Vancouver    ▏                                      −0.02m    −1%              │
│                                                                                  │
│  Gross shortfall 2.54m across behind placements; 0.65m is masked by              │
│  over-delivery elsewhere, so the campaign reads −3.1% net.                 ⓘ    │
├──────────────────────────────────────────────────────────────────────────────────┤
│  ▲ LIVE ISSUES (6)                                      [cards, as §5]           │
├──────────────────────────────────────────────────────────────────────────────────┤
│  ■ COMPLETED SHORTFALLS (0)                                                      │
│     ✓ No closed placements on this campaign finished below contract.             │
├──────────────────────────────────────────────────────────────────────────────────┤
│  AUDIENCE & PRICING                                                              │
│  Reach 71% · Frequency 6.4 · Showing #6 · CPM $13.78 · 19.4% off rate card       │
│  ~ modelled estimates — see Method                                         ⓘ    │
├──────────────────────────────────────────────────────────────────────────────────┤
│  PLACEMENT CONTRIBUTION                                      [table, as §10]     │
└──────────────────────────────────────────────────────────────────────────────────┘
```

Ordering is strictly most-actionable-first: status → money → trajectory → cause →
what can still be fixed → what must be reconciled → modelled context → full detail.

The gross-vs-net note is a genuine analytical finding the current dashboard hides: on
campaign 8, 0.65m of real operational shortfall is masked by over-delivery elsewhere.
Surfacing it is the difference between a reporting tool and an analytical one.

---

## 13. Interaction patterns

### Progressive disclosure — three tiers, as the brief specifies

| Tier | Trigger | Content |
|---|---|---|
| 1 | Always visible | `−8.4%` |
| 2 | `ⓘ` popover | "Delivery is currently 8.4% below the amount expected at this point in the scheduled flight." |
| 3 | "Full methodology →" in the popover | Formula, assumptions, link into Method |

This is what lets one interface serve a recruiter, a marketer and an analyst without
three different pages.

### Placement drawer

Row or card click slides a 480px right drawer in 240ms. Holds: identity, pacing bars,
full metric list with observed / calculated / modelled markers, downtime hours (currently
generated but never surfaced anywhere), and the site's booking history as a link into
Inventory. Esc closes, focus is trapped and restored, `aria-modal`. Below 768px it
becomes a full-screen sheet.

### Filters

One filter row scoping everything beneath it — never per-chart filters, never a filter
inside a chart card. Custom dropdown buttons rather than native `<select>` (the brief's
"giant native selects scattered across the page" is accurate about the current build).
Active filters appear as removable chips. Search is debounced at 120ms.

### Motion

| Token | Duration | Use |
|---|---|---|
| `--t-fast` | 120ms | hover, focus, tab switch |
| `--t-base` | 180ms | expand/collapse, number tween, filter re-render |
| `--t-slow` | 240ms | drawer |

Easing `cubic-bezier(.2,.6,.3,1)`. Number tweens run only when a value actually changes
and never exceed 240ms. Charts animate on first paint only, never on re-filter — a
re-animating chart delays reading it, which is the opposite of the point.

**All of it inside `@media (prefers-reduced-motion: reduce)` → `animation: none;
transition-duration: 1ms`.** No parallax, no bounce, no glow, no skeleton flash on
re-filter — the previous render holds at reduced opacity so layout never jumps.

### States

| State | Treatment |
|---|---|
| Healthy campaign | `✓ Campaign is tracking to plan — no placements exceed the −5% threshold.` on a faint green ground |
| Empty filter result | `No placements match these filters.` + `[Reset filters]` |
| No live issues | `✓ Nothing live needs attention right now.` + pointer to completed |
| Missing `data.js` | Existing message, restyled as a proper error card |

No empty chart containers render, ever — the container is replaced by its state message.

---

## 14. Responsive behaviour

| Breakpoint | Behaviour |
|---|---|
| ≥ 1280 | Full two-column hero, 12-column grid, all table columns |
| 1024–1279 | Hero stays two-column at 55/45, drill-down charts full width |
| 768–1023 | Hero stacks, campaign cards one per row, tables drop `Flight` and `Markets` into the composite cell |
| 480–767 | Nav → scrollable tab strip, attention cards full-bleed, completed table → card list, drawer → full-screen sheet |
| < 480 | Single column, hero figure 40px, secondary tiles 2-up |

Horizontal scroll is permitted on exactly one element — the placement contribution table
in drill-down — inside its own `overflow-x: auto` container with a sticky first column.
The page body never scrolls horizontally at any width. Minimum 16px side gutter
throughout; 44px minimum touch targets below 768px.

---

## 15. Accessibility

- Contrast measured, not assumed — see §7. Amber's 1.79:1 on light is the one colour
  that may never stand alone; the glyph-plus-label chip is mandatory.
- Every status is conveyed by **glyph + label + colour**, so it survives greyscale,
  CVD and `forced-colors`.
- Visible focus ring on every interactive element: 2px accent, 2px offset. Never removed.
- Full keyboard path: skip link → nav (arrow keys between tabs) → filters → table
  (sortable headers are buttons) → drawer (focus trapped, Esc closes, focus restored).
- `aria-current` on the active tab, `aria-sort` on sorted columns, `aria-expanded` on
  disclosures, `aria-modal` on the drawer, live region announcing filter result counts.
- Every chart has a table twin; no value is reachable only by hover.
- `prefers-reduced-motion` honoured globally.

---

## 16. Observed / calculated / modelled

A standing marker system, because the brief requires the three to be distinguishable and
because it is the project's central credibility claim.

| Class | Marker | Examples |
|---|---|---|
| Observed | `°` | verified impressions, downtime hours, delivery days, negotiated rate, rate card |
| Calculated | `·` | contracted to date, variance, spend to date, CPM, shortfall value, required daily, recovery pace |
| Modelled | `~` | reach, frequency, showing level, preventable exposure, visibility factors |

Markers appear in table headers and tile labels, with the legend permanently in the
Method view and in every `ⓘ` popover. One honest note belongs in Method: contracted
impressions are themselves modelled (`traffic × visibility × days`), so "observed" here
means observed within the synthetic model, not measured in the world.

---

## 17. Decisions — approved

1. **Light-first**, with a persisted dark toggle; light uses refined neutral surfaces
   rather than pure white. Both themes designed, neither a flip of the other.
2. **Graphite chrome + blue accent**, brand strictly separate from status colour.
3. **Campaign names added** — headline reads `Signal Everywhere`, with
   `Nimbus Telecom · Product launch` beneath it as metadata.
4. **Generator changes** — fault onset dates and recovery events (recommended in
   `product-audit.md` §7, because they make time-to-detection measurable rather than
   asserted), plus latent site quality. Nothing in this spec depends on them: every
   surface here works on today's data, and the trend/projection/reliability surfaces
   that would need them are deliberately not specified. Approving them adds a
   time-to-detection figure to the Overview and the campaign drill-down, and rewrites
   every published number in `README.md` and `assumptions.md`.
