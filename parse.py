"""Parse openfootball text files into a flat list of matches (raw team names)."""
import json, re, sys, glob, os
from datetime import date

ROOT = os.environ.get("OF_ROOT", "/home/claude/data/openfootball")
OUT = sys.argv[1]

MONTHS = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
DATE_RE = re.compile(r"^\s*(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(\d{4}))?\s*$")
V_RE = re.compile(r"^\s*(?:\d{1,2}:\d{2}\s+)?(.+?)\s+v\s+(.+?)\s{2,}(\d+)-(\d+)(.*)$")
A_RE = re.compile(r"^\s*(?:\d{1,2}:\d{2}\s+)?(.+?)\s{2,}(\d+)-(\d+)(?:\s*\(\d+-\d+\))?\s{2,}(\S.*?)\s*$")
CODE_RE = re.compile(r"\s*\(([A-Z]{3})\)\s*$")
PAREN2 = re.compile(r"\((\d+)-(\d+),\s*(\d+)-(\d+)\)")
PAREN1 = re.compile(r"\((\d+)-(\d+)\)")


def parse_file(path, season0, comp, country=None):
    out = []
    cur = None
    stage = ""
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("="):
            continue
        if s.startswith("▪"):
            stage = s.lstrip("▪").strip()
            continue
        m = DATE_RE.match(line)
        if m:
            mon, day, yr = MONTHS[m.group(1)], int(m.group(2)), m.group(3)
            if yr:
                y = int(yr)
            else:
                y = season0 if mon >= 7 else season0 + 1
            cur = date(y, mon, day)
            continue
        if s.startswith("(") or cur is None:
            continue
        h = a = None
        hg = ag = None
        m = V_RE.match(line)
        if m:
            h, a = m.group(1).strip(), m.group(2).strip()
            hg, ag, tail = int(m.group(3)), int(m.group(4)), m.group(5)
            if "a.e.t." in tail or "pen." in tail:
                p = PAREN2.search(tail)
                if p:
                    hg, ag = int(p.group(1)), int(p.group(2))
                else:
                    continue  # cannot recover regulation-time score
        else:
            m = A_RE.match(line)
            if not m:
                continue
            h, a = m.group(1).strip(), re.sub(r"\s*\[.*?\]\s*$", "", m.group(4)).strip()
            hg, ag = int(m.group(2)), int(m.group(3))
        ch = CODE_RE.search(h)
        ca = CODE_RE.search(a)
        hc = ch.group(1) if ch else country
        ac = ca.group(1) if ca else country
        hc = {"MCO": "FRA"}.get(hc, hc); ac = {"MCO": "FRA"}.get(ac, ac)
        h = CODE_RE.sub("", h).strip()
        a = CODE_RE.sub("", a).strip()
        neutral = comp in ("CL", "EL", "UECL") and stage.lower().endswith("final") and "semi" not in stage.lower() and "quarter" not in stage.lower()
        out.append(dict(d=cur.isoformat(), comp=comp, s=season0, h=h, a=a, hc=hc, ac=ac, hg=hg, ag=ag, n=int(neutral), st=stage))
    return out


matches = []
# domestic
for league, folder, country, pat in [
    ("ENG1", "england", "ENG", "1-*.txt"),
    ("GER1", "deutschland", "GER", "1-*.txt"),
    ("ESP1", "espana", "ESP", "1-*.txt"),
    ("ITA1", "italy", "ITA", "1-seriea.txt"),
]:
    for d in sorted(glob.glob(f"{ROOT}/{folder}/[0-9][0-9][0-9][0-9]-[0-9][0-9]")):
        s0 = int(os.path.basename(d)[:4])
        files = [f for f in glob.glob(f"{d}/{pat}") if not f.endswith("-full.txt")]
        for f in files:
            matches += parse_file(f, s0, league, country)
for f in sorted(glob.glob(f"{ROOT}/europe/france/*_fr1.txt")):
    s0 = int(os.path.basename(f)[:4])
    matches += parse_file(f, s0, "FRA1", "FRA")
for lg, folder, code, suf in (("NED1", "netherlands", "NED", "nl1"), ("POR1", "portugal", "POR", "pt1")):
    for f in sorted(glob.glob(f"{ROOT}/europe/{folder}/*_{suf}.txt")):
        s0 = int(os.path.basename(f)[:4])
        matches += parse_file(f, s0, lg, code)
# european
COMPS = {"cl": "CL", "clq": "CLQ", "el": "EL", "elq": "ELQ", "conf": "UECL", "confq": "UECLQ"}
for d in sorted(glob.glob(f"{ROOT}/europe-champions-league/[0-9][0-9][0-9][0-9]-[0-9][0-9]")):
    s0 = int(os.path.basename(d)[:4])
    for k, c in COMPS.items():
        f = f"{d}/{k}.txt"
        if os.path.exists(f):
            matches += parse_file(f, s0, c)

matches.sort(key=lambda m: m["d"])
json.dump(matches, open(OUT, "w"), ensure_ascii=False)

# diagnostics
from collections import Counter, defaultdict
cnt = Counter((m["comp"], m["s"]) for m in matches)
print("total matches:", len(matches))
for comp in ["ENG1", "GER1", "ESP1", "ITA1", "FRA1", "NED1", "POR1", "CL", "CLQ", "EL", "ELQ", "UECL", "UECLQ"]:
    row = {s: n for (c, s), n in sorted(cnt.items()) if c == comp}
    print(comp, row)
print("last match date per comp:")
for comp in ["ENG1", "GER1", "ESP1", "ITA1", "FRA1", "NED1", "POR1", "CL", "EL", "UECL"]:
    ds = [m["d"] for m in matches if m["comp"] == comp]
    print(" ", comp, max(ds) if ds else None)
print("country codes (euro):", Counter(m["hc"] for m in matches if m["comp"] in COMPS.values()).most_common(8))
