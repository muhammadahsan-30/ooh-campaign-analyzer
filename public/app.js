/*
 * OOH Campaign Performance Analyzer — dashboard.
 *
 * Presentation only. Every metric shown here was computed in Python
 * (src/metrics.py) and written out by src/export_json.py. Nothing is
 * recalculated in the browser, so there is one source of truth for the numbers
 * and the figures on screen are the ones the unit tests cover.
 *
 * Data arrives as window.OOH_DATA from data.js rather than fetch('data.json'),
 * because browsers block fetch() against file:// URLs — this way the dashboard
 * opens correctly straight from disk as well as from a web server.
 */
(function () {
  "use strict";

  var D = window.OOH_DATA;
  var charts = {};
  var FIELDS = ["fClient", "fCity", "fFormat"];

  if (!D) {
    document.getElementById("cards").innerHTML =
      '<p class="empty">data.js missing — run <code>python src/export_json.py</code></p>';
    return;
  }

  // ---------- formatting ----------
  function nfmt(n) {
    if (n === null || n === undefined || isNaN(n)) return "—";
    var a = Math.abs(n);
    if (a >= 1e9) return (n / 1e9).toFixed(2) + "bn";
    if (a >= 1e6) return (n / 1e6).toFixed(1) + "m";
    if (a >= 1e3) return Math.round(n / 1e3) + "k";
    return Math.round(n).toLocaleString();
  }
  function pct(n) {
    if (n === null || n === undefined || isNaN(n)) return "—";
    return (n > 0 ? "+" : "") + n.toFixed(1) + "%";
  }
  function money(n) { return Math.round(n).toLocaleString(); }
  function tidy(s) { return String(s).replace(/_/g, " "); }
  function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }

  // ---------- KPI cards ----------
  function renderCards(s) {
    // The two flagged cards lead: they are the answer the dashboard exists to
    // give. Spend / delivered / CPM follow as context.
    var cards = [
      { lab: "Under-delivering", val: s.under_count, sub: s.under_pct.toFixed(1) + "% of placements below −5%", cls: "flag" },
      { lab: "Spend at risk", val: "$" + money(s.value_at_risk), sub: "CAD attached to the shortfall", cls: "flag" },
      { lab: "Media spend tracked", val: "$" + money(s.spend), sub: "CAD across " + s.placements + " placements" },
      { lab: "Impressions delivered", val: nfmt(s.delivered), sub: "vs " + nfmt(s.contracted) + " contracted", cls: "ok" },
      { lab: "Blended CPM", val: "$" + s.blended_cpm.toFixed(2), sub: "CAD per thousand, verified delivery" }
    ];
    document.getElementById("cards").innerHTML = cards.map(function (c) {
      return '<div class="kpi ' + (c.cls || "") + '">' +
             '<div class="lab">' + c.lab + "</div>" +
             '<div class="val">' + c.val + "</div>" +
             '<div class="sub">' + c.sub + "</div></div>";
    }).join("");
  }

  // ---------- filters ----------
  function fillSelect(id, values) {
    var el = document.getElementById(id);
    values.slice().sort().forEach(function (v) {
      var o = document.createElement("option");
      o.value = v; o.textContent = tidy(v);
      el.appendChild(o);
    });
  }
  function filters() {
    return {
      client: document.getElementById("fClient").value,
      city: document.getElementById("fCity").value,
      format: document.getElementById("fFormat").value
    };
  }

  // ---------- tables ----------
  function renderWorst() {
    var f = filters();
    var rows = D.worst_placements.filter(function (r) {
      return (!f.client || r.client_name === f.client)
          && (!f.city   || r.city        === f.city)
          && (!f.format || r.format      === f.format);
    });
    var tb = document.querySelector("#tWorst tbody");
    document.getElementById("count").textContent =
      rows.length + " of " + D.worst_placements.length + " flagged placements shown";
    if (!rows.length) {
      tb.innerHTML = '<tr><td colspan="8" class="empty">No under-delivering placements match these filters.</td></tr>';
      return;
    }
    tb.innerHTML = rows.map(function (r, i) {
      return "<tr>" +
        '<td class="rank">' + (i + 1) + "</td>" +
        "<td>" + r.client_name + "</td>" +
        '<td class="dim">' + r.city + "</td>" +
        '<td><span class="pill">' + tidy(r.format) + "</span></td>" +
        '<td class="num">' + nfmt(r.contracted_impressions) + "</td>" +
        '<td class="num">' + nfmt(r.verified_impressions) + "</td>" +
        '<td class="num ' + (r.variance_pct < 0 ? "neg" : "pos") + '">' + pct(r.variance_pct) + "</td>" +
        '<td class="num">' + money(r.spend) + "</td>" +
        "</tr>";
    }).join("");
  }

  function renderCampaigns() {
    var f = filters();
    var rows = D.campaigns.filter(function (c) {
      return (!f.client || c.client === f.client)
          // a campaign matches a city filter if it ran in that market at all
          && (!f.city   || c.market_list.indexOf(f.city) !== -1);
    });
    var tb = document.querySelector("#tCamp tbody");
    if (!rows.length) {
      tb.innerHTML = '<tr><td colspan="10" class="empty">No campaigns match these filters.</td></tr>';
      return;
    }
    tb.innerHTML = rows.map(function (c) {
      return "<tr>" +
        "<td>" + c.client + "</td>" +
        '<td><span class="pill">' + tidy(c.objective) + "</span></td>" +
        '<td class="num dim" title="' + c.market_list.join(", ") + '">' + c.markets + "</td>" +
        '<td class="num">' + c.placements + "</td>" +
        '<td class="num">' + money(c.spend) + "</td>" +
        '<td class="num">' + nfmt(c.delivered) + "</td>" +
        '<td class="num ' + (c.variance_pct < 0 ? "neg" : "pos") + '">' + pct(c.variance_pct) + "</td>" +
        '<td class="num">' + c.cpm.toFixed(2) + "</td>" +
        '<td class="num">' + c.reach_pct.toFixed(0) + "%</td>" +
        '<td class="num">' + c.frequency.toFixed(1) + "</td>" +
        "</tr>";
    }).join("");
  }

  // ---------- charts ----------
  function baseOpts() {
    var grid = css("--line"), text = css("--muted");
    return {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: text, font: { family: "Inter", size: 11 }, boxWidth: 10, usePointStyle: true } },
        tooltip: {
          backgroundColor: css("--surface-2"), borderColor: grid, borderWidth: 1,
          titleColor: css("--text"), bodyColor: text, padding: 10, displayColors: false
        }
      },
      scales: {
        x: { grid: { color: grid, drawTicks: false }, ticks: { color: text, font: { family: "Inter", size: 10 } } },
        y: { grid: { color: grid, drawTicks: false },
             ticks: { color: text, font: { family: "Inter", size: 10 }, callback: function (v) { return nfmt(v); } } }
      }
    };
  }

  function renderMonthly() {
    var m = D.monthly;
    if (charts.monthly) charts.monthly.destroy();
    var o = baseOpts();
    o.plugins.tooltip.callbacks = { label: function (c) { return c.dataset.label + ": " + nfmt(c.parsed.y); } };
    charts.monthly = new Chart(document.getElementById("cMonthly"), {
      type: "line",
      data: {
        labels: m.map(function (r) { return r.month; }),
        datasets: [
          { label: "Planned", data: m.map(function (r) { return r.planned; }),
            borderColor: css("--faint"), borderDash: [4, 4], borderWidth: 1.5,
            pointRadius: 0, tension: .3, fill: false },
          { label: "Delivered", data: m.map(function (r) { return r.delivered; }),
            borderColor: css("--cyan"), backgroundColor: css("--cyan-dim"),
            borderWidth: 2, pointRadius: 0, tension: .3, fill: true }
        ]
      },
      options: o
    });
  }

  function renderFormat() {
    var f = D.by_format.slice().sort(function (a, b) { return a.cpm - b.cpm; });
    if (charts.fmt) charts.fmt.destroy();
    var o = baseOpts();
    o.plugins.legend.display = false;
    o.plugins.tooltip.callbacks = { label: function (c) { return "CPM $" + c.parsed.y.toFixed(2) + " CAD"; } };
    o.scales.y.ticks.callback = function (v) { return "$" + v.toFixed(2); };
    charts.fmt = new Chart(document.getElementById("cFormat"), {
      type: "bar",
      data: {
        labels: f.map(function (r) { return tidy(r.key); }),
        datasets: [{ data: f.map(function (r) { return r.cpm; }),
                     backgroundColor: css("--amber"), borderRadius: 4, maxBarThickness: 46 }]
      },
      options: o
    });
  }

  // ---------- assumptions ----------
  function renderAssumptions() {
    var labels = {
      visibility_factors: "Visibility factors",
      reach_model: "Reach model",
      reach_limitation: "Reach — known limitation",
      market_tiers: "Market tiers",
      under_delivery: "Under-delivery rate",
      spend_basis: "Spend basis"
    };
    document.getElementById("assump").innerHTML = Object.keys(D.assumptions).map(function (k) {
      return '<div class="arow"><dt>' + (labels[k] || k) + "</dt><dd>" + D.assumptions[k] + "</dd></div>";
    }).join("");
  }

  // ---------- boot ----------
  function redraw() { renderWorst(); renderCampaigns(); }

  renderCards(D.summary);
  fillSelect("fClient", D.by_client.map(function (r) { return r.key; }));
  fillSelect("fCity", D.by_city.map(function (r) { return r.key; }));
  fillSelect("fFormat", D.by_format.map(function (r) { return r.key; }));
  FIELDS.forEach(function (id) {
    document.getElementById(id).addEventListener("change", redraw);
  });
  document.getElementById("reset").addEventListener("click", function () {
    FIELDS.forEach(function (id) { document.getElementById(id).value = ""; });
    redraw();
  });
  renderMonthly();
  renderFormat();
  renderAssumptions();
  redraw();
})();
