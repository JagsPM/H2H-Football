"""Pack Elo output into a compact JSON for the web page."""
import json, math, re
from collections import defaultdict, Counter

o = json.load(open("elo_out.json"))
R, pre, P = o["R"], o["pre"], o["params"]
bt = json.load(open("backtest.json"))
M = json.load(open("matches_canon.json"))
M.sort(key=lambda m: m["d"])
teams = json.load(open("teams.json"))
assert len(M) == len(pre)

DOM = {"ENG1", "GER1", "ESP1", "ITA1", "FRA1", "NED1", "POR1"}
BIG = {"ENG", "GER", "ESP", "ITA", "FRA", "NED", "POR"}
COMP_LABEL = {"ENG1": "PL", "GER1": "BL", "ESP1": "LL", "ITA1": "SA", "FRA1": "L1", "NED1": "ED", "POR1": "PPL", "CL": "CL", "CLQ": "CL-kval", "EL": "EL", "ELQ": "EL-kval", "UECL": "Conf", "UECLQ": "Conf-kval"}
COMPS = list(COMP_LABEL)
LEAGUE_NAME = {"ENG": "Premier League", "GER": "Bundesliga", "ESP": "La Liga", "ITA": "Serie A", "FRA": "Ligue 1", "NED": "Eredivisie", "POR": "Primeira Liga"}
COUNTRY_DK = {"DEN": "Danmark", "POR": "Portugal", "NED": "Holland", "BEL": "Belgien", "TUR": "Tyrkiet", "SCO": "Skotland",
              "AUT": "Østrig", "SUI": "Schweiz", "GRE": "Grækenland", "CRO": "Kroatien", "NOR": "Norge", "SWE": "Sverige", "POL": "Polen",
              "CZE": "Tjekkiet", "SRB": "Serbien", "UKR": "Ukraine", "ISR": "Israel", "CYP": "Cypern", "HUN": "Ungarn", "ROU": "Rumænien",
              "BUL": "Bulgarien", "ARM": "Armenien", "BIH": "Bosnien-Hercegovina", "LVA": "Letland", "MDA": "Moldova", "LTU": "Litauen", "EST": "Estland", "MKD": "Nordmakedonien", "GEO": "Georgien", "MNE": "Montenegro", "ALB": "Albanien", "LUX": "Luxembourg", "MLT": "Malta", "FRO": "Færøerne", "GIB": "Gibraltar", "SVN": "Slovenien", "SVK": "Slovakiet", "KAZ": "Kasakhstan", "AZE": "Aserbajdsjan", "MCO": "Monaco (FRA)",
              "FIN": "Finland", "IRL": "Irland", "WAL": "Wales", "NIR": "Nordirland", "ISL": "Island", "RUS": "Rusland", "BLR": "Belarus"}

Kd, Ke, HFA = P["Kd"], P["Ke"], P["HFA"]


def G(gd):
    gd = abs(gd)
    return 1.0 if gd <= 1 else (1.5 if gd == 2 else (11 + gd) / 8.0)


def disp(raw):
    special = {"AZ": "AZ Alkmaar", "Feyenoord Rotterdam": "Feyenoord", "Cambuur-Leeuwarden": "Cambuur", "Twente '65": "Twente", "SBV Excelsior": "Excelsior", "Willem II Tilburg": "Willem II", "CF Estrela da Amadora": "Estrela da Amadora", "CS Marítimo": "Marítimo", "GD Estoril Praia": "Estoril", "Sporting Clube de Braga": "Sporting Braga", "Casa Pia AC": "Casa Pia", "NEC": "NEC Nijmegen", "AJ Auxerre": "Auxerre", "Paris FC": "Paris FC", "Paris": "Paris FC", "Stade Rennais FC 1901": "Rennes", "Strasbourg Alsace": "Strasbourg", "RC Strasbourg Alsace": "Strasbourg",
               "Racing Club de Lens": "Lens", "RC Lens": "Lens", "ES Troyes AC": "Troyes", "Le Havre AC": "Le Havre", "Angers SCO": "Angers", "Cagliari Calcio": "Cagliari", "Como 1907": "Como",
               "Frosinone Calcio": "Frosinone", "Genoa CFC": "Genoa", "Parma Calcio 1913": "Parma", "US Lecce": "Lecce", "US Sassuolo Calcio": "Sassuolo", "Udinese Calcio": "Udinese",
               "PAE Olympiakos SFP": "Olympiakos", "Le Mans FC": "Le Mans", "Hellas Verona FC": "Hellas Verona", "Juventus FC": "Juventus", "SS Lazio": "Lazio",
               "Club Atlético de Madrid": "Atlético Madrid", "Real Betis Balompié": "Real Betis", "Sport Lisboa e Benfica": "Benfica",
               "Sporting Clube de Portugal": "Sporting CP", "Paris Saint-Germain FC": "Paris Saint-Germain", "Brugge KV": "Club Brugge",
               "Club Brugge KV": "Club Brugge", "Royale Union Saint-Gilloise": "Union Saint-Gilloise", "FC Internazionale Milano": "Inter",
               "Internazionale Milano": "Inter", "SL Benfica": "Benfica", "SS Lazio": "Lazio", "Lazio Roma": "Lazio", "AS Roma": "Roma",
               "Olympique de Marseille": "Marseille", "Olympique Lyonnais": "Lyon", "Lille OSC": "Lille", "Stade Rennais FC": "Rennes",
               "FC Bayern München": "Bayern München", "FC Barcelona": "Barcelona", "Barcelona": "Barcelona", "Bayer 04 Leverkusen": "Bayer Leverkusen",
               "Borussia Mönchengladbach": "Gladbach", "TSG 1899 Hoffenheim": "Hoffenheim", "1. FC Köln": "1. FC Köln",
               "SV 07 Elversberg": "Elversberg", "1. FC Union Berlin": "Union Berlin", "Celta de Vigo": "Celta Vigo", "RC Celta de Vigo": "Celta Vigo",
               "Deportivo Alavés": "Alavés", "Espanyol de Barcelona": "Espanyol", "RCD Espanyol de Barcelona": "Espanyol", "Levante UD": "Levante",
               "Rayo Vallecano de Madrid": "Rayo Vallecano", "Real Racing Club de Santander": "Racing Santander", "Real Sociedad de Fútbol": "Real Sociedad",
               "Atalanta BC": "Atalanta", "Bologna FC 1909": "Bologna", "SSC Napoli": "Napoli", "Galatasaray SK": "Galatasaray",
               "PFC Ludogorets Razgrad": "Ludogorets", "Olympiakos Piraeus": "Olympiakos", "Qarabağ Ağdam FK": "Qarabağ", "ACF Fiorentina": "Fiorentina",
               "GNK Dinamo Zagreb": "Dinamo Zagreb", "FK Bodø/Glimt": "Bodø/Glimt", "Molde FK": "Molde", "BSC Young Boys": "Young Boys",
               "AC Sparta Praha": "Sparta Prag", "SK Slavia Praha": "Slavia Prag", "Viktoria Plzeň": "Viktoria Plzeň", "Viborg FF": "Viborg",
               "FC København": "København", "Stade Brestois 29": "Brest", "OGC Nice": "Nice", "AS Monaco": "Monaco", "RSC Anderlecht": "Anderlecht",
               "KAA Gent": "Gent", "FK Mladá Boleslav": "Mladá Boleslav", "IF Elfsborg": "Elfsborg", "Malmö FF": "Malmö", "FCSB": "FCSB",
               "PAOK Saloniki": "PAOK", "APOEL Nikosia": "APOEL", "Omonia Nikosia": "Omonia", "Crvena Zvezda": "Røde Stjerne Beograd",
               "Dinamo Kiev": "Dynamo Kyiv", "Dinamo Minsk": "Dinamo Minsk", "Ferencvárosi TC": "Ferencváros", "FK Astana": "Astana", "FK Kairat": "Kairat"}
    if raw in special:
        return special[raw]
    s = raw
    s = re.sub(r"^(FC|AFC|RC|RCD|CA|CD|UD|SD|SC|SV|VfL|VfB|FSV|1\.\s*FSV)\s+(?=\S)", "", s) if not s.startswith("1. FC") else s
    s = re.sub(r"\s+(FC|AFC|CF|SC|BK|IF)$", "", s)
    return s.strip()


# ---------- selectable set
sel = set()
season_teams = defaultdict(set)
for m in M:
    if m["comp"] in DOM:
        season_teams[(m["comp"], m["s"])].update([m["hid"], m["aid"]])
for _c in DOM:
    _cur = max(s for (c, s) in season_teams if c == _c)
    sel |= season_teams[(_c, _cur)]
EURO_S = max(m["s"] for m in M if m["comp"] == "CL")
euro_cnt = Counter()
for m in M:
    if m["comp"] in ("CL", "EL", "UECL") and m["s"] in (EURO_S - 1, EURO_S):
        euro_cnt[m["hid"]] += 1
        euro_cnt[m["aid"]] += 1
for t, n in euro_cnt.items():
    if n >= 6 and t.split(":")[0] not in BIG:
        sel.add(t)
sel = sorted(sel)
print("selectable teams:", len(sel), Counter(t.split(":")[0] for t in sel).most_common(12))

# ---------- replay for per-team histories
hist = defaultdict(list)  # team -> list of match records + post-rating
for m, p in zip(M, pre):
    rh, ra, E = p
    gd = m["hg"] - m["ag"]
    S = 1.0 if gd > 0 else (0.5 if gd == 0 else 0.0)
    K = Kd if m["comp"] in DOM else Ke
    d = K * G(gd) * (S - E)
    d_int = int(m["d"].replace("-", ""))
    hist[m["hid"]].append((d_int, m["comp"], 1 if not m["n"] else 2, m["aid"], m["hg"], m["ag"], rh, ra, rh + d))
    hist[m["aid"]].append((d_int, m["comp"], 0 if not m["n"] else 2, m["hid"], m["ag"], m["hg"], ra, rh, ra - d))

data_end = max(m["d"] for m in M if m["comp"] in DOM and m["hg"] is not None)
print("latest domestic match:", data_end)

idx = {}
tlist = []


def tix(t):
    if t not in idx:
        idx[t] = len(tlist)
        tr = teams[t]
        c = tr["country"]
        tlist.append(dict(id=t, name=disp(tr["raw"]), c=c, r=round(R[t]), sel=int(t in sel)))
    return idx[t]


for t in sel:
    tix(t)

NLAST = 60
out_teams = []
for t in sel:
    h = hist[t]
    last = h[-1][0]
    ms = []
    for (d, comp, venue, opp, gf, ga, rs, ro, post) in h[-NLAST:]:
        ms.append([d, COMPS.index(comp), venue, tix(opp), gf, ga, round(rs), round(ro)])
    # monthly rating series (post-match), from 2019-07 to data_end
    series = []
    y, mo = 2019, 7
    ei = 0
    cur = None
    ye, me = int(data_end[:4]), int(data_end[5:7])
    while (y, mo) <= (ye, me):
        limit = y * 10000 + mo * 100 + 31
        while ei < len(h) and h[ei][0] <= limit:
            cur = h[ei][8]
            ei += 1
        series.append(round(cur) if cur is not None else None)
        mo += 1
        if mo == 13:
            y, mo = y + 1, 1
    c = t.split(":")[0]
    tr = tlist[idx[t]]
    tr["lg"] = LEAGUE_NAME.get(c, COUNTRY_DK.get(c, c))
    tr["last"] = last
    tr["nall"] = len(h)
    out_teams.append(dict(i=idx[t], m=ms, s=series))

# ---------- H2H table (both teams selectable)
selset = set(sel)
h2h = []
for m in M:
    if m["hid"] in selset and m["aid"] in selset:
        h2h.append([int(m["d"].replace("-", "")), idx[m["hid"]], idx[m["aid"]], m["hg"], m["ag"], COMPS.index(m["comp"]), m["n"]])

# ---------- global constants
dom = [m for m in M if m["comp"] in DOM and m["d"] >= "2015-07-01"]
mu_h = sum(m["hg"] for m in dom) / len(dom)
mu_a = sum(m["ag"] for m in dom) / len(dom)
ref_ratings = [R[t] for t in sel if t.split(":")[0] in ("ENG", "GER", "ESP")]
r_ref = sum(ref_ratings) / len(ref_ratings)
lastdate = {c: max(m["d"] for m in M if m["comp"] == c) for c in ("ENG1", "GER1", "ESP1", "ITA1", "FRA1", "NED1", "POR1", "CL")}

pack = dict(
    comps=[COMP_LABEL[c] for c in COMPS],
    teams=tlist,
    prof=out_teams,
    h2h=h2h,
    model=dict(ah=P["ah"], aa=P["aa"], b=P["b"], rho=P["rho"], hfa=HFA, mu_h=mu_h, mu_a=mu_a, r_ref=r_ref, K_dom=Kd, K_eur=Ke),
    meta=dict(data_end=data_end, last=lastdate, backtest=bt, n_matches=len(M), built=__import__("datetime").date.today().isoformat(), series_start="2019-07"),
    offsets={c: round(v) for c, v in o["off"].items() if c in ("ENG", "GER", "ESP", "ITA", "FRA", "POR", "NED")},
)
json.dump(pack, open("data.json", "w"), ensure_ascii=False, separators=(",", ":"))
import os
print("data.json size KB:", os.path.getsize("data.json") // 1024, "| teams in table:", len(tlist), "| h2h rows:", len(h2h))
print("mu_h %.3f mu_a %.3f r_ref %.0f" % (mu_h, mu_a, r_ref))
print("\nDISPLAY NAMES:")
for lg in ("Premier League", "Bundesliga", "La Liga", "Serie A", "Ligue 1", "Eredivisie", "Primeira Liga"):
    print(lg, "->", sorted(t["name"] for t in tlist if t.get("lg") == lg))
others = sorted((t["lg"], t["name"]) for t in tlist if t["sel"] and t.get("lg") not in LEAGUE_NAME.values())
print("OTHERS:", others)
