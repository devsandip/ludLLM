"""A curated, deterministic anachronism backstop.

LLMs have a weak grip on chronology: they will give a country a nuclear weapon
before its first test, run DNA profiling before it was invented, or put a mobile
phone in a 1960s scene. The capability baseline on each Era (state/schema.py) is
the primary defense (the model commits to what the period allows, and a
cross-family critic checks it); this term scan is the cheap mechanical backstop
for the embarrassing lexical cases, the same role find_leaks plays for secrets.

Two directions, because anachronism cuts both ways:

  EARLIEST - a thing that did not exist yet, or a place name not yet adopted,
             appearing too early ("DNA profiling" in 1975, "Mumbai" in 1990).
  LATEST   - a defunct state or a superseded place name appearing too late
             ("the Soviet Union" in 2010, "Leningrad" in 2005).

This is intentionally PARTIAL and high-precision: every entry is unambiguous
enough to scan prose for without drowning in false positives. It catches the
obvious howlers; it does not replace the period critic, which catches the
semantic ones (a character "Googling", a war that has not happened yet, slang
from the wrong decade) that no word list can.
"""

from __future__ import annotations

import re

# term -> (earliest plausible year, short reason). Flagged when an era predates it.
EARLIEST: dict[str, tuple[int, str]] = {
    # --- communications ---
    "mobile phone": (1983, "no commercial cellular telephony"),
    "cell phone": (1983, "no commercial cellular telephony"),
    "cellphone": (1983, "no commercial cellular telephony"),
    "cellular phone": (1983, "no commercial cellular telephony"),
    "smartphone": (2007, "the smartphone era starts with the iPhone"),
    "text message": (1993, "SMS not yet in service"),
    "satellite phone": (1998, "no consumer satphones before Iridium"),
    "satphone": (1998, "no consumer satphones before Iridium"),
    "fax machine": (1966, "the modern fax machine postdates this"),
    "email": (1991, "email is not yet in general use"),
    "e-mail": (1991, "email is not yet in general use"),
    "the internet": (1991, "the public internet does not exist yet"),
    "world wide web": (1991, "the web does not exist yet"),
    "wi-fi": (1999, "wireless networking not yet available"),
    "wifi": (1999, "wireless networking not yet available"),
    "skype": (2003, "voice-over-IP calling not yet available"),
    "whatsapp": (2009, "the app does not exist yet"),
    "encrypted messaging app": (2009, "no smartphone messaging apps yet"),
    # --- computing ---
    "personal computer": (1977, "no consumer personal computers"),
    "laptop": (1985, "no portable computers yet"),
    "flash drive": (2000, "USB flash storage not yet available"),
    "thumb drive": (2000, "USB flash storage not yet available"),
    "usb": (1997, "USB not yet on the market"),
    "cd-rom": (1985, "the format does not exist yet"),
    "dvd": (1996, "the format does not exist yet"),
    "search engine": (1995, "no web search engines yet"),
    "google search": (1998, "Google does not exist yet"),
    "googled": (1998, "Google does not exist yet"),
    "googling": (1998, "Google does not exist yet"),
    # --- positioning, surveillance, forensics ---
    "gps": (1990, "no fielded GPS receivers yet"),
    "dna testing": (1986, "DNA profiling not yet in casework"),
    "dna profiling": (1986, "DNA profiling not yet in casework"),
    "dna fingerprinting": (1986, "DNA profiling not yet in casework"),
    "dna evidence": (1986, "DNA profiling not yet in casework"),
    "dna analysis": (1986, "DNA profiling not yet in casework"),
    "genetic fingerprint": (1986, "DNA profiling not yet in casework"),
    "facial recognition": (2001, "automated face matching not yet deployed"),
    "biometric": (1990, "no biometric systems yet"),
    # --- weapons / hardware ---
    "glock": (1982, "the pistol is not yet made"),
    "ak-74": (1974, "the rifle is not yet issued"),
    "stinger missile": (1981, "the system is not yet fielded"),
    "stealth bomber": (1989, "no stealth aircraft in service"),
    "predator drone": (1995, "the UAV does not exist yet"),
    "drone strike": (2001, "armed UAV strikes have not begun"),
    # --- place names adopted later (the NEW name appearing too early) ---
    "mumbai": (1995, "the city is called Bombay until 1995"),
    "chennai": (1996, "the city is called Madras until 1996"),
    "kolkata": (2001, "the city is called Calcutta until 2001"),
    "beijing": (1979, "rendered Peking in English until the pinyin shift"),
    "myanmar": (1989, "the country is called Burma until 1989"),
    "sri lanka": (1972, "the country is called Ceylon until 1972"),
    "zimbabwe": (1980, "the country is called Rhodesia until 1980"),
    "ho chi minh city": (1975, "the city is called Saigon until 1975"),
}

# term -> (last valid year, short reason). Flagged when an era postdates it.
LATEST: dict[str, tuple[int, str]] = {
    # --- states that ceased to exist ---
    "soviet union": (1991, "the USSR dissolves at the end of 1991"),
    "the ussr": (1991, "the USSR dissolves at the end of 1991"),
    "the kgb": (1991, "the KGB is dissolved in 1991"),
    "east germany": (1990, "the GDR is absorbed in 1990"),
    "west germany": (1990, "the two Germanys reunify in 1990"),
    "the gdr": (1990, "the GDR is absorbed in 1990"),
    "the stasi": (1990, "the Stasi is dissolved in 1990"),
    "czechoslovakia": (1992, "the federation splits at the end of 1992"),
    "zaire": (1997, "renamed the Democratic Republic of the Congo in 1997"),
    "rhodesia": (1980, "becomes Zimbabwe in 1980"),
    # --- place names superseded (the OLD name appearing too late) ---
    "leningrad": (1991, "renamed Saint Petersburg in 1991"),
    "bombay": (1995, "renamed Mumbai in 1995"),
    "madras": (1996, "renamed Chennai in 1996"),
    "calcutta": (2001, "renamed Kolkata in 2001"),
    "peking": (1979, "rendered Beijing in English after the pinyin shift"),
    "saigon": (1975, "renamed Ho Chi Minh City in 1975"),
    "burma": (1989, "renamed Myanmar in 1989"),
    "ceylon": (1972, "renamed Sri Lanka in 1972"),
}


def _matches(term: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE) is not None


def scan_anachronisms(text: str, year: int | None) -> list[str]:
    """Flag period-inconsistent terms in `text` for a scene set in `year`.

    Returns one short advisory line per hit. Empty when `year` is unknown (an era
    with no anchored year cannot be checked) or nothing trips. Advisory by design:
    the human gate decides, exactly as with every other check in the system.
    """
    if year is None:
        return []
    flags: list[str] = []
    for term, (earliest, reason) in EARLIEST.items():
        if year < earliest and _matches(term, text):
            flags.append(f'"{term}" in a {year} scene: {reason} (not until {earliest})')
    for term, (latest, reason) in LATEST.items():
        if year > latest and _matches(term, text):
            flags.append(f'"{term}" in a {year} scene: {reason}')
    return flags
