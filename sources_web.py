# -*- coding: utf-8 -*-
"""
SOURCES WEB — toutes les sources gratuites (sans cle) de l'IA apprenante.

Sources branchees :
  1. Open-Meteo        -> la vraie meteo (« meteo a Lyon »)
  2. REST Countries    -> infos pays (« capitale du Japon »)
  3. Wiktionnaire      -> definitions (« que veut dire ubuesque »)
  4. MediaWiki/Fandom  -> wikis Minecraft, Pokemon, Mario, Zelda
  5. Wikipedia         -> encyclopedie generale (par defaut)
  6. DuckDuckGo        -> reponses courtes (dernier recours)

Chaque source a un repli propre : si l'une ne repond pas, on passe a la
suivante sans planter. Aucune cle, aucun compte.
"""

import re
import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "IA-Apprenante/1.0 (projet educatif)"}
TIMEOUT = 7


def _strip_accents(s):
    return s.translate(str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc"))


def _get(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _strip_html(html):
    import html as _h
    t = re.sub(r"(?is)<(script|style|sup|table)[^>]*>.*?</\1>", " ", html)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = _h.unescape(t)
    t = re.sub(r"\[\s*modifier[^\]]*\]", " ", t, flags=re.I)
    t = re.sub(r"\[\d+\]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _phrases(texte, n=2):
    p = re.split(r"(?<=[.!?])\s+", texte.strip())
    return " ".join(p[:n]).strip()


# ======================================================================
#  1. MEDIAWIKI generique (Wikipedia, Wiktionnaire, Fandom...)
# ======================================================================
WIKIS = {
    "wikipedia":    ("https://fr.wikipedia.org/w/api.php", "Wikipedia"),
    "wiktionnaire": ("https://fr.wiktionary.org/w/api.php", "Wiktionnaire"),
    "minecraft":    ("https://minecraft.fandom.com/fr/api.php", "Wiki Minecraft"),
    "pokemon":      ("https://pokemon.fandom.com/fr/api.php", "Wiki Pokemon"),
    "mario":        ("https://mario.fandom.com/fr/api.php", "Wiki Mario"),
    "zelda":        ("https://zelda.fandom.com/fr/api.php", "Wiki Zelda"),
}


def _mw_search(api, query, limit=3):
    url = api + "?" + urllib.parse.urlencode(
        {"action": "query", "list": "search", "srsearch": query,
         "format": "json", "srlimit": limit})
    return [h["title"] for h in _get(url).get("query", {}).get("search", [])]


def _mw_extract(api, titre):
    """Renvoie (texte, est_une_page_d_homonymie)."""
    # 1) extrait en texte brut (dispo sur Wikipedia/Wiktionnaire)
    try:
        url = api + "?" + urllib.parse.urlencode(
            {"action": "query", "prop": "extracts|pageprops", "explaintext": 1,
             "exintro": 1, "titles": titre, "format": "json",
             "formatversion": 2})
        pages = _get(url).get("query", {}).get("pages", [])
        if pages:
            p = pages[0]
            if "disambiguation" in (p.get("pageprops") or {}):
                return "", True           # page « plusieurs sens »
            ex = (p.get("extract") or "").strip()
            if len(ex) > 25:
                return ex, False
    except Exception:  # noqa: BLE001
        pass
    # 2) repli : on lit le HTML de la page (marche partout, meme Fandom)
    try:
        url = api + "?" + urllib.parse.urlencode(
            {"action": "parse", "page": titre, "prop": "text",
             "format": "json", "formatversion": 2})
        return _strip_html(_get(url).get("parse", {}).get("text", "")), False
    except Exception:  # noqa: BLE001
        return "", False


def wiki(cle, query, phrases=2):
    api, nom = WIKIS[cle]
    for titre in _mw_search(api, query):
        ex, homonymie = _mw_extract(api, titre)
        if homonymie or not ex or len(ex) < 25:
            continue
        bas = _strip_accents(ex.lower())
        if "peut faire reference" in bas or "peut designer" in bas:
            continue
        # une liste de sens = plusieurs lignes courtes -> on passe
        if cle != "wiktionnaire":
            lignes = [l for l in ex.split("\n") if l.strip()]
            if len(lignes) >= 3 and sum(len(l) for l in lignes) / len(lignes) < 80:
                continue
        return _phrases(ex, phrases), f"{nom} — « {titre} »"
    return None


def candidats(query, cle="wikipedia", limit=3):
    """Les titres de pages qui correspondent le mieux a la recherche."""
    api, _nom = WIKIS[cle]
    try:
        return _mw_search(api, query, limit)
    except Exception:  # noqa: BLE001
        return []


def est_homonymie(titre, cle="wikipedia"):
    """Cette page liste-t-elle plusieurs sens differents ?"""
    api, _nom = WIKIS[cle]
    try:
        url = api + "?" + urllib.parse.urlencode(
            {"action": "query", "prop": "pageprops", "titles": titre,
             "format": "json", "formatversion": 2})
        pages = _get(url).get("query", {}).get("pages", [])
        return bool(pages) and "disambiguation" in (pages[0].get("pageprops") or {})
    except Exception:  # noqa: BLE001
        return False


def homonymes(titre, cle="wikipedia", limit=5):
    """Les differents sens listes par une page d'homonymie."""
    api, _nom = WIKIS[cle]
    try:
        url = api + "?" + urllib.parse.urlencode(
            {"action": "query", "prop": "links", "titles": titre,
             "pllimit": 40, "plnamespace": 0, "format": "json",
             "formatversion": 2})
        pages = _get(url).get("query", {}).get("pages", [])
        if not pages:
            return []
        liens = [l["title"] for l in (pages[0].get("links") or [])]
        return [t for t in liens if "homonymie" not in t.lower()][:limit]
    except Exception:  # noqa: BLE001
        return []


def page(titre, cle="wikipedia", phrases=2):
    """Ouvre une page precise (apres que l'utilisateur a choisi un sens)."""
    api, nom = WIKIS[cle]
    try:
        ex, _hom = _mw_extract(api, titre)
    except Exception:  # noqa: BLE001
        return None
    if not ex or len(ex) < 25:
        return None
    return _phrases(ex, phrases), f"{nom} — « {titre} »"


# ======================================================================
#  2. OPEN-METEO : la vraie meteo
# ======================================================================
CODES_METEO = {
    0: "ciel degage", 1: "plutot degage", 2: "partiellement nuageux",
    3: "couvert", 45: "brouillard", 48: "brouillard givrant",
    51: "bruine legere", 53: "bruine", 55: "bruine forte",
    61: "pluie legere", 63: "pluie", 65: "forte pluie",
    66: "pluie verglacante", 71: "neige legere", 73: "neige",
    75: "forte neige", 77: "grains de neige", 80: "averses",
    81: "averses", 82: "fortes averses", 85: "averses de neige",
    95: "orage", 96: "orage avec grele", 99: "orage violent",
}


def meteo(ville):
    g = _get("https://geocoding-api.open-meteo.com/v1/search?" +
             urllib.parse.urlencode({"name": ville, "count": 1,
                                     "language": "fr", "format": "json"}))
    res = g.get("results") or []
    if not res:
        return None
    r = res[0]
    f = _get("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(
        {"latitude": r["latitude"], "longitude": r["longitude"],
         "current": "temperature_2m,weather_code,wind_speed_10m",
         "daily": "temperature_2m_max,temperature_2m_min",
         "timezone": "auto", "forecast_days": 1}))
    cur = f.get("current", {})
    day = f.get("daily", {})
    code = int(cur.get("weather_code", 0))
    tmin = (day.get("temperature_2m_min") or [None])[0]
    tmax = (day.get("temperature_2m_max") or [None])[0]
    txt = (f"A {r.get('name')} ({r.get('country', '')}) il fait "
           f"{cur.get('temperature_2m')} C, {CODES_METEO.get(code, 'temps variable')}, "
           f"vent {cur.get('wind_speed_10m')} km/h.")
    if tmin is not None and tmax is not None:
        txt += f" Aujourd'hui : de {tmin} a {tmax} C."
    return txt, "Open-Meteo"


# ======================================================================
#  3. REST COUNTRIES : infos sur un pays
# ======================================================================
def pays(nom):
    url = ("https://restcountries.com/v3.1/name/" + urllib.parse.quote(nom) +
           "?fields=name,capital,population,currencies,languages,region,translations")
    d = _get(url)
    if not isinstance(d, list) or not d:
        return None
    c = d[0]
    fr = (c.get("translations", {}).get("fra", {}).get("common")
          or c.get("name", {}).get("common", nom))
    cap = ", ".join(c.get("capital") or []) or "inconnue"
    pop = c.get("population", 0)
    mon = ", ".join(v.get("name", "") for v in (c.get("currencies") or {}).values())
    lang = ", ".join((c.get("languages") or {}).values())
    txt = (f"{fr} : capitale {cap}, environ {pop:,} habitants".replace(",", " ") +
           f". Monnaie : {mon or 'inconnue'}. Langue(s) : {lang or 'inconnue'}. "
           f"Region : {c.get('region', '?')}.")
    return txt, "REST Countries"


# ======================================================================
#  4. DUCKDUCKGO : reponse courte (dernier recours)
# ======================================================================
def duckduckgo(query):
    d = _get("https://api.duckduckgo.com/?" + urllib.parse.urlencode(
        {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}))
    ab = (d.get("AbstractText") or "").strip()
    if len(ab) > 20:
        src = d.get("AbstractSource") or "DuckDuckGo"
        return _phrases(ab, 2), f"DuckDuckGo ({src})"
    for t in d.get("RelatedTopics", []):
        txt = (t.get("Text") or "").strip()
        if len(txt) > 30:
            return _phrases(txt, 2), "DuckDuckGo"
    return None


# ======================================================================
#  L'AIGUILLEUR : quelle source pour quelle question ?
# ======================================================================
def _essai(fn, *a):
    try:
        return fn(*a)
    except Exception:  # noqa: BLE001
        return None


def chercher(texte, mots=None):
    """Renvoie (reponse, source) ou None. Essaie les sources dans l'ordre."""
    t = _strip_accents(texte.lower())
    mots = mots or re.findall(r"[a-zà-ÿ0-9]{3,}", t)
    query = " ".join(mots) or texte.strip("? ")

    # --- METEO ---
    if re.search(r"\bmeteo\b|quel temps|temps qu'il fait|il pleut|fait-il beau", t):
        m = re.search(r"\b(?:a|de|en|sur|pour)\s+([a-zà-ÿ\-' ]{3,})$",
                      texte.strip(" ?!."), re.I)
        ville = (m.group(1) if m else (mots[-1] if mots else "")).strip()
        if ville:
            r = _essai(meteo, ville)
            if r:
                return r

    # --- PAYS ---
    if re.search(r"\bpays\b|capitale|habitants|monnaie|drapeau", t):
        cible = None
        m = re.search(r"(?:de|du|des|d'|en)\s+([a-zà-ÿ\-' ]{3,})$",
                      texte.strip(" ?!."), re.I)
        if m:
            cible = m.group(1).strip()
        elif mots:
            cible = mots[-1]
        if cible:
            r = _essai(pays, cible)
            if r:
                return r

    # --- DEFINITION (Wiktionnaire) ---
    if re.search(r"veut dire|signifie|definition|definis|c'est quoi le mot", t):
        mot = mots[-1] if mots else texte
        r = _essai(wiki, "wiktionnaire", mot, 3)
        if r:
            return r

    # --- WIKIS DE JEUX (Fandom) ---
    for cle, motscle in (("minecraft", ("minecraft", "creeper", "redstone",
                                        "enderman", "crafting", "mineur")),
                         ("pokemon", ("pokemon", "pikachu", "dracaufeu",
                                      "pokedex", "salameche", "bulbizarre")),
                         ("mario", ("mario", "luigi", "bowser", "yoshi",
                                    "peach", "toad")),
                         ("zelda", ("zelda", "link", "hyrule", "ganon"))):
        if any(k in t for k in motscle):
            r = _essai(wiki, cle, query)
            if r:
                return r

    # --- WIKIPEDIA (par defaut) ---
    r = _essai(wiki, "wikipedia", query)
    if r:
        return r

    # --- DUCKDUCKGO (dernier recours) ---
    return _essai(duckduckgo, query)
