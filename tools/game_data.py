# -*- coding: utf-8 -*-
"""THE single source of game data for TamaNaruto.

Everything the firmware knows about a ninja comes from here: the roster, which
village it belongs to, its rank, fighting style and chakra nature, its base
stats and its jutsu.

    python3 tools/gen_dex.py      # -> dex.h   (roster, villages, nature chart)
    python3 tools/gen_moves.py    # -> moves.h, move_names.h (jutsu, learnsets)
    python3 tools/gen_ladders.py  # -> trainers.h, badges.h (Chunin exams)
    python3 tools/pack_sprites.py # -> tools/sdcard/mons/*.bin (from the sheets)

How the game works
------------------
The engine's "regions" are the hidden villages: Konoha, Suna, Kiri and Oto.
Each owns a contiguous block of dex numbers.

A ninja keeps its RANK from the series -- Naruto is a Genin, Kakashi a Jonin,
Hiruzen a Kage. Nobody turns into somebody else, so there are no
evolutions (EVOLUTIONS is empty and the engine simply never offers one). What
grows is the level.

  * The academy scroll (the old egg) hatches a ninja of the chosen village.
    Genin are common, Chunin rare, Jonin and Kage legendary.
  * Missions (wild encounters) are ranked by your level: Genin first, Chunin
    from level 25, Jonin from 49, Kage from 61.
  * Defeated ninja can be recruited with a sealing scroll into team or box.
  * Each village's boss ladder is its Chunin exam: eight rounds, four elite
    and a final.

Stages are kept by their engine index; the UI names them (S_STAGE_0..5):
  0 -     1 AKADEMIE   2 GENIN   3 CHUNIN   4 JONIN   5 KAGE

Fighting style is the old attribute triangle:
  TAI beats GEN, GEN beats NIN, NIN beats TAI (x1.3 / x0.8).
Chakra nature is the old element: the canonical cycle Katon > Futon > Raiton >
Doton > Suiton > Katon, Mokuton over Suiton and Doton, Yin and Yang over each
other. CHAKRA (no nature) is neutral.
"""

# ---------------------------------------------------------------------------
STAGES = ['BABY1', 'BABY2', 'ROOKIE', 'CHAMPION', 'ULTIMATE', 'MEGA']
RANK_NAMES = ['-', 'AKADEMIE', 'GENIN', 'CHUNIN', 'JONIN', 'KAGE']
# The level at which each rank turns up in missions.
STAGE_ENTRY = [1, 2, 7, 25, 49, 61]

# Fighting styles. Engine names kept (VACCINE beats VIRUS beats DATA):
#   VACCINE = TAI, VIRUS = GEN, DATA = NIN, FREE = neutral.
ATTRS = ['VACCINE', 'DATA', 'VIRUS', 'FREE']
STYLE = {'TAI': 'VACCINE', 'NIN': 'DATA', 'GEN': 'VIRUS', 'FREE': 'FREE'}
ATTR_LABEL = {'VACCINE': 'TAI', 'DATA': 'NIN', 'VIRUS': 'GEN', 'FREE': 'FREI'}

# Chakra natures, the battle engine's types. Engine order and names are kept
# so the generated enum stays stable; ELEMENT_LABEL is what the panel shows.
ELEMENTS = ['neutral', 'fire', 'water', 'plant', 'electric', 'wind',
            'earth', 'light', 'dark']
ELEMENT_LABEL = {
    'neutral': 'CHAKRA', 'fire': 'KATON', 'water': 'SUITON', 'plant': 'MOKUTON',
    'electric': 'RAITON', 'wind': 'FUTON', 'earth': 'DOTON', 'light': 'YANG',
    'dark': 'YIN',
}

CHART = {
    'fire':     {'wind': 2, 'plant': 2, 'water': .5, 'fire': .5},
    'wind':     {'electric': 2, 'fire': .5, 'wind': .5},
    'electric': {'earth': 2, 'wind': .5, 'electric': .5},
    'earth':    {'water': 2, 'electric': .5, 'plant': .5, 'earth': .5},
    'water':    {'fire': 2, 'earth': .5, 'plant': .5, 'water': .5},
    'plant':    {'water': 2, 'earth': 2, 'fire': .5, 'plant': .5},
    'light':    {'dark': 2, 'light': .5},
    'dark':     {'light': 2, 'dark': .5},
}

ELEMENT_ACCENT = {
    'neutral': '#8a8a6a', 'fire': '#e8503a', 'water': '#4f93c4',
    'plant': '#3c8a4c', 'electric': '#b8960b', 'wind': '#7fae9a',
    'earth': '#b08a3d', 'light': '#c9a227', 'dark': '#6a5a9e',
}
# 0 meadow, 1 beach, 2 forest, 3 volcano, 4 mountain, 5 snow
ELEMENT_BIOME = {
    'neutral': 2, 'fire': 3, 'water': 1, 'plant': 2, 'electric': 4,
    'wind': 0, 'earth': 4, 'light': 0, 'dark': 2,
}

# ---------------------------------------------------------------------------
STAGE_BASE = [18, 30, 48, 72, 94, 114]
PROFILES = {
    'bal':   (1.00, 1.00, 1.00, 1.00, 1.00, 1.00),
    'phys':  (1.00, 1.25, 1.05, 0.95, 0.80, 0.95),
    'spec':  (0.95, 0.80, 0.95, 1.00, 1.25, 1.05),
    'tank':  (1.20, 0.95, 1.30, 0.70, 0.85, 1.10),
    'fast':  (0.90, 1.05, 0.80, 1.35, 1.05, 0.85),
    'weak':  (0.80, 0.75, 0.75, 0.80, 0.75, 0.75),
}

# ---------------------------------------------------------------------------
# The roster.
#
# (num, village, sprite, display, rank, style, nature, profile, jutsu)
#   sprite   key of the sheet in tools/sprites/picks.json
#   display  <= 15 chars, ASCII upper case (the bitmap font has no accents)
#   rank     1 AKADEMIE  2 GENIN  3 CHUNIN  4 JONIN  5 KAGE
#   jutsu    signature techniques, strongest last
KO, SU, KI, OT = 'KONOHA', 'SUNA', 'KIRI', 'OTO'

ROSTER = [
    # ---------------- Konoha ------------------------------------------------
    (1,  KO, 'nc2_naruto',        'NARUTO',       2, 'NIN', 'wind',     'bal',  ['KAGE BUNSHIN', 'UZUMAKI REN', 'RASENGAN']),
    (2,  KO, 'nc2_sasuke',        'SASUKE',       2, 'NIN', 'fire',     'fast', ['GOKAKYU', 'SHISHI RENDAN', 'CHIDORI']),
    (3,  KO, 'nc2_sakura',        'SAKURA',       2, 'GEN', 'earth',    'spec', ['KAWARIMI', 'SHANNARO']),
    (4,  KO, 'nc1_ino',           'INO',          2, 'GEN', 'dark',     'spec', ['SHINTENSHIN', 'BLUETENSTURM']),
    (5,  KO, 'nc1_shikamaru',     'SHIKAMARU',    3, 'GEN', 'dark',     'spec', ['KAGEMANE', 'KAGE KUBI']),
    (6,  KO, 'nc1_choji',         'CHOJI',        2, 'TAI', 'light',    'tank', ['BAIKA', 'NIKUDAN']),
    (7,  KO, 'nc2_kiba',          'KIBA',         2, 'TAI', 'neutral',  'fast', ['JUJIN BUNSHIN', 'GATSUGA']),
    (8,  KO, 'nc1_shino',         'SHINO',        2, 'NIN', 'dark',     'tank', ['MUSHI KABE', 'KIKAICHU']),
    (9,  KO, 'nc2_neji',          'NEJI',         2, 'TAI', 'neutral',  'bal',  ['JUKEN', 'KAITEN', 'HAKKE 64']),
    (10, KO, 'nc2_rock_lee',      'ROCK LEE',     2, 'TAI', 'neutral',  'fast', ['KONOHA SENPU', 'OMOTE RENGE']),
    (11, KO, 'nc1_konohamaru',    'KONOHAMARU',   1, 'NIN', 'neutral',  'weak', ['BUNSHIN']),
    (12, KO, 'nc1_enemy_ninja_1', 'KONOHA-CHUNIN', 3, 'TAI', 'earth',   'tank', ['FELSWURF', 'DOTON HEKI']),
    (13, KO, 'nc1_kakashi',       'KAKASHI',      4, 'NIN', 'electric', 'fast', ['SHARINGAN', 'CHIDORI', 'RAIKIRI']),
    (14, KO, 'nc2_3rd_hokage',    'HIRUZEN',      5, 'NIN', 'fire',     'bal',  ['ENMA', 'KATON RYUEN', 'SHIKI FUJIN']),
    (15, KO, 'tobirama',          'TOBIRAMA',     5, 'NIN', 'water',    'fast', ['HIRAISHIN', 'SUIRYUDAN']),
    (16, KO, 'hashirama',         'HASHIRAMA',    5, 'NIN', 'plant',    'tank', ['MOKUTON', 'JUKAI KOTAN']),
    # ---------------- Suna --------------------------------------------------
    (17, SU, 'nc1_gaara',         'GAARA',        2, 'NIN', 'earth',    'tank', ['SUNA NO TATE', 'SABAKU KYU']),
    (18, SU, 'nc2_kankuro',       'KANKURO',      2, 'GEN', 'dark',     'bal',  ['GIFTNADEL', 'KARASU']),
    (19, SU, 'nc1_temari',        'TEMARI',       2, 'NIN', 'wind',     'spec', ['KAMAITACHI', 'DAI KAMAITACHI']),
    (20, SU, 'nc1_ninja',         'SUNA-NINJA',   3, 'TAI', 'wind',     'fast', ['FUTON DAN', 'KUNAI HAGEL']),
    # ---------------- Kiri --------------------------------------------------
    (21, KI, 'nc1_haku',          'HAKU',         2, 'NIN', 'water',    'fast', ['SENBON', 'MAKYO HYOSHO']),
    (22, KI, 'nc1_enemy_ninja_2', 'KIRI-NINJA',   3, 'TAI', 'water',    'phys', ['SENBON', 'GIFTKLAUE', 'KETTENFALLE']),
    (23, KI, 'nc1_zabuza',        'ZABUZA',       4, 'TAI', 'water',    'phys', ['KIRIGAKURE', 'SUIRYUDAN', 'KUBIKIRI']),
    # ---------------- Oto ---------------------------------------------------
    (24, OT, 'nc2_dosu',          'DOSU',         2, 'GEN', 'neutral',  'tank', ['KYOMEISEN', 'SCHALLWELLE']),
    (25, OT, 'nc2_abumi',         'ZAKU',         2, 'NIN', 'wind',     'spec', ['ZANKUHA', 'ZANKUKYOKUHA']),
    (26, OT, 'nc2_sound_ninja_1', 'OTO-NINJA',    2, 'TAI', 'neutral',  'bal',  ['KUNAI HAGEL']),
    (27, OT, 'nc2_sound_ninja_2', 'OTO-WAECHTER', 3, 'TAI', 'earth',    'tank', ['DOTON HEKI', 'FELSWURF']),
    (28, OT, 'nc2_sound_ninja_3', 'OTO-MASKE',    3, 'GEN', 'dark',     'spec', ['SCHATTENKLINGE', 'GIFTNEBEL']),
    (29, OT, 'nc2_sound_ninja_4', 'OTO-KRALLE',   3, 'TAI', 'dark',     'fast', ['GIFTKLAUE', 'SCHATTENKLINGE']),
    (30, OT, 'nc2_sound_ninja_6', 'OTO-KETTE',    3, 'TAI', 'neutral',  'phys', ['KETTENFALLE', 'FELSWURF']),
    (31, OT, 'nc2_sound_ninja_5', 'OTO-KOLOSS',   4, 'TAI', 'earth',    'tank', ['DOTON HEKI', 'ERDBEBEN']),
    (32, OT, 'nc2_kabuto',        'KABUTO',       4, 'NIN', 'light',    'bal',  ['SHOSEN', 'CHAKRA SKALPELL']),
    (33, OT, 'nc2_orochimaru',    'OROCHIMARU',   5, 'NIN', 'dark',     'spec', ['SENEIJA', 'KUSANAGI', 'EDO TENSEI']),
]

# (name, lo, hi, first-scroll starters)
VERSIONS = [
    (KO, 1, 16, [1, 2, 3]),
    (SU, 17, 20, [17, 18, 19]),
    (KI, 21, 23, [21]),
    (OT, 24, 33, [24, 25, 26]),
]

BIOME_OVERRIDE = {21: 5, 22: 1, 23: 1, 17: 4, 18: 4, 19: 4, 20: 4}

# Favourite food per ninja (index into the feed menu: 0 RAMEN 1 DANGO 2 ONIGIRI).
FAVOURITE = {1: 0, 6: 2, 3: 1, 4: 1, 10: 2, 13: 1}

# No ninja turns into another one. Kept as a table so the engine's
# digivolution code still compiles; it is simply never offered anything.
EVOLUTIONS = []

# ---------------------------------------------------------------------------
# Jutsu.
# (NAME <= 12 chars, nature, category, power, accuracy, effect, param,
#  statMask, stages, target, ailment, ailmentChance, display <= 23)
MC_PHYS, MC_SPEC, MC_STATUS = 0, 1, 2
AIL_NONE, AIL_PARA, AIL_BURN, AIL_POISON, AIL_SLEEP, AIL_FREEZE, AIL_CONFUSE = range(7)
EF_NONE, EF_STAGE, EF_RECOIL, EF_DRAIN, EF_FIXED_LVL, EF_FIXED, EF_PRIORITY, \
    EF_NEVER_MISS, EF_MULTI, EF_HEAL, EF_RECHARGE, EF_CHARGE = range(12)
ST_ATK, ST_DEF, ST_SPA, ST_SPD, ST_SPE = 1, 2, 4, 8, 16
TG_SELF, TG_FOE = 0, 1

def A(name, el, cat, pw, acc=100, eff=EF_NONE, param=0, mask=0, stg=0,
      tgt=TG_FOE, ail=AIL_NONE, ach=0, disp=None):
    return (name, el, cat, pw, acc, eff, param, mask, stg, tgt, ail, ach, disp)

MOVES = [
    # --- basics, learned by everyone -----------------------------------------
    A('SHURIKEN',     'neutral', MC_SPEC, 30),
    A('KUNAI',        'neutral', MC_PHYS, 40),
    A('TRITT',        'neutral', MC_PHYS, 50),
    A('SHUNSHIN',     'neutral', MC_PHYS, 40, eff=EF_PRIORITY, param=1),
    A('FAUSTHIEB',    'neutral', MC_PHYS, 70),
    A('WIRBELTRITT',  'neutral', MC_PHYS, 85, 95),
    A('CHAKRA-STOSS', 'neutral', MC_SPEC, 130, 90, eff=EF_RECHARGE),
    A('BLOCK',        'neutral', MC_STATUS, 0, 0, EF_STAGE, 0, ST_DEF | ST_SPD, 1, TG_SELF),
    A('CHAKRA LADEN', 'neutral', MC_STATUS, 0, 0, EF_STAGE, 0, ST_ATK | ST_SPA, 1, TG_SELF),
    A('FOKUS',        'neutral', MC_STATUS, 0, 0, EF_STAGE, 0, ST_SPE, 2, TG_SELF),
    A('DROHEN',       'neutral', MC_STATUS, 0, 100, EF_STAGE, 0, ST_ATK, -1, TG_FOE),
    A('HEILPILLE',    'neutral', MC_STATUS, 0, 0, EF_HEAL, 50, tgt=TG_SELF),
    # --- Konoha --------------------------------------------------------------
    A('KAGE BUNSHIN', 'neutral', MC_STATUS, 0, 0, EF_STAGE, 0, ST_ATK | ST_SPE, 1, TG_SELF, disp='KAGE BUNSHIN NO JUTSU'),
    A('UZUMAKI REN',  'neutral', MC_PHYS, 85, disp='UZUMAKI NARUTO RENDAN'),
    A('RASENGAN',     'wind',    MC_SPEC, 110),
    A('GOKAKYU',      'fire',    MC_SPEC, 80, ail=AIL_BURN, ach=20, disp='GOKAKYU NO JUTSU'),
    A('SHISHI RENDN', 'neutral', MC_PHYS, 90, disp='SHISHI RENDAN'),
    A('CHIDORI',      'electric', MC_PHYS, 110, ail=AIL_PARA, ach=20),
    A('KAWARIMI',     'neutral', MC_STATUS, 0, 0, EF_STAGE, 0, ST_DEF | ST_SPD, 2, TG_SELF, disp='KAWARIMI NO JUTSU'),
    A('SHANNARO',     'earth',   MC_PHYS, 95, 95, disp='SHANNARO!'),
    A('SHINTENSHIN',  'dark',    MC_SPEC, 60, 95, ail=AIL_CONFUSE, ach=50, disp='SHINTENSHIN NO JUTSU'),
    A('BLUETENSTURM', 'plant',   MC_SPEC, 80, disp='BLUETENSTURM'),
    A('KAGEMANE',     'dark',    MC_SPEC, 50, 95, ail=AIL_PARA, ach=60, disp='KAGEMANE NO JUTSU'),
    A('KAGE KUBI',    'dark',    MC_PHYS, 100, disp='KAGE KUBISHIBARI'),
    A('BAIKA',        'light',   MC_STATUS, 0, 0, EF_STAGE, 0, ST_ATK | ST_DEF, 1, TG_SELF, disp='BAIKA NO JUTSU'),
    A('NIKUDAN',      'light',   MC_PHYS, 110, 90, disp='NIKUDAN SENSHA'),
    A('JUJIN BUNSHN', 'neutral', MC_STATUS, 0, 0, EF_STAGE, 0, ST_ATK, 2, TG_SELF, disp='JUJIN BUNSHIN'),
    A('GATSUGA',      'neutral', MC_PHYS, 100, 95),
    A('MUSHI KABE',   'dark',    MC_STATUS, 0, 0, EF_STAGE, 0, ST_DEF | ST_SPD, 2, TG_SELF, disp='MUSHI KABE'),
    A('KIKAICHU',     'dark',    MC_SPEC, 75, eff=EF_DRAIN, param=50, disp='KIKAICHU NO JUTSU'),
    A('JUKEN',        'neutral', MC_PHYS, 70, eff=EF_PRIORITY, param=1),
    A('KAITEN',       'neutral', MC_PHYS, 90, disp='HAKKESHO KAITEN'),
    A('HAKKE 64',     'neutral', MC_SPEC, 115, 90, ail=AIL_PARA, ach=20, disp='HAKKE ROKUJUYON SHO'),
    A('KONOHA SENPU', 'neutral', MC_PHYS, 75),
    A('OMOTE RENGE',  'neutral', MC_PHYS, 130, 90, eff=EF_RECOIL, param=4),
    A('BUNSHIN',      'neutral', MC_STATUS, 0, 0, EF_STAGE, 0, ST_SPE, 1, TG_SELF, disp='BUNSHIN NO JUTSU'),
    A('DOTON HEKI',   'earth',   MC_STATUS, 0, 0, EF_STAGE, 0, ST_DEF, 2, TG_SELF, disp='DOTON DOROJOHEKI'),
    A('KUNAI HAGEL',  'neutral', MC_PHYS, 75),
    A('SHARINGAN',    'neutral', MC_STATUS, 0, 0, EF_STAGE, 0, ST_SPA | ST_SPE, 1, TG_SELF),
    A('RAIKIRI',      'electric', MC_PHYS, 130, 90, ail=AIL_PARA, ach=20),
    A('ENMA',         'earth',   MC_PHYS, 110, disp='ENMA, AFFENKOENIG'),
    A('KATON RYUEN',  'fire',    MC_SPEC, 115, 90, ail=AIL_BURN, ach=20, disp='KATON RYUEN HOKA'),
    A('SHIKI FUJIN',  'dark',    MC_SPEC, 150, 85, eff=EF_RECHARGE),
    A('HIRAISHIN',    'neutral', MC_PHYS, 95, eff=EF_PRIORITY, param=1, disp='HIRAISHIN NO JUTSU'),
    A('SUIRYUDAN',    'water',   MC_SPEC, 120, 90, disp='SUIRYUDAN NO JUTSU'),
    A('MOKUTON',      'plant',   MC_PHYS, 115, disp='MOKUTON NO JUTSU'),
    A('JUKAI KOTAN',  'plant',   MC_SPEC, 140, 90, eff=EF_DRAIN, param=25),
    # --- Suna ----------------------------------------------------------------
    A('SUNA NO TATE', 'earth',   MC_STATUS, 0, 0, EF_STAGE, 0, ST_DEF | ST_SPD, 2, TG_SELF),
    A('SABAKU KYU',   'earth',   MC_SPEC, 110, 90, ail=AIL_PARA, ach=20, disp='SABAKU KYU'),
    A('GIFTNADEL',    'dark',    MC_PHYS, 60, ail=AIL_POISON, ach=40),
    A('KARASU',       'neutral', MC_PHYS, 90, disp='KARASU, DIE PUPPE'),
    A('KAMAITACHI',   'wind',    MC_SPEC, 85, disp='KAMAITACHI NO JUTSU'),
    A('DAI KAMAITAC', 'wind',    MC_SPEC, 120, 90, disp='DAI KAMAITACHI'),
    A('FUTON DAN',    'wind',    MC_SPEC, 70),
    # --- Kiri ----------------------------------------------------------------
    A('SENBON',       'water',   MC_PHYS, 60, eff=EF_PRIORITY, param=1),
    A('MAKYO HYOSHO', 'water',   MC_SPEC, 110, 90, ail=AIL_FREEZE, ach=20, disp='MAKYO HYOSHO'),
    A('GIFTKLAUE',    'dark',    MC_PHYS, 70, ail=AIL_POISON, ach=30),
    A('KETTENFALLE',  'neutral', MC_PHYS, 80, 95, ail=AIL_PARA, ach=20),
    A('KIRIGAKURE',   'water',   MC_STATUS, 0, 0, EF_STAGE, 0, ST_SPE | ST_DEF, 1, TG_SELF, disp='KIRIGAKURE NO JUTSU'),
    A('KUBIKIRI',     'neutral', MC_PHYS, 115, disp='KUBIKIRIBOCHO'),
    # --- Oto -----------------------------------------------------------------
    A('KYOMEISEN',    'neutral', MC_SPEC, 85, 95, ail=AIL_CONFUSE, ach=30),
    A('SCHALLWELLE',  'neutral', MC_SPEC, 60),
    A('ZANKUHA',      'wind',    MC_SPEC, 80),
    A('ZANKUKYOKUHA', 'wind',    MC_SPEC, 115, 90),
    A('FELSWURF',     'earth',   MC_PHYS, 80, 95),
    A('SCHATTENKLNG', 'dark',    MC_PHYS, 85, disp='SCHATTENKLINGE'),
    A('GIFTNEBEL',    'dark',    MC_SPEC, 60, 95, ail=AIL_POISON, ach=50),
    A('ERDBEBEN',     'earth',   MC_PHYS, 115, 90),
    A('SHOSEN',       'light',   MC_STATUS, 0, 0, EF_HEAL, 50, tgt=TG_SELF, disp='SHOSEN NO JUTSU'),
    A('CHAKRA SKALP', 'light',   MC_PHYS, 100, disp='CHAKRA NO MESU'),
    A('SENEIJA',      'dark',    MC_PHYS, 90, ail=AIL_POISON, ach=30, disp='SEN\'EIJASHU'),
    A('KUSANAGI',     'neutral', MC_PHYS, 120, disp='KUSANAGI-SCHWERT'),
    A('EDO TENSEI',   'dark',    MC_SPEC, 150, 85, eff=EF_RECHARGE),
    # --- fallback, never learned ----------------------------------------------
    A('STRUGGLE',     'neutral', MC_PHYS, 50, 0, EF_RECOIL, 4),
]

# The roster names a few jutsu by their full form; map them to the <=12 key.
ALIAS = {'SHISHI RENDAN': 'SHISHI RENDN', 'JUJIN BUNSHIN': 'JUJIN BUNSHN',
         'DAI KAMAITACHI': 'DAI KAMAITAC', 'SCHATTENKLINGE': 'SCHATTENKLNG',
         'CHAKRA SKALPELL': 'CHAKRA SKALP'}
ROSTER = [r[:8] + ([ALIAS.get(m, m) for m in r[8]],) for r in ROSTER]

# Basic moves, localised. Jutsu keep their Japanese names in every language,
# which is also how the series handles them.
# Order: ES, EN, FR, DE, IT, PT. ASCII only (the bitmap font has no accents).
GENERIC_NAMES = {
    'SHURIKEN':     ['SHURIKEN',      'SHURIKEN',      'SHURIKEN',      'SHURIKEN',      'SHURIKEN',      'SHURIKEN'],
    'KUNAI':        ['KUNAI',         'KUNAI',         'KUNAI',         'KUNAI',         'KUNAI',         'KUNAI'],
    'TRITT':        ['PATADA',        'KICK',          'COUP DE PIED',  'TRITT',         'CALCIO',        'CHUTE'],
    'SHUNSHIN':     ['SHUNSHIN',      'SHUNSHIN',      'SHUNSHIN',      'SHUNSHIN',      'SHUNSHIN',      'SHUNSHIN'],
    'FAUSTHIEB':    ['PUNETAZO',      'PUNCH',         'COUP DE POING', 'FAUSTHIEB',     'PUGNO',         'SOCO'],
    'WIRBELTRITT':  ['PATADA GIRO',   'SPIN KICK',     'COUP TOURNANT', 'WIRBELTRITT',   'CALCIO ROTANTE', 'CHUTE GIRATORIO'],
    'CHAKRA-STOSS': ['GOLPE CHAKRA',  'CHAKRA BURST',  'CHOC CHAKRA',   'CHAKRA-STOSS',  'COLPO CHAKRA',  'GOLPE CHAKRA'],
    'BLOCK':        ['BLOQUEO',       'BLOCK',         'PARADE',        'BLOCK',         'PARATA',        'BLOQUEIO'],
    'CHAKRA LADEN': ['CARGAR CHAKRA', 'CHARGE CHAKRA', 'CHARGE CHAKRA', 'CHAKRA LADEN',  'CARICA CHAKRA', 'CARREGAR CHAKRA'],
    'FOKUS':        ['CONCENTRACION', 'FOCUS',         'CONCENTRATION', 'FOKUS',         'CONCENTRAZIONE', 'FOCO'],
    'DROHEN':       ['INTIMIDAR',     'INTIMIDATE',    'INTIMIDATION',  'DROHEN',        'INTIMIDIRE',    'INTIMIDAR'],
    'HEILPILLE':    ['PILDORA',       'SOLDIER PILL',  'PILULE',        'HEILPILLE',     'PILLOLA',       'PILULA'],
    'STRUGGLE':     ['FORCEJEO',      'STRUGGLE',      'LUTTE',         'VERZWEIFLUNG',  'SCONTRO',       'DEBATER'],
}

# Basic moves by rank, as (move, level offset from the rank's entry level).
# Offset None = level 1, so a ninja met in a mission always has something.
STAGE_GENERIC = {
    0: [('SHURIKEN', None)],
    1: [('SHURIKEN', None), ('KUNAI', 0)],
    2: [('KUNAI', None), ('DROHEN', 3), ('TRITT', 6), ('BLOCK', 10), ('SHUNSHIN', 13)],
    3: [('KUNAI', None), ('FAUSTHIEB', 8), ('CHAKRA LADEN', 12), ('WIRBELTRITT', 16), ('HEILPILLE', 20)],
    4: [('FAUSTHIEB', None), ('FOKUS', 4), ('CHAKRA-STOSS', 14)],
    5: [('WIRBELTRITT', None), ('HEILPILLE', 6), ('CHAKRA-STOSS', 10)],
}
# Signature jutsu, as level offsets from the rank's entry level. A ninja meets
# its first one at once, the others as it levels.
SIG_OFFSETS = [0, 8, 18]

# ---------------------------------------------------------------------------
# Chunin exams (the engine's boss ladders): 8 rounds, 4 elite and a final per
# village. Teams are (dex, level).
AREAS = {
    KO: ['AKADEMIE', 'TRAININGSPLATZ', 'WALD DES TODES', 'VORRUNDE',
         'ARENA', 'HOKAGE-FELSEN', 'ANBU-BASIS', 'HOKAGE-TURM'],
    SU: ['WUESTENTOR', 'DUENEN', 'SANDSTURM', 'OASE',
         'FELSSCHLUCHT', 'PUPPENWERKSTATT', 'KAZEKAGE-HAUS', 'SANDPALAST'],
    KI: ['NEBELHAFEN', 'BRUECKE', 'SUMPF', 'EISWALD',
         'SPIEGELSEE', 'NEBELWALD', 'SCHWERTGRAB', 'MIZUKAGE-HAUS'],
    OT: ['REISFELD', 'VERSTECK', 'GIFTSUMPF', 'LABOR',
         'KERKER', 'SCHLANGENTAL', 'GEHEIMBASIS', 'OROCHIMARUS SAAL'],
}


def _ladder(ver):
    """Eight rounds, four elite and a final. Like the real Chunin exam, every
    village sends ninja: each round's leader is from the home village where it
    has one of that rank, the rest of the team comes from everyone. A Jonin is
    only met at a level where one could exist."""
    bn = by_num()
    vi = [v[0] for v in VERSIONS].index(ver)
    def rank(st, home=None):
        return [r[0] for r in ROSTER if r[4] == st and (home is None or r[1] == home)]
    allr = {st: rank(st) for st in range(6)}
    homer = {st: rank(st, ver) for st in range(6)}
    gen = allr[2]
    chu = allr[3]
    jon = allr[4]
    top = homer[5] or homer[4] or allr[5]
    pick = lambda lst, i: lst[(i + 3 * vi) % len(lst)]
    lead = lambda st, i: (homer[st] or allr[st])[(i + vi) % len(homer[st] or allr[st])]
    nm = lambda d: bn[d][3]
    el = lambda d: bn[d][6]
    def team(leader, others):
        seen, out = {leader}, []
        for d, lv in others:
            if d in seen:
                continue
            seen.add(d); out.append((d, lv))
        return out
    out = []
    # round 1: academy students warm up for a Genin, so one starter can win it
    # (Suna and Oto open with two, Konoha and Kiri with three: touch_test
    # relies on the ladders not all having the same shape)
    aca = allr[1] or gen
    L = lead(2, 0)
    first = [(aca[0], 3), (aca[0], 4)][:1 if vi % 2 else 2] + [(L, 5)]
    out.append((nm(L), el(L), first))
    for i, lvls in ((1, (9, 11)), (2, (13, 14, 16))):
        L = lead(2, i)
        size = len(lvls)
        others = team(L, [(pick(gen, i * 3 + k), lvls[k]) for k in range(size)])[:size - 1]
        out.append((nm(L), el(L), others + [(L, lvls[size - 1])]))
    for i in range(5):
        L = lead(3, i)
        others = team(L, [(pick(gen, i), 23 + 3 * i), (pick(chu, i + 1), 26 + 3 * i)])
        out.append((nm(L), el(L), others + [(L, 28 + 3 * i)]))
    for i in range(4):
        L = lead(4, i)
        others = team(L, [(pick(chu, i), 46 + 2 * i), (pick(jon, i + 1), 50 + 2 * i)])
        out.append((nm(L), el(L), others + [(L, 52 + 2 * i)]))
    L = top[-1]
    others = team(L, [(pick(jon, 0), 58), (pick(chu, 2), 60)] +
                  [(m, 62 + k) for k, m in enumerate(top[:-1])])
    out.append((nm(L), el(L), others + [(L, 64)]))
    return out


# ---------------------------------------------------------------------------
def by_num():
    return {r[0]: r for r in ROSTER}


LADDERS = {v[0]: _ladder(v[0]) for v in VERSIONS}
for _v in AREAS:
    AREAS[_v] = AREAS[_v] + ['ELITE'] * 4 + ['FINALE']


def evolve_level(num):
    return 0


def first_target(num):
    return 0


def base_stats(num):
    _n, _v, _s, _d, stage, _a, _e, prof, _m = by_num()[num]
    b = STAGE_BASE[stage]
    wob = [((num * 37 + i * 11) % 9) - 4 for i in range(6)]
    return tuple(max(5, min(160, round(b * f) + w)) for f, w in zip(PROFILES[prof], wob))


def learnset(num):
    """[(move NAME, level)] in level order."""
    _n, _v, _s, _d, stage, _a, _e, _p, sigs = by_num()[num]
    # Counted from level 1, not from the rank's mission level: a Jonin can come
    # out of an academy scroll at level 1, and must not stand there with one
    # punch until level 49.
    entry = 1
    out = []
    for mv, off in STAGE_GENERIC[stage]:
        out.append((mv, 1 if off is None else entry + off))
    for i, mv in enumerate(sigs):
        out.append((mv, entry + SIG_OFFSETS[min(i, len(SIG_OFFSETS) - 1)]))
    seen, uniq = set(), []
    for mv, lv in sorted(out, key=lambda x: x[1]):
        if mv in seen:
            continue
        seen.add(mv)
        uniq.append((mv, min(lv, 100)))
    return uniq


def rarity_tier(num):
    """Academy-scroll rarity: Genin common, Chunin rare, Jonin/Kage legendary."""
    st = by_num()[num][4]
    return 'R_COMUN' if st <= 2 else ('R_RARO' if st == 3 else 'R_LEGENDARIO')


def validate():
    nums = [r[0] for r in ROSTER]
    assert nums == list(range(1, len(ROSTER) + 1)), 'dex numbers must be 1..N'
    names = {m[0] for m in MOVES}
    for r in ROSTER:
        assert len(r[3]) <= 15, r[3]
        assert r[5] in ATTRS, r
        for mv in r[8]:
            assert mv in names, (r[3], mv)
    for m in MOVES:
        assert len(m[0]) <= 12, m[0]
        assert m[1] in ELEMENTS, m
        assert len(m[12] or m[0]) <= 23, m
    assert len(names) == len(MOVES), 'duplicate jutsu name'
    lo = 1
    for name, a, b, st in VERSIONS:
        assert a == lo, name
        lo = b + 1
        for s in st:
            assert a <= s <= b, ('starter outside its village', name, s)
    assert lo == len(ROSTER) + 1, 'villages must tile the roster'
    bn = by_num()
    for v, ladder in LADDERS.items():
        assert len(ladder) == 13, v
        for name, el, team in ladder:
            assert el in ELEMENTS
            assert 2 <= len(team) <= 6, (v, name)
            if ladder.index((name, el, team)):   # round 1 may field two students
                assert len({d for d, _ in team}) == len(team), ('twice in one team', v, name)
            for d, lv in team:
                assert lv >= STAGE_ENTRY[bn[d][4]] - 3, ('boss below its rank', v, name, d, lv)
    return True


# Style is stored with the engine's attribute names.
ROSTER = [r[:5] + (STYLE[r[5]],) + r[6:] for r in ROSTER]

if __name__ == '__main__':
    validate()
    print('ok: %d ninja, %d jutsu, %d villages' % (len(ROSTER), len(MOVES), len(VERSIONS)))
