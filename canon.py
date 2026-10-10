"""Canonicalise team names -> stable team ids. Writes matches_canon.json + teams.json."""
import json, re, sys, unicodedata, difflib
from collections import defaultdict, Counter

IN, OUT_M, OUT_T = sys.argv[1:4]
matches = json.load(open(IN))

TRANS = str.maketrans({"ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE", "ß": "ss", "đ": "d", "ł": "l", "Ł": "L", "ð": "d", "þ": "th", "œ": "oe", "ı": "i"})
STOP = {
    "fc", "afc", "cf", "sc", "ac", "ssc", "fk", "sk", "bk", "if", "ik", "sv", "tsv", "vfl", "vfb", "tsg", "fsv", "rc", "rcd", "ud", "cd",
    "ca", "sd", "cp", "de", "la", "el", "club", "bv", "vf", "spvgg", "esv", "msv", "sg", "ff", "fb", "gf", "futbol", "balompie", "calcio", "bsc_",
}
TOKMAP = {"utd": "united", "man": "manchester", "nottm": "nottingham"}

ALIAS = {
    # England
    "tottenham": "tottenham hotspur", "wolves": "wolverhampton wanderers", "west brom": "west bromwich albion",
    "brighton": "brighton and hove albion", "qpr": "queens park rangers", "newcastle": "newcastle united",
    "leeds": "leeds united", "sheffield utd": "sheffield united",
    # Germany
    "bayern munich": "bayern munchen", "bayern": "bayern munchen",
    "borussia mgladbach": "monchengladbach", "borussia monchengladbach": "monchengladbach", "bor monchengladbach": "monchengladbach",
    "mgladbach": "monchengladbach", "gladbach": "monchengladbach",
    "hamburger": "hamburg", "hertha berlin": "hertha bsc", "hertha": "hertha bsc", "leipzig": "rb leipzig",
    "borussia dortmund": "dortmund", "bayer leverkusen": "leverkusen", "eintracht frankfurt": "frankfurt",
    "bor dortmund": "dortmund",
    # Spain
    "athletic": "athletic bilbao", "alaves": "deportivo alaves", "rayo vallecano madrid": "rayo vallecano",
    "espanyol barcelona": "espanyol", "deportivo coruna": "deportivo la coruna", "atletico de madrid": "atletico madrid",
    "real sociedad": "real sociedad", "celta": "celta vigo", "real betis": "real betis",
    "real madrid c f": "real madrid", "qarabag agdam": "qarabag", "royale union saint gilloise": "union saint gilloise",
    "gnk dinamo zagreb": "dinamo zagreb", "racing lens": "lens", "atalanta bc": "atalanta", "feyenoord rotterdam": "feyenoord",
    "psv eindhoven": "psv", "sporting clube portugal": "sporting", "sporting clube braga": "sporting braga", "ue santa coloma": "santa coloma",
    "internazionale milano": "inter", "sport lisboa e benfica": "sl benfica", "red bull salzburg": "rb salzburg",
    "pae olympiakos sfp": "olympiakos piraeus",
    # Italy / France
    "acf fiorentina": "fiorentina", "us cremonese": "cremonese", "genoa cfc": "genoa", "ss lazio": "lazio", "lazio roma": "lazio",
    "us lecce": "lecce", "uc sampdoria": "sampdoria", "us sassuolo": "sassuolo", "as roma": "roma",
    "aj auxerre": "auxerre", "es troyes": "troyes", "estac troyes": "troyes", "lille osc": "lille", "strasbourg alsace": "strasbourg", "paris": "paris fc",
    "az": "az alkmaar", "nec": "nec nijmegen", "sbv vitesse": "vitesse", "cambuur leeuwarden": "cambuur",
    # Denmark (European matches only)
    "copenhagen": "kobenhavn", "agf": "aarhus", "aab": "aalborg", "ob": "odense", "odense boldklub": "odense",
}


def norm(name):
    s = name.translate(TRANS)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ").replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    toks = [TOKMAP.get(t, t) for t in s.split()]
    toks = [t for t in toks if t not in STOP and not re.fullmatch(r"\d{1,4}", t)]
    k = " ".join(toks)
    return ALIAS.get(k, k)


DOMESTIC = {"ENG1": "ENG", "GER1": "GER", "ESP1": "ESP", "ITA1": "ITA", "FRA1": "FRA", "NED1": "NED", "POR1": "POR"}
BIG = set(DOMESTIC.values())

# 1) domestic key sets
dom_keys = defaultdict(set)
for m in matches:
    if m["comp"] in DOMESTIC:
        c = DOMESTIC[m["comp"]]
        dom_keys[c].add(norm(m["h"]))
        dom_keys[c].add(norm(m["a"]))

# 2) team ids
raw_names = defaultdict(Counter)  # id -> raw name -> latest date count
latest_raw = {}                   # id -> (date, raw)


def tid(raw, country):
    k = norm(raw)
    return f"{country}:{k}", k


unmapped_big = Counter()
for m in matches:
    for side, cc in (("h", "hc"), ("a", "ac")):
        raw, c = m[side], m[cc]
        if c is None:
            c = "UNK"
        i, k = tid(raw, c)
        if c in BIG and m["comp"] not in DOMESTIC and k not in dom_keys[c]:
            unmapped_big[(c, raw, k)] += 1
        m[side + "id"] = i
        raw_names[i][raw] += 1
        if i not in latest_raw or m["d"] >= latest_raw[i][0]:
            latest_raw[i] = (m["d"], raw)

# diagnostics 1: domestic team counts per season
print("== domestic teams per league-season (expected ENG20 GER18 ESP20 ITA20 FRA20/18)")
per = defaultdict(set)
for m in matches:
    if m["comp"] in DOMESTIC:
        per[(m["comp"], m["s"])].update([m["hid"], m["aid"]])
bad = False
for (lg, s), t in sorted(per.items()):
    exp = {"ENG1": 20, "GER1": 18, "ESP1": 20, "ITA1": 20, "FRA1": 18 if s >= 2023 else 20, "NED1": 18, "POR1": 18}[lg]
    flag = "" if len(t) == exp else "   <-- CHECK"
    if flag:
        bad = True
    if flag or s in (2000, 2010, 2012, 2025, 2026):
        print(f"{lg} {s}: {len(t)}{flag}")
print("all seasons ok" if not bad else "")

print("\n== Euro rows with big-4 country code not matching any domestic key:")
for (c, raw, k), n in unmapped_big.most_common(40):
    near = difflib.get_close_matches(k, list(dom_keys[c]), n=2, cutoff=0.6)
    print(f"{c} '{raw}' key='{k}' x{n}  near={near}")

print("\n== near-duplicate keys within a country (possible split clubs):")
by_c = defaultdict(set)
for i in raw_names:
    c, k = i.split(":", 1)
    by_c[c].add(k)
for c, ks in sorted(by_c.items()):
    ks = sorted(ks)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            if difflib.SequenceMatcher(None, ks[i], ks[j]).ratio() > 0.84 or (ks[i] in ks[j].split() or ks[j] in ks[i].split()):
                print(f"{c}: '{ks[i]}' ~ '{ks[j]}'")

json.dump(matches, open(OUT_M, "w"), ensure_ascii=False)
teams = {i: dict(country=i.split(":", 1)[0], key=i.split(":", 1)[1], raw=latest_raw[i][1], last=latest_raw[i][0], n=sum(raw_names[i].values())) for i in raw_names}
json.dump(teams, open(OUT_T, "w"), ensure_ascii=False)
print("\nteams:", len(teams), "| per big country:", {c: sum(1 for t in teams.values() if t["country"] == c) for c in sorted(BIG)})
