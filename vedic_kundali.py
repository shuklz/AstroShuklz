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
               f'\u091c\u0928\u094d\u092e \u0915\u0941\u0923\u094d\u0921\u0932\u0940</text>')
    svg.append(f'<text x="{W//2}" y="48" text-anchor="middle" '
               f'font-size="12" fill="#444">{bd["name"]}</text>')
    svg.append(f'<text x="{W//2}" y="63" text-anchor="middle" '
               f'font-size="10" fill="#777">'
               f'{bd["day"]:02d}/{bd["month"]:02d}/{bd["year"]}  '
               f'{bd["hour"]:02d}:{bd["minute"]:02d}  \u00b7  {bd["place"]}</text>')

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
                       f'\u0932</text>')
        plist = sign_planets[s_idx]
        for i, pname in enumerate(plist):
            pdata = planets[pname]
            abbr  = PLANET_HI.get(pname, pname[:2])
            deg   = int(pdata['deg'])
            retro = "\u1d5b" if pdata['retro'] else ""
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
               f'\u0932\u0917\u094d\u0928: {chart["asc_sign_hi"]} {dms_str(chart["asc_deg"])}  \u00b7  '
               f'\u0930\u093e\u0936\u093f: {chart["moon_rashi_hi"]}  \u00b7  '
               f'\u0928\u0915\u094d\u0937\u0924\u094d\u0930: {chart["nakshatra"]} '
               f'\u092a\u0926 {chart["nak_pada"]} '
               f'({chart["nak_lord"]})</text>')
    svg.append(f'<text x="{W//2}" y="{fy+16}" text-anchor="middle" '
               f'font-size="8" fill="#AAAAAA">'
               f'Lahiri Ayanamsha  \u00b7  Swiss Ephemeris</text>')
    svg.append('</svg>')

    return "\n".join(svg)


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
    "Sun": "\u0938\u0942\u0930\u094d\u092f", "Moon": "\u091a\u0928\u094d\u0926\u094d\u0930",
    "Mars": "\u092e\u0902\u0917\u0932", "Mercury": "\u092c\u0941\u0927",
    "Jupiter": "\u0917\u0941\u0930\u0941", "Venus": "\u0936\u0941\u0915\u094d\u0930",
    "Saturn": "\u0936\u0928\u093f", "Rahu": "\u0930\u093e\u0939\u0941",
    "Ketu": "\u0915\u0947\u0924\u0941",
}

DASHA_READING_HI = {
    "Ketu": {
        "nature": "\u0906\u0927\u094d\u092f\u093e\u0924\u094d\u092e\u093f\u0915, \u0906\u0924\u094d\u092e\u0928\u093f\u0930\u0940\u0915\u094d\u0937\u0923 \u0914\u0930 \u092a\u0930\u093f\u0935\u0930\u094d\u0924\u0928\u0915\u093e\u0930\u0940",
        "themes": "\u0906\u0927\u094d\u092f\u093e\u0924\u094d\u092e\u093f\u0915 \u0935\u093f\u0915\u093e\u0938, \u092d\u094c\u0924\u093f\u0915 \u0907\u091a\u094d\u091b\u093e\u0913\u0902 \u0938\u0947 \u0935\u0948\u0930\u093e\u0917\u094d\u092f, \u092a\u0942\u0930\u094d\u0935 \u091c\u0928\u094d\u092e \u0915\u0930\u094d\u092e \u0938\u092e\u093e\u0927\u093e\u0928 \u0914\u0930 \u0905\u091a\u093e\u0928\u0915 \u092a\u0930\u093f\u0935\u0930\u094d\u0924\u0928",
        "positive": "\u0924\u0940\u0935\u094d\u0930 \u0905\u0902\u0924\u0930\u094d\u091c\u094d\u091e\u093e\u0928, \u0906\u0927\u094d\u092f\u093e\u0924\u094d\u092e\u093f\u0915 \u0909\u092a\u0932\u092c\u094d\u0927\u093f\u092f\u093e\u0901, \u092a\u0941\u0930\u093e\u0928\u0947 \u092a\u094d\u0930\u0924\u093f\u0930\u0942\u092a\u094b\u0902 \u0938\u0947 \u092e\u0941\u0915\u094d\u0924\u093f",
        "challenges": "\u092d\u094d\u0930\u092e, \u0905\u092a\u094d\u0930\u0924\u094d\u092f\u093e\u0936\u093f\u0924 \u0939\u093e\u0928\u093f, \u0938\u094d\u0935\u093e\u0938\u094d\u0925\u094d\u092f \u0938\u092e\u0938\u094d\u092f\u093e\u090f\u0901 \u0914\u0930 \u0905\u0915\u0947\u0932\u0947\u092a\u0928 \u0915\u0940 \u092d\u093e\u0935\u0928\u093e",
        "advice": "\u0906\u0927\u094d\u092f\u093e\u0924\u094d\u092e\u093f\u0915 \u0938\u093e\u0927\u0928\u093e \u0905\u092a\u0928\u093e\u090f\u0901, \u092c\u0921\u093c\u0940 \u092d\u094c\u0924\u093f\u0915 \u092a\u094d\u0930\u0924\u093f\u092c\u0926\u094d\u0927\u0924\u093e\u0913\u0902 \u0938\u0947 \u092c\u091a\u0947\u0902, \u0926\u093f\u0928\u091a\u0930\u094d\u092f\u093e \u0938\u0947 \u0938\u094d\u0925\u093f\u0930 \u0930\u0939\u0947\u0902\u0964",
    },
    "Venus": {
        "nature": "\u0935\u0948\u092d\u0935\u092a\u0942\u0930\u094d\u0923, \u0938\u0943\u091c\u0928\u093e\u0924\u094d\u092e\u0915 \u0914\u0930 \u0938\u0902\u092c\u0902\u0927-\u0915\u0947\u0902\u0926\u094d\u0930\u093f\u0924",
        "themes": "\u092a\u094d\u0930\u0947\u092e, \u0935\u093f\u0935\u093e\u0939, \u0915\u0932\u093e\u0924\u094d\u092e\u0915 \u0915\u093e\u0930\u094d\u092f, \u0927\u0928 \u0938\u0902\u091a\u092f, \u0938\u0941\u0916-\u0938\u0941\u0935\u093f\u0927\u093e \u0914\u0930 \u0938\u093e\u092e\u093e\u091c\u093f\u0915 \u0938\u0902\u092c\u0902\u0927",
        "positive": "\u0906\u0930\u094d\u0925\u093f\u0915 \u0938\u092e\u0943\u0926\u094d\u0927\u093f, \u0938\u0941\u0916\u0926 \u0938\u0902\u092c\u0902\u0927, \u0915\u0932\u093e\u0924\u094d\u092e\u0915 \u0938\u092b\u0932\u0924\u093e, \u0935\u093e\u0939\u0928/\u0938\u0902\u092a\u0924\u094d\u0924\u093f \u0915\u0940 \u092a\u094d\u0930\u093e\u092a\u094d\u0924\u093f",
        "challenges": "\u0905\u0924\u093f-\u092d\u094b\u0917, \u0905\u0924\u094d\u092f\u0927\u093f\u0915 \u0916\u0930\u094d\u091a, \u0938\u0902\u092c\u0902\u0927\u094b\u0902 \u092e\u0947\u0902 \u091c\u091f\u093f\u0932\u0924\u093e",
        "advice": "\u0938\u093e\u0930\u094d\u0925\u0915 \u0938\u0902\u092c\u0902\u0927 \u092c\u0928\u093e\u090f\u0902, \u0938\u092e\u091d\u0926\u093e\u0930\u0940 \u0938\u0947 \u0928\u093f\u0935\u0947\u0936 \u0915\u0930\u0947\u0902, \u0938\u0943\u091c\u0928\u093e\u0924\u094d\u092e\u0915 \u0930\u0941\u091a\u093f\u092f\u094b\u0902 \u0915\u094b \u0905\u092a\u0928\u093e\u090f\u0902\u0964",
    },
    "Sun": {
        "nature": "\u0905\u0927\u093f\u0915\u093e\u0930\u092a\u0942\u0930\u094d\u0923, \u092e\u0939\u0924\u094d\u0935\u093e\u0915\u093e\u0902\u0915\u094d\u0937\u0940 \u0914\u0930 \u0906\u0924\u094d\u092e\u0905\u092d\u093f\u0935\u094d\u092f\u0915\u094d\u0924\u093f",
        "themes": "\u0915\u0930\u093f\u092f\u0930 \u092e\u0947\u0902 \u0909\u0928\u094d\u0928\u0924\u093f, \u0928\u0947\u0924\u0943\u0924\u094d\u0935 \u0915\u0940 \u092d\u0942\u092e\u093f\u0915\u093e, \u0938\u0930\u0915\u093e\u0930\u0940 \u0938\u0902\u092a\u0930\u094d\u0915, \u092a\u093f\u0924\u093e \u0915\u093e \u092a\u094d\u0930\u092d\u093e\u0935, \u0938\u094d\u0935\u093e\u0938\u094d\u0925\u094d\u092f \u0914\u0930 \u092a\u094d\u0930\u0924\u093f\u0937\u094d\u0920\u093e",
        "positive": "\u092a\u0926 \u0914\u0930 \u0905\u0927\u093f\u0915\u093e\u0930 \u092e\u0947\u0902 \u0935\u0943\u0926\u094d\u0927\u093f, \u0938\u0930\u0915\u093e\u0930\u0940 \u0915\u0943\u092a\u093e, \u0926\u0943\u0922\u093c \u0907\u091a\u094d\u091b\u093e\u0936\u0915\u094d\u0924\u093f, \u0928\u0947\u0924\u0943\u0924\u094d\u0935 \u0915\u0947 \u0905\u0935\u0938\u0930",
        "challenges": "\u0905\u0939\u0902\u0915\u093e\u0930 \u0938\u0902\u0918\u0930\u094d\u0937, \u0905\u0927\u093f\u0915\u093e\u0930\u093f\u092f\u094b\u0902 \u0938\u0947 \u0924\u0928\u093e\u0935\u092a\u0942\u0930\u094d\u0923 \u0938\u0902\u092c\u0902\u0927, \u0939\u0943\u0926\u092f/\u0928\u0947\u0924\u094d\u0930/\u0939\u0921\u094d\u0921\u093f\u092f\u094b\u0902 \u0938\u0947 \u0938\u0902\u092c\u0902\u0927\u093f\u0924 \u0938\u094d\u0935\u093e\u0938\u094d\u0925\u094d\u092f \u0938\u092e\u0938\u094d\u092f\u093e\u090f\u0901",
        "advice": "\u0928\u092e\u094d\u0930\u0924\u093e \u0915\u0947 \u0938\u093e\u0925 \u0928\u0947\u0924\u0943\u0924\u094d\u0935 \u0915\u0930\u0947\u0902, \u0938\u094d\u0935\u093e\u0938\u094d\u0925\u094d\u092f \u0915\u093e \u0927\u094d\u092f\u093e\u0928 \u0930\u0916\u0947\u0902, \u092a\u093f\u0924\u093e \u0915\u093e \u0938\u092e\u094d\u092e\u093e\u0928 \u0915\u0930\u0947\u0902\u0964",
    },
    "Moon": {
        "nature": "\u092d\u093e\u0935\u0928\u093e\u0924\u094d\u092e\u0915, \u092a\u094b\u0937\u0915 \u0914\u0930 \u092e\u093e\u0928\u0938\u093f\u0915 \u0930\u0942\u092a \u0938\u0947 \u0938\u0915\u094d\u0930\u093f\u092f",
        "themes": "\u092d\u093e\u0935\u0928\u093e\u0924\u094d\u092e\u0915 \u0938\u094d\u0935\u093e\u0938\u094d\u0925\u094d\u092f, \u092e\u093e\u0924\u093e \u0915\u093e \u092a\u094d\u0930\u092d\u093e\u0935, \u0938\u093e\u0930\u094d\u0935\u091c\u0928\u093f\u0915 \u0935\u094d\u092f\u0935\u0939\u093e\u0930, \u092f\u093e\u0924\u094d\u0930\u093e, \u092e\u093e\u0928\u0938\u093f\u0915 \u0936\u093e\u0902\u0924\u093f \u0914\u0930 \u0918\u0930\u0947\u0932\u0942 \u0938\u0941\u0916",
        "positive": "\u092d\u093e\u0935\u0928\u093e\u0924\u094d\u092e\u0915 \u0938\u0902\u0924\u0941\u0937\u094d\u091f\u093f, \u092e\u093e\u0924\u093e \u0938\u0947 \u0905\u091a\u094d\u091b\u0947 \u0938\u0902\u092c\u0902\u0927, \u091c\u0928\u092a\u094d\u0930\u093f\u092f\u0924\u093e, \u092f\u093e\u0924\u094d\u0930\u093e \u0915\u0947 \u0905\u0935\u0938\u0930, \u092e\u093e\u0928\u0938\u093f\u0915 \u0938\u094d\u092a\u0937\u094d\u091f\u0924\u093e",
        "challenges": "\u092e\u0928\u094b\u0926\u0936\u093e \u092e\u0947\u0902 \u0909\u0924\u093e\u0930-\u091a\u0922\u093c\u093e\u0935, \u091a\u093f\u0902\u0924\u093e, \u0918\u0930\u0947\u0932\u0942 \u0935\u093f\u0918\u094d\u0928 \u0914\u0930 \u0905\u0924\u093f-\u0938\u0902\u0935\u0947\u0926\u0928\u0936\u0940\u0932\u0924\u093e",
        "advice": "\u092e\u093e\u0928\u0938\u093f\u0915 \u0938\u094d\u0935\u093e\u0938\u094d\u0925\u094d\u092f \u0915\u094b \u092a\u094d\u0930\u093e\u0925\u092e\u093f\u0915\u0924\u093e \u0926\u0947\u0902, \u092a\u093e\u0928\u0940 \u0915\u0947 \u0928\u093f\u0915\u091f \u0938\u092e\u092f \u092c\u093f\u0924\u093e\u090f\u0902, \u092a\u0930\u093f\u0935\u093e\u0930\u093f\u0915 \u092c\u0902\u0927\u0928\u094b\u0902 \u0915\u094b \u092a\u094b\u0937\u093f\u0924 \u0915\u0930\u0947\u0902\u0964",
    },
    "Mars": {
        "nature": "\u090a\u0930\u094d\u091c\u093e\u0935\u093e\u0928, \u0938\u093e\u0939\u0938\u0940 \u0914\u0930 \u0915\u094d\u0930\u093f\u092f\u093e-\u0915\u0947\u0902\u0926\u094d\u0930\u093f\u0924",
        "themes": "\u0936\u093e\u0930\u0940\u0930\u093f\u0915 \u090a\u0930\u094d\u091c\u093e, \u0938\u0902\u092a\u0924\u094d\u0924\u093f \u0915\u0947 \u092e\u093e\u092e\u0932\u0947, \u092d\u093e\u0908-\u092c\u0939\u0928, \u0938\u093e\u0939\u0938, \u0924\u0915\u0928\u0940\u0915\u0940 \u0915\u094c\u0936\u0932 \u0914\u0930 \u092a\u094d\u0930\u0924\u093f\u0938\u094d\u092a\u0930\u094d\u0927\u093e",
        "positive": "\u092a\u094d\u0930\u0924\u093f\u0938\u094d\u092a\u0930\u094d\u0927\u093e \u092e\u0947\u0902 \u0938\u092b\u0932\u0924\u093e, \u0938\u0902\u092a\u0924\u094d\u0924\u093f \u0915\u0940 \u092a\u094d\u0930\u093e\u092a\u094d\u0924\u093f, \u0936\u093e\u0930\u0940\u0930\u093f\u0915 \u0936\u0915\u094d\u0924\u093f, \u091a\u0941\u0928\u094c\u0924\u093f\u092f\u094b\u0902 \u0915\u093e \u0938\u093e\u092e\u0928\u093e \u0915\u0930\u0928\u0947 \u0915\u093e \u0938\u093e\u0939\u0938",
        "challenges": "\u0926\u0941\u0930\u094d\u0918\u091f\u0928\u093e\u090f\u0901, \u0938\u0902\u0918\u0930\u094d\u0937, \u0930\u0915\u094d\u0924 \u0938\u0902\u092c\u0902\u0927\u0940 \u0938\u094d\u0935\u093e\u0938\u094d\u0925\u094d\u092f \u0938\u092e\u0938\u094d\u092f\u093e\u090f\u0901, \u0915\u093e\u0928\u0942\u0928\u0940 \u0935\u093f\u0935\u093e\u0926 \u0914\u0930 \u0915\u094d\u0930\u094b\u0927 \u092a\u094d\u0930\u092c\u0902\u0927\u0928",
        "advice": "\u090a\u0930\u094d\u091c\u093e \u0915\u094b \u0936\u093e\u0930\u0940\u0930\u093f\u0915 \u0917\u0924\u093f\u0935\u093f\u0927\u093f \u0914\u0930 \u0930\u091a\u0928\u093e\u0924\u094d\u092e\u0915 \u092a\u0930\u093f\u092f\u094b\u091c\u0928\u093e\u0913\u0902 \u092e\u0947\u0902 \u0932\u0917\u093e\u090f\u0902, \u0905\u0928\u093e\u0935\u0936\u094d\u092f\u0915 \u0938\u0902\u0918\u0930\u094d\u0937\u094b\u0902 \u0938\u0947 \u092c\u091a\u0947\u0902, \u0927\u0948\u0930\u094d\u092f \u0930\u0916\u0947\u0902\u0964",
    },
    "Rahu": {
        "nature": "\u092e\u0939\u0924\u094d\u0935\u093e\u0915\u093e\u0902\u0915\u094d\u0937\u0940, \u0905\u092a\u0930\u0902\u092a\u0930\u093e\u0917\u0924 \u0914\u0930 \u0938\u093e\u0902\u0938\u093e\u0930\u093f\u0915",
        "themes": "\u092d\u094c\u0924\u093f\u0915 \u092e\u0939\u0924\u094d\u0935\u093e\u0915\u093e\u0902\u0915\u094d\u0937\u093e, \u0935\u093f\u0926\u0947\u0936\u0940 \u0938\u0902\u092a\u0930\u094d\u0915, \u092a\u094d\u0930\u094c\u0926\u094d\u092f\u094b\u0917\u093f\u0915\u0940, \u0905\u092a\u0930\u0902\u092a\u0930\u093e\u0917\u0924 \u092e\u093e\u0930\u094d\u0917, \u0905\u091a\u093e\u0928\u0915 \u0909\u0924\u094d\u0925\u093e\u0928 \u0914\u0930 \u091c\u0941\u0928\u0942\u0928\u0940 \u092a\u094d\u0930\u092f\u093e\u0938",
        "positive": "\u0905\u091a\u093e\u0928\u0915 \u0932\u093e\u092d, \u0935\u093f\u0926\u0947\u0936\u094b\u0902 \u092e\u0947\u0902 \u0938\u092b\u0932\u0924\u093e, \u092a\u094d\u0930\u094c\u0926\u094d\u092f\u094b\u0917\u093f\u0915\u0940 \u092e\u0947\u0902 \u0909\u0928\u094d\u0928\u0924\u093f, \u0938\u093e\u092e\u093e\u091c\u093f\u0915 \u092c\u093e\u0927\u093e\u0913\u0902 \u0915\u094b \u0924\u094b\u0921\u093c\u0928\u093e",
        "challenges": "\u0927\u094b\u0916\u093e, \u092d\u094d\u0930\u092e, \u0928\u0936\u093e, \u092d\u092f \u0914\u0930 \u091a\u093f\u0902\u0924\u093e, \u0915\u0932\u0902\u0915 \u0914\u0930 \u092d\u094d\u0930\u093e\u092e\u0915 \u092a\u094d\u0930\u092f\u093e\u0938",
        "advice": "\u0938\u092d\u0940 \u0935\u094d\u092f\u0935\u0939\u093e\u0930\u094b\u0902 \u092e\u0947\u0902 \u0928\u0948\u0924\u093f\u0915 \u0930\u0939\u0947\u0902, \u0936\u0949\u0930\u094d\u091f\u0915\u091f \u0914\u0930 \u091c\u0932\u094d\u0926\u0940 \u0927\u0928-\u092a\u094d\u0930\u093e\u092a\u094d\u0924\u093f \u092f\u094b\u091c\u0928\u093e\u0913\u0902 \u0938\u0947 \u092c\u091a\u0947\u0902, \u0906\u0927\u094d\u092f\u093e\u0924\u094d\u092e\u093f\u0915 \u0930\u0942\u092a \u0938\u0947 \u0938\u094d\u0925\u093f\u0930 \u0930\u0939\u0947\u0902\u0964",
    },
    "Jupiter": {
        "nature": "\u092c\u0941\u0926\u094d\u0927\u093f\u092e\u093e\u0928, \u0935\u093f\u0938\u094d\u0924\u093e\u0930\u0935\u093e\u0926\u0940 \u0914\u0930 \u092a\u0930\u094b\u092a\u0915\u093e\u0930\u0940",
        "themes": "\u091c\u094d\u091e\u093e\u0928, \u0909\u091a\u094d\u091a \u0936\u093f\u0915\u094d\u0937\u093e, \u0906\u0927\u094d\u092f\u093e\u0924\u094d\u092e\u093f\u0915\u0924\u093e, \u0938\u0902\u0924\u093e\u0928, \u0927\u0928, \u0917\u0941\u0930\u0941 \u0915\u093e \u092a\u094d\u0930\u092d\u093e\u0935 \u0914\u0930 \u0927\u093e\u0930\u094d\u092e\u093f\u0915 \u0915\u093e\u0930\u094d\u092f",
        "positive": "\u0906\u0927\u094d\u092f\u093e\u0924\u094d\u092e\u093f\u0915 \u0935\u093f\u0915\u093e\u0938, \u0936\u0948\u0915\u094d\u0937\u093f\u0915 \u0909\u092a\u0932\u092c\u094d\u0927\u093f\u092f\u093e\u0901, \u0938\u0902\u0924\u093e\u0928 \u092a\u094d\u0930\u093e\u092a\u094d\u0924\u093f, \u0927\u0928 \u0935\u0943\u0926\u094d\u0927\u093f, \u0924\u0940\u0930\u094d\u0925\u092f\u093e\u0924\u094d\u0930\u093e \u0915\u0947 \u0905\u0935\u0938\u0930",
        "challenges": "\u0905\u0924\u093f-\u0906\u0936\u093e\u0935\u093e\u0926, \u0935\u091c\u0928 \u0935\u0943\u0926\u094d\u0927\u093f, \u092f\u0915\u0943\u0924 \u0938\u0902\u092c\u0902\u0927\u0940 \u0938\u092e\u0938\u094d\u092f\u093e\u090f\u0901 \u0914\u0930 \u0906\u0924\u094d\u092e\u0938\u0902\u0924\u0941\u0937\u094d\u091f\u093f",
        "advice": "\u0909\u091a\u094d\u091a \u0936\u093f\u0915\u094d\u0937\u093e \u092a\u094d\u0930\u093e\u092a\u094d\u0924 \u0915\u0930\u0947\u0902, \u0917\u0941\u0930\u0941 \u0915\u0940 \u0916\u094b\u091c \u0915\u0930\u0947\u0902, \u0909\u0926\u093e\u0930\u0924\u093e \u0915\u093e \u0905\u092d\u094d\u092f\u093e\u0938 \u0915\u0930\u0947\u0902, \u0927\u0930\u094d\u092e \u0915\u0947 \u0905\u0928\u0941\u0938\u093e\u0930 \u0915\u093e\u0930\u094d\u092f \u0915\u0930\u0947\u0902\u0964",
    },
    "Saturn": {
        "nature": "\u0905\u0928\u0941\u0936\u093e\u0938\u093f\u0924, \u0915\u093e\u0930\u094d\u092e\u093f\u0915 \u0914\u0930 \u0926\u0943\u0922\u093c",
        "themes": "\u0915\u0920\u093f\u0928 \u092a\u0930\u093f\u0936\u094d\u0930\u092e, \u0905\u0928\u0941\u0936\u093e\u0938\u0928, \u0926\u0940\u0930\u094d\u0918\u093e\u092f\u0941, \u0915\u0930\u094d\u092e, \u0938\u0947\u0935\u093e, \u0935\u093f\u0932\u0902\u092c \u0914\u0930 \u0935\u094d\u092f\u0935\u0938\u094d\u0925\u093f\u0924 \u0935\u093f\u0915\u093e\u0938",
        "positive": "\u092a\u0942\u0930\u094d\u0935 \u092a\u0930\u093f\u0936\u094d\u0930\u092e \u0915\u093e \u092b\u0932, \u0926\u0943\u0922\u093c\u0924\u093e \u0938\u0947 \u0938\u093f\u0926\u094d\u0927\u093f, \u0905\u091a\u0932 \u0938\u0902\u092a\u0924\u094d\u0924\u093f \u0932\u093e\u092d, \u0915\u0930\u093f\u092f\u0930 \u0938\u094d\u0925\u093f\u0930\u0924\u093e \u0914\u0930 \u0917\u0939\u0930\u0940 \u092a\u0930\u093f\u092a\u0915\u094d\u0935\u0924\u093e",
        "challenges": "\u0935\u093f\u0932\u0902\u092c \u0914\u0930 \u092c\u093e\u0927\u093e\u090f\u0901, \u091c\u094b\u0921\u093c\u094b\u0902/\u0939\u0921\u094d\u0921\u093f\u092f\u094b\u0902 \u0915\u0940 \u0938\u094d\u0935\u093e\u0938\u094d\u0925\u094d\u092f \u0938\u092e\u0938\u094d\u092f\u093e\u090f\u0901, \u0905\u0915\u0947\u0932\u0947\u092a\u0928 \u0915\u0940 \u092d\u093e\u0935\u0928\u093e, \u092d\u093e\u0930\u0940 \u091c\u093f\u092e\u094d\u092e\u0947\u0926\u093e\u0930\u093f\u092f\u093e\u0901 \u0914\u0930 \u0905\u0935\u0938\u093e\u0926",
        "advice": "\u0905\u0928\u0941\u0936\u093e\u0938\u0928 \u0914\u0930 \u0927\u0948\u0930\u094d\u092f \u0905\u092a\u0928\u093e\u090f\u0902, \u0928\u093f\u0903\u0938\u094d\u0935\u093e\u0930\u094d\u0925 \u0938\u0947\u0935\u093e \u0915\u0930\u0947\u0902, \u0939\u0921\u094d\u0921\u093f\u092f\u094b\u0902 \u0914\u0930 \u091c\u094b\u0921\u093c\u094b\u0902 \u0915\u0940 \u0926\u0947\u0916\u092d\u093e\u0932 \u0915\u0930\u0947\u0902, \u0936\u0949\u0930\u094d\u091f\u0915\u091f \u0938\u0947 \u092c\u091a\u0947\u0902\u0964",
    },
    "Mercury": {
        "nature": "\u092c\u094c\u0926\u094d\u0927\u093f\u0915, \u0938\u0902\u0935\u093e\u0926\u0936\u0940\u0932 \u0914\u0930 \u0905\u0928\u0941\u0915\u0942\u0932\u0928\u0936\u0940\u0932",
        "themes": "\u0938\u0902\u0935\u093e\u0926, \u0935\u094d\u092f\u093e\u092a\u093e\u0930, \u0936\u093f\u0915\u094d\u0937\u093e, \u092c\u0941\u0926\u094d\u0927\u093f, \u0935\u094d\u092f\u093e\u092a\u093e\u0930, \u0932\u0947\u0916\u0928 \u0914\u0930 \u0935\u093f\u0936\u094d\u0932\u0947\u0937\u0923\u093e\u0924\u094d\u092e\u0915 \u0938\u094b\u091a",
        "positive": "\u0935\u094d\u092f\u093e\u092a\u093e\u0930\u093f\u0915 \u0938\u092b\u0932\u0924\u093e, \u092c\u094c\u0926\u094d\u0927\u093f\u0915 \u0909\u092a\u0932\u092c\u094d\u0927\u093f\u092f\u093e\u0901, \u0905\u091a\u094d\u091b\u093e \u0938\u0902\u0935\u093e\u0926, \u0938\u092b\u0932 \u0935\u093e\u0930\u094d\u0924\u093e, \u0932\u0947\u0916\u0928/\u092a\u094d\u0930\u0915\u093e\u0936\u0928 \u0914\u0930 \u0928\u090f \u0915\u094c\u0936\u0932 \u0938\u0940\u0916\u0928\u093e",
        "challenges": "\u0918\u092c\u0930\u093e\u0939\u091f, \u0924\u094d\u0935\u091a\u093e \u0938\u092e\u0938\u094d\u092f\u093e\u090f\u0901, \u0905\u0928\u093f\u0930\u094d\u0923\u092f, \u0935\u093e\u0923\u0940 \u0938\u0902\u092c\u0902\u0927\u0940 \u0938\u092e\u0938\u094d\u092f\u093e\u090f\u0901, \u0935\u094d\u092f\u093e\u092a\u093e\u0930\u093f\u0915 \u0905\u0938\u092b\u0932\u0924\u093e\u090f\u0901 \u0914\u0930 \u092c\u093f\u0916\u0930\u093e \u0927\u094d\u092f\u093e\u0928",
        "advice": "\u0936\u093f\u0915\u094d\u0937\u093e \u0914\u0930 \u0915\u094c\u0936\u0932 \u0935\u093f\u0915\u093e\u0938 \u092e\u0947\u0902 \u0928\u093f\u0935\u0947\u0936 \u0915\u0930\u0947\u0902, \u0906\u092f \u0915\u0947 \u0938\u094d\u0930\u094b\u0924\u094b\u0902 \u092e\u0947\u0902 \u0935\u093f\u0935\u093f\u0927\u0924\u093e \u0932\u093e\u090f\u0902, \u0938\u094d\u092a\u0937\u094d\u091f \u0938\u0902\u0935\u093e\u0926 \u092c\u0928\u093e\u090f \u0930\u0916\u0947\u0902\u0964",
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
        blocks.append("\u0935\u0930\u094d\u0924\u092e\u093e\u0928 \u0926\u0936\u093e \u0915\u093e\u0932 \u0928\u093f\u0930\u094d\u0927\u093e\u0930\u093f\u0924 \u0928\u0939\u0940\u0902 \u0915\u093f\u092f\u093e \u091c\u093e \u0938\u0915\u093e\u0964")
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
    blocks.append("## \u0935\u0930\u094d\u0924\u092e\u093e\u0928 \u0926\u0936\u093e \u0938\u094d\u0925\u093f\u0924\u093f")
    position = f"\u0906\u092a \u0935\u0930\u094d\u0924\u092e\u093e\u0928 \u092e\u0947\u0902 <b>{maha_hi} \u092e\u0939\u093e\u0926\u0936\u093e</b>"
    if current_antar:
        antar_hi = PLANET_HI_FULL.get(current_antar, current_antar)
        position += f" \u0915\u0947 \u0905\u0902\u0924\u0930\u094d\u0917\u0924 <b>{antar_hi} \u0905\u0902\u0924\u0930\u094d\u0926\u0936\u093e</b>"
    if current_prat:
        prat_hi = PLANET_HI_FULL.get(current_prat, current_prat)
        position += f" \u0914\u0930 <b>{prat_hi} \u092a\u094d\u0930\u0924\u094d\u092f\u0902\u0924\u0930</b>"
    position += " \u091a\u0932 \u0930\u0939\u0947 \u0939\u0948\u0902\u0964"
    if remaining_yrs > 1:
        position += (f" {maha_hi} \u092e\u0939\u093e\u0926\u0936\u093e <b>{current_maha_data[2].strftime('%B %Y')}</b> "
                     f"\u0924\u0915 \u091c\u093e\u0930\u0940 \u0930\u0939\u0947\u0917\u0940 "
                     f"(\u0932\u0917\u092d\u0917 {remaining_yrs:.1f} \u0935\u0930\u094d\u0937 \u0936\u0947\u0937)\u0964")
    else:
        position += (f" {maha_hi} \u092e\u0939\u093e\u0926\u0936\u093e <b>{current_maha_data[2].strftime('%B %Y')}</b> "
                     f"\u092e\u0947\u0902 \u0938\u092e\u093e\u092a\u094d\u0924 \u0939\u094b\u0917\u0940 "
                     f"({remaining_days} \u0926\u093f\u0928 \u0936\u0947\u0937)\u0964")
    blocks.append(position)

    # Mahadasha reading
    blocks.append(f"## {maha_hi} \u092e\u0939\u093e\u0926\u0936\u093e \u2014 \u0906\u092a \u0915\u094d\u092f\u093e \u0905\u0928\u0941\u092d\u0935 \u0915\u0930 \u0930\u0939\u0947 \u0939\u0948\u0902")
    blocks.append(
        f"{maha_hi} \u0915\u093e \u0915\u093e\u0932 <b>{maha_info.get('nature', '\u092e\u0939\u0924\u094d\u0935\u092a\u0942\u0930\u094d\u0923')}</b> "
        f"\u092a\u094d\u0930\u0915\u0943\u0924\u093f \u0915\u093e \u0939\u0948\u0964 \u0907\u0938 \u0915\u093e\u0932 \u0915\u0947 \u092a\u094d\u0930\u092e\u0941\u0916 \u0935\u093f\u0937\u092f\u094b\u0902 \u092e\u0947\u0902 \u0936\u093e\u092e\u093f\u0932 \u0939\u0948\u0902: "
        f"{maha_info.get('themes', '\u0935\u093f\u092d\u093f\u0928\u094d\u0928 \u091c\u0940\u0935\u0928 \u092a\u0930\u093f\u0935\u0930\u094d\u0924\u0928')}\u0964")
    blocks.append(
        f"<b>\u0907\u0938 \u0915\u093e\u0932 \u0915\u0940 \u0936\u0915\u094d\u0924\u093f\u092f\u093e\u0901:</b> "
        f"{maha_info.get('positive', '\u0935\u093f\u0915\u093e\u0938 \u0915\u0947 \u0905\u0935\u0938\u0930')}\u0964")
    blocks.append(
        f"<b>\u0938\u093e\u0935\u0927\u093e\u0928\u0940 \u0915\u0947 \u0915\u094d\u0937\u0947\u0924\u094d\u0930:</b> "
        f"{maha_info.get('challenges', '\u091a\u0941\u0928\u094c\u0924\u093f\u092f\u093e\u0901 \u0906 \u0938\u0915\u0924\u0940 \u0939\u0948\u0902')}\u0964")

    # Antardasha
    if current_antar:
        antar_hi = PLANET_HI_FULL.get(current_antar, current_antar)
        antar_info = DASHA_READING_HI.get(current_antar, {})
        antar_end = current_antar_data[2]
        blocks.append(f"## {antar_hi} \u0905\u0902\u0924\u0930\u094d\u0926\u0936\u093e \u2014 \u0935\u0930\u094d\u0924\u092e\u093e\u0928 \u0909\u092a-\u0915\u093e\u0932 \u0915\u093e \u092a\u094d\u0930\u092d\u093e\u0935")
        blocks.append(
            f"{maha_hi} \u0915\u0947 \u0935\u094d\u092f\u093e\u092a\u0915 \u0915\u093e\u0932 \u092e\u0947\u0902, <b>{antar_hi} "
            f"\u0905\u0902\u0924\u0930\u094d\u0926\u0936\u093e</b> (<b>{antar_end.strftime('%B %Y')}</b> \u0924\u0915) "
            f"<b>{antar_info.get('nature', '\u0935\u093f\u0936\u0947\u0937')}</b> \u090a\u0930\u094d\u091c\u093e \u091c\u094b\u0921\u093c\u0924\u0940 \u0939\u0948\u0964 "
            f"\u092f\u0939 \u0909\u092a-\u0915\u093e\u0932 {antar_info.get('themes', '\u0915\u0941\u091b \u091c\u0940\u0935\u0928 \u0915\u094d\u0937\u0947\u0924\u094d\u0930\u094b\u0902')} \u092a\u0930 \u091c\u094b\u0930 \u0926\u0947\u0924\u093e \u0939\u0948\u0964")
        blocks.append(
            f"<b>{maha_hi}\u2013{antar_hi}</b> \u0915\u093e \u0938\u0902\u092f\u094b\u091c\u0928 \u0926\u0930\u094d\u0936\u093e\u0924\u093e \u0939\u0948 \u0915\u093f "
            f"{maha_hi} \u092e\u0939\u093e\u0926\u0936\u093e \u0915\u0947 \u0935\u094d\u092f\u093e\u092a\u0915 \u0935\u093f\u0937\u092f "
            f"{antar_hi} \u0915\u0947 \u092a\u094d\u0930\u092d\u093e\u0935 \u0938\u0947 \u091b\u0928\u0924\u0947 \u0939\u0948\u0902 \u2014 "
            f"{antar_info.get('positive', '\u0905\u0935\u0938\u0930')} \u0932\u093e\u0924\u0947 \u0939\u0941\u090f "
            f"{antar_info.get('challenges', '\u0938\u0902\u092d\u093e\u0935\u093f\u0924 \u0915\u0920\u093f\u0928\u093e\u0907\u092f\u094b\u0902')} \u0915\u0947 \u092a\u094d\u0930\u0924\u093f \u0938\u091a\u0947\u0924 \u0930\u0939\u0928\u093e \u091a\u093e\u0939\u093f\u090f\u0964")

    # Pratyantar
    if current_prat:
        prat_hi = PLANET_HI_FULL.get(current_prat, current_prat)
        prat_info = DASHA_READING_HI.get(current_prat, {})
        prat_end = current_prat_data[2]
        days_left = (prat_end - today).days
        blocks.append(f"## {prat_hi} \u092a\u094d\u0930\u0924\u094d\u092f\u0902\u0924\u0930 \u2014 \u0924\u093e\u0924\u094d\u0915\u093e\u0932\u093f\u0915 \u092a\u094d\u0930\u092d\u093e\u0935")
        blocks.append(
            f"\u0938\u092c\u0938\u0947 \u0924\u093e\u0924\u094d\u0915\u093e\u0932\u093f\u0915 \u0938\u094d\u0924\u0930 \u092a\u0930, <b>{prat_hi} \u092a\u094d\u0930\u0924\u094d\u092f\u0902\u0924\u0930</b> "
            f"(\u0905\u0917\u0932\u0947 <b>{days_left} \u0926\u093f\u0928\u094b\u0902</b> \u0924\u0915, "
            f"{prat_end.strftime('%d %B %Y')} \u0924\u0915) "
            f"{prat_info.get('themes', '\u0935\u093f\u0936\u0947\u0937 \u092e\u093e\u092e\u0932\u094b\u0902')} \u092a\u0930 \u0905\u0932\u094d\u092a\u0915\u093e\u0932\u093f\u0915 \u0927\u094d\u092f\u093e\u0928 \u0932\u093e\u0924\u093e \u0939\u0948\u0964 "
            f"\u0907\u0938 \u0938\u0942\u0915\u094d\u0937\u094d\u092e \u0915\u093e\u0932 \u092e\u0947\u0902 "
            f"{prat_info.get('positive', '\u0938\u0915\u093e\u0930\u093e\u0924\u094d\u092e\u0915 \u0935\u093f\u0915\u093e\u0938')} \u0926\u0947\u0916\u0947\u0902\u0964")

    # Looking ahead
    blocks.append("## \u0906\u0917\u0947 \u0926\u0947\u0916\u0947\u0902 \u2014 \u0906\u0928\u0947 \u0935\u093e\u0932\u0947 \u092a\u0930\u093f\u0935\u0930\u094d\u0924\u0928")
    if next_antar_data:
        na_lord, na_start, na_end, na_yrs = next_antar_data
        na_hi = PLANET_HI_FULL.get(na_lord, na_lord)
        na_info = DASHA_READING_HI.get(na_lord, {})
        blocks.append(
            f"\u0905\u0917\u0932\u093e \u0905\u0902\u0924\u0930\u094d\u0926\u0936\u093e \u092a\u0930\u093f\u0935\u0930\u094d\u0924\u0928 <b>{maha_hi}\u2013{na_hi}</b> \u0939\u094b\u0917\u093e, "
            f"\u091c\u094b <b>{na_start.strftime('%B %Y')}</b> \u0938\u0947 \u0936\u0941\u0930\u0942 \u0939\u094b\u0917\u093e\u0964 "
            f"\u092f\u0939 <b>{na_info.get('nature', '\u092d\u093f\u0928\u094d\u0928')}</b> \u090a\u0930\u094d\u091c\u093e \u0915\u0940 \u0913\u0930 \u092c\u0926\u0932\u093e\u0935 \u0932\u093e\u090f\u0917\u093e, "
            f"\u091c\u093f\u0938\u092e\u0947\u0902 {na_info.get('themes', '\u0928\u090f \u0935\u093f\u0937\u092f')} \u092a\u0930 \u091c\u094b\u0930 \u0939\u094b\u0917\u093e\u0964")
    if next_maha_data:
        nm_lord, nm_start, nm_end, nm_yrs = next_maha_data
        nm_hi = PLANET_HI_FULL.get(nm_lord, nm_lord)
        nm_info = DASHA_READING_HI.get(nm_lord, {})
        blocks.append(
            f"\u090f\u0915 \u092c\u0921\u093c\u093e \u091c\u0940\u0935\u0928 \u092a\u0930\u093f\u0935\u0930\u094d\u0924\u0928 \u0924\u092c \u0906\u090f\u0917\u093e \u091c\u092c <b>{nm_hi} \u092e\u0939\u093e\u0926\u0936\u093e</b> "
            f"<b>{nm_start.strftime('%B %Y')}</b> \u092e\u0947\u0902 \u0936\u0941\u0930\u0942 \u0939\u094b\u0917\u0940 "
            f"({nm_yrs:.1f} \u0935\u0930\u094d\u0937, {nm_end.strftime('%B %Y')} \u0924\u0915)\u0964 "
            f"\u092f\u0939 \u0935\u0930\u094d\u0924\u092e\u093e\u0928 {maha_hi} \u0915\u0947 \u0935\u093f\u0937\u092f\u094b\u0902 \u0938\u0947 "
            f"<b>{nm_info.get('nature', '\u092d\u093f\u0928\u094d\u0928')}</b> \u092a\u094d\u0930\u0915\u0943\u0924\u093f \u0915\u0947 \u0915\u093e\u0932 \u0915\u0940 \u0913\u0930 \u092e\u0939\u0924\u094d\u0935\u092a\u0942\u0930\u094d\u0923 \u092c\u0926\u0932\u093e\u0935 \u0939\u094b\u0917\u093e\u0964")
        blocks.append(
            f"<b>{nm_hi} \u092e\u0939\u093e\u0926\u0936\u093e \u092e\u0947\u0902 \u0915\u094d\u092f\u093e \u0905\u092a\u0947\u0915\u094d\u0937\u093e \u0915\u0930\u0947\u0902:</b> "
            f"{nm_info.get('themes', '\u0928\u090f \u091c\u0940\u0935\u0928 \u0935\u093f\u0937\u092f')}\u0964 "
            f"\u092a\u094d\u0930\u092e\u0941\u0916 \u0936\u0915\u094d\u0924\u093f\u092f\u093e\u0901: {nm_info.get('positive', '\u0935\u093f\u092d\u093f\u0928\u094d\u0928 \u0905\u0935\u0938\u0930')}\u0964")

    # Guidance
    blocks.append(f"## \u0935\u0930\u094d\u0924\u092e\u093e\u0928 \u0915\u093e\u0932 \u0915\u0947 \u0932\u093f\u090f \u092e\u093e\u0930\u094d\u0917\u0926\u0930\u094d\u0936\u0928")
    blocks.append(maha_info.get('advice', '\u0938\u0902\u0924\u0941\u0932\u093f\u0924 \u0914\u0930 \u0938\u091a\u0947\u0924 \u0930\u0939\u0947\u0902\u0964'))

    return blocks


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
        retro = "\u211e" if p['retro'] else ""
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
        marker = "\u25c4 NOW" if is_now else ""
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
            marker = "\u25c4 NOW" if is_now else ""
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
                    marker = "\u25c4 NOW" if is_now else ""
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
    font_paths = [
        # macOS
        "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",
        # Linux / PythonAnywhere — Noto Sans Devanagari
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.otf",
        # Lohit fallback (common on Ubuntu/Debian)
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
    story.append(Paragraph("\u091c\u0928\u094d\u092e \u0915\u0941\u0923\u094d\u0921\u0932\u0940", title_style))
    story.append(Paragraph("by AstroShuklz", brand_style))
    story.append(Paragraph(f"{bd['name']}", subtitle_style))
    story.append(Paragraph(
        f"{bd['day']:02d}/{bd['month']:02d}/{bd['year']}  &nbsp; "
        f"{bd['hour']:02d}:{bd['minute']:02d}  &nbsp;\u00b7&nbsp; {bd['place']}",
        info_style))

    summary = (f"Lagna: {chart['asc_sign_en']} ({chart['asc_sign_hi']}) "
               f"{dms_str(chart['asc_deg'])}  &nbsp;\u00b7&nbsp; "
               f"Rashi: {chart['moon_rashi']} ({chart['moon_rashi_hi']})  &nbsp;\u00b7&nbsp; "
               f"Nakshatra: {chart['nakshatra']}, Pada {chart['nak_pada']} "
               f"({chart['nak_lord']})")
    story.append(Paragraph(summary, info_style))
    story.append(Spacer(1, 5*mm))

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
        retro = "\u211e" if p['retro'] else ""
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

    # ── Page 2: All three Dasha tables ───────────────────────────
    story.append(PageBreak())

    # Mahadasha
    story.append(Paragraph("Vimshottari Dasha \u2014 Mahadasha", section_style))

    m_header = ['Lord', 'Start', 'End', 'Years', '']
    m_data = [m_header]
    current_maha = None
    for lord, start, end, yrs in chart['dashas']:
        is_now = start <= today < end
        if is_now:
            current_maha = lord
        marker = "\u25c4 NOW" if is_now else ""
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
            f"Vimshottari Dasha \u2014 Antardasha (within {current_maha} Mahadasha)",
            section_style))

        a_header = ['Lord', 'Start', 'End', 'Duration', '']
        a_data = [a_header]
        current_antar = None
        for ad_lord, ad_start, ad_end, ad_yrs in chart['antardasha'][current_maha]:
            is_now = ad_start <= today < ad_end
            if is_now:
                current_antar = ad_lord
            marker = "\u25c4 NOW" if is_now else ""
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
                    f"Vimshottari Dasha \u2014 Pratyantar "
                    f"(within {current_maha}\u2013{current_antar})",
                    section_style))
                pd_header = ['Lord', 'Start', 'End', 'Duration', '']
                pd_data = [pd_header]
                for pd_lord, pd_start, pd_end, pd_yrs in chart['pratyantar'][key]:
                    is_now = pd_start <= today < pd_end
                    marker = "\u25c4 NOW" if is_now else ""
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
    # HINDI PAGES (हिन्दी)
    # ══════════════════════════════════════════════════════════════

    # Hindi styles
    hi_title_style = ParagraphStyle('KHiTitle', parent=styles['Title'],
        fontName=deva_font, fontSize=22, textColor=MAROON,
        alignment=TA_CENTER, spaceAfter=2*mm)
    hi_subtitle_style = ParagraphStyle('KHiSubtitle', parent=styles['Normal'],
        fontName=deva_font, fontSize=11, textColor=colors.HexColor("#444"),
        alignment=TA_CENTER, spaceAfter=1*mm)
    hi_info_style = ParagraphStyle('KHiInfo', parent=styles['Normal'],
        fontName=deva_font, fontSize=9, textColor=colors.HexColor("#555"),
        alignment=TA_CENTER, spaceAfter=3*mm)
    hi_section_style = ParagraphStyle('KHiSection', parent=styles['Heading2'],
        fontName=deva_font, fontSize=12, textColor=MAROON,
        alignment=TA_CENTER, spaceBefore=5*mm, spaceAfter=2*mm)
    hi_brand_style = ParagraphStyle('KHiBrand', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=10, textColor=colors.HexColor("#B8860B"),
        alignment=TA_CENTER, spaceAfter=4*mm)

    # ── Hindi Page 1: Header + Planetary Positions ───────────────
    story.append(PageBreak())
    story.append(Paragraph("\u091c\u0928\u094d\u092e \u0915\u0941\u0923\u094d\u0921\u0932\u0940", hi_title_style))
    story.append(Paragraph("by AstroShuklz", hi_brand_style))
    story.append(Paragraph(f"{bd['name']}", hi_subtitle_style))
    story.append(Paragraph(
        f"{bd['day']:02d}/{bd['month']:02d}/{bd['year']}  &nbsp; "
        f"{bd['hour']:02d}:{bd['minute']:02d}  &nbsp;\u00b7&nbsp; {bd['place']}",
        hi_info_style))

    hi_summary = (f"\u0932\u0917\u094d\u0928: {chart['asc_sign_hi']} "
                  f"{dms_str(chart['asc_deg'])}  &nbsp;\u00b7&nbsp; "
                  f"\u0930\u093e\u0936\u093f: {chart['moon_rashi_hi']}  &nbsp;\u00b7&nbsp; "
                  f"\u0928\u0915\u094d\u0937\u0924\u094d\u0930: {chart['nakshatra']}, "
                  f"\u092a\u0926 {chart['nak_pada']} "
                  f"({PLANET_HI_FULL.get(chart['nak_lord'], chart['nak_lord'])})")
    story.append(Paragraph(hi_summary, hi_info_style))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("\u0917\u094d\u0930\u0939 \u0938\u094d\u0925\u093f\u0924\u093f", hi_section_style))

    hi_p_header = ['\u0917\u094d\u0930\u0939', '\u0930\u093e\u0936\u093f',
                   '\u0905\u0902\u0936', '\u0930\u093e\u0936\u093f#',
                   '\u0932\u0917\u094d\u0928', '\u091a\u0928\u094d\u0926\u094d\u0930', '\u0935']
    hi_p_data = [hi_p_header]
    for pname in order:
        p = planets[pname]
        sidx = p['sign_idx']
        rashi = sidx + 1
        h_lag = (sidx - asc_sign) % 12 + 1
        h_moon = (sidx - moon_sign) % 12 + 1
        retro = "\u211e" if p['retro'] else ""
        hi_p_data.append([PLANET_HI_FULL.get(pname, pname), p['sign_hi'],
                          dms_str(p['deg']), str(rashi),
                          f"\u092d{h_lag}", f"\u092d{h_moon}", retro])

    hi_ptable = Table(hi_p_data, colWidths=[50, 70, 65, 40, 45, 45, 20])
    hi_ptable.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,0), deva_font),
        ('FONTNAME',   (0,1), (-1,-1), deva_font),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
        ('BACKGROUND', (0,0), (-1,0), HEADER_BG),
        ('TEXTCOLOR',  (0,0), (-1,0), HEADER_FG),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ROW_ALT]),
        ('TOPPADDING',  (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',(0,0), (-1,-1), 3),
    ]))
    story.append(hi_ptable)

    # ── Hindi Page 2: Dasha Tables ───────────────────────────────
    story.append(PageBreak())

    # Mahadasha
    story.append(Paragraph("\u0935\u093f\u0902\u0936\u094b\u0924\u094d\u0924\u0930\u0940 \u0926\u0936\u093e \u2014 \u092e\u0939\u093e\u0926\u0936\u093e", hi_section_style))
    hi_m_header = ['\u0938\u094d\u0935\u093e\u092e\u0940', '\u0906\u0930\u0902\u092d', '\u0905\u0902\u0924', '\u0935\u0930\u094d\u0937', '']
    hi_m_data = [hi_m_header]
    for lord, start, end, yrs in chart['dashas']:
        is_now = start <= today < end
        marker = "\u25c4 \u0905\u092d\u0940" if is_now else ""
        hi_m_data.append([PLANET_HI_FULL.get(lord, lord), start.strftime('%b %Y'),
                          end.strftime('%b %Y'), f"{yrs:.1f}", marker])

    hi_mtable = Table(hi_m_data, colWidths=[60, 80, 80, 50, 55])
    hi_m_style = [
        ('FONTNAME',   (0,0), (-1,-1), deva_font),
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
            hi_m_style.append(('BACKGROUND', (0, i), (-1, i), ROW_NOW))
            hi_m_style.append(('FONTNAME', (0, i), (-1, i), deva_font))
    hi_mtable.setStyle(TableStyle(hi_m_style))
    story.append(hi_mtable)

    # Antardasha
    if current_maha and current_maha in chart.get('antardasha', {}):
        maha_hi_name = PLANET_HI_FULL.get(current_maha, current_maha)
        story.append(Paragraph(
            f"\u0935\u093f\u0902\u0936\u094b\u0924\u094d\u0924\u0930\u0940 \u0926\u0936\u093e \u2014 "
            f"\u0905\u0902\u0924\u0930\u094d\u0926\u0936\u093e ({maha_hi_name} \u092e\u0939\u093e\u0926\u0936\u093e \u092e\u0947\u0902)",
            hi_section_style))

        hi_a_header = ['\u0938\u094d\u0935\u093e\u092e\u0940', '\u0906\u0930\u0902\u092d', '\u0905\u0902\u0924', '\u0905\u0935\u0927\u093f', '']
        hi_a_data = [hi_a_header]
        hi_current_antar = None
        for ad_lord, ad_start, ad_end, ad_yrs in chart['antardasha'][current_maha]:
            is_now = ad_start <= today < ad_end
            if is_now:
                hi_current_antar = ad_lord
            marker = "\u25c4 \u0905\u092d\u0940" if is_now else ""
            months = ad_yrs * 12
            dur_str = f"{ad_yrs:.1f}\u0935" if months >= 12 else f"{months:.1f}\u092e"
            hi_a_data.append([PLANET_HI_FULL.get(ad_lord, ad_lord),
                              ad_start.strftime('%d %b %Y'),
                              ad_end.strftime('%d %b %Y'), dur_str, marker])

        hi_atable = Table(hi_a_data, colWidths=[60, 90, 90, 55, 55])
        hi_a_style = [
            ('FONTNAME',   (0,0), (-1,-1), deva_font),
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
                hi_a_style.append(('BACKGROUND', (0, i), (-1, i), ROW_NOW))
        hi_atable.setStyle(TableStyle(hi_a_style))
        story.append(hi_atable)

        # Pratyantar
        if hi_current_antar:
            key = (current_maha, hi_current_antar)
            if key in chart.get('pratyantar', {}):
                antar_hi_name = PLANET_HI_FULL.get(hi_current_antar, hi_current_antar)
                story.append(Paragraph(
                    f"\u0935\u093f\u0902\u0936\u094b\u0924\u094d\u0924\u0930\u0940 \u0926\u0936\u093e \u2014 "
                    f"\u092a\u094d\u0930\u0924\u094d\u092f\u0902\u0924\u0930 ({maha_hi_name}\u2013{antar_hi_name})",
                    hi_section_style))
                hi_pd_header = ['\u0938\u094d\u0935\u093e\u092e\u0940', '\u0906\u0930\u0902\u092d', '\u0905\u0902\u0924', '\u0905\u0935\u0927\u093f', '']
                hi_pd_data = [hi_pd_header]
                for pd_lord, pd_start, pd_end, pd_yrs in chart['pratyantar'][key]:
                    is_now = pd_start <= today < pd_end
                    marker = "\u25c4 \u0905\u092d\u0940" if is_now else ""
                    days = pd_yrs * 365.25
                    dur_str = f"{pd_yrs*12:.1f}\u092e" if days >= 30 else f"{days:.0f}\u0926"
                    hi_pd_data.append([PLANET_HI_FULL.get(pd_lord, pd_lord),
                                       pd_start.strftime('%d %b %Y'),
                                       pd_end.strftime('%d %b %Y'), dur_str, marker])
                hi_pdtable = Table(hi_pd_data, colWidths=[60, 90, 90, 55, 55])
                hi_pd_style = [
                    ('FONTNAME',   (0,0), (-1,-1), deva_font),
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
                        hi_pd_style.append(('BACKGROUND', (0, i), (-1, i), ROW_NOW))
                hi_pdtable.setStyle(TableStyle(hi_pd_style))
                story.append(hi_pdtable)

    # ── Hindi Page 3: Predictions ────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("\u0926\u0936\u093e \u092b\u0932 \u090f\u0935\u0902 \u092d\u0935\u093f\u0937\u094d\u092f\u0935\u093e\u0923\u0940", hi_title_style))
    story.append(Paragraph("by AstroShuklz", hi_brand_style))
    story.append(Spacer(1, 3*mm))

    hi_reading_style = ParagraphStyle('KHiReading', parent=styles['Normal'],
        fontName=deva_font, fontSize=9.5, textColor=colors.HexColor("#333"),
        alignment=TA_LEFT, leading=14, spaceBefore=2*mm, spaceAfter=2*mm)
    hi_reading_bold = ParagraphStyle('KHiReadBold', parent=hi_reading_style,
        fontName=deva_font, fontSize=10, textColor=MAROON,
        spaceBefore=4*mm, spaceAfter=1*mm)

    hi_reading = _dasha_reading_hi(chart, today)
    for block in hi_reading:
        if block.startswith("##"):
            story.append(Paragraph(block[2:].strip(), hi_reading_bold))
        else:
            story.append(Paragraph(block, hi_reading_style))

    # ── Disclaimer & Footer (shared) ─────────────────────────────
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(
        "\u0905\u0938\u094d\u0935\u0940\u0915\u0930\u0923: \u092f\u0939 \u092a\u0920\u0928 \u0936\u093e\u0938\u094d\u0924\u094d\u0930\u0940\u092f "
        "\u0935\u093f\u0902\u0936\u094b\u0924\u094d\u0924\u0930\u0940 \u0926\u0936\u093e \u0935\u094d\u092f\u093e\u0916\u094d\u092f\u093e\u0913\u0902 "
        "\u092a\u0930 \u0906\u0927\u093e\u0930\u093f\u0924 \u0939\u0948 \u0914\u0930 \u0915\u0947\u0935\u0932 "
        "\u0936\u0948\u0915\u094d\u0937\u093f\u0915/\u092e\u0928\u094b\u0930\u0902\u091c\u0928 \u0909\u0926\u094d\u0926\u0947\u0936\u094d\u092f\u094b\u0902 "
        "\u0915\u0947 \u0932\u093f\u090f \u0939\u0948\u0964 \u0935\u094d\u092f\u0915\u094d\u0924\u093f\u0917\u0924 "
        "\u092e\u093e\u0930\u094d\u0917\u0926\u0930\u094d\u0936\u0928 \u0915\u0947 \u0932\u093f\u090f \u0915\u093f\u0938\u0940 "
        "\u092f\u094b\u0917\u094d\u092f \u091c\u094d\u092f\u094b\u0924\u093f\u0937 \u0938\u0947 \u092a\u0930\u093e\u092e\u0930\u094d\u0936 \u0915\u0930\u0947\u0902\u0964",
        disclaimer_style))

    story.append(Spacer(1, 8*mm))
    footer_style = ParagraphStyle('KFooter2', parent=styles['Normal'],
        fontName='Helvetica', fontSize=7, textColor=colors.HexColor("#AAAAAA"),
        alignment=TA_CENTER)
    story.append(Paragraph("Lahiri Ayanamsha  \u00b7  Swiss Ephemeris  \u00b7  "
                           "Generated by AstroShuklz", footer_style))

    doc.build(story)
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
        print(f"  \u2713 Found in CSV: lat={lat}, lon={lon}, UTC{utc:+.1f}")
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
                print(f"  \u2713 {location.address[:60]}")
                print(f"    lat={lat:.4f}, lon={lon:.4f}, UTC{offset_hours:+.2f} ({tz_name})")

                # Auto-save to CSV for future lookups
                save_city_to_csv(key, lat, lon, offset_hours)
                CITY_DB[key] = (lat, lon, offset_hours)
                print(f"    \u2713 Saved to cities.csv")

                return (lat, lon, offset_hours)

    except ImportError:
        pass
    except Exception:
        pass

    # ── 3. Fallback to hardcoded legacy DB ───────────────────────────────
    result = _LEGACY_CITY_DB.get(key)
    if result:
        lat, lon, utc = result
        print(f"  \u2713 Found in legacy DB: lat={lat}, lon={lon}, UTC{utc:+.1f}")
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