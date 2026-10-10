#!/bin/bash
# Bygger siden fra friske data. Kræver python3, numpy, scipy og git.
set -e
export OF_ROOT="$PWD/data/openfootball"
mkdir -p "$OF_ROOT"
for r in england deutschland espana italy europe europe-champions-league; do
  rm -rf "$OF_ROOT/$r"
  git clone -q --depth 1 "https://github.com/openfootball/$r.git" "$OF_ROOT/$r"
done
python3 -I parse.py matches_raw.json | tail -25
python3 -I canon.py matches_raw.json matches_canon.json teams.json | grep -E "CHECK|all seasons ok|teams:"
python3 -I elo.py | tail -12
python3 -I build_data.py | grep -E "selectable|latest|data.json"
python3 -I make_page.py
python3 -I check.py
mkdir -p site
{ printf '<!doctype html>\n<html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">\n<meta name="description" content="Sammenlign to fodboldhold fra syv europæiske ligaer med Elo-justeret statistik og fair odds. Kun til information.">\n'; cat index.html; printf '\n</html>\n'; } > site/index.html
cp site/index.html elo-head-to-head.html
