"""Story data for the Friday 20 November 2026 front page.

All display strings come from the design spec; the status, source and
region of every story come from stories.json. Forty-six stories: ids 1-4
are the leads, 5-16 the medium cards, and 30 briefs (ids 17-19, 21,
23, 25-29, 31-44, 47-52). Badges on
the 16 lead/card stories: 11 CONFIRMED, 4 REPORTED (7, 11, 12, 14),
1 CLAIMED (15); brief 52 is also CLAIMED. Badges SHOWN (2026-11-21,
user-confirmed): CONFIRMED only on the 4 leads (1-4) — the 7 CONFIRMED
medium cards (5, 6, 8, 9, 10, 13, 16) show no badge, and an unmarked
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
    # Oceania (2026-11-21, P3): deep magenta — distinct from Latin
    # America red (pinker) and Asia purple (redder). First use:
    # card 13, Phillips in Wellington.
    "Oceania": (190, 45, 115),
}

# Each lead: id, region, kicker, headline, dek, source, status.
# LEAD ORDER (2026-11-21, user order): Kyiv is lead 1, Cyclone
# Akvan (promoted from card 14) is lead 2, S&P stays 3, COP31
# stays 4. Poland moves to card 14 (see CARDS) reframed as
# "Poland says". The ids ARE the display numbers (number circles
# and map dots), so they are renumbered with the order.
LEADS = [
    {
        "id": 1,
        "region": "Europe",
        "kicker": "EUROPE · UKRAINE WAR",
        "headline": "Russia hits Kyiv bridges in overnight attack",
        # P5 (2026-11-21): precise figures — 111 missiles (84 cruise
        # + 27 ballistic) and 404 drones, at least nine killed,
        # three bridges hit, power and water cut. Two sources.
        # FIT (2026-11-21): the "(Kyiv Independent, BBC)" tail was
        # dropped — the source credit already shows both names, and
        # the full dek truncated at 11px. Facts unchanged.
        "dek": "111 missiles and 404 drones; at least nine killed, "
               "three bridges hit; power and water cut.",
        "source": "Kyiv Independent · BBC",
        "status": "CONFIRMED",
    },
    {
        "id": 2,
        "region": "Asia",
        "kicker": "ODISHA · INDIA · CYCLONE",
        # P1 (2026-11-21): promoted from card 14 — the day's biggest
        # natural disaster (300,000+ moved to shelters) is now a
        # lead. Same headline/dek/facts as the card (landfall near
        # Gopalpur from 8 am, winds 70–80 km/h, no deaths reported).
        "headline": "Cyclone Akvan hits coast; 300,000+ to shelters",
        "dek": "Landfall near Gopalpur ~8 am; 70–80 km/h; no deaths "
               "reported.",
        "source": "IMD · PTI",
        "status": "CONFIRMED",
    },
    {
        "id": 3,
        "region": "North America",
        "kicker": "N. AMERICA · MARKETS",
        "headline": "S&P 500 slides into correction as AI stocks fall",
        "dek": "AI sell-off: S&P down 3.7% to 6,910, Nasdaq down 5.3%, "
               "wiping out 2026 gains.",
        "source": "Reuters",
        "status": "CONFIRMED",
    },
    {
        "id": 4,
        "region": "Global",
        "kicker": "GLOBAL · CLIMATE",
        "headline": "COP31 into overtime as draft drops fossil fuels",
        "dek": "Summit runs past its deadline as a draft deal drops all "
               "fossil-fuel phase-out text.",
        "source": "AP",
        "status": "CONFIRMED",
    },
]

# Each card: id, region, kicker, headline, dek, source, status.
CARDS = [
    {
        "id": 5, "region": "Europe", "kicker": "EUROPE · DIPLOMACY",
        "headline": "UK and EU sign post-Brexit deals",
        "dek": "Food exports, carbon markets, youth scheme for 18–31s.",
        "source": "BBC", "status": "CONFIRMED",
    },
    {
        "id": 6, "region": "Global", "kicker": "GLOBAL · UNITED NATIONS",
        "headline": "UN chief race stalls after ninth vote",
        "dek": "Ninth poll leaves every candidate blocked by a veto.",
        # Second source (2026-11-21): Apex Wire independently reported
        # the same ninth-poll deadlock (Grynspan 10/4/1, veto blocks) —
        # so this is genuinely two-source confirmed, not single-source.
        "source": "PassBlue · Apex Wire", "status": "CONFIRMED",
    },
    {
        "id": 7, "region": "Middle East", "kicker": "MIDDLE EAST · IRAN WAR",
        "headline": "Iran war nears ninth month; Trump in no rush",
        "dek": "Trump: no decision on next Iran step until 2027.",
        "source": "CBS News", "status": "REPORTED",
    },
    {
        "id": 8, "region": "Middle East", "kicker": "MIDDLE EAST · YEMEN",
        "headline": "Saudi coalition strikes Hodeidah port",
        "dek": "Port hit after five Houthi drones were intercepted.",
        # Second source (2026-11-21): Reuters independently reported
        # the Hodeidah strike + five drones/one missile intercepted —
        # so this is genuinely two-source confirmed, not single-source.
        "source": "Arab News · Reuters", "status": "CONFIRMED",
    },
    {
        "id": 9, "region": "Latin America",
        "kicker": "LATIN AMERICA · QUAKE",
        "headline": "Magnitude 6.7 earthquake hits central Peru",
        "dek": "Quake near Cerro de Pasco shook Lima; no tsunami.",
        "source": "USGS", "status": "CONFIRMED",
    },
    {
        "id": 10, "region": "North America", "kicker": "N. AMERICA · WILDFIRE",
        "headline": "Jury convicts man over deadly Palisades Fire",
        "dek": "Guilty of arson in the fire that killed 12 people.",
        "source": "AP", "status": "CONFIRMED",
    },
    {
        "id": 11, "region": "Global", "kicker": "GLOBAL · HEALTH",
        "headline": "Pill shows promise against pancreatic cancer",
        # P4 (2026-11-21): "nearly all" was hype — the trial's
        # objective response rate is 60.7% of 61 patients. Precise
        # figure replaces the exaggeration (rivals quote 60.7%).
        # FIT (2026-11-21): "(Guardian)" dropped — the source credit
        # already shows The Guardian, and the full dek truncated.
        "dek": "Daraxonrasib + chemo: 60.7% of 61 responded in an "
               "early trial.",
        "source": "The Guardian", "status": "REPORTED",
    },
    {
        "id": 12, "region": "North America", "kicker": "N. AMERICA · TECH",
        # P2 (2026-11-21): merged card — the old 12 (AI-tax threat)
        # and 13 (Nvidia down 14%) were the same Nvidia/AI story
        # twice. One card now carries both angles; the freed slot
        # becomes the Oceania card (13, Phillips).
        # FIT (2026-11-21): headline tightened ("as SEC probe report
        # and AI-tax threat land" -> "on SEC probe and AI-tax
        # threat") and dek tightened ("Reuters says SEC staff
        # examining accounting; Trump threatens tax on overseas AI
        # centres (Reuters, BBC)" -> "SEC probing Nvidia accounts;
        # Trump threatens AI-centre tax") — the as-proposed texts
        # overflowed to 4 headline lines and truncated the dek.
        # Facts unchanged; sources in the credit line.
        "headline": "Nvidia sinks 14% on SEC probe and AI-tax threat",
        "dek": "SEC probing Nvidia accounts; Trump threatens "
               "AI-centre tax.",
        "source": "Reuters · BBC", "status": "REPORTED",
    },
    {
        "id": 13, "region": "Oceania", "kicker": "WELLINGTON · CRICKET",
        # P3 (2026-11-21): Oceania — the 8th region, previously
        # zero. Fills the slot freed by merging 12+13. Phillips
        # 118 off 216 balls in Wellington completes centuries in
        # Tests, ODIs and T20Is vs India in 2026 — first NZ player
        # to do it in a calendar year (ICC).
        # FIX (2026-11-21, user order): the headline MUST carry
        # "vs India" before the record claim — "first NZ century in
        # all formats" alone is false (Williamson and others have
        # centuries in all three formats generally); the record is
        # centuries in all three formats AGAINST INDIA. Headline is
        # now just "Phillips hits 118 vs India" (2 lines) and the
        # dek carries the full record claim.
        "headline": "Phillips hits 118 vs India",
        "dek": "First NZ batter with centuries in all three formats "
               "against India.",
        "source": "ICC", "status": "CONFIRMED",
    },
    {
        "id": 14, "region": "Europe", "kicker": "EUROPE · POLAND",
        # LEAD REORDER (2026-11-21, user order): Poland moves here
        # from lead 1 into Akvan's old slot. The claim is now
        # ATTRIBUTED — headline "Poland says", dek read as Poland's
        # claim — so it is not stated as an un-attributed fact, and
        # the status is REPORTED (as stated) rather than CONFIRMED.
        # Facts unchanged: two missiles fell in eastern Poland,
        # Tusk calls it a deliberate provocation. FIT: the dek is
        # shortened to fit 2 lines at 10.5px ("in the east" =
        # eastern Poland; the art shows the eastern border).
        "headline": "Poland says Russian missiles hit its soil",
        "dek": "Two missiles fell in the east; Tusk: deliberate "
               "provocation.",
        "source": "BBC", "status": "REPORTED",
    },
    {
        "id": 15, "region": "Middle East", "kicker": "MIDDLE EAST · GAZA",
        "headline": "Israeli strikes kill six in Gaza; truce frays",
        "dek": "Six killed as troops cross the Yellow Line near Nuseirat.",
        "source": "Al Jazeera", "status": "CLAIMED",
    },
    {
        "id": 16, "region": "Europe", "kicker": "EUROPE · PROTESTS",
        "headline": "Gen Z protests sweep 25 European countries",
        "dek": "Students march in 25 countries over costs and spending.",
        "source": "BBC", "status": "CONFIRMED",
    },
]

# Each brief: id, region, flag code (see build.py draw_flag), text.
# Flag codes are ISO country codes. ("GTA" and "CLAIM" were drawn
# chips; briefs 51/52 now fly real flags — US for GTA VI, set in
# Leonida, Rockstar's Florida ("Vice City, USA"); DE for Riemann,
# the German mathematician behind the 1859 hypothesis.)
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
    (37, "Middle East", "IQ", "Iraq enters Jurf al-Nasr"),
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
    35: "RTRS", 36: "RTRS", 37: "AL JAZEERA", 38: "RTRS",
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
# Kyiv/Poland are Europe (stories 2/1), Iraq is Middle East
# (brief 37), COP31 is Global (story 4), S&P is North America
# (story 3). The timeline dots, stems, rules and times are drawn
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
# Anchors:
#   1 eastern Poland (Lublin area) · 2 Kyiv · 3 New York (NYSE) ·
#   4 Antalya (COP31) · 5 Brussels · 6 New York (UN HQ) · 7 Tehran ·
#   8 Hodeidah, Yemen · 9 Cerro de Pasco, Peru · 10 Los Angeles ·
#   11 London (Guardian report; the trial story names no place) ·
#   12 Washington DC · 13 Santa Clara, California (Nvidia HQ) ·
#   14 Manila · 15 Gaza · 16 Berlin.
MAP_ANCHORS = [
    # LEAD REORDER (2026-11-21): ids renumbered with the stories —
    # 1 Kyiv (30.5, 50.45), 2 Odisha (85.0, 19.3), 14 Poland
    # (23.0, 51.5). All other anchors unchanged.
    (1, "Europe", 30.5, 50.45),
    (2, "Asia", 85.0, 19.3),
    (3, "North America", -74.0, 40.7),
    (4, "Global", 30.7, 36.9),
    (5, "Europe", 4.35, 50.85),
    (6, "Global", -74.0, 40.7),
    (7, "Middle East", 51.4, 35.7),
    (8, "Middle East", 42.8, 14.8),
    (9, "Latin America", -76.25, -10.7),
    (10, "North America", -118.25, 34.05),
    (11, "Global", -0.1, 51.5),
    (12, "North America", -121.9, 37.4),
    # P3 (2026-11-21): card 13 is now Phillips in Wellington, NZ
    # (lon 174.8) — beyond the map's eastern edge (lon 155), so the
    # dot is clamped to the edge at Wellington's latitude: it sits
    # in the Pacific at the frame's right edge, pointing toward NZ.
    (13, "Oceania", 155.0, -41.3),
    (14, "Europe", 23.0, 51.5),
    (15, "Middle East", 34.45, 31.5),
    (16, "Europe", 13.4, 52.5),
]

# Brief dots: (brief id, region, longitude, latitude) of the brief's
# true place — the small unnumbered dots on the map, in the brief's
# region colour. Where a brief names a city it sits on that city;
# where it is a national story it sits on that country's capital or
# the place named. Anchors:
#   17 Cologne (Lufthansa HQ) · 18 Copenhagen · 19 Tallinn ·
#   21 Paris · 23 Odisha coast (cyclone landfall) ·
#   25 Tokyo · 26 Osaka (second Japan brief) · 27 Riyadh ·
#   28 Ahmedabad (bullet-train terminus) · 29 Kathmandu ·
#   31 New York (Mamdani/Rikers) · 32 St Louis
#   (Bayer/Monsanto US base, Roundup litigation) · 33 New York
#   (Gupta sentencing, SDNY) · 34 Washington DC (White House) ·
#   35 Ottawa (the Canada trade deal is the story's subject) ·
#   36 Qeshm Island · 37 Jurf al-Nasr, Iraq · 38 Washington DC ·
#   39 Washington DC (Treasury sanctions) · 40 Abuja · 41 Turkana,
#   Kenya · 42 Johannesburg · 43 Egypt's Eastern Desert (Red Sea
#   gold-mining area) · 44 Accra · 47 Tapachula, Chiapas (caravan entry) ·
#   48 Santiago · 49 Buenos Aires · 50 Caracas · 51 central
#   Florida (Leonida, GTA VI's setting) · 52 Gottingen (Riemann).
BRIEF_ANCHORS = [
    (17, "Europe", 7.0, 50.95),
    (18, "Europe", 12.57, 55.68),
    (19, "Europe", 24.75, 59.44),
    (21, "Europe", 2.35, 48.86),
    (23, "Asia", 121.0, 14.6),
    (25, "Asia", 139.7, 35.7),
    (26, "Asia", 135.5, 34.7),
    (27, "Asia", 46.7, 24.6),
    (28, "Asia", 72.6, 23.0),
    (29, "Asia", 85.3, 27.7),
    (31, "North America", -74.0, 40.7),
    (33, "North America", -74.0, 40.7),
    (35, "North America", -75.7, 45.4),
    (36, "Middle East", 56.3, 26.9),
    (37, "Middle East", 44.2, 32.9),
    (38, "Middle East", -77.0, 38.9),
    (39, "Middle East", -77.0, 38.9),
    (40, "Africa", 7.5, 9.1),
    (41, "Africa", 36.1, 3.1),
    (42, "Africa", 28.0, -26.2),
    (43, "Africa", 32.5, 26.5),
    (47, "Latin America", -92.6, 15.9),
    (50, "Latin America", -66.9, 10.5),
    (51, "Global", -81.5, 27.8),
]

DATE_CHECK_LINES = [
    # EXPANDED 2026-11-21 (user order): LEFT OUT 8 items, NOT YET
    # 3 items — the 5 added items are all verified real (parent
    # verified by live news search): Anthropic's $83 IPO debut
    # (first Nasdaq trading Thu 19 Nov), Tonga's drought emergency
    # (27-day state of emergency Thu 19 Nov), the migrant boat lost
    # off Senegal (capsized off Yenne, reported Thu 19 Nov), the
    # Senate Iran war-powers vote (rejected Thu 19 Nov — NO vote
    # tally: sources report it as both 48-51 and 51-48), and the
    # COP31 final text (due Sat 21 Nov; the summit ran overtime).
    # EDGE stays DELETED (it named "Sat 21 Nov" for the Peru quake,
    # which contradicted the paper's Friday date; the card now
    # carries "FRI 19:09 LOCAL" instead).
    "LEFT OUT: Myanmar genocide ruling, Thu 19 Nov · Trump–Xi–Putin summit, "
    "Thu 19 Nov · Voyager 1 light-day, Wed 18 Nov · Anthropic's $83 IPO "
    "debut, Thu 19 Nov · Tonga's drought emergency, Thu 19 Nov · Migrant "
    "boat lost off Senegal, Thu 19 Nov · Senate Iran war-powers vote, "
    "Thu 19 Nov",
    "NOT YET: BepiColombo enters Mercury orbit, Sat 21 Nov · NATO chief Rutte "
    "due in Warsaw, Sat 21 Nov · COP31 final text, Sat 21 Nov",
]

# (text, is_red) segments for the markets line.
MARKETS_SEGMENTS = [
    ("S&P 500 6,910 ", False), ("-3.7%", True), ("  ·  Nasdaq ", False),
    ("-5.3%", True), ("  ·  Nikkei ", False), ("-5.06%", True),
    ("  ·  Brent $89.87  ·  Gold ", False), ("-4%", True),
    ("  ·  Bitcoin ", False), ("-4.15%", True),
]

SPORTS_TEXT = (
    "Alcaraz beats Cobolli at ATP Finals  ·  A Lim Kim aces 16th, leads "
    "LPGA finale  ·  Price undisputed welterweight champion  ·  Harden's "
    "50th 50-pt game, Cavs 128–119 Pacers"
)

FOOTER_TEXT = (
    "Every story happened, or was first reported, on Friday "
    "20 November 2026. CLAIMED = one side's account. REPORTED = as stated. "
    "Unmarked = confirmed. Sources: Reuters, AP, BBC, AFP, Al Jazeera. "
    "Original drawings."
)
