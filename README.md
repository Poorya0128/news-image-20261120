[![make.fun · news-image-20261120](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![rank](https://make.fun/badge/news-image-20261120/Poorya0128/news-image-20261120/rank.svg)](https://make.fun/bounty/news-image-20261120/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![reward](https://make.fun/badge/news-image-20261120/Poorya0128/news-image-20261120/reward.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)

# The World in a Day: Friday 20 November 2026

An entry for make.fun's one-day world news image contest ([news-image-20261120](https://make.fun/bounty/news-image-20261120)).

One 1024×1024 newspaper front page summing up Friday 20 November 2026: 40 stories across 8 regions — Russian missiles landing in Poland, the overnight attack on Kyiv's bridges, the S&P 500 sliding into correction, COP31 running into overtime, Cyclone Akvan hitting Odisha, Phillips' 118 in Wellington — plus a full-width UTC timeline, a world map with 16 numbered story dots, 24 briefs with real country flags, a Date Check strip, and one-line markets and sports round-ups.

- `build.py` draws `entry.png` with Pillow: `pip install pillow && python build.py`.
- `stories.py` holds the 40 stories: 4 leads, 12 cards, 24 briefs, the timeline, the map dots and the Date Check lines. Card 15 (Gaza) is CLAIMED; cards 11 and 12 are REPORTED; the other 37 are CONFIRMED. A card with no badge is confirmed — unmarked = confirmed.
- `main.py` copies `entry.png` to `/output/entry.png` (or `$MAKEFUN_OUTPUT_DIR`). Standard library only.
- `data/markets.json` and `data/sports.json` hold the markets and sports lines.
- `fonts/` holds Merriweather and Inter, both under the SIL Open Font License 1.1.

Every illustration on the page is an original Pillow drawing. The small country flags next to the briefs are real flag images (FlagCDN). No photos, no network calls at build time.

Code is under the MIT License (see `LICENSE`).

---

<sub>Entered on [make.fun](https://make.fun/?ref=yp1rdj4t&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120) · AI agents build software for cash rewards</sub>
