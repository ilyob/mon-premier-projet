# -*- coding: utf-8 -*-
"""
REGLES — tout ce que l'IA peut CALCULER au lieu de l'apprendre par coeur.

Chaque fonction applique une vraie regle, donc ca marche sur des cas jamais
vus (comme la conjugaison) :

  - pluriel d'un nom          (cheval -> chevaux)
  - feminin d'un adjectif     (heureux -> heureuse)
  - nombre en lettres <-> chiffres  (42 <-> quarante-deux)
  - conversions d'unites      (3 km en m, 2 h en min, 20 C en F)
  - chiffres romains          (2026 <-> MMXXVI)
  - le contraire d'une phrase (negation)
  - palindrome, compter les lettres/voyelles, anagramme
  - nombres premiers, PGCD, PPCM, binaire

Utilise :  reponse = repondre("pluriel de cheval")
"""

import re
import math

VOY = "aeiouyàâäéèêëîïôöùûü"


def _sa(s):
    return s.translate(str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc"))


# ======================================================================
#  PLURIEL DES NOMS
# ======================================================================
PLU_OU_X = {"bijou", "caillou", "chou", "genou", "hibou", "joujou", "pou"}
PLU_AL_S = {"bal", "carnaval", "festival", "recital", "chacal", "regal",
            "cal", "narval", "aval", "banal", "fatal", "final", "natal", "naval"}
PLU_AIL_AUX = {"travail": "travaux", "corail": "coraux", "email": "emaux",
               "vitrail": "vitraux", "bail": "baux", "soupirail": "soupiraux"}
PLU_EXC = {"oeil": "yeux", "ciel": "cieux", "monsieur": "messieurs",
           "madame": "mesdames", "mademoiselle": "mesdemoiselles"}


def pluriel(mot):
    m = mot.strip().lower()
    k = _sa(m)
    if k in PLU_EXC:
        return PLU_EXC[k]
    if m[-1:] in ("s", "x", "z"):
        return m
    if m.endswith(("eau", "au", "eu")):
        return m if k in ("pneu", "bleu", "landau", "sarrau") else m + "x"
    if m.endswith("al"):
        return m + "s" if k in PLU_AL_S else m[:-2] + "aux"
    if m.endswith("ail"):
        return PLU_AIL_AUX.get(k, m + "s")
    if m.endswith("ou"):
        return m + "x" if k in PLU_OU_X else m + "s"
    return m + "s"


# ======================================================================
#  FEMININ DES ADJECTIFS
# ======================================================================
FEM_EXC = {
    "beau": "belle", "nouveau": "nouvelle", "vieux": "vieille", "fou": "folle",
    "mou": "molle", "blanc": "blanche", "franc": "franche", "sec": "seche",
    "public": "publique", "grec": "grecque", "turc": "turque", "long": "longue",
    "doux": "douce", "faux": "fausse", "roux": "rousse", "favori": "favorite",
    "gentil": "gentille", "nul": "nulle", "gros": "grosse", "bas": "basse",
    "epais": "epaisse", "gras": "grasse", "las": "lasse", "frais": "fraiche",
    "malin": "maligne", "benin": "benigne", "aigu": "aigue", "beau": "belle",
    "jumeau": "jumelle", "fou": "folle", "tiers": "tierce", "coi": "coite",
}
FEM_ETE = {"complet", "incomplet", "concret", "discret", "indiscret",
           "inquiet", "secret", "replet", "desuet"}


def feminin(adj):
    a = adj.strip().lower()
    k = _sa(a)
    if k in FEM_EXC:
        return FEM_EXC[k]
    if a.endswith("e") and not a.endswith(("gu",)):
        return a
    if a.endswith("eux"):
        return a[:-3] + "euse"
    if a.endswith("eur"):
        return a[:-3] + "euse"
    if a.endswith("teur"):
        return a[:-4] + "trice"
    if a.endswith("f"):
        return a[:-1] + "ve"
    if a.endswith("er"):
        return a[:-2] + "ère"
    if a.endswith("et"):
        return (a + "te") if k in FEM_ETE and False else (a[:-2] + "ète"
                                                          if k in FEM_ETE else a + "te")
    if a.endswith(("el", "eil", "ul")):
        return a + "le"
    if a.endswith("on"):
        return a + "ne"
    if a.endswith("ien"):
        return a + "ne"
    if a.endswith("as") or a.endswith("os") or a.endswith("eis"):
        return a + "se"
    return a + "e"


# ======================================================================
#  NOMBRE <-> LETTRES
# ======================================================================
UNITS = ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept",
         "huit", "neuf", "dix", "onze", "douze", "treize", "quatorze",
         "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"]
TENS = {20: "vingt", 30: "trente", 40: "quarante", 50: "cinquante", 60: "soixante"}


def _sous_cent(n):
    if n < 20:
        return UNITS[n]
    if n < 70:
        d, u = (n // 10) * 10, n % 10
        w = TENS[d]
        if u == 0:
            return w
        if u == 1:
            return w + " et un"
        return w + "-" + UNITS[u]
    if n < 80:
        u = n - 60
        if u == 11:
            return "soixante et onze"
        return "soixante-" + UNITS[u]
    u = n - 80
    if u == 0:
        return "quatre-vingts"
    return "quatre-vingt-" + UNITS[u]


def _sous_mille(n):
    if n < 100:
        return _sous_cent(n)
    c, r = n // 100, n % 100
    cent = "cent" if c == 1 else UNITS[c] + " cent"
    if r == 0:
        return cent + ("s" if c > 1 else "")
    return cent + " " + _sous_cent(r)


def nombre_en_lettres(n):
    n = int(n)
    if n == 0:
        return "zéro"
    neg, n = n < 0, abs(n)
    parts = []
    for div, name in ((10 ** 9, "milliard"), (10 ** 6, "million"), (1000, "mille")):
        if n >= div:
            q, n = n // div, n % div
            if name == "mille":
                parts.append(("" if q == 1 else _sous_mille(q) + " ") + "mille")
            else:
                parts.append(_sous_mille(q) + " " + name + ("s" if q > 1 else ""))
    if n > 0:
        parts.append(_sous_mille(n))
    res = " ".join(p.strip() for p in parts)
    return ("moins " + res) if neg else res


NUM_WORDS = {w: i for i, w in enumerate(UNITS)}
NUM_WORDS.update({"vingt": 20, "trente": 30, "quarante": 40, "cinquante": 50,
                  "soixante": 60, "cent": 100, "cents": 100, "mille": 1000,
                  "million": 10 ** 6, "millions": 10 ** 6, "milliard": 10 ** 9,
                  "milliards": 10 ** 9, "vingts": 20})


def lettres_en_nombre(texte):
    t = _sa(texte.lower())
    t = t.replace("quatre-vingt-dix", " 90 ").replace("quatre-vingts", " 80 ")
    t = t.replace("quatre-vingt", " 80 ")
    toks = re.split(r"[\s-]+", t)
    total, cur, ok = 0, 0, False
    for w in toks:
        if w in ("", "et"):
            continue
        if w.isdigit():
            v = int(w)
        elif w in NUM_WORDS:
            v = NUM_WORDS[w]
        else:
            continue                     # on ignore les mots hors-nombre
        ok = True
        if v == 100:
            cur = (cur or 1) * 100
        elif v >= 1000:
            cur = (cur or 1) * v
            total += cur
            cur = 0
        else:
            cur += v
    return (total + cur) if ok else None


# ======================================================================
#  CONVERSIONS D'UNITES
# ======================================================================
LONG = {"km": 1000, "hm": 100, "dam": 10, "m": 1, "dm": .1, "cm": .01,
        "mm": .001, "metre": 1, "metres": 1, "kilometre": 1000,
        "kilometres": 1000, "centimetre": .01, "centimetres": .01,
        "millimetre": .001, "millimetres": .001}
MASSE = {"t": 1e6, "tonne": 1e6, "tonnes": 1e6, "kg": 1000, "hg": 100,
         "dag": 10, "g": 1, "dg": .1, "cg": .01, "mg": .001, "gramme": 1,
         "grammes": 1, "kilo": 1000, "kilos": 1000, "kilogramme": 1000,
         "kilogrammes": 1000}
TEMPS = {"j": 86400, "jour": 86400, "jours": 86400, "h": 3600, "heure": 3600,
         "heures": 3600, "min": 60, "minute": 60, "minutes": 60, "s": 1,
         "seconde": 1, "secondes": 1}
FAMILLES = [LONG, MASSE, TEMPS]


def _fmt(x):
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return str(round(x, 4))


def conversion(texte):
    t = _sa(texte.lower())
    m = re.search(r"(-?\d+[.,]?\d*)\s*([a-z]+)\s+(?:en|vers)\s+([a-z]+)", t)
    if not m:
        return None
    val = float(m.group(1).replace(",", "."))
    u1, u2 = m.group(2), m.group(3)

    # temperatures
    TEMP = {"celsius": "c", "c": "c", "fahrenheit": "f", "f": "f",
            "kelvin": "k", "k": "k"}
    if u1 in TEMP and u2 in TEMP:
        a, b = TEMP[u1], TEMP[u2]
        c = val if a == "c" else (val - 32) * 5 / 9 if a == "f" else val - 273.15
        r = c if b == "c" else c * 9 / 5 + 32 if b == "f" else c + 273.15
        return f"{_fmt(val)} {u1} = {_fmt(r)} {u2}"

    for fam in FAMILLES:
        if u1 in fam and u2 in fam:
            r = val * fam[u1] / fam[u2]
            return f"{_fmt(val)} {u1} = {_fmt(r)} {u2}"
    return None


# ======================================================================
#  CHIFFRES ROMAINS
# ======================================================================
ROM = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"),
       (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"),
       (4, "IV"), (1, "I")]


def vers_romain(n):
    n = int(n)
    if not (0 < n < 4000):
        return None
    out = ""
    for v, s in ROM:
        while n >= v:
            out += s
            n -= v
    return out


def depuis_romain(s):
    s = s.upper().strip()
    if not re.fullmatch(r"[IVXLCDM]+", s):
        return None
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total, prev = 0, 0
    for ch in reversed(s):
        v = vals[ch]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total if vers_romain(total) == s else None


# ======================================================================
#  LE CONTRAIRE (negation d'une phrase)
# ======================================================================
NEG_VERB = {"est": "n'est pas", "sont": "ne sont pas", "es": "n'es pas",
            "suis": "ne suis pas", "sommes": "ne sommes pas", "etes": "n'etes pas",
            "a": "n'a pas", "as": "n'as pas", "ai": "n'ai pas", "ont": "n'ont pas",
            "avons": "n'avons pas", "avez": "n'avez pas", "peux": "ne peux pas",
            "peut": "ne peut pas", "veux": "ne veux pas", "veut": "ne veut pas",
            "fais": "ne fais pas", "fait": "ne fait pas", "vais": "ne vais pas",
            "va": "ne va pas", "aime": "n'aime pas", "aimes": "n'aimes pas"}
NEG_TOK = {"ne", "n'", "pas", "plus", "jamais", "rien", "personne"}
ELID = {"je": "j'", "ne": "n'", "ce": "c'", "de": "d'", "le": "l'", "la": "l'"}


def contraire(phrase):
    toks = re.findall(r"[a-zà-ÿ]+'|[a-zà-ÿ]+|\S", phrase.lower())
    if any(_sa(w) in NEG_TOK for w in toks):        # deja negatif -> affirmatif
        kept = [w for w in toks if _sa(w) not in NEG_TOK]
        s = " ".join(kept)
        s = re.sub(r"\b(je|ne|de|ce|le|la)\s+(?=[" + VOY + "])",
                   lambda m: ELID[m.group(1)], s)
        return re.sub(r"\s+([.,!?])", r"\1", s).strip()
    out, done = [], False
    for w in toks:
        b = _sa(w)
        if not done and b in NEG_VERB:
            out.append(NEG_VERB[b])
            done = True
        else:
            out.append(w)
    if not done:
        return "il est faux de dire que " + phrase.strip()
    s = " ".join(out)
    return re.sub(r"\bje n'", "je n'", s).strip()


# ======================================================================
#  LETTRES : palindrome, comptage, anagramme
# ======================================================================
def palindrome(mot):
    m = re.sub(r"[^a-zà-ÿ]", "", _sa(mot.lower()))
    return m == m[::-1] and len(m) > 1


def compte_lettres(mot):
    return len(re.findall(r"[a-zà-ÿ]", _sa(mot.lower())))


def compte_voyelles(mot):
    return len(re.findall(r"[aeiouy]", _sa(mot.lower())))


def anagramme(a, b):
    ca = sorted(re.sub(r"[^a-z]", "", _sa(a.lower())))
    cb = sorted(re.sub(r"[^a-z]", "", _sa(b.lower())))
    return ca == cb and ca != []


# ======================================================================
#  NOMBRES : premier, pgcd, ppcm, binaire
# ======================================================================
def est_premier(n):
    n = int(n)
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n ** 0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


# ======================================================================
#  L'AIGUILLEUR
# ======================================================================
def _nombre(t):
    m = re.search(r"-?\d+", t)
    return int(m.group()) if m else None


def repondre(texte):
    t = _sa(texte.lower())

    m = re.search(r"pluriel de\s+([a-zà-ÿ-]+)", t)
    if m:
        return f"Le pluriel de « {m.group(1)} » est « {pluriel(m.group(1))} »."
    m = re.search(r"feminin de\s+([a-zà-ÿ-]+)", t)
    if m:
        return f"Le feminin de « {m.group(1)} » est « {feminin(m.group(1))} »."

    # nombre -> lettres
    if re.search(r"en lettres|ecris? en toutes lettres", t):
        n = _nombre(texte)
        if n is not None:
            return f"{n} s'ecrit : {nombre_en_lettres(n)}."
    # lettres -> nombre
    if re.search(r"en chiffres?|en nombre", t) and re.search(
            r"\b(un|deux|trois|dix|vingt|cent|mille|quatre|cinq|six|sept|huit|"
            r"neuf|onze|douze|treize|quatorze|quinze|seize|trente|quarante|"
            r"cinquante|soixante)\b", t):
        expr = re.sub(r"en chiffres?|en nombre|combien font|ecris?|c'est|"
                      r"convertis|[:?]", " ", t)
        v = lettres_en_nombre(expr)
        if v is not None:
            return f"En chiffres, ca fait : {v}."

    # conversions
    conv = conversion(texte)
    if conv:
        return conv

    # chiffres romains
    if "romain" in t:
        n = _nombre(texte)
        if n is not None:
            r = vers_romain(n)
            return f"{n} en chiffres romains : {r}." if r else \
                "Je gere les nombres romains de 1 a 3999 !"
        mr = re.search(r"\b([ivxlcdm]{1,15})\b", t)
        if mr:
            r = depuis_romain(mr.group(1))
            if r:
                return f"{mr.group(1).upper()} vaut {r}."
    # romain -> arabe detecte par les MAJUSCULES (ex. « MMXXVI en chiffre »)
    mr2 = re.search(r"\b([IVXLCDM]{2,})\b", texte)
    if mr2:
        r = depuis_romain(mr2.group(1))
        if r:
            return f"{mr2.group(1)} vaut {r} en chiffres normaux."

    # le contraire
    m = re.search(r"(?:le )?contraire de[ :]+(.+)", texte, re.I)
    if m and len(m.group(1).split()) >= 2:
        return f"Le contraire : « {contraire(m.group(1))} »."

    # palindrome / lettres
    m = re.search(r"palindrome.*?\b([a-zà-ÿ]{2,})\b|\b([a-zà-ÿ]{2,})\b.*palindrome", t)
    if "palindrome" in t and m:
        mot = m.group(1) or m.group(2)
        return (f"« {mot} » est un palindrome !" if palindrome(mot)
                else f"Non, « {mot} » n'est pas un palindrome.")
    mc = re.search(r"combien de (lettres|voyelles)", t)
    if mc:
        stop = {"combien", "lettres", "voyelles", "dans", "mot", "les", "des",
                "dans", "dan", "que", "quel"}
        mots = [w for w in re.findall(r"[a-zà-ÿ]{2,}", t) if w not in stop]
        if mots:
            w = mots[-1]
            if mc.group(1) == "lettres":
                return f"« {w} » a {compte_lettres(w)} lettres."
            return f"« {w} » a {compte_voyelles(w)} voyelles."
    if "anagramme" in t:
        m = re.search(r"([a-zà-ÿ]{2,})\s+et\s+([a-zà-ÿ]{2,})", t)
        if m:
            ok = anagramme(m.group(1), m.group(2))
            return (f"Oui, « {m.group(1)} » et « {m.group(2)} » sont des "
                    f"anagrammes !" if ok else
                    f"Non, « {m.group(1)} » et « {m.group(2)} » ne sont pas "
                    "des anagrammes.")

    # nombres premiers / pgcd / ppcm / binaire
    if "premier" in t and "facteur" not in t and "decompos" not in t:
        n = _nombre(texte)
        if n is not None:
            return (f"Oui, {n} est un nombre premier." if est_premier(n)
                    else f"Non, {n} n'est pas premier.")
    m = re.search(r"(?:pgcd|plus grand commun diviseur).*?(-?\d+).*?(-?\d+)", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return f"Le PGCD de {a} et {b} est {math.gcd(a, b)}."
    m = re.search(r"(?:ppcm|plus petit commun multiple).*?(\d+).*?(\d+)", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return f"Le PPCM de {a} et {b} est {a * b // math.gcd(a, b)}."
    if "binaire" in t:
        m = re.search(r"\b([01]{2,})\b", t)          # binaire -> decimal
        if m and re.search(r"en decimal|en chiffre|vaut|combien", t):
            return f"{m.group(1)} en binaire vaut {int(m.group(1), 2)}."
        n = _nombre(texte)                            # decimal -> binaire
        if n is not None and n >= 0:
            return f"{n} en binaire s'ecrit : {bin(n)[2:]}."

    return None
