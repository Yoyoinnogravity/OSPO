"""Guardian 30115 — Aled's populate bank from Fifteen Squared.

Cut one film at a time. Do not rebuild films already locked.
Source: https://fifteensquared.net/2026/09/18/guardian-cryptic-crossword-no-30115-by-brendan/
Setter Brendan, blogger manehi. We credit all.
"""

from __future__ import annotations

# Already cut (do not rebuild unless Aled asks).
CUT = frozenset(
    {
        "DREAMLIKE",
        "RASTA",
        "FATS",
        "WELLINGTON",
        "COLE",
        "SMILES",
        "AIMLESSLY",
    }
)
# Filmed once; Aled said no. Leave on ice.
ON_ICE = frozenset({"DAVIS CUP"})

# Waiting on Guardian 30115. MASS MEDIA is a separate FT film.
WAITING = (
    "A GOGO",
    "SALAL",
    "RISINGS",
    "INSTANT",
    "AUDIT",
    "BUD",
    "HAVANAS",
    "DINES IN",
    "MASOCHISM",
    "SOMME",
    "NAURU",
    "TENSIONAL",
    "ASIDES",
    "LYREBIRD",
    "HARM",
    "HOLIDAYS",
    "ROACH",
    "STRONG SUIT",
    "TRAIN",
    "BASSISTS",
    "DOMINO",
    "SIMONE",
    "MONK",
    "CLUB",
    "ELLA",
)
