"""Sanity checks after a rebuild. Exit code 1 = do NOT publish. Prints warnings for things to review."""
import json, sys, datetime
d = json.load(open("data.json"))
T = d["teams"]
fail, warn = [], []
exp = {"ENG": 20, "ESP": 20, "ITA": 20, "GER": 18, "FRA": 18, "NED": 18, "POR": 18}
cnt = {}
for t in T:
    if t["sel"]:
        cnt[t["c"]] = cnt.get(t["c"], 0) + 1
for c, n in exp.items():
    if cnt.get(c) != n:
        fail.append(f"{c}: {cnt.get(c)} selectable teams, expected {n}")
if len(T) < 300: fail.append("too few teams in table")
bt = d["meta"]["backtest"]
if bt["acc"] < 0.48 or bt["ll_model"] >= bt["ll_base"]: fail.append(f"backtest looks broken: {bt}")
names = [t["name"] for t in T if t["sel"]]
dups = {n for n in names if names.count(n) > 1}
if dups: fail.append(f"duplicate display names: {sorted(dups)}")
lm = d["model"]
if not (1500 < lm["r_ref"] < 1800): fail.append("r_ref out of range")
age = (datetime.date.today() - datetime.date.fromisoformat(d["meta"]["data_end"])).days
if age > 21: warn.append(f"latest league match is {age} days old ({d['meta']['data_end']}) - source may be lagging (or international break/off-season)")
for k, v in d["meta"]["last"].items():
    a = (datetime.date.today() - datetime.date.fromisoformat(v)).days
    if a > 60: warn.append(f"{k}: last match {v} ({a} days old)")
try:
    known = set(json.load(open("known_teams.json")))
except Exception:
    known = None
ids = {t["id"]: t["name"] for t in T if t["sel"]}
if known is not None:
    new = sorted(ids[i] for i in set(ids) - known); gone = sorted(known - set(ids))
    if new: warn.append(f"NEW selectable teams (check display names): {new}")
    if gone: warn.append(f"REMOVED teams: {gone}")
json.dump(sorted(ids), open("known_teams.new.json", "w"))
print("teams selectable:", len(names), "| data_end:", d["meta"]["data_end"], "| backtest n=%d acc=%.3f" % (bt["n"], bt["acc"]))
for w in warn: print("WARN:", w)
for f in fail: print("FAIL:", f)
print("CHECK", "FAILED" if fail else "OK")
sys.exit(1 if fail else 0)
