# Elo Head-to-Head

Fodbold-sammenligner på tværs af ligaer (Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Eredivisie, Primeira Liga) med Elo-justeret statistik, modelforudsigelse og fair odds. Fire sprog: dansk, engelsk, spansk, tysk.

Kun til information. Ikke spilråd. 18+. Se ansvarsfraskrivelsen på siden.

## Sådan virker opdateringen
GitHub kører `opdater.yml` hver mandag. Den henter nye kampe fra [openfootball](https://github.com/openfootball) (public domain), kører modellen, kontrollerer resultatet (`check.py`) og udgiver siden på GitHub Pages. Fejler kontrollen, udgives intet, og GitHub sender dig en mail.

## Opsætning (én gang)
1. Opret en gratis konto på github.com.
2. Opret et nyt **offentligt** repository (fx `fodbold-elo`).
3. Upload alle filerne fra denne mappe. Mappen `.github/workflows/opdater.yml` er skjult i Stifinder: slå "Skjulte filer" til, eller opret filen på GitHub med *Add file → Create new file*, skriv stien `.github/workflows/opdater.yml` og indsæt indholdet.
4. Gå til *Settings → Pages* og vælg **Source: GitHub Actions**.
5. Gå til *Actions → Opdater siden → Run workflow*. Efter få minutter ligger siden på `https://BRUGERNAVN.github.io/REPONAVN/`.
6. Eget domæne senere: *Settings → Pages → Custom domain*.

## Filer
`parse.py` → `canon.py` → `elo.py` → `build_data.py` → `make_page.py` → `check.py`, samlet i `update.sh`. `template.html` er selve siden.
