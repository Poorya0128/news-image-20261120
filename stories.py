"""Story data for the Friday 20 November 2026 front page.

All display strings come from the design spec; the status, source and
region of every story come from stories.json. Thirty-nine stories: ids 1-4
are the leads, 5-16 the medium cards, and 23 briefs (ids 17-19, 21,
23, 25-29, 31, 33, 35, 36, 38-43, 47, 50, 51). Badges on
the 16 lead/card stories: 12 CONFIRMED, 3 REPORTED (8, 12, 13),
1 CLAIMED (15). Badges SHOWN (2026-11-21,
user-confirmed): CONFIRMED only on the 4 leads (1-4) — the 8 CONFIRMED
medium cards (5, 6, 7, 9, 10, 11, 14, 16) show no badge, and an unmarked
medium card reads as confirmed; REPORTED / CLAIMED badges on the
medium cards are unchanged.
"""

REGION_COLOURS = {
    "Europe": (43, 92, 168),
    "Middle East": (198, 110, 28),
    "North America": (26, 110, 74),
    "Latin America": (176, 58, 46),
    "Asia": (123, 75, 166),
    "Africa": (14, 124, 123),
    "Global": (90, 90, 90),
}

# Each lead: id, region, kicker, headline, dek, source, status.
# LEAD ORDER (2026-11-21, round 5, user order): Poland returns to
# lead 1 as CONFIRMED (second source confirmed: AP, ISW and The
# Times all report two Russian missiles landed in Poland Fri 20 Nov;
# Tusk called it a deliberate provocation). Kyiv is lead 2, Cyclone
# Akvan is lead 3, S&P stays 4. COP31 is demoted to card 5. The ids
# ARE the display numbers (number circles and map dots), so they are
# renumbered with the order.
LEADS = [
    {
        "id": 1,
        "region": "Europe",
        "kicker": "EUROPE · POLAND",
        # ROUND 5 (2026-11-21): Poland is CONFIRMED, not REPORTED —
        # AP, ISW and The Times independently confirm two Russian
        # missiles landed in eastern Poland Fri 20 Nov, and Tusk
        # called it a deliberate/intentional provocation. Definitive
        # headline again ("Russian missiles hit Poland"), source
        # "AP · ISW".
        "headline": "Russian missiles hit Poland",
        "dek": "Two missiles fell in the east; Tusk: deliberate "
               "provocation.",
        "source": "AP · ISW",
        "status": "CONFIRMED",
    },
    {
        "id": 2,
        "region": "Europe",
        "kicker": "EUROPE · UKRAINE WAR",
        "headline": "Russia hits Kyiv bridges in overnight attack",
        # P5 (2026-11-21): precise figures — 111 missiles (84 cruise
        # + 27 ballistic) and 404 drones, at least nine killed,
        # three bridges hit, power and water cut. Two sources.
        # FIT (2026-11-21): the "(Kyiv Independent, BBC)" tail was
        # dropped — the source credit already shows both names, and
        # the full dek truncated at 11px. Facts unchanged.
        # ROUND 5 (2026-11-21): source is now "Kyiv Independent ·
        # CNN" so the 9-killed figure is properly cited (CNN
        # confirms 9; early reports said 8).
        "dek": "111 missiles and 404 drones; at least nine killed, "
               "three bridges hit; power and water cut.",
        "source": "Kyiv Independent · CNN",
        "status": "CONFIRMED",
    },
    {
        "id": 3,
        "region": "Asia",
        "kicker": "ASIA · CYCLONE",
        # ROUND 5 (2026-11-21): kicker was "ODISHA · INDIA ·
        # CYCLONE" — now "ASIA · CYCLONE" to match the other
        # leads' "region · topic" pattern. Same headline/dek/facts
        # as before (landfall near Gopalpur from 8 am, winds
        # 70–80 km/h, no deaths reported; 300,000+ to shelters —
        # precise: 370,000 evacuated per Odisha Chief Secretary).
        "headline": "Cyclone Akvan hits coast; 300,000+ to shelters",
        "dek": "Landfall near Gopalpur ~8 am; 70–80 km/h; no deaths "
               "reported.",
        "source": "IMD · PTI",
        "status": "CONFIRMED",
    },
    {
        "id": 4,
        "region": "North America",
        "kicker": "N. AMERICA · MARKETS",
        "headline": "S&P 500 slides into correction as AI stocks fall",
        # ROUND 5 (2026-11-21): FRIDAY 20 Nov numbers (user order) —
        # S&P 500 closed 6,910.39, down 3.70%, entering correction
        # (off 11.62% from its record close); Nasdaq down 5.28%.
        # "Wiping out 2026 gains" is DROPPED: the S&P was still up
        # 0.95% year-to-date at the Friday close (Morningstar/Dow
        # Jones Market Data) — it was the NASDAQ that wiped out its
        # 2026 gains (now -2.7% YTD).
        "dek": "AI sell-off: S&P down 3.7% to 6,910, Nasdaq down 5.3%.",
        "source": "Reuters",
        "status": "CONFIRMED",
    },
]

# Each card: id, region, kicker, headline, dek, source, status.
# CARD LINEUP (2026-11-21, round 5, user order): 5 COP31 (demoted
# from lead 4), 6 UK-EU, 7 UN chief, 8 Iran war, 9 Hodeidah,
# 10 Peru quake, 11 Palisades, 12 Pill, 13 Nvidia, 14 Iraq
# (promoted from brief 37), 15 Gaza, 16 Gen Z. The cricket card
# is gone — Phillips 118 vs India moves to the SPORT line.
CARDS = [
    {
        "id": 5, "region": "Global", "kicker": "GLOBAL · CLIMATE",
        # ROUND 7 (2026-11-22, user order): dek DELETED — the headline
        # alone must carry the meaning: "draft drops fossil-fuel
        # phase-out" absorbs the dek's "phase-out text".
        "headline": "COP31 overtime; phase-out dropped",
        "dek": "Draft deal drops all fossil-fuel phase-out text.",
        "source": "AP", "status": "CONFIRMED",
    },
    {
        "id": 6, "region": "Europe", "kicker": "EUROPE · DIPLOMACY",
        # ROUND 7 (2026-11-22): dek DELETED — headline absorbs it:
        # the deals cover food, carbon and youth.
        "headline": "UK–EU deals on food, carbon, youth",
        "dek": "Food exports, carbon markets, youth scheme for 18–31s.",
        "source": "BBC", "status": "CONFIRMED",
    },
    {
        "id": 7, "region": "Global", "kicker": "GLOBAL · UNITED NATIONS",
        # ROUND 7 (2026-11-22): dek DELETED — headline absorbs it:
        # the ninth vote ended in a veto deadlock.
        "headline": "UN chief race deadlocked by veto",
        "dek": "Ninth poll leaves every candidate blocked by a veto.",
        # Second source (2026-11-21): Apex Wire independently reported
        # the same ninth-poll deadlock (Grynspan 10/4/1, veto blocks) —
        # so this is genuinely two-source confirmed, not single-source.
        "source": "PassBlue · Apex Wire", "status": "CONFIRMED",
    },
    {
        "id": 8, "region": "Middle East", "kicker": "MIDDLE EAST · IRAN WAR",
        # ROUND 7 (2026-11-22): dek DELETED — headline absorbs it.
        # ROUND 7e (2026-11-22, user order): "delays" attributed
        # the decision to Trump; CBS says "no decision until
        # 2027", so the headline quotes that, Trump as source.
        "headline": "No Iran decision until 2027, Trump says",
        "dek": "Trump: no decision on next Iran step until 2027.",
        "source": "CBS News", "status": "REPORTED",
    },
    {
        "id": 9, "region": "Middle East", "kicker": "MIDDLE EAST · YEMEN",
        # ROUND 7 (2026-11-22): dek DELETED — headline absorbs it.
        # ROUND 7e (2026-11-22, user order): the old headline lost
        # the subject — the Saudi-led coalition did the hitting.
        "headline": "Saudi-led coalition hits Hodeidah port",
        "dek": "Port hit after five Houthi drones were intercepted.",
        # Second source (2026-11-21): Reuters independently reported
        # the Hodeidah strike + five drones/one missile intercepted —
        # so this is genuinely two-source confirmed, not single-source.
        "source": "Arab News · Reuters", "status": "CONFIRMED",
    },
    {
        "id": 10, "region": "Latin America",
        "kicker": "LATIN AMERICA · QUAKE",
        # ROUND 7 (2026-11-22): dek DELETED — headline absorbs it:
        # Lima was shaken, no tsunami.
        "headline": "6.7 quake hits Peru, shakes Lima",
        "dek": "Quake near Cerro de Pasco shook Lima; no tsunami.",
        "source": "USGS", "status": "CONFIRMED",
    },
    {
        "id": 11, "region": "North America", "kicker": "N. AMERICA · WILDFIRE",
        # ROUND 7 (2026-11-22): dek DELETED — headline absorbs it:
        # arson conviction, 12 killed.
        "headline": "Arson conviction in Palisades Fire, 12 dead",
        "dek": "Guilty of arson in the fire that killed 12 people.",
        "source": "AP", "status": "CONFIRMED",
    },
    {
        "id": 12, "region": "Global", "kicker": "GLOBAL · HEALTH",
        # ROUND 7 (2026-11-22): dek DELETED — headline absorbs it:
        # the 60.7% response figure is now in the headline.
        # ROUND 7e (2026-11-22, user order): "early trial" added —
        # the green check in the art reads as a certain cure, so
        # the headline must carry the early-trial hedge.
        "headline": "Pancreatic pill: 60.7% respond in early trial",
        "dek": "Daraxonrasib + chemo: 60.7% of 61 responded in an "
               "early trial.",
        "source": "The Guardian", "status": "REPORTED",
    },
    {
        "id": 13, "region": "North America", "kicker": "N. AMERICA · TECH",
        # ROUND 5 (2026-11-21): FRIDAY 20 Nov numbers (user order) —
        # Nvidia closed down 14.01% on Friday (KuCoin/CNBC). The
        # headline's cause is now neutral: "on" -> "amid"
        # ("Nvidia sinks 14% amid SEC probe and AI-tax threat").
        # Art "-14%" unchanged.
        # ROUND 7 (2026-11-22): dek DELETED — headline absorbs it:
        # SEC probes Nvidia's accounts; Trump eyes an AI tax.
        "headline": "Nvidia sinks 14% on SEC probe, AI tax",
        "dek": "SEC probing Nvidia accounts; Trump threatens "
               "AI-centre tax.",
        "source": "Reuters · BBC", "status": "REPORTED",
    },
    {
        "id": 14, "region": "Middle East", "kicker": "MIDDLE EAST · IRAQ",
        # ROUND 5 (2026-11-21): promoted from brief 37 — the Iraq
        # story (govt forces entered Jurf al-Nasr, Kataeb Hezbollah
        # stronghold in Babil, Fri 20 Nov morning, no resistance,
        # handover ~14:00 Baghdad time) is a card now; the cricket
        # card it replaces moves to the SPORT line. New card art:
        # Iraq map + red star + tricolour flag.
        # ROUND 7 (2026-11-22): dek DELETED — headline absorbs it:
        # place, group and no resistance all in the headline.
        "headline": "Iraq enters Jurf al-Nasr unopposed",
        "dek": "Forces enter Kataeb Hezbollah stronghold; no "
               "resistance.",
        "source": "AFP", "status": "CONFIRMED",
    },
    {
        "id": 15, "region": "Middle East", "kicker": "MIDDLE EAST · GAZA",
        # ROUND 7 (2026-11-22): dek DELETED — headline absorbs it:
        # troops crossed the Yellow Line.
        "headline": "Gaza strikes kill six; troops cross line",
        "dek": "Six killed as troops cross the Yellow Line near Nuseirat.",
        "source": "Al Jazeera", "status": "CLAIMED",
    },
    {
        "id": 16, "region": "Europe", "kicker": "EUROPE · PROTESTS",
        # ROUND 7 (2026-11-22): dek DELETED — headline absorbs it:
        # the cause is costs and spending.
        "headline": "Gen Z protests 25 countries over costs",
        "dek": "Students march in 25 countries over costs and spending.",
        "source": "BBC", "status": "CONFIRMED",
    },
]

# Each brief: id, region, flag code (see build.py draw_flag), text.
# Flag codes are ISO country codes. ("GTA" and "CLAIM" were drawn
# chips; briefs 51/52 now fly real flags — US for GTA VI, set in
# Leonida, Rockstar's Florida ("Vice City, USA"); DE for Riemann,
# the German mathematician behind the 1859 hypothesis.)
# ROUND 5 (2026-11-21): brief 37 (Iraq) is DELETED — it is a card
# now (card 14). 23 briefs remain.
BRIEFS = [
    (17, "Europe", "DE", "Lufthansa to cut 1,000 jobs"),
    (18, "Europe", "DK", "Denmark expels Russian diplomat"),
    (19, "Europe", "EE", "Estonia to shut Russia crossings"),
    (21, "Europe", "FR", "France probes Depardieu, Houellebecq"),
    (23, "Asia", "PH", "Marcos: P41.1bn in APEC pledges"),
    (25, "Asia", "JP", "Japan–China ties at record low"),
    (26, "Asia", "JP", "Japan core inflation at year high"),
    (27, "Asia", "SA", "Saudi, Japan agree oil deal"),
    (28, "Asia", "IN", "India's bullet train from late 2027"),
    (29, "Asia", "NP", "Nepal PM to visit India first time"),
    (31, "North America", "US", "Mamdani to close Rikers by 2032"),
    (33, "North America", "US", "Gupta gets 19½ years in NY plot"),
    (35, "North America", "US", "Trump: more work on Canada deal"),
    (36, "Middle East", "IR", "Qeshm blast blamed on munitions"),
    (38, "Middle East", "US", "Trump: Iran wants a deal"),
    (39, "Middle East", "US", "US sanctions four Iranians"),
    (40, "Africa", "NG", "Nigeria boat capsizes; 4 dead"),
    (41, "Africa", "KE", "Kenya drills first commercial oil"),
    (42, "Africa", "ZA", "South Africa: murders fall by 1,600"),
    (43, "Africa", "EG", "Egypt tribes hand over rifles"),
    (47, "Latin America", "MX", "New migrant caravan enters Mexico"),
    (50, "Latin America", "VE", "Venezuela rejects ICJ on Esequibo"),
    (51, "Global", "US", "GTA VI: $3.79bn day one, a record"),
]

# Brief sources: the source of every brief, verbatim from stories.json.
# The brief list shows a compact source LABEL at the END of each row,
# right-aligned at the row end (the map's numbered dots 1-16 are
# unaffected):
#   label = the source upper-cased, shortened only where the full
#   name cannot fit the label slot (see build.py draw_briefs):
#   Reuters -> RTRS (full REUTERS, 32.3px at 7px, would truncate
#   briefs 47 and 51, whose texts leave only ~3.5px spare);
#   Bloomberg Law -> BLOOM (full BLOOMBERG, 44.7px, would truncate
#   brief 34, 16px spare); Daily Jagran -> JAGRAN, Zee News -> ZEE,
#   Deccan Herald -> DECCAN, Capital FM -> CAPITAL, Footy Ghana ->
#   FOOTY, The Guardian -> GUARDIAN, Buenos Aires Times -> BA TIMES,
#   CANA News -> CANA. All other sources fit whole.
BRIEF_SOURCE_LABEL = {
    17: "SKIFT", 18: "BBC", 19: "EURONEWS", 21: "BBC",
    23: "MALAYA", 25: "JAPAN TIMES",
    26: "CNBC", 27: "JAPAN TIMES", 28: "DECCAN", 29: "BBC",
    31: "RTRS", 33: "RTRS",
    35: "RTRS", 36: "RTRS", 38: "RTRS",
    39: "RTRS", 40: "AL JAZEERA", 41: "CAPITAL", 42: "ENCA",
    43: "ELZATOUNA",
    47: "RTRS", 50: "CANA",
    51: "RTRS",
}

# Timeline events: (time, x, short label, above_line, anchor, region).
# anchor: how the single-line label sits relative to its dot — "center"
# (centred on the dot, no leader), "left" (label starts 6px right of the
# dot, vertical leader stem at the dot), "right" (label ends 6px left of
# the dot, stem at the dot). The displaced labels are the ones whose
# centred span would collide with a neighbour (00:30 vs the "THE DAY"
# title; 11:00 vs 14:00, whose left-anchored label starts at its dot). Times and labels are
# the exact facts from stories.json; only the placement is designed.
# Region is verified against stories.json (and the story it belongs to):
# Kyiv/Poland are Europe (leads 2/1), Iraq is Middle East
# (card 14), COP31 is Global (card 5), S&P is North America
# (lead 4). The timeline dots, stems, rules and times are drawn
# in the event's region colour (REGION_COLOURS above).
# TIMELINE-ONLY CUT (2026-11-21): 5 events, down from 7 — the
# 11:30 UK-EU deals and 20:00 Palisades verdict markers were
# dropped (weakest news weight; each decluttered the tightest
# pair on the ruler). Their stories STAY in the paper unchanged.
TIMELINE = [
    ("00:30", 107, "Kyiv bridges hit", True, "left", "Europe"),
    ("02:30", 184, "Missiles land in Poland", False, "center", "Europe"),
    ("11:00", 512, "Iraq enters Jurf al-Nasr", True, "right", "Middle East"),
    ("14:00", 627, "COP31 into overtime", True, "left", "Global"),
    ("21:00", 897, "S&P slides into correction", True, "center", "North America"),
]

# Map dots: (story id, region, longitude, latitude) of the story's
# true place. The map in build.py projects these onto real Natural
# Earth coastlines (data/world.json) and lays the numbered dots out
# with a spring force (each dot pulled to its anchor, pushed apart
# from any dot closer than 13.5px) — no leader lines, no anchor dots:
# every dot sits on, or the minimum nudge from, its true place.
# Anchors (ROUND 5, 2026-11-21 — renumbered with the stories):
#   1 eastern Poland (Lublin area) · 2 Kyiv · 3 Odisha (Akvan
#   landfall) · 4 New York (NYSE) · 5 Antalya (COP31) · 6 Brussels ·
#   7 New York (UN HQ) · 8 Tehran · 9 Hodeidah, Yemen · 10 Cerro de
#   Pasco, Peru · 11 Los Angeles · 12 London (Guardian report; the
#   trial story names no place) · 13 Santa Clara, California
#   (Nvidia HQ) · 14 Jurf al-Nasr, Iraq · 15 Gaza · 16 Berlin.
MAP_ANCHORS = [
    (1, "Europe", 23.0, 51.5),
    (2, "Europe", 30.5, 50.45),
    (3, "Asia", 85.0, 19.3),
    (4, "North America", -74.0, 40.7),
    (5, "Global", 30.7, 36.9),
    (6, "Europe", 4.35, 50.85),
    (7, "Global", -74.0, 40.7),
    (8, "Middle East", 51.4, 35.7),
    (9, "Middle East", 42.8, 14.8),
    (10, "Latin America", -76.25, -10.7),
    (11, "North America", -118.25, 34.05),
    (12, "Global", -0.1, 51.5),
    (13, "North America", -121.9, 37.4),
    (14, "Middle East", 44.2, 32.9),
    (15, "Middle East", 34.45, 31.5),
    (16, "Europe", 13.4, 52.5),
]

# ROUND 5 (2026-11-21): the brief dots are REMOVED from the map
# (review item 9) — only the 16 numbered dots remain, so
# BRIEF_ANCHORS is deleted entirely (it was used only by draw_map's
# brief-dot layout/drawing).

DATE_CHECK_LINES = [
    # EXPANDED 2026-11-21 (user order): LEFT OUT 7 items, NOT YET
    # 3 items — the 5 added items are all verified real (parent
    # verified by live news search): Anthropic's $83 IPO debut
    # (first Nasdaq trading Thu 19 Nov), Tonga's drought emergency
    # (27-day state of emergency Thu 19 Nov), the migrant boat lost
    # off Senegal (incident overnight Tue->Wed 17-18 Nov, reported
    # Thu 19 Nov — ROUND 5: the row date is Wed 18 Nov, the day
    # of the sinking, not Thu 19 Nov), the Senate Iran war-powers
    # vote (rejected Thu 19 Nov — NO vote tally: sources report it
    # as both 48-51 and 51-48), and the COP31 final text (due Sat
    # 21 Nov; the summit ran overtime).
    # EDGE stays DELETED (it named "Sat 21 Nov" for the Peru quake,
    # which contradicted the paper's Friday date; the card now
    # carries "FRI 19:09 LOCAL" instead).
    "LEFT OUT: Myanmar genocide ruling, Thu 19 Nov · Trump–Xi–Putin summit, "
    "Thu 19 Nov · Voyager 1 light-day, Wed 18 Nov · Anthropic's $83 IPO "
    "debut, Thu 19 Nov · Tonga's drought emergency, Thu 19 Nov · Migrant "
    "boat lost off Senegal, Wed 18 Nov · Senate Iran war-powers vote, "
    "Thu 19 Nov",
    "NOT YET: BepiColombo enters Mercury orbit, Sat 21 Nov · NATO chief Rutte "
    "due in Warsaw, Sat 21 Nov · COP31 final text, Sat 21 Nov",
]

# (text, is_red) segments for the markets line.
# ROUND 5 (2026-11-21): FRIDAY 20 Nov closes (user order), verified
# by live search — S&P 500 6,910.39 -3.70%, Nasdaq 22,617.73 -5.28%,
# Nikkei 56,436.65 -5.06%, Brent $92.57/bbl (settled +0.64%; the old
# $89.87 was wrong for Friday), Gold -4% (Dec futures -3.98% to
# $3,539/oz), Bitcoin -4.5% (to just below $58,200; the old -4.15%
# was understated for Friday).
MARKETS_SEGMENTS = [
    ("S&P 500 6,910 ", False), ("-3.7%", True), ("  ·  Nasdaq ", False),
    ("-5.3%", True), ("  ·  Nikkei ", False), ("-5.06%", True),
    ("  ·  Brent $92.57  ·  Gold ", False), ("-4%", True),
    ("  ·  Bitcoin ", False), ("-4.9%", True),
]

# ROUND 5 (2026-11-21): cricket moves here as a 5th SPORT item —
# "Phillips 118 vs India" (the card is gone; Iraq took its slot).
# Harden's item is shortened (", Cavs 128–119 Pacers" -> ", Cavs win")
# so all 5 items still fit in 4 lines at 12.5px.
# ROUND 7f (2026-11-22, user order): "Phillips 118 vs India" is
# ambiguous — say whose Phillips and what he did: NZ's Phillips
# hits 118 vs India.
SPORTS_TEXT = (
    "Alcaraz beats Cobolli at ATP Finals  ·  A Lim Kim aces 16th, leads "
    "LPGA finale  ·  Price undisputed welterweight champion  ·  Harden's "
    "50th 50-pt game, Cavs win  ·  NZ's Phillips hits 118 vs India"
)

# ROUND 5 (2026-11-21): footer rewritten — "Times are UTC; local date
# counts; market figures are closing values." added (review items 3
# and 11: the Peru quake's local date counts, and market figures are
# closing values). "Original drawings." dropped and the opening
# shortened to "Friday 20 November 2026." so the line still fits the
# 1000px content width at 9.5px on ONE line (measured 990.5px).
# ROUND 7f (2026-11-22, user order): "closing values" is wrong for
# Bitcoin, which trades 24 h — the market figures are day changes,
# Bitcoin's a 24 h one. New line measures 960.5px at 9.5px, still
# one line.
FOOTER_TEXT = (
    "Friday 20 November 2026. CLAIMED = one side's account. REPORTED = "
    "as stated. Unmarked = confirmed. Times are UTC; local date counts; "
    "market figures are day changes (Bitcoin: 24 h). Sources: Reuters, AP, BBC, AFP, "
    "Al Jazeera."
)
