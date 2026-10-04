# Power BI on macOS — browser-first feasibility

**Verdict: yes.** A credible, portfolio-quality Power BI companion can be built entirely
from macOS using Power BI Service web authoring. **Power BI Desktop is not required, and
Tableau Public is not needed.**

One capability is conditional on something only the account holder can check — see
*The single open risk* below. It affects **distribution**, not the build.

Researched against current Microsoft Learn documentation (October 2026), not recollection.

---

## Capability matrix

| Capability | Status | Notes |
|---|---|---|
| Upload / import CSV | ✅ **Supported in browser** | *Create → Get data* launches the Power Query "Get data" experience; choose connector, transform, then "Create a semantic model only" |
| Semantic model creation | ✅ **Supported in browser** | Lands directly in the web model editor |
| Table relationships | ✅ **Supported in browser** | Drag column-to-column in the diagram, or *Manage relationships* in the ribbon. Cardinality and cross-filter direction configurable in Properties |
| DAX measures | ✅ **Supported in browser** | *New measure* in the ribbon; full formula bar with IntelliSense, same as Desktop |
| Calculated columns | ✅ **Supported in browser** | *New column* |
| Calculated tables | ✅ **Supported in browser** | *New table* — **this is what makes field parameters possible**, see below |
| Mark as date table | ✅ **Supported in browser** | Right-click table → *Mark as date table* |
| Power Query transforms | ✅ **Supported in browser** | *Transform data* opens the full Power Query editor |
| Report creation | ✅ **Supported in browser** | *New report* from the model, or at model-creation time |
| Cards / KPI visuals | ✅ **Supported in browser** | Standard visual gallery |
| Matrix / table visuals | ✅ **Supported in browser** | Standard |
| Waterfall chart | ✅ **Supported in browser** | Standard visual |
| Heatmap-like visual | ✅ **Supported in browser** | No dedicated heatmap; a **matrix with background conditional formatting** is the native idiom and is what we specify |
| Line charts | ✅ **Supported in browser** | Standard |
| Slicers | ✅ **Supported in browser** | Standard |
| Conditional formatting | ✅ **Supported in browser** | Including background colour scales on matrix cells |
| **Decomposition tree** | ✅ **Supported in browser** | Documented as *"Applies to: Power BI Desktop **and Power BI service**"*. Max 50 levels, 5,000 data points, top-10 per level |
| Decomposition tree **AI splits** | ⚠️ **Limitation** | AI splits are **not supported under Publish to Web**. Manual drilling — which is what our page needs — works fine. We will disable AI splits so behaviour is identical in-service and published |
| Drill-through | ✅ **Supported in browser** | Page order in the right-click menu may differ from Desktop; cosmetic |
| Tooltip pages | ✅ **Supported in browser** | Standard report-page property |
| Bookmarks | ✅ **Supported in browser** | 20 personal bookmarks per report limit (irrelevant here) |
| **Field parameters** | ⚠️ **Supported with a workaround** | There is no *Modeling → New parameter* button in web modeling. But a field parameter **is just a calculated table using `NAMEOF()`**, and calculated tables are fully supported in the browser. The exact DAX is in `powerbi-dax.md` — hand-authored, it behaves identically |
| Model editing after creation | ✅ **Supported in browser** | Auto-saves; version history available |
| Report publishing | ✅ **Supported in browser** | Native — the report is already in the service |
| **Public sharing (Publish to web)** | ⚠️ **Conditional** | Free licences *can* create a publish-to-web embed code, **but a tenant admin must have the feature enabled**. See below |
| Screenshots / export | ✅ **Supported in browser** | Export to PDF/PowerPoint; screenshots trivially |

**Nothing in the matrix is DESKTOP-ONLY / NOT PRACTICAL for this project.**

---

## The single open risk: Publish to web

Free Power BI accounts can create publish-to-web embed codes, **subject to the tenant
administrator's setting**. A Power BI account requires a work or school email — here that
means the `uwaterloo.ca` tenant, whose admin policy is set by the university, not by us.

**This cannot be determined from documentation.** It is visible in one place: in the
report, *File → Embed report → Publish to web (public)*. If the option is greyed out or
absent, the tenant has it disabled.

### If Publish to web is unavailable

The build is unaffected — only the public link is. In order of preference:

1. **Screenshots plus a short interaction GIF** committed to the repo. This was always the
   baseline in `powerbi-plan.md`, and it is what most recruiters actually look at. The
   decomposition tree responding in a GIF demonstrates the capability as convincingly as a
   live link.
2. **A personal Microsoft 365 Developer tenant** (free, 90-day renewable) where the account
   holder *is* the admin and can enable publish-to-web. More setup, fully in-browser.
3. **Tableau Public** — only if a genuinely public live link is judged essential. It is a
   worse fit for the BI-skills story (no DAX, no semantic model in the Power BI sense) and
   should not be chosen merely because publish-to-web is blocked.

**Do not switch tools pre-emptively.** The build is identical either way; the decision
point is distribution, and it arrives after the report exists.

---

## Two consequences for the build

**1. Disable AI splits on the decomposition tree.** Under *Analysis* formatting, turn AI
splits off. They do not survive Publish to web, and a visual that behaves differently in
public than in-service is worse than one that behaves consistently. Manual drilling is the
capability the page is demonstrating anyway: *exposure → campaign → market → format →
placement*.

**2. Field parameters are authored as DAX, not through a button.** The build guide gives
the exact calculated-table definition. This is arguably a better demonstration than
clicking the Desktop wizard, because the resulting table is written out and explainable.

---

## What this does not change

The division of labour from `powerbi-plan.md` stands: sequential/event logic
(fault onset, detection crossing, recovery runs) stays precomputed in Python, and only
additive/ratio measures are reproduced in DAX. That decision was about *analytical
judgement*, not about tooling, and browser authoring does not affect it.

---

## Sources

- [Edit semantic models in the Power BI service](https://learn.microsoft.com/en-us/power-bi/transform-model/service-edit-data-models)
- [Create and view decomposition tree visuals in Power BI](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-decomposition-tree)
- [Power BI features available to free users](https://learn.microsoft.com/en-us/power-bi/consumer/end-user-features)
- [Use field parameters in Power BI reports](https://learn.microsoft.com/en-us/power-bi/create-reports/power-bi-field-parameters)
- [Embed a report in a secure portal or website](https://learn.microsoft.com/en-us/power-bi/collaborate-share/service-embed-secure)
