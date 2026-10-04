"""
Cross-system validation for the BI layer.

Computes each metric three ways and writes bi/validation_expected.csv:

  python_value            from src/metrics.py -- the authoritative implementation
  sql_value               from raw SQL against ooh.db, computed independently
  expected_powerbi_value  what the DAX measure in docs/powerbi-dax.md must return

The point is semantic correctness, not forced numerical equality. Where a
population differs the difference is recorded in `population_definition` rather
than reconciled away -- that distinction is the whole reason this file exists.

Two measures are deliberately NOT interchangeable and must never share a label:

  Total negative delivery exposure   every placement behind by any amount (227)
  Flagged media-value exposure       only those past the -5% line (82)

Run:  python src/validate_bi.py
"""
import os, sqlite3, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics as m
import export_bi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB   = os.environ.get("OOH_DB", os.path.join(ROOT, "data", "ooh.db"))
OUT  = os.path.join(ROOT, "bi", "validation_expected.csv")

# One prorated-placement CTE, reused by every SQL check so the SQL side is a
# genuinely independent reimplementation rather than a copy of the Python.
CTE = """
WITH pd AS (
  SELECT p.placement_id,
         p.contracted_impressions * COUNT(*)
             / (julianday(p.end_date) - julianday(p.start_date)) AS ctd,
         SUM(d.verified_impressions)          AS ver,
         p.negotiated_rate * COUNT(*) / 28.0  AS spend
  FROM placements p
  JOIN delivery d ON d.placement_id = p.placement_id
  GROUP BY p.placement_id
)
"""


def sql(con, expr, where=""):
    return con.execute(f"{CTE} SELECT {expr} FROM pd {where}").fetchone()[0]


def main():
    con = sqlite3.connect(DB)
    daily = pd.read_sql_query(
        "SELECT placement_id, date, verified_impressions, estimated_impressions, "
        "downtime_hours FROM delivery ORDER BY placement_id, date", con)
    df = export_bi.load(con)
    as_of = m.as_of_date(df)
    df = export_bi.enrich(df, daily, as_of)

    behind  = df[df["shortfall"] > 0]
    flagged = df[df["is_flagged"]]
    dec     = m.shortfall_decomposition(df)

    BEHIND = "every placement delivering under contract to date"
    FLAG   = "placements breaching the -5% attention line"
    ALL    = "all placements"

    rows = [
        dict(metric="Total spend",
             python_value=df["spend"].sum(),
             sql_value=sql(con, "SUM(spend)"),
             population_definition=ALL, tolerance=0.01),
        dict(metric="Verified impressions to date",
             python_value=df["verified_impressions"].sum(),
             sql_value=sql(con, "SUM(ver)"),
             population_definition=ALL, tolerance=1),
        dict(metric="Contracted to date",
             python_value=df["contracted_to_date"].sum(),
             sql_value=sql(con, "SUM(ctd)"),
             population_definition=ALL, tolerance=1),
        dict(metric="Gross shortfall",
             python_value=dec["gross_shortfall"],
             sql_value=sql(con, "SUM(CASE WHEN ver<ctd THEN ctd-ver ELSE 0 END)"),
             population_definition=BEHIND, tolerance=1),
        dict(metric="Over-delivery offset",
             python_value=dec["over_delivery_offset"],
             sql_value=sql(con, "SUM(CASE WHEN ver>ctd THEN ver-ctd ELSE 0 END)"),
             population_definition="every placement delivering above contract to date",
             tolerance=1),
        dict(metric="Net shortfall",
             python_value=dec["net_shortfall"],
             sql_value=sql(con, "SUM(ctd-ver)"),
             population_definition=ALL + " (gross minus offset)", tolerance=1),
        dict(metric="Total negative delivery exposure",
             python_value=df["billed_shortfall"].sum(),
             sql_value=sql(con, "SUM(CASE WHEN ver<ctd THEN (ctd-ver)*spend/ctd ELSE 0 END)"),
             population_definition=BEHIND + " -- NOT the same as the flagged measure below",
             tolerance=0.01),
        dict(metric="Flagged media-value exposure",
             python_value=flagged["billed_shortfall"].sum(),
             sql_value=sql(con, "SUM(CASE WHEN ver<ctd THEN (ctd-ver)*spend/ctd ELSE 0 END)",
                           "WHERE (ver-ctd)*100.0/ctd < -5"),
             population_definition=FLAG + " -- NOT the same as the total above",
             tolerance=0.01),
        dict(metric="Flagged placement count",
             python_value=len(flagged),
             sql_value=sql(con, "COUNT(*)", "WHERE (ver-ctd)*100.0/ctd < -5"),
             population_definition=FLAG, tolerance=0),
        dict(metric="Placements behind",
             python_value=len(behind),
             sql_value=sql(con, "COUNT(*)", "WHERE ver < ctd"),
             population_definition=BEHIND, tolerance=0),
        dict(metric="Live issues",
             python_value=int((df["status"] == "live_issue").sum()),
             sql_value=None,
             population_definition="flagged placements still in flight; status is derived in Python",
             tolerance=0),
        dict(metric="Completed shortfalls",
             python_value=int((df["status"] == "completed_shortfall").sum()),
             sql_value=None,
             population_definition="flagged placements whose flight has closed; derived in Python",
             tolerance=0),
    ]

    out = []
    for r in rows:
        py, sq, tol = float(r["python_value"]), r["sql_value"], float(r["tolerance"])
        if sq is None:
            status = "PYTHON ONLY"
        else:
            status = "MATCH" if abs(py - float(sq)) <= tol else "DIVERGENT"
        out.append({
            "metric": r["metric"],
            "python_value": round(py, 2),
            "sql_value": "" if sq is None else round(float(sq), 2),
            # DAX aggregates the same exported grain, so it must land on Python.
            "expected_powerbi_value": round(py, 2),
            "population_definition": r["population_definition"],
            "tolerance": tol,
            "status": status,
        })

    frame = pd.DataFrame(out)
    frame.to_csv(OUT, index=False)
    con.close()

    w = max(len(r["metric"]) for r in out)
    print(f"{'metric'.ljust(w)}  {'python':>16} {'sql':>16}  status")
    for r in out:
        print(f"{r['metric'].ljust(w)}  {r['python_value']:>16,.2f} "
              f"{(r['sql_value'] if r['sql_value']!='' else float('nan')):>16,.2f}  {r['status']}")
    bad = [r for r in out if r["status"] == "DIVERGENT"]
    print(f"\n{len(out)} metrics · {sum(1 for r in out if r['status']=='MATCH')} matched · "
          f"{sum(1 for r in out if r['status']=='PYTHON ONLY')} python-only · {len(bad)} divergent")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
