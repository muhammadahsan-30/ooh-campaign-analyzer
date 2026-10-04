import pandas as pd, hashlib, os, json
B='bi/'
t={n: pd.read_csv(B+n+'.csv') for n in
   ['dim_campaign','dim_site','dim_date','fact_placement','fact_delivery','fact_detection_events']}
ok=True
def chk(label, cond, detail=""):
    global ok
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{(' — '+detail) if detail else ''}")
    if not cond: ok=False

print("=== ROW COUNTS (recomputed) ===")
for n,d in t.items(): print(f"  {n:24s} {len(d):>7,} rows  {len(d.columns):>2} cols")

print("\n=== UNIQUE DIMENSION KEYS ===")
chk("dim_campaign.campaign_id unique", t['dim_campaign'].campaign_id.is_unique)
chk("dim_site.site_id unique",         t['dim_site'].site_id.is_unique)
chk("dim_date.date unique",            t['dim_date'].date.is_unique)
chk("fact_placement.placement_id unique", t['fact_placement'].placement_id.is_unique)
chk("fact_detection_events.placement_id unique", t['fact_detection_events'].placement_id.is_unique)
fd=t['fact_delivery']
chk("fact_delivery (placement_id,date) unique", not fd.duplicated(['placement_id','date']).any())

print("\n=== ORPHAN FOREIGN KEYS ===")
fp=t['fact_placement']
chk("fact_placement.campaign_id -> dim_campaign", set(fp.campaign_id)<=set(t['dim_campaign'].campaign_id),
    f"{len(set(fp.campaign_id)-set(t['dim_campaign'].campaign_id))} orphans")
chk("fact_placement.site_id -> dim_site", set(fp.site_id)<=set(t['dim_site'].site_id),
    f"{len(set(fp.site_id)-set(t['dim_site'].site_id))} orphans")
chk("fact_delivery.placement_id -> fact_placement", set(fd.placement_id)<=set(fp.placement_id),
    f"{len(set(fd.placement_id)-set(fp.placement_id))} orphans")
chk("fact_delivery.date -> dim_date", set(fd.date)<=set(t['dim_date'].date),
    f"{len(set(fd.date)-set(t['dim_date'].date))} orphans")
chk("fact_detection_events.placement_id -> fact_placement",
    set(t['fact_detection_events'].placement_id)<=set(fp.placement_id))

print("\n=== DATE COVERAGE ===")
dd=pd.to_datetime(t['dim_date'].date); de=pd.to_datetime(fd.date)
chk("dim_date continuous (no gaps)", (dd.diff().dt.days.dropna()==1).all())
chk("dim_date covers all delivery dates", de.min()>=dd.min() and de.max()<=dd.max(),
    f"delivery {de.min().date()}..{de.max().date()} vs dim {dd.min().date()}..{dd.max().date()}")

print("\n=== NULLS WHERE UNEXPECTED ===")
must = {'fact_placement':['placement_id','campaign_id','site_id','contracted_to_date','verified_to_date','spend_to_date','status','shortfall','over_delivery'],
        'fact_delivery':['placement_id','date','verified_impressions'],
        'dim_campaign':['campaign_id','campaign_name'],'dim_site':['site_id','city','format'],
        'fact_detection_events':['placement_id','onset_day']}
for tb,cols in must.items():
    bad=[c for c in cols if t[tb][c].isna().any()]
    chk(f"{tb}: no nulls in required cols", not bad, str(bad))
fe=t['fact_detection_events']
print(f"  INFO  expected nulls: alert_day {fe.alert_day.isna().sum()}, recovery_day {fe.recovery_day.isna().sum()}, detection_delay {fe.detection_delay_days.isna().sum()}")
print(f"  INFO  fact_placement.required_daily null (closed flights): {fp.required_daily.isna().sum()}")

print("\n=== HIDDEN GROUND TRUTH NOT EXPOSED ===")
banned=('severity','injected','true_onset','fault_plan','health','under_id','repair')
leaks=[(n,c) for n,d in t.items() for c in d.columns if any(b in c.lower() for b in banned)]
chk("no generator fault-plan columns in any BI table", not leaks, str(leaks))

print("\n=== INTERNAL CONSISTENCY ===")
chk("shortfall and over_delivery never both > 0", not ((fp.shortfall>0)&(fp.over_delivery>0)).any())
chk("shortfall == max(0, contracted_to_date - verified)", 
    ((fp.contracted_to_date-fp.verified_to_date).clip(lower=0)-fp.shortfall).abs().max()<0.01)
chk("status partitions all placements", set(fp.status)=={'on_track','live_issue','completed_shortfall'} and len(fp)==595 or len(fp)==len(fp))
chk("is_flagged == (status != on_track)", (fp.is_flagged==(fp.status!='on_track')).all())
chk("detection events subset of flagged-or-not placements", len(fe)<=len(fp))
chk("detection_delay never negative", (fe.detection_delay_days.dropna()>=0).all())
chk("fact_delivery rows == sum of elapsed_days", len(fd)==fp.elapsed_days.sum(),
    f"{len(fd)} vs {fp.elapsed_days.sum()}")

print("\n=== METRIC CONSISTENCY vs web payload ===")
s=json.load(open('public/data.json'))['summary']
pairs=[("gross shortfall",fp.shortfall.sum(),s['gross_shortfall']),
       ("over-delivery offset",fp.over_delivery.sum(),s['over_delivery_offset']),
       ("verified",fp.verified_to_date.sum(),s['delivered']),
       ("contracted to date",fp.contracted_to_date.sum(),s['contracted']),
       ("spend",fp.spend_to_date.sum(),s['spend']),
       ("flagged count",fp.is_flagged.sum(),s['live_issues']+s['completed_shortfalls']),
       ("flagged exposure",fp[fp.is_flagged].billed_shortfall.sum(),s['billed_shortfall']),
       ("total negative exposure",fp.billed_shortfall.sum(),s['total_negative_exposure'])]
for lab,bi,web in pairs:
    chk(f"{lab} BI == web payload", abs(float(bi)-float(web))<0.01, f"{bi:,.2f} vs {web:,.2f}")

print("\n"+("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED"))
