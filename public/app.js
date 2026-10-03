/*
 * OOH Campaign Performance Analyzer — interface.
 *
 * Presentation only. Every metric rendered here was computed in Python
 * (src/metrics.py) and written out by src/export_json.py. Nothing is
 * recalculated in the browser, so there is one source of truth for each number
 * and the figures on screen are the ones the unit tests cover.
 *
 * Data arrives as window.OOH_DATA from data.js rather than fetch('data.json'),
 * because browsers block fetch() against file:// URLs — this way the dashboard
 * opens straight from disk as well as from a web server.
 */
(function () {
  "use strict";

  var D = window.OOH_DATA;
  if (!D) {
    document.getElementById("main").innerHTML =
      '<p class="empty">data.js missing — run <code>python src/export_json.py</code></p>';
    return;
  }
  var S = D.summary;

  /* ---------------- formatting ---------------- */
  function imp(n) {                       // impressions
    if (n === null || n === undefined || isNaN(n)) return "—";
    var a = Math.abs(n);
    if (a >= 1e9) return (n / 1e9).toFixed(2) + "bn";
    if (a >= 1e6) return (n / 1e6).toFixed(1) + "m";
    if (a >= 1e3) return Math.round(n / 1e3) + "k";
    return Math.round(n).toLocaleString();
  }
  function cash(n) {                      // compact money
    if (n === null || n === undefined || isNaN(n)) return "—";
    var a = Math.abs(n);
    if (a >= 1e6) return "$" + (n / 1e6).toFixed(2) + "m";
    if (a >= 1e4) return "$" + Math.round(n / 1e3) + "K";
    return "$" + Math.round(n).toLocaleString();
  }
  function exact(n) { return "$" + Math.round(n).toLocaleString(); }
  function pct(n, d) {
    if (n === null || n === undefined || isNaN(n)) return "—";
    return (n > 0 ? "+" : "") + n.toFixed(d === undefined ? 1 : d) + "%";
  }
  function tidy(s) { return String(s).replace(/_/g, " "); }
  function cap(s) { s = tidy(s); return s.charAt(0).toUpperCase() + s.slice(1); }
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function longdate(iso) {
    var p = String(iso).split("-");
    var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return Number(p[2]) + " " + MON[Number(p[1]) - 1] + " " + p[0];
  }
  function dayDate(startIso, offset) {
    var d = new Date(startIso + "T00:00:00");
    d.setDate(d.getDate() + offset);
    return longdate(d.toISOString().slice(0, 10));
  }
  // Status is always a glyph plus a word, never colour alone.
  function chip(status, material) {
    if (status === "live_issue")
      return material === false
        ? '<span class="chip minor"><i class="dot"></i>Minor live issue</span>'
        : '<span class="chip live"><i class="dot"></i>Needs attention</span>';
    if (status === "completed_shortfall")
      return '<span class="chip done"><i class="dot"></i>Reconcile</span>';
    return '<span class="chip ok"><i class="dot"></i>On track</span>';
  }
  function placeName(p) { return p.city + " · " + cap(p.format); }
  function days(n) { return n + (n === 1 ? " day" : " days"); }

  /* ---------------- app shell ---------------- */
  var VIEWS = [["overview", "Overview"], ["attention", "Attention"],
               ["campaigns", "Campaigns"], ["markets", "Markets"],
               ["inventory", "Inventory"], ["efficiency", "Efficiency"],
               ["method", "Method"]];

  function buildNav() {
    document.getElementById("nav").innerHTML = VIEWS.map(function (v) {
      var badge = v[0] === "attention"
        ? ' <span class="badge">' + S.live_issues + "</span>" : "";
      return '<button class="navtab" type="button" data-view="' + v[0] + '">' +
             v[1] + badge + "</button>";
    }).join("");
    document.getElementById("nav").addEventListener("click", function (e) {
      var b = e.target.closest("[data-view]");
      if (b) show(b.dataset.view);
    });
  }

  function show(name, skipHash) {
    if (!VIEWS.some(function (v) { return v[0] === name; })) name = "overview";
    VIEWS.forEach(function (v) {
      document.getElementById("v-" + v[0]).classList.toggle("on", v[0] === name);
    });
    [].forEach.call(document.querySelectorAll(".navtab"), function (b) {
      if (b.dataset.view === name) b.setAttribute("aria-current", "page");
      else b.removeAttribute("aria-current");
    });
    if (!skipHash) location.hash = name;
    window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
  }

  /* ---------------- theme ---------------- */
  function initTheme() {
    var saved = null;
    try { saved = localStorage.getItem("ooh-theme"); } catch (e) {}
    if (saved) document.documentElement.setAttribute("data-theme", saved);
    document.getElementById("themebtn").addEventListener("click", function () {
      var cur = document.documentElement.getAttribute("data-theme");
      if (!cur) {
        cur = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      }
      var next = cur === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("ooh-theme", next); } catch (e) {}
    });
  }

  /* ---------------- overview ---------------- */
  function renderOverview() {
    document.getElementById("asofchip").textContent = "as of " + longdate(S.as_of);
    document.getElementById("heroFig").textContent = S.delivery_to_plan_pct.toFixed(1) + "%";
    document.getElementById("heroSub").textContent =
      imp(S.delivered) + " verified of " + imp(S.contracted) +
      " expected by " + longdate(S.as_of);

    // Segment order on track → completed → live is a colour-vision requirement:
    // green beside red fails CVD separation, and grey is what divides them.
    var segs = [["s-ok", S.on_track], ["s-done", S.completed_shortfalls],
                ["s-live", S.live_issues]];
    document.getElementById("healthBar").innerHTML = segs.map(function (s) {
      return '<div class="' + s[0] + '" style="flex:' + s[1] + '"></div>';
    }).join("");
    document.getElementById("healthLeg").innerHTML =
      '<span><i class="k-ok"></i>' + S.on_track + " on track</span>" +
      '<span><i class="k-done"></i>' + S.completed_shortfalls + " completed shortfalls</span>" +
      '<span><i class="k-live"></i>' + S.live_issues + " live issues</span>";

    // The tension the product exists to surface, stated directly under the
    // reassuring headline figure.
    document.getElementById("hiddenNote").innerHTML =
      "…but <b>" + imp(S.gross_shortfall) + " impressions</b> are short across <b>" +
      S.placements_behind + " placements</b>. <b>" + Math.round(S.masking_pct) +
      "%</b> of that is cancelled out on paper by other sites running ahead, which is why " +
      "the headline reads " + pct(S.variance_pct) + " rather than " +
      pct(S.gross_shortfall_pct) + ".";

    document.getElementById("states").innerHTML = [
      { n: S.live_issues, t: "Live issues", go: "attention",
        s: exact(S.billed_shortfall_live) + " already lost · " +
           exact(S.preventable_exposure) + " still preventable" },
      { n: S.completed_shortfalls, t: "Completed shortfalls", go: "attention",
        s: exact(S.billed_shortfall_completed) + " to reconcile" },
      { n: S.on_track, t: "On track", go: "campaigns",
        s: "within 5% of plan for the days that have run" }
    ].map(function (r) {
      return '<button class="state" type="button" data-go="' + r.go + '">' +
        '<span class="state-n num">' + r.n + "</span><span>" +
        '<span class="state-t">' + r.t + "</span>" +
        '<span class="state-s">' + r.s + "</span></span>" +
        '<span class="state-go" aria-hidden="true">›</span></button>';
    }).join("");

    document.getElementById("overviewCallout").innerHTML =
      '<div class="callout"><span class="glyph">!</span>' +
      "<p><b>" + S.material_issues + " live issues</b> each hold more than " +
      exact(S.material_threshold) + " of preventable exposure — " +
      exact(S.material_exposure) + " of the " + exact(S.preventable_exposure) +
      " total.</p>" +
      '<button class="btn" type="button" data-go="attention">Review attention centre →</button></div>';

    var det = S.detection;
    document.getElementById("whyTrad").textContent =
      "On this dataset a fault sat undetected for a median of " +
      det.median_reconciliation_delay_days + " days between starting and the flight closing.";
    document.getElementById("whyTool").textContent =
      "Measured against contracted-to-date, the same faults crossed the alert line a median of " +
      det.median_detection_delay_days + " days after they began — with a median of " +
      det.median_days_remaining_at_detection + " days of flight still left to act in.";

    renderPacing();
    renderExposure();
  }

  function pacingBars(progress, delivered, statusClass) {
    return '<div class="pace">' +
      '<span class="k">Flight</span><span class="track"><i class="fill-plan" style="width:' +
        Math.min(100, progress) + '%"></i></span><span class="v">' + progress.toFixed(0) + "%</span>" +
      '<span class="k">Delivery</span><span class="track"><i class="fill-' + statusClass +
        '" style="width:' + Math.min(100, delivered) + '%"></i></span><span class="v">' +
        delivered.toFixed(0) + "%</span></div>";
  }

  function campaignStatus(c) {
    if (c.live_issues > 0) return "live";
    if (c.completed_shortfalls > 0) return "done";
    return "ok";
  }

  function campaignCard(c, clickable) {
    var st = campaignStatus(c);
    var chipHtml = st === "live"
      ? '<span class="chip live"><i class="dot"></i>' + c.live_issues + " live issues</span>"
      : st === "done"
        ? '<span class="chip done"><i class="dot"></i>' + c.completed_shortfalls + " to reconcile</span>"
        : '<span class="chip ok"><i class="dot"></i>On track</span>';
    return '<button class="ccard' + (c.in_flight ? "" : " closed") +
      '" type="button" data-campaign="' + c.campaign_id + '"' +
      (clickable ? "" : ' tabindex="-1"') + ">" +
      "<span><span class='cname'>" + esc(c.name) + "</span>" +
      "<span class='cmeta'>" + esc(c.client) + " · " + cap(c.objective) + " · " +
        longdate(c.start) + " → " + longdate(c.end) + "</span>" +
      "<span class='cmask'>" + pct(c.variance_pct) + " net · <b>" +
        imp(c.gross_shortfall) + "</b> gross short, <b>" + Math.round(c.masking_pct) +
        "%</b> masked by over-delivery</span></span>" +
      "<span>" + pacingBars(c.progress_pct, c.delivered_pct, st) +
      "<span style='display:block;margin-top:10px'>" + chipHtml + "</span></span>" +
      "<span class='cmoney'><span class='v'>" + cash(c.billed_shortfall) +
      "</span><span class='l'>billed shortfall</span></span></button>";
  }

  function renderPacing() {
    document.getElementById("pacingBoard").innerHTML =
      D.campaigns.map(function (c) { return campaignCard(c, true); }).join("");
  }

  function rankedBars(rows, valueKey, labelKey, fmt) {
    var max = Math.max.apply(null, rows.map(function (r) { return Math.abs(r[valueKey]); }));
    return rows.map(function (r) {
      var w = max > 0 ? Math.max(0, r[valueKey]) / max * 100 : 0;
      return '<div class="rrow"><span class="rk">' + cap(r[labelKey]) + "</span>" +
        '<span class="rb"><i style="width:' + w + '%"></i></span>' +
        '<span class="rv">' + fmt(r[valueKey]) + "</span>" +
        '<span class="rp">' + (r.share_pct !== undefined ? r.share_pct.toFixed(0) + "%" : "") +
        "</span></div>";
    }).join("");
  }

  function renderExposure() {
    var top = D.by_market[0];
    document.getElementById("exposureNote").innerHTML =
      "<b>" + top.key + "</b> carries " + top.share_pct.toFixed(0) +
      "% of the book's net shortfall — " + imp(top.net_shortfall) +
      " impressions, " + exact(top.billed_shortfall) + " of billed media value.";
    document.getElementById("exposureBars").innerHTML =
      rankedBars(D.by_market, "net_shortfall", "key", imp);
  }

  /* ---------------- attention ---------------- */
  var filters = { campaign: "", city: "", format: "", q: "" };

  function matches(p) {
    if (filters.campaign && String(p.campaign_id) !== filters.campaign) return false;
    if (filters.city && p.city !== filters.city) return false;
    if (filters.format && p.format !== filters.format) return false;
    if (filters.q) {
      var hay = (p.city + " " + p.area + " " + p.format + " " + p.client + " " +
                 p.campaign_name + " " + p.site_id).toLowerCase();
      if (hay.indexOf(filters.q.toLowerCase()) === -1) return false;
    }
    return true;
  }

  function issueCard(p) {
    // The sentence is the point of the card: what recovery would take, and
    // whether the placement can actually do it.
    var pace = p.recovery_pace;
    var note;
    if (pace === null) {
      note = "No flight remaining.";
    } else if (pace <= 1.05) {
      note = "Finishing whole needs <b>" + Math.round(pace * 100) +
             "%</b> of planned daily delivery for the remaining " + days(p.remaining_days) +
             " — within what a restored face can sustain.";
    } else {
      note = "Finishing whole would need <b>" + Math.round(pace * 100) +
             "%</b> of planned daily delivery for the remaining " + days(p.remaining_days) +
             ". A healthy face delivers 96–105% of plan, so this gap closes with " +
             "added weight or a make-good, not by catching up.";
    }
    var detected = p.onset_day !== null && p.alert_day !== null
      ? '<div class="inote" style="margin-top:12px"><span class="glyph">◷</span><span>' +
        "Delivery fell away on <b>" + dayDate(p.start, p.onset_day) + "</b> (flight day " +
        (p.onset_day + 1) + ") and crossed the alert line <b>" +
        days(p.detection_delay_days) + "</b> later, with " +
        days(p.days_remaining_at_detection) + " of flight still to run. " +
        "End-of-campaign reconciliation would have found it " +
        days(p.reconciliation_delay_days) + " after it began.</span></div>"
      : "";
    var running = p.fault_index !== null && !p.recovered
      ? Math.round(p.fault_index * 100) + "% of plan"
      : Math.round(p.delivery_index * 100) + "% of plan";

    return '<article class="issue' + (p.material ? "" : " minor") + '">' +
      '<div class="ihead"><div>' +
        '<div class="iwhere">' + placeName(p) + " · " + esc(p.area) + "</div>" +
        '<div class="iwho">' + esc(p.campaign_name) + " · " + esc(p.client) +
          " · site #" + p.site_id + "</div>" +
        '<div style="margin-top:8px">' + chip(p.status, p.material) +
          (p.recovered ? ' <span class="chip ok"><i class="dot"></i>Recovered</span>' : "") +
        "</div>" +
      "</div><div class='iexp'><div class='v num'>" + exact(p.preventable_exposure) +
        "</div><div class='l'>still preventable</div>" +
        "<div class='l'>" + exact(p.billed_shortfall) + " already lost</div></div></div>" +
      '<div class="igrid">' +
        '<div><div class="k">Behind plan</div><div class="v neg">' + pct(p.variance_pct) + "</div></div>" +
        '<div><div class="k">Running at</div><div class="v">' + running + "</div></div>" +
        '<div><div class="k">Days left</div><div class="v">' + p.remaining_days + "</div></div>" +
        '<div><div class="k">Recovery pace</div><div class="v">' +
          (pace === null ? "—" : Math.round(pace * 100) + "%") + "</div></div>" +
      "</div>" +
      '<div class="inote"><span class="glyph">⚑</span><span>' + note + "</span></div>" +
      detected +
      '<div class="iact"><button class="btn ghost" type="button" data-placement="' +
        p.placement_id + '">View placement</button></div></article>';
  }

  var DONE_COLS = [
    { k: "placement", t: "Placement" }, { k: "campaign", t: "Campaign" },
    { k: "flight_days", t: "Flight", r: true },
    { k: "verified_impressions", t: "Delivered", r: true },
    { k: "variance_pct", t: "Variance", r: true, sort: true },
    { k: "billed_shortfall", t: "Billed shortfall", r: true, sort: true }
  ];
  var doneSort = { key: "billed_shortfall", dir: -1 };

  function renderAttention() {
    document.getElementById("attFig").textContent = exact(S.preventable_exposure);
    document.getElementById("attSub").textContent =
      "across " + S.live_issues + " live placements. The " + S.completed_shortfalls +
      " completed shortfalls below are no longer recoverable by delivery — they are " +
      exact(S.billed_shortfall_completed) + " of reconciliation.";

    var live = D.attention.live.filter(matches);
    var done = D.attention.completed.filter(matches);
    document.getElementById("fCount").textContent =
      live.length + " live · " + done.length + " completed shown";

    document.getElementById("liveIssues").innerHTML = live.length
      ? live.map(issueCard).join("")
      : '<div class="goodstate"><span aria-hidden="true">✓</span><span><b>Nothing live needs ' +
        "attention.</b> No placement still in the air is more than 5% behind plan.</span></div>";

    var head = DONE_COLS.map(function (c) {
      var label = c.sort
        ? '<button type="button" data-sort="' + c.k + '">' + c.t +
          (doneSort.key === c.k ? (doneSort.dir < 0 ? " ↓" : " ↑") : "") + "</button>"
        : c.t;
      return "<th" + (c.r ? ' class="r"' : "") +
             (doneSort.key === c.k ? ' aria-sort="' + (doneSort.dir < 0 ? "descending" : "ascending") + '"' : "") +
             ">" + label + "</th>";
    }).join("");
    document.querySelector("#tDone thead").innerHTML = "<tr>" + head + "</tr>";

    done.sort(function (a, b) {
      return (a[doneSort.key] - b[doneSort.key]) * doneSort.dir;
    });
    document.querySelector("#tDone tbody").innerHTML = done.length
      ? done.map(function (p) {
          return '<tr data-placement="' + p.placement_id + '" tabindex="0">' +
            "<td><div class='cellmain'>" + placeName(p) + "</div>" +
              "<div class='cellsub'>" + esc(p.area) + " · site #" + p.site_id + "</div></td>" +
            "<td><div class='cellmain'>" + esc(p.campaign_name) + "</div>" +
              "<div class='cellsub'>" + esc(p.client) + "</div></td>" +
            "<td class='r'>" + p.flight_days + " d<div class='cellsub'>closed " +
              longdate(p.end) + "</div></td>" +
            "<td class='r'>" + imp(p.verified_impressions) + "<div class='cellsub'>of " +
              imp(p.contracted_to_date) + "</div></td>" +
            "<td class='r neg'>" + pct(p.variance_pct) + "</td>" +
            "<td class='r'>" + exact(p.billed_shortfall) + "</td></tr>";
        }).join("")
      : '<tr><td colspan="6" class="empty">No completed shortfalls match these filters.</td></tr>';
  }

  function renderChips() {
    var out = [];
    if (filters.campaign) {
      var c = D.campaigns.filter(function (x) {
        return String(x.campaign_id) === filters.campaign; })[0];
      out.push(["campaign", c ? c.name : filters.campaign]);
    }
    if (filters.city) out.push(["city", filters.city]);
    if (filters.format) out.push(["format", cap(filters.format)]);
    if (filters.q) out.push(["q", '"' + filters.q + '"']);
    document.getElementById("fChips").innerHTML = out.length
      ? "Showing: " + out.map(function (f) {
          return '<span class="fchip">' + esc(f[1]) +
                 '<button type="button" data-clear="' + f[0] + '" aria-label="Remove filter">✕</button></span>';
        }).join("")
      : "";
  }

  function initFilters() {
    var cs = document.getElementById("fCampaign");
    D.campaigns.forEach(function (c) {
      cs.insertAdjacentHTML("beforeend",
        '<option value="' + c.campaign_id + '">' + esc(c.name) + "</option>");
    });
    fill("fCity", D.by_market.map(function (r) { return r.key; }));
    fill("fFormat", D.by_format.map(function (r) { return r.key; }));
    function fill(id, vals) {
      var el = document.getElementById(id);
      vals.slice().sort().forEach(function (v) {
        el.insertAdjacentHTML("beforeend", '<option value="' + v + '">' + cap(v) + "</option>");
      });
    }
    var map = { fCampaign: "campaign", fCity: "city", fFormat: "format" };
    Object.keys(map).forEach(function (id) {
      document.getElementById(id).addEventListener("change", function () {
        filters[map[id]] = this.value; refilter();
      });
    });
    var t;
    document.getElementById("fSearch").addEventListener("input", function () {
      var v = this.value;
      clearTimeout(t);
      t = setTimeout(function () { filters.q = v; refilter(); }, 120);
    });
    document.getElementById("fReset").addEventListener("click", reset);
    document.getElementById("fChips").addEventListener("click", function (e) {
      var b = e.target.closest("[data-clear]");
      if (!b) return;
      var k = b.dataset.clear;
      filters[k] = "";
      if (k === "campaign") document.getElementById("fCampaign").value = "";
      if (k === "city") document.getElementById("fCity").value = "";
      if (k === "format") document.getElementById("fFormat").value = "";
      if (k === "q") document.getElementById("fSearch").value = "";
      refilter();
    });
    document.querySelector("#tDone thead").addEventListener("click", function (e) {
      var b = e.target.closest("[data-sort]");
      if (!b) return;
      var k = b.dataset.sort;
      doneSort.dir = doneSort.key === k ? -doneSort.dir : -1;
      doneSort.key = k;
      renderAttention();
    });
  }
  function reset() {
    filters = { campaign: "", city: "", format: "", q: "" };
    ["fCampaign", "fCity", "fFormat", "fSearch"].forEach(function (id) {
      document.getElementById(id).value = "";
    });
    refilter();
  }
  function refilter() { renderChips(); renderAttention(); }

  /* ---------------- trajectory chart (hand-built SVG) ---------------- */
  function trajectory(c) {
    var A = c.trajectory.actual, E = c.trajectory.expected;
    if (!A.length) return "";
    var W = 760, H = 240, L = 58, R = 18, T = 14, B = 30;
    var max = Math.max(E[E.length - 1], A[A.length - 1]) * 1.04 || 1;
    var n = A.length;
    function x(i) { return L + (n === 1 ? 0 : i / (n - 1) * (W - L - R)); }
    function y(v) { return H - B - v / max * (H - T - B); }
    function path(arr) {
      return arr.map(function (v, i) { return (i ? "L" : "M") + x(i).toFixed(1) + " " + y(v).toFixed(1); }).join(" ");
    }
    // The gap between expected and actual, filled: the shortfall made visible.
    var gap = path(E) + " " + A.map(function (v, i) {
      var j = n - 1 - i;
      return "L" + x(j).toFixed(1) + " " + y(A[j]).toFixed(1);
    }).join(" ") + " Z";

    var grid = "", ticks = 4;
    for (var g = 0; g <= ticks; g++) {
      var val = max * g / ticks, yy = y(val);
      grid += '<line class="grid" x1="' + L + '" y1="' + yy.toFixed(1) + '" x2="' + (W - R) +
              '" y2="' + yy.toFixed(1) + '"/>' +
              '<text x="' + (L - 8) + '" y="' + (yy + 3).toFixed(1) + '" text-anchor="end">' +
              imp(val) + "</text>";
    }
    // Fault onsets, as marks on the day axis. Real temporal signal: faults have
    // onset dates in the data, so this is observed rather than decorative.
    var onsets = (c.fault_onsets || []).filter(function (o) { return o[0] < n; })
      .map(function (o) {
        return '<rect class="onset" x="' + (x(o[0]) - 1.5).toFixed(1) + '" y="' + (H - B) +
               '" width="3" height="6" rx="1"><title>' + o[1] +
               " placement fault" + (o[1] > 1 ? "s" : "") + " began on flight day " +
               (o[0] + 1) + "</title></rect>";
      }).join("");

    // The gap is usually a few percent, so the two lines nearly coincide. One
    // selective direct label at the end states the shortfall rather than
    // leaving the reader to judge a two-pixel separation -- and the label wears
    // a text colour, with the red connector beside it carrying the identity.
    var gapVal = E[n - 1] - A[n - 1], annot = "";
    if (gapVal > 0) {
      var lx = x(n - 1), yE = y(E[n - 1]), yA = y(A[n - 1]);
      annot = '<line x1="' + lx.toFixed(1) + '" y1="' + yE.toFixed(1) + '" x2="' + lx.toFixed(1) +
        '" y2="' + yA.toFixed(1) + '" stroke="var(--alert)" stroke-width="2" stroke-linecap="round"/>' +
        '<text class="lbl" x="' + (lx - 8).toFixed(1) + '" y="' + (yE - 10).toFixed(1) +
        '" text-anchor="end">' + imp(gapVal) + " short</text>";
    }

    return '<svg class="chart" viewBox="0 0 ' + W + " " + H +
      '" role="img" aria-label="Cumulative delivery against the contracted line by flight day">' +
      grid +
      '<path class="gap" d="' + gap + '"/>' +
      '<path class="ln-plan" d="' + path(E) + '"/>' +
      '<path class="ln-act" d="' + path(A) + '"/>' +
      '<line class="axis" x1="' + L + '" y1="' + (H - B) + '" x2="' + (W - R) + '" y2="' + (H - B) + '"/>' +
      annot + onsets +
      '<text x="' + L + '" y="' + (H - B + 18) + '">Flight day 1</text>' +
      '<text x="' + (W - R) + '" y="' + (H - B + 18) + '" text-anchor="end">Day ' + n + "</text>" +
      "</svg>";
  }

  /* ---------------- campaigns ---------------- */
  function renderCampaigns() {
    document.getElementById("campaignCards").innerHTML =
      D.campaigns.map(function (c) { return campaignCard(c, true); }).join("");
  }

  var ddBreak = "market";
  var currentCampaign = null;

  function openCampaign(id) {
    var c = D.campaigns.filter(function (x) { return x.campaign_id === id; })[0];
    if (!c) return;
    currentCampaign = id;
    document.getElementById("campaignList").hidden = true;
    var el = document.getElementById("campaignDetail");
    el.hidden = false;
    el.innerHTML = campaignDetail(c);
    show("campaigns");
  }

  function closeCampaign() {
    currentCampaign = null;
    document.getElementById("campaignDetail").hidden = true;
    document.getElementById("campaignList").hidden = false;
  }

  function campaignDetail(c) {
    var rows = ddBreak === "market" ? c.by_market : c.by_format;
    var top = rows.filter(function (r) { return r.net_shortfall > 0; })[0];
    var live = D.attention.live.filter(function (p) { return p.campaign_id === c.campaign_id; });
    var done = D.attention.completed.filter(function (p) { return p.campaign_id === c.campaign_id; });
    var tops = D.top_placements[String(c.campaign_id)] || [];

    return '<button class="back" type="button" id="ddBack">← All campaigns</button>' +
      '<div class="ddhead"><div><h1>' + esc(c.name) + "</h1>" +
        '<div class="ddmeta">' + esc(c.client) + " · " + cap(c.objective) + " · " +
          longdate(c.start) + " → " + longdate(c.end) + " · " + c.placements +
          " placements across " + c.markets + " markets</div></div>" +
        "<div>" + (c.in_flight
          ? '<span class="chip live"><i class="dot"></i>In flight · ' +
            c.progress_pct.toFixed(0) + "% elapsed</span>"
          : '<span class="chip done"><i class="dot"></i>Flight closed</span>') + "</div></div>" +

      '<div class="panel"><div class="tiles">' +
        tile("Variance to date", pct(c.variance_pct), imp(c.delivered) + " of " + imp(c.contracted_to_date)) +
        tile("Gross shortfall", imp(c.gross_shortfall), Math.round(c.masking_pct) + "% masked by over-delivery") +
        tile("Billed shortfall", exact(c.billed_shortfall), c.live_issues + " live · " + c.completed_shortfalls + " completed") +
        tile("Spend to date", cash(c.spend), c.discount_pct.toFixed(1) + "% off rate card") +
      "</div></div>" +

      '<div class="panel"><div class="phead"><h2>Delivery trajectory</h2>' +
        '<span class="phint">cumulative, by flight day</span></div>' +
        '<div class="pbody"><div class="legend">' +
          '<span><i style="background:#898781"></i>Contracted to date</span>' +
          '<span><i style="background:var(--accent)"></i>Verified delivery</span>' +
          '<span><i style="background:var(--alert);opacity:.4;height:8px"></i>Shortfall</span>' +
          (c.fault_onsets.length ? '<span><i style="background:var(--alert);height:6px;width:3px"></i>Fault onset</span>' : "") +
        "</div>" + trajectory(c) +
        '<p class="pnote" style="padding:0;margin-top:12px">Flight day rather than calendar date, so ' +
        "the chart is about this campaign's progress rather than which month it ran in. " +
        (c.fault_onsets.length
          ? "Marks on the axis are the days individual placements began falling away."
          : "No placement on this campaign sustained a fault.") + "</p></div></div>" +

      '<div class="panel"><div class="phead"><h2>What is driving the shortfall?</h2>' +
        '<span class="phint"><span class="seg">' +
          '<button type="button" data-break="market" aria-pressed="' + (ddBreak === "market") + '">Market</button>' +
          '<button type="button" data-break="format" aria-pressed="' + (ddBreak === "format") + '">Format</button>' +
        "</span></span></div>" +
        (top ? '<p class="pnote"><b>' + cap(top.key) + "</b> accounts for " +
          top.share_pct.toFixed(0) + "% of this campaign's net shortfall.</p>" : "") +
        '<div class="pbody"><div class="ranked">' +
          rankedBars(rows, "net_shortfall", "key", imp) + "</div>" +
        '<p class="pnote" style="padding:0;margin-top:16px">Gross shortfall ' + imp(c.gross_shortfall) +
          " across placements that are behind; " + imp(c.over_delivery_offset) +
          " is masked by over-delivery elsewhere, so the campaign reads " + pct(c.variance_pct) +
          " net.</p></div></div>" +

      '<div class="panel flat"><div class="phead" style="padding-left:0"><h2>Live issues</h2>' +
        '<span class="phint">' + live.length + "</span></div>" +
        '<div class="pbody" style="padding-left:0;padding-right:0">' +
        (live.length ? '<div class="issues">' + live.map(issueCard).join("") + "</div>"
          : '<div class="goodstate"><span aria-hidden="true">✓</span><span><b>No live issues.</b> ' +
            (c.in_flight ? "No placement still in the air is more than 5% behind plan."
                         : "This flight has closed.") + "</span></div>") + "</div></div>" +

      '<div class="panel"><div class="phead"><h2>Completed shortfalls</h2>' +
        '<span class="phint">' + done.length + "</span></div>" +
        (done.length
          ? '<div class="tablewrap"><table><thead><tr><th>Placement</th><th class="r">Delivered</th>' +
            '<th class="r">Variance</th><th class="r">Billed shortfall</th></tr></thead><tbody>' +
            done.map(function (p) {
              return '<tr data-placement="' + p.placement_id + '" tabindex="0"><td>' +
                "<div class='cellmain'>" + placeName(p) + "</div><div class='cellsub'>" +
                esc(p.area) + " · site #" + p.site_id + "</div></td>" +
                "<td class='r'>" + imp(p.verified_impressions) + "</td>" +
                "<td class='r neg'>" + pct(p.variance_pct) + "</td>" +
                "<td class='r'>" + exact(p.billed_shortfall) + "</td></tr>";
            }).join("") + "</tbody></table></div>"
          : '<div class="pbody"><div class="goodstate"><span aria-hidden="true">✓</span>' +
            "<span><b>No completed shortfalls.</b> No closed placement on this campaign " +
            "finished below contract.</span></div></div>") + "</div>" +

      '<div class="panel"><div class="phead"><h2>Biggest contributing placements</h2>' +
        '<span class="phint">top 10 by impressions short</span></div>' +
        '<div class="tablewrap"><table><thead><tr><th>Placement</th><th>Status</th>' +
        '<th class="r">Short</th><th class="r">Variance</th><th class="r">Billed</th></tr></thead><tbody>' +
        tops.map(function (p) {
          return '<tr data-placement="' + p.placement_id + '" tabindex="0"><td>' +
            "<div class='cellmain'>" + placeName(p) + "</div><div class='cellsub'>" +
            esc(p.area) + " · site #" + p.site_id + "</div></td>" +
            "<td>" + chip(p.status) + "</td>" +
            "<td class='r'>" + imp(p.shortfall) + "</td>" +
            "<td class='r " + (p.variance_pct < 0 ? "neg" : "pos") + "'>" + pct(p.variance_pct) + "</td>" +
            "<td class='r'>" + exact(p.billed_shortfall) + "</td></tr>";
        }).join("") + "</tbody></table></div></div>" +

      '<div class="panel"><div class="phead"><h2>Audience and pricing</h2>' +
        '<span class="phint">~ modelled estimates</span></div><div class="tiles">' +
        tile("Reach", c.reach_pct.toFixed(0) + "%", "~ of combined market population") +
        tile("Frequency", c.frequency.toFixed(1) + "×", "~ average exposures per person") +
        tile("Showing", "#" + c.daily_grp.toFixed(0), "~ daily GRP across its markets") +
        tile("CPM", "$" + (c.cpm || 0).toFixed(2), "· on verified delivery") +
      "</div></div>";
  }

  function tile(lab, val, sub) {
    return '<div class="tile"><div class="lab">' + lab + '</div><div class="val num">' +
           val + '</div><div class="sub">' + sub + "</div></div>";
  }

  /* ---------------- markets, inventory, efficiency, method ---------------- */
  function contribTable(sel, rows) {
    document.querySelector(sel + " thead").innerHTML =
      '<tr><th>Market</th><th class="r">Placements</th><th class="r">Flagged</th>' +
      '<th class="r">Gross short</th><th class="r">Net short</th>' +
      '<th class="r">Masked</th><th class="r">Billed shortfall</th><th class="r">Share</th></tr>';
    document.querySelector(sel + " tbody").innerHTML = rows.map(function (r) {
      return "<tr><td class='cellmain'>" + cap(r.key) + "</td>" +
        "<td class='r'>" + r.placements + "</td>" +
        "<td class='r'>" + r.flagged + "</td>" +
        "<td class='r'>" + imp(r.gross_shortfall) + "</td>" +
        "<td class='r'>" + imp(r.net_shortfall) + "</td>" +
        "<td class='r'>" + Math.round(r.masking_pct) + "%</td>" +
        "<td class='r'>" + exact(r.billed_shortfall) + "</td>" +
        "<td class='r'>" + r.share_pct.toFixed(0) + "%</td></tr>";
    }).join("");
  }

  function renderMarkets() {
    contribTable("#tMarket", D.by_market);
    contribTable("#tFormat", D.by_format);
    document.querySelector("#tFormat thead th").textContent = "Format";
  }

  function renderInventory() {
    var b = D.inventory_baseline;
    var more = b.observed_repeat_sites > b.expected_by_chance;
    document.getElementById("inventoryVerdict").innerHTML =
      '<div class="callout info"><span class="glyph">i</span><p>' +
      "<b>" + b.observed_repeat_sites + " sites</b> were flagged on two or more campaigns. " +
      "If every booking independently carried the overall " + b.flag_rate_pct.toFixed(1) +
      "% flag rate, <b>" + b.expected_by_chance + "</b> would be expected by chance alone. " +
      (more
        ? "Repeat under-delivery is running ahead of chance, which is worth investigating."
        : "Repeat under-delivery is <b>no more common than chance</b>, so this table is a " +
          "delivery history rather than a reliability ranking — the synthetic model gives no " +
          "site a persistent quality, and the data says so.") + "</p></div>";

    document.querySelector("#tInv thead").innerHTML =
      '<tr><th>Site</th><th class="r">Campaigns</th><th class="r">Placements</th>' +
      '<th class="r">Delivery</th><th class="r">Times flagged</th><th class="r">Downtime</th></tr>';
    document.querySelector("#tInv tbody").innerHTML = D.inventory.slice(0, 40).map(function (r) {
      return "<tr><td><div class='cellmain'>" + r.city + " · " + cap(r.format) + "</div>" +
        "<div class='cellsub'>" + esc(r.area) + " · site #" + r.site_id + "</div></td>" +
        "<td class='r'>" + r.campaigns_booked + "</td><td class='r'>" + r.placements + "</td>" +
        "<td class='r " + (r.delivery_pct < 95 ? "neg" : "") + "'>" + r.delivery_pct.toFixed(1) + "%</td>" +
        "<td class='r'>" + r.times_flagged + "</td>" +
        "<td class='r'>" + (r.downtime_hours_per_day === null ? "—"
          : r.downtime_hours_per_day.toFixed(2) + " h/day") + "</td></tr>";
    }).join("");
  }

  function renderEfficiency() {
    var E = D.efficiency;
    document.getElementById("cpmStatic").innerHTML =
      rankedBars(E.static, "cpm", "key", function (v) { return "$" + v.toFixed(2); });
    // One number is a stat, not a chart: a single-bar bar chart says nothing a
    // figure does not say better.
    var dig = E.digital[0];
    document.getElementById("cpmDigital").innerHTML = dig
      ? '<div class="solo"><span class="v num">$' + dig.cpm.toFixed(2) + "</span>" +
        '<span class="l">per thousand verified impressions · ' + dig.placements +
        " placements · " + cash(dig.spend) + " billed</span></div>"
      : "";
    document.getElementById("digitalNote").textContent = D.assumptions.digital_vs_static_cpm;
    document.getElementById("cpmPremium").innerHTML =
      rankedBars(E.premium_all, "cpm_premium_pct", "key",
                 function (v) { return "+" + v.toFixed(1) + "%"; });
  }

  function renderMethod() {
    var steps = [
      ["01", "Expected delivery today", "Contracted impressions prorated to the days that have actually run, so a live flight is judged on its elapsed days rather than its full booking.", "contracted × elapsed ÷ flight days"],
      ["02", "Verified delivery", "What the placement actually delivered over the same window, summed from the daily delivery records.", "Σ verified impressions"],
      ["03", "Delivery variance", "The two compared. Below −5% a placement is flagged; gross shortfall sums only the placements that are behind, with no credit for those running ahead.", "(verified − expected) ÷ expected"],
      ["04", "Media value exposure", "The shortfall priced at the rate the client agreed to pay per thousand — and, for live placements, what more accrues if nothing changes.", "shortfall × contracted CPM ÷ 1000"]
    ];
    document.getElementById("methodSteps").innerHTML = steps.map(function (s) {
      return '<div class="step"><div class="n">' + s[0] + "</div><h3>" + s[1] +
             "</h3><p>" + s[2] + "</p><code>" + s[3] + "</code></div>";
    }).join("");

    var labels = {
      as_of_basis: "As-of date and proration", gross_vs_net: "Gross against net shortfall",
      fault_model: "How faults are generated and found", detection: "Detection delay",
      preventable_exposure: "Preventable exposure ~", recovery_pace: "Required recovery pace",
      visibility_factors: "Visibility factors ~", reach_model: "Reach model ~",
      market_tiers: "Market tiers", spend_basis: "Spend basis",
      digital_vs_static_cpm: "Digital against static CPM",
      inventory_reliability: "Inventory reliability", downtime: "Downtime"
    };
    document.getElementById("assumptions").innerHTML = Object.keys(D.assumptions).map(function (k) {
      return "<details class='adet'><summary>" + (labels[k] || k) + "</summary><p>" +
             esc(D.assumptions[k]) + "</p></details>";
    }).join("");
  }

  /* ---------------- placement drawer ---------------- */
  var lastFocus = null;
  function openDrawer(id) {
    var all = D.attention.live.concat(D.attention.completed);
    var p = all.filter(function (x) { return x.placement_id === id; })[0];
    if (!p) {
      var keys = Object.keys(D.top_placements);
      for (var i = 0; i < keys.length && !p; i++) {
        p = D.top_placements[keys[i]].filter(function (x) { return x.placement_id === id; })[0];
      }
    }
    if (!p) return;
    lastFocus = document.activeElement;
    var dt = D.downtime[String(id)];
    var rows = [
      ["Status", chip(p.status, p.material)],
      ["Campaign", esc(p.campaign_name || "")],
      ["Contracted to date", imp(p.contracted_to_date)],
      ["Verified delivery", imp(p.verified_impressions)],
      ["Variance", pct(p.variance_pct)],
      ["Impressions short", imp(p.shortfall)],
      ["Spend billed", exact(p.spend)],
      ["Billed shortfall", exact(p.billed_shortfall)]
    ];
    if (p.preventable_exposure) rows.push(["Still preventable ~", exact(p.preventable_exposure)]);
    if (p.recovery_pace) rows.push(["Recovery pace", Math.round(p.recovery_pace * 100) + "%"]);
    if (p.onset_day !== null && p.onset_day !== undefined)
      rows.push(["Fault began", "flight day " + (p.onset_day + 1)]);
    if (p.detection_delay_days !== null && p.detection_delay_days !== undefined)
      rows.push(["Detected after", p.detection_delay_days + " days"]);

    document.getElementById("drawerBody").innerHTML =
      "<h2>" + placeName(p) + "</h2>" +
      '<div class="ddmeta">' + esc(p.area || "") + " · site #" + p.site_id + "</div>" +
      '<dl class="dl">' + rows.map(function (r) {
        return "<dt>" + r[0] + "</dt><dd>" + r[1] + "</dd>";
      }).join("") + "</dl>" +
      (dt ? '<p class="pnote" style="padding:0">Logged downtime of ' + dt.hours.toFixed(1) +
            " hours accounts for " + imp(dt.impressions) + " impressions — " +
            dt.share_of_shortfall_pct.toFixed(0) + "% of this placement's shortfall. " +
            "The rest is not explained by outages.</p>" : "");
    document.getElementById("drawer").hidden = false;
    requestAnimationFrame(function () {
      document.getElementById("drawer").classList.add("on");
      document.getElementById("scrim").classList.add("on");
      document.getElementById("dclose").focus();
    });
  }
  function closeDrawer() {
    document.getElementById("drawer").classList.remove("on");
    document.getElementById("scrim").classList.remove("on");
    setTimeout(function () { document.getElementById("drawer").hidden = true; }, 240);
    if (lastFocus) lastFocus.focus();
  }

  /* ---------------- boot ---------------- */
  buildNav();
  initTheme();
  initFilters();
  renderOverview();
  renderChips();
  renderAttention();
  renderCampaigns();
  renderMarkets();
  renderInventory();
  renderEfficiency();
  renderMethod();

  document.body.addEventListener("click", function (e) {
    var go = e.target.closest("[data-go]");
    if (go) { show(go.dataset.go); return; }
    var pl = e.target.closest("[data-placement]");
    if (pl) { openDrawer(Number(pl.dataset.placement)); return; }
    var cm = e.target.closest("[data-campaign]");
    if (cm) { openCampaign(Number(cm.dataset.campaign)); return; }
    var br = e.target.closest("[data-break]");
    if (br) {
      ddBreak = br.dataset.break;
      if (currentCampaign !== null) openCampaign(currentCampaign);
      return;
    }
    if (e.target.id === "ddBack") closeCampaign();
    if (e.target.id === "dclose" || e.target.id === "scrim") closeDrawer();
  });
  document.body.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeDrawer();
    if (e.key === "Enter") {
      var row = e.target.closest && e.target.closest("tr[data-placement]");
      if (row) openDrawer(Number(row.dataset.placement));
    }
  });
  document.getElementById("go-attention").addEventListener("click", function () {
    show("attention");
  });
  window.addEventListener("hashchange", function () {
    show(location.hash.replace("#", ""), true);
  });

  show(location.hash.replace("#", "") || "overview", true);
})();
