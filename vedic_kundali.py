#!/usr/bin/env python3
"""
Vedic Kundali Generator
=======================
Generates a North Indian style Janma Kundali (birth chart) using the
Swiss Ephemeris library for accurate planetary positions.

Usage:
    python vedic_kundali.py

Dependencies:
    pip install pyswisseph geopy timezonefinder pytz
"""

import swisseph as swe
import math
from datetime import datetime, timezone, timedelta
import os

# ─── Configuration ────────────────────────────────────────────────────────────

AYANAMSHA = swe.SIDM_LAHIRI   # Lahiri / Chitrapaksha (standard in India)

SIGNS_EN = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]
SIGNS_HI = [
    "Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya",
    "Tula","Vrishchika","Dhanus","Makara","Kumbha","Meena"
]
SIGNS_SHORT = ["Ar","Ta","Ge","Ca","Le","Vi","Li","Sc","Sa","Cp","Aq","Pi"]
SIGNS_HI_SHORT = ["मेष","वृष","मिथ","कर्क","सिंह","कन्या","तुला","वृश्चि","धनु","मकर","कुंभ","मीन"]
SIGNS_HI_FULL = [
    "मेष","वृषभ","मिथुन","कर्क",
    "सिंह","कन्या","तुला","वृश्चिक",
    "धनु","मकर","कुंभ","मीन"
]

PLANETS_SWE = {
    "Sun":     swe.SUN,
    "Moon":    swe.MOON,
    "Mars":    swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus":   swe.VENUS,
    "Saturn":  swe.SATURN,
}
PLANET_ABBR = {
    "Sun":"Su", "Moon":"Mo", "Mars":"Ma", "Mercury":"Me",
    "Jupiter":"Ju", "Venus":"Ve", "Saturn":"Sa", "Rahu":"Ra", "Ketu":"Ke"
}
PLANET_HI = {
    "Sun":"सू", "Moon":"चं", "Mars":"मं", "Mercury":"बु",
    "Jupiter":"गु", "Venus":"शु", "Saturn":"श", "Rahu":"रा", "Ketu":"के"
}

NAKSHATRAS = [
    ("Ashwini","Ketu"),("Bharani","Venus"),("Krittika","Sun"),
    ("Rohini","Moon"),("Mrigashira","Mars"),("Ardra","Rahu"),
    ("Punarvasu","Jupiter"),("Pushya","Saturn"),("Ashlesha","Mercury"),
    ("Magha","Ketu"),("Purva Phalguni","Venus"),("Uttara Phalguni","Sun"),
    ("Hasta","Moon"),("Chitra","Mars"),("Swati","Rahu"),
    ("Vishakha","Jupiter"),("Anuradha","Saturn"),("Jyeshtha","Mercury"),
    ("Mula","Ketu"),("Purva Ashadha","Venus"),("Uttara Ashadha","Sun"),
    ("Shravana","Moon"),("Dhanishtha","Mars"),("Shatabhisha","Rahu"),
    ("Purva Bhadrapada","Jupiter"),("Uttara Bhadrapada","Saturn"),("Revati","Mercury")
]

DASHA_SEQUENCE = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]
DASHA_YEARS    = {"Ketu":7,"Venus":20,"Sun":6,"Moon":10,"Mars":7,
                  "Rahu":18,"Jupiter":16,"Saturn":19,"Mercury":17}

# ─── Planet Strength Scorecard Data ──────────────────────────────────────────

# Exaltation signs (0-indexed)
EXALTATION = {
    "Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
    "Jupiter": 3, "Venus": 11, "Saturn": 6, "Rahu": 1, "Ketu": 7,
}
# Debilitation signs (0-indexed)
DEBILITATION = {
    "Sun": 6, "Moon": 7, "Mars": 3, "Mercury": 11,
    "Jupiter": 9, "Venus": 5, "Saturn": 0, "Rahu": 7, "Ketu": 1,
}
# Mulatrikona: planet -> (sign_idx, deg_start, deg_end)
MULATRIKONA = {
    "Sun": (4, 0, 20),      # Leo 0-20°
    "Moon": (1, 3, 30),      # Taurus 3-30°
    "Mars": (0, 0, 12),      # Aries 0-12°
    "Mercury": (5, 15, 20),  # Virgo 15-20°
    "Jupiter": (8, 0, 10),   # Sagittarius 0-10°
    "Venus": (6, 0, 15),     # Libra 0-15°
    "Saturn": (10, 0, 20),   # Aquarius 0-20°
}
# Own signs: planet -> list of sign indices it rules
OWN_SIGNS = {
    "Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5],
    "Jupiter": [8, 11], "Venus": [1, 6], "Saturn": [9, 10],
    "Rahu": [10], "Ketu": [7],
}
# Natural friendships (classical Vedic)
NATURAL_FRIENDS = {
    "Sun":     {"friends": ["Moon","Mars","Jupiter"], "enemies": ["Venus","Saturn"], "neutral": ["Mercury"]},
    "Moon":    {"friends": ["Sun","Mercury"], "enemies": [], "neutral": ["Mars","Jupiter","Venus","Saturn"]},
    "Mars":    {"friends": ["Sun","Moon","Jupiter"], "enemies": ["Mercury"], "neutral": ["Venus","Saturn"]},
    "Mercury": {"friends": ["Sun","Venus"], "enemies": ["Moon"], "neutral": ["Mars","Jupiter","Saturn"]},
    "Jupiter": {"friends": ["Sun","Moon","Mars"], "enemies": ["Mercury","Venus"], "neutral": ["Saturn"]},
    "Venus":   {"friends": ["Mercury","Saturn"], "enemies": ["Sun","Moon"], "neutral": ["Mars","Jupiter"]},
    "Saturn":  {"friends": ["Mercury","Venus"], "enemies": ["Sun","Moon","Mars"], "neutral": ["Jupiter"]},
    "Rahu":    {"friends": ["Venus","Saturn"], "enemies": ["Sun","Moon","Mars"], "neutral": ["Mercury","Jupiter"]},
    "Ketu":    {"friends": ["Mars","Jupiter"], "enemies": ["Venus","Saturn"], "neutral": ["Sun","Moon","Mercury"]},
}
# Combustion orbs in degrees from Sun. Tuple = (direct, retrograde)
COMBUSTION_ORBS = {
    "Moon": 12, "Mars": 17, "Mercury": (14, 12),
    "Jupiter": 11, "Venus": (10, 8), "Saturn": 15,
}
NATURAL_BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
NATURAL_MALEFICS = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}
# Special Vedic aspects (house offset from planet's position)
SPECIAL_ASPECTS = {
    "Mars": [4, 8],       # 4th and 8th house aspect
    "Jupiter": [5, 9],    # 5th and 9th house aspect
    "Saturn": [3, 10],    # 3rd and 10th house aspect
}
# Navamsha (D-9) starting signs by element
NAVAMSHA_START = {
    0: 0, 4: 0, 8: 0,    # Fire signs (Aries/Leo/Sag) → start from Aries
    1: 9, 5: 9, 9: 9,    # Earth signs (Tau/Vir/Cap) → start from Capricorn
    2: 6, 6: 6, 10: 6,   # Air signs (Gem/Lib/Aqu) → start from Libra
    3: 3, 7: 3, 11: 3,   # Water signs (Can/Sco/Pis) → start from Cancer
}
# House placement scores
HOUSE_SCORES = {1:20, 4:20, 7:20, 10:20, 5:18, 9:18,
                3:14, 6:14, 11:14, 2:12, 8:5, 12:5}
# Sign rulers (index-based) for dignity lookup
_SIGN_RULERS_IDX = ["Mars","Venus","Mercury","Moon","Sun","Mercury",
                    "Venus","Mars","Jupiter","Saturn","Saturn","Jupiter"]

# Hindi labels for strength display
DIGNITY_HI = {
    "Exalted": "उच्च", "Own Sign": "स्वराशि", "Mulatrikona": "मूलत्रिकोण",
    "Friendly": "मित्र राशि", "Neutral": "सम राशि",
    "Enemy": "शत्रु राशि", "Debilitated": "नीच",
}
MATURITY_LABELS = {
    "Infant": (0, 5), "Young": (5, 10), "Mature": (10, 20),
    "Old": (20, 25), "Aged": (25, 30),
}
MATURITY_SCORES = {"Infant": 4, "Young": 7, "Mature": 10, "Old": 7, "Aged": 4}
MATURITY_HI = {"Infant": "शिशु", "Young": "युवा", "Mature": "परिपक्व",
               "Old": "वृद्ध", "Aged": "जीर्ण"}
STRENGTH_LABELS_HI = {"Strong": "बलवान", "Moderate": "मध्यम", "Weak": "दुर्बल"}


def _get_sign_dignity(planet, sign_idx, deg):
    """Return (dignity_label, points) for a planet in a sign."""
    if sign_idx == EXALTATION.get(planet):
        return ("Exalted", 35)
    if sign_idx == DEBILITATION.get(planet):
        return ("Debilitated", 0)
    mt = MULATRIKONA.get(planet)
    if mt and sign_idx == mt[0] and mt[1] <= deg <= mt[2]:
        return ("Mulatrikona", 28)
    if sign_idx in OWN_SIGNS.get(planet, []):
        return ("Own Sign", 30)
    # Check friendship via sign ruler
    ruler = _SIGN_RULERS_IDX[sign_idx]
    fdata = NATURAL_FRIENDS.get(planet, {})
    if ruler in fdata.get("friends", []):
        return ("Friendly", 22)
    if ruler in fdata.get("enemies", []):
        return ("Enemy", 8)
    return ("Neutral", 15)


def _get_maturity(deg):
    """Return (maturity_label, points) for a degree within sign."""
    for label, (lo, hi) in MATURITY_LABELS.items():
        if lo <= deg < hi:
            return (label, MATURITY_SCORES[label])
    return ("Aged", 4)


def calculate_planet_strength(chart):
    """
    Calculate strength score (0-100) for each of 9 planets.
    Returns dict: { "Sun": {"score":72, "dignity":"Own Sign", ...}, ... }
    """
    planets = chart['planets']
    asc_sign = chart['asc_sign']
    sun_lon = planets['Sun']['lon']
    order = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]
    results = {}

    # Pre-compute house for each planet
    planet_houses = {}
    for pn in order:
        sidx = planets[pn]['sign_idx']
        planet_houses[pn] = (sidx - asc_sign) % 12 + 1

    for pname in order:
        p = planets[pname]
        sidx = p['sign_idx']
        deg = p['deg']
        house = planet_houses[pname]

        # 1. Sign Dignity (0-35)
        dignity_label, dignity_pts = _get_sign_dignity(pname, sidx, deg)

        # 2. House Placement (5-20)
        house_pts = HOUSE_SCORES.get(house, 10)

        # 3. Degree Maturity (4-10)
        maturity_label, maturity_pts = _get_maturity(deg)

        # 4. Combustion (-15 to 0)
        combustion_pts = 0
        is_combust = False
        if pname not in ("Sun", "Rahu", "Ketu") and pname in COMBUSTION_ORBS:
            orb_val = COMBUSTION_ORBS[pname]
            if isinstance(orb_val, tuple):
                orb = orb_val[1] if p['retro'] else orb_val[0]
            else:
                orb = orb_val
            diff = abs(p['lon'] - sun_lon)
            diff = min(diff, 360 - diff)
            if diff <= orb:
                combustion_pts = -15
                is_combust = True
            elif diff <= orb * 1.5:
                combustion_pts = -8

        # 5. Retrograde (±5, skip Rahu/Ketu)
        retro_pts = 0
        if p['retro'] and pname not in ("Rahu", "Ketu"):
            if pname in NATURAL_BENEFICS:
                retro_pts = -5
            else:
                retro_pts = 5

        # 6. Aspects received (-15 to +15)
        aspect_pts = 0
        for other in order:
            if other == pname:
                continue
            o_house = planet_houses[other]
            # Universal 7th aspect
            aspected_houses = [(o_house + 6) % 12 + 1]  # 7th from other
            # Special aspects
            for offset in SPECIAL_ASPECTS.get(other, []):
                aspected_houses.append((o_house + offset - 1) % 12 + 1)
            if house in aspected_houses:
                if other in NATURAL_BENEFICS:
                    aspect_pts += 5
                else:
                    aspect_pts -= 5
        aspect_pts = max(-15, min(15, aspect_pts))

        # 7. Conjunctions (-8 to +8)
        conj_pts = 0
        for other in order:
            if other == pname:
                continue
            if planets[other]['sign_idx'] == sidx:  # same sign
                if other in NATURAL_BENEFICS:
                    conj_pts += 4
                else:
                    conj_pts -= 4
        conj_pts = max(-8, min(8, conj_pts))

        # Final score
        raw = dignity_pts + house_pts + maturity_pts + combustion_pts + retro_pts + aspect_pts + conj_pts
        score = max(0, min(100, raw))
        overall = "Strong" if score >= 70 else ("Moderate" if score >= 40 else "Weak")

        results[pname] = {
            "score": score,
            "dignity": dignity_label, "dignity_pts": dignity_pts,
            "house": house, "house_pts": house_pts,
            "maturity": maturity_label, "maturity_pts": maturity_pts,
            "combustion_pts": combustion_pts, "is_combust": is_combust,
            "retro_pts": retro_pts,
            "aspect_pts": aspect_pts,
            "conj_pts": conj_pts,
            "overall": overall,
        }

    # ── Classify: Strengthen / Balance / Pacify ──
    # Functional benefics for each Lagna (lords of trikona 1,5,9 and kendra 1,4,7,10)
    # Functional malefics = lords of trishthana (6,8,12) and maraka (2,7)
    for pname in order:
        house = planet_houses[pname]
        sign_idx = planets[pname]['sign_idx']
        # Determine houses ruled by this planet
        ruled_houses = []
        for h in range(12):
            if _SIGN_RULERS_IDX[h] == pname or (
                _SIGN_RULERS_IDX[(asc_sign + h) % 12] == pname):
                pass
        # Simplified: use owned signs relative to lagna
        owns = OWN_SIGNS.get(pname, [])
        ruled = [(s - asc_sign) % 12 + 1 for s in owns]

        is_func_benefic = any(h in (1, 5, 9) for h in ruled)
        is_func_malefic = any(h in (6, 8, 12) for h in ruled)
        score = results[pname]['score']

        if is_func_benefic and score < 50:
            remedy = "Strengthen"
        elif is_func_malefic and score >= 50:
            remedy = "Pacify"
        elif is_func_malefic and score < 40:
            remedy = "Pacify"
        else:
            remedy = "Balance"

        results[pname]['remedy'] = remedy
        results[pname]['func_benefic'] = is_func_benefic
        results[pname]['func_malefic'] = is_func_malefic

    return results


REMEDY_HI = {"Strengthen": "बल बढ़ाएँ", "Balance": "संतुलित करें", "Pacify": "शांत करें"}
REMEDY_ICONS = {"Strengthen": "✅", "Balance": "⚖️", "Pacify": "⚠️"}


def _planet_strength_reading(pname, pdata, sinfo, lang="en"):
    """Generate a 2-3 sentence reading for a planet's strength."""
    score = sinfo['score']
    dignity = sinfo['dignity']
    maturity = sinfo['maturity']
    house = sinfo['house']
    overall = sinfo['overall']

    if lang == "hi":
        sign_name = SIGNS_HI_FULL[pdata['sign_idx']]
        dig_hi = DIGNITY_HI.get(dignity, dignity)
        mat_hi = MATURITY_HI.get(maturity, maturity)
        ovr_hi = STRENGTH_LABELS_HI.get(overall, overall)
        bhav_names = {1:"तनु",2:"धन",3:"सहज",4:"सुख",5:"पुत्र",6:"अरि",
                      7:"कलत्र",8:"रन्ध्र",9:"धर्म",10:"कर्म",11:"लाभ",12:"व्यय"}
        bhav = bhav_names.get(house, str(house))
        parts = [f"{sign_name} में {dig_hi} स्थिति में, भवन {house} ({bhav}) में स्थित।"]
        parts.append(f"{pdata['deg']:.0f}° पर {mat_hi} अवस्था।")
        if sinfo['is_combust']:
            parts.append("सूर्य से अस्त — प्रभाव में कमी।")
        if pdata['retro'] and pname not in ("Rahu", "Ketu"):
            parts.append("वक्री — अंतर्मुखी ऊर्जा।")
        remedy_hi = REMEDY_HI.get(sinfo.get('remedy', 'Balance'), 'संतुलित करें')
        icon = REMEDY_ICONS.get(sinfo.get('remedy', 'Balance'), '⚖️')
        parts.append(f"समग्र: {ovr_hi} ({score}/100)। {icon} {remedy_hi}।")
        return " ".join(parts)
    else:
        sign_name = pdata['sign_en']
        bhav_names = {1:"Tanu",2:"Dhana",3:"Sahaja",4:"Sukha",5:"Putra",6:"Ari",
                      7:"Kalatra",8:"Randhra",9:"Dharma",10:"Karma",11:"Labha",12:"Vyaya"}
        bhav = bhav_names.get(house, str(house))
        parts = [f"{dignity} in {sign_name}, placed in House {house} ({bhav})."]
        parts.append(f"At {pdata['deg']:.0f}°, in {maturity} phase.")
        if sinfo['is_combust']:
            parts.append("Combust (close to Sun) — effectiveness reduced.")
        if pdata['retro'] and pname not in ("Rahu", "Ketu"):
            if pname in NATURAL_BENEFICS:
                parts.append("Retrograde — blessings may be delayed but eventually strong.")
            else:
                parts.append("Retrograde — challenges intensify but bring hidden strength.")
        remedy = sinfo.get('remedy', 'Balance')
        icon = REMEDY_ICONS.get(remedy, '')
        parts.append(f"Overall: {overall} ({score}/100). {icon} {remedy}.")
        return " ".join(parts)


# ─── Bhava (House) Reading Engine ─────────────────────────────────────────────

BHAV_FULL_EN = {
    1: ("Tanu", "Self & Personality"),
    2: ("Dhana", "Wealth & Family"),
    3: ("Sahaja", "Siblings & Courage"),
    4: ("Sukha", "Happiness & Home"),
    5: ("Putra", "Children & Creativity"),
    6: ("Ari", "Enemies & Health"),
    7: ("Kalatra", "Marriage & Partnership"),
    8: ("Randhra", "Transformation & Longevity"),
    9: ("Dharma", "Fortune & Higher Wisdom"),
    10: ("Karma", "Career & Status"),
    11: ("Labha", "Gains & Networks"),
    12: ("Vyaya", "Loss & Spirituality"),
}

BHAV_FULL_HI = {
    1: ("तनु", "स्वयं एवं व्यक्तित्व"),
    2: ("धन", "धन एवं परिवार"),
    3: ("सहज", "भाई-बहन एवं साहस"),
    4: ("सुख", "सुख एवं गृह"),
    5: ("पुत्र", "संतान एवं रचनात्मकता"),
    6: ("अरि", "शत्रु एवं स्वास्थ्य"),
    7: ("कलत्र", "विवाह एवं साझेदारी"),
    8: ("रन्ध्र", "रूपांतरण एवं आयु"),
    9: ("धर्म", "भाग्य एवं उच्च ज्ञान"),
    10: ("कर्म", "कैरियर एवं प्रतिष्ठा"),
    11: ("लाभ", "लाभ एवं मित्र-मंडल"),
    12: ("व्यय", "हानि एवं आध्यात्मिकता"),
}

# What each house governs — used in readings
BHAV_GOVERNS_EN = {
    1: "your physical body, health, personality, first impressions, and how you approach life",
    2: "your wealth, family values, speech, food habits, and early education",
    3: "your siblings, courage, communication skills, short journeys, and self-effort",
    4: "your mother, home environment, emotional peace, vehicles, and property",
    5: "your children, intelligence, creativity, romance, past-life merit, and education",
    6: "your enemies, diseases, debts, daily struggles, service, and competition",
    7: "your spouse, marriage, business partnerships, public dealings, and legal matters",
    8: "your longevity, sudden events, inheritance, occult knowledge, and transformation",
    9: "your father, fortune, higher learning, dharma, long-distance travel, and guru",
    10: "your career, reputation, authority, government dealings, and public status",
    11: "your income, gains, elder siblings, social networks, and fulfilment of desires",
    12: "your expenses, foreign lands, moksha, isolation, spiritual growth, and hidden enemies",
}

BHAV_GOVERNS_HI = {
    1: "आपका शरीर, स्वास्थ्य, व्यक्तित्व, प्रथम प्रभाव और जीवन दृष्टिकोण",
    2: "आपका धन, पारिवारिक मूल्य, वाणी, भोजन और प्रारंभिक शिक्षा",
    3: "आपके भाई-बहन, साहस, संवाद कौशल, लघु यात्राएँ और पुरुषार्थ",
    4: "आपकी माता, घरेलू वातावरण, मानसिक शांति, वाहन और संपत्ति",
    5: "आपकी संतान, बुद्धि, रचनात्मकता, प्रेम, पूर्व जन्म के पुण्य और शिक्षा",
    6: "आपके शत्रु, रोग, ऋण, दैनिक संघर्ष, सेवा और प्रतिस्पर्धा",
    7: "आपका जीवनसाथी, विवाह, व्यापार साझेदारी और कानूनी मामले",
    8: "आपकी आयु, अचानक घटनाएँ, विरासत, गुप्त ज्ञान और रूपांतरण",
    9: "आपके पिता, भाग्य, उच्च शिक्षा, धर्म, लंबी यात्राएँ और गुरु",
    10: "आपका कैरियर, प्रतिष्ठा, अधिकार, सरकारी संबंध और सामाजिक स्थिति",
    11: "आपकी आय, लाभ, बड़े भाई-बहन, सामाजिक नेटवर्क और इच्छापूर्ति",
    12: "आपके व्यय, विदेश, मोक्ष, एकांत, आध्यात्मिक विकास और छिपे शत्रु",
}

# Planet effects when placed in a house — short phrases
PLANET_IN_HOUSE_EN = {
    "Sun": {
        "benefic": "brings leadership, confidence, and authority",
        "malefic": "may cause ego conflicts, health issues related to heat, and strained relations with authority",
    },
    "Moon": {
        "benefic": "brings emotional fulfilment, popularity, and mental peace",
        "malefic": "may cause emotional instability, mood swings, and mental restlessness",
    },
    "Mars": {
        "benefic": "brings energy, courage, and the drive to take action",
        "malefic": "may cause aggression, accidents, conflicts, and impulsive decisions",
    },
    "Mercury": {
        "benefic": "brings intelligence, communication skills, and analytical ability",
        "malefic": "may cause nervousness, indecision, and issues with speech or paperwork",
    },
    "Jupiter": {
        "benefic": "brings wisdom, expansion, blessings, and good fortune",
        "malefic": "may cause over-optimism, excess, or missed opportunities due to complacency",
    },
    "Venus": {
        "benefic": "brings beauty, comfort, romance, and artistic expression",
        "malefic": "may cause over-indulgence, relationship complications, or vanity",
    },
    "Saturn": {
        "benefic": "brings discipline, patience, long-term success through hard work",
        "malefic": "may cause delays, obstacles, hardship, and chronic issues",
    },
    "Rahu": {
        "benefic": "brings unconventional success, foreign connections, and material ambition",
        "malefic": "may cause obsession, confusion, illusions, and sudden disruptions",
    },
    "Ketu": {
        "benefic": "brings spiritual insight, detachment, and past-life wisdom",
        "malefic": "may cause disinterest, isolation, mysterious problems, and lack of direction",
    },
}

PLANET_IN_HOUSE_HI = {
    "Sun": {
        "benefic": "नेतृत्व, आत्मविश्वास और अधिकार प्रदान करता है",
        "malefic": "अहंकार, ताप संबंधी स्वास्थ्य समस्या और अधिकार से तनावपूर्ण संबंध हो सकते हैं",
    },
    "Moon": {
        "benefic": "भावनात्मक संतुष्टि, लोकप्रियता और मानसिक शांति देता है",
        "malefic": "भावनात्मक अस्थिरता, मनोदशा परिवर्तन और मानसिक बेचैनी हो सकती है",
    },
    "Mars": {
        "benefic": "ऊर्जा, साहस और कार्य करने की प्रेरणा देता है",
        "malefic": "आक्रामकता, दुर्घटना, विवाद और आवेगपूर्ण निर्णय हो सकते हैं",
    },
    "Mercury": {
        "benefic": "बुद्धि, संवाद कौशल और विश्लेषण क्षमता प्रदान करता है",
        "malefic": "घबराहट, अनिर्णय और वाणी या दस्तावेज़ी समस्याएँ हो सकती हैं",
    },
    "Jupiter": {
        "benefic": "ज्ञान, विस्तार, आशीर्वाद और शुभ भाग्य लाता है",
        "malefic": "अति-आशावाद, अतिरेक या आत्मसंतुष्टि से अवसर चूक सकते हैं",
    },
    "Venus": {
        "benefic": "सौंदर्य, सुख-सुविधा, प्रेम और कलात्मक अभिव्यक्ति देता है",
        "malefic": "अति-भोग, संबंधों में जटिलता या अहंकार हो सकता है",
    },
    "Saturn": {
        "benefic": "अनुशासन, धैर्य और कठोर परिश्रम से दीर्घकालिक सफलता देता है",
        "malefic": "विलंब, बाधाएँ, कष्ट और दीर्घकालिक समस्याएँ हो सकती हैं",
    },
    "Rahu": {
        "benefic": "अपरंपरागत सफलता, विदेशी संबंध और भौतिक महत्वाकांक्षा लाता है",
        "malefic": "जुनून, भ्रम, माया और अचानक व्यवधान हो सकते हैं",
    },
    "Ketu": {
        "benefic": "आध्यात्मिक अंतर्दृष्टि, वैराग्य और पूर्वजन्म का ज्ञान देता है",
        "malefic": "उदासीनता, एकांत, रहस्यमय समस्याएँ और दिशाहीनता हो सकती है",
    },
}

# ─── Navamsha (D-9) Interpretation Data ──────────────────────────────────────

# Navamsha Lagna interpretations (12 signs)
NAVAMSHA_LAGNA_EN = {
    0: "Aries Navamsha Lagna reveals a soul driven by initiative, courage, and pioneering spirit. Your inner nature is assertive and independent. Over time, you develop strong leadership qualities and a desire to forge new paths.",
    1: "Taurus Navamsha Lagna reveals a soul seeking stability, comfort, and material security. Your inner nature values beauty, loyalty, and steady growth. You develop patience and a deep appreciation for life's pleasures.",
    2: "Gemini Navamsha Lagna reveals a soul driven by intellectual curiosity and communication. Your inner nature is adaptable, witty, and versatile. You develop through knowledge, networking, and diverse experiences.",
    3: "Cancer Navamsha Lagna reveals a soul seeking emotional security and nurturing connections. Your inner nature is caring, intuitive, and deeply sensitive. You develop through family bonds and emotional wisdom.",
    4: "Leo Navamsha Lagna reveals a soul driven by creativity, self-expression, and leadership. Your inner nature is confident, generous, and dramatic. You develop through creative pursuits and inspiring others.",
    5: "Virgo Navamsha Lagna reveals a soul seeking perfection, service, and analytical clarity. Your inner nature is practical, detail-oriented, and health-conscious. You develop through service and self-improvement.",
    6: "Libra Navamsha Lagna reveals a soul driven by harmony, partnership, and aesthetic beauty. Your inner nature values balance, diplomacy, and fairness. You develop through relationships and artistic expression.",
    7: "Scorpio Navamsha Lagna reveals a soul driven by transformation, depth, and intensity. Your inner nature is powerful, researching, and secretive. You develop through crisis, rebirth, and uncovering hidden truths.",
    8: "Sagittarius Navamsha Lagna reveals a soul seeking wisdom, higher knowledge, and dharmic living. Your inner nature is philosophical, optimistic, and truth-seeking. You develop through travel, teaching, and spiritual growth.",
    9: "Capricorn Navamsha Lagna reveals a soul driven by ambition, discipline, and responsibility. Your inner nature is structured, hardworking, and goal-oriented. You develop through perseverance and building lasting achievements.",
    10: "Aquarius Navamsha Lagna reveals a soul seeking humanitarian ideals, innovation, and independence. Your inner nature is progressive, unconventional, and community-minded. You develop through social reform and original thinking.",
    11: "Pisces Navamsha Lagna reveals a soul driven by spirituality, compassion, and transcendence. Your inner nature is intuitive, imaginative, and deeply empathetic. You develop through devotion, art, and selfless service.",
}

NAVAMSHA_LAGNA_HI = {
    0: "मेष नवांश लग्न पहल, साहस और अग्रणी भावना से प्रेरित आत्मा को दर्शाता है। आपका आंतरिक स्वभाव दृढ़ और स्वतंत्र है। समय के साथ आप मजबूत नेतृत्व गुण विकसित करते हैं।",
    1: "वृषभ नवांश लग्न स्थिरता, आराम और भौतिक सुरक्षा चाहने वाली आत्मा को दर्शाता है। आपका आंतरिक स्वभाव सौंदर्य, वफादारी और स्थिर विकास को महत्व देता है।",
    2: "मिथुन नवांश लग्न बौद्धिक जिज्ञासा और संचार से प्रेरित आत्मा को दर्शाता है। आपका आंतरिक स्वभाव अनुकूलनशील, बुद्धिमान और बहुमुखी है।",
    3: "कर्क नवांश लग्न भावनात्मक सुरक्षा और पोषण संबंधों की तलाश करने वाली आत्मा को दर्शाता है। आपका आंतरिक स्वभाव देखभाल करने वाला, सहज और गहरा संवेदनशील है।",
    4: "सिंह नवांश लग्न रचनात्मकता, आत्म-अभिव्यक्ति और नेतृत्व से प्रेरित आत्मा को दर्शाता है। आपका आंतरिक स्वभाव आत्मविश्वासी, उदार और प्रभावशाली है।",
    5: "कन्या नवांश लग्न पूर्णता, सेवा और विश्लेषणात्मक स्पष्टता चाहने वाली आत्मा को दर्शाता है। आपका आंतरिक स्वभाव व्यावहारिक और विस्तार-उन्मुख है।",
    6: "तुला नवांश लग्न सद्भाव, साझेदारी और सौंदर्यात्मक सुंदरता से प्रेरित आत्मा को दर्शाता है। आपका आंतरिक स्वभाव संतुलन और कूटनीति को महत्व देता है।",
    7: "वृश्चिक नवांश लग्न परिवर्तन, गहराई और तीव्रता से प्रेरित आत्मा को दर्शाता है। आपका आंतरिक स्वभाव शक्तिशाली, गहन अनुसंधानी और रहस्यमय है।",
    8: "धनु नवांश लग्न ज्ञान, उच्च शिक्षा और धार्मिक जीवन चाहने वाली आत्मा को दर्शाता है। आपका आंतरिक स्वभाव दार्शनिक, आशावादी और सत्य-खोजी है।",
    9: "मकर नवांश लग्न महत्वाकांक्षा, अनुशासन और जिम्मेदारी से प्रेरित आत्मा को दर्शाता है। आपका आंतरिक स्वभाव संरचित, कर्मठ और लक्ष्य-उन्मुख है।",
    10: "कुंभ नवांश लग्न मानवतावादी आदर्शों, नवाचार और स्वतंत्रता चाहने वाली आत्मा को दर्शाता है। आपका आंतरिक स्वभाव प्रगतिशील और समुदाय-उन्मुख है।",
    11: "मीन नवांश लग्न आध्यात्मिकता, करुणा और उत्कर्ष से प्रेरित आत्मा को दर्शाता है। आपका आंतरिक स्वभाव सहज, कल्पनाशील और गहरा सहानुभूतिपूर्ण है।",
}

# 7th house of Navamsha - Marriage/Spouse indicators
NAVAMSHA_7TH_EN = {
    0: "Aries on the 7th house of Navamsha suggests a spouse who is assertive, energetic, and independent. The marriage dynamic involves initiative and passion. Your partner may have strong leadership qualities.",
    1: "Taurus on the 7th house of Navamsha suggests a spouse who is stable, loyal, and comfort-loving. The marriage is grounded in material security and sensual pleasures. Your partner values tradition.",
    2: "Gemini on the 7th house of Navamsha suggests a spouse who is communicative, intellectual, and versatile. The marriage thrives on mental stimulation and variety. Your partner may be youthful in spirit.",
    3: "Cancer on the 7th house of Navamsha suggests a spouse who is nurturing, emotional, and family-oriented. The marriage is deeply caring and protective. Your partner values emotional bonding.",
    4: "Leo on the 7th house of Navamsha suggests a spouse who is confident, creative, and generous. The marriage involves mutual respect and admiration. Your partner may have a commanding presence.",
    5: "Virgo on the 7th house of Navamsha suggests a spouse who is practical, analytical, and service-oriented. The marriage values organization and health. Your partner is detail-conscious and helpful.",
    6: "Libra on the 7th house of Navamsha suggests a spouse who is diplomatic, charming, and harmony-seeking. The marriage is balanced and aesthetically refined. Your partner values fairness and beauty.",
    7: "Scorpio on the 7th house of Navamsha suggests a spouse who is intense, passionate, and transformative. The marriage involves deep emotional bonding. Your partner has magnetic personality.",
    8: "Sagittarius on the 7th house of Navamsha suggests a spouse who is philosophical, adventurous, and optimistic. The marriage involves shared beliefs and exploration. Your partner values freedom.",
    9: "Capricorn on the 7th house of Navamsha suggests a spouse who is disciplined, ambitious, and responsible. The marriage is structured and goal-oriented. Your partner values commitment and status.",
    10: "Aquarius on the 7th house of Navamsha suggests a spouse who is progressive, independent, and humanitarian. The marriage is unconventional and friendship-based. Your partner values individuality.",
    11: "Pisces on the 7th house of Navamsha suggests a spouse who is spiritual, compassionate, and imaginative. The marriage involves deep soul connection and empathy. Your partner is intuitive and selfless.",
}

NAVAMSHA_7TH_HI = {
    0: "नवांश के 7वें भाव में मेष एक ऐसे जीवनसाथी का संकेत देता है जो दृढ़, ऊर्जावान और स्वतंत्र है। विवाह में पहल और जुनून शामिल है।",
    1: "नवांश के 7वें भाव में वृषभ एक स्थिर, वफादार और आराम-प्रेमी जीवनसाथी का संकेत देता है। विवाह भौतिक सुरक्षा पर आधारित है।",
    2: "नवांश के 7वें भाव में मिथुन एक संवादशील, बौद्धिक और बहुमुखी जीवनसाथी का संकेत देता है। विवाह मानसिक उत्तेजना पर पनपता है।",
    3: "नवांश के 7वें भाव में कर्क एक पोषण करने वाले, भावनात्मक और परिवार-उन्मुख जीवनसाथी का संकेत देता है।",
    4: "नवांश के 7वें भाव में सिंह एक आत्मविश्वासी, रचनात्मक और उदार जीवनसाथी का संकेत देता है।",
    5: "नवांश के 7वें भाव में कन्या एक व्यावहारिक, विश्लेषणात्मक और सेवा-उन्मुख जीवनसाथी का संकेत देता है।",
    6: "नवांश के 7वें भाव में तुला एक कूटनीतिक, आकर्षक और सामंजस्य-प्रेमी जीवनसाथी का संकेत देता है।",
    7: "नवांश के 7वें भाव में वृश्चिक एक तीव्र, भावुक और परिवर्तनकारी जीवनसाथी का संकेत देता है।",
    8: "नवांश के 7वें भाव में धनु एक दार्शनिक, साहसी और आशावादी जीवनसाथी का संकेत देता है।",
    9: "नवांश के 7वें भाव में मकर एक अनुशासित, महत्वाकांक्षी और जिम्मेदार जीवनसाथी का संकेत देता है।",
    10: "नवांश के 7वें भाव में कुंभ एक प्रगतिशील, स्वतंत्र और मानवतावादी जीवनसाथी का संकेत देता है।",
    11: "नवांश के 7वें भाव में मीन एक आध्यात्मिक, दयालु और कल्पनाशील जीवनसाथी का संकेत देता है।",
}

# Vargottama planet interpretations
VARGOTTAMA_EN = {
    "Sun": "Your Sun is Vargottama — your sense of authority, self-identity, and soul purpose is deeply confirmed. You carry natural leadership and clarity of purpose that strengthens with age.",
    "Moon": "Your Moon is Vargottama — your emotional nature and mental stability are exceptionally strong. You have a naturally settled mind and strong intuitive abilities.",
    "Mars": "Your Mars is Vargottama — your courage, energy, and drive are powerfully confirmed. You possess unwavering determination and physical vitality.",
    "Mercury": "Your Mercury is Vargottama — your intellect, communication skills, and analytical abilities are deeply confirmed. You excel in learning and articulation.",
    "Jupiter": "Your Jupiter is Vargottama — your wisdom, spirituality, and fortune are powerfully confirmed. You are blessed with genuine knowledge and dharmic guidance.",
    "Venus": "Your Venus is Vargottama — your capacity for love, beauty, and luxury is deeply confirmed. Relationships and artistic talents are naturally strong.",
    "Saturn": "Your Saturn is Vargottama — your discipline, perseverance, and karmic lessons are powerfully confirmed. You have extraordinary endurance and practical wisdom.",
    "Rahu": "Your Rahu is Vargottama — your worldly ambitions and desires are intensely focused. Material pursuits carry strong karmic momentum from past lives.",
    "Ketu": "Your Ketu is Vargottama — your spiritual detachment and past-life wisdom are deeply confirmed. You have natural inclination toward moksha and spiritual liberation.",
}

VARGOTTAMA_HI = {
    "Sun": "आपका सूर्य वर्गोत्तम है — आपकी अधिकार भावना, आत्म-पहचान और जीवन उद्देश्य गहराई से पुष्ट है। आप प्राकृतिक नेतृत्व और उद्देश्य की स्पष्टता रखते हैं।",
    "Moon": "आपका चन्द्र वर्गोत्तम है — आपका भावनात्मक स्वभाव और मानसिक स्थिरता असाधारण रूप से मजबूत है। आपके पास स्वाभाविक रूप से स्थिर मन है।",
    "Mars": "आपका मंगल वर्गोत्तम है — आपका साहस, ऊर्जा और संकल्प शक्तिशाली रूप से पुष्ट है। आप अटल दृढ़ संकल्प रखते हैं।",
    "Mercury": "आपका बुध वर्गोत्तम है — आपकी बुद्धि, संवाद कौशल और विश्लेषणात्मक क्षमताएं गहराई से पुष्ट हैं।",
    "Jupiter": "आपका गुरु वर्गोत्तम है — आपका ज्ञान, आध्यात्मिकता और भाग्य शक्तिशाली रूप से पुष्ट है।",
    "Venus": "आपका शुक्र वर्गोत्तम है — प्रेम, सौंदर्य और विलासिता की आपकी क्षमता गहराई से पुष्ट है।",
    "Saturn": "आपका शनि वर्गोत्तम है — आपका अनुशासन, दृढ़ता और कार्मिक सबक शक्तिशाली रूप से पुष्ट है।",
    "Rahu": "आपका राहु वर्गोत्तम है — आपकी सांसारिक महत्वाकांक्षाएं तीव्रता से केंद्रित हैं।",
    "Ketu": "आपका केतु वर्गोत्तम है — आपका आध्यात्मिक वैराग्य और पूर्व जन्म का ज्ञान गहराई से पुष्ट है।",
}


def generate_bhava_readings(chart, strength_data, lang="en"):
    """
    Generate a personalized reading for each of the 12 houses.
    Returns list of dicts: [{house_num, bhav, title, sign, reading_para}, ...]
    """
    planets = chart['planets']
    asc_sign = chart['asc_sign']  # 0-based index
    order = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]

    # Map planets to houses
    planet_in_house = {h: [] for h in range(1, 13)}
    for pname in order:
        sidx = planets[pname]['sign_idx']
        house = (sidx - asc_sign) % 12 + 1
        planet_in_house[house].append(pname)

    # House lord for each house
    def get_house_lord(house_num):
        sign_idx = (asc_sign + house_num - 1) % 12
        return _SIGN_RULERS_IDX[sign_idx]

    bhav_data = BHAV_FULL_HI if lang == "hi" else BHAV_FULL_EN
    governs = BHAV_GOVERNS_HI if lang == "hi" else BHAV_GOVERNS_EN
    planet_effects = PLANET_IN_HOUSE_HI if lang == "hi" else PLANET_IN_HOUSE_EN
    signs = SIGNS_HI_FULL if lang == "hi" else None

    readings = []
    for h in range(1, 13):
        bhav_name, bhav_title = bhav_data[h]
        sign_idx = (asc_sign + h - 1) % 12
        if lang == "hi":
            sign_name = SIGNS_HI_FULL[sign_idx]
        else:
            sign_name = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
                         "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"][sign_idx]

        lord = get_house_lord(h)
        lord_house = (planets[lord]['sign_idx'] - asc_sign) % 12 + 1
        lord_strength = strength_data.get(lord, {})
        lord_score = lord_strength.get('score', 50)
        lord_overall = lord_strength.get('overall', 'Moderate')

        plist = planet_in_house[h]

        # Build reading paragraph
        parts = []

        if lang == "hi":
            parts.append(f"भवन {h} ({bhav_name} — {bhav_title}) में {sign_name} राशि विराजमान है।")
            parts.append(f"यह भवन {governs[h]} को नियंत्रित करता है।")
            lord_hi = PLANET_HI_FULL.get(lord, lord)
            lord_ovr_hi = STRENGTH_LABELS_HI.get(lord_overall, lord_overall)
            lord_bhav_hi = BHAV_FULL_HI.get(lord_house, (str(lord_house), ""))[0]
            parts.append(f"इस भवन का स्वामी {lord_hi} है जो भवन {lord_house} ({lord_bhav_hi}) में स्थित है "
                         f"और {lord_ovr_hi} ({lord_score}/100) स्थिति में है।")

            if not plist:
                parts.append("इस भवन में कोई ग्रह स्थित नहीं है। फलाफल भवन स्वामी की स्थिति पर निर्भर करेगा।")
                if lord_score >= 70:
                    parts.append("भवन स्वामी बलवान होने से इस भवन के क्षेत्रों में शुभ परिणाम अपेक्षित हैं।")
                elif lord_score < 40:
                    parts.append("भवन स्वामी दुर्बल होने से इन क्षेत्रों में चुनौतियाँ संभव हैं।")
            else:
                for pname in plist:
                    pinfo = strength_data.get(pname, {})
                    pscore = pinfo.get('score', 50)
                    poverall = pinfo.get('overall', 'Moderate')
                    p_hi = PLANET_HI_FULL.get(pname, pname)
                    p_ovr_hi = STRENGTH_LABELS_HI.get(poverall, poverall)
                    effect_type = "benefic" if pscore >= 50 else "malefic"
                    effect = planet_effects.get(pname, {}).get(effect_type, "")
                    parts.append(f"{p_hi} ({p_ovr_hi}, {pscore}/100): {effect}।")

                # Overall house assessment
                avg_score = sum(strength_data.get(p, {}).get('score', 50) for p in plist) / len(plist)
                benefic_count = sum(1 for p in plist if p in NATURAL_BENEFICS)
                malefic_count = sum(1 for p in plist if p in NATURAL_MALEFICS)

                if avg_score >= 65 and benefic_count >= malefic_count:
                    parts.append("कुल मिलाकर यह भवन बहुत अनुकूल है — इन जीवन क्षेत्रों में सकारात्मक परिणाम अपेक्षित हैं।")
                elif avg_score >= 50:
                    parts.append("यह भवन संतुलित है — मिश्रित परिणाम संभव, सचेत प्रयास से लाभ होगा।")
                elif malefic_count > benefic_count:
                    parts.append("इस भवन में चुनौतियाँ अधिक हैं — धैर्य और उचित उपाय से सुधार संभव है।")

        else:  # English
            parts.append(f"House {h} ({bhav_name} — {bhav_title}) is occupied by {sign_name}.")
            parts.append(f"This house governs {governs[h]}.")
            lord_bhav = BHAV_FULL_EN.get(lord_house, (str(lord_house), ""))[0]
            parts.append(f"The lord of this house is {lord}, placed in House {lord_house} ({lord_bhav}), "
                         f"currently {lord_overall} ({lord_score}/100).")

            if not plist:
                parts.append("No planets occupy this house. Results depend primarily on the house lord's placement and strength.")
                if lord_score >= 70:
                    parts.append("With a strong house lord, favourable outcomes are expected in these life areas.")
                elif lord_score < 40:
                    parts.append("The house lord is weak, which may bring challenges in these areas. Remedies for the lord planet are recommended.")
            else:
                for pname in plist:
                    pinfo = strength_data.get(pname, {})
                    pscore = pinfo.get('score', 50)
                    poverall = pinfo.get('overall', 'Moderate')
                    effect_type = "benefic" if pscore >= 50 else "malefic"
                    effect = planet_effects.get(pname, {}).get(effect_type, "")
                    parts.append(f"{pname} ({poverall}, {pscore}/100): {effect}.")

                # Overall house assessment
                avg_score = sum(strength_data.get(p, {}).get('score', 50) for p in plist) / len(plist)
                benefic_count = sum(1 for p in plist if p in NATURAL_BENEFICS)
                malefic_count = sum(1 for p in plist if p in NATURAL_MALEFICS)

                if avg_score >= 65 and benefic_count >= malefic_count:
                    parts.append("Overall, this is a very favourable house — expect positive outcomes in these life areas.")
                elif avg_score >= 50:
                    parts.append("This house shows balanced energy — mixed results are likely, conscious effort will tip the balance favourably.")
                elif malefic_count > benefic_count:
                    parts.append("This house faces challenges — patience and appropriate remedies can bring improvement.")

        readings.append({
            "house": h,
            "bhav": bhav_name,
            "title": bhav_title,
            "sign": sign_name,
            "planets": plist,
            "lord": lord,
            "para": " ".join(parts),
        })

    return readings


def _draw_strength_bar_chart(strength_data):
    """Draw horizontal bar chart of planet scores using PIL. Returns BytesIO PNG."""
    from PIL import Image, ImageDraw, ImageFont
    import io

    W, H = 820, 480
    img = Image.new("RGB", (W, H), "#FFFDF5")
    draw = ImageDraw.Draw(img)

    # Use standard fonts (avoid Devanagari shaping issues in PIL)
    try:
        # Try system fonts that render Latin well
        _sys_fonts = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        font_path = None
        for fp in _sys_fonts:
            if os.path.exists(fp):
                font_path = fp
                break
        font_label = ImageFont.truetype(font_path, 16) if font_path else ImageFont.load_default()
        font_score = ImageFont.truetype(font_path, 14) if font_path else ImageFont.load_default()
        font_title = ImageFont.truetype(font_path, 20) if font_path else ImageFont.load_default()
        font_axis = ImageFont.truetype(font_path, 11) if font_path else ImageFont.load_default()
    except Exception:
        font_label = font_score = font_title = font_axis = ImageFont.load_default()

    # Title
    draw.text((W // 2, 20), "Planet Strength Visualization", fill="#8B0000",
              font=font_title, anchor="mt")

    # Chart area
    left_margin = 120
    right_margin = 60
    top = 55
    bar_area_w = W - left_margin - right_margin
    order = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]
    bar_h = 32
    gap = 10
    colors_map = {"Sun": "#B8860B", "Moon": "#1E5FAD", "Mars": "#CC0000",
                  "Mercury": "#1C7C3A", "Jupiter": "#E07000", "Venus": "#7B00CC",
                  "Saturn": "#1C1C8C", "Rahu": "#006400", "Ketu": "#8B3A00"}

    # Scale lines
    for pct in [0, 25, 50, 75, 100]:
        x = left_margin + int(bar_area_w * pct / 100)
        draw.line([(x, top - 5), (x, top + 9 * (bar_h + gap))], fill="#E0E0E0", width=1)
        draw.text((x, top + 9 * (bar_h + gap) + 5), str(pct), fill="#999",
                  font=font_axis, anchor="mt")

    for i, pname in enumerate(order):
        sinfo = strength_data[pname]
        score = sinfo['score']
        y = top + i * (bar_h + gap)

        # Planet label
        draw.text((left_margin - 10, y + bar_h // 2), pname,
                  fill=colors_map.get(pname, "#333"), font=font_label, anchor="rm")

        # Bar
        bar_w = int(bar_area_w * score / 100)
        if score >= 70:
            bar_color = "#4CAF50"  # green
        elif score >= 40:
            bar_color = "#FF9800"  # orange
        else:
            bar_color = "#F44336"  # red
        draw.rounded_rectangle(
            [(left_margin, y), (left_margin + bar_w, y + bar_h)],
            radius=4, fill=bar_color)

        # Score label
        draw.text((left_margin + bar_w + 8, y + bar_h // 2),
                  f"{score}", fill="#333", font=font_score, anchor="lm")

        # Overall + Remedy label
        remedy = sinfo.get('remedy', 'Balance')
        icon = REMEDY_ICONS.get(remedy, '')
        ovr = sinfo['overall']
        ovr_color = "#4CAF50" if ovr == "Strong" else ("#FF9800" if ovr == "Moderate" else "#F44336")
        draw.text((W - 15, y + bar_h // 2), f"{ovr} {icon}", fill=ovr_color,
                  font=font_axis, anchor="rm")

    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


# ─── Core Calculation ─────────────────────────────────────────────────────────

def local_to_ut(year, month, day, hour, minute, second, utc_offset_hours):
    """Convert local time to Universal Time (decimal hours)."""
    local_decimal = hour + minute/60 + second/3600
    ut_decimal    = local_decimal - utc_offset_hours
    # Handle day boundary
    if ut_decimal < 0:
        ut_decimal += 24
        day -= 1
    elif ut_decimal >= 24:
        ut_decimal -= 24
        day += 1
    return year, month, day, ut_decimal


def julian_day(year, month, day, ut_hours):
    """Calculate Julian Day Number using Swiss Ephemeris."""
    return swe.julday(year, month, day, ut_hours)


def sidereal_position(jd, planet_id):
    """Return sidereal longitude of a planet using Lahiri ayanamsha."""
    swe.set_sid_mode(AYANAMSHA)
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED
    pos, ret = swe.calc_ut(jd, planet_id, flags)
    lon = pos[0] % 360
    speed = pos[3]  # deg/day; negative = retrograde
    return lon, speed


def ascendant(jd, lat, lon_geo):
    """Calculate sidereal Lagna (Ascendant)."""
    swe.set_sid_mode(AYANAMSHA)
    houses, ascmc = swe.houses_ex(jd, lat, lon_geo, b'P', swe.FLG_SIDEREAL)
    # ascmc[0] = tropical ASC; apply ayanamsha manually if needed
    # houses_ex with FLG_SIDEREAL should give sidereal directly
    asc_sid = ascmc[0] % 360
    return asc_sid, houses


def sign_and_degree(longitude):
    """Return sign index (0-11), sign name, and degree within sign."""
    sign_idx = int(longitude / 30) % 12
    deg_in_sign = longitude % 30
    return sign_idx, SIGNS_EN[sign_idx], SIGNS_HI[sign_idx], deg_in_sign


def dms_str(deg):
    """Format decimal degrees as D°M'S\"."""
    d = int(deg)
    m = int((deg - d) * 60)
    s = int(((deg - d) * 60 - m) * 60)
    return f"{d:2d}°{m:02d}'{s:02d}\""


def nakshatra_info(moon_lon):
    """Return nakshatra name, lord, and pada for given longitude."""
    nak_idx = int(moon_lon * 27 / 360) % 27
    frac    = (moon_lon * 27 / 360) - int(moon_lon * 27 / 360)
    pada    = int(frac * 4) + 1
    name, lord = NAKSHATRAS[nak_idx]
    return name, lord, pada, nak_idx


def vimshottari_dasha(moon_lon, birth_date):
    """
    Calculate Vimshottari Dasha sequence from birth.
    Returns list of (lord, start_date, end_date, years).
    """
    nak_idx = int(moon_lon * 27 / 360) % 27
    _, lord  = NAKSHATRAS[nak_idx]
    # Fraction consumed in current nakshatra
    frac_in_nak = (moon_lon * 27 / 360) - int(moon_lon * 27 / 360)
    remaining_frac = 1.0 - frac_in_nak
    
    # Find starting dasha lord in sequence
    start_idx = DASHA_SEQUENCE.index(lord)
    
    # Build sequence
    dashas = []
    current_date = birth_date
    
    for i in range(9):
        idx  = (start_idx + i) % 9
        d_lord = DASHA_SEQUENCE[idx]
        yrs  = DASHA_YEARS[d_lord]
        if i == 0:
            actual_yrs = yrs * remaining_frac
        else:
            actual_yrs = yrs
        days = actual_yrs * 365.25
        end_date = current_date + timedelta(days=days)
        dashas.append((d_lord, current_date, end_date, actual_yrs))
        current_date = end_date
    
    return dashas


DASHA_TOTAL_YEARS = 120  # Sum of all Vimshottari dasha years

def antardasha(mahadasha_lord, maha_start, maha_duration_years):
    """
    Calculate Antardasha (Bhukti) sub-periods within a Mahadasha.
    Returns list of (lord, start_date, end_date, years).
    """
    start_idx = DASHA_SEQUENCE.index(mahadasha_lord)
    sub_periods = []
    current = maha_start
    for i in range(9):
        idx = (start_idx + i) % 9
        sub_lord = DASHA_SEQUENCE[idx]
        yrs = maha_duration_years * DASHA_YEARS[sub_lord] / DASHA_TOTAL_YEARS
        days = yrs * 365.25
        end = current + timedelta(days=days)
        sub_periods.append((sub_lord, current, end, yrs))
        current = end
    return sub_periods


def pratyantar_dasha(antar_lord, antar_start, antar_duration_years):
    """
    Calculate Pratyantar Dasha sub-sub-periods within an Antardasha.
    Returns list of (lord, start_date, end_date, years).
    """
    start_idx = DASHA_SEQUENCE.index(antar_lord)
    sub_periods = []
    current = antar_start
    for i in range(9):
        idx = (start_idx + i) % 9
        sub_lord = DASHA_SEQUENCE[idx]
        yrs = antar_duration_years * DASHA_YEARS[sub_lord] / DASHA_TOTAL_YEARS
        days = yrs * 365.25
        end = current + timedelta(days=days)
        sub_periods.append((sub_lord, current, end, yrs))
        current = end
    return sub_periods


# ─── Navamsha (D-9) Calculation ──────────────────────────────────────────────

def _navamsha_sign(lon):
    """Given sidereal longitude (0-360), return navamsha sign index (0-11)."""
    sign_idx = int(lon / 30) % 12
    deg_in_sign = lon % 30
    pada = min(int(deg_in_sign / (30.0 / 9)), 8)  # 0-8
    start = NAVAMSHA_START[sign_idx]
    return (start + pada) % 12


def calculate_navamsha(planets, asc_lon):
    """Compute Navamsha (D-9) positions for all planets and ascendant."""
    nav_asc_idx = _navamsha_sign(asc_lon)
    natal_asc_idx = int(asc_lon / 30) % 12

    navamsha_planets = {}
    vargottama_list = []

    for pname, pdata in planets.items():
        nav_idx = _navamsha_sign(pdata['lon'])
        is_varg = (pdata['sign_idx'] == nav_idx)
        if is_varg:
            vargottama_list.append(pname)
        navamsha_planets[pname] = {
            'nav_sign_idx': nav_idx,
            'nav_sign_en': SIGNS_EN[nav_idx],
            'nav_sign_hi': SIGNS_HI[nav_idx],
            'natal_sign_idx': pdata['sign_idx'],
            'natal_sign_en': pdata['sign_en'],
            'is_vargottama': is_varg,
            'deg': pdata['deg'],
            'retro': pdata['retro'],
        }

    # Build house-to-planets mapping from Nav Lagna
    nav_house_planets = {i: [] for i in range(1, 13)}
    for pname, ndata in navamsha_planets.items():
        h = (ndata['nav_sign_idx'] - nav_asc_idx) % 12 + 1
        nav_house_planets[h].append(pname)

    return {
        'nav_asc_sign_idx': nav_asc_idx,
        'nav_asc_sign_en': SIGNS_EN[nav_asc_idx],
        'nav_asc_sign_hi': SIGNS_HI[nav_asc_idx],
        'nav_asc_vargottama': (natal_asc_idx == nav_asc_idx),
        'navamsha_planets': navamsha_planets,
        'nav_house_planets': nav_house_planets,
        'vargottama_planets': vargottama_list,
    }


def generate_navamsha_reading(chart, strength_data, lang="en"):
    """Generate Navamsha reading as list of (heading, body_text) tuples."""
    navamsha = chart.get('navamsha')
    if not navamsha:
        return []

    readings = []
    nav_asc_idx = navamsha['nav_asc_sign_idx']

    # 1. Navamsha Lagna — Inner Nature
    if lang == "hi":
        lagna_text = NAVAMSHA_LAGNA_HI.get(nav_asc_idx, "")
        if navamsha['nav_asc_vargottama']:
            lagna_text += " लग्न वर्गोत्तम है — आपका बाहरी और आंतरिक स्वभाव एक ही राशि में है, जो आपके व्यक्तित्व को गहरा बल प्रदान करता है।"
        readings.append(("नवांश लग्न — आंतरिक स्वभाव", lagna_text))
    else:
        lagna_text = NAVAMSHA_LAGNA_EN.get(nav_asc_idx, "")
        if navamsha['nav_asc_vargottama']:
            lagna_text += " Your Ascendant is Vargottama — the outer personality and inner soul are aligned in the same sign, giving exceptional strength to your character."
        readings.append(("Navamsha Lagna — Inner Nature", lagna_text))

    # 2. Vargottama Planets
    varg_list = navamsha['vargottama_planets']
    if varg_list:
        if lang == "hi":
            heading = "वर्गोत्तम ग्रह"
            parts = []
            for pname in varg_list:
                txt = VARGOTTAMA_HI.get(pname, "")
                if txt:
                    parts.append(txt)
            readings.append((heading, "\n\n".join(parts) if parts else "कोई वर्गोत्तम ग्रह नहीं।"))
        else:
            heading = "Vargottama Planets"
            parts = []
            for pname in varg_list:
                txt = VARGOTTAMA_EN.get(pname, "")
                if txt:
                    parts.append(txt)
            readings.append((heading, "\n\n".join(parts) if parts else "No vargottama planets."))
    else:
        if lang == "hi":
            readings.append(("वर्गोत्तम ग्रह", "आपकी कुण्डली में कोई वर्गोत्तम ग्रह नहीं है। यह सामान्य है — अधिकांश कुण्डलियों में केवल एक या दो वर्गोत्तम ग्रह होते हैं।"))
        else:
            readings.append(("Vargottama Planets", "There are no vargottama planets in your chart. This is normal — most charts have only one or two vargottama planets, if any."))

    # 3. 7th House — Marriage & Partnership
    seventh_sign_idx = (nav_asc_idx + 6) % 12
    if lang == "hi":
        seventh_text = NAVAMSHA_7TH_HI.get(seventh_sign_idx, "")
        readings.append(("7वाँ भाव — विवाह एवं साझेदारी", seventh_text))
    else:
        seventh_text = NAVAMSHA_7TH_EN.get(seventh_sign_idx, "")
        readings.append(("7th House — Marriage & Partnership", seventh_text))

    # 4. Dignity Changes — D-1 vs D-9 (Enhanced table with Trend & Meaning)
    # Dignity ranking for trend calculation (higher = stronger)
    DIGNITY_RANK = {"Exalted": 6, "Mulatrikona": 5, "Own Sign": 4,
                    "Friendly": 3, "Neutral": 2, "Enemy": 1, "Debilitated": 0}

    # Trend and Meaning mappings based on dignity shift
    def _get_trend_meaning(pname, d1_dig, d9_dig, lang_code):
        r1 = DIGNITY_RANK.get(d1_dig, 2)
        r9 = DIGNITY_RANK.get(d9_dig, 2)
        diff = r9 - r1

        if diff >= 3:
            trend_en, trend_hi = "Improving", "सुधार"
            arrow = "↑"
        elif diff >= 1:
            trend_en, trend_hi = "Improving", "सुधार"
            arrow = "↑"
        elif diff == 0:
            trend_en, trend_hi = "Stable", "स्थिर"
            arrow = "→"
        elif diff >= -2:
            trend_en, trend_hi = "Softening", "मंदन"
            arrow = "↓"
        else:
            trend_en, trend_hi = "Challenging", "चुनौतीपूर्ण"
            arrow = "↓"

        # Override for specific strong shifts
        if d9_dig == "Exalted" and d1_dig not in ("Exalted", "Mulatrikona"):
            trend_en, trend_hi = "Strong", "प्रबल"
            arrow = "↑"
        if d9_dig == "Debilitated":
            trend_en, trend_hi = "Challenging", "चुनौतीपूर्ण"
            arrow = "↓"
        if d9_dig == "Own Sign" and d1_dig in ("Neutral", "Enemy", "Debilitated"):
            trend_en, trend_hi = "Strong", "प्रबल"
            arrow = "↑"

        # Per-planet meaning
        PLANET_MEANING_EN = {
            "Sun": {True: "Authority and confidence grow stronger over time",
                    False: "Self-identity needs conscious development", None: "Sense of self remains consistent"},
            "Moon": {True: "Emotional maturity grows strongly over time",
                     False: "Emotional stability needs nurturing", None: "Mental peace remains steady"},
            "Mars": {True: "Action power becomes refined and effective",
                     False: "Energy needs proper channeling", None: "Drive and courage remain consistent"},
            "Mercury": {True: "Communication improves with age",
                        False: "Analytical skills need sharpening", None: "Intellect remains balanced"},
            "Jupiter": {True: "Wisdom deepens significantly over time",
                        False: "Wisdom present early, needs effort to sustain", None: "Spiritual growth remains steady"},
            "Venus": {True: "Relationships and creativity flourish over time",
                      False: "Strong attraction early, becomes more balanced", None: "Artistic sensibilities remain stable"},
            "Saturn": {True: "Discipline and karmic rewards increase",
                       False: "Discipline required; results come with effort", None: "Perseverance remains consistent"},
            "Rahu": {True: "Material ambition increases significantly",
                     False: "Worldly desires need grounding", None: "Ambitions remain focused"},
            "Ketu": {True: "Spiritual depth intensifies over time",
                     False: "Spiritual tendencies need conscious cultivation", None: "Spiritual tendencies remain steady"},
        }
        PLANET_MEANING_HI = {
            "Sun": {True: "अधिकार और आत्मविश्वास समय के साथ मजबूत होता है",
                    False: "आत्म-पहचान को सचेत विकास की आवश्यकता", None: "आत्म-भावना स्थिर रहती है"},
            "Moon": {True: "भावनात्मक परिपक्वता समय के साथ बढ़ती है",
                     False: "भावनात्मक स्थिरता को पोषण की आवश्यकता", None: "मानसिक शांति स्थिर रहती है"},
            "Mars": {True: "कार्य शक्ति परिष्कृत और प्रभावी होती है",
                     False: "ऊर्जा को उचित दिशा की आवश्यकता", None: "साहस और संकल्प स्थिर रहता है"},
            "Mercury": {True: "संवाद कौशल उम्र के साथ सुधरता है",
                        False: "विश्लेषणात्मक कौशल को तीक्ष्ण करने की आवश्यकता", None: "बुद्धि संतुलित रहती है"},
            "Jupiter": {True: "ज्ञान समय के साथ गहरा होता है",
                        False: "ज्ञान पहले से है, बनाए रखने के लिए प्रयास आवश्यक", None: "आध्यात्मिक विकास स्थिर रहता है"},
            "Venus": {True: "संबंध और रचनात्मकता समय के साथ फलती-फूलती है",
                      False: "प्रारंभिक आकर्षण मजबूत, बाद में संतुलित", None: "कलात्मक संवेदनशीलता स्थिर रहती है"},
            "Saturn": {True: "अनुशासन और कार्मिक पुरस्कार बढ़ते हैं",
                       False: "अनुशासन आवश्यक; परिणाम प्रयास से आते हैं", None: "दृढ़ता स्थिर रहती है"},
            "Rahu": {True: "भौतिक महत्वाकांक्षा काफी बढ़ती है",
                     False: "सांसारिक इच्छाओं को आधार की आवश्यकता", None: "महत्वाकांक्षाएं केंद्रित रहती हैं"},
            "Ketu": {True: "आध्यात्मिक गहराई समय के साथ तीव्र होती है",
                     False: "आध्यात्मिक प्रवृत्तियों को सचेत विकास की आवश्यकता", None: "आध्यात्मिक प्रवृत्तियाँ स्थिर रहती हैं"},
        }

        if diff > 0:
            key = True
        elif diff < 0:
            key = False
        else:
            key = None

        if lang_code == "hi":
            meaning = PLANET_MEANING_HI.get(pname, {}).get(key, "")
            trend = trend_hi
        else:
            meaning = PLANET_MEANING_EN.get(pname, {}).get(key, "")
            trend = trend_en

        return arrow, trend, meaning

    if strength_data:
        order = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        nav_planets = navamsha['navamsha_planets']
        dignity_rows = []  # list of (planet, d1_dig, d9_dig, arrow, trend, meaning)
        for pname in order:
            if pname not in nav_planets:
                continue
            ndata = nav_planets[pname]
            natal_idx = ndata['natal_sign_idx']
            nav_idx = ndata['nav_sign_idx']
            deg = ndata['deg']
            d1_dignity, _ = _get_sign_dignity(pname, natal_idx, deg)
            d9_dignity, _ = _get_sign_dignity(pname, nav_idx, deg)
            arrow, trend, meaning = _get_trend_meaning(pname, d1_dignity, d9_dignity, lang)

            if lang == "hi":
                p_label = PLANET_HI_FULL.get(pname, pname)
                d1_label = DIGNITY_HI.get(d1_dignity, d1_dignity)
                d9_label = DIGNITY_HI.get(d9_dignity, d9_dignity)
            else:
                p_label = pname
                d1_label = d1_dignity
                d9_label = d9_dignity

            dignity_rows.append((p_label, d1_label, d9_label, arrow, trend, meaning))

        if dignity_rows:
            # Return as special "TABLE" type for rendering
            if lang == "hi":
                readings.append(("TABLE:गरिमा परिवर्तन — D-1 बनाम D-9", dignity_rows))
            else:
                readings.append(("TABLE:Dignity Changes — D-1 vs D-9", dignity_rows))

    return readings


# ─── Chart Drawing (Text + SVG) ───────────────────────────────────────────────

def generate_chart(birth_data):
    """
    Main function: compute chart and return dict of all data.
    
    birth_data = {
        'name': str,
        'year': int, 'month': int, 'day': int,
        'hour': int, 'minute': int, 'second': int,
        'utc_offset': float,   # e.g. 5.5 for IST
        'lat': float, 'lon': float,
        'place': str
    }
    """
    # 1. Convert to UT
    y, m, d, ut = local_to_ut(
        birth_data['year'], birth_data['month'], birth_data['day'],
        birth_data['hour'], birth_data['minute'], birth_data['second'],
        birth_data['utc_offset']
    )
    jd = julian_day(y, m, d, ut)
    
    # 2. Ascendant
    asc_lon, houses = ascendant(jd, birth_data['lat'], birth_data['lon'])
    asc_sign, asc_sign_en, asc_sign_hi, asc_deg = sign_and_degree(asc_lon)
    
    # 3. Planets
    planets = {}
    for name, pid in PLANETS_SWE.items():
        lon, speed = sidereal_position(jd, pid)
        s_idx, s_en, s_hi, deg = sign_and_degree(lon)
        retro = speed < 0
        planets[name] = {
            'lon': lon, 'sign_idx': s_idx, 'sign_en': s_en,
            'sign_hi': s_hi, 'deg': deg, 'retro': retro, 'speed': speed
        }
    
    # 4. Rahu / Ketu (True Node)
    rahu_lon, rahu_speed = sidereal_position(jd, swe.TRUE_NODE)
    ketu_lon = (rahu_lon + 180) % 360
    r_idx, r_en, r_hi, r_deg = sign_and_degree(rahu_lon)
    k_idx, k_en, k_hi, k_deg = sign_and_degree(ketu_lon)
    planets['Rahu'] = {'lon': rahu_lon, 'sign_idx': r_idx, 'sign_en': r_en,
                       'sign_hi': r_hi, 'deg': r_deg, 'retro': True, 'speed': rahu_speed}
    planets['Ketu'] = {'lon': ketu_lon, 'sign_idx': k_idx, 'sign_en': k_en,
                       'sign_hi': k_hi, 'deg': k_deg, 'retro': True, 'speed': 0}
    
    # 5. Nakshatra
    moon_lon = planets['Moon']['lon']
    nak_name, nak_lord, nak_pada, nak_idx = nakshatra_info(moon_lon)
    
    # 6. House placements (whole-sign equal house from Lagna)
    # Use sign indices — avoids the off-by-one that raw degree arithmetic causes
    # when planet and lagna are in different parts of their signs.
    house_planets = {i: [] for i in range(1, 13)}
    for pname, pdata in planets.items():
        h = (pdata['sign_idx'] - asc_sign) % 12 + 1
        house_planets[h].append(pname)
    
    # 7. Vimshottari Dasha
    birth_dt = datetime(birth_data['year'], birth_data['month'], birth_data['day'],
                        birth_data['hour'], birth_data['minute'])
    dashas = vimshottari_dasha(moon_lon, birth_dt)

    # 8. Antardasha and Pratyantar Dasha for each Mahadasha
    today = datetime.now()
    all_antardasha = {}
    all_pratyantar = {}
    for maha_lord, maha_start, maha_end, maha_yrs in dashas:
        ad_list = antardasha(maha_lord, maha_start, maha_yrs)
        all_antardasha[maha_lord] = ad_list
        for ad_lord, ad_start, ad_end, ad_yrs in ad_list:
            key = (maha_lord, ad_lord)
            pd_list = pratyantar_dasha(ad_lord, ad_start, ad_yrs)
            all_pratyantar[key] = pd_list

    # 9. Navamsha (D-9) chart
    navamsha = calculate_navamsha(planets, asc_lon)

    # 10. Sade Sati
    sade_sati = calculate_sade_sati(planets['Moon']['sign_idx'], birth_data['year'])

    return {
        'birth_data': birth_data,
        'jd': jd,
        'asc_lon': asc_lon, 'asc_sign': asc_sign, 'asc_sign_en': asc_sign_en,
        'asc_sign_hi': asc_sign_hi, 'asc_deg': asc_deg,
        'planets': planets,
        'house_planets': house_planets,
        'nakshatra': nak_name, 'nak_lord': nak_lord, 'nak_pada': nak_pada,
        'dashas': dashas,
        'antardasha': all_antardasha,
        'pratyantar': all_pratyantar,
        'moon_rashi': planets['Moon']['sign_en'],
        'moon_rashi_hi': planets['Moon']['sign_hi'],
        'navamsha': navamsha,
        'sade_sati': sade_sati,
    }


# ─── Text Output ──────────────────────────────────────────────────────────────

def print_chart(chart):
    bd = chart['birth_data']
    planets = chart['planets']

    asc_sign  = chart['asc_sign']                      # 0-based lagna sign index
    moon_sign = planets['Moon']['sign_idx']             # 0-based moon sign index

    width = 72
    print("\n" + "═"*width)
    print(f"  JANMA KUNDALI — {bd['name'].upper()}")
    print("═"*width)
    print(f"  Date  : {bd['day']:02d}/{bd['month']:02d}/{bd['year']}")
    print(f"  Time  : {bd['hour']:02d}:{bd['minute']:02d} IST")
    print(f"  Place : {bd['place']}")
    print("─"*width)
    print(f"  Lagna (Ascendant) : {chart['asc_sign_en']} ({chart['asc_sign_hi']}) "
          f"— {dms_str(chart['asc_deg'])}")
    print(f"  Rashi (Moon sign) : {chart['moon_rashi']} ({chart['moon_rashi_hi']})")
    print(f"  Nakshatra         : {chart['nakshatra']}, Pada {chart['nak_pada']} "
          f"(Lord: {chart['nak_lord']})")
    print("─"*width)

    # Column header
    print(f"  {'Graha':<10} {'Sign (Rashi)':<22} {'Degree':<12} "
          f"{'Rashi#':<8} {'H/Lagna':<9} {'H/Moon':<8} {'R'}")
    print("─"*width)

    order = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]
    for pname in order:
        p      = planets[pname]
        sidx   = p['sign_idx']
        rashi  = sidx + 1                              # 1=Aries … 12=Pisces
        h_lag  = (sidx - asc_sign)  % 12 + 1          # house from Lagna
        h_moon = (sidx - moon_sign) % 12 + 1          # house from Moon
        retro  = "℞" if p['retro'] else " "
        sign_str = f"{p['sign_en']} ({p['sign_hi']})"
        print(f"  {pname:<10} {sign_str:<22} {dms_str(p['deg']):<12} "
              f"  {rashi:<6}   H{h_lag:<7} H{h_moon:<6}{retro}")

    print("─"*width)
    print(f"  Rashi# = zodiac cell (Aries=1…Pisces=12, matches chart cell labels)")
    print(f"  H/Lagna = house from Lagna ({chart['asc_sign_en']})  |  "
          f"H/Moon = house from Moon ({chart['moon_rashi']})")
    print("─"*width)

    print("\n  VIMSHOTTARI DASHA (Mahadasha):")
    print(f"  {'Lord':<12} {'Start':<14} {'End':<14} {'Years'}")
    print("  " + "─"*52)
    today = datetime.now()
    current_maha = None
    for lord, start, end, yrs in chart['dashas']:
        marker = " ◄ NOW" if start <= today < end else ""
        if start <= today < end:
            current_maha = lord
        print(f"  {lord:<12} {start.strftime('%b %Y'):<14} {end.strftime('%b %Y'):<14} "
              f"{yrs:.1f}{marker}")

    # ── Antardasha for current Mahadasha ──
    if current_maha and current_maha in chart.get('antardasha', {}):
        print("\n  " + "─"*width)
        print(f"\n  VIMSHOTTARI DASHA: Antardasha (within {current_maha} Mahadasha):")
        print(f"  {'Lord':<12} {'Start':<16} {'End':<16} {'Duration'}")
        print("  " + "─"*56)
        current_antar = None
        for ad_lord, ad_start, ad_end, ad_yrs in chart['antardasha'][current_maha]:
            marker = " ◄ NOW" if ad_start <= today < ad_end else ""
            if ad_start <= today < ad_end:
                current_antar = ad_lord
            months = ad_yrs * 12
            if months >= 12:
                dur_str = f"{ad_yrs:.1f}y"
            else:
                dur_str = f"{months:.1f}m"
            print(f"  {ad_lord:<12} {ad_start.strftime('%d %b %Y'):<16} "
                  f"{ad_end.strftime('%d %b %Y'):<16} {dur_str}{marker}")

        # ── Pratyantar for current Antardasha ──
        if current_antar:
            key = (current_maha, current_antar)
            if key in chart.get('pratyantar', {}):
                print("\n  " + "─"*width)
                print(f"\n  VIMSHOTTARI DASHA: Pratyantar "
                      f"(within {current_maha}-{current_antar}):")
                print(f"  {'Lord':<12} {'Start':<16} {'End':<16} {'Duration'}")
                print("  " + "─"*56)
                for pd_lord, pd_start, pd_end, pd_yrs in chart['pratyantar'][key]:
                    marker = " ◄ NOW" if pd_start <= today < pd_end else ""
                    days = pd_yrs * 365.25
                    if days >= 30:
                        dur_str = f"{pd_yrs*12:.1f}m"
                    else:
                        dur_str = f"{days:.0f}d"
                    print(f"  {pd_lord:<12} {pd_start.strftime('%d %b %Y'):<16} "
                          f"{pd_end.strftime('%d %b %Y'):<16} {dur_str}{marker}")

    print("═"*width + "\n")


# ─── SVG North Indian Chart ───────────────────────────────────────────────────

def generate_svg(chart, output_path="kundali_chart.svg"):
    """
    Generate a North Indian style Janma Kundali as an SVG file.

    Layout convention: H1 (Lagna) at LEFT — matching ParasharPatrika /
    most Indian astrology software.  Houses run clockwise:
      LEFT=1, BOTTOM-LEFT=2, BOTTOM=3, BOTTOM-RIGHT=4,
      RIGHT=5, TOP-RIGHT=6, TOP=7, TOP-LEFT=8,
      INNER-BOTTOM-LEFT=9, INNER-BOTTOM-RIGHT=10,
      INNER-TOP-RIGHT=11, INNER-TOP-LEFT=12
    """

    asc_sign = chart['asc_sign']   # 0-11
    planets  = chart['planets']
    bd       = chart['birth_data']

    W, H_SVG = 620, 660
    # Chart grid origin and half-size
    ox, oy = 60, 60          # top-left corner of outer rect
    gw, gh = 500, 500        # grid width / height
    cx = ox + gw // 2        # 310
    cy = oy + gh // 2        # 310

    # ── Cell centres (H1=LEFT, clockwise) ──────────────────────
    #  Outer 8 cells + 4 inner triangles
    cell_centers = {
        1:  (ox + 60,          cy),              # LEFT diamond
        2:  (ox + 90,          oy + gh - 80),    # BOTTOM-LEFT tri
        3:  (cx,               oy + gh - 60),    # BOTTOM diamond
        4:  (ox + gw - 90,     oy + gh - 80),    # BOTTOM-RIGHT tri
        5:  (ox + gw - 60,     cy),              # RIGHT diamond
        6:  (ox + gw - 90,     oy + 80),         # TOP-RIGHT tri
        7:  (cx,               oy + 60),         # TOP diamond
        8:  (ox + 90,          oy + 80),         # TOP-LEFT tri
        9:  (cx - 90,          cy + 70),         # INNER BOTTOM-LEFT
        10: (cx + 90,          cy + 70),         # INNER BOTTOM-RIGHT
        11: (cx + 90,          cy - 70),         # INNER TOP-RIGHT
        12: (cx - 90,          cy - 70),         # INNER TOP-LEFT
    }

    # Which sign goes in each cell? H1=Lagna sign, clockwise
    cell_sign = {h: (asc_sign + h - 1) % 12 for h in range(1, 13)}

    # Group planet names by sign index
    sign_planets = {i: [] for i in range(12)}
    for pname, pdata in planets.items():
        sign_planets[pdata['sign_idx']].append(pname)

    PLANET_COLORS = {
        "Sun":     "#B8860B",   # dark goldenrod
        "Moon":    "#1E5FAD",   # royal blue
        "Mars":    "#CC0000",   # red
        "Mercury": "#1C7C3A",   # green
        "Jupiter": "#E07000",   # orange
        "Venus":   "#7B00CC",   # purple
        "Saturn":  "#1C1C8C",   # dark blue
        "Rahu":    "#006400",   # dark green
        "Ketu":    "#8B3A00",   # dark brown
    }

    svg = []
    svg.append(f'<svg width="{W}" height="{H_SVG}" viewBox="0 0 {W} {H_SVG}" '
               f'xmlns="http://www.w3.org/2000/svg" font-family="Arial,sans-serif">')
    svg.append(f'<rect width="{W}" height="{H_SVG}" fill="#fffdf5"/>')

    # ── Title ───────────────────────────────────────────────────
    svg.append(f'<text x="{W//2}" y="30" text-anchor="middle" '
               f'font-size="17" font-weight="bold" fill="#8B0000">जन्म कुण्डली</text>')
    svg.append(f'<text x="{W//2}" y="48" text-anchor="middle" '
               f'font-size="12" fill="#444">{bd["name"]}</text>')
    svg.append(f'<text x="{W//2}" y="63" text-anchor="middle" '
               f'font-size="10" fill="#777">'
               f'{bd["day"]:02d}/{bd["month"]:02d}/{bd["year"]}  '
               f'{bd["hour"]:02d}:{bd["minute"]:02d} IST  ·  {bd["place"]}</text>')

    # ── Grid lines ──────────────────────────────────────────────
    # Outer rectangle
    svg.append(f'<rect x="{ox}" y="{oy+20}" width="{gw}" height="{gh}" '
               f'fill="#FFFEF5" stroke="#8B6914" stroke-width="1.5"/>')
    # Diagonals
    svg.append(f'<line x1="{ox}" y1="{oy+20}" x2="{ox+gw}" y2="{oy+20+gh}" '
               f'stroke="#8B6914" stroke-width="0.8"/>')
    svg.append(f'<line x1="{ox+gw}" y1="{oy+20}" x2="{ox}" y2="{oy+20+gh}" '
               f'stroke="#8B6914" stroke-width="0.8"/>')
    # Horizontal mid
    svg.append(f'<line x1="{ox}" y1="{oy+20+gh//2}" x2="{ox+gw}" y2="{oy+20+gh//2}" '
               f'stroke="#8B6914" stroke-width="0.8"/>')
    # Vertical mid
    svg.append(f'<line x1="{ox+gw//2}" y1="{oy+20}" x2="{ox+gw//2}" y2="{oy+20+gh}" '
               f'stroke="#8B6914" stroke-width="0.8"/>')

    # Recalculate actual cy after the +20 offset
    acy = oy + 20 + gh // 2   # actual vertical centre of grid = 330

    cell_centers = {
        1:  (ox + 62,          acy),             # LEFT diamond
        2:  (ox + 95,          oy+20+gh - 82),   # BOTTOM-LEFT tri
        3:  (ox+gw//2,         oy+20+gh - 58),   # BOTTOM diamond
        4:  (ox+gw - 95,       oy+20+gh - 82),   # BOTTOM-RIGHT tri
        5:  (ox+gw - 62,       acy),             # RIGHT diamond
        6:  (ox+gw - 95,       oy+20 + 82),      # TOP-RIGHT tri
        7:  (ox+gw//2,         oy+20 + 58),      # TOP diamond
        8:  (ox + 95,          oy+20 + 82),      # TOP-LEFT tri
        9:  (ox+gw//2 - 92,    acy + 72),        # INNER BOTTOM-LEFT
        10: (ox+gw//2 + 92,    acy + 72),        # INNER BOTTOM-RIGHT
        11: (ox+gw//2 + 92,    acy - 72),        # INNER TOP-RIGHT
        12: (ox+gw//2 - 92,    acy - 72),        # INNER TOP-LEFT
    }

    # ── Lagna marker on H1 cell (LEFT) ─────────────────────────
    lx, ly = cell_centers[1]
    svg.append(f'<polygon points="{lx-10},{ly-28} {lx+50},{ly} {lx-10},{ly+28}" '
               f'fill="#FFF3C4" stroke="#C8922A" stroke-width="1"/>')

    # ── Place sign name, house number, and planets in each cell ─
    for h in range(1, 13):
        s_idx = cell_sign[h]
        px, py_c = cell_centers[h]

        # House number (small, muted)
        svg.append(f'<text x="{px}" y="{py_c - 24}" text-anchor="middle" '
                   f'font-size="9" fill="#AAAAAA">{h}</text>')

        # Sign name (Hindi, small)
        svg.append(f'<text x="{px}" y="{py_c - 10}" text-anchor="middle" '
                   f'font-size="9" fill="#666666">{SIGNS_HI[s_idx]}</text>')

        # Lagna label on H1
        if h == 1:
            svg.append(f'<text x="{px - 18}" y="{py_c + 4}" text-anchor="middle" '
                       f'font-size="8" fill="#8B0000" font-weight="bold">ल</text>')

        # Planets
        plist = sign_planets[s_idx]
        for i, pname in enumerate(plist):
            pdata = planets[pname]
            abbr  = PLANET_HI.get(pname, pname[:2])
            deg   = int(pdata['deg'])
            retro = "ᵛ" if pdata['retro'] else ""
            col   = PLANET_COLORS.get(pname, "#333")
            yp    = py_c + 8 + i * 17
            svg.append(
                f'<text x="{px}" y="{yp}" text-anchor="middle" '
                f'font-size="14" font-weight="bold" fill="{col}">'
                f'{abbr}{retro}'
                f'<tspan font-size="8" baseline-shift="super">{deg}</tspan>'
                f'</text>'
            )

    # ── Footer ──────────────────────────────────────────────────
    fy = oy + 20 + gh + 30
    svg.append(f'<text x="{W//2}" y="{fy}" text-anchor="middle" '
               f'font-size="10" fill="#555">'
               f'लग्न: {chart["asc_sign_hi"]} {dms_str(chart["asc_deg"])}  ·  '
               f'राशि: {chart["moon_rashi_hi"]}  ·  '
               f'नक्षत्र: {chart["nakshatra"]} पद {chart["nak_pada"]} '
               f'({chart["nak_lord"]})</text>')
    svg.append(f'<text x="{W//2}" y="{fy+16}" text-anchor="middle" '
               f'font-size="8" fill="#AAAAAA">'
               f'Lahiri Ayanamsha  ·  Swiss Ephemeris</text>')

    svg.append('</svg>')

    svg_content = "\n".join(svg)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"  SVG chart saved: {output_path}")
    return svg_content


def generate_svg_string(chart):
    """Generate SVG chart as a string (no file I/O). Used by the web app."""
    # Reuse generate_svg logic but capture the string before file write.
    # We build the SVG inline here to avoid writing to disk.
    asc_sign = chart['asc_sign']
    planets  = chart['planets']
    bd       = chart['birth_data']

    W, H_SVG = 620, 660
    ox, oy = 60, 60
    gw, gh = 500, 500
    cx = ox + gw // 2
    cy = oy + gh // 2

    svg = []
    svg.append(f'<svg width="{W}" height="{H_SVG}" viewBox="0 0 {W} {H_SVG}" '
               f'xmlns="http://www.w3.org/2000/svg" font-family="Arial,sans-serif">')
    svg.append(f'<rect width="{W}" height="{H_SVG}" fill="#fffdf5"/>')

    svg.append(f'<text x="{W//2}" y="30" text-anchor="middle" '
               f'font-size="17" font-weight="bold" fill="#8B0000">'
               f'जन्म कुण्डली</text>')
    svg.append(f'<text x="{W//2}" y="48" text-anchor="middle" '
               f'font-size="12" fill="#444">{bd["name"]}</text>')
    svg.append(f'<text x="{W//2}" y="63" text-anchor="middle" '
               f'font-size="10" fill="#777">'
               f'{bd["day"]:02d}/{bd["month"]:02d}/{bd["year"]}  '
               f'{bd["hour"]:02d}:{bd["minute"]:02d}  ·  {bd["place"]}</text>')

    # Grid
    svg.append(f'<rect x="{ox}" y="{oy+20}" width="{gw}" height="{gh}" '
               f'fill="#FFFEF5" stroke="#8B6914" stroke-width="1.5"/>')
    svg.append(f'<line x1="{ox}" y1="{oy+20}" x2="{ox+gw}" y2="{oy+20+gh}" '
               f'stroke="#8B6914" stroke-width="0.8"/>')
    svg.append(f'<line x1="{ox+gw}" y1="{oy+20}" x2="{ox}" y2="{oy+20+gh}" '
               f'stroke="#8B6914" stroke-width="0.8"/>')
    svg.append(f'<line x1="{ox}" y1="{oy+20+gh//2}" x2="{ox+gw}" y2="{oy+20+gh//2}" '
               f'stroke="#8B6914" stroke-width="0.8"/>')
    svg.append(f'<line x1="{ox+gw//2}" y1="{oy+20}" x2="{ox+gw//2}" y2="{oy+20+gh}" '
               f'stroke="#8B6914" stroke-width="0.8"/>')

    acy = oy + 20 + gh // 2

    cell_centers = {
        1:  (ox + 62,          acy),
        2:  (ox + 95,          oy+20+gh - 82),
        3:  (ox+gw//2,         oy+20+gh - 58),
        4:  (ox+gw - 95,       oy+20+gh - 82),
        5:  (ox+gw - 62,       acy),
        6:  (ox+gw - 95,       oy+20 + 82),
        7:  (ox+gw//2,         oy+20 + 58),
        8:  (ox + 95,          oy+20 + 82),
        9:  (ox+gw//2 - 92,    acy + 72),
        10: (ox+gw//2 + 92,    acy + 72),
        11: (ox+gw//2 + 92,    acy - 72),
        12: (ox+gw//2 - 92,    acy - 72),
    }

    cell_sign = {h: (asc_sign + h - 1) % 12 for h in range(1, 13)}

    sign_planets = {i: [] for i in range(12)}
    for pname, pdata in planets.items():
        sign_planets[pdata['sign_idx']].append(pname)

    PLANET_COLORS = {
        "Sun":"#B8860B", "Moon":"#1E5FAD", "Mars":"#CC0000", "Mercury":"#1C7C3A",
        "Jupiter":"#E07000", "Venus":"#7B00CC", "Saturn":"#1C1C8C",
        "Rahu":"#006400", "Ketu":"#8B3A00",
    }

    # Lagna marker
    lx, ly = cell_centers[1]
    svg.append(f'<polygon points="{lx-10},{ly-28} {lx+50},{ly} {lx-10},{ly+28}" '
               f'fill="#FFF3C4" stroke="#C8922A" stroke-width="1"/>')

    for h in range(1, 13):
        s_idx = cell_sign[h]
        px, py_c = cell_centers[h]
        svg.append(f'<text x="{px}" y="{py_c - 24}" text-anchor="middle" '
                   f'font-size="9" fill="#AAAAAA">{h}</text>')
        svg.append(f'<text x="{px}" y="{py_c - 10}" text-anchor="middle" '
                   f'font-size="9" fill="#666666">{SIGNS_HI[s_idx]}</text>')
        if h == 1:
            svg.append(f'<text x="{px - 18}" y="{py_c + 4}" text-anchor="middle" '
                       f'font-size="8" fill="#8B0000" font-weight="bold">'
                       f'ल</text>')
        plist = sign_planets[s_idx]
        for i, pname in enumerate(plist):
            pdata = planets[pname]
            abbr  = PLANET_HI.get(pname, pname[:2])
            deg   = int(pdata['deg'])
            retro = "ᵛ" if pdata['retro'] else ""
            col   = PLANET_COLORS.get(pname, "#333")
            yp    = py_c + 8 + i * 17
            svg.append(
                f'<text x="{px}" y="{yp}" text-anchor="middle" '
                f'font-size="14" font-weight="bold" fill="{col}">'
                f'{abbr}{retro}'
                f'<tspan font-size="8" baseline-shift="super">{deg}</tspan>'
                f'</text>')

    fy = oy + 20 + gh + 30
    svg.append(f'<text x="{W//2}" y="{fy}" text-anchor="middle" '
               f'font-size="10" fill="#555">'
               f'लग्न: {chart["asc_sign_hi"]} {dms_str(chart["asc_deg"])}  ·  '
               f'राशि: {chart["moon_rashi_hi"]}  ·  '
               f'नक्षत्र: {chart["nakshatra"]} '
               f'पद {chart["nak_pada"]} '
               f'({chart["nak_lord"]})</text>')
    svg.append(f'<text x="{W//2}" y="{fy+16}" text-anchor="middle" '
               f'font-size="8" fill="#AAAAAA">'
               f'Lahiri Ayanamsha  ·  Swiss Ephemeris</text>')
    svg.append('</svg>')

    return "\n".join(svg)


def generate_golden_chart_image(chart):
    """
    Render planetary data onto the golden frame template image.
    Returns a BytesIO PNG image ready for embedding in the PDF.
    Uses Pillow to composite text onto the ornate golden kundali frame.
    Template: static/chart-template.png (1536x1024, golden frame with
    North Indian kundali grid on black background).
    """
    from PIL import Image, ImageDraw, ImageFont
    import io as _io

    asc_sign = chart['asc_sign']
    planets  = chart['planets']

    # Load golden frame template
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "static", "chart-template.png")
    img = Image.open(template_path).convert("RGBA")
    tw, th = img.size  # 1536 x 1024

    draw = ImageDraw.Draw(img)

    # ── Load fonts ──
    font_size_planet = 30
    font_size_house  = 24
    font_size_deg    = 16
    font_size_label  = 32

    _base = os.path.dirname(os.path.abspath(__file__))
    font_candidates = [
        os.path.join(_base, "fonts", "NotoSansDevanagari.ttf"),
        "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    font_planet = ImageFont.load_default()
    font_house  = ImageFont.load_default()
    font_deg    = ImageFont.load_default()
    font_label  = ImageFont.load_default()
    for fp in font_candidates:
        try:
            font_planet = ImageFont.truetype(fp, font_size_planet)
            font_house  = ImageFont.truetype(fp, font_size_house)
            font_deg    = ImageFont.truetype(fp, font_size_deg)
            font_label  = ImageFont.truetype(fp, font_size_label)
            break
        except Exception:
            continue

    # ── Golden frame grid geometry (1536x1024) ──
    # The golden frame sits centered on black background.
    # Frame inner edges measured from the template image:
    fl, fr = 210, 1325   # frame inner left/right
    ft, fb = 115, 905    # frame inner top/bottom
    cx = (fl + fr) // 2  # center x ~768
    cy = (ft + fb) // 2  # center y ~510

    # Quarter-points (where the midpoint lines intersect the edges)
    mx = (fl + fr) // 2  # mid-x
    my = (ft + fb) // 2  # mid-y
    qx = (fr - fl) // 4  # quarter-width ~279
    qy = (fb - ft) // 4  # quarter-height ~198

    # Cell centers for the 12 houses in North Indian layout.
    # The grid has a rectangle divided by diagonals and midpoint lines.
    # Outer triangles (houses 1-8) and inner diamond (houses 9-12).
    # North Indian chart: house positions are FIXED on the grid.
    # House 7 = top-center, 8 = top-left, 1 = left-center (Lagna),
    # 2 = bottom-left, 3 = bottom-center, 4 = bottom-right,
    # 5 = right-center, 6 = top-right
    # Inner diamond: 12 = top-left, 11 = top-right,
    #                10 = bottom-right, 9 = bottom-left
    #
    # Each house has a CENTER for the house number and a PLANET AREA
    # where planets are drawn (offset from center to avoid overlap).
    # house_num_pos: where to draw the house number
    # house_planet_pos: center of the planet placement area
    # For bottom/right houses, planets go ABOVE the number to stay inside frame
    house_centers = {
        7:  (mx,              ft + qy * 0.50),     # Top center
        8:  (mx - qx * 0.70, ft + qy * 0.55),     # Top-left
        6:  (mx + qx * 0.70, ft + qy * 0.55),     # Top-right
        1:  (fl + qx * 0.60, my),                  # Left center (Lagna)
        5:  (fr - qx * 0.70, my),                  # Right center (pulled in)
        2:  (mx - qx * 0.65, fb - qy * 0.55),     # Bottom-left
        3:  (mx,              fb - qy * 0.40),     # Bottom center
        4:  (mx + qx * 0.50, fb - qy * 0.65),     # Bottom-right (well inside)
        12: (mx - qx * 0.35, my - qy * 0.35),     # Inner top-left
        11: (mx + qx * 0.35, my - qy * 0.35),     # Inner top-right
        10: (mx + qx * 0.35, my + qy * 0.35),     # Inner bottom-right
        9:  (mx - qx * 0.35, my + qy * 0.35),     # Inner bottom-left
    }
    cell_centers = house_centers

    # Map house number -> sign index
    cell_sign = {h: (asc_sign + h - 1) % 12 for h in range(1, 13)}

    # Group planets by sign
    sign_planets = {i: [] for i in range(12)}
    for pname, pdata in planets.items():
        sign_planets[pdata['sign_idx']].append(pname)

    PLANET_COLORS = {
        "Sun": "#B8860B", "Moon": "#1E5FAD", "Mars": "#CC0000",
        "Mercury": "#1C7C3A", "Jupiter": "#E07000", "Venus": "#7B00CC",
        "Saturn": "#1C1C8C", "Rahu": "#006400", "Ketu": "#8B3A00",
    }

    # ── Draw "लग्न कुण्डली" label above the frame ──
    draw.text((cx, ft - 30), "लग्न कुण्डली", fill="#DAA520",
              font=font_label, anchor="mb")

    # ── Draw house numbers and planets in each cell ──
    for h in range(1, 13):
        s_idx = cell_sign[h]
        px, py = int(cell_centers[h][0]), int(cell_centers[h][1])

        # For bottom-half houses, put number below and planets above
        # For top-half/side houses, put number above and planets below
        # Houses where planets should grow toward center (away from edges)
        edge_houses = {2, 3, 4, 5, 9, 10}
        is_bottom = h in edge_houses

        plist = sign_planets[s_idx]
        n = len(plist)

        if is_bottom:
            # Number at bottom of cell, planets above
            num_y = py + 15 if n > 0 else py
            draw.text((px, num_y), str(h), fill="#9B8968",
                      font=font_house, anchor="mm")
            py_base = py - 10  # planets above
        else:
            # Number at top of cell, planets below
            num_y = py - 15 if n > 0 else py
            draw.text((px, num_y), str(h), fill="#9B8968",
                      font=font_house, anchor="mm")
            py_base = py + 10  # planets below

        if n == 0:
            continue

        # Direction: bottom houses grow upward, top houses grow downward
        direction = -1 if is_bottom else 1

        # For crowded houses (3+), use 2 columns; otherwise single column
        if n >= 3:
            row_spacing = 28
            col_offset = 45
            rows = (n + 1) // 2
            if is_bottom:
                start_y = py_base + (rows - 1) * row_spacing // 2
            else:
                start_y = py_base - (rows - 1) * row_spacing // 2
            for i, pname in enumerate(plist):
                pdata = planets[pname]
                abbr = PLANET_HI.get(pname, pname[:2])
                deg = int(pdata['deg'])
                retro_mark = "ᵛ" if pdata['retro'] else ""
                color = PLANET_COLORS.get(pname, "#333333")
                row = i // 2
                column = i % 2
                xp = px - col_offset // 2 + column * col_offset
                yp = start_y + row * row_spacing * direction
                label = f"{abbr}{retro_mark}"
                deg_label = f"{deg:02d}"
                draw.text((xp - 5, yp), label, fill=color,
                          font=font_planet, anchor="mm")
                draw.text((xp + 20, yp - 8), deg_label, fill=color,
                          font=font_deg, anchor="mm")
        else:
            spacing = 32
            if is_bottom:
                start_y = py_base + (n - 1) * spacing // 2
            else:
                start_y = py_base - (n - 1) * spacing // 2
            for i, pname in enumerate(plist):
                pdata = planets[pname]
                abbr = PLANET_HI.get(pname, pname[:2])
                deg = int(pdata['deg'])
                retro_mark = "ᵛ" if pdata['retro'] else ""
                color = PLANET_COLORS.get(pname, "#333333")
                yp = start_y + i * spacing * direction
                label = f"{abbr}{retro_mark}"
                deg_label = f"{deg:02d}"
                draw.text((px - 5, yp), label, fill=color,
                          font=font_planet, anchor="mm")
                draw.text((px + 20, yp - 8), deg_label, fill=color,
                          font=font_deg, anchor="mm")

    # ── Crop to frame area (remove black border) and convert ──
    # The golden frame with ornaments spans approx:
    #   left=145, top=48, right=1390, bottom=978 (including corner ornaments)
    crop_box = (145, 48, 1390, 978)
    img_cropped = img.crop(crop_box)

    img_rgb = img_cropped.convert("RGB")
    buf = _io.BytesIO()
    img_rgb.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf


# ─── Dasha Interpretations ────────────────────────────────────────────────────

DASHA_READING = {
    "Ketu": {
        "nature": "spiritual, introspective, and transformative",
        "themes": ("spiritual growth, detachment from material desires, "
                   "introspection, past-life karma resolution, and sudden changes"),
        "positive": ("heightened intuition, spiritual breakthroughs, liberation "
                     "from old patterns, interest in meditation and occult sciences"),
        "challenges": ("confusion, unexpected losses, health issues (especially "
                       "related to nerves), feelings of isolation, and sudden reversals"),
        "advice": ("Embrace spiritual practices, avoid major material commitments, "
                   "stay grounded through routine, and trust the process of inner transformation."),
    },
    "Venus": {
        "nature": "luxurious, creative, and relationship-oriented",
        "themes": ("love, marriage, artistic pursuits, wealth accumulation, "
                   "comfort, beauty, and social connections"),
        "positive": ("financial prosperity, harmonious relationships, artistic "
                     "success, acquisition of vehicles/property, and social recognition"),
        "challenges": ("over-indulgence, excessive spending, relationship "
                       "complications, health issues related to reproductive system or kidneys"),
        "advice": ("Cultivate meaningful relationships, invest wisely, pursue "
                   "creative interests, and maintain balance between pleasure and discipline."),
    },
    "Sun": {
        "nature": "authoritative, ambitious, and self-expressive",
        "themes": ("career advancement, leadership roles, government connections, "
                   "father's influence, health vitality, and recognition"),
        "positive": ("rise in status and authority, government favour, strong "
                     "willpower, leadership opportunities, and improved confidence"),
        "challenges": ("ego conflicts, strained relations with authority figures, "
                       "health issues related to heart/eyes/bones, and political setbacks"),
        "advice": ("Step into leadership with humility, strengthen your health "
                   "regimen, honour your father, and pursue righteous goals."),
    },
    "Moon": {
        "nature": "emotional, nurturing, and mentally active",
        "themes": ("emotional well-being, mother's influence, public dealings, "
                   "travel, mental peace, and domestic happiness"),
        "positive": ("emotional fulfilment, good relations with mother, public "
                     "popularity, travel opportunities, mental clarity, and nurturing connections"),
        "challenges": ("mood fluctuations, anxiety, water-related issues, "
                       "domestic disturbances, and over-sensitivity"),
        "advice": ("Prioritise mental health, spend time near water, nurture "
                   "family bonds, and develop emotional resilience through mindfulness."),
    },
    "Mars": {
        "nature": "energetic, courageous, and action-oriented",
        "themes": ("physical energy, property matters, siblings, courage, "
                   "technical skills, and competitive endeavours"),
        "positive": ("success in competitions, property acquisition, physical "
                     "strength, courage to face challenges, and technical achievements"),
        "challenges": ("accidents, conflicts, blood-related health issues, "
                       "legal disputes, anger management problems, and hasty decisions"),
        "advice": ("Channel energy into physical activity and constructive projects, "
                   "avoid unnecessary conflicts, be cautious with legal matters, and practice patience."),
    },
    "Rahu": {
        "nature": "ambitious, unconventional, and worldly",
        "themes": ("material ambition, foreign connections, technology, "
                   "unconventional paths, sudden rise, and obsessive pursuits"),
        "positive": ("sudden gains, success in foreign lands, technological "
                     "advancement, breaking social barriers, and worldly achievements"),
        "challenges": ("deception, confusion, addictions, fear and anxiety, "
                       "scandals, and illusory pursuits that lead nowhere"),
        "advice": ("Stay ethical in all dealings, avoid shortcuts and get-rich-quick "
                   "schemes, be discerning about new associations, and ground yourself spiritually."),
    },
    "Jupiter": {
        "nature": "wise, expansive, and benevolent",
        "themes": ("wisdom, higher education, spirituality, children, wealth, "
                   "teacher/guru influence, and dharmic pursuits"),
        "positive": ("spiritual growth, educational achievements, birth of children, "
                     "wealth expansion, wise counsel, and pilgrimage opportunities"),
        "challenges": ("over-optimism, weight gain, liver-related issues, "
                       "complacency, and problems with children or teachers"),
        "advice": ("Pursue higher learning, seek a mentor or guru, practice "
                   "generosity, maintain a healthy lifestyle, and align actions with dharma."),
    },
    "Saturn": {
        "nature": "disciplined, karmic, and persevering",
        "themes": ("hard work, discipline, longevity, karma, service, "
                   "delays, and structured growth"),
        "positive": ("rewards for past hard work, mastery through persistence, "
                     "real estate gains, career stability, and deep maturity"),
        "challenges": ("delays and obstacles, chronic health issues (joints/bones), "
                       "feelings of loneliness, heavy responsibilities, and depression"),
        "advice": ("Embrace discipline and patience, serve others selflessly, "
                   "take care of bones and joints, avoid shortcuts, and trust that slow progress is lasting progress."),
    },
    "Mercury": {
        "nature": "intellectual, communicative, and adaptable",
        "themes": ("communication, business, education, intellect, "
                   "trade, writing, and analytical thinking"),
        "positive": ("business success, intellectual achievements, good communication, "
                     "successful negotiations, writing/publishing, and learning new skills"),
        "challenges": ("nervousness, skin issues, indecisiveness, speech problems, "
                       "business setbacks, and scattered focus"),
        "advice": ("Invest in education and skill development, diversify income "
                   "sources, maintain clear communication, and avoid over-thinking."),
    },
}


def _dasha_reading(chart, today):
    """Generate a list of text blocks for the dasha reading page."""
    blocks = []
    dashas = chart['dashas']

    # Find current and next Mahadasha
    current_maha = None
    current_maha_data = None
    next_maha_data = None
    for i, (lord, start, end, yrs) in enumerate(dashas):
        if start <= today < end:
            current_maha = lord
            current_maha_data = (lord, start, end, yrs)
            if i + 1 < len(dashas):
                next_maha_data = dashas[i + 1]
            break

    if not current_maha:
        blocks.append("Unable to determine current Dasha period for reading.")
        return blocks

    # Find current Antardasha
    current_antar = None
    current_antar_data = None
    next_antar_data = None
    ad_list = chart.get('antardasha', {}).get(current_maha, [])
    for i, (ad_lord, ad_start, ad_end, ad_yrs) in enumerate(ad_list):
        if ad_start <= today < ad_end:
            current_antar = ad_lord
            current_antar_data = (ad_lord, ad_start, ad_end, ad_yrs)
            if i + 1 < len(ad_list):
                next_antar_data = ad_list[i + 1]
            break

    # Find current Pratyantar
    current_prat = None
    current_prat_data = None
    if current_antar:
        key = (current_maha, current_antar)
        pd_list = chart.get('pratyantar', {}).get(key, [])
        for pd_lord, pd_start, pd_end, pd_yrs in pd_list:
            if pd_start <= today < pd_end:
                current_prat = pd_lord
                current_prat_data = (pd_lord, pd_start, pd_end, pd_yrs)
                break

    maha_info = DASHA_READING.get(current_maha, {})
    remaining_days = (current_maha_data[2] - today).days
    remaining_yrs = remaining_days / 365.25

    # ── Current Position Summary ──
    blocks.append("## Current Dasha Position")
    position = (f"You are currently running <b>{current_maha} Mahadasha</b>")
    if current_antar:
        position += f" with <b>{current_antar} Antardasha</b>"
    if current_prat:
        position += f" and <b>{current_prat} Pratyantar</b>"
    position += "."
    if remaining_yrs > 1:
        position += (f" The {current_maha} Mahadasha continues until "
                     f"<b>{current_maha_data[2].strftime('%B %Y')}</b> "
                     f"(approximately {remaining_yrs:.1f} years remaining).")
    else:
        position += (f" The {current_maha} Mahadasha ends in "
                     f"<b>{current_maha_data[2].strftime('%B %Y')}</b> "
                     f"({remaining_days} days remaining).")
    blocks.append(position)

    # ── Current Mahadasha Reading ──
    blocks.append(f"## {current_maha} Mahadasha — What You Are Experiencing")
    blocks.append(
        f"The {current_maha} period is <b>{maha_info.get('nature', 'significant')}</b> "
        f"in nature. The key themes of this period include {maha_info.get('themes', 'various life changes')}.")
    blocks.append(
        f"<b>Strengths of this period:</b> {maha_info.get('positive', 'Growth opportunities')}.")
    blocks.append(
        f"<b>Areas of caution:</b> {maha_info.get('challenges', 'Challenges may arise')}.")

    # ── Current Antardasha influence ──
    if current_antar:
        antar_info = DASHA_READING.get(current_antar, {})
        antar_end = current_antar_data[2]
        blocks.append(f"## {current_antar} Antardasha — Current Sub-Period Influence")
        blocks.append(
            f"Within the broader {current_maha} period, the <b>{current_antar} "
            f"Antardasha</b> (running until <b>{antar_end.strftime('%B %Y')}</b>) "
            f"adds a layer of {antar_info.get('nature', 'specific')} energy. "
            f"This sub-period emphasises {antar_info.get('themes', 'certain life areas')}.")

        # Combined effect
        blocks.append(
            f"The combination of <b>{current_maha}–{current_antar}</b> suggests a "
            f"period where the {current_maha} Mahadasha's broader themes are "
            f"filtered through {current_antar}'s influence — bringing "
            f"{antar_info.get('positive', 'opportunities')} while requiring "
            f"awareness of {antar_info.get('challenges', 'potential difficulties')}.")

    # ── Current Pratyantar influence ──
    if current_prat:
        prat_info = DASHA_READING.get(current_prat, {})
        prat_end = current_prat_data[2]
        days_left = (prat_end - today).days
        blocks.append(f"## {current_prat} Pratyantar — Immediate Influence")
        blocks.append(
            f"At the most immediate level, the <b>{current_prat} Pratyantar</b> "
            f"(active for the next <b>{days_left} days</b>, until "
            f"{prat_end.strftime('%d %B %Y')}) brings short-term focus on "
            f"{prat_info.get('themes', 'specific matters')}. "
            f"Watch for {prat_info.get('positive', 'positive developments')} "
            f"during this micro-period.")

    # ── Upcoming Transitions ──
    blocks.append("## Looking Ahead — Upcoming Transitions")

    # Next Antardasha
    if next_antar_data:
        na_lord, na_start, na_end, na_yrs = next_antar_data
        na_info = DASHA_READING.get(na_lord, {})
        blocks.append(
            f"The next Antardasha shift will be to <b>{current_maha}–{na_lord}</b>, "
            f"beginning around <b>{na_start.strftime('%B %Y')}</b>. "
            f"This will bring a shift towards {na_info.get('nature', 'different')} "
            f"energy, with emphasis on {na_info.get('themes', 'new themes')}.")

    # Next Mahadasha
    if next_maha_data:
        nm_lord, nm_start, nm_end, nm_yrs = next_maha_data
        nm_info = DASHA_READING.get(nm_lord, {})
        blocks.append(
            f"A major life transition awaits when the <b>{nm_lord} Mahadasha</b> "
            f"begins in <b>{nm_start.strftime('%B %Y')}</b> "
            f"(lasting {nm_yrs:.1f} years until {nm_end.strftime('%B %Y')}). "
            f"This will mark a significant shift from the current "
            f"{current_maha} themes towards a period that is "
            f"<b>{nm_info.get('nature', 'different')}</b> in nature.")
        blocks.append(
            f"<b>What to expect in {nm_lord} Mahadasha:</b> "
            f"{nm_info.get('themes', 'New life themes')}. "
            f"Key strengths will include {nm_info.get('positive', 'various opportunities')}.")

    # ── Guidance ──
    blocks.append(f"## Guidance for the Current Period")
    blocks.append(maha_info.get('advice', 'Stay balanced and mindful.'))

    return blocks


# ─── Hindi Data ──────────────────────────────────────────────────────────────

PLANET_HI_FULL = {
    "Sun": "सूर्य", "Moon": "चन्द्र",
    "Mars": "मंगल", "Mercury": "बुध",
    "Jupiter": "गुरु", "Venus": "शुक्र",
    "Saturn": "शनि", "Rahu": "राहु",
    "Ketu": "केतु",
}

DASHA_READING_HI = {
    "Ketu": {
        "nature": "आध्यात्मिक, आत्मनिरीक्षण और परिवर्तनकारी",
        "themes": "आध्यात्मिक विकास, भौतिक इच्छाओं से वैराग्य, पूर्व जन्म कर्म समाधान और अचानक परिवर्तन",
        "positive": "तीव्र अंतर्ज्ञान, आध्यात्मिक उपलब्धियाँ, पुराने प्रतिरूपों से मुक्ति",
        "challenges": "भ्रम, अप्रत्याशित हानि, स्वास्थ्य समस्याएँ और अकेलेपन की भावना",
        "advice": "आध्यात्मिक साधना अपनाएँ, बड़ी भौतिक प्रतिबद्धताओं से बचें, दिनचर्या से स्थिर रहें।",
    },
    "Venus": {
        "nature": "वैभवपूर्ण, सृजनात्मक और संबंध-केंद्रित",
        "themes": "प्रेम, विवाह, कलात्मक कार्य, धन संचय, सुख-सुविधा और सामाजिक संबंध",
        "positive": "आर्थिक समृद्धि, सुखद संबंध, कलात्मक सफलता, वाहन/संपत्ति की प्राप्ति",
        "challenges": "अति-भोग, अत्यधिक खर्च, संबंधों में जटिलता",
        "advice": "सार्थक संबंध बनाएं, समझदारी से निवेश करें, सृजनात्मक रुचियों को अपनाएं।",
    },
    "Sun": {
        "nature": "अधिकारपूर्ण, महत्वाकांक्षी और आत्मअभिव्यक्ति",
        "themes": "करियर में उन्नति, नेतृत्व की भूमिका, सरकारी संपर्क, पिता का प्रभाव, स्वास्थ्य और प्रतिष्ठा",
        "positive": "पद और अधिकार में वृद्धि, सरकारी कृपा, दृढ़ इच्छाशक्ति, नेतृत्व के अवसर",
        "challenges": "अहंकार संघर्ष, अधिकारियों से तनावपूर्ण संबंध, हृदय/नेत्र/हड्डियों से संबंधित स्वास्थ्य समस्याएँ",
        "advice": "नम्रता के साथ नेतृत्व करें, स्वास्थ्य का ध्यान रखें, पिता का सम्मान करें।",
    },
    "Moon": {
        "nature": "भावनात्मक, पोषक और मानसिक रूप से सक्रिय",
        "themes": "भावनात्मक स्वास्थ्य, माता का प्रभाव, सार्वजनिक व्यवहार, यात्रा, मानसिक शांति और घरेलू सुख",
        "positive": "भावनात्मक संतुष्टि, माता से अच्छे संबंध, जनप्रियता, यात्रा के अवसर, मानसिक स्पष्टता",
        "challenges": "मनोदशा में उतार-चढ़ाव, चिंता, घरेलू विघ्न और अति-संवेदनशीलता",
        "advice": "मानसिक स्वास्थ्य को प्राथमिकता दें, पानी के निकट समय बिताएं, परिवारिक बंधनों को पोषित करें।",
    },
    "Mars": {
        "nature": "ऊर्जावान, साहसी और क्रिया-केंद्रित",
        "themes": "शारीरिक ऊर्जा, संपत्ति के मामले, भाई-बहन, साहस, तकनीकी कौशल और प्रतिस्पर्धा",
        "positive": "प्रतिस्पर्धा में सफलता, संपत्ति की प्राप्ति, शारीरिक शक्ति, चुनौतियों का सामना करने का साहस",
        "challenges": "दुर्घटनाएँ, संघर्ष, रक्त संबंधी स्वास्थ्य समस्याएँ, कानूनी विवाद और क्रोध प्रबंधन",
        "advice": "ऊर्जा को शारीरिक गतिविधि और रचनात्मक परियोजनाओं में लगाएं, अनावश्यक संघर्षों से बचें, धैर्य रखें।",
    },
    "Rahu": {
        "nature": "महत्वाकांक्षी, अपरंपरागत और सांसारिक",
        "themes": "भौतिक महत्वाकांक्षा, विदेशी संपर्क, प्रौद्योगिकी, अपरंपरागत मार्ग, अचानक उत्थान और जुनूनी प्रयास",
        "positive": "अचानक लाभ, विदेशों में सफलता, प्रौद्योगिकी में उन्नति, सामाजिक बाधाओं को तोड़ना",
        "challenges": "धोखा, भ्रम, नशा, भय और चिंता, कलंक और भ्रामक प्रयास",
        "advice": "सभी व्यवहारों में नैतिक रहें, शॉर्टकट और जल्दी धन-प्राप्ति योजनाओं से बचें, आध्यात्मिक रूप से स्थिर रहें।",
    },
    "Jupiter": {
        "nature": "बुद्धिमान, विस्तारवादी और परोपकारी",
        "themes": "ज्ञान, उच्च शिक्षा, आध्यात्मिकता, संतान, धन, गुरु का प्रभाव और धार्मिक कार्य",
        "positive": "आध्यात्मिक विकास, शैक्षिक उपलब्धियाँ, संतान प्राप्ति, धन वृद्धि, तीर्थयात्रा के अवसर",
        "challenges": "अति-आशावाद, वजन वृद्धि, यकृत संबंधी समस्याएँ और आत्मसंतुष्टि",
        "advice": "उच्च शिक्षा प्राप्त करें, गुरु की खोज करें, उदारता का अभ्यास करें, धर्म के अनुसार कार्य करें।",
    },
    "Saturn": {
        "nature": "अनुशासित, कार्मिक और दृढ़",
        "themes": "कठिन परिश्रम, अनुशासन, दीर्घायु, कर्म, सेवा, विलंब और व्यवस्थित विकास",
        "positive": "पूर्व परिश्रम का फल, दृढ़ता से सिद्धि, अचल संपत्ति लाभ, करियर स्थिरता और गहरी परिपक्वता",
        "challenges": "विलंब और बाधाएँ, जोड़ों/हड्डियों की स्वास्थ्य समस्याएँ, अकेलेपन की भावना, भारी जिम्मेदारियाँ और अवसाद",
        "advice": "अनुशासन और धैर्य अपनाएं, निःस्वार्थ सेवा करें, हड्डियों और जोड़ों की देखभाल करें, शॉर्टकट से बचें।",
    },
    "Mercury": {
        "nature": "बौद्धिक, संवादशील और अनुकूलनशील",
        "themes": "संवाद, व्यापार, शिक्षा, बुद्धि, व्यापार, लेखन और विश्लेषणात्मक सोच",
        "positive": "व्यापारिक सफलता, बौद्धिक उपलब्धियाँ, अच्छा संवाद, सफल वार्ता, लेखन/प्रकाशन और नए कौशल सीखना",
        "challenges": "घबराहट, त्वचा समस्याएँ, अनिर्णय, वाणी संबंधी समस्याएँ, व्यापारिक असफलताएँ और बिखरा ध्यान",
        "advice": "शिक्षा और कौशल विकास में निवेश करें, आय के स्रोतों में विविधता लाएं, स्पष्ट संवाद बनाए रखें।",
    },
}


def _dasha_reading_hi(chart, today):
    """Generate Hindi dasha reading text blocks."""
    blocks = []
    dashas = chart['dashas']

    current_maha = None
    current_maha_data = None
    next_maha_data = None
    for i, (lord, start, end, yrs) in enumerate(dashas):
        if start <= today < end:
            current_maha = lord
            current_maha_data = (lord, start, end, yrs)
            if i + 1 < len(dashas):
                next_maha_data = dashas[i + 1]
            break

    if not current_maha:
        blocks.append("वर्तमान दशा काल निर्धारित नहीं किया जा सका।")
        return blocks

    current_antar = None
    current_antar_data = None
    next_antar_data = None
    ad_list = chart.get('antardasha', {}).get(current_maha, [])
    for i, (ad_lord, ad_start, ad_end, ad_yrs) in enumerate(ad_list):
        if ad_start <= today < ad_end:
            current_antar = ad_lord
            current_antar_data = (ad_lord, ad_start, ad_end, ad_yrs)
            if i + 1 < len(ad_list):
                next_antar_data = ad_list[i + 1]
            break

    current_prat = None
    current_prat_data = None
    if current_antar:
        key = (current_maha, current_antar)
        pd_list = chart.get('pratyantar', {}).get(key, [])
        for pd_lord, pd_start, pd_end, pd_yrs in pd_list:
            if pd_start <= today < pd_end:
                current_prat = pd_lord
                current_prat_data = (pd_lord, pd_start, pd_end, pd_yrs)
                break

    maha_hi = PLANET_HI_FULL.get(current_maha, current_maha)
    maha_info = DASHA_READING_HI.get(current_maha, {})
    remaining_days = (current_maha_data[2] - today).days
    remaining_yrs = remaining_days / 365.25

    # Current position
    blocks.append("## वर्तमान दशा स्थिति")
    position = f"आप वर्तमान में <b>{maha_hi} महादशा</b>"
    if current_antar:
        antar_hi = PLANET_HI_FULL.get(current_antar, current_antar)
        position += f" के अंतर्गत <b>{antar_hi} अंतर्दशा</b>"
    if current_prat:
        prat_hi = PLANET_HI_FULL.get(current_prat, current_prat)
        position += f" और <b>{prat_hi} प्रत्यंतर</b>"
    position += " चल रहे हैं।"
    if remaining_yrs > 1:
        position += (f" {maha_hi} महादशा <b>{current_maha_data[2].strftime('%B %Y')}</b> "
                     f"तक जारी रहेगी "
                     f"(लगभग {remaining_yrs:.1f} वर्ष शेष)।")
    else:
        position += (f" {maha_hi} महादशा <b>{current_maha_data[2].strftime('%B %Y')}</b> "
                     f"में समाप्त होगी "
                     f"({remaining_days} दिन शेष)।")
    blocks.append(position)

    # Mahadasha reading — extract defaults for Python 3.9 f-string compatibility
    _m_nature = maha_info.get('nature', 'महत्वपूर्ण')
    _m_themes = maha_info.get('themes', 'विभिन्न जीवन परिवर्तन')
    _m_positive = maha_info.get('positive', 'विकास के अवसर')
    _m_challenges = maha_info.get('challenges', 'चुनौतियाँ आ सकती हैं')
    blocks.append(f"## {maha_hi} महादशा — आप क्या अनुभव कर रहे हैं")
    blocks.append(
        f"{maha_hi} का काल <b>{_m_nature}</b> "
        f"प्रकृति का है। इस काल के प्रमुख विषयों में शामिल हैं: "
        f"{_m_themes}।")
    blocks.append(
        f"<b>इस काल की शक्तियाँ:</b> "
        f"{_m_positive}।")
    blocks.append(
        f"<b>सावधानी के क्षेत्र:</b> "
        f"{_m_challenges}।")

    # Antardasha
    if current_antar:
        antar_hi = PLANET_HI_FULL.get(current_antar, current_antar)
        antar_info = DASHA_READING_HI.get(current_antar, {})
        antar_end = current_antar_data[2]
        _a_nature = antar_info.get('nature', 'विशेष')
        _a_themes = antar_info.get('themes', 'कुछ जीवन क्षेत्रों')
        _a_positive = antar_info.get('positive', 'अवसर')
        _a_challenges = antar_info.get('challenges', 'संभावित कठिनाइयों')
        blocks.append(f"## {antar_hi} अंतर्दशा — वर्तमान उप-काल का प्रभाव")
        blocks.append(
            f"{maha_hi} के व्यापक काल में, <b>{antar_hi} "
            f"अंतर्दशा</b> (<b>{antar_end.strftime('%B %Y')}</b> तक) "
            f"<b>{_a_nature}</b> ऊर्जा जोड़ती है। "
            f"यह उप-काल {_a_themes} पर जोर देता है।")
        blocks.append(
            f"<b>{maha_hi}–{antar_hi}</b> का संयोजन दर्शाता है कि "
            f"{maha_hi} महादशा के व्यापक विषय "
            f"{antar_hi} के प्रभाव से छनते हैं — "
            f"{_a_positive} लाते हुए "
            f"{_a_challenges} के प्रति सचेत रहना चाहिए।")

    # Pratyantar
    if current_prat:
        prat_hi = PLANET_HI_FULL.get(current_prat, current_prat)
        prat_info = DASHA_READING_HI.get(current_prat, {})
        prat_end = current_prat_data[2]
        days_left = (prat_end - today).days
        _p_themes = prat_info.get('themes', 'विशेष मामलों')
        _p_positive = prat_info.get('positive', 'सकारात्मक विकास')
        blocks.append(f"## {prat_hi} प्रत्यंतर — तात्कालिक प्रभाव")
        blocks.append(
            f"सबसे तात्कालिक स्तर पर, <b>{prat_hi} प्रत्यंतर</b> "
            f"(अगले <b>{days_left} दिनों</b> तक, "
            f"{prat_end.strftime('%d %B %Y')} तक) "
            f"{_p_themes} पर अल्पकालिक ध्यान लाता है। "
            f"इस सूक्ष्म काल में "
            f"{_p_positive} देखें।")

    # Looking ahead
    blocks.append("## आगे देखें — आने वाले परिवर्तन")
    if next_antar_data:
        na_lord, na_start, na_end, na_yrs = next_antar_data
        na_hi = PLANET_HI_FULL.get(na_lord, na_lord)
        na_info = DASHA_READING_HI.get(na_lord, {})
        _na_nature = na_info.get('nature', 'भिन्न')
        _na_themes = na_info.get('themes', 'नए विषय')
        blocks.append(
            f"अगला अंतर्दशा परिवर्तन <b>{maha_hi}–{na_hi}</b> होगा, "
            f"जो <b>{na_start.strftime('%B %Y')}</b> से शुरू होगा। "
            f"यह <b>{_na_nature}</b> ऊर्जा की ओर बदलाव लाएगा, "
            f"जिसमें {_na_themes} पर जोर होगा।")
    if next_maha_data:
        nm_lord, nm_start, nm_end, nm_yrs = next_maha_data
        nm_hi = PLANET_HI_FULL.get(nm_lord, nm_lord)
        nm_info = DASHA_READING_HI.get(nm_lord, {})
        _nm_nature = nm_info.get('nature', 'भिन्न')
        _nm_themes = nm_info.get('themes', 'नए जीवन विषय')
        _nm_positive = nm_info.get('positive', 'विभिन्न अवसर')
        blocks.append(
            f"एक बड़ा जीवन परिवर्तन तब आएगा जब <b>{nm_hi} महादशा</b> "
            f"<b>{nm_start.strftime('%B %Y')}</b> में शुरू होगी "
            f"({nm_yrs:.1f} वर्ष, {nm_end.strftime('%B %Y')} तक)। "
            f"यह वर्तमान {maha_hi} के विषयों से "
            f"<b>{_nm_nature}</b> प्रकृति के काल की ओर महत्वपूर्ण बदलाव होगा।")
        blocks.append(
            f"<b>{nm_hi} महादशा में क्या अपेक्षा करें:</b> "
            f"{_nm_themes}। "
            f"प्रमुख शक्तियाँ: {_nm_positive}।")

    # Guidance
    blocks.append(f"## वर्तमान काल के लिए मार्गदर्शन")
    blocks.append(maha_info.get('advice', 'संतुलित और सचेत रहें।'))

    return blocks


# ─── Transit / Gochar Engine ─────────────────────────────────────────────────

def current_transits(target_date=None):
    """
    Calculate current sidereal positions of all 9 planets for a given date.
    Returns dict: {planet_name: {lon, sign_idx, sign_en, sign_hi, deg, retro}}
    """
    if target_date is None:
        target_date = datetime.now()

    # Use noon UT for daily transits
    y, m, d = target_date.year, target_date.month, target_date.day
    jd = julian_day(y, m, d, 12.0)  # noon UT

    transits = {}
    for name, pid in PLANETS_SWE.items():
        lon, speed = sidereal_position(jd, pid)
        s_idx, s_en, s_hi, deg = sign_and_degree(lon)
        transits[name] = {
            'lon': lon, 'sign_idx': s_idx, 'sign_en': s_en,
            'sign_hi': s_hi, 'deg': deg, 'retro': speed < 0
        }

    # Rahu / Ketu
    rahu_lon, rahu_speed = sidereal_position(jd, swe.TRUE_NODE)
    ketu_lon = (rahu_lon + 180) % 360
    r_idx, r_en, r_hi, r_deg = sign_and_degree(rahu_lon)
    k_idx, k_en, k_hi, k_deg = sign_and_degree(ketu_lon)
    transits['Rahu'] = {'lon': rahu_lon, 'sign_idx': r_idx, 'sign_en': r_en,
                        'sign_hi': r_hi, 'deg': r_deg, 'retro': True}
    transits['Ketu'] = {'lon': ketu_lon, 'sign_idx': k_idx, 'sign_en': k_en,
                        'sign_hi': k_hi, 'deg': k_deg, 'retro': True}
    return transits


def transit_house_from_moon(natal_moon_sign_idx, transit_sign_idx):
    """Calculate which house a transit planet occupies from natal Moon sign."""
    return (transit_sign_idx - natal_moon_sign_idx) % 12 + 1


def detect_sade_sati(natal_moon_sign_idx, transit_saturn_sign_idx):
    """
    Detect Sade Sati phase based on Saturn's transit.
    Returns None or one of: 'rising', 'peak', 'setting'
    """
    house = (transit_saturn_sign_idx - natal_moon_sign_idx) % 12 + 1
    if house == 12:
        return "rising"
    elif house == 1:
        return "peak"
    elif house == 2:
        return "setting"
    return None


def _saturn_sign_at_date(year, month, day):
    """Get Saturn's sidereal sign index (0-11) at a given date using Lahiri ayanamsha."""
    swe.set_sid_mode(AYANAMSHA)
    jd = swe.julday(year, month, day, 12.0)
    pos, _ret = swe.calc_ut(jd, swe.SATURN, swe.FLG_SIDEREAL | swe.FLG_SPEED)
    return int(pos[0] / 30) % 12


def _refine_sign_boundary(year1, month1, day1, year2, month2, day2, target_sign):
    """Binary-search for the exact date Saturn enters target_sign between two dates.
    Returns (year, month, day) of the first day Saturn is in target_sign."""
    from datetime import date
    d1 = date(year1, month1, day1)
    d2 = date(year2, month2, day2)
    while (d2 - d1).days > 1:
        mid = d1 + (d2 - d1) / 2
        s = _saturn_sign_at_date(mid.year, mid.month, mid.day)
        if s == target_sign:
            d2 = mid
        else:
            d1 = mid
    return d2.year, d2.month, d2.day


def calculate_sade_sati(moon_sign_idx, birth_year):
    """
    Calculate all Sade Sati periods for the native.

    Args:
        moon_sign_idx: 0-based index of Moon's sign (0=Aries, 11=Pisces)
        birth_year: year of birth

    Returns:
        list of dicts, each with:
            'cycle': int (1, 2, 3...)
            'start_date': datetime (when Saturn enters 12th from Moon)
            'peak_start': datetime (when Saturn enters Moon sign)
            'peak_end': datetime (when Saturn leaves Moon sign)
            'end_date': datetime (when Saturn leaves 2nd from Moon)
            'is_current': bool
            'phase': str or None ('Rising', 'Peak', 'Setting', None)
            'phases': list of (phase_name, start_datetime) tuples
    """
    sign_12th = (moon_sign_idx - 1) % 12   # 12th from Moon (Rising)
    sign_moon = moon_sign_idx               # Moon sign itself (Peak)
    sign_2nd  = (moon_sign_idx + 1) % 12    # 2nd from Moon (Setting)
    sade_sati_signs = {sign_12th, sign_moon, sign_2nd}

    today = datetime.now()
    scan_start = birth_year - 5   # catch a cycle that may have started before birth
    scan_end = birth_year + 95

    # --- Pass 1: Scan at 15-day intervals to find raw in/out transitions ---
    raw_segments = []  # list of (date, sign) tuples where Saturn is in a SS sign
    prev_in_ss = False

    from datetime import date as _date

    d = _date(scan_start, 1, 1)
    end_d = _date(min(scan_end, 2200), 12, 31)
    step = timedelta(days=15)

    while d <= end_d:
        sat_sign = _saturn_sign_at_date(d.year, d.month, d.day)
        in_ss = sat_sign in sade_sati_signs

        if in_ss and not prev_in_ss:
            # Sade Sati begins — record entry
            raw_segments.append({'entry_date': d, 'entry_sign': sat_sign, 'transitions': [(d, sat_sign)]})
        elif in_ss and prev_in_ss and raw_segments:
            # Still in Sade Sati — track sign transitions
            if sat_sign != raw_segments[-1]['transitions'][-1][1]:
                raw_segments[-1]['transitions'].append((d, sat_sign))
        elif not in_ss and prev_in_ss and raw_segments:
            # Sade Sati ends
            raw_segments[-1]['exit_date'] = d

        prev_in_ss = in_ss
        d += step

    # Handle ongoing Sade Sati (no exit found)
    if raw_segments and 'exit_date' not in raw_segments[-1]:
        raw_segments[-1]['exit_date'] = None

    # --- Pass 2: Merge segments that are close together (retrograde re-entries) ---
    merged = []
    for seg in raw_segments:
        if merged and seg['exit_date'] is not None:
            prev = merged[-1]
            prev_exit = prev.get('exit_date')
            if prev_exit is not None:
                gap = (seg['entry_date'] - prev_exit).days
                if gap < 270:  # less than 9 months gap = retrograde re-entry
                    prev['exit_date'] = seg.get('exit_date')
                    prev['transitions'].extend(seg['transitions'])
                    continue
        merged.append(seg)

    # --- Pass 3: For each merged period, determine clean phase boundaries ---
    # We want: first entry into sign_12th, first entry into sign_moon,
    #          last exit from sign_moon, last exit from sign_2nd
    periods = []
    cycle_num = 0

    for seg in merged:
        transitions = seg['transitions']
        entry_d = seg['entry_date']
        exit_d = seg.get('exit_date')

        # Classify transitions by phase, taking first/last occurrence of each sign
        phase_dates = {}  # sign -> (first_entry_date, last_seen_date)
        for t_date, t_sign in transitions:
            if t_sign not in phase_dates:
                phase_dates[t_sign] = [t_date, t_date]
            else:
                phase_dates[t_sign][1] = t_date

        # Build phases list in order: Rising -> Peak -> Setting
        phases = []
        start_date = None
        peak_start = None
        peak_end = None
        end_date = None

        if sign_12th in phase_dates:
            start_date = datetime(phase_dates[sign_12th][0].year,
                                  phase_dates[sign_12th][0].month,
                                  phase_dates[sign_12th][0].day)
            phases.append(('Rising', start_date))

        if sign_moon in phase_dates:
            peak_start = datetime(phase_dates[sign_moon][0].year,
                                  phase_dates[sign_moon][0].month,
                                  phase_dates[sign_moon][0].day)
            phases.append(('Peak', peak_start))
            if sign_2nd in phase_dates:
                peak_end = datetime(phase_dates[sign_2nd][0].year,
                                    phase_dates[sign_2nd][0].month,
                                    phase_dates[sign_2nd][0].day)
            elif exit_d:
                peak_end = datetime(exit_d.year, exit_d.month, exit_d.day)
            else:
                peak_end = None

        if sign_2nd in phase_dates:
            setting_start = datetime(phase_dates[sign_2nd][0].year,
                                     phase_dates[sign_2nd][0].month,
                                     phase_dates[sign_2nd][0].day)
            phases.append(('Setting', setting_start))

        # Overall start/end
        if not start_date:
            # Sade Sati might start directly at Peak (if person born mid-cycle)
            if peak_start:
                start_date = peak_start
            elif phases:
                start_date = phases[0][1]
            else:
                start_date = datetime(entry_d.year, entry_d.month, entry_d.day)

        if exit_d:
            end_date = datetime(exit_d.year, exit_d.month, exit_d.day)
        else:
            end_date = None  # ongoing

        # Skip periods entirely before birth
        if end_date and end_date.year < birth_year:
            continue

        cycle_num += 1

        # Determine current status
        is_current = False
        current_phase = None
        if end_date is None or (start_date <= today and (end_date is None or today < end_date)):
            if start_date <= today:
                is_current = True
                # Determine which phase we're in
                for i, (pname, pstart) in enumerate(phases):
                    pend = phases[i+1][1] if i+1 < len(phases) else end_date
                    if pend is None or today < pend:
                        current_phase = pname
                        break
                if current_phase is None and phases:
                    current_phase = phases[-1][0]

        periods.append({
            'cycle': cycle_num,
            'start_date': start_date,
            'peak_start': peak_start,
            'peak_end': peak_end,
            'end_date': end_date,
            'is_current': is_current,
            'phase': current_phase if is_current else None,
            'phases': phases,
        })

    return periods


# ─── Sade Sati Interpretation Constants ────────────────────────────────────

SADE_SATI_PHASES_EN = {
    "Rising": {
        "title": "Rising Phase (Ascending) — Saturn in 12th from Moon",
        "description": (
            "The beginning of Sade Sati. Saturn transits the 12th house from your Moon sign, "
            "affecting expenses, sleep, foreign travel, and spiritual matters. You may experience "
            "increased expenses, sleep disturbances, feelings of isolation, or a need for solitude. "
            "This phase often brings subconscious shifts and spiritual awakening."
        ),
        "effects": [
            "Increased expenses or financial pressure",
            "Sleep disturbances or vivid dreams",
            "Feelings of isolation or detachment",
            "Foreign travel or relocation possibilities",
            "Beginning of inner transformation",
        ],
    },
    "Peak": {
        "title": "Peak Phase (Climax) — Saturn on Moon Sign",
        "description": (
            "The most intense phase of Sade Sati. Saturn directly transits your Moon sign, "
            "creating maximum pressure on your emotional and mental state. This is a period of "
            "deep karmic lessons. While challenging, it builds extraordinary resilience and maturity. "
            "Your emotional strength is being tested and forged."
        ),
        "effects": [
            "Emotional turbulence and mental stress",
            "Health issues — especially related to mind/emotions",
            "Career challenges or major professional shifts",
            "Relationship tensions requiring patience",
            "Deep personal transformation and maturity",
        ],
    },
    "Setting": {
        "title": "Setting Phase (Descending) — Saturn in 2nd from Moon",
        "description": (
            "The final phase of Sade Sati. Saturn transits the 2nd house from your Moon sign, "
            "affecting finances, family, speech, and accumulated wealth. The intensity begins to ease. "
            "Financial pressures may persist but you are now stronger. Family dynamics require attention."
        ),
        "effects": [
            "Financial fluctuations — savings may be tested",
            "Family responsibilities increase",
            "Speech and communication need care",
            "Health of family elders may need attention",
            "Gradual easing of overall pressure",
        ],
    },
}

SADE_SATI_PHASES_HI = {
    "Rising": {
        "title": "आरंभिक चरण (उदय) — शनि चन्द्र से 12वें भाव में",
        "description": (
            "साढ़ेसाती का प्रारम्भ। शनि आपकी चन्द्र राशि से 12वें भाव में गोचर कर रहे हैं, "
            "जिससे खर्च, नींद, विदेश यात्रा और आध्यात्मिक मामलों पर प्रभाव पड़ता है। "
            "खर्चों में वृद्धि, नींद में बाधा, एकांत की भावना या विदेश यात्रा संभव है। "
            "यह चरण आंतरिक परिवर्तन और आध्यात्मिक जागरण लाता है।"
        ),
        "effects": [
            "खर्चों में वृद्धि या आर्थिक दबाव",
            "नींद में बाधा या विचित्र स्वप्न",
            "एकांत या वैराग्य की भावना",
            "विदेश यात्रा या स्थानान्तरण की संभावना",
            "आंतरिक परिवर्तन का प्रारम्भ",
        ],
    },
    "Peak": {
        "title": "चरम चरण (शीर्ष) — शनि चन्द्र राशि पर",
        "description": (
            "साढ़ेसाती का सबसे तीव्र चरण। शनि सीधे आपकी चन्द्र राशि पर गोचर कर रहे हैं, "
            "जिससे भावनात्मक और मानसिक स्थिति पर अधिकतम दबाव पड़ता है। "
            "यह गहन कार्मिक शिक्षा का समय है। चुनौतीपूर्ण होते हुए भी, "
            "यह असाधारण सहनशीलता और परिपक्वता निर्मित करता है।"
        ),
        "effects": [
            "भावनात्मक उथल-पुथल और मानसिक तनाव",
            "स्वास्थ्य समस्याएँ — विशेषकर मन/भावनाओं से संबंधित",
            "करियर में चुनौतियाँ या बड़े पेशेवर परिवर्तन",
            "रिश्तों में तनाव — धैर्य आवश्यक",
            "गहन व्यक्तिगत परिवर्तन और परिपक्वता",
        ],
    },
    "Setting": {
        "title": "अंतिम चरण (अस्त) — शनि चन्द्र से 2रे भाव में",
        "description": (
            "साढ़ेसाती का अंतिम चरण। शनि आपकी चन्द्र राशि से 2रे भाव में गोचर कर रहे हैं, "
            "जिससे धन, परिवार, वाणी और संचित सम्पत्ति प्रभावित होती है। "
            "तीव्रता कम होने लगती है। आर्थिक दबाव बना रह सकता है "
            "पर अब आप पहले से मज़बूत हैं। पारिवारिक मामलों पर ध्यान दें।"
        ),
        "effects": [
            "आर्थिक उतार-चढ़ाव — बचत की परीक्षा",
            "पारिवारिक जिम्मेदारियों में वृद्धि",
            "वाणी और संवाद में सावधानी आवश्यक",
            "परिवार के बड़ों के स्वास्थ्य पर ध्यान दें",
            "समग्र दबाव में क्रमिक कमी",
        ],
    },
}

SADE_SATI_REMEDIES_EN = {
    "spiritual": [
        "Recite Hanuman Chalisa on Saturdays",
        "Light a sesame oil lamp on Saturday evenings",
        "Donate black items (sesame, black cloth, iron) on Saturdays",
        "Visit Shani temple on Saturdays",
        "Chant 'Om Sham Shanaischaraya Namah' 108 times daily",
    ],
    "karma": [
        "Serve the elderly and underprivileged — Saturn rewards service",
        "Practice extreme discipline in daily routine",
        "Accept delays with patience — do not take shortcuts",
        "Be honest in all dealings — Saturn punishes dishonesty harshly",
        "Take responsibility for your mistakes without blaming others",
        "Reduce ego and practice humility",
        "Maintain physical fitness — Saturn governs bones and joints",
    ],
    "practical": [
        "Avoid major financial risks during Peak phase",
        "Strengthen savings and reduce debt",
        "Maintain regular health checkups",
        "Keep relationships drama-free — practice patience",
        "Use this period for serious study or skill-building",
    ],
}

SADE_SATI_REMEDIES_HI = {
    "spiritual": [
        "शनिवार को हनुमान चालीसा का पाठ करें",
        "शनिवार संध्या को तिल के तेल का दीपक जलाएँ",
        "शनिवार को काली वस्तुओं (तिल, काला कपड़ा, लोहा) का दान करें",
        "शनिवार को शनि मंदिर जाएँ",
        "प्रतिदिन 'ॐ शं शनैश्चराय नमः' का 108 बार जाप करें",
    ],
    "karma": [
        "बुजुर्गों और वंचितों की सेवा करें — शनि सेवा का पुरस्कार देते हैं",
        "दैनिक दिनचर्या में कठोर अनुशासन रखें",
        "विलम्ब को धैर्य से स्वीकारें — शॉर्टकट न अपनाएँ",
        "सभी व्यवहारों में ईमानदार रहें — शनि बेईमानी को कठोर दण्ड देते हैं",
        "अपनी गलतियों की ज़िम्मेदारी लें, दूसरों को दोष न दें",
        "अहंकार कम करें और विनम्रता का अभ्यास करें",
        "शारीरिक स्वस्थता बनाए रखें — शनि हड्डियों और जोड़ों के स्वामी हैं",
    ],
    "practical": [
        "चरम चरण में बड़े आर्थिक जोखिमों से बचें",
        "बचत मज़बूत करें और ऋण कम करें",
        "नियमित स्वास्थ्य जाँच कराएँ",
        "रिश्तों में शांति रखें — धैर्य का अभ्यास करें",
        "इस काल का उपयोग गम्भीर अध्ययन या कौशल-निर्माण के लिए करें",
    ],
}


# ─── Gochar (Transit) Interpretation Data ─────────────────────────────────────

# Standard Vedic benefic houses for each planet (from Moon sign)
GOCHAR_BENEFIC_HOUSES = {
    "Sun":     [3, 6, 10, 11],
    "Moon":    [1, 3, 6, 7, 10, 11],
    "Mars":    [3, 6, 11],
    "Mercury": [2, 4, 6, 8, 10, 11],
    "Jupiter": [2, 5, 7, 9, 11],
    "Venus":   [1, 2, 3, 4, 5, 8, 9, 11, 12],
    "Saturn":  [3, 6, 11],
    "Rahu":    [3, 6, 10, 11],
    "Ketu":    [3, 6, 10, 11],
}

# Transit effects per planet per house from Moon
GOCHAR_EFFECTS = {
    "Sun": {
        1: "Focus on self, health awareness needed. Avoid ego conflicts with superiors.",
        2: "Financial caution advised. Possible eye-related issues. Watch expenses.",
        3: "Courage and confidence rise. Victory over rivals. Good for short travels.",
        4: "Domestic unrest possible. Vehicle-related caution. Mental stress.",
        5: "Challenges with children or investments. Creative blocks. Stomach issues.",
        6: "Victory over enemies and competitors. Health improves. Government favour.",
        7: "Travel likely. Relationship friction. Partnership disagreements.",
        8: "Health caution — fever, fatigue. Avoid risky ventures. Low vitality.",
        9: "Obstacles in long travels. Tension with father or mentor. Spiritual tests.",
        10: "Career success and recognition. Authority figures supportive. Public honour.",
        11: "Financial gains and social success. Goals achieved. Happy period.",
        12: "Expenditure rises. Eye or head issues. Government-related stress.",
    },
    "Moon": {
        1: "Emotional well-being and comfort. Good health. Pleasant period.",
        2: "Financial gains possible. Family harmony. Good food and comforts.",
        3: "Success in endeavours. Courage increases. Favourable for siblings.",
        4: "Emotional unease. Fear and anxiety. Domestic tension.",
        5: "Mental worry about children. Emotional instability. Poor digestion.",
        6: "Victory over enemies. Health recovery. Good for competitive matters.",
        7: "Social happiness. Good relationships. Travel with comfort.",
        8: "Emotional disturbance. Health issues. Unexpected expenses.",
        9: "Spiritual inclination. Pilgrimage possible. Positive mindset.",
        10: "Professional success. Public recognition. Emotional satisfaction.",
        11: "Gains and fulfilment. Happy social circle. Wishes come true.",
        12: "Expenditure and emotional drain. Sleep disturbance. Restlessness.",
    },
    "Mars": {
        1: "Health issues — fever, blood pressure. Accidents possible. Anger rises.",
        2: "Financial losses. Family conflicts. Speech-related problems.",
        3: "Courage and victory. Success in competition. Property gains possible.",
        4: "Domestic problems. Vehicle accidents possible. Blood-related issues.",
        5: "Conflicts with children. Investment losses. Stomach or surgical issues.",
        6: "Victory over enemies. Legal success. Health improves significantly.",
        7: "Marital discord. Partnership conflicts. Travel with difficulties.",
        8: "Accidents and health risks. Surgical situations. Financial setbacks.",
        9: "Conflicts with elders. Legal issues. Unnecessary aggression.",
        10: "Professional challenges. Conflicts with authority. Hard work required.",
        11: "Financial gains. Goals achieved through effort. Social success.",
        12: "Expenditure rises. Hidden enemies active. Hospitalisation possible.",
    },
    "Mercury": {
        1: "Communication issues. Skin problems. Nervous tension.",
        2: "Financial gains through trade. Good speech. Business success.",
        3: "Conflicts with siblings. Communication breakdown. Short travel issues.",
        4: "Educational success. Property gains. Mental peace and clarity.",
        5: "Intellectual achievements. Good for students. Creative success.",
        6: "Victory through intelligence. Legal wins. Health improvement.",
        7: "Business partnerships thrive. Good negotiations. Travel for trade.",
        8: "Research success. Inheritance possible. Hidden knowledge revealed.",
        9: "Spiritual learning. Higher education success. Teaching opportunities.",
        10: "Career advancement through communication. Writing success. Recognition.",
        11: "Financial gains through intellect. Social networking success. Wishes fulfilled.",
        12: "Expenditure on education. Foreign connections. Sleep disturbance.",
    },
    "Jupiter": {
        1: "Health issues possible. Weight gain. Lack of focus. Displacement.",
        2: "Wealth increase. Family happiness. Good speech and knowledge. Excellent period.",
        3: "Displacement or role change. Sibling issues. Loss of position.",
        4: "Loss of happiness. Domestic issues. Vehicle problems. Mental unease.",
        5: "Birth of children. Educational success. Spiritual growth. Excellent period.",
        6: "Defeat by enemies. Health issues. Legal problems. Debts increase.",
        7: "Marriage or strong partnership. Spouse happiness. Travel. Very auspicious.",
        8: "Obstacles and delays. Health issues. Loss of reputation. Difficult transit.",
        9: "Excellent fortune. Pilgrimage. Higher learning. Guru blessing. Best transit.",
        10: "Career setbacks. Loss of position. Humiliation possible. Challenging.",
        11: "Maximum gains. Wishes fulfilled. Birth of children. Best financial period.",
        12: "Expenditure and losses. Change of residence. Spiritual journey. Isolation.",
    },
    "Venus": {
        1: "Comfort and luxury. Romantic happiness. Good health and appearance.",
        2: "Family wealth increases. Good food and comforts. Harmonious speech.",
        3: "Success in artistic endeavours. Good relationships. Social popularity.",
        4: "Domestic happiness. Vehicle or property acquisition. Comfortable home.",
        5: "Romantic relationships. Creative success. Children's happiness.",
        6: "Challenges in relationships. Health awareness needed. Enemy troubles.",
        7: "Relationship difficulties. Partnership tension. Avoid new commitments.",
        8: "Wealth through unexpected sources. Occult interests. Transformation.",
        9: "Spiritual and cultural pursuits. Pilgrimage. Fortune through arts.",
        10: "Career difficulties. Reputation concerns. Professional jealousy.",
        11: "Social success and gains. Luxuries increase. Wishes fulfilled.",
        12: "Expenditure on pleasures. Bed comforts. Foreign travel possible.",
    },
    "Saturn": {
        1: "Health issues. Mental heaviness. Physical fatigue. Sade Sati effects.",
        2: "Financial difficulties. Family tensions. Speech problems.",
        3: "Relief from difficulties. Success after struggle. Good for servants.",
        4: "Domestic unhappiness. Mother's health concern. Property disputes.",
        5: "Children-related worries. Investment losses. Mental anxiety.",
        6: "Victory over enemies. Health improvement. Debt clearance. Good period.",
        7: "Marital challenges. Partner's health. Travel with hardship.",
        8: "Health risks. Chronic issues flare up. Legal problems. Difficult period.",
        9: "Obstacles in fortune. Father's health. Spiritual crisis.",
        10: "Career pressure. Hard work without proportional reward. Responsibilities.",
        11: "Steady gains. Long-term goals materialise. Social recognition. Good period.",
        12: "Expenditure and losses. Isolation. Foreign stay. Hospitalisation possible.",
    },
    "Rahu": {
        1: "Confusion about identity. Health anxiety. Foreign influence strong.",
        2: "Financial irregularities. Family misunderstandings. Speech problems.",
        3: "Courage through unconventional means. Success in technology. Good period.",
        4: "Domestic confusion. Property disputes. Mother's concern.",
        5: "Unconventional thinking. Risky investments. Children's concerns.",
        6: "Victory over enemies through cunning. Legal success. Health recovery.",
        7: "Unusual relationships. Foreign partner possible. Partnership confusion.",
        8: "Hidden matters surface. Research breakthroughs. Health scares.",
        9: "Unconventional spiritual path. Foreign travel. Guru confusion.",
        10: "Sudden career changes. Unconventional success. Technology-driven growth.",
        11: "Gains through foreign connections. Unexpected profits. Wishes fulfilled.",
        12: "Foreign travel or residence. Expenditure. Spiritual seeking. Isolation.",
    },
    "Ketu": {
        1: "Spiritual awakening. Health confusion. Identity transformation.",
        2: "Family detachment. Financial unpredictability. Speech confusion.",
        3: "Spiritual courage. Victory through intuition. Good for meditation.",
        4: "Domestic detachment. Property letting go. Inner peace sought.",
        5: "Past-life connections with children. Intuitive insights. Spiritual study.",
        6: "Spiritual victory over enemies. Karmic debt clearance. Good period.",
        7: "Karmic relationship lessons. Detachment from partnerships.",
        8: "Sudden spiritual experiences. Research into occult. Transformation.",
        9: "Deep spiritual growth. Past-life karma resolution. Pilgrimage.",
        10: "Career detachment. Seeking purpose beyond material success.",
        11: "Unexpected spiritual gains. Letting go of desires brings fulfilment.",
        12: "Moksha-oriented. Liberation. Foreign ashram. Spiritual culmination.",
    },
}

SADE_SATI_TEXT = {
    "rising": (
        "Sade Sati (Rising Phase): Saturn is transiting the 12th house from your Moon sign, "
        "marking the beginning of the 7.5-year Sade Sati period. You may experience increased "
        "expenditure, sleep disturbances, and a sense of unease. Financial caution is advised. "
        "This phase prepares you for the deeper lessons ahead. Practice patience and build savings."
    ),
    "peak": (
        "Sade Sati (Peak Phase): Saturn is transiting over your natal Moon sign. This is the "
        "most intense phase of Sade Sati. Emotional pressure, career challenges, health concerns, "
        "and mental heaviness are common. However, this is also a powerful period for inner growth "
        "and building lasting resilience. Stay disciplined, avoid shortcuts, and lean on spiritual practice."
    ),
    "setting": (
        "Sade Sati (Setting Phase): Saturn is transiting the 2nd house from your Moon sign. "
        "The intense pressure is gradually easing. Financial matters need continued attention. "
        "Family relationships may still feel strained. The lessons of Sade Sati are integrating — "
        "you are emerging stronger and wiser. Continue steady efforts."
    ),
}

SADE_SATI_TEXT_HI = {
    "rising": (
        "साढ़ेसाती (आरंभिक चरण): शनि आपकी चन्द्र राशि से 12वें भाव में गोचर कर रहे हैं। "
        "खर्च में वृद्धि, नींद में बाधा और बेचैनी हो सकती है। "
        "धैर्य रखें और बचत करें।"
    ),
    "peak": (
        "साढ़ेसाती (चरम चरण): शनि आपकी चन्द्र राशि पर गोचर कर रहे हैं। "
        "यह सबसे तीव्र चरण है। भावनात्मक दबाव, करियर चुनौतियाँ, "
        "स्वास्थ्य चिंताएँ और मानसिक भारीपन हो सकता है। "
        "अनुशासन बनाए रखें, आध्यात्मिक साधना करें।"
    ),
    "setting": (
        "साढ़ेसाती (अंतिम चरण): शनि आपकी चन्द्र राशि से 2रे भाव में हैं। "
        "तीव्र दबाव धीरे-धीरे कम हो रहा है। "
        "आर्थिक मामलों पर ध्यान दें। स्थिर प्रयास जारी रखें।"
    ),
}

# Hindi labels for readings
_HI_LABELS = {
    "overview": "सारांश",
    "reading_for": "पाठन",
    "moon_sign": "चन्द्र राशि",
    "period": "अवधि",
    "current_dasha": "वर्तमान दशा",
    "mahadasha": "महादशा",
    "antardasha": "अन्तर्दशा",
    "pratyantar": "प्रत्यन्तर दशा",
    "dasha_influence": "दशा प्रभाव",
    "transit_effects": "गोचर प्रभाव",
    "this_week": "इस सप्ताह का व्यक्तिगत पाठन",
    "this_month": "इस महीने का व्यक्तिगत पाठन",
    "this_year": "इस वर्ष का व्यक्तिगत पाठन",
    "nature": "प्रकृति",
    "themes": "विषय",
    "strengths": "शक्तियाँ",
    "caution": "सावधानी",
    "advice": "सलाह",
    "guidance": "मार्गदर्शन और सारांश",
    "favourable": "अनुकूल",
    "challenging": "चुनौतीपूर्ण",
    "house": "भाव",
    "from_moon": "चन्द्र से",
    "retrograde": "वक्री",
    "sade_sati": "साढ़ेसाती सूचना",
    "weekly_transits": "इस सप्ताह के प्रमुख ग्रह गोचर",
    "monthly_transits": "इस माह के ग्रह गोचर",
    "yearly_transits": "इस वर्ष के प्रमुख गोचर",
    "overall_positive": "कुल मिलाकर, ग्रह गोचर <strong>अधिकांशतः अनुकूल</strong> हैं।",
    "overall_mixed": "ग्रह गोचर <strong>मिश्रित</strong> हैं — कुछ क्षेत्र अच्छे, कुछ में सावधानी चाहिए।",
    "overall_challenging": "ग्रह गोचर <strong>चुनौतीपूर्ण</strong> हैं — धैर्य और योजना आवश्यक है।",
}

# Hindi gochar effects (short summaries per planet per house from Moon)
GOCHAR_EFFECTS_HI = {
    "Sun": {
        1: "आत्म-चिंतन, स्वास्थ्य पर ध्यान दें। अहंकार से बचें।",
        2: "आर्थिक सावधानी। नेत्र संबंधी समस्याएँ। खर्च पर नियंत्रण।",
        3: "साहस और आत्मविश्वास बढ़ता है। प्रतिद्वंद्वियों पर विजय।",
        4: "घरेलू अशांति। वाहन से सावधानी। मानसिक तनाव।",
        5: "संतान या निवेश में चुनौती। रचनात्मक अवरोध। पेट संबंधी समस्या।",
        6: "शत्रुओं पर विजय। स्वास्थ्य सुधरता। सरकारी कृपा।",
        7: "यात्रा संभव। रिश्तों में तनाव। साझेदारी में मतभेद।",
        8: "स्वास्थ्य सावधानी — बुखार, थकान। जोखिम वाले कार्यों से बचें।",
        9: "लंबी यात्राओं में बाधा। पिता/गुरु से तनाव। आध्यात्मिक परीक्षा।",
        10: "करियर में सफलता और मान्यता। अधिकारियों का समर्थन।",
        11: "आर्थिक लाभ और सामाजिक सफलता। लक्ष्य प्राप्ति। शुभ समय।",
        12: "खर्च बढ़ता है। नेत्र/शीर्ष समस्या। सरकारी तनाव।",
    },
    "Moon": {
        1: "भावनात्मक सुख और आराम। अच्छा स्वास्थ्य।",
        2: "आर्थिक लाभ। पारिवारिक सामंजस्य। अच्छा भोजन और सुख।",
        3: "कार्यों में सफलता। साहस बढ़ता है।",
        4: "भावनात्मक अशांति। भय और चिंता। घरेलू तनाव।",
        5: "संतान की चिंता। भावनात्मक अस्थिरता।",
        6: "शत्रुओं पर विजय। स्वास्थ्य सुधार।",
        7: "सामाजिक सुख। अच्छे संबंध। आरामदायक यात्रा।",
        8: "भावनात्मक विक्षोभ। स्वास्थ्य समस्या। अप्रत्याशित खर्च।",
        9: "आध्यात्मिक रुझान। तीर्थयात्रा संभव। सकारात्मक मानसिकता।",
        10: "पेशेवर सफलता। सार्वजनिक मान्यता। भावनात्मक संतोष।",
        11: "लाभ और पूर्ति। शुभ सामाजिक वृत्त। इच्छापूर्ति।",
        12: "खर्च और भावनात्मक थकान। नींद में बाधा। बेचैनी।",
    },
    "Mars": {
        1: "स्वास्थ्य समस्या — बुखार, रक्तचाप। दुर्घटना संभव। क्रोध बढ़ता है।",
        2: "आर्थिक हानि। पारिवारिक विवाद। वाणी संबंधी समस्या।",
        3: "साहस और विजय। प्रतियोगिता में सफलता। संपत्ति लाभ संभव।",
        4: "घरेलू समस्या। वाहन दुर्घटना संभव। रक्त संबंधी समस्या।",
        5: "संतान से विवाद। निवेश हानि। शल्य क्रिया संभव।",
        6: "शत्रुओं पर विजय। कानूनी सफलता। स्वास्थ्य सुधार।",
        7: "वैवाहिक विवाद। साझेदारी संघर्ष। कठिन यात्रा।",
        8: "दुर्घटना और स्वास्थ्य जोखिम। शल्य क्रिया। आर्थिक हानि।",
        9: "बड़ों से विवाद। कानूनी समस्या। अनावश्यक आक्रामकता।",
        10: "पेशेवर चुनौती। अधिकारियों से विवाद। कठिन परिश्रम।",
        11: "आर्थिक लाभ। प्रयास से लक्ष्य प्राप्ति। सामाजिक सफलता।",
        12: "खर्च बढ़ता है। छिपे शत्रु सक्रिय। अस्पताल में भर्ती संभव।",
    },
    "Mercury": {
        1: "संचार समस्या। त्वचा रोग। तनाव।",
        2: "व्यापार से आर्थिक लाभ। अच्छी वाणी।",
        3: "भाई-बहनों से विवाद। संचार भंग।",
        4: "शैक्षिक सफलता। संपत्ति लाभ। मानसिक शांति।",
        5: "बौद्धिक उपलब्धियाँ। छात्रों के लिए अच्छा। रचनात्मक सफलता।",
        6: "बुद्धि से विजय। कानूनी जीत। स्वास्थ्य सुधार।",
        7: "व्यापारिक साझेदारी फलती है। अच्छी वार्ता। व्यापार यात्रा।",
        8: "शोध सफलता। विरासत संभव। छिपा ज्ञान प्रकट।",
        9: "आध्यात्मिक शिक्षा। उच्च शिक्षा सफलता। शिक्षण के अवसर।",
        10: "संचार द्वारा करियर उन्नति। लेखन सफलता। मान्यता।",
        11: "बुद्धि से आर्थिक लाभ। सामाजिक नेटवर्किंग सफल। इच्छापूर्ति।",
        12: "शिक्षा पर खर्च। विदेशी संबंध। नींद में बाधा।",
    },
    "Jupiter": {
        1: "स्वास्थ्य समस्या। वजन वृद्धि। ध्यान की कमी। स्थान परिवर्तन।",
        2: "धन वृद्धि। पारिवारिक सुख। अच्छी वाणी और ज्ञान। उत्तम समय।",
        3: "स्थान परिवर्तन। भाई-बहन समस्या। पद हानि।",
        4: "सुख की हानि। घरेलू समस्या। वाहन समस्या। मानसिक अशांति।",
        5: "संतान जन्म। शैक्षिक सफलता। आध्यात्मिक विकास। उत्तम समय।",
        6: "शत्रुओं से पराजय। स्वास्थ्य समस्या। कानूनी समस्या। ऐण वृद्धि।",
        7: "विवाह या शक्तिशाली साझेदारी। पत्नी सुख। यात्रा। अत्यंत शुभ।",
        8: "बाधाएँ और विलम्ब। स्वास्थ्य समस्या। प्रतिष्ठा हानि। कठिन समय।",
        9: "उत्तम भाग्य। तीर्थयात्रा। उच्च शिक्षा। गुरु कृपा। सर्वश्रेष्ठ गोचर।",
        10: "करियर में हानि। पद हानि। अपमान संभव। चुनौतीपूर्ण।",
        11: "अधिकतम लाभ। इच्छापूर्ति। संतान जन्म। सर्वश्रेष्ठ आर्थिक समय।",
        12: "खर्च और हानि। निवास परिवर्तन। आध्यात्मिक यात्रा। एकांत।",
    },
    "Venus": {
        1: "आराम और विलास। रोमांटिक सुख। अच्छा स्वास्थ्य।",
        2: "पारिवारिक धन वृद्धि। अच्छा भोजन। सुखद वाणी।",
        3: "कलात्मक सफलता। अच्छे संबंध। सामाजिक लोकप्रियता।",
        4: "घरेलू सुख। वाहन/संपत्ति प्राप्ति। आरामदायक घर।",
        5: "रोमांटिक संबंध। रचनात्मक सफलता। संतान सुख।",
        6: "संबंधों में चुनौती। स्वास्थ्य सावधानी। शत्रु कष्ट।",
        7: "संबंधों में कठिनाई। साझेदारी तनाव। नई प्रतिबद्धताओं से बचें।",
        8: "अप्रत्याशित स्रोतों से धन। तांत्रिक रुचि। परिवर्तन।",
        9: "आध्यात्मिक और सांस्कृतिक कार्य। तीर्थयात्रा। कला से भाग्य।",
        10: "करियर कठिनाई। प्रतिष्ठा चिंता। पेशेवर ईर्ष्या।",
        11: "सामाजिक सफलता और लाभ। विलासिता बढ़ती है। इच्छापूर्ति।",
        12: "सुखों पर खर्च। शय्या सुख। विदेश यात्रा संभव।",
    },
    "Saturn": {
        1: "स्वास्थ्य समस्या। मानसिक भारीपन। शारीरिक थकान। साढ़ेसाती प्रभाव।",
        2: "आर्थिक कठिनाई। पारिवारिक तनाव। वाणी समस्या।",
        3: "कठिनाइयों से राहत। संघर्ष के बाद सफलता। शुभ समय।",
        4: "घरेलू दुख। माता के स्वास्थ्य चिंता। संपत्ति विवाद।",
        5: "संतान संबंधी चिंता। निवेश हानि। मानसिक चिंता।",
        6: "शत्रुओं पर विजय। स्वास्थ्य सुधार। ऐण मुक्ति। शुभ समय।",
        7: "वैवाहिक चुनौती। साथी के स्वास्थ्य। कठिन यात्रा।",
        8: "स्वास्थ्य जोखिम। जीर्ण रोग बढ़े। कानूनी समस्या। कठिन समय।",
        9: "भाग्य में बाधा। पिता के स्वास्थ्य। आध्यात्मिक संकट।",
        10: "करियर दबाव। कठिन परिश्रम बिना अनुपातिक फल। जिम्मेदारियाँ।",
        11: "स्थिर लाभ। दीर्घकालिक लक्ष्य पूरे होते हैं। सामाजिक मान्यता। शुभ समय।",
        12: "खर्च और हानि। एकांत। विदेश प्रवास। अस्पताल में भर्ती संभव।",
    },
    "Rahu": {
        1: "पहचान में भ्रम। स्वास्थ्य चिंता। विदेशी प्रभाव प्रबल।",
        2: "आर्थिक अनियमितता। परिवार गलतफहमी। वाणी समस्या।",
        3: "अपरंपरागत साधनों से साहस। तकनीक में सफलता। शुभ समय।",
        4: "घरेलू भ्रम। संपत्ति विवाद। माता की चिंता।",
        5: "अपरंपरागत सोच। जोखिम निवेश। संतान चिंता।",
        6: "चालाकी से शत्रुओं पर विजय। कानूनी सफलता। स्वास्थ्य सुधार।",
        7: "असामान्य संबंध। विदेशी साथी संभव। साझेदारी भ्रम।",
        8: "छिपे मामले प्रकट। शोध सफलता। स्वास्थ्य भय।",
        9: "अपरंपरागत आध्यात्मिक मार्ग। विदेश यात्रा। गुरु भ्रम।",
        10: "अचानक करियर परिवर्तन। अपरंपरागत सफलता। तकनीक-चालित वृद्धि।",
        11: "विदेशी संबंधों से लाभ। अप्रत्याशित लाभ। इच्छापूर्ति।",
        12: "विदेश यात्रा/निवास। खर्च। आध्यात्मिक खोज। एकांत।",
    },
    "Ketu": {
        1: "आध्यात्मिक जागरण। स्वास्थ्य भ्रम। पहचान परिवर्तन।",
        2: "पारिवारिक वैराग्य। आर्थिक अनिश्चितता। वाणी भ्रम।",
        3: "आध्यात्मिक साहस। अंतर्ज्ञान से विजय। ध्यान के लिए अच्छा।",
        4: "घरेलू वैराग्य। संपत्ति त्याग। आंतरिक शांति की खोज।",
        5: "संतान से पूर्व जन्म संबंध। अंतर्ज्ञान से अंतर्दृष्टि। आध्यात्मिक अध्ययन।",
        6: "आध्यात्मिक विजय। कार्मिक ऐण मुक्ति। शुभ समय।",
        7: "कार्मिक संबंध सबक। साझेदारी से वैराग्य।",
        8: "अचानक आध्यात्मिक अनुभव। तांत्रिक शोध। परिवर्तन।",
        9: "गहरी आध्यात्मिक वृद्धि। पूर्व जन्म कर्म समाधान। तीर्थयात्रा।",
        10: "करियर वैराग्य। भौतिक सफलता से परे उद्देश्य की खोज।",
        11: "अप्रत्याशित आध्यात्मिक लाभ। इच्छाओं को छोड़ने से पूर्ति।",
        12: "मोक्ष-उन्मुख। मुक्ति। विदेशी आश्रम। आध्यात्मिक परिणति।",
    },
}


# ─── Personalized Reading Generator ──────────────────────────────────────────

def _find_current_dasha_periods(chart, today):
    """Find current Maha, Antar, and Pratyantar dasha periods."""
    current_maha = current_antar = current_prat = None
    current_maha_data = current_antar_data = current_prat_data = None
    next_maha_data = next_antar_data = None

    for i, (lord, start, end, yrs) in enumerate(chart['dashas']):
        if start <= today < end:
            current_maha = lord
            current_maha_data = (lord, start, end, yrs)
            if i + 1 < len(chart['dashas']):
                next_maha_data = chart['dashas'][i + 1]
            break

    if current_maha:
        ad_list = chart.get('antardasha', {}).get(current_maha, [])
        for i, (ad_lord, ad_start, ad_end, ad_yrs) in enumerate(ad_list):
            if ad_start <= today < ad_end:
                current_antar = ad_lord
                current_antar_data = (ad_lord, ad_start, ad_end, ad_yrs)
                if i + 1 < len(ad_list):
                    next_antar_data = ad_list[i + 1]
                break

    if current_maha and current_antar:
        key = (current_maha, current_antar)
        pd_list = chart.get('pratyantar', {}).get(key, [])
        for pd_lord, pd_start, pd_end, pd_yrs in pd_list:
            if pd_start <= today < pd_end:
                current_prat = pd_lord
                current_prat_data = (pd_lord, pd_start, pd_end, pd_yrs)
                break

    return {
        'maha': current_maha, 'maha_data': current_maha_data,
        'antar': current_antar, 'antar_data': current_antar_data,
        'prat': current_prat, 'prat_data': current_prat_data,
        'next_maha': next_maha_data, 'next_antar': next_antar_data,
    }


def generate_personalized_reading(birth_data, period="week", lang="en"):
    """
    Generate personalized reading combining natal chart, dashas, and transits.
    period: "week", "month", or "year"
    lang: "en" or "hi"
    Returns dict with 'title' and 'sections' (list of {heading, content}).
    """
    chart = generate_chart(birth_data)
    today = datetime.now()
    moon_sign_idx = chart['planets']['Moon']['sign_idx']
    moon_sign = chart['planets']['Moon']['sign_en']

    if lang == "hi":
        dasha_data = DASHA_READING_HI
        gochar_data = GOCHAR_EFFECTS_HI
        sade_sati_data = SADE_SATI_TEXT_HI
        labels = _HI_LABELS
        planet_names = PLANET_HI_FULL
        moon_sign_display = chart['planets']['Moon']['sign_hi']
    else:
        dasha_data = DASHA_READING
        gochar_data = GOCHAR_EFFECTS
        sade_sati_data = SADE_SATI_TEXT
        labels = None
        planet_names = None
        moon_sign_display = moon_sign

    # Get current transits
    transits = current_transits(today)

    # Get current dasha periods
    dasha_info = _find_current_dasha_periods(chart, today)

    # Analyze transit houses from Moon
    transit_analysis = {}
    for planet, tdata in transits.items():
        house = transit_house_from_moon(moon_sign_idx, tdata['sign_idx'])
        is_benefic = house in GOCHAR_BENEFIC_HOUSES.get(planet, [])
        effect = gochar_data.get(planet, {}).get(house, "")
        transit_analysis[planet] = {
            'house': house, 'sign': tdata['sign_en'],
            'sign_hi': tdata.get('sign_hi', tdata['sign_en']),
            'is_benefic': is_benefic, 'effect': effect,
            'retro': tdata.get('retro', False),
        }

    # Detect Sade Sati
    saturn_sign_idx = transits['Saturn']['sign_idx']
    sade_sati = detect_sade_sati(moon_sign_idx, saturn_sign_idx)

    # Build sections based on period
    sections = []

    # ── Section 1: Overview ──
    if period == "week":
        date_end = today + timedelta(days=7)
        period_label = f"{today.strftime('%d %b')} – {date_end.strftime('%d %b %Y')}"
        title = labels["this_week"] if lang == "hi" else "This Week's Personalized Reading"
    elif period == "month":
        period_label = today.strftime('%B %Y')
        title = labels["this_month"] if lang == "hi" else "This Month's Personalized Reading"
    else:
        period_label = today.strftime('%Y')
        title = labels["this_year"] if lang == "hi" else "This Year's Personalized Reading"

    # Overview section
    if lang == "hi":
        overview = f"<p>{labels['reading_for']} <strong>{birth_data['name']}</strong> · {labels['moon_sign']}: <strong>{moon_sign_display}</strong> · {labels['period']}: <strong>{period_label}</strong></p>"
    else:
        overview = f"<p>Reading for <strong>{birth_data['name']}</strong> · Moon Sign: <strong>{moon_sign}</strong> · Period: <strong>{period_label}</strong></p>"

    if dasha_info['maha']:
        maha = dasha_info['maha']
        if lang == "hi":
            maha_hi = planet_names.get(maha, maha)
            overview += f"<p>{labels['current_dasha']}: <strong>{maha_hi} {labels['mahadasha']}</strong>"
            if dasha_info['antar']:
                antar_hi = planet_names.get(dasha_info['antar'], dasha_info['antar'])
                overview += f" → <strong>{antar_hi} {labels['antardasha']}</strong>"
            if dasha_info['prat']:
                prat_hi = planet_names.get(dasha_info['prat'], dasha_info['prat'])
                overview += f" → <strong>{prat_hi} {labels['pratyantar']}</strong>"
        else:
            overview += f"<p>Current Dasha: <strong>{maha} Mahadasha</strong>"
            if dasha_info['antar']:
                overview += f" → <strong>{dasha_info['antar']} Antardasha</strong>"
            if dasha_info['prat']:
                overview += f" → <strong>{dasha_info['prat']} Pratyantar</strong>"
        overview += "</p>"

    sections.append({"heading": labels["overview"] if lang == "hi" else "Overview", "content": overview})

    # ── Section 2: Dasha Influence ──
    if dasha_info['maha']:
        maha = dasha_info['maha']
        maha_info = dasha_data.get(maha, {})

        if period == "week" and dasha_info['prat']:
            # Weekly: focus on Pratyantar
            prat = dasha_info['prat']
            prat_info = dasha_data.get(prat, {})
            prat_end = dasha_info['prat_data'][2]
            if lang == "hi":
                prat_hi = planet_names.get(prat, prat)
                maha_hi = planet_names.get(maha, maha)
                antar_hi = planet_names.get(dasha_info['antar'], dasha_info['antar'])
                dasha_content = (
                    f"<p>आपका तात्कालिक प्रभाव <strong>{prat_hi} {labels['pratyantar']}</strong> "
                    f"({prat_end.strftime('%d %b %Y')} तक) है, जो "
                    f"<strong>{prat_info.get('nature', 'महत्वपूर्ण')}</strong> {labels['nature']} का है।</p>"
                    f"<p><strong>इस सप्ताह की ऊर्जा:</strong> {prat_info.get('themes', 'विभिन्न जीवन परिवर्तन')}।</p>"
                    f"<p><strong>{labels['strengths']}:</strong> {prat_info.get('positive', 'विकास के अवसर')}।</p>"
                    f"<p><strong>{labels['caution']}:</strong> {prat_info.get('challenges', 'चुनौतियाँ आ सकती हैं')}।</p>"
                )
                sections.append({"heading": f"{labels['dasha_influence']}: {maha_hi}–{antar_hi}–{prat_hi}", "content": dasha_content})
            else:
                dasha_content = (
                    f"<p>Your immediate influence is the <strong>{prat} Pratyantar Dasha</strong> "
                    f"(until {prat_end.strftime('%d %b %Y')}), which is "
                    f"<strong>{prat_info.get('nature', 'significant')}</strong> in nature.</p>"
                    f"<p><strong>This week's energy:</strong> {prat_info.get('themes', 'Various life changes')}.</p>"
                    f"<p><strong>Opportunities:</strong> {prat_info.get('positive', 'Growth opportunities')}.</p>"
                    f"<p><strong>Watch out for:</strong> {prat_info.get('challenges', 'Challenges may arise')}.</p>"
                )
                sections.append({"heading": f"Dasha Influence: {maha}–{dasha_info['antar']}–{prat}", "content": dasha_content})

        elif period == "month" and dasha_info['antar']:
            # Monthly: focus on Antardasha
            antar = dasha_info['antar']
            antar_info = dasha_data.get(antar, {})
            antar_end = dasha_info['antar_data'][2]
            if lang == "hi":
                antar_hi = planet_names.get(antar, antar)
                maha_hi = planet_names.get(maha, maha)
                dasha_content = (
                    f"<p>इस महीने पर <strong>{antar_hi} {labels['antardasha']}</strong> "
                    f"({antar_end.strftime('%b %Y')} तक) का प्रभाव है, {maha_hi} {labels['mahadasha']} के अंतर्गत।</p>"
                    f"<p>{antar_hi} उप-काल <strong>{antar_info.get('nature', 'महत्वपूर्ण')}</strong> है। "
                    f"प्रमुख {labels['themes']}: {antar_info.get('themes', 'विभिन्न परिवर्तन')}।</p>"
                    f"<p><strong>इस माह की {labels['strengths']}:</strong> {antar_info.get('positive', 'अवसर')}।</p>"
                    f"<p><strong>{labels['caution']}:</strong> {antar_info.get('challenges', 'सावधान रहें')}।</p>"
                    f"<p><strong>{labels['advice']}:</strong> {antar_info.get('advice', 'संतुलन बनाए रखें।')}।</p>"
                )
                sections.append({"heading": f"{labels['dasha_influence']}: {maha_hi}–{antar_hi}", "content": dasha_content})
            else:
                dasha_content = (
                    f"<p>This month is shaped by your <strong>{antar} Antardasha</strong> "
                    f"(until {antar_end.strftime('%b %Y')}) within the broader {maha} Mahadasha.</p>"
                    f"<p>The {antar} sub-period is <strong>{antar_info.get('nature', 'significant')}</strong>. "
                    f"Key themes: {antar_info.get('themes', 'various changes')}.</p>"
                    f"<p><strong>Strengths this month:</strong> {antar_info.get('positive', 'Opportunities')}.</p>"
                    f"<p><strong>Areas of caution:</strong> {antar_info.get('challenges', 'Be mindful')}.</p>"
                    f"<p><strong>Advice:</strong> {antar_info.get('advice', 'Stay balanced.')}.</p>"
                )
                sections.append({"heading": f"Dasha Influence: {maha}–{antar}", "content": dasha_content})

        else:
            # Yearly: focus on Mahadasha
            maha_end = dasha_info['maha_data'][2]
            remaining = (maha_end - today).days / 365.25
            if lang == "hi":
                maha_hi = planet_names.get(maha, maha)
                dasha_content = (
                    f"<p>{period_label} की प्रमुख थीम <strong>{maha_hi} {labels['mahadasha']}</strong> "
                    f"(शेष {remaining:.1f} वर्ष, {maha_end.strftime('%b %Y')} तक) है।</p>"
                    f"<p>यह काल <strong>{maha_info.get('nature', 'महत्वपूर्ण')}</strong> है। "
                    f"जीवन {labels['themes']}: {maha_info.get('themes', 'विभिन्न परिवर्तन')}।</p>"
                    f"<p><strong>वर्ष की {labels['strengths']}:</strong> {maha_info.get('positive', 'अवसर')}।</p>"
                    f"<p><strong>वर्ष की चुनौतियाँ:</strong> {maha_info.get('challenges', 'सावधान रहें')}।</p>"
                    f"<p><strong>वार्षिक {labels['advice']}:</strong> {maha_info.get('advice', 'संतुलन बनाए रखें।')}</p>"
                )
                sections.append({"heading": f"{labels['dasha_influence']}: {maha_hi} {labels['mahadasha']}", "content": dasha_content})
            else:
                dasha_content = (
                    f"<p>The overarching theme of {period_label} is your <strong>{maha} Mahadasha</strong> "
                    f"({remaining:.1f} years remaining, ending {maha_end.strftime('%b %Y')}).</p>"
                    f"<p>This period is <strong>{maha_info.get('nature', 'significant')}</strong>. "
                    f"Life themes: {maha_info.get('themes', 'various changes')}.</p>"
                    f"<p><strong>Year's strengths:</strong> {maha_info.get('positive', 'Opportunities')}.</p>"
                    f"<p><strong>Year's challenges:</strong> {maha_info.get('challenges', 'Be mindful')}.</p>"
                    f"<p><strong>Annual guidance:</strong> {maha_info.get('advice', 'Stay balanced.')}</p>"
                )
                sections.append({"heading": f"Dasha Theme: {maha} Mahadasha", "content": dasha_content})

    # ── Section 3: Transit (Gochar) Effects ──
    if period == "week":
        transit_planets = ["Sun", "Moon", "Mars", "Mercury", "Venus"]
        if lang == "hi":
            transit_heading = labels["weekly_transits"]
        else:
            transit_heading = "Key Planetary Transits This Week"
    elif period == "month":
        transit_planets = ["Sun", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        if lang == "hi":
            transit_heading = labels["monthly_transits"]
        else:
            transit_heading = "Planetary Transits This Month"
    else:
        transit_planets = ["Jupiter", "Saturn", "Rahu", "Ketu", "Mars", "Venus"]
        if lang == "hi":
            transit_heading = labels["yearly_transits"]
        else:
            transit_heading = "Major Transits This Year"

    if lang == "hi":
        transit_content = f"<p>आपकी {labels['moon_sign']} (<strong>{moon_sign_display}</strong>) से गोचर प्रभाव:</p>"
    else:
        transit_content = f"<p>Transit effects analysed from your Moon sign (<strong>{moon_sign}</strong>):</p>"
    transit_content += '<div class="transit-grid">'

    for planet in transit_planets:
        ta = transit_analysis.get(planet, {})
        if not ta:
            continue
        icon = "✅" if ta['is_benefic'] else "⚠️"
        if lang == "hi":
            status = labels["favourable"] if ta['is_benefic'] else labels["challenging"]
            retro_mark = f" ({labels['retrograde']})" if ta.get('retro') else ""
            p_name = planet_names.get(planet, planet)
            sign_display = ta.get('sign_hi', ta['sign'])
            transit_content += (
                f'<div class="transit-item {"benefic" if ta["is_benefic"] else "malefic"}">'
                f'<strong>{icon} {p_name}</strong> {sign_display} में{retro_mark} '
                f'({labels["house"]} {ta["house"]} {labels["from_moon"]} — <em>{status}</em>)<br>'
                f'<span class="effect-text">{ta["effect"]}</span>'
                f'</div>'
            )
        else:
            status = "Favourable" if ta['is_benefic'] else "Challenging"
            retro_mark = " (Retrograde)" if ta.get('retro') else ""
            transit_content += (
                f'<div class="transit-item {"benefic" if ta["is_benefic"] else "malefic"}">'
                f'<strong>{icon} {planet}</strong> in {ta["sign"]}{retro_mark} '
                f'(House {ta["house"]} from Moon — <em>{status}</em>)<br>'
                f'<span class="effect-text">{ta["effect"]}</span>'
                f'</div>'
            )

    transit_content += '</div>'
    sections.append({"heading": transit_heading, "content": transit_content})

    # ── Section 4: Sade Sati (if active) ──
    if sade_sati:
        sade_sati_content = f"<p>{sade_sati_data[sade_sati]}</p>"
        sade_sati_heading = f"⚡ {labels['sade_sati']}" if lang == "hi" else "⚡ Sade Sati Alert"
        sections.append({"heading": sade_sati_heading, "content": sade_sati_content})

    # ── Section 5: Summary & Guidance ──
    # Count benefic vs malefic transits for the selected planets
    benefic_count = sum(1 for p in transit_planets if transit_analysis.get(p, {}).get('is_benefic'))
    total = len(transit_planets)

    if benefic_count > total * 0.6:
        if lang == "hi":
            overall = labels["overall_positive"]
        else:
            overall = "Overall, the planetary transits are <strong>predominantly favourable</strong> for this period."
        tone = "positive"
    elif benefic_count > total * 0.4:
        if lang == "hi":
            overall = labels["overall_mixed"]
        else:
            overall = "The planetary transits present a <strong>mixed picture</strong> — some areas flourish while others need care."
        tone = "mixed"
    else:
        if lang == "hi":
            overall = labels["overall_challenging"]
        else:
            overall = "The transits indicate a <strong>challenging period</strong> requiring patience and careful planning."
        tone = "challenging"

    if dasha_info['maha']:
        maha_advice = dasha_data.get(dasha_info['maha'], {}).get('advice', '')
        if lang == "hi":
            guidance = f"<p>{overall}</p><p><strong>{labels['dasha_influence']} {labels['advice']}:</strong> {maha_advice}</p>"
        else:
            guidance = f"<p>{overall}</p><p><strong>Dasha Guidance:</strong> {maha_advice}</p>"
    else:
        guidance = f"<p>{overall}</p>"

    # Add period-specific tips
    if period == "week":
        if lang == "hi":
            if tone == "positive":
                guidance += "<p><strong>साप्ताहिक सलाह:</strong> यह सप्ताह नई गतिविधियां शुरू करने, लोगों से मिलने और लक्ष्यों का सक्रिय रूप से अनुसरण करने के लिए अच्छा है।</p>"
            elif tone == "mixed":
                guidance += "<p><strong>साप्ताहिक सलाह:</strong> इस सप्ताह अपनी शक्तियों पर ध्यान दें। जोखिम भरे निर्णय टालें।</p>"
            else:
                guidance += "<p><strong>साप्ताहिक सलाह:</strong> इस सप्ताह धीरे चलें। नियमित कार्यों और आत्म-देखभाल पर ध्यान दें।</p>"
        else:
            if tone == "positive":
                guidance += "<p><strong>Weekly Tip:</strong> This is a good week to initiate new activities, meet people, and pursue goals actively.</p>"
            elif tone == "mixed":
                guidance += "<p><strong>Weekly Tip:</strong> Focus on your strengths this week. Postpone risky decisions to more favourable days.</p>"
            else:
                guidance += "<p><strong>Weekly Tip:</strong> Take it slow this week. Focus on routine tasks and self-care. Avoid confrontations.</p>"
    elif period == "month":
        if lang == "hi":
            if tone == "positive":
                guidance += "<p><strong>मासिक सलाह:</strong> एक उत्पादक महीना। आत्मविश्वास से लक्ष्य निर्धारित करें।</p>"
            elif tone == "mixed":
                guidance += "<p><strong>मासिक सलाह:</strong> इस महीने महत्वाकांक्षा और सावधानी में संतुलन बनाएं।</p>"
            else:
                guidance += "<p><strong>मासिक सलाह:</strong> इस महीने धैर्य और संयम आवश्यक है। स्वास्थ्य और बचत पर ध्यान दें।</p>"
        else:
            if tone == "positive":
                guidance += "<p><strong>Monthly Tip:</strong> A productive month ahead. Set ambitious goals and work towards them with confidence.</p>"
            elif tone == "mixed":
                guidance += "<p><strong>Monthly Tip:</strong> Balance ambition with caution this month. The first half may differ from the second.</p>"
            else:
                guidance += "<p><strong>Monthly Tip:</strong> This month calls for patience and consolidation. Focus on health, savings, and inner work.</p>"
    else:
        if lang == "hi":
            if tone == "positive":
                guidance += "<p><strong>वार्षिक दृष्टिकोण:</strong> विकास और विस्तार का वर्ष। जीवन की प्रमुख उपलब्धियां संभव।</p>"
            elif tone == "mixed":
                guidance += "<p><strong>वार्षिक दृष्टिकोण:</strong> सीखने और अनुकूलन का वर्ष। लचीलेपन से सफलता मिलेगी।</p>"
            else:
                guidance += "<p><strong>वार्षिक दृष्टिकोण:</strong> गहन आंतरिक कार्य और कार्मिक शुद्धि का वर्ष। भविष्य की मजबूत नींव बनाएं।</p>"
        else:
            if tone == "positive":
                guidance += "<p><strong>Annual Outlook:</strong> A year of growth and expansion. Major life milestones possible. Stay grateful and grounded.</p>"
            elif tone == "mixed":
                guidance += "<p><strong>Annual Outlook:</strong> A year of learning and adaptation. Success comes through flexibility and perseverance.</p>"
            else:
                guidance += "<p><strong>Annual Outlook:</strong> A year of deep inner work and karmic clearing. Build strong foundations for the future.</p>"

    sections.append({"heading": labels["guidance"] if lang == "hi" else "Guidance & Summary", "content": guidance})

    # Add disclaimer
    if lang == "hi":
        disclaimer = (
            "<p style='font-size:0.8rem; color:#999; margin-top:16px; border-top:1px solid #eee; padding-top:12px;'>"
            "<em>ये पाठन वैदिक ज्योतिष सिद्धांतों पर आधारित हैं। "
            "ये मार्गदर्शन और मनोरंजन के लिए हैं। "
            "महत्वपूर्ण निर्णयों के लिए अपने विवेक का उपयोग करें।</em></p>"
            "<p style='font-size:0.75rem; color:#B8860B;'>by AstroShuklz · लाहिरी अयनांश · Swiss Ephemeris</p>"
        )
    else:
        disclaimer = (
            "<p style='font-size:0.8rem; color:#999; margin-top:16px; border-top:1px solid #eee; padding-top:12px;'>"
            "<em>These readings are based on Vedic astrological principles using your birth chart, "
            "current Vimshottari Dasha periods, and planetary transit (Gochar) positions. "
            "They are for guidance and entertainment purposes. Use your own judgement for important decisions.</em></p>"
            "<p style='font-size:0.75rem; color:#B8860B;'>by AstroShuklz · Lahiri Ayanamsha · Swiss Ephemeris</p>"
        )
    sections.append({"heading": "", "content": disclaimer})

    return {"title": title, "sections": sections}


# ─── PDF Report ──────────────────────────────────────────────────────────────

def generate_pdf(chart, output_path="kundali_report.pdf", svg_path=None):
    """
    Generate a nicely formatted PDF report with the Kundali chart (SVG),
    planetary positions, and Vimshottari Dasha tables.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                     Paragraph, Spacer, Image, PageBreak)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    import io

    # ── Register Devanagari font ─────────────────────────────────
    deva_font = "Helvetica"
    deva_font_bold = "Helvetica-Bold"
    try:
        pdfmetrics.registerFont(TTFont("DevSangam",
            "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",
            subfontIndex=0))
        deva_font = "DevSangam"
        deva_font_bold = "DevSangam"
    except Exception:
        pass  # fallback to Helvetica

    # ── Colours ──────────────────────────────────────────────────
    MAROON      = colors.HexColor("#8B0000")
    GOLD        = colors.HexColor("#8B6914")
    CREAM       = colors.HexColor("#FFFDF5")
    HEADER_BG   = colors.HexColor("#8B0000")
    HEADER_FG   = colors.white
    ROW_ALT     = colors.HexColor("#FFF8E7")
    ROW_NOW     = colors.HexColor("#FFFACD")

    # ── Document setup ───────────────────────────────────────────
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            topMargin=15*mm, bottomMargin=15*mm,
                            leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    story = []

    # Custom styles
    title_style = ParagraphStyle('KTitle', parent=styles['Title'],
        fontName=deva_font, fontSize=22, textColor=MAROON,
        alignment=TA_CENTER, spaceAfter=2*mm)
    subtitle_style = ParagraphStyle('KSubtitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=11, textColor=colors.HexColor("#444"),
        alignment=TA_CENTER, spaceAfter=1*mm)
    info_style = ParagraphStyle('KInfo', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#555"),
        alignment=TA_CENTER, spaceAfter=3*mm)
    section_style = ParagraphStyle('KSection', parent=styles['Heading2'],
        fontName='Helvetica-Bold', fontSize=12, textColor=MAROON,
        alignment=TA_CENTER, spaceBefore=5*mm, spaceAfter=2*mm)

    bd = chart['birth_data']
    planets = chart['planets']
    asc_sign = chart['asc_sign']
    moon_sign = planets['Moon']['sign_idx']
    today = datetime.now()

    # ── Page 1: Header ───────────────────────────────────────────
    story.append(Paragraph("जन्म कुण्डली", title_style))
    story.append(Paragraph(f"{bd['name']}", subtitle_style))
    story.append(Paragraph(
        f"{bd['day']:02d}/{bd['month']:02d}/{bd['year']}  &nbsp; "
        f"{bd['hour']:02d}:{bd['minute']:02d} IST  &nbsp;·&nbsp; {bd['place']}",
        info_style))

    # Lagna / Rashi / Nakshatra summary
    summary = (f"Lagna: {chart['asc_sign_en']} ({chart['asc_sign_hi']}) "
               f"{dms_str(chart['asc_deg'])}  &nbsp;·&nbsp; "
               f"Rashi: {chart['moon_rashi']} ({chart['moon_rashi_hi']})  &nbsp;·&nbsp; "
               f"Nakshatra: {chart['nakshatra']}, Pada {chart['nak_pada']} "
               f"({chart['nak_lord']})")
    story.append(Paragraph(summary, info_style))

    # ── Embed SVG chart as image ─────────────────────────────────
    if svg_path and os.path.exists(svg_path):
        try:
            from svglib.svglib import svg2rlg
            from reportlab.graphics import renderPDF
            drawing = svg2rlg(svg_path)
            if drawing:
                # Scale to fit page width
                scale = (A4[0] - 30*mm) / drawing.width
                drawing.width *= scale
                drawing.height *= scale
                drawing.scale(scale, scale)
                story.append(drawing)
                story.append(Spacer(1, 3*mm))
        except ImportError:
            # svglib not available — render SVG via PNG conversion or skip
            pass

    # ── Planetary Positions Table ────────────────────────────────
    story.append(Paragraph("Planetary Positions", section_style))

    p_header = ['Graha', 'Sign (Rashi)', 'Degree', 'Rashi#',
                'H/Lagna', 'H/Moon', 'R']
    p_data = [p_header]
    order = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]
    for pname in order:
        p = planets[pname]
        sidx = p['sign_idx']
        rashi = sidx + 1
        h_lag = (sidx - asc_sign) % 12 + 1
        h_moon = (sidx - moon_sign) % 12 + 1
        retro = "℞" if p['retro'] else ""
        sign_str = f"{p['sign_en']} ({p['sign_hi']})"
        p_data.append([pname, sign_str, dms_str(p['deg']),
                       str(rashi), f"H{h_lag}", f"H{h_moon}", retro])

    col_w = [55, 115, 65, 40, 45, 45, 20]
    ptable = Table(p_data, colWidths=col_w)
    ptable.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
        ('BACKGROUND', (0,0), (-1,0), HEADER_BG),
        ('TEXTCOLOR',  (0,0), (-1,0), HEADER_FG),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ROW_ALT]),
        ('TOPPADDING',  (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',(0,0), (-1,-1), 3),
    ]))
    story.append(ptable)

    # ── Mahadasha Table ──────────────────────────────────────────
    story.append(Paragraph("Vimshottari Dasha — Mahadasha", section_style))

    m_header = ['Lord', 'Start', 'End', 'Years', '']
    m_data = [m_header]
    current_maha = None
    for lord, start, end, yrs in chart['dashas']:
        is_now = start <= today < end
        if is_now:
            current_maha = lord
        marker = "◄ NOW" if is_now else ""
        m_data.append([lord, start.strftime('%b %Y'), end.strftime('%b %Y'),
                       f"{yrs:.1f}", marker])

    mtable = Table(m_data, colWidths=[70, 80, 80, 50, 50])
    m_style = [
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
        ('BACKGROUND', (0,0), (-1,0), HEADER_BG),
        ('TEXTCOLOR',  (0,0), (-1,0), HEADER_FG),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ROW_ALT]),
        ('TOPPADDING',  (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',(0,0), (-1,-1), 3),
    ]
    # Highlight current Mahadasha row
    for i, (lord, start, end, yrs) in enumerate(chart['dashas'], 1):
        if start <= today < end:
            m_style.append(('BACKGROUND', (0, i), (-1, i), ROW_NOW))
            m_style.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
    mtable.setStyle(TableStyle(m_style))
    story.append(mtable)

    # ── Page 2: Antardasha + Pratyantar ──────────────────────────
    story.append(PageBreak())

    if current_maha and current_maha in chart.get('antardasha', {}):
        story.append(Paragraph(
            f"Vimshottari Dasha — Antardasha (within {current_maha} Mahadasha)",
            section_style))

        a_header = ['Lord', 'Start', 'End', 'Duration', '']
        a_data = [a_header]
        current_antar = None
        for ad_lord, ad_start, ad_end, ad_yrs in chart['antardasha'][current_maha]:
            is_now = ad_start <= today < ad_end
            if is_now:
                current_antar = ad_lord
            marker = "◄ NOW" if is_now else ""
            months = ad_yrs * 12
            dur_str = f"{ad_yrs:.1f}y" if months >= 12 else f"{months:.1f}m"
            a_data.append([ad_lord, ad_start.strftime('%d %b %Y'),
                           ad_end.strftime('%d %b %Y'), dur_str, marker])

        atable = Table(a_data, colWidths=[70, 90, 90, 55, 50])
        a_style = [
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 8),
            ('BACKGROUND', (0,0), (-1,0), HEADER_BG),
            ('TEXTCOLOR',  (0,0), (-1,0), HEADER_FG),
            ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
            ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ROW_ALT]),
            ('TOPPADDING',  (0,0), (-1,-1), 3),
            ('BOTTOMPADDING',(0,0), (-1,-1), 3),
        ]
        for i, (ad_lord, ad_start, ad_end, ad_yrs) in enumerate(
                chart['antardasha'][current_maha], 1):
            if ad_start <= today < ad_end:
                a_style.append(('BACKGROUND', (0, i), (-1, i), ROW_NOW))
                a_style.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
        atable.setStyle(TableStyle(a_style))
        story.append(atable)

        # ── Pratyantar Dasha ─────────────────────────────────────
        if current_antar:
            key = (current_maha, current_antar)
            if key in chart.get('pratyantar', {}):
                story.append(Paragraph(
                    f"Vimshottari Dasha — Pratyantar "
                    f"(within {current_maha}–{current_antar})",
                    section_style))

                pd_header = ['Lord', 'Start', 'End', 'Duration', '']
                pd_data = [pd_header]
                for pd_lord, pd_start, pd_end, pd_yrs in chart['pratyantar'][key]:
                    is_now = pd_start <= today < pd_end
                    marker = "◄ NOW" if is_now else ""
                    days = pd_yrs * 365.25
                    dur_str = f"{pd_yrs*12:.1f}m" if days >= 30 else f"{days:.0f}d"
                    pd_data.append([pd_lord, pd_start.strftime('%d %b %Y'),
                                    pd_end.strftime('%d %b %Y'), dur_str, marker])

                pdtable = Table(pd_data, colWidths=[70, 90, 90, 55, 50])
                pd_style = [
                    ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE',   (0,0), (-1,-1), 8),
                    ('BACKGROUND', (0,0), (-1,0), HEADER_BG),
                    ('TEXTCOLOR',  (0,0), (-1,0), HEADER_FG),
                    ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
                    ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ROW_ALT]),
                    ('TOPPADDING',  (0,0), (-1,-1), 3),
                    ('BOTTOMPADDING',(0,0), (-1,-1), 3),
                ]
                for i, (pd_lord, pd_start, pd_end, pd_yrs) in enumerate(
                        chart['pratyantar'][key], 1):
                    if pd_start <= today < pd_end:
                        pd_style.append(('BACKGROUND', (0, i), (-1, i), ROW_NOW))
                        pd_style.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
                pdtable.setStyle(TableStyle(pd_style))
                story.append(pdtable)

    # ── Page 3: General Reading / Dasha Insights ───────────────
    story.append(PageBreak())
    story.append(Paragraph("Dasha Reading &amp; General Insights", title_style))
    story.append(Spacer(1, 3*mm))

    reading_style = ParagraphStyle('KReading', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9.5, textColor=colors.HexColor("#333"),
        alignment=TA_LEFT, leading=14, spaceBefore=2*mm, spaceAfter=2*mm)
    reading_bold = ParagraphStyle('KReadBold', parent=reading_style,
        fontName='Helvetica-Bold', fontSize=10, textColor=MAROON,
        spaceBefore=4*mm, spaceAfter=1*mm)
    disclaimer_style = ParagraphStyle('KDisclaimer', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=7.5,
        textColor=colors.HexColor("#999"), alignment=TA_CENTER,
        spaceBefore=8*mm, spaceAfter=2*mm)

    reading = _dasha_reading(chart, today)
    for block in reading:
        if block.startswith("##"):
            story.append(Paragraph(block[2:].strip(), reading_bold))
        else:
            story.append(Paragraph(block, reading_style))

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(
        "Disclaimer: This reading is generated based on classical Vimshottari "
        "Dasha interpretations and is for educational/entertainment purposes only. "
        "For personalised guidance, consult a qualified Jyotish practitioner.",
        disclaimer_style))

    # ── Footer ───────────────────────────────────────────────────
    story.append(Spacer(1, 8*mm))
    footer_style = ParagraphStyle('KFooter', parent=styles['Normal'],
        fontName='Helvetica', fontSize=7, textColor=colors.HexColor("#AAAAAA"),
        alignment=TA_CENTER)
    story.append(Paragraph("Lahiri Ayanamsha  ·  Swiss Ephemeris  ·  "
                           "Generated by Vedic Kundali Generator", footer_style))

    doc.build(story)
    print(f"  PDF report saved: {output_path}")


def _generate_hindi_pdf(chart, today, strength_data=None):
    """Generate Hindi pages as PDF using WeasyPrint for proper Devanagari rendering.
    Returns a BytesIO buffer, or None if WeasyPrint is unavailable."""
    try:
        from weasyprint import HTML
    except (ImportError, OSError):
        return None

    import io as _io

    bd = chart['birth_data']
    planets = chart['planets']
    asc_sign = chart['asc_sign']
    moon_sign = planets['Moon']['sign_idx']
    order = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]

    # Bundled font path
    font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "fonts", "NotoSansDevanagari.ttf")
    font_url = f"file://{font_path}"

    # ── Build HTML ────────────────────────────────────────────────
    css = f"""
    @font-face {{
        font-family: 'NotoHindi';
        src: url('{font_url}');
    }}
    body {{ font-family: 'NotoHindi', 'Devanagari Sangam MN', 'Noto Sans Devanagari', sans-serif;
           color: #333; margin: 40px; font-size: 10pt; }}
    h1 {{ color: #8B0000; text-align: center; font-size: 20pt; margin-bottom: 2px; }}
    .brand {{ text-align: center; color: #B8860B; font-style: italic; font-size: 10pt; margin-bottom: 10px; }}
    .info {{ text-align: center; color: #555; font-size: 9pt; margin-bottom: 5px; }}
    h2 {{ color: #8B0000; text-align: center; font-size: 12pt; margin-top: 15px; margin-bottom: 8px; }}
    h3 {{ color: #8B0000; font-size: 10pt; margin-top: 12px; margin-bottom: 4px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 8pt; }}
    th {{ background: #8B0000; color: white; padding: 4px 6px; text-align: center; }}
    td {{ padding: 4px 6px; text-align: center; border: 0.5px solid #CCC; }}
    /* no alternate row coloring */
    tr.now {{ background: #FFFACD; font-weight: bold; }}
    .reading {{ font-size: 9.5pt; line-height: 1.5; margin: 5px 0; }}
    .disclaimer {{ font-size: 7.5pt; color: #999; text-align: center; font-style: italic; margin-top: 20px; }}
    .footer {{ font-size: 7pt; color: #AAA; text-align: center; margin-top: 10px; }}
    .page-break {{ page-break-before: always; }}
    """

    html_parts = [f"<html><head><style>{css}</style></head><body>"]

    # ── Hindi Page 1: Header + Planetary Positions ───────────────
    html_parts.append("<h1>जन्म कुण्डली</h1>")
    html_parts.append('<div class="brand">by AstroShuklz</div>')
    html_parts.append(f'<div class="info" style="font-size:11pt; color:#444; font-weight:bold;">{bd["name"]}</div>')
    html_parts.append(f'<div class="info">{bd["day"]:02d}/{bd["month"]:02d}/{bd["year"]}  '
                       f'{bd["hour"]:02d}:{bd["minute"]:02d}  ·  {bd["place"]}</div>')
    html_parts.append(f'<div class="info">लग्न: {SIGNS_HI_FULL[asc_sign]} '
                       f'{dms_str(chart["asc_deg"])}  ·  '
                       f'राशि: {SIGNS_HI_FULL[moon_sign]}  ·  '
                       f'नक्षत्र: {chart["nakshatra"]}, '
                       f'पद {chart["nak_pada"]} '
                       f'({PLANET_HI_FULL.get(chart["nak_lord"], chart["nak_lord"])})</div>')

    # ── Hindi House Position Table (same as English page 1) ──
    BHAV_NAMES_HI_TBL = {
        1: "तनु",    2: "धन",     3: "सहज",    4: "सुख",
        5: "पुत्र",   6: "अरि",    7: "कलत्र",   8: "रन्ध्र",
        9: "धर्म",  10: "कर्म",   11: "लाभ",   12: "व्यय",
    }
    HOUSE_DESC_HI = {
        1: "स्वयं, शरीर, व्यक्तित्व, रूप, स्वास्थ्य",
        2: "धन, परिवार, वाणी, भोजन, शिक्षा",
        3: "भाई-बहन, साहस, संवाद, लघु यात्रा",
        4: "माता, सुख, गृह, सम्पत्ति, वाहन",
        5: "संतान, बुद्धि, रचनात्मकता, प्रेम",
        6: "शत्रु, रोग, ऋण, बाधा, सेवा",
        7: "पति/पत्नी, साझेदारी, व्यापार, विदेश",
        8: "रूपांतरण, आयु, रहस्य, विरासत",
        9: "भाग्य, पिता, धर्म, उच्च शिक्षा, गुरु",
        10: "कर्म, पद, अधिकार, यश, सरकार",
        11: "लाभ, आय, मित्र, इच्छापूर्ति",
        12: "हानि, व्यय, विदेश, मोक्ष, एकांत",
    }
    SIGNS_HI_TBL = ["मेष","वृषभ","मिथुन","कर्क","सिंह","कन्या",
                     "तुला","वृश्चिक","धनु","मकर","कुम्भ","मीन"]
    RASHI_ELEMENT_HI = ["अग्नि","पृथ्वी","वायु","जल","अग्नि","पृथ्वी",
                         "वायु","जल","अग्नि","पृथ्वी","वायु","जल"]
    RASHI_NATURE_HI = ["चर","स्थिर","द्विस्वभाव","चर","स्थिर","द्विस्वभाव",
                        "चर","स्थिर","द्विस्वभाव","चर","स्थिर","द्विस्वभाव"]

    # Build planet lookup for Hindi table
    hi_planet_in_house = {h: [] for h in range(1, 13)}
    for pname in order:
        p = planets[pname]
        sidx = p['sign_idx']
        h_lag = (sidx - asc_sign) % 12 + 1
        hi_planet_in_house[h_lag].append((pname, dms_str(p['deg']),
                                          "℞" if p['retro'] else ""))

    html_parts.append("<h2>ग्रह स्थिति</h2>")
    html_parts.append('<table style="font-size:9.5pt;"><tr>'
                       '<th>#</th><th>भवन</th><th>भाव</th>'
                       '<th>भवन विशेषता</th><th>राशि</th>'
                       '<th>राशि विशेषता</th><th>ग्रह</th>'
                       '<th>अंश</th><th>व</th><th>चं.भ</th></tr>')

    moon_sign_val = planets['Moon']['sign_idx']
    for rank in range(1, 13):
        sign_idx = (asc_sign + rank - 1) % 12
        house_num = ((asc_sign + rank - 1) % 12) + 1
        bhav_hi = BHAV_NAMES_HI_TBL[house_num]
        desc_hi = HOUSE_DESC_HI[house_num]
        rashi_hi = SIGNS_HI_TBL[sign_idx]
        elem_hi = RASHI_ELEMENT_HI[sign_idx]
        nature_hi = RASHI_NATURE_HI[sign_idx]
        hfm = (sign_idx - moon_sign_val) % 12 + 1

        plist = hi_planet_in_house[rank]
        if plist:
            planet_str = ", ".join(PLANET_HI_FULL.get(p[0], p[0]) for p in plist)
            deg_str = "<br/>".join(f"{PLANET_HI_FULL.get(p[0], p[0])}: {p[1]}" for p in plist)
            retro_str = "<br/>".join(p[2] for p in plist)
        else:
            planet_str = "-"
            deg_str = "-"
            retro_str = ""

        # Highlight 1st row (Ascendant) and Moon row
        row_style = ""
        if rank == 1:
            row_style = ' style="background:#FFF3CD; font-weight:bold;"'
        elif hfm == 1:
            row_style = ' style="background:#E3F2FD;"'

        html_parts.append(f"<tr{row_style}><td>{rank}</td><td><b>{house_num}</b></td>"
                           f"<td>{bhav_hi}</td><td>{desc_hi}</td>"
                           f"<td>{rashi_hi}</td>"
                           f"<td>{elem_hi} | {nature_hi}</td>"
                           f"<td>{planet_str}</td><td>{deg_str}</td>"
                           f"<td>{retro_str}</td><td>{hfm}</td></tr>")
    html_parts.append("</table>")

    # ── Hindi Explanatory Notes Page ─────────────────────────
    html_parts.append('<div class="page-break"></div>')
    html_parts.append("<h2>ग्रह स्थिति तालिका — व्याख्यात्मक टिप्पणियाँ</h2>")

    # Sign rulers in Hindi
    SIGN_RULERS_HI = {
        "Aries": "मंगल", "Taurus": "शुक्र", "Gemini": "बुध",
        "Cancer": "चन्द्र", "Leo": "सूर्य", "Virgo": "बुध",
        "Libra": "शुक्र", "Scorpio": "मंगल", "Sagittarius": "गुरु",
        "Capricorn": "शनि", "Aquarius": "शनि", "Pisces": "गुरु",
    }
    SIGN_TRAITS_HI = {
        "Aries": "साहसी, अग्रणी और कर्मठ",
        "Taurus": "स्थिर, धैर्यवान और भौतिकवादी",
        "Gemini": "अनुकूलनशील, संवादप्रिय और जिज्ञासु",
        "Cancer": "पालनकर्ता, भावनात्मक और रक्षात्मक",
        "Leo": "आत्मविश्वासी, रचनात्मक और प्रभावशाली",
        "Virgo": "विश्लेषणात्मक, विस्तार-उन्मुख और सेवा-भावी",
        "Libra": "संतुलित, कूटनीतिक और सौंदर्यप्रिय",
        "Scorpio": "तीव्र, रूपांतरकारी और गहन दृष्टि वाले",
        "Sagittarius": "साहसिक, दार्शनिक और आशावादी",
        "Capricorn": "महत्वाकांक्षी, अनुशासित और व्यावहारिक",
        "Aquarius": "नवप्रवर्तक, मानवतावादी और स्वतंत्र",
        "Pisces": "अंतर्ज्ञानी, करुणामय और आध्यात्मिक",
    }

    asc_name_en = chart['asc_sign_en']
    asc_deg_val = chart['asc_deg']
    asc_abs = asc_sign * 30 + asc_deg_val
    asc_rashi_hi = SIGNS_HI_FULL[asc_sign]
    asc_ruler_hi = SIGN_RULERS_HI.get(asc_name_en, "")
    asc_traits_hi = SIGN_TRAITS_HI.get(asc_name_en, "")
    moon_rashi_hi = SIGNS_HI_FULL[moon_sign]

    # Early/mid/late degree Hindi
    if asc_deg_val < 10:
        deg_note_hi = "प्रारंभिक अंश (0-10°) दर्शाता है कि राशि की ऊर्जा ताज़ा और कच्ची है।"
    elif asc_deg_val < 20:
        deg_note_hi = "मध्य अंश (10-20°) दर्शाता है कि राशि के गुण पूर्ण रूप से व्यक्त हो रहे हैं।"
    else:
        deg_note_hi = "अंतिम अंश (20-30°) दर्शाता है कि इस राशि से परिपक्वता और संक्रमण ऊर्जा है।"

    html_parts.append(
        '<h3 style="color:#8B0000;">1. लग्न (उदय राशि)</h3>'
        '<div class="reading">'
        'वैदिक ज्योतिष में <b>लग्न</b> (उदय राशि) वह राशि है जो आपके जन्म के '
        'सटीक क्षण में पूर्वी क्षितिज पर उदय हो रही थी। यह आपके बाहरी व्यक्तित्व, '
        'दूसरों की आपके प्रति धारणा और जीवन के प्रति आपके दृष्टिकोण को दर्शाता है। '
        'लग्न की गणना 0° से 360° के बीच होती है, प्रत्येक राशि 30° का भाग लेती है। '
        'प्रथम भवन की पंक्ति तालिका में '
        '<span style="color:#DAA520;"><b>स्वर्ण रंग</b></span> में चिह्नित है।'
        '</div>')

    html_parts.append(
        '<div class="reading"><b>अंश व्याख्या:</b> '
        f'आपका लग्न कांतिवृत्त पर <b>{asc_abs:.2f}°</b> पर है। '
        f'चूँकि {asc_rashi_hi} {asc_sign * 30}° से {asc_sign * 30 + 30}° तक फैली है, '
        f'आपका लग्न {asc_rashi_hi} में <b>{dms_str(asc_deg_val)}</b> पर पड़ता है। '
        f'{deg_note_hi}</div>')

    html_parts.append(
        '<div class="reading"><b>ग्रह स्वामी:</b> '
        f'{asc_rashi_hi} का स्वामी ग्रह <b>{asc_ruler_hi}</b> है। '
        f'लग्नेश के रूप में, आपकी कुण्डली में {asc_ruler_hi} का स्थान '
        f'(भवन, राशि और दृष्टि) आपके समग्र जीवन मार्ग, स्वास्थ्य और '
        f'व्यक्तित्व अभिव्यक्ति पर विशेष प्रभाव डालता है।</div>')

    html_parts.append(
        f'<div style="background:#FFFDE7; border:1px solid #DAA520; padding:8px; '
        f'margin:8px 0; font-style:italic; color:#2E4057;">'
        f'<b>सारांश:</b> आपका लग्न <b>{asc_abs:.2f}°</b> '
        f'({asc_rashi_hi} में {dms_str(asc_deg_val)}) पर है, अर्थात आपकी '
        f'उदय राशि <b>{asc_rashi_hi}</b> है। आप {asc_traits_hi} ऊर्जा प्रक्षेपित '
        f'करते हैं। लग्नेश {asc_ruler_hi} आपकी मूल पहचान और जीवन पथ को '
        f'और आकार देता है।</div>')

    # 2. HFM
    html_parts.append(
        '<h3 style="color:#8B0000;">2. चं.भ (चन्द्र से भवन)</h3>'
        '<div class="reading">'
        'वैदिक ज्योतिष में भवन केवल <b>लग्न</b> से ही नहीं, बल्कि '
        f'<b>चन्द्रमा</b> (चन्द्र कुण्डली) से भी पढ़े जाते हैं। आपका चन्द्रमा '
        f'<b>{moon_rashi_hi}</b> में है, जो आपकी चन्द्र कुण्डली का प्रथम भवन बनता है। '
        'चं.भ प्रत्येक भवन की चन्द्रमा की स्थिति से गिनती दर्शाता है।</div>'
        '<div class="reading">'
        'चन्द्र कुण्डली आपके <b>भावनात्मक परिदृश्य</b>, मानसिक प्रवृत्तियों '
        'और आंतरिक धारणा को प्रकट करती है — जबकि लग्न कुण्डली आपके बाहरी जीवन '
        'को दर्शाती है। चन्द्रमा का भवन (चं.भ=1) तालिका में '
        '<span style="color:#1E88E5;"><b>नीले रंग</b></span> में चिह्नित है।</div>')

    # 3. Retrograde
    html_parts.append(
        '<h3 style="color:#8B0000;">3. व (वक्री ग्रह)</h3>'
        '<div class="reading">'
        '<b>व</b> से चिह्नित ग्रह पृथ्वी से पीछे चलते प्रतीत होते हैं। '
        'वैदिक ज्योतिष में वक्री ग्रह शक्तिशाली माने जाते हैं लेकिन उनकी '
        'ऊर्जा <b>अंतर्मुखी</b> हो जाती है। ये प्रायः कार्मिक पाठ, विलम्बित '
        'परन्तु तीव्र परिणाम, पूर्वजन्म के अधूरे कार्य, या गहन आत्मनिरीक्षण '
        'की आवश्यकता दर्शाते हैं। वक्री शुभ ग्रह (गुरु, शुक्र) अप्रत्याशित लाभ '
        'दे सकते हैं, जबकि वक्री पाप ग्रह (शनि, मंगल) अंततः समाधान से पहले '
        'चुनौतियों को तीव्र कर सकते हैं।</div>')

    # 4. Bhav
    html_parts.append(
        '<h3 style="color:#8B0000;">4. भाव (भवन पद्धति)</h3>'
        '<div class="reading">'
        '12 भवनों में से प्रत्येक जीवन के विशिष्ट क्षेत्रों को नियंत्रित करता है। '
        'तालिका में भवन संख्या उस भवन में स्थित राशि की प्राकृतिक राशिचक्र '
        'स्थिति से मेल खाती है। भाव का नाम (तनु, धन, सहज आदि) उस भवन द्वारा '
        'शासित जीवन क्षेत्र का वर्णन करता है। किसी भवन में स्थित ग्रह अपने '
        'प्राकृतिक कारकत्व के अनुसार उन जीवन क्षेत्रों को प्रभावित करते हैं।</div>')

    # ── Hindi Bhava Reading Page ─────────────────────────────────
    bhava_readings_hi = generate_bhava_readings(chart, strength_data, lang="hi")

    html_parts.append('<div class="page-break"></div>')
    html_parts.append("<h2>भाव विश्लेषण — भवन पठन</h2>")
    html_parts.append('<div class="brand">by AstroShuklz</div>')
    html_parts.append(
        '<div class="reading" style="font-size:11px; margin-bottom:8px;">'
        '12 भवनों में से प्रत्येक जीवन के विशिष्ट क्षेत्रों को नियंत्रित करता है। '
        'नीचे दिया गया पठन प्रत्येक भवन में स्थित राशि, ग्रह, उनके बल और '
        'भवन स्वामी की स्थिति को मिलाकर आपके प्रत्येक जीवन क्षेत्र का '
        'व्यक्तिगत मूल्यांकन प्रस्तुत करता है।</div>')

    for br in bhava_readings_hi:
        h = br['house']
        planet_list_hi = ", ".join([PLANET_HI_FULL.get(p, p) for p in br['planets']]) if br['planets'] else "रिक्त"
        html_parts.append(
            f'<div style="margin-top:8px;">'
            f'<b style="color:#8B0000; font-size:13px;">भवन {h} — {br["bhav"]} '
            f'({br["title"]}) · {br["sign"]} · [{planet_list_hi}]</b></div>')
        html_parts.append(f'<div class="reading">{br["para"]}</div>')

    # ── Hindi Planet Strength Page ───────────────────────────────
    html_parts.append('<div class="page-break"></div>')
    html_parts.append("<h2>ग्रह बल विश्लेषण</h2>")
    html_parts.append('<div class="brand">by AstroShuklz</div>')

    if strength_data:
        for pname in order:
            hi_name = PLANET_HI_FULL.get(pname, pname)
            reading = _planet_strength_reading(pname, planets[pname],
                                               strength_data[pname], lang="hi")
            html_parts.append(f'<div class="reading"><b>{hi_name}:</b> {reading}</div>')

        # Embed bar chart as base64 image
        import base64 as _b64
        chart_buf = _draw_strength_bar_chart(strength_data)
        img_b64 = _b64.b64encode(chart_buf.read()).decode()
        html_parts.append(f'<img src="data:image/png;base64,{img_b64}" '
                           f'style="width:100%; max-width:600px; margin:10px auto; display:block;"/>')
        html_parts.append('<div class="reading" style="font-size:8pt; color:#666;">'
                           '<b>विधि:</b> अंक राशि गरिमा (35), भवन स्थान (20), अंश परिपक्वता (10), '
                           'दृष्टि (±15), युति (±8), अस्त (−15), वक्री (±5) पर आधारित। सीमा: 0-100।</div>')

    # ── Hindi Vedic Remedies Page ─────────────────────────────
    if strength_data:
        PLANET_REMEDIES_HI = {
            "Sun": ("माणिक्य (Ruby)", "सूर्य नमस्कार, आदित्य हृदयम्",
                    "रविवार", "गेहूँ, गुड़, ताँबा — पिता तुल्य व्यक्तियों को",
                    "रविवार को लाल/गहरे लाल वस्त्र"),
            "Moon": ("मोती (Pearl)", "चन्द्र मंत्र, दुर्गा चालीसा",
                     "सोमवार", "सफेद चावल, दूध, चाँदी — माता तुल्य व्यक्तियों को",
                     "सोमवार को सफेद वस्त्र"),
            "Mars": ("मूँगा (Red Coral)", "हनुमान चालीसा, मंगल मंत्र",
                     "मंगलवार", "लाल मसूर, गुड़ — भाई-बहन/सैनिकों को",
                     "मंगलवार को लाल वस्त्र"),
            "Mercury": ("पन्ना (Emerald)", "विष्णु सहस्रनाम, बुध मंत्र",
                        "बुधवार", "हरी मूँग दाल, पुस्तकें — छात्रों को",
                        "बुधवार को हरे वस्त्र"),
            "Jupiter": ("पुखराज (Yellow Sapphire)", "गुरु मंत्र, बृहस्पति स्तोत्रम्",
                        "गुरुवार", "पीली वस्तुएँ, हल्दी, केला — ब्राह्मणों/गुरुओं को",
                        "गुरुवार को पीले वस्त्र"),
            "Venus": ("हीरा / सफेद पुखराज", "शुक्र मंत्र, लक्ष्मी स्तोत्रम्",
                      "शुक्रवार", "सफेद वस्तुएँ, चावल, रेशम — महिलाओं को",
                      "शुक्रवार को सफेद/क्रीम वस्त्र"),
            "Saturn": ("नीलम (Blue Sapphire) — सावधानी से", "शनि मंत्र, हनुमान चालीसा",
                       "शनिवार", "काले तिल, सरसों का तेल, लोहा — श्रमिकों को",
                       "शनिवार को काले/गहरे नीले वस्त्र"),
            "Rahu": ("गोमेद (Hessonite)", "राहु मंत्र, दुर्गा सप्तशती",
                     "शनिवार", "काली वस्तुएँ, नारियल — सफाईकर्मियों को",
                     "नशे से बचें, ईमानदारी का अभ्यास करें"),
            "Ketu": ("लहसुनिया (Cat's Eye)", "केतु मंत्र, गणेश अथर्वशीर्ष",
                     "मंगलवार/शनिवार", "बहुरंगी कम्बल — संन्यासियों/तपस्वियों को",
                     "आध्यात्मिक साधना, ध्यान, वैराग्य"),
        }

        html_parts.append('<div class="page-break"></div>')
        html_parts.append("<h2>वैदिक उपाय — त्वरित संदर्भ</h2>")
        html_parts.append('<div class="brand">by AstroShuklz</div>')

        html_parts.append('<div class="reading" style="font-style:italic; font-size:8pt; color:#666;">'
            'नोट: रत्न केवल योग्य ज्योतिषी से परामर्श के बाद ही धारण करें। '
            'मंत्र, दान और कर्म सुधार सबसे सुरक्षित और सर्वाधिक अनुशंसित उपाय हैं।</div>')

        html_parts.append(
            '<h3 style="color:#8B0000;">उपाय क्रम (सर्वोच्च से भौतिक):</h3>'
            '<div class="reading">'
            '🧘 <b>सर्वोच्च:</b> मंत्र/जप, दान, कर्म सुधार (व्यवहार परिवर्तन)<br/>'
            '🔮 <b>मध्यम:</b> व्रत (उपवास), पूजा/अनुष्ठान<br/>'
            '💎 <b>भौतिक:</b> रत्न (केवल योग्य मार्गदर्शन से)</div>')

        for pname in order:
            sinfo = strength_data[pname]
            hi_name = PLANET_HI_FULL.get(pname, pname)
            remedy_class = sinfo.get('remedy', 'Balance')
            remedy_hi = REMEDY_HI.get(remedy_class, 'संतुलित करें')
            icon = REMEDY_ICONS.get(remedy_class, '⚖️')
            ovr_hi = STRENGTH_LABELS_HI.get(sinfo['overall'], sinfo['overall'])
            gem, mantra, day, charity, tip = PLANET_REMEDIES_HI[pname]

            html_parts.append(
                f'<h3 style="color:#8B0000;">{icon} {hi_name} — '
                f'{ovr_hi} ({sinfo["score"]}/100) — {remedy_hi}</h3>')

            if remedy_class == "Strengthen":
                html_parts.append(
                    f'<div class="reading">'
                    f'<b>मंत्र:</b> {mantra} | <b>दिन:</b> {day}<br/>'
                    f'<b>दान:</b> {charity}<br/>'
                    f'<b>रत्न:</b> {gem} (पहले ज्योतिषी से परामर्श करें)<br/>'
                    f'<b>सुझाव:</b> {tip}</div>')
            elif remedy_class == "Pacify":
                html_parts.append(
                    f'<div class="reading">'
                    f'<b>मंत्र:</b> {mantra} | <b>व्रत:</b> {day}<br/>'
                    f'<b>दान:</b> {charity}<br/>'
                    f'<b>सावधानी:</b> {gem} न पहनें — शांत करें, बल न बढ़ाएँ<br/>'
                    f'<b>सुझाव:</b> {tip}</div>')
            else:
                html_parts.append(
                    f'<div class="reading">'
                    f'<b>मंत्र:</b> {mantra} | <b>दिन:</b> {day}<br/>'
                    f'<b>दान:</b> {charity}<br/>'
                    f'<b>सुझाव:</b> {tip}</div>')

    # ── Hindi Karma Remedy Page ──────────────────────────────
    if strength_data:
        KARMA_HI = {
            "Sun": {"icon":"☀️", "principle":"उत्तरदायित्व लें और सत्यनिष्ठा से कार्य करें — मान्यता की खोज बंद करें।",
                "weak":"आत्मविश्वास और नेतृत्व को सुदृढ़ करें। छोटी स्थितियों में आगे बढ़ें, स्वयं के लिए बोलें, और कर्म से आत्मविश्वास बनाएँ।",
                "strong":"आपका सूर्य प्रबल है। अहंकार से बचें, दूसरों की स्वतंत्रता का सम्मान करें, और उदाहरण से नेतृत्व करें।",
                "moderate":"सत्यनिष्ठा बनाए रखें, पिता/पितृ तुल्य व्यक्तियों का सम्मान करें, और अपने निर्णयों की ज़िम्मेदारी लें।"},
            "Moon": {"icon":"🌙", "principle":"मन को स्थिर करें — भीतर से भावनात्मक सुरक्षा बनाएँ।",
                "weak":"भावनात्मक अस्थिरता हो सकती है। दैनिक ध्यान करें, जल के निकट समय बिताएँ, माता से सम्बन्ध सुदृढ़ करें।",
                "strong":"भावनात्मक गहराई आपका उपहार है। मनोवेग से निर्णय न लें, आवश्यकतानुसार वैराग्य का अभ्यास करें।",
                "moderate":"दिनचर्या, विश्राम और सार्थक सम्बन्धों से भावनात्मक संतुलन बनाएँ।"},
            "Mars": {"icon":"♂️", "principle":"क्रोध पर नियंत्रण रखें — ऊर्जा को अनुशासित कार्य में लगाएँ।",
                "weak":"दृढ़ता और शारीरिक ऊर्जा बढ़ाएँ। नियमित व्यायाम करें, ना कहना सीखें, साहस का अभ्यास करें।",
                "strong":"आपका मंगल प्रबल है। आक्रामकता और आवेगी निर्णयों से बचें। ऊर्जा को खेल या रचनात्मक कार्य में लगाएँ।",
                "moderate":"दृढ़ता और धैर्य में संतुलन रखें। सही के लिए खड़े हों पर विवेकपूर्ण रहें।"},
            "Mercury": {"icon":"☿", "principle":"स्पष्ट संवाद करें — अति-चिंतन और चतुर छल से बचें।",
                "weak":"संवाद और विश्लेषण कौशल सुधारें। अधिक पढ़ें, लिखें, नया कौशल सीखें।",
                "strong":"आपकी तीव्र बुद्धि सम्पत्ति है। छल या अति-चिंतन से बचें। व्यापार में ईमानदार रहें।",
                "moderate":"सीखते और संवाद करते रहें। गपशप से बचें, सक्रिय श्रवण का अभ्यास करें।"},
            "Jupiter": {"icon":"♃", "principle":"नैतिक जीवन जिएँ — ज्ञान को लागू करें, केवल उपदेश न दें।",
                "weak":"ज्ञान और बुद्धि सक्रिय रूप से खोजें। शास्त्र पढ़ें, गुरु खोजें, दूसरों को सिखाएँ, बिना अपेक्षा दान करें।",
                "strong":"गुरु आपको ज्ञान प्रदान करता है। आत्म-धार्मिकता से बचें, विनम्र रहें, निर्धनों की शिक्षा में सहयोग करें।",
                "moderate":"आध्यात्मिक और बौद्धिक विकास जारी रखें। गुरुजनों का सम्मान करें, दानशील रहें।"},
            "Venus": {"icon":"♀️", "principle":"सम्बन्धों को महत्व दें — सुख और उत्तरदायित्व में संतुलन रखें।",
                "weak":"सम्बन्धों और सुख-सुविधाओं पर ध्यान दें। कृतज्ञता का अभ्यास करें, साथी की देखभाल करें, कला में रुचि विकसित करें।",
                "strong":"शुक्र आपको आकर्षण और समृद्धि देता है। विलासिता में अति से बचें, सम्बन्धों को हल्के में न लें।",
                "moderate":"सम्बन्धों को ध्यान और देखभाल से पोषित करें। भौतिक सुख और आध्यात्मिक मूल्यों में संतुलन रखें।"},
            "Saturn": {"icon":"♄", "principle":"निरंतर रहें — बिना शिकायत धैर्यपूर्वक कर्तव्य निभाएँ।",
                "weak":"विलम्ब और बाधाएँ आ सकती हैं। कठोर परिश्रम अपनाएँ, परिणामों में धैर्य रखें, बुजुर्गों की सेवा करें।",
                "strong":"शनि आपको अनुशासन और सहनशक्ति देता है। अत्यधिक कठोरता से बचें, करुणा का अभ्यास करें।",
                "moderate":"उत्तरदायित्वों के प्रति प्रतिबद्ध रहें। श्रमिकों और सेवकों का सम्मान करें, समयनिष्ठ रहें।"},
            "Rahu": {"icon":"☊", "principle":"इच्छाओं पर नियंत्रण रखें — शॉर्टकट से बचें और वास्तविकता में टिके रहें।",
                "weak":"भ्रम और भटकाव हो सकता है। नशे से दूर रहें, जल्दी अमीर बनने की योजनाओं से बचें, ईमानदारी अपनाएँ।",
                "strong":"राहु भौतिक महत्वाकांक्षा देता है। लक्ष्यों की अंधी खोज से बचें, संतोष का अभ्यास करें, पारदर्शी रहें।",
                "moderate":"महत्वाकांक्षाओं को नैतिकता पर आधारित रखें। छल से बचें, अपनी जड़ों से जुड़े रहें।"},
            "Ketu": {"icon":"☋", "principle":"केंद्रित रहें — आध्यात्मिकता और व्यावहारिक जीवन में संतुलन रखें।",
                "weak":"दिशाहीनता या वैराग्य हो सकता है। दिनचर्या से स्वयं को स्थिर करें, पारिवारिक सम्बन्ध बनाए रखें।",
                "strong":"केतु गहन आध्यात्मिक दृष्टि देता है। संसार से अत्यधिक विरक्ति से बचें, प्रियजनों से जुड़े रहें।",
                "moderate":"आंतरिक चिंतन और बाहरी सहभागिता में संतुलन रखें। ध्यान करें पर उत्तरदायित्व न छोड़ें।"},
        }

        html_parts.append('<div class="page-break"></div>')
        html_parts.append("<h2>कर्म उपाय विधान</h2>")
        html_parts.append('<div class="brand">by AstroShuklz</div>')
        html_parts.append(
            '<div style="font-style:italic; font-size:9pt; color:#2E4057; '
            'border:1px solid #8B0000; padding:8px; background:#FFF8F0; margin:8px 0;">'
            'कर्म सुधार वैदिक ज्योतिष में सबसे उच्च और शक्तिशाली उपाय है। '
            'मंत्र और अनुष्ठान लक्षणों को संबोधित करते हैं, जबकि अपने व्यवहार और कर्मों को '
            'बदलना मूल कारण को संबोधित करता है। नीचे आपका व्यक्तिगत कर्म विधान प्रत्येक '
            'ग्रह की शक्ति और आपकी कुण्डली में भूमिका पर आधारित है।</div>')

        for pname in order:
            sinfo = strength_data[pname]
            hi_name = PLANET_HI_FULL.get(pname, pname)
            kr = KARMA_HI[pname]
            overall = sinfo['overall']
            ovr_hi = STRENGTH_LABELS_HI.get(overall, overall)
            score = sinfo['score']

            if overall == "Weak":
                advice = kr['weak']
            elif overall == "Strong":
                advice = kr['strong']
            else:
                advice = kr['moderate']

            html_parts.append(
                f'<h3 style="color:#8B0000;">{kr["icon"]} {hi_name} — '
                f'{ovr_hi} ({score}/100)</h3>')
            html_parts.append(
                f'<div class="reading" style="font-style:italic; color:#555; font-size:8.5pt;">'
                f'{kr["principle"]}</div>')
            html_parts.append(f'<div class="reading">{advice}</div>')

        html_parts.append(
            '<div style="text-align:center; font-style:italic; font-size:9pt; '
            'color:#2E4057; border:1px solid #8B0000; padding:8px; '
            'background:#FFF8F0; margin:15px 0;">'
            '"आपका कर्म ही आपका सबसे बड़ा उपाय है। अपने कर्म बदलें, ग्रह स्वयं अनुकूल होंगे।"'
            '<br/>— शास्त्रीय वैदिक ज्ञान</div>')

    # ── Hindi Navamsha (D-9) Pages ─────────────────────────────────
    navamsha = chart.get('navamsha')
    if navamsha:
        html_parts.append('<div class="page-break"></div>')
        html_parts.append("<h2>नवांश (D-9) — विभागीय चार्ट</h2>")
        html_parts.append('<div class="brand">by AstroShuklz</div>')

        nav_asc = navamsha['nav_asc_sign_idx']
        nav_planets = navamsha['navamsha_planets']
        nav_house_planets = navamsha['nav_house_planets']

        BHAV_NAMES_HI_NAV = {
            1: "तनु",    2: "धन",     3: "सहज",    4: "सुख",
            5: "पुत्र",   6: "अरि",    7: "कलत्र",   8: "रन्ध्र",
            9: "धर्म",  10: "कर्म",   11: "लाभ",   12: "व्यय",
        }

        html_parts.append('<table style="font-size:9.5pt;"><tr>'
                           '<th>#</th><th>भवन</th><th>भाव</th>'
                           '<th>राशि (D-9)</th><th>Zodiac</th>'
                           '<th>ग्रह</th><th>D-1 राशि</th><th>वर्ग</th></tr>')

        for rank in range(1, 13):
            sign_idx = (nav_asc + rank - 1) % 12
            house_num = rank
            bhav_hi = BHAV_NAMES_HI_NAV.get(house_num, "")
            rashi_hi = SIGNS_HI_TBL[sign_idx]
            zodiac = SIGNS_EN[sign_idx]

            plist = nav_house_planets.get(rank, [])
            if plist:
                planet_str = ", ".join(PLANET_HI_FULL.get(p, p) for p in plist)
                d1_parts = []
                has_varg = False
                for pname in plist:
                    ndata = nav_planets[pname]
                    d1_parts.append(SIGNS_HI_TBL[ndata['natal_sign_idx']])
                    if ndata['is_vargottama']:
                        has_varg = True
                d1_str = ", ".join(d1_parts)
                varg_str = "\u2726" if has_varg else ""
            else:
                planet_str = "-"
                d1_str = "-"
                varg_str = ""

            row_style = ""
            if rank == 1:
                row_style = ' style="background:#FFF3CD; font-weight:bold;"'
            elif has_varg if plist else False:
                row_style = ' style="background:#E8F5E9;"'

            html_parts.append(f"<tr{row_style}><td>{rank}</td><td><b>{house_num}</b></td>"
                               f"<td>{bhav_hi}</td><td>{rashi_hi}</td>"
                               f"<td>{zodiac}</td>"
                               f"<td>{planet_str}</td><td>{d1_str}</td>"
                               f"<td>{varg_str}</td></tr>")
        html_parts.append("</table>")

        html_parts.append(
            '<div style="font-size:8pt; color:#666; margin-top:5px;">'
            '<b>नवांश (D-9)</b> वैदिक ज्योतिष में सबसे महत्वपूर्ण विभागीय चार्ट है। '
            'यह आपके आंतरिक स्वभाव, आत्मा का उद्देश्य और विवाह भाग्य को दर्शाता है। '
            '<b>वर्गोत्तम</b> (\u2726) ग्रह D-1 और D-9 दोनों में एक ही राशि में हैं।</div>')

        # ── Hindi Navamsha Reading Page ────────────────────────
        html_parts.append('<div class="page-break"></div>')
        html_parts.append("<h2>नवांश पठन — आंतरिक स्वभाव एवं विवाह</h2>")
        html_parts.append('<div class="brand">by AstroShuklz</div>')

        nav_readings_hi = generate_navamsha_reading(chart, strength_data, lang="hi")
        for heading, body in nav_readings_hi:
            if heading.startswith("TABLE:"):
                table_title = heading[6:]
                html_parts.append(f'<h3 style="color:#8B0000;">{table_title}</h3>')
                html_parts.append('<table><tr><th>ग्रह</th><th>D-1</th><th>D-9</th>'
                                  '<th></th><th>प्रवृत्ति</th><th>अर्थ</th></tr>')
                for (p_label, d1_label, d9_label, arrow, trend, meaning) in body:
                    if arrow == "↑":
                        clr = "#2E7D32"
                    elif arrow == "↓":
                        clr = "#C62828"
                    else:
                        clr = "#1565C0"
                    html_parts.append(
                        f'<tr><td>{p_label}</td><td>{d1_label}</td><td>{d9_label}</td>'
                        f'<td style="color:{clr}; font-size:14pt;">{arrow}</td>'
                        f'<td style="color:{clr}; font-weight:bold;">{trend}</td>'
                        f'<td style="text-align:left;">{meaning}</td></tr>')
                html_parts.append('</table>')
            else:
                html_parts.append(f'<h3 style="color:#8B0000;">{heading}</h3>')
                for para in body.split("\n\n"):
                    para = para.strip()
                    if para:
                        html_parts.append(f'<div class="reading">{para.replace(chr(10), "<br/>")}</div>')

    # ── Hindi Sade Sati Page ───────────────────────────────────────
    sade_sati = chart.get('sade_sati', [])
    if sade_sati:
        html_parts.append('<div class="page-break"></div>')
        html_parts.append("<h1>साढ़ेसाती — शनि का साढ़े सात वर्षीय गोचर</h1>")
        html_parts.append('<div class="brand">by AstroShuklz</div>')

        moon_sign_hi = SIGNS_HI_FULL[moon_sign]
        html_parts.append(f'<h2>साढ़ेसाती क्या है?</h2>')
        html_parts.append(
            f'<div class="reading">साढ़ेसाती तब होती है जब शनि आपकी चन्द्र राशि '
            f'(<b>{moon_sign_hi}</b>) से 12वें, 1ले और 2रे भाव से गोचर करते हैं। '
            f'प्रत्येक चक्र लगभग 7.5 वर्ष का होता है और जीवनकाल में 2-3 बार आता है। '
            f'यह कार्मिक शिक्षा, अनुशासन और अंततः आध्यात्मिक विकास लाती है।</div>')

        # Cycles table
        html_parts.append('<h2>आपके साढ़ेसाती चक्र</h2>')
        html_parts.append('<table><tr><th>चक्र</th><th>चरण</th>'
                          '<th>अवधि</th><th>काल</th><th>स्थिति</th></tr>')

        phase_name_hi = {'Rising': 'उदय', 'Peak': 'चरम', 'Setting': 'अस्त'}
        for period in sade_sati:
            for p_idx, (phase_name, phase_start) in enumerate(period['phases']):
                if p_idx + 1 < len(period['phases']):
                    phase_end = period['phases'][p_idx + 1][1]
                else:
                    phase_end = period['end_date']

                start_str = phase_start.strftime('%b %Y')
                end_str = phase_end.strftime('%b %Y') if phase_end else "जारी"

                if phase_end:
                    dur_days = (phase_end - phase_start).days
                    dur_years = dur_days / 365.25
                    dur_str = f"{dur_years:.1f} वर्ष"
                else:
                    dur_str = "—"

                is_this_phase_current = (period['is_current'] and
                                         period['phase'] == phase_name)
                if is_this_phase_current:
                    status = "वर्तमान ◄"
                elif phase_end and phase_end < today:
                    status = "बीता"
                else:
                    status = "भविष्य"

                cls = ' class="now"' if is_this_phase_current else ''
                cycle_label = str(period['cycle']) if p_idx == 0 else ''
                html_parts.append(
                    f'<tr{cls}><td>{cycle_label}</td>'
                    f'<td>{phase_name_hi.get(phase_name, phase_name)}</td>'
                    f'<td>{start_str} — {end_str}</td>'
                    f'<td>{dur_str}</td><td>{status}</td></tr>')
        html_parts.append('</table>')

        # Current status
        html_parts.append('<h2>वर्तमान स्थिति</h2>')
        current_period = None
        for p in sade_sati:
            if p['is_current']:
                current_period = p
                break

        if current_period:
            phase = current_period['phase']
            phase_info = SADE_SATI_PHASES_HI.get(phase, {})
            html_parts.append(
                f'<div class="reading"><b>आप वर्तमान में साढ़ेसाती में हैं — '
                f'{phase_info.get("title", phase)}</b></div>')
            html_parts.append(f'<div class="reading">{phase_info.get("description", "")}</div>')
            html_parts.append('<div class="reading"><b>प्रमुख प्रभाव:</b></div>')
            for effect in phase_info.get('effects', []):
                html_parts.append(f'<div class="reading">\u2022 {effect}</div>')
        else:
            future = [p for p in sade_sati if p['start_date'] > today]
            past = [p for p in sade_sati if p['end_date'] and p['end_date'] <= today]
            if future:
                nxt = future[0]
                html_parts.append(
                    f'<div class="reading">आप वर्तमान में साढ़ेसाती में <b>नहीं</b> हैं। '
                    f'आपकी अगली साढ़ेसाती लगभग <b>{nxt["start_date"].strftime("%B %Y")}</b> '
                    f'में प्रारम्भ होगी।</div>')
            elif past:
                last = past[-1]
                html_parts.append(
                    f'<div class="reading">आप वर्तमान में साढ़ेसाती में <b>नहीं</b> हैं। '
                    f'आपकी अंतिम साढ़ेसाती लगभग <b>{last["end_date"].strftime("%B %Y")}</b> '
                    f'में समाप्त हुई।</div>')

        # Remedies
        html_parts.append('<h2>साढ़ेसाती उपाय</h2>')
        html_parts.append('<h3 style="color:#8B0000;">आध्यात्मिक उपाय</h3>')
        for r in SADE_SATI_REMEDIES_HI['spiritual']:
            html_parts.append(f'<div class="reading">\u2022 {r}</div>')
        html_parts.append('<h3 style="color:#8B0000;">कर्म सुधार</h3>')
        for r in SADE_SATI_REMEDIES_HI['karma']:
            html_parts.append(f'<div class="reading">\u2022 {r}</div>')
        html_parts.append('<h3 style="color:#8B0000;">व्यावहारिक सलाह</h3>')
        for r in SADE_SATI_REMEDIES_HI['practical']:
            html_parts.append(f'<div class="reading">\u2022 {r}</div>')

    # ── Hindi Dasha Tables ───────────────────────────────────────
    html_parts.append('<div class="page-break"></div>')

    # Mahadasha
    html_parts.append("<h2>विंशोत्तरी दशा — महादशा</h2>")
    html_parts.append("<table><tr><th>स्वामी</th><th>आरंभ</th>"
                       "<th>अंत</th><th>वर्ष</th><th></th></tr>")
    current_maha = None
    for lord, start, end, yrs in chart['dashas']:
        is_now = start <= today < end
        if is_now:
            current_maha = lord
        cls = ' class="now"' if is_now else ""
        marker = "◄ अभी" if is_now else ""
        html_parts.append(f"<tr{cls}><td>{PLANET_HI_FULL.get(lord, lord)}</td>"
                           f"<td>{start.strftime('%b %Y')}</td>"
                           f"<td>{end.strftime('%b %Y')}</td>"
                           f"<td>{yrs:.1f}</td><td>{marker}</td></tr>")
    html_parts.append("</table>")

    # Antardasha
    if current_maha and current_maha in chart.get('antardasha', {}):
        maha_hi = PLANET_HI_FULL.get(current_maha, current_maha)
        html_parts.append(f"<h2>विंशोत्तरी दशा — "
                           f"अंतर्दशा ({maha_hi} महादशा में)</h2>")
        html_parts.append("<table><tr><th>स्वामी</th><th>आरंभ</th>"
                           "<th>अंत</th><th>अवधि</th><th></th></tr>")
        current_antar = None
        for ad_lord, ad_start, ad_end, ad_yrs in chart['antardasha'][current_maha]:
            is_now = ad_start <= today < ad_end
            if is_now:
                current_antar = ad_lord
            cls = ' class="now"' if is_now else ""
            marker = "◄ अभी" if is_now else ""
            months = ad_yrs * 12
            dur = f"{ad_yrs:.1f}व" if months >= 12 else f"{months:.1f}म"
            html_parts.append(f"<tr{cls}><td>{PLANET_HI_FULL.get(ad_lord, ad_lord)}</td>"
                               f"<td>{ad_start.strftime('%d %b %Y')}</td>"
                               f"<td>{ad_end.strftime('%d %b %Y')}</td>"
                               f"<td>{dur}</td><td>{marker}</td></tr>")
        html_parts.append("</table>")

        # Pratyantar
        if current_antar:
            key = (current_maha, current_antar)
            if key in chart.get('pratyantar', {}):
                antar_hi = PLANET_HI_FULL.get(current_antar, current_antar)
                html_parts.append(f"<h2>विंशोत्तरी दशा — "
                                   f"प्रत्यंतर ({maha_hi}–{antar_hi})</h2>")
                html_parts.append("<table><tr><th>स्वामी</th><th>आरंभ</th>"
                                   "<th>अंत</th><th>अवधि</th><th></th></tr>")
                for pd_lord, pd_start, pd_end, pd_yrs in chart['pratyantar'][key]:
                    is_now = pd_start <= today < pd_end
                    cls = ' class="now"' if is_now else ""
                    marker = "◄ अभी" if is_now else ""
                    days = pd_yrs * 365.25
                    dur = f"{pd_yrs*12:.1f}म" if days >= 30 else f"{days:.0f}द"
                    html_parts.append(f"<tr{cls}><td>{PLANET_HI_FULL.get(pd_lord, pd_lord)}</td>"
                                       f"<td>{pd_start.strftime('%d %b %Y')}</td>"
                                       f"<td>{pd_end.strftime('%d %b %Y')}</td>"
                                       f"<td>{dur}</td><td>{marker}</td></tr>")
                html_parts.append("</table>")

    # ── Hindi Page 3: Predictions ────────────────────────────────
    html_parts.append('<div class="page-break"></div>')
    html_parts.append("<h1>दशा फल एवं भविष्यवाणी</h1>")
    html_parts.append('<div class="brand">by AstroShuklz</div>')

    hi_reading = _dasha_reading_hi(chart, today)
    for block in hi_reading:
        if block.startswith("##"):
            html_parts.append(f"<h3>{block[2:].strip()}</h3>")
        else:
            html_parts.append(f'<div class="reading">{block}</div>')

    # Disclaimer
    html_parts.append('<div class="disclaimer">'
                       'अस्वीकरण: यह पठन '
                       'शास्त्रीय विंशोत्तरी '
                       'दशा व्याख्याओं पर '
                       'आधारित है। '
                       'व्यक्तिगत मार्गदर्शन '
                       'के लिए किसी योग्य '
                       'ज्योतिष से परामर्श करें।</div>')
    html_parts.append('<div class="footer">Lahiri Ayanamsha · Swiss Ephemeris · Generated by AstroShuklz</div>')
    html_parts.append("</body></html>")

    html_str = "\n".join(html_parts)
    buf = _io.BytesIO()
    HTML(string=html_str).write_pdf(buf)
    buf.seek(0)
    return buf


def generate_pdf_to_buffer(chart, svg_content=None):
    """
    Generate PDF report to an in-memory BytesIO buffer (no file I/O).
    Used by the Flask web app. Returns a seeked-to-0 BytesIO object.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                     Paragraph, Spacer, PageBreak)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    import io

    # ── Register Devanagari font (cross-platform) ────────────────
    deva_font = "Helvetica"
    deva_font_bold = "Helvetica-Bold"
    # Bundled font first (works on PythonAnywhere), then system fonts
    _bundled_font = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "fonts", "NotoSansDevanagari.ttf")
    font_paths = [
        _bundled_font,
        # macOS
        "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",
        # Linux system fonts
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.otf",
        "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
    ]
    for fp in font_paths:
        try:
            if fp.endswith(".ttc"):
                pdfmetrics.registerFont(TTFont("DevSangam", fp, subfontIndex=0))
            else:
                pdfmetrics.registerFont(TTFont("DevSangam", fp))
            deva_font = "DevSangam"
            deva_font_bold = "DevSangam"
            break
        except Exception:
            continue

    # ── Colours ──────────────────────────────────────────────────
    MAROON      = colors.HexColor("#8B0000")
    HEADER_BG   = colors.HexColor("#8B0000")
    HEADER_FG   = colors.white
    ROW_ALT     = colors.HexColor("#FFF8E7")
    ROW_NOW     = colors.HexColor("#FFFACD")

    # ── Document setup ───────────────────────────────────────────
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4,
                            topMargin=15*mm, bottomMargin=15*mm,
                            leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('KTitle', parent=styles['Title'],
        fontName=deva_font, fontSize=22, textColor=MAROON,
        alignment=TA_CENTER, spaceAfter=2*mm)
    subtitle_style = ParagraphStyle('KSubtitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=11, textColor=colors.HexColor("#444"),
        alignment=TA_CENTER, spaceAfter=1*mm)
    info_style = ParagraphStyle('KInfo', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#555"),
        alignment=TA_CENTER, spaceAfter=3*mm)
    section_style = ParagraphStyle('KSection', parent=styles['Heading2'],
        fontName='Helvetica-Bold', fontSize=12, textColor=MAROON,
        alignment=TA_CENTER, spaceBefore=5*mm, spaceAfter=2*mm)

    bd = chart['birth_data']
    planets = chart['planets']
    asc_sign = chart['asc_sign']
    moon_sign = planets['Moon']['sign_idx']
    today = datetime.now()

    # ── Branding subtitle style ────────────────────────────────
    brand_style = ParagraphStyle('KBrand', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=10, textColor=colors.HexColor("#B8860B"),
        alignment=TA_CENTER, spaceAfter=4*mm)

    # ── Page 1: Header + Planetary Positions ─────────────────────
    story.append(Paragraph("जन्म कुण्डली", title_style))
    story.append(Paragraph("by AstroShuklz", brand_style))
    story.append(Paragraph(f"{bd['name']}", subtitle_style))
    story.append(Paragraph(
        f"{bd['day']:02d}/{bd['month']:02d}/{bd['year']}  &nbsp; "
        f"{bd['hour']:02d}:{bd['minute']:02d}  &nbsp;·&nbsp; {bd['place']}",
        info_style))

    summary = (f"Lagna: {chart['asc_sign_en']} ({chart['asc_sign_hi']}) "
               f"{dms_str(chart['asc_deg'])}  &nbsp;·&nbsp; "
               f"Rashi: {chart['moon_rashi']} ({chart['moon_rashi_hi']})  &nbsp;·&nbsp; "
               f"Nakshatra: {chart['nakshatra']}, Pada {chart['nak_pada']} "
               f"({chart['nak_lord']})")
    story.append(Paragraph(summary, info_style))
    story.append(Spacer(1, 3*mm))

    # ── Reference data for House Position table ─────────────────
    BHAV_NAMES = {
        1: "Tanu",    2: "Dhana",   3: "Sahaja",  4: "Sukha",
        5: "Putra",   6: "Ari",     7: "Kalatra",  8: "Randhra",
        9: "Dharma", 10: "Karma",  11: "Labha",   12: "Vyaya",
    }
    BHAV_NAMES_HI = {
        1: "तनु",    2: "धन",     3: "सहज",    4: "सुख",
        5: "पुत्र",   6: "अरि",    7: "कलत्र",   8: "रन्ध्र",
        9: "धर्म",  10: "कर्म",   11: "लाभ",   12: "व्यय",
    }
    HOUSE_DESC = {
        1: "Self, body, personality, appearance, health, vitality",
        2: "Wealth, family, speech, food, values, early education",
        3: "Siblings, courage, communication, short travel, efforts",
        4: "Mother, happiness, home, property, vehicles, inner peace",
        5: "Children, intelligence, creativity, romance, past merit",
        6: "Enemies, disease, debts, obstacles, service, competition",
        7: "Spouse, partnerships, business, foreign travel, public",
        8: "Transformation, longevity, secrets, occult, inheritance",
        9: "Luck, father, dharma, higher learning, long travel, guru",
        10: "Career, status, authority, fame, actions, government",
        11: "Gains, income, friends, networks, fulfilment of desires",
        12: "Loss, expenses, foreign lands, moksha, isolation, sleep",
    }
    SIGNS_EN = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
                "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    SIGNS_HI_FULL = ["Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya",
                     "Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"]
    RASHI_ELEMENT = ["Fire","Earth","Air","Water","Fire","Earth",
                     "Air","Water","Fire","Earth","Air","Water"]
    RASHI_NATURE = ["Movable","Fixed","Dual","Movable","Fixed","Dual",
                    "Movable","Fixed","Dual","Movable","Fixed","Dual"]
    RASHI_QUALITY = [
        "Bold, pioneering, leadership",
        "Steady, patient, materialistic",
        "Adaptable, communicative, curious",
        "Nurturing, emotional, protective",
        "Confident, creative, authoritative",
        "Analytical, detail-oriented, service",
        "Balanced, diplomatic, aesthetic",
        "Intense, transformative, secretive",
        "Adventurous, philosophical, optimistic",
        "Ambitious, disciplined, practical",
        "Innovative, humanitarian, independent",
        "Intuitive, compassionate, spiritual",
    ]

    # ── Paragraph styles for table cells ──
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=11,
        textColor=colors.HexColor("#333"))
    cell_style_bold = ParagraphStyle('CellBold', parent=cell_style,
        fontName='Helvetica-Bold', fontSize=9)
    cell_center = ParagraphStyle('CellCenter', parent=cell_style,
        alignment=TA_CENTER)
    cell_center_bold = ParagraphStyle('CellCenterBold', parent=cell_style_bold,
        alignment=TA_CENTER)
    footnote_style = ParagraphStyle('Footnote', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#666"),
        leading=11, spaceBefore=3*mm)
    footnote_bold = ParagraphStyle('FootnoteBold', parent=footnote_style,
        fontName='Helvetica-Bold', textColor=MAROON)

    # ── Page 1: Comprehensive House Position Table ────────────
    story.append(Paragraph("Planetary Position", section_style))

    # Build planet lookup: house_num -> list of (name, degree, retro)
    planet_in_house = {h: [] for h in range(1, 13)}
    order = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]
    for pname in order:
        p = planets[pname]
        sidx = p['sign_idx']
        h_lag = (sidx - asc_sign) % 12 + 1
        planet_in_house[h_lag].append((pname, dms_str(p['deg']),
                                       "R" if p['retro'] else ""))

    # Moon's house for HFM calculation
    moon_house = (moon_sign - asc_sign) % 12 + 1

    # Table header — short single-row labels
    hp_header = [
        Paragraph('<b>#</b>', cell_center_bold),
        Paragraph('<b>Hse</b>', cell_center_bold),
        Paragraph('<b>Bhav</b>', cell_center_bold),
        Paragraph('<b>House Characteristics</b>', cell_style_bold),
        Paragraph('<b>Zodiac</b>', cell_center_bold),
        Paragraph('<b>Rashi</b>', cell_center_bold),
        Paragraph('<b>Rashi Characteristics</b>', cell_style_bold),
        Paragraph('<b>Planet</b>', cell_center_bold),
        Paragraph('<b>Degree</b>', cell_center_bold),
        Paragraph('<b>R</b>', cell_center_bold),
        Paragraph('<b>HFM</b>', cell_center_bold),
    ]
    hp_data = [hp_header]

    # Build rows — start from Ascendant house, cycle through 12
    for rank in range(1, 13):
        house_num = ((asc_sign + rank - 1) % 12) + 1  # house number
        sign_idx = (asc_sign + rank - 1) % 12          # 0-based sign index
        bhav = BHAV_NAMES[house_num]
        bhav_hi = BHAV_NAMES_HI[house_num]
        desc = HOUSE_DESC[house_num]
        zodiac = SIGNS_EN[sign_idx]
        rashi = SIGNS_HI_FULL[sign_idx]
        rashi_char = f"{RASHI_ELEMENT[sign_idx]} | {RASHI_NATURE[sign_idx]}: {RASHI_QUALITY[sign_idx]}"

        # HFM: house from Moon (count from Moon's sign)
        hfm = (sign_idx - moon_sign) % 12 + 1

        # Planets in this house (rank = house from lagna)
        plist = planet_in_house[rank]
        if plist:
            planet_str = ", ".join(p[0] for p in plist)
            deg_str = "\n".join(f"{p[0]}: {p[1]}" for p in plist)
            retro_str = "\n".join(p[2] for p in plist)
        else:
            planet_str = "-"
            deg_str = "-"
            retro_str = ""

        row = [
            Paragraph(str(rank), cell_center),
            Paragraph(str(house_num), cell_center_bold),
            Paragraph(bhav, cell_center),
            Paragraph(desc, cell_style),
            Paragraph(zodiac, cell_center),
            Paragraph(rashi, cell_center),
            Paragraph(rashi_char, cell_style),
            Paragraph(planet_str, cell_center),
            Paragraph(deg_str, cell_center),
            Paragraph(retro_str, cell_center),
            Paragraph(str(hfm), cell_center),
        ]
        hp_data.append(row)

    # Column widths (total ~530 for A4 with margins)
    hp_col_w = [24, 28, 36, 110, 48, 42, 105, 50, 48, 14, 25]
    hp_table = Table(hp_data, colWidths=hp_col_w, repeatRows=1)

    # Header cell style with white text for dark background
    cell_header = ParagraphStyle('CellHeader', parent=cell_center_bold,
        textColor=colors.white, fontSize=7.5)
    cell_header_left = ParagraphStyle('CellHeaderLeft', parent=cell_style_bold,
        textColor=colors.white, fontSize=7.5)

    hp_style_rules = [
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,0), 8.5),
        ('FONTSIZE',   (0,1), (-1,-1), 8.5),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F5E6C8")),
        ('TEXTCOLOR',  (0,0), (-1,0), MAROON),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('TOPPADDING',  (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',(0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING',(0,0), (-1,-1), 3),
    ]

    # Highlight Row 1 (1st House / Ascendant) with golden background
    GOLD_BG = colors.HexColor("#FFF3CD")
    hp_style_rules.append(('BACKGROUND', (0, 1), (-1, 1), GOLD_BG))
    hp_style_rules.append(('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'))

    # Highlight the Moon row (HFM=1) with light blue
    MOON_BG = colors.HexColor("#E3F2FD")
    for rank in range(1, 13):
        sign_idx = (asc_sign + rank - 1) % 12
        hfm = (sign_idx - moon_sign) % 12 + 1
        if hfm == 1:
            hp_style_rules.append(('BACKGROUND', (0, rank), (-1, rank), MOON_BG))
            break

    hp_table.setStyle(TableStyle(hp_style_rules))
    story.append(hp_table)

    # ── Explanatory Notes Page ──────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Planetary Position Table — Explanatory Notes",
                            section_style))
    story.append(Spacer(1, 3*mm))

    # ── Sign rulers for Ascendant note ──
    SIGN_RULERS = {
        "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
        "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
        "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
        "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
    }
    SIGN_TRAITS = {
        "Aries": "bold, pioneering, and action-oriented",
        "Taurus": "steady, patient, and materialistic",
        "Gemini": "adaptable, communicative, and intellectually curious",
        "Cancer": "nurturing, emotional, and protective",
        "Leo": "confident, creative, and authoritative",
        "Virgo": "analytical, detail-oriented, and service-minded",
        "Libra": "balanced, diplomatic, and aesthetic",
        "Scorpio": "intense, transformative, and deeply perceptive",
        "Sagittarius": "adventurous, philosophical, and optimistic",
        "Capricorn": "ambitious, disciplined, and practical",
        "Aquarius": "innovative, humanitarian, and independent",
        "Pisces": "intuitive, compassionate, and spiritual",
    }

    asc_sign_name = chart['asc_sign_en']
    asc_deg_val = chart['asc_deg']
    asc_abs_deg = asc_sign * 30 + asc_deg_val
    asc_ruler = SIGN_RULERS.get(asc_sign_name, "Unknown")
    asc_traits = SIGN_TRAITS.get(asc_sign_name, "")
    asc_deg_in_sign = asc_deg_val  # degree within the sign (0-30)

    note_style = ParagraphStyle('NoteStyle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#333"),
        alignment=TA_LEFT, leading=13, spaceBefore=2*mm, spaceAfter=2*mm)
    note_heading = ParagraphStyle('NoteHeading', parent=note_style,
        fontName='Helvetica-Bold', fontSize=10, textColor=MAROON,
        spaceBefore=4*mm, spaceAfter=1*mm)
    note_summary = ParagraphStyle('NoteSummary', parent=note_style,
        fontName='Helvetica-Oblique', fontSize=9.5,
        textColor=colors.HexColor("#2E4057"),
        borderColor=colors.HexColor("#DAA520"), borderWidth=1,
        borderPadding=6, backColor=colors.HexColor("#FFFDE7"),
        spaceBefore=3*mm, spaceAfter=3*mm)

    # 1. ASCENDANT / LAGNA
    story.append(Paragraph("1. Ascendant (Lagna / Rising Sign)", note_heading))
    story.append(Paragraph(
        'In Vedic astrology, the <b>Ascendant</b> (or Rising Sign) is the zodiac sign '
        'that was rising on the eastern horizon at the exact moment of your birth. '
        'It represents your outward personality, how others perceive you, and your '
        'approach to life. The Ascendant is calculated in degrees (0° to 360°) along '
        'the ecliptic, with each zodiac sign occupying 30° of this circle. '
        'The 1st House row is <font color="#DAA520"><b>highlighted in gold</b></font> '
        'in the table above.',
        note_style))

    # Degree interpretation
    story.append(Paragraph("<b>Degree Interpretation:</b>", note_style))
    story.append(Paragraph(
        f'Your Ascendant is at <b>{asc_abs_deg:.2f}°</b> on the ecliptic. '
        f'Since {asc_sign_name} spans from {asc_sign * 30}° to {asc_sign * 30 + 30}°, '
        f'your Lagna falls at <b>{dms_str(asc_deg_in_sign)}</b> within {asc_sign_name}. '
        f'{"An early degree (0-10°) suggests the sign energy is fresh and raw. " if asc_deg_in_sign < 10 else ""}'
        f'{"A mid-degree (10-20°) indicates the sign qualities are fully expressed. " if 10 <= asc_deg_in_sign < 20 else ""}'
        f'{"A late degree (20-30°) suggests maturity and transition energy from this sign. " if asc_deg_in_sign >= 20 else ""}',
        note_style))

    # Planetary ruler
    story.append(Paragraph("<b>Planetary Ruler:</b>", note_style))
    story.append(Paragraph(
        f'The ruling planet of {asc_sign_name} is <b>{asc_ruler}</b>. '
        f'As the lord of your Ascendant, {asc_ruler}\'s placement in your chart '
        f'(its house, sign, and aspects) has a particularly strong influence on your '
        f'overall life direction, health, and personality expression.',
        note_style))

    # Personalized summary
    story.append(Paragraph(
        f'<b>Summary:</b> Your Ascendant at <b>{asc_abs_deg:.2f}°</b> '
        f'({dms_str(asc_deg_in_sign)} in {asc_sign_name}) means your Rising Sign is '
        f'<b>{asc_sign_name}</b>, and you likely project an energy that is '
        f'{asc_traits}. The influence of {asc_ruler} as your chart ruler further '
        f'shapes your core identity and life path.',
        note_summary))

    # 2. HFM
    story.append(Paragraph("2. HFM (House From Moon)", note_heading))
    moon_sign_name = chart['moon_rashi']
    story.append(Paragraph(
        f'In Vedic astrology, houses are read not only from the <b>Lagna</b> '
        f'(Ascendant) but also from the <b>Moon</b> (Chandra Kundali). '
        f'Your Moon is in <b>{moon_sign_name}</b>, which becomes the 1st house '
        f'of your Moon chart. HFM shows each house counted from the Moon\'s position.',
        note_style))
    story.append(Paragraph(
        'The Moon chart reveals your <b>emotional landscape</b>, mental tendencies, '
        'and inner perception — while the Lagna chart shows your external life '
        'and physical reality. Professional astrologers always read both charts '
        'together for a complete picture. '
        'The Moon\'s house (HFM=1) is '
        '<font color="#1E88E5"><b>highlighted in blue</b></font> in the table.',
        note_style))

    # 3. RETROGRADE
    story.append(Paragraph("3. R (Retrograde Planets)", note_heading))
    story.append(Paragraph(
        'Planets marked with <b>R</b> appear to move backward from Earth\'s '
        'perspective. In Vedic astrology, retrograde planets are considered '
        'strong but their energy turns <b>inward</b>. They often indicate '
        'karmic lessons, delayed but intensified results, unfinished business '
        'from past lives, or areas where deeper introspection is needed. '
        'Retrograde benefics (Jupiter, Venus) can give unexpected gains, while '
        'retrograde malefics (Saturn, Mars) may intensify challenges before '
        'eventual resolution.',
        note_style))

    # 4. BHAV (House System)
    story.append(Paragraph("4. Bhav (House System)", note_heading))
    story.append(Paragraph(
        'Each of the 12 houses (Bhav) governs specific life areas. The house '
        'number in the table corresponds to the natural zodiac position of '
        'the sign occupying that house. The Bhav name (Tanu, Dhana, Sahaja, etc.) '
        'describes the life domain ruled by that house. Planets placed in a house '
        'influence those life areas according to their natural significations.',
        note_style))

    # ── Bhava (House) Reading Pages ──────────────────────────────
    strength_data = calculate_planet_strength(chart)
    bhava_readings = generate_bhava_readings(chart, strength_data, lang="en")

    story.append(PageBreak())
    story.append(Paragraph("Bhava Reading — House Analysis", section_style))
    story.append(Paragraph("by AstroShuklz", brand_style))
    story.append(Spacer(1, 3*mm))

    bhava_intro_style = ParagraphStyle('BhavaIntro', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9.5, textColor=colors.HexColor("#333333"),
        leading=13, spaceAfter=4*mm)
    story.append(Paragraph(
        "Each of the 12 Bhavas (houses) governs specific life areas. The reading below combines "
        "the sign occupying each house, the planets placed there (if any), their strength scores, "
        "and the house lord's condition to give you a personalised assessment of each life domain.",
        bhava_intro_style))

    bhava_head_style = ParagraphStyle('BhavaHead', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#8B0000"),
        leading=14, spaceBefore=4*mm, spaceAfter=1*mm)
    bhava_body_style = ParagraphStyle('BhavaBody', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9.5, textColor=colors.HexColor("#222222"),
        leading=13, spaceAfter=2*mm, leftIndent=4*mm)

    for br in bhava_readings:
        h = br['house']
        planet_str = ", ".join(br['planets']) if br['planets'] else "Empty"
        heading = f"House {h} — {br['bhav']} ({br['title']}) · {br['sign']} · [{planet_str}]"
        story.append(Paragraph(heading, bhava_head_style))
        story.append(Paragraph(br['para'], bhava_body_style))

    # ── Planet Strength Analysis Page ────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Planet Strength Analysis", section_style))
    story.append(Paragraph("by AstroShuklz", brand_style))
    story.append(Spacer(1, 2*mm))

    strength_reading_style = ParagraphStyle('StrReading', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#333"),
        alignment=TA_LEFT, leading=12, spaceBefore=1*mm, spaceAfter=1*mm)
    strength_planet_style = ParagraphStyle('StrPlanet', parent=strength_reading_style,
        fontName='Helvetica-Bold', fontSize=9, textColor=MAROON)

    planet_order = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]
    for pname in planet_order:
        reading = _planet_strength_reading(pname, planets[pname],
                                           strength_data[pname], lang="en")
        story.append(Paragraph(f"<b>{pname}:</b> {reading}", strength_reading_style))

    story.append(Spacer(1, 3*mm))

    # Bar chart
    try:
        from reportlab.platypus import Image as RLImage
        chart_buf = _draw_strength_bar_chart(strength_data)
        chart_img = RLImage(chart_buf, width=165*mm, height=97*mm)
        story.append(chart_img)
    except Exception as e:
        story.append(Paragraph(f"[Chart unavailable: {e}]", info_style))

    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "<b>Methodology:</b> Scores combine sign dignity (35), house placement (20), "
        "degree maturity (10), aspects (±15), conjunctions (±8), combustion (−15), "
        "and retrogression (±5) per classical Vedic principles. Range: 0-100.",
        footnote_style))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "<b>Remedy Classification:</b> "
        "✅ <b>Strengthen</b> — Functional benefic that is weak; "
        "strengthen through mantras, charity, and positive karma. "
        "⚖️ <b>Balance</b> — Planet is neutral or mixed; "
        "maintain awareness and balance through mindful actions. "
        "⚠️ <b>Pacify</b> — Functional malefic or strong negative influence; "
        "pacify through specific rituals, fasting, and charitable acts.",
        footnote_style))

    # ── Vedic Remedies Reference ─────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Vedic Remedies — Quick Reference", section_style))
    story.append(Paragraph("by AstroShuklz", brand_style))
    story.append(Spacer(1, 3*mm))

    PLANET_REMEDIES = {
        "Sun": ("Ruby (Manikya)", "Surya Namaskar, Aditya Hridayam",
                "Sunday", "Wheat, jaggery, copper to father figures",
                "Red/dark red clothing on Sundays"),
        "Moon": ("Pearl (Moti)", "Chandra mantra, Durga Chalisa",
                 "Monday", "White rice, milk, silver to mother figures",
                 "White clothing on Mondays"),
        "Mars": ("Red Coral (Moonga)", "Hanuman Chalisa, Mangal mantra",
                 "Tuesday", "Red lentils, jaggery to siblings/soldiers",
                 "Red clothing on Tuesdays"),
        "Mercury": ("Emerald (Panna)", "Vishnu Sahasranama, Budh mantra",
                    "Wednesday", "Green moong dal, books to students",
                    "Green clothing on Wednesdays"),
        "Jupiter": ("Yellow Sapphire (Pukhraj)", "Guru mantra, Brihaspati Stotram",
                    "Thursday", "Yellow items, turmeric, bananas to Brahmins/teachers",
                    "Yellow clothing on Thursdays"),
        "Venus": ("Diamond (Heera) / White Sapphire", "Shukra mantra, Lakshmi Stotram",
                  "Friday", "White items, rice, silk to women",
                  "White/cream clothing on Fridays"),
        "Saturn": ("Blue Sapphire (Neelam) — with caution", "Shani mantra, Hanuman Chalisa",
                   "Saturday", "Black sesame, mustard oil, iron to labourers",
                   "Black/dark blue clothing on Saturdays"),
        "Rahu": ("Hessonite (Gomed)", "Rahu mantra, Durga Saptashati",
                 "Saturday", "Black items, coconut to sweepers/outcasts",
                 "Avoid intoxicants, practice honesty"),
        "Ketu": ("Cat's Eye (Lehsunia)", "Ketu mantra, Ganesh Atharvashirsha",
                 "Tuesday/Saturday", "Multi-coloured blanket to sages/ascetics",
                 "Spiritual practice, meditation, detachment"),
    }

    remedy_header_style = ParagraphStyle('RemedyHead', parent=note_style,
        fontName='Helvetica-Bold', fontSize=9.5, textColor=MAROON,
        spaceBefore=3*mm, spaceAfter=1*mm)

    story.append(Paragraph(
        '<i>Note: Gemstones should only be worn after consulting a qualified '
        'Jyotish practitioner. Mantras, charity, and karma correction are the '
        'safest and most universally recommended remedies.</i>',
        footnote_style))
    story.append(Spacer(1, 2*mm))

    # Tiered approach
    story.append(Paragraph("Remedy Hierarchy (Highest to Material):", remedy_header_style))
    tier_style = ParagraphStyle('TierStyle', parent=note_style, fontSize=8.5, leading=12)
    story.append(Paragraph(
        "🧘 <b>Highest:</b> Mantra/Japa, Charity (Dana), Karma correction (behaviour change)<br/>"
        "🔮 <b>Medium:</b> Fasting (Vrat), Pooja/Rituals<br/>"
        "💎 <b>Material:</b> Gemstones (only with qualified guidance)",
        tier_style))
    story.append(Spacer(1, 2*mm))

    # Per-planet remedies based on their classification
    for pname in planet_order:
        sinfo = strength_data[pname]
        remedy_class = sinfo.get('remedy', 'Balance')
        icon = REMEDY_ICONS.get(remedy_class, '')
        gem, mantra, day, charity, tip = PLANET_REMEDIES[pname]

        story.append(Paragraph(
            f"{icon} <b>{pname}</b> — {sinfo['overall']} ({sinfo['score']}/100) — {remedy_class}",
            remedy_header_style))

        if remedy_class == "Strengthen":
            story.append(Paragraph(
                f"<b>Mantra:</b> {mantra} | <b>Day:</b> {day}<br/>"
                f"<b>Charity:</b> {charity}<br/>"
                f"<b>Gemstone:</b> {gem} (consult astrologer first)<br/>"
                f"<b>Tip:</b> {tip}",
                tier_style))
        elif remedy_class == "Pacify":
            story.append(Paragraph(
                f"<b>Mantra:</b> {mantra} | <b>Fast:</b> {day}<br/>"
                f"<b>Charity:</b> {charity}<br/>"
                f"<b>Caution:</b> Do NOT wear {gem} — pacify, don't strengthen<br/>"
                f"<b>Tip:</b> {tip}",
                tier_style))
        else:  # Balance
            story.append(Paragraph(
                f"<b>Mantra:</b> {mantra} | <b>Day:</b> {day}<br/>"
                f"<b>Charity:</b> {charity}<br/>"
                f"<b>Tip:</b> {tip}",
                tier_style))

    # ── Karma Remedy Page ────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Karma Remedy Prescription", section_style))
    story.append(Paragraph("by AstroShuklz", brand_style))
    story.append(Spacer(1, 3*mm))

    KARMA_REMEDIES = {
        "Sun": {
            "icon": "☀️", "principle": "Take responsibility and act with integrity — stop seeking validation.",
            "weak": "Your sense of self and authority needs strengthening. Practice leadership in small ways — take charge of situations, speak up for yourself, and build confidence through action, not approval from others.",
            "strong": "Your strong Sun gives natural authority. Channel it wisely — avoid ego clashes, respect others' autonomy, and lead by example rather than force.",
            "moderate": "Your Sun is balanced. Maintain integrity in all dealings, honour your father/father figures, and take ownership of your life decisions.",
        },
        "Moon": {
            "icon": "🌙", "principle": "Stabilize your mind — build emotional security from within.",
            "weak": "Emotional turbulence may affect your decisions. Practice daily meditation, spend time near water, nurture your relationship with your mother, and create a stable home environment.",
            "strong": "Your emotional depth is a gift. Avoid mood-driven decisions, practice detachment when needed, and use your empathy to help others without absorbing their pain.",
            "moderate": "Maintain emotional balance through routine, rest, and meaningful connections. Trust your intuition but verify with logic.",
        },
        "Mars": {
            "icon": "♂️", "principle": "Control anger — channel energy into disciplined action.",
            "weak": "You may lack assertiveness or physical vitality. Take up regular exercise, learn to say no, practice courage in daily situations, and avoid suppressing justified anger.",
            "strong": "Your Mars gives tremendous drive. Avoid aggression, impulsive decisions, and domination. Channel energy into sports, fitness, or constructive competition.",
            "moderate": "Balance assertion with patience. Stand up for what's right but pick your battles wisely. Regular physical activity is essential.",
        },
        "Mercury": {
            "icon": "☿", "principle": "Communicate clearly — avoid overthinking and clever manipulation.",
            "weak": "Communication and analytical skills need attention. Read more, write regularly, learn a new skill, and practice expressing your thoughts clearly and honestly.",
            "strong": "Your sharp intellect is an asset. Avoid using it for manipulation or overthinking. Be honest in business dealings and honour your commitments.",
            "moderate": "Keep learning and communicating. Avoid gossip, practice active listening, and use your intelligence for the benefit of others.",
        },
        "Jupiter": {
            "icon": "♃", "principle": "Live ethically — apply wisdom, don't just preach it.",
            "weak": "Seek knowledge and wisdom actively. Study sacred texts, find a mentor/guru, teach what you know to others, and practice generosity without expectation.",
            "strong": "Your Jupiter blesses you with wisdom. Avoid self-righteousness, stay humble, share your knowledge freely, and support education for the underprivileged.",
            "moderate": "Continue your spiritual and intellectual growth. Respect teachers and elders, be charitable, and maintain ethical standards in all areas of life.",
        },
        "Venus": {
            "icon": "♀️", "principle": "Value relationships — balance pleasure with responsibility.",
            "weak": "Relationships and comfort may feel lacking. Practice gratitude for what you have, treat your spouse/partner with extra care, appreciate beauty in nature, and develop artistic interests.",
            "strong": "Your Venus gives charm and abundance. Avoid excess in luxury, maintain fidelity, don't take relationships for granted, and share your abundance with others.",
            "moderate": "Nurture your relationships with attention and care. Balance material enjoyment with spiritual values. Support women's causes.",
        },
        "Saturn": {
            "icon": "♄", "principle": "Be consistent — do your duty patiently without complaint.",
            "weak": "You may face delays and obstacles. Embrace hard work, be patient with results, serve the elderly and underprivileged, and never take shortcuts in your duties.",
            "strong": "Your Saturn gives discipline and endurance. Avoid being overly rigid or harsh on yourself/others. Practice compassion alongside duty.",
            "moderate": "Stay committed to your responsibilities. Treat workers and servants with respect, maintain punctuality, and accept life's delays as lessons in patience.",
        },
        "Rahu": {
            "icon": "☊", "principle": "Control desires — avoid shortcuts and stay grounded in reality.",
            "weak": "Confusion and misdirection may trouble you. Stay away from intoxicants, avoid get-rich-quick schemes, practice honesty, and build genuine rather than superficial connections.",
            "strong": "Your Rahu gives worldly ambition. Avoid obsessive pursuit of material goals, practice contentment, be transparent in all dealings, and don't exploit others for gain.",
            "moderate": "Keep your ambitions grounded in ethics. Avoid deception even when tempted, stay connected to your roots, and practice digital/media detox regularly.",
        },
        "Ketu": {
            "icon": "☋", "principle": "Stay focused — balance spirituality with practical life.",
            "weak": "You may feel directionless or detached. Ground yourself through routine, maintain family connections, complete what you start, and balance spiritual seeking with worldly duties.",
            "strong": "Your Ketu gives deep spiritual insight. Avoid excessive withdrawal from the world, stay connected to loved ones, and use your intuition to guide rather than isolate.",
            "moderate": "Balance inner reflection with outer engagement. Practice meditation but remain active in your responsibilities. Trust your instincts.",
        },
    }

    karma_intro = ParagraphStyle('KarmaIntro', parent=note_style,
        fontName='Helvetica-Oblique', fontSize=9.5,
        textColor=colors.HexColor("#2E4057"),
        borderColor=colors.HexColor("#8B0000"), borderWidth=1,
        borderPadding=6, backColor=colors.HexColor("#FFF8F0"),
        spaceBefore=2*mm, spaceAfter=4*mm)

    story.append(Paragraph(
        '<i>Karma correction is the highest and most powerful form of remedy in Vedic '
        'astrology. While mantras and rituals address the symptoms, changing your '
        'behaviour and actions addresses the root cause. Your personalised Karma '
        'Prescription below is based on each planet\'s strength and role in your chart.</i>',
        karma_intro))

    karma_head_style = ParagraphStyle('KarmaHead', parent=note_style,
        fontName='Helvetica-Bold', fontSize=10, textColor=MAROON,
        spaceBefore=3*mm, spaceAfter=0.5*mm)
    karma_principle = ParagraphStyle('KarmaPrinciple', parent=note_style,
        fontName='Helvetica-Oblique', fontSize=8.5,
        textColor=colors.HexColor("#555"), spaceAfter=0.5*mm)
    karma_body = ParagraphStyle('KarmaBody', parent=note_style,
        fontSize=9, leading=13, spaceAfter=1*mm)

    for pname in planet_order:
        sinfo = strength_data[pname]
        kr = KARMA_REMEDIES[pname]
        overall = sinfo['overall']
        score = sinfo['score']
        icon = kr['icon']

        # Pick advice based on strength
        if overall == "Weak":
            advice = kr['weak']
        elif overall == "Strong":
            advice = kr['strong']
        else:
            advice = kr['moderate']

        story.append(Paragraph(
            f"{icon} <b>{pname}</b> — {overall} ({score}/100)",
            karma_head_style))
        story.append(Paragraph(f"<i>{kr['principle']}</i>", karma_principle))
        story.append(Paragraph(advice, karma_body))

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(
        '<i>"Your karma is your greatest remedy. Change your actions, and the planets '
        'will follow." — Classical Vedic Wisdom</i>',
        ParagraphStyle('KarmaQuote', parent=karma_intro,
            alignment=TA_CENTER, fontSize=9)))

    # ── Navamsha (D-9) Table Page ─────────────────────────────
    navamsha = chart.get('navamsha')
    if navamsha:
        story.append(PageBreak())
        story.append(Paragraph("Navamsha (D-9) — Divisional Chart", section_style))
        story.append(Paragraph("by AstroShuklz", brand_style))

        nav_asc = navamsha['nav_asc_sign_idx']
        nav_planets = navamsha['navamsha_planets']
        nav_house_planets = navamsha['nav_house_planets']

        nav_header = [
            Paragraph('<b>#</b>', cell_center_bold),
            Paragraph('<b>House</b>', cell_center_bold),
            Paragraph('<b>Bhav</b>', cell_center_bold),
            Paragraph('<b>Rashi (D-9)</b>', cell_center_bold),
            Paragraph('<b>Zodiac</b>', cell_center_bold),
            Paragraph('<b>Planet(s)</b>', cell_center_bold),
            Paragraph('<b>D-1 Sign</b>', cell_center_bold),
            Paragraph('<b>Varg</b>', cell_center_bold),
        ]
        nav_data = [nav_header]

        VARG_GREEN = colors.HexColor("#E8F5E9")
        varg_rows = []

        for rank in range(1, 13):
            sign_idx = (nav_asc + rank - 1) % 12
            house_num = rank
            bhav = BHAV_NAMES.get(house_num, "")
            zodiac = SIGNS_EN[sign_idx]
            rashi = SIGNS_HI_FULL[sign_idx]

            plist = nav_house_planets.get(rank, [])
            if plist:
                planet_str = ", ".join(plist)
                d1_parts = []
                varg_parts = []
                has_varg = False
                for pname in plist:
                    ndata = nav_planets[pname]
                    d1_parts.append(ndata['natal_sign_en'])
                    if ndata['is_vargottama']:
                        varg_parts.append("\u2726")
                        has_varg = True
                    else:
                        varg_parts.append("")
                d1_str = ", ".join(d1_parts)
                varg_str = " ".join(varg_parts).strip()
                if has_varg:
                    varg_rows.append(rank)
            else:
                planet_str = "-"
                d1_str = "-"
                varg_str = ""

            row = [
                Paragraph(str(rank), cell_center),
                Paragraph(str(house_num), cell_center_bold),
                Paragraph(bhav, cell_center),
                Paragraph(rashi, cell_center),
                Paragraph(zodiac, cell_center),
                Paragraph(planet_str, cell_center),
                Paragraph(d1_str, cell_center),
                Paragraph(varg_str, cell_center),
            ]
            nav_data.append(row)

        nav_col_w = [24, 36, 46, 70, 70, 90, 90, 36]
        nav_table = Table(nav_data, colWidths=nav_col_w, repeatRows=1)

        nav_style_rules = [
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0, 0), (-1, 0), 8.5),
            ('FONTSIZE',   (0, 1), (-1, -1), 8.5),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F5E6C8")),
            ('TEXTCOLOR',  (0, 0), (-1, 0), MAROON),
            ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID',       (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TOPPADDING',  (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]

        # Highlight Row 1 (Nav Lagna) with golden background
        nav_style_rules.append(('BACKGROUND', (0, 1), (-1, 1), GOLD_BG))
        nav_style_rules.append(('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'))

        # Highlight Vargottama rows in light green
        for vr in varg_rows:
            nav_style_rules.append(('BACKGROUND', (0, vr), (-1, vr), VARG_GREEN))

        nav_table.setStyle(TableStyle(nav_style_rules))
        story.append(nav_table)

        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(
            '<b>Navamsha (D-9)</b> is the most important divisional chart in Vedic astrology. '
            'It reveals your inner nature, soul purpose, and marriage destiny. '
            '<b>Vargottama</b> (\u2726) planets occupy the same sign in both D-1 and D-9, '
            'indicating exceptional strength and confirmed significations.',
            footnote_style))

        # ── Navamsha Reading Page ─────────────────────────────
        story.append(PageBreak())
        story.append(Paragraph("Navamsha Reading — Inner Nature &amp; Marriage", section_style))
        story.append(Paragraph("by AstroShuklz", brand_style))
        story.append(Spacer(1, 3 * mm))

        nav_reading_head = ParagraphStyle('NavReadHead', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=10, textColor=MAROON,
            spaceBefore=5 * mm, spaceAfter=2 * mm)
        nav_reading_body = ParagraphStyle('NavReadBody', parent=styles['Normal'],
            fontName='Helvetica', fontSize=9.5, leading=14,
            textColor=colors.HexColor("#333333"), spaceAfter=3 * mm)

        nav_readings = generate_navamsha_reading(chart, strength_data, lang="en")
        for heading, body in nav_readings:
            if heading.startswith("TABLE:"):
                # Enhanced Dignity Changes table
                table_title = heading[6:]
                story.append(Paragraph(table_title, nav_reading_head))
                story.append(Spacer(1, 2*mm))
                dc_header = ['Planet', 'D-1', 'D-9', '', 'Trend', 'Meaning']
                dc_data = [dc_header]
                for (p_label, d1_label, d9_label, arrow, trend, meaning) in body:
                    dc_data.append([p_label, d1_label, d9_label, arrow, trend, meaning])
                dc_widths = [55, 65, 55, 15, 60, 220]
                dc_table = Table(dc_data, colWidths=dc_widths)
                dc_style_rules = [
                    ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE',    (0,0), (-1,0), 8),
                    ('FONTSIZE',    (0,1), (-1,-1), 8.5),
                    ('FONTNAME',    (0,1), (-1,-1), 'Helvetica'),
                    ('BACKGROUND',  (0,0), (-1,0), HEADER_BG),
                    ('TEXTCOLOR',   (0,0), (-1,0), HEADER_FG),
                    ('ALIGN',       (0,0), (4,-1), 'CENTER'),
                    ('ALIGN',       (5,0), (5,-1), 'LEFT'),
                    ('GRID',        (0,0), (-1,-1), 0.5, colors.white),
                    ('TOPPADDING',  (0,0), (-1,-1), 4),
                    ('BOTTOMPADDING',(0,0), (-1,-1), 4),
                    ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
                ]
                # Color-code trend arrows
                for i, (p_label, d1_label, d9_label, arrow, trend, meaning) in enumerate(body, 1):
                    if arrow == "↑":
                        dc_style_rules.append(('TEXTCOLOR', (3,i), (4,i), colors.HexColor("#2E7D32")))
                    elif arrow == "↓":
                        dc_style_rules.append(('TEXTCOLOR', (3,i), (4,i), colors.HexColor("#C62828")))
                    else:
                        dc_style_rules.append(('TEXTCOLOR', (3,i), (4,i), colors.HexColor("#1565C0")))
                dc_table.setStyle(TableStyle(dc_style_rules))
                story.append(dc_table)
            else:
                story.append(Paragraph(heading, nav_reading_head))
                # Handle newlines in body text
                for para in body.split("\n\n"):
                    para = para.strip()
                    if para:
                        story.append(Paragraph(para.replace("\n", "<br/>"), nav_reading_body))

    # ── Sade Sati Page ───────────────────────────────────────────
    sade_sati = chart.get('sade_sati', [])
    if sade_sati:
        story.append(PageBreak())
        story.append(Paragraph("Sade Sati — Saturn&#39;s 7.5-Year Transit", section_style))
        story.append(Paragraph("by AstroShuklz", brand_style))
        story.append(Spacer(1, 3 * mm))

        moon_sign_en = chart['moon_rashi']
        ss_intro_style = ParagraphStyle('SSIntro', parent=styles['Normal'],
            fontName='Helvetica', fontSize=9.5, leading=14,
            textColor=colors.HexColor("#333333"), spaceAfter=4 * mm)
        ss_body_style = ParagraphStyle('SSBody', parent=styles['Normal'],
            fontName='Helvetica', fontSize=9, leading=13,
            textColor=colors.HexColor("#333333"), spaceAfter=2 * mm)
        ss_effect_style = ParagraphStyle('SSEffect', parent=styles['Normal'],
            fontName='Helvetica', fontSize=8.5, leading=12,
            textColor=colors.HexColor("#444444"), leftIndent=10,
            spaceAfter=1 * mm)

        # Section 1: What is Sade Sati? (with Saturn strength context)
        story.append(Paragraph("What is Sade Sati?", section_style))

        # Get Saturn strength for personalized context
        saturn_score = 0
        saturn_overall = "Moderate"
        if strength_data and 'Saturn' in strength_data:
            saturn_score = strength_data['Saturn'].get('score', 0)
            saturn_overall = strength_data['Saturn'].get('overall', 'Moderate')

        if saturn_score >= 70:
            saturn_context = (
                f"In your chart, <b>Saturn is strong ({saturn_score}/100)</b> — "
                f"Sade Sati will bring growth through discipline rather than hardship. "
                f"A strong Saturn means you handle Saturn's lessons with resilience and maturity.")
        elif saturn_score >= 40:
            saturn_context = (
                f"In your chart, <b>Saturn is moderately placed ({saturn_score}/100)</b> — "
                f"Sade Sati will bring a mix of challenges and growth. Discipline and patience "
                f"will be your greatest allies during these periods.")
        else:
            saturn_context = (
                f"In your chart, <b>Saturn is weak ({saturn_score}/100)</b> — "
                f"Sade Sati periods may feel more intense. Extra attention to health, finances, "
                f"and relationships is advised. The remedies below are especially important for you.")

        story.append(Paragraph(
            f"Sade Sati occurs when Saturn transits through the 12th, 1st, and 2nd houses "
            f"from your Moon sign (<b>{moon_sign_en}</b>). Each cycle lasts approximately "
            f"7.5 years and occurs 2-3 times in a lifetime. It brings karmic lessons, "
            f"discipline, and ultimately spiritual growth.",
            ss_intro_style))
        story.append(Paragraph(saturn_context, ss_intro_style))

        # Section 2: Your Sade Sati Cycles (table)
        story.append(Paragraph("Your Sade Sati Cycles", section_style))

        # Phase display: icon, intensity label, intensity color
        PHASE_DISPLAY = {
            'Rising':  ('\u23f3 Rising',  'Medium',  '#FF8F00'),
            'Peak':    ('\u26a0 Peak',    'High',    '#C62828'),
            'Setting': ('\u263c Setting', 'Moderate', '#2E7D32'),
        }

        ss_header = ['Cycle', 'Phase', 'Intensity', 'Period', 'Duration', 'Status']
        ss_data = [ss_header]
        ss_row_meta = []
        PAST_BG = colors.HexColor("#FCE4E4")
        FUTURE_BG = colors.HexColor("#FFF9E6")
        CURRENT_BG = colors.HexColor("#E8F5E9")

        for period in sade_sati:
            for phase_name, phase_start in period['phases']:
                phase_idx = [p[0] for p in period['phases']].index(phase_name)
                if phase_idx + 1 < len(period['phases']):
                    phase_end = period['phases'][phase_idx + 1][1]
                else:
                    phase_end = period['end_date']

                start_str = phase_start.strftime('%b %Y')
                end_str = phase_end.strftime('%b %Y') if phase_end else "Ongoing"

                if phase_end:
                    dur_years = (phase_end - phase_start).days / 365.25
                    dur_str = f"{dur_years:.1f}y"
                else:
                    dur_str = "\u2014"

                is_this_phase_current = (period['is_current'] and
                                         period['phase'] == phase_name)
                if is_this_phase_current:
                    status = "Current"
                elif phase_end and phase_end < today:
                    status = "Past"
                else:
                    status = "Future"

                cycle_label = f"{period['cycle']}" if period['phases'][0][0] == phase_name else ""
                phase_disp, intensity, _ = PHASE_DISPLAY.get(phase_name, (phase_name, '', '#333'))

                ss_data.append([cycle_label, phase_disp, intensity,
                               f"{start_str} \u2014 {end_str}", dur_str, status])
                ss_row_meta.append((status, phase_name))

        ss_col_widths = [35, 65, 55, 140, 40, 50]
        ss_table = Table(ss_data, colWidths=ss_col_widths)
        ss_style_rules = [
            ('FONTNAME',    (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',    (0, 0), (-1, 0), 8),
            ('FONTSIZE',    (0, 1), (-1, -1), 8),
            ('FONTNAME',    (0, 1), (-1, -1), 'Helvetica'),
            ('BACKGROUND',  (0, 0), (-1, 0), HEADER_BG),
            ('TEXTCOLOR',   (0, 0), (-1, 0), HEADER_FG),
            ('ALIGN',       (0, 0), (-1, -1), 'CENTER'),
            ('GRID',        (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ('TOPPADDING',  (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ]
        for row_idx, (meta_status, meta_phase) in enumerate(ss_row_meta, 1):
            if meta_status == "Current":
                ss_style_rules.append(('BACKGROUND', (0, row_idx), (-1, row_idx), CURRENT_BG))
                ss_style_rules.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))
                ss_data[row_idx][5] = "Current \u25c4"
            elif meta_status == "Past":
                ss_style_rules.append(('BACKGROUND', (0, row_idx), (-1, row_idx), PAST_BG))
            elif meta_status == "Future":
                ss_style_rules.append(('BACKGROUND', (0, row_idx), (-1, row_idx), FUTURE_BG))
            # Color intensity column
            _, _, int_color = PHASE_DISPLAY.get(meta_phase, ('', '', '#333'))
            ss_style_rules.append(('TEXTCOLOR', (2, row_idx), (2, row_idx),
                                   colors.HexColor(int_color)))
            ss_style_rules.append(('FONTNAME', (2, row_idx), (2, row_idx), 'Helvetica-Bold'))

        ss_table.setStyle(TableStyle(ss_style_rules))
        story.append(ss_table)
        story.append(Spacer(1, 4 * mm))

        # Section 3: Current Status
        story.append(Paragraph("Current Status", section_style))
        current_period = None
        for p in sade_sati:
            if p['is_current']:
                current_period = p
                break

        if current_period:
            phase = current_period['phase']
            phase_info = SADE_SATI_PHASES_EN.get(phase, {})
            story.append(Paragraph(
                f"<b>You are currently in Sade Sati — {phase_info.get('title', phase)} Phase</b>",
                ss_body_style))
            story.append(Paragraph(phase_info.get('description', ''), ss_body_style))
            story.append(Paragraph("<b>Key Effects:</b>", ss_body_style))
            for effect in phase_info.get('effects', []):
                story.append(Paragraph(f"\u2022 {effect}", ss_effect_style))
        else:
            # Find next or most recent
            future = [p for p in sade_sati if p['start_date'] > today]
            past = [p for p in sade_sati if p['end_date'] and p['end_date'] <= today]
            if future:
                nxt = future[0]
                story.append(Paragraph(
                    f"You are <b>not</b> currently in Sade Sati. "
                    f"Your next Sade Sati begins approximately <b>{nxt['start_date'].strftime('%B %Y')}</b>.",
                    ss_body_style))
            elif past:
                last = past[-1]
                story.append(Paragraph(
                    f"You are <b>not</b> currently in Sade Sati. "
                    f"Your most recent Sade Sati ended approximately <b>{last['end_date'].strftime('%B %Y')}</b>.",
                    ss_body_style))
        story.append(Spacer(1, 3 * mm))

        # Section 4: Remedies
        story.append(Paragraph("Sade Sati Remedies", section_style))

        remedy_head_style = ParagraphStyle('SSRemedyHead', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=9, textColor=MAROON,
            spaceBefore=3 * mm, spaceAfter=1 * mm)

        story.append(Paragraph("Spiritual Remedies", remedy_head_style))
        for r in SADE_SATI_REMEDIES_EN['spiritual']:
            story.append(Paragraph(f"\u2022 {r}", ss_effect_style))

        story.append(Paragraph("Karma Correction", remedy_head_style))
        for r in SADE_SATI_REMEDIES_EN['karma']:
            story.append(Paragraph(f"\u2022 {r}", ss_effect_style))

        story.append(Paragraph("Practical Advice", remedy_head_style))
        for r in SADE_SATI_REMEDIES_EN['practical']:
            story.append(Paragraph(f"\u2022 {r}", ss_effect_style))

    # ── Dasha tables ───────────────────────────────────────────
    story.append(PageBreak())

    # Mahadasha
    story.append(Paragraph("Vimshottari Dasha — Mahadasha", section_style))

    m_header = ['Lord', 'Start', 'End', 'Years', '']
    m_data = [m_header]
    current_maha = None
    for lord, start, end, yrs in chart['dashas']:
        is_now = start <= today < end
        if is_now:
            current_maha = lord
        marker = "◄ NOW" if is_now else ""
        m_data.append([lord, start.strftime('%b %Y'), end.strftime('%b %Y'),
                       f"{yrs:.1f}", marker])

    mtable = Table(m_data, colWidths=[70, 80, 80, 50, 50])
    m_style = [
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
        ('BACKGROUND', (0,0), (-1,0), HEADER_BG),
        ('TEXTCOLOR',  (0,0), (-1,0), HEADER_FG),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ROW_ALT]),
        ('TOPPADDING',  (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',(0,0), (-1,-1), 3),
    ]
    for i, (lord, start, end, yrs) in enumerate(chart['dashas'], 1):
        if start <= today < end:
            m_style.append(('BACKGROUND', (0, i), (-1, i), ROW_NOW))
            m_style.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
    mtable.setStyle(TableStyle(m_style))
    story.append(mtable)

    if current_maha and current_maha in chart.get('antardasha', {}):
        story.append(Paragraph(
            f"Vimshottari Dasha — Antardasha (within {current_maha} Mahadasha)",
            section_style))

        a_header = ['Lord', 'Start', 'End', 'Duration', '']
        a_data = [a_header]
        current_antar = None
        for ad_lord, ad_start, ad_end, ad_yrs in chart['antardasha'][current_maha]:
            is_now = ad_start <= today < ad_end
            if is_now:
                current_antar = ad_lord
            marker = "◄ NOW" if is_now else ""
            months = ad_yrs * 12
            dur_str = f"{ad_yrs:.1f}y" if months >= 12 else f"{months:.1f}m"
            a_data.append([ad_lord, ad_start.strftime('%d %b %Y'),
                           ad_end.strftime('%d %b %Y'), dur_str, marker])

        atable = Table(a_data, colWidths=[70, 90, 90, 55, 50])
        a_style = [
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 8),
            ('BACKGROUND', (0,0), (-1,0), HEADER_BG),
            ('TEXTCOLOR',  (0,0), (-1,0), HEADER_FG),
            ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
            ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ROW_ALT]),
            ('TOPPADDING',  (0,0), (-1,-1), 3),
            ('BOTTOMPADDING',(0,0), (-1,-1), 3),
        ]
        for i, (ad_lord, ad_start, ad_end, ad_yrs) in enumerate(
                chart['antardasha'][current_maha], 1):
            if ad_start <= today < ad_end:
                a_style.append(('BACKGROUND', (0, i), (-1, i), ROW_NOW))
                a_style.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
        atable.setStyle(TableStyle(a_style))
        story.append(atable)

        # Pratyantar
        if current_antar:
            key = (current_maha, current_antar)
            if key in chart.get('pratyantar', {}):
                story.append(Paragraph(
                    f"Vimshottari Dasha — Pratyantar "
                    f"(within {current_maha}–{current_antar})",
                    section_style))
                pd_header = ['Lord', 'Start', 'End', 'Duration', '']
                pd_data = [pd_header]
                for pd_lord, pd_start, pd_end, pd_yrs in chart['pratyantar'][key]:
                    is_now = pd_start <= today < pd_end
                    marker = "◄ NOW" if is_now else ""
                    days = pd_yrs * 365.25
                    dur_str = f"{pd_yrs*12:.1f}m" if days >= 30 else f"{days:.0f}d"
                    pd_data.append([pd_lord, pd_start.strftime('%d %b %Y'),
                                    pd_end.strftime('%d %b %Y'), dur_str, marker])
                pdtable = Table(pd_data, colWidths=[70, 90, 90, 55, 50])
                pd_style = [
                    ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE',   (0,0), (-1,-1), 8),
                    ('BACKGROUND', (0,0), (-1,0), HEADER_BG),
                    ('TEXTCOLOR',  (0,0), (-1,0), HEADER_FG),
                    ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
                    ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ROW_ALT]),
                    ('TOPPADDING',  (0,0), (-1,-1), 3),
                    ('BOTTOMPADDING',(0,0), (-1,-1), 3),
                ]
                for i, (pd_lord, pd_start, pd_end, pd_yrs) in enumerate(
                        chart['pratyantar'][key], 1):
                    if pd_start <= today < pd_end:
                        pd_style.append(('BACKGROUND', (0, i), (-1, i), ROW_NOW))
                        pd_style.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
                pdtable.setStyle(TableStyle(pd_style))
                story.append(pdtable)

    # ── Page 3: Prediction / Dasha Reading ──────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Dasha Reading &amp; Predictions", title_style))
    story.append(Paragraph("by AstroShuklz", brand_style))
    story.append(Spacer(1, 3*mm))

    reading_style = ParagraphStyle('KReading2', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9.5, textColor=colors.HexColor("#333"),
        alignment=TA_LEFT, leading=14, spaceBefore=2*mm, spaceAfter=2*mm)
    reading_bold = ParagraphStyle('KReadBold2', parent=reading_style,
        fontName='Helvetica-Bold', fontSize=10, textColor=MAROON,
        spaceBefore=4*mm, spaceAfter=1*mm)
    disclaimer_style = ParagraphStyle('KDisclaimer2', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=7.5,
        textColor=colors.HexColor("#999"), alignment=TA_CENTER,
        spaceBefore=8*mm, spaceAfter=2*mm)

    reading = _dasha_reading(chart, today)
    for block in reading:
        if block.startswith("##"):
            story.append(Paragraph(block[2:].strip(), reading_bold))
        else:
            story.append(Paragraph(block, reading_style))

    # ══════════════════════════════════════════════════════════════
    # Build English PDF first, then merge with Hindi PDF (weasyprint)
    # ══════════════════════════════════════════════════════════════

    # ── English disclaimer ──────────────────────────────────────
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(
        "Disclaimer: This reading is generated based on classical Vimshottari "
        "Dasha interpretations and is for educational/entertainment purposes only. "
        "For personalised guidance, consult a qualified Jyotish practitioner.",
        disclaimer_style))

    story.append(Spacer(1, 8*mm))
    footer_style = ParagraphStyle('KFooter2', parent=styles['Normal'],
        fontName='Helvetica', fontSize=7, textColor=colors.HexColor("#AAAAAA"),
        alignment=TA_CENTER)
    story.append(Paragraph("Lahiri Ayanamsha  ·  Swiss Ephemeris  ·  "
                           "Generated by AstroShuklz", footer_style))

    doc.build(story)

    # ══════════════════════════════════════════════════════════════
    # HINDI PAGES via WeasyPrint (proper Devanagari conjunct rendering)
    # ══════════════════════════════════════════════════════════════
    hindi_pdf_buf = _generate_hindi_pdf(chart, today, strength_data)

    # Merge English + Hindi PDFs
    if hindi_pdf_buf:
        from PyPDF2 import PdfReader, PdfWriter
        writer = PdfWriter()
        pdf_buffer.seek(0)
        eng_reader = PdfReader(pdf_buffer)
        for page in eng_reader.pages:
            writer.add_page(page)
        hi_reader = PdfReader(hindi_pdf_buf)
        for page in hi_reader.pages:
            writer.add_page(page)
        merged = io.BytesIO()
        writer.write(merged)
        merged.seek(0)
        return merged

    pdf_buffer.seek(0)
    return pdf_buffer


# ─── City Coordinates Lookup (CSV-backed) ────────────────────────────────────

import csv

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CITIES_CSV = os.path.join(_SCRIPT_DIR, "cities.csv")


def load_city_db(csv_path=_CITIES_CSV):
    """Load city database from CSV file. Returns dict keyed by lowercase city name."""
    db = {}
    if not os.path.exists(csv_path):
        return db
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            city = row["city"].strip().lower()
            db[city] = (float(row["lat"]), float(row["lon"]), float(row["utc_offset"]))
    return db


def save_city_to_csv(city, lat, lon, utc_offset, csv_path=_CITIES_CSV):
    """Append a new city to the CSV file (auto-learn from geopy lookups)."""
    key = city.strip().lower()
    # Avoid duplicates
    existing = load_city_db(csv_path)
    if key in existing:
        return
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["city", "lat", "lon", "utc_offset"])
        writer.writerow([key, lat, lon, utc_offset])


# Load city DB at module import time
CITY_DB = load_city_db()


# Legacy hardcoded DB kept as inline fallback if CSV is missing
_LEGACY_CITY_DB = {
    # ── India ──────────────────────────────────────────────────────────────
    "agra":             (27.1767,  78.0081,  5.5),
    "ahmedabad":        (23.0225,  72.5714,  5.5),
    "allahabad":        (25.4358,  81.8463,  5.5),
    "amritsar":         (31.6340,  74.8723,  5.5),
    "aurangabad":       (19.8762,  75.3433,  5.5),
    "bangalore":        (12.9716,  77.5946,  5.5),
    "bengaluru":        (12.9716,  77.5946,  5.5),
    "bhopal":           (23.2599,  77.4126,  5.5),
    "bhubaneswar":      (20.2961,  85.8245,  5.5),
    "bombay":           (19.0760,  72.8777,  5.5),
    "calcutta":         (22.5726,  88.3639,  5.5),
    "chandigarh":       (30.7333,  76.7794,  5.5),
    "chennai":          (13.0827,  80.2707,  5.5),
    "coimbatore":       (11.0168,  76.9558,  5.5),
    "delhi":            (28.6139,  77.2090,  5.5),
    "dehradun":         (30.3165,  78.0322,  5.5),
    "faridabad":        (28.4089,  77.3178,  5.5),
    "guwahati":         (26.1445,  91.7362,  5.5),
    "gurgaon":          (28.4595,  77.0266,  5.5),
    "gurugram":         (28.4595,  77.0266,  5.5),
    "hyderabad":        (17.3850,  78.4867,  5.5),
    "indore":           (22.7196,  75.8577,  5.5),
    "jaipur":           (26.9124,  75.7873,  5.5),
    "jalandhar":        (31.3260,  75.5762,  5.5),
    "jammu":            (32.7266,  74.8570,  5.5),
    "jodhpur":          (26.2389,  73.0243,  5.5),
    "kanpur":           (26.4499,  80.3319,  5.5),
    "kochi":            ( 9.9312,  76.2673,  5.5),
    "kolkata":          (22.5726,  88.3639,  5.5),
    "kozhikode":        (11.2588,  75.7804,  5.5),
    "lucknow":          (26.8467,  80.9462,  5.5),
    "ludhiana":         (30.9010,  75.8573,  5.5),
    "madras":           (13.0827,  80.2707,  5.5),
    "madurai":          ( 9.9252,  78.1198,  5.5),
    "mangalore":        (12.9141,  74.8560,  5.5),
    "mumbai":           (19.0760,  72.8777,  5.5),
    "mysore":           (12.2958,  76.6394,  5.5),
    "nagpur":           (21.1458,  79.0882,  5.5),
    "nashik":           (19.9975,  73.7898,  5.5),
    "new delhi":        (28.6139,  77.2090,  5.5),
    "noida":            (28.5355,  77.3910,  5.5),
    "patna":            (25.5941,  85.1376,  5.5),
    "pune":             (18.5204,  73.8567,  5.5),
    "rajkot":           (22.3039,  70.8022,  5.5),
    "ranchi":           (23.3441,  85.3096,  5.5),
    "shimla":           (31.1048,  77.1734,  5.5),
    "srinagar":         (34.0837,  74.7973,  5.5),
    "surat":            (21.1702,  72.8311,  5.5),
    "thane":            (19.2183,  72.9781,  5.5),
    "thiruvananthapuram":(8.5241,  76.9366,  5.5),
    "trivandrum":       ( 8.5241,  76.9366,  5.5),
    "varanasi":         (25.3176,  82.9739,  5.5),
    "vijayawada":       (16.5062,  80.6480,  5.5),
    "visakhapatnam":    (17.6868,  83.2185,  5.5),
    "vizag":            (17.6868,  83.2185,  5.5),
    # ── South Asia ─────────────────────────────────────────────────────────
    "dhaka":            (23.8103,  90.4125,  6.0),
    "chittagong":       (22.3569,  91.7832,  6.0),
    "karachi":          (24.8607,  67.0011,  5.0),
    "lahore":           (31.5204,  74.3587,  5.0),
    "islamabad":        (33.6844,  73.0479,  5.0),
    "colombo":          ( 6.9271,  79.8612,  5.5),
    "kathmandu":        (27.7172,  85.3240,  5.75),
    "kabul":            (34.5553,  69.2075,  4.5),
    # ── Southeast Asia ─────────────────────────────────────────────────────
    "singapore":        ( 1.3521, 103.8198,  8.0),
    "jakarta":          (-6.2088, 106.8456,  7.0),
    "solo":             (-7.5755, 110.8243,  7.0),
    "surakarta":        (-7.5755, 110.8243,  7.0),
    "surabaya":         (-7.2575, 112.7521,  7.0),
    "bandung":          (-6.9175, 107.6191,  7.0),
    "bali":             (-8.3405, 115.0920,  8.0),
    "denpasar":         (-8.6500, 115.2167,  8.0),
    "yogyakarta":       (-7.7956, 110.3695,  7.0),
    "medan":            ( 3.5952,  98.6722,  7.0),
    "kuala lumpur":     ( 3.1390, 101.6869,  8.0),
    "kl":               ( 3.1390, 101.6869,  8.0),
    "penang":           ( 5.4141, 100.3288,  8.0),
    "bangkok":          (13.7563, 100.5018,  7.0),
    "manila":           (14.5995, 120.9842,  8.0),
    "ho chi minh city": (10.8231, 106.6297,  7.0),
    "hanoi":            (21.0285, 105.8542,  7.0),
    "phnom penh":       (11.5564, 104.9282,  7.0),
    "yangon":           (16.8661,  96.1951,  6.5),
    "rangoon":          (16.8661,  96.1951,  6.5),
    "vientiane":        (17.9757, 102.6331,  7.0),
    # ── East Asia ──────────────────────────────────────────────────────────
    "tokyo":            (35.6762, 139.6503,  9.0),
    "osaka":            (34.6937, 135.5023,  9.0),
    "seoul":            (37.5665, 126.9780,  9.0),
    "beijing":          (39.9042, 116.4074,  8.0),
    "shanghai":         (31.2304, 121.4737,  8.0),
    "hong kong":        (22.3193, 114.1694,  8.0),
    "taipei":           (25.0330, 121.5654,  8.0),
    "macau":            (22.1987, 113.5439,  8.0),
    # ── Middle East ────────────────────────────────────────────────────────
    "dubai":            (25.2048,  55.2708,  4.0),
    "abu dhabi":        (24.4539,  54.3773,  4.0),
    "sharjah":          (25.3462,  55.4209,  4.0),
    "doha":             (25.2854,  51.5310,  3.0),
    "riyadh":           (24.6877,  46.7219,  3.0),
    "jeddah":           (21.3891,  39.8579,  3.0),
    "muscat":           (23.5880,  58.3829,  4.0),
    "kuwait city":      (29.3759,  47.9774,  3.0),
    "manama":           (26.2154,  50.5832,  3.0),
    "beirut":           (33.8938,  35.5018,  2.0),
    "tehran":           (35.6892,  51.3890,  3.5),
    "istanbul":         (41.0082,  28.9784,  3.0),
    "ankara":           (39.9334,  32.8597,  3.0),
    "tel aviv":         (32.0853,  34.7818,  2.0),
    # ── Africa ─────────────────────────────────────────────────────────────
    "cairo":            (30.0444,  31.2357,  2.0),
    "nairobi":          (-1.2921,  36.8219,  3.0),
    "lagos":            ( 6.5244,   3.3792,  1.0),
    "johannesburg":     (-26.2041, 28.0473,  2.0),
    "cape town":        (-33.9249, 18.4241,  2.0),
    "addis ababa":      ( 9.0320,  38.7469,  3.0),
    "accra":            ( 5.6037,  -0.1870,  0.0),
    "dar es salaam":    (-6.7924,  39.2083,  3.0),
    "casablanca":       (33.5731,  -7.5898,  1.0),
    "khartoum":         (15.5007,  32.5599,  3.0),
    # ── Europe ─────────────────────────────────────────────────────────────
    "london":           (51.5074,  -0.1278,  0.0),
    "paris":            (48.8566,   2.3522,  1.0),
    "berlin":           (52.5200,  13.4050,  1.0),
    "madrid":           (40.4168,  -3.7038,  1.0),
    "rome":             (41.9028,  12.4964,  1.0),
    "amsterdam":        (52.3676,   4.9041,  1.0),
    "brussels":         (50.8503,   4.3517,  1.0),
    "vienna":           (48.2082,  16.3738,  1.0),
    "zurich":           (47.3769,   8.5417,  1.0),
    "stockholm":        (59.3293,  18.0686,  1.0),
    "oslo":             (59.9139,  10.7522,  1.0),
    "copenhagen":       (55.6761,  12.5683,  1.0),
    "helsinki":         (60.1699,  24.9384,  2.0),
    "warsaw":           (52.2297,  21.0122,  1.0),
    "prague":           (50.0755,  14.4378,  1.0),
    "budapest":         (47.4979,  19.0402,  1.0),
    "bucharest":        (44.4268,  26.1025,  2.0),
    "athens":           (37.9838,  23.7275,  2.0),
    "lisbon":           (38.7223,  -9.1393,  0.0),
    "moscow":           (55.7558,  37.6173,  3.0),
    "st petersburg":    (59.9311,  30.3609,  3.0),
    "kyiv":             (50.4501,  30.5234,  2.0),
    "zagreb":           (45.8150,  15.9819,  1.0),
    # ── Americas ───────────────────────────────────────────────────────────
    "new york":         (40.7128, -74.0060, -5.0),
    "los angeles":      (34.0522,-118.2437, -8.0),
    "chicago":          (41.8781, -87.6298, -6.0),
    "houston":          (29.7604, -95.3698, -6.0),
    "phoenix":          (33.4484,-112.0740, -7.0),
    "philadelphia":     (39.9526, -75.1652, -5.0),
    "san antonio":      (29.4241, -98.4936, -6.0),
    "san diego":        (32.7157,-117.1611, -8.0),
    "san francisco":    (37.7749,-122.4194, -8.0),
    "seattle":          (47.6062,-122.3321, -8.0),
    "miami":            (25.7617, -80.1918, -5.0),
    "dallas":           (32.7767, -96.7970, -6.0),
    "washington":       (38.9072, -77.0369, -5.0),
    "boston":           (42.3601, -71.0589, -5.0),
    "atlanta":          (33.7490, -84.3880, -5.0),
    "toronto":          (43.6510, -79.3470, -5.0),
    "vancouver":        (49.2827,-123.1207, -8.0),
    "montreal":         (45.5017, -73.5673, -5.0),
    "calgary":          (51.0447,-114.0719, -7.0),
    "mexico city":      (19.4326, -99.1332, -6.0),
    "sao paulo":        (-23.5505,-46.6333, -3.0),
    "rio de janeiro":   (-22.9068,-43.1729, -3.0),
    "buenos aires":     (-34.6037,-58.3816, -3.0),
    "bogota":           ( 4.7110, -74.0721, -5.0),
    "lima":             (-12.0464,-77.0428, -5.0),
    "santiago":         (-33.4489,-70.6693, -4.0),
    "caracas":          (10.4806, -66.9036, -4.0),
    # ── Oceania ────────────────────────────────────────────────────────────
    "sydney":           (-33.8688, 151.2093, 10.0),
    "melbourne":        (-37.8136, 144.9631, 10.0),
    "brisbane":         (-27.4698, 153.0251, 10.0),
    "perth":            (-31.9505, 115.8605,  8.0),
    "auckland":         (-36.8509, 174.7645, 12.0),
}

def lookup_city(city_name, birth_year=None, birth_month=None, birth_day=None):
    """
    Look up a city and return (lat, lon, utc_offset).

    Strategy:
    1. Check CSV-backed CITY_DB first (fast, offline).
    2. Try geopy (Nominatim) + timezonefinder for unknown cities.
       If found, auto-save to cities.csv for future lookups.
    3. Fall back to hardcoded _LEGACY_CITY_DB.
    4. Return None if city not found anywhere.
    """
    global CITY_DB
    key = city_name.strip().lower()

    # ── 1. Check CSV-loaded database ─────────────────────────────────────
    result = CITY_DB.get(key)
    if result:
        lat, lon, utc = result
        print(f"  ✓ Found in CSV: lat={lat}, lon={lon}, UTC{utc:+.1f}")
        return result

    # ── 2. Try geopy (online lookup) ─────────────────────────────────────
    try:
        from geopy.geocoders import Nominatim
        from timezonefinder import TimezoneFinder
        import pytz

        geolocator = Nominatim(user_agent="vedic_kundali_v2", timeout=5)
        location   = geolocator.geocode(city_name)

        if location:
            lat, lon = location.latitude, location.longitude
            tf       = TimezoneFinder()
            tz_name  = tf.timezone_at(lng=lon, lat=lat)

            if tz_name:
                tz = pytz.timezone(tz_name)
                if birth_year and birth_month and birth_day:
                    from datetime import datetime as _dt
                    dt = _dt(birth_year, birth_month, birth_day, 12, 0)
                else:
                    from datetime import datetime as _dt
                    dt = _dt.now()
                offset_hours = tz.utcoffset(dt).total_seconds() / 3600
                print(f"  ✓ {location.address[:60]}")
                print(f"    lat={lat:.4f}, lon={lon:.4f}, UTC{offset_hours:+.2f} ({tz_name})")

                # Auto-save to CSV for future lookups
                save_city_to_csv(key, lat, lon, offset_hours)
                CITY_DB[key] = (lat, lon, offset_hours)
                print(f"    ✓ Saved to cities.csv")

                return (lat, lon, offset_hours)

    except ImportError:
        pass
    except Exception:
        pass

    # ── 3. Fallback to hardcoded legacy DB ───────────────────────────────
    result = _LEGACY_CITY_DB.get(key)
    if result:
        lat, lon, utc = result
        print(f"  ✓ Found in legacy DB: lat={lat}, lon={lon}, UTC{utc:+.1f}")
        # Auto-save to CSV so it's available next time from CSV
        save_city_to_csv(key, lat, lon, utc)
        CITY_DB[key] = result
        return result

    return None


# ─── Interactive Input ────────────────────────────────────────────────────────

def get_input(prompt, validator=None, default=None):
    """Prompt user with optional validation and default value."""
    while True:
        display = f"{prompt}"
        if default is not None:
            display += f" [{default}]"
        display += ": "
        val = input(display).strip()
        if val == "" and default is not None:
            return default
        if validator:
            result = validator(val)
            if result is not None:
                return result
            print("  ✗ Invalid input, please try again.")
        else:
            if val:
                return val


def parse_date(s):
    """Accept DD/MM/YYYY or DD-MM-YYYY."""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d %m %Y"):
        try:
            d = datetime.strptime(s.strip(), fmt)
            return (d.year, d.month, d.day)
        except ValueError:
            pass
    return None


def parse_time(s):
    """Accept HH:MM or HH:MM:SS in 24h format."""
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            t = datetime.strptime(s.strip(), fmt)
            return (t.hour, t.minute, t.second)
        except ValueError:
            pass
    return None


def interactive_input():
    """Collect birth details interactively from the user."""
    print("\n" + "─"*50)
    print("  🪐  VEDIC KUNDALI GENERATOR")
    print("─"*50)
    print("  Enter birth details below.")
    print("  Press Enter to accept [default] values.\n")

    name = get_input("  Name")

    date_parts = get_input(
        "  Date of birth (DD/MM/YYYY)",
        validator=parse_date,
        default="27/02/1964"
    )
    year, month, day = date_parts

    time_parts = get_input(
        "  Time of birth (HH:MM, 24-hr)",
        validator=parse_time,
        default="00:58"
    )
    hour, minute, second = time_parts

    place = get_input("  Place of birth (city, country)", default="Kolkata")

    # Look up city — pass birth date so DST is resolved correctly
    coords = lookup_city(place, birth_year=year, birth_month=month, birth_day=day)
    if coords:
        lat, lon, utc_offset = coords
    else:
        print(f"\n  ✗ Could not find '{place}'.")
        print(  "    Tips: try 'Solo, Indonesia' or 'Surakarta, Indonesia'")
        print(  "    Or enter coordinates manually below.\n")
        def parse_float(s):
            try: return float(s)
            except: return None
        lat        = get_input("  Latitude  (e.g. -7.57 for Solo)",  validator=parse_float)
        lon        = get_input("  Longitude (e.g. 110.82 for Solo)", validator=parse_float)
        utc_offset = get_input("  UTC offset (e.g. 7.0 for WIB)",    validator=parse_float, default=5.5)

    return {
        'name':       name,
        'year':       year,  'month':  month,  'day':    day,
        'hour':       hour,  'minute': minute, 'second': second,
        'utc_offset': utc_offset,
        'lat':        lat,   'lon':    lon,
        'place':      place,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    # If arguments passed on command line, use them (for scripting)
    # Otherwise run interactive prompt
    birth_data = interactive_input()

    print("\n  Calculating chart...")
    chart = generate_chart(birth_data)

    # Text output
    print_chart(chart)

    # SVG — save next to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    safe_name  = birth_data['name'].replace(" ", "_").lower()
    svg_path   = os.path.join(script_dir, f"kundali_{safe_name}.svg")
    generate_svg(chart, svg_path)

    # PDF — save next to SVG
    pdf_path = os.path.join(script_dir, f"kundali_{safe_name}.pdf")
    generate_pdf(chart, pdf_path, svg_path=svg_path)

    print(f"\n  ✓ Done!")
    print(f"    SVG chart → {svg_path}")
    print(f"    PDF report → {pdf_path}\n")