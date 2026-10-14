# -*- coding: utf-8 -*-
"""
REGLES_PLUS — encore plus de regles que l'IA CALCULE (jamais par coeur).

MATHS      : puissance, racine, factorielle, pourcentage, moyenne/somme/
             mediane/min/max, diviseurs, facteurs premiers, table de X,
             pair/impair, arrondi, Fibonacci, PGCD deja ailleurs,
             geometrie (aire/perimetre/Pythagore), fraction simplifiee,
             bases (hexadecimal, octal)
LETTRES    : ordre alphabetique, lettre suivante/precedente, position,
             ecrire a l'envers, majuscules/minuscules, rimes, compter les
             mots, code de Cesar, code Morse, alphabet OTAN
DATES      : jour de la semaine, annee bissextile, jours d'un mois, age,
             jours entre deux dates

Utilise :  reponse = repondre("table de 7")
"""

import re
import math
import calendar
from datetime import date

MOIS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5,
        "juin": 6, "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10,
        "novembre": 11, "decembre": 12}
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS_NOM = ["", "janvier", "fevrier", "mars", "avril", "mai", "juin",
            "juillet", "aout", "septembre", "octobre", "novembre", "decembre"]


def _sa(s):
    return s.translate(str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc"))


def _fmt(x):
    if isinstance(x, float) and abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    if isinstance(x, float):
        return str(round(x, 4))
    return str(x)


def _nums(t):
    return [float(n.replace(",", ".")) for n in re.findall(r"-?\d+[.,]?\d*", t)]


def _ints(t):
    return [int(n) for n in re.findall(r"-?\d+", t)]


# ======================================================================
#  MATHS
# ======================================================================
def diviseurs(n):
    n = abs(int(n))
    return [i for i in range(1, n + 1) if n % i == 0]


def facteurs_premiers(n):
    n = abs(int(n))
    out, d = [], 2
    while d * d <= n:
        while n % d == 0:
            out.append(d)
            n //= d
        d += 1
    if n > 1:
        out.append(n)
    return out


def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


# ======================================================================
#  LETTRES : Cesar, Morse, OTAN
# ======================================================================
def cesar(texte, dec):
    out = []
    for ch in texte:
        if "a" <= ch <= "z":
            out.append(chr((ord(ch) - 97 + dec) % 26 + 97))
        elif "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + dec) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)


MORSE = {"a": ".-", "b": "-...", "c": "-.-.", "d": "-..", "e": ".", "f": "..-.",
         "g": "--.", "h": "....", "i": "..", "j": ".---", "k": "-.-",
         "l": ".-..", "m": "--", "n": "-.", "o": "---", "p": ".--.",
         "q": "--.-", "r": ".-.", "s": "...", "t": "-", "u": "..-", "v": "...-",
         "w": ".--", "x": "-..-", "y": "-.--", "z": "--..", "0": "-----",
         "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....",
         "6": "-....", "7": "--...", "8": "---..", "9": "----."}
MORSE_INV = {v: k for k, v in MORSE.items()}

OTAN = {"a": "Alpha", "b": "Bravo", "c": "Charlie", "d": "Delta", "e": "Echo",
        "f": "Foxtrot", "g": "Golf", "h": "Hotel", "i": "India", "j": "Juliett",
        "k": "Kilo", "l": "Lima", "m": "Mike", "n": "November", "o": "Oscar",
        "p": "Papa", "q": "Quebec", "r": "Romeo", "s": "Sierra", "t": "Tango",
        "u": "Uniform", "v": "Victor", "w": "Whiskey", "x": "Xray",
        "y": "Yankee", "z": "Zulu"}


def en_morse(texte):
    out = []
    for mot in _sa(texte.lower()).split():
        out.append(" ".join(MORSE[c] for c in mot if c in MORSE))
    return " / ".join(o for o in out if o)


def de_morse(code):
    mots = code.strip().split(" / ")
    res = []
    for mot in mots:
        res.append("".join(MORSE_INV.get(s, "?") for s in mot.split()))
    return " ".join(res)


def rime(a, b):
    a, b = _sa(a.lower()), _sa(b.lower())
    for n in (3, 2):
        if len(a) >= n and len(b) >= n and a[-n:] == b[-n:]:
            return True
    return a[-1:] == b[-1:] and a[-1:] in "aeiouy"


# ======================================================================
#  DATES
# ======================================================================
def _parse_date(t):
    m = re.search(r"(\d{1,2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{2,4})", t)
    if m:
        j, mo, an = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if an < 100:
            an += 2000
        try:
            return date(an, mo, j)
        except ValueError:
            return None
    m = re.search(r"(\d{1,2})\s+([a-zà-ÿ]+)\s+(\d{4})", t)
    if m and _sa(m.group(2)) in MOIS:
        try:
            return date(int(m.group(3)), MOIS[_sa(m.group(2))], int(m.group(1)))
        except ValueError:
            return None
    return None


def jours_avant_anniversaire(naissance):
    """Combien de jours avant le prochain anniversaire (date de naissance donnee)."""
    au = date.today()

    def _anniv(annee):
        try:
            return date(annee, naissance.month, naissance.day)
        except ValueError:               # 29 fevrier -> 1er mars
            return date(annee, 3, 1)

    prochain = _anniv(au.year)
    if prochain < au:
        prochain = _anniv(au.year + 1)
    jours = (prochain - au).days
    age = prochain.year - naissance.year
    jour_sem = JOURS[prochain.weekday()]
    if jours == 0:
        return (f"C'est AUJOURD'HUI ! Joyeux anniversaire, tu as {age} ans ! 🎉")
    quand = f"le {jour_sem} {prochain.day} {MOIS_NOM[prochain.month]} {prochain.year}"
    if jours == 1:
        return f"C'est DEMAIN ({quand}) ! Tu vas avoir {age} ans. 🎂"
    sem = jours // 7
    detail = f" (environ {sem} semaines)" if sem >= 2 else ""
    return (f"Ton prochain anniversaire tombe {quand}, dans {jours} jours{detail}. "
            f"Tu auras {age} ans ! 🎂")


# ======================================================================
#  L'AIGUILLEUR
# ======================================================================
def repondre(texte):
    t = _sa(texte.lower())
    nums = _nums(t)
    ints = _ints(t)

    # ---------- DATES ----------
    if "bissextile" in t and ints:
        a = [n for n in ints if n > 31][0] if any(n > 31 for n in ints) else ints[-1]
        bis = a % 4 == 0 and (a % 100 != 0 or a % 400 == 0)
        etat = "est" if bis else "n'est pas"
        return f"{a} {etat} une annee bissextile."
    if ("jour" in t and ("quel jour" in t or "tombe" in t or "quel est le jour" in t)):
        d = _parse_date(t)
        if d:
            return f"Le {d.day:02d}/{d.month:02d}/{d.year} est un {JOURS[d.weekday()]}."
    if ("combien de jours" in t or "nombre de jours" in t) and " entre " in t:
        ds = re.findall(r"\d{1,2}\s*[/\-.]\s*\d{1,2}\s*[/\-.]\s*\d{2,4}", t)
        if len(ds) >= 2:
            d1, d2 = _parse_date(ds[0]), _parse_date(ds[1])
            if d1 and d2:
                return f"Il y a {abs((d2 - d1).days)} jours entre ces deux dates."
    if "combien de jours" in t and any(mo in t for mo in MOIS) and ints:
        for nom, mo in MOIS.items():
            if nom in t:
                an = next((n for n in ints if n > 31), date.today().year)
                return (f"Le mois de {nom} {an} compte "
                        f"{calendar.monthrange(an, mo)[1]} jours.")
    if ("age" in t or "quel age" in t) and re.search(r"\d{1,2}\s*[/\-.]\s*\d", t):
        d = _parse_date(t)
        if d:
            au = date.today()
            ans = au.year - d.year - ((au.month, au.day) < (d.month, d.day))
            return f"Cette personne a {ans} ans (nee le {d.day:02d}/{d.month:02d}/{d.year})."

    # ---------- BASES ----------
    hex_tok = re.search(r"\b([0-9a-f]*[a-f][0-9a-f]*)\b", t)  # token avec une lettre a-f
    veut_dec = re.search(r"en decimal|vaut|en chiffre|en nombre", t)
    if "hexadecimal" in t or "hexa" in t or (hex_tok and veut_dec
                                             and len(hex_tok.group(1)) >= 2):
        if veut_dec and hex_tok:
            return (f"{hex_tok.group(1).upper()} en hexadecimal vaut "
                    f"{int(hex_tok.group(1), 16)}.")
        if ints:
            return f"{ints[-1]} en hexadecimal s'ecrit : {format(abs(ints[-1]), 'X')}."
    if "octal" in t:
        if re.search(r"en decimal|vaut", t):
            mo = re.search(r"\b([0-7]{1,10})\b", t)
            if mo:
                return f"{mo.group(1)} en octal vaut {int(mo.group(1), 8)}."
        if ints:
            return f"{ints[-1]} en octal s'ecrit : {format(abs(ints[-1]), 'o')}."

    # ---------- LETTRES ----------
    if "morse" in t:
        mc = re.search(r"[.\-/ ]{3,}", texte)
        if ("decode" in t or "traduis" in t or "veut dire" in t) and mc:
            return f"En morse, ca dit : {de_morse(mc.group(0))}"
        mm = re.search(r"morse[ :]+(?:le mot |la phrase |de )?(.+)", texte, re.I)
        if not mm:
            mm = re.search(r"(?:ecris|code|traduis|met[s]?)\s+(.+?)\s+en morse", texte, re.I)
        if mm:
            return f"En morse : {en_morse(mm.group(1))}"
    if "otan" in t or "alphabet radio" in t or "epelle" in t:
        mm = re.search(r"(?:epelle|otan|radio)[^a-zà-ÿ]*([a-zà-ÿ]+)", texte, re.I)
        if mm:
            mot = _sa(mm.group(1).lower())
            return mm.group(1) + " : " + ", ".join(OTAN[c] for c in mot if c in OTAN)
    if "cesar" in t or "cesare" in t:
        d = next((n for n in ints), 3)
        mm = re.search(r"(?:code|chiffre|decode|dechiffre)\s+(.+?)\s+"
                       r"(?:avec|de|en)?\s*cesar", texte, re.I)
        if not mm:
            mm = re.search(r"cesar[^a-zà-ÿ0-9]*(?:de\s*\d+)?\s*[:]?\s*(.+)", texte, re.I)
        if mm:
            phrase = re.sub(r"\bde\s*\d+\b|\bdecalage\b|\bdecale\b", "", mm.group(1)).strip()
            if "decode" in t or "dechiffre" in t:
                return f"Decode (Cesar -{d}) : {cesar(phrase, -d)}"
            return f"Code Cesar (+{d}) : {cesar(phrase, d)}"
    if "ordre alphabetique" in t or "ordre alphabetiques" in t or "range" in t and "alphab" in t:
        part = re.split(r"[:]", texte, 1)
        src = part[1] if len(part) > 1 else texte
        mots = re.findall(r"[a-zà-ÿ]{2,}", src.lower())
        mots = [m for m in mots if m not in ("range", "ordre", "alphabetique",
                                             "dans", "les", "mots", "par")]
        if len(mots) >= 2:
            return "Dans l'ordre : " + ", ".join(sorted(mots, key=_sa))
    m = re.search(r"lettre (?:vient |qui vient )?(apres|avant|suit|precede)\s+([a-z])", t)
    if m:
        c = m.group(2)
        if m.group(1) in ("apres", "suit"):
            return f"Apres « {c} » vient « {chr(ord(c) + 1)} »." if c < "z" \
                else "« z » est la derniere lettre !"
        return f"Avant « {c} » vient « {chr(ord(c) - 1)} »." if c > "a" \
            else "« a » est la premiere lettre !"
    m = re.search(r"position de la lettre\s+([a-z])|quelle position.*\b([a-z])\b", t)
    if m and "lettre" in t:
        c = m.group(1) or m.group(2)
        return f"« {c} » est la {ord(c) - 96}e lettre de l'alphabet."
    if "envers" in t or "inverse" in t or "renverse" in t:
        skip = ("ecris", "ecrire", "mot", "phrase", "le", "la", "les", "met",
                "mets", "affiche")
        m = re.search(r"([a-zà-ÿ]{2,})\s+a\s*l['\s]?envers", t)
        if not m:
            m = re.search(r"(?:envers|inverse|renverse)\s*(?:le mot|la phrase)?"
                          r"\s*[:]?\s*([a-zà-ÿ]{2,})", t)
        if m and m.group(1) not in skip:
            mot = m.group(1)
            return f"« {mot} » a l'envers : « {mot[::-1]} »."
    m = re.search(r"en majuscules?\s*[:]?\s*(.+)|(.+?)\s+en majuscules?", texte, re.I)
    if m and "majuscule" in t:
        return (m.group(1) or m.group(2)).strip().upper()
    m = re.search(r"en minuscules?\s*[:]?\s*(.+)|(.+?)\s+en minuscules?", texte, re.I)
    if m and "minuscule" in t:
        return (m.group(1) or m.group(2)).strip().lower()
    if "rime" in t:
        m = re.search(r"([a-zà-ÿ]{2,})\s+(?:rime avec|et)\s+([a-zà-ÿ]{2,})", t)
        if m:
            return (f"Oui, « {m.group(1)} » rime avec « {m.group(2)} » !"
                    if rime(m.group(1), m.group(2))
                    else f"Non, « {m.group(1)} » ne rime pas avec « {m.group(2)} ».")
    if "combien de mots" in t:
        m = re.search(r"phrase\s*[:]?\s*(.+)|mots dans\s*[:]?\s*(.+)", texte, re.I)
        src = (m.group(1) or m.group(2)) if m else ""
        n = len(re.findall(r"[a-zà-ÿ]+", src))
        if n:
            return f"Il y a {n} mots dans cette phrase."

    # ---------- MATHS ----------
    m = re.search(r"(-?\d+)\s*(?:puissance|exposant|\^|\*\*)\s*(\d+)", t)
    if m:
        a, e = int(m.group(1)), int(m.group(2))
        if e <= 300:
            return f"{a} puissance {e} = {a ** e}."
    if "racine" in t and ints:
        n = abs(ints[-1])
        r = math.isqrt(n)
        if r * r == n:
            return f"La racine carree de {n} est {r}."
        return f"La racine carree de {n} vaut environ {round(math.sqrt(n), 4)}."
    if ("factorielle" in t or re.search(r"\d+\s*!", t)) and ints:
        n = abs(ints[-1])
        if n <= 900:
            return f"{n}! (factorielle de {n}) = {math.factorial(n)}."
    m = re.search(r"(-?\d+[.,]?\d*)\s*(?:%|pour ?cent)\s*(?:de|sur)\s*(-?\d+[.,]?\d*)", t)
    if m:
        p = float(m.group(1).replace(",", ".")) / 100
        v = float(m.group(2).replace(",", "."))
        return f"{m.group(1)}% de {m.group(2)} = {_fmt(p * v)}."
    if "moyenne" in t and len(nums) >= 2:
        return f"La moyenne de {', '.join(_fmt(x) for x in nums)} est {_fmt(sum(nums) / len(nums))}."
    if ("mediane" in t) and len(nums) >= 2:
        s = sorted(nums)
        n = len(s)
        med = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
        return f"La mediane est {_fmt(med)}."
    if re.search(r"\bsomme\b|\btotal\b|addition de", t) and len(nums) >= 2:
        return f"La somme est {_fmt(sum(nums))}."
    if re.search(r"plus grand|maximum|le max\b", t) and len(nums) >= 2:
        return f"Le plus grand est {_fmt(max(nums))}."
    if re.search(r"plus petit|minimum|le min\b", t) and len(nums) >= 2:
        return f"Le plus petit est {_fmt(min(nums))}."
    if ("diviseurs" in t) and ints:
        n = abs(ints[-1])
        d = diviseurs(n)
        return f"Les diviseurs de {n} sont : {', '.join(map(str, d))}."
    if ("facteurs premiers" in t or "decompose" in t or "decomposition" in t) and ints:
        n = abs(ints[-1])
        f = facteurs_premiers(n)
        return f"{n} = {' x '.join(map(str, f))} (facteurs premiers)."
    if re.search(r"table (?:de multiplication )?de\s+-?\d+", t):
        n = ints[-1]
        lignes = [f"{n} x {i} = {n * i}" for i in range(1, 11)]
        return f"Table de {n} :\n" + "\n".join(lignes)
    m = re.search(r"(-?\d+)\s+est[- ]?(?:il|elle)?\s+(pair|impair)", t)
    if m:
        n = int(m.group(1))
        pair = n % 2 == 0
        return f"{n} est un nombre {'pair' if pair else 'impair'}."
    if ("arrondi" in t or "arrondis" in t) and nums:
        x = nums[-1]
        return f"{_fmt(x)} arrondi a l'unite = {int(round(x))}."
    if "fibonacci" in t and ints:
        n = abs(ints[-1])
        if n <= 500:
            suite = [str(fibonacci(i)) for i in range(1, min(n, 15) + 1)]
            if "suite" in t or "premiers" in t:
                return f"Les {min(n, 15)} premiers Fibonacci : {', '.join(suite)}."
            return f"Le {n}e nombre de Fibonacci est {fibonacci(n)}."
    if ("hypotenuse" in t or "pythagore" in t) and len(nums) >= 2:
        a, b = nums[0], nums[1]
        return f"L'hypotenuse vaut racine de ({_fmt(a)}²+{_fmt(b)}²) = {_fmt(math.hypot(a, b))}."
    if "aire" in t:
        if "cercle" in t and nums:
            r = nums[-1]
            return f"Aire d'un cercle de rayon {_fmt(r)} = {_fmt(math.pi * r * r)} (π×r²)."
        if "carre" in t and nums:
            c = nums[-1]
            return f"Aire d'un carre de cote {_fmt(c)} = {_fmt(c * c)}."
        if "rectangle" in t and len(nums) >= 2:
            return f"Aire d'un rectangle {_fmt(nums[0])}×{_fmt(nums[1])} = {_fmt(nums[0] * nums[1])}."
        if "triangle" in t and len(nums) >= 2:
            return f"Aire d'un triangle (base {_fmt(nums[0])}, hauteur {_fmt(nums[1])}) = {_fmt(nums[0] * nums[1] / 2)}."
    if "perimetre" in t:
        if "cercle" in t and nums:
            r = nums[-1]
            return f"Perimetre (circonference) d'un cercle de rayon {_fmt(r)} = {_fmt(2 * math.pi * r)} (2×π×r)."
        if "carre" in t and nums:
            return f"Perimetre d'un carre de cote {_fmt(nums[-1])} = {_fmt(nums[-1] * 4)}."
        if "rectangle" in t and len(nums) >= 2:
            return f"Perimetre d'un rectangle {_fmt(nums[0])}×{_fmt(nums[1])} = {_fmt(2 * (nums[0] + nums[1]))}."
    m = re.search(r"simplifie\s+(\d+)\s*/\s*(\d+)", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        g = math.gcd(a, b)
        return f"{a}/{b} se simplifie en {a // g}/{b // g}." if g > 1 \
            else f"{a}/{b} est deja irreductible."

    return None
