# -*- coding: utf-8 -*-
"""
RAISONNEMENT MULTI-ETAPES — enchaine plusieurs regles dans une seule question.

Exemples :
  - « le double de la racine de 144 »        -> 2 x 12 = 24
  - « la moitie de 3 fois 8 »                 -> (3x8)/2 = 12
  - « combien de minutes dans 3 heures et quart » -> 195
  - « combien de secondes dans 2 minutes et demie » -> 150
  - « quel jour serai-je dans 100 jours »     -> un vendredi (date + jour)
  - « quelle heure dans 90 minutes »          -> calcule l'heure

Idee : on decompose la phrase, on evalue chaque morceau (qui peut lui-meme
etre une operation), puis on combine. C'est ca, raisonner en plusieurs etapes.
"""

import re
import math
from datetime import date, timedelta, datetime

try:
    import regles          # pour les nombres en lettres -> chiffres
except Exception:  # noqa: BLE001
    regles = None


def _sa(s):
    return s.translate(str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc"))


def _fmt(x):
    if isinstance(x, float) and abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    if isinstance(x, float):
        return str(round(x, 4))
    return str(x)


OPS = {"plus": "+", "moins": "-", "fois": "*", "multiplie par": "*",
       "divise par": "/", "sur": "/"}


def _valeur(s):
    """Evalue un morceau qui peut etre un nombre, un nombre en lettres, une
    operation, une racine, un double/moitie/carre... (recursif)."""
    if s is None:
        return None
    s = s.strip(" ?.!")
    if not s:
        return None

    # double / triple / moitie / carre / cube de X
    m = re.match(r"(?:le |la |du )?(double|triple|quadruple|moitie|tiers|quart|"
                 r"carre|cube)\s+(?:de\s+|d')(.+)", s)
    if m:
        v = _valeur(m.group(2))
        if v is None:
            return None
        return {"double": 2 * v, "triple": 3 * v, "quadruple": 4 * v,
                "moitie": v / 2, "tiers": v / 3, "quart": v / 4,
                "carre": v * v, "cube": v * v * v}[m.group(1)]

    # racine (carree) de X
    m = re.match(r"(?:la )?racine\s+(?:carree\s+)?(?:de\s+|d')(.+)", s)
    if m:
        v = _valeur(m.group(1))
        if v is None or v < 0:
            return None
        r = math.isqrt(int(v)) if float(v).is_integer() else math.sqrt(v)
        return r if (isinstance(r, int) and r * r == int(v)) else math.sqrt(v)

    # operation en toutes lettres : « 3 fois 8 », « 10 plus 5 »
    for mot, op in OPS.items():
        m = re.match(r"(.+?)\s+" + mot + r"\s+(.+)", s)
        if m:
            a, b = _valeur(m.group(1)), _valeur(m.group(2))
            if a is not None and b is not None:
                try:
                    return eval(f"{a}{op}{b}", {"__builtins__": {}})  # noqa: S307
                except Exception:  # noqa: BLE001
                    return None

    # expression arithmetique directe : « 3*8 », « 12+4 »
    if re.fullmatch(r"[0-9\.\s\+\-\*/x\(\)]+", s):
        try:
            return eval(s.replace("x", "*"), {"__builtins__": {}})  # noqa: S307
        except Exception:  # noqa: BLE001
            pass

    # un nombre (chiffres)
    m = re.fullmatch(r"-?\d+(?:[.,]\d+)?", s)
    if m:
        return float(s.replace(",", "."))

    # un nombre ecrit en lettres (« quarante-deux »)
    if regles is not None:
        v = regles.lettres_en_nombre(s)
        if v is not None:
            return float(v)
    return None


# minutes contenues dans « X heures (et quart / et demie / ...) »
FRAC = {"et quart": 0.25, "et demie": 0.5, "et demi": 0.5,
        "et trois quarts": 0.75, "moins le quart": -0.25}


def _duree_en(texte):
    """« combien de minutes dans 3 heures et quart » -> 195."""
    m = re.search(r"combien de (minutes|secondes|heures)\s+(?:dans|pour|font)\s+"
                  r"(.+)", texte)
    if not m:
        return None
    cible, reste = m.group(1), m.group(2)
    # valeur en heures / minutes / secondes trouvee dans « reste »
    mh = re.search(r"(\d+(?:[.,]\d+)?)\s*(heures?|h|minutes?|min|secondes?|s)\b",
                   reste)
    if not mh:
        return None
    val = float(mh.group(1).replace(",", "."))
    unite = mh.group(2)
    for mot, f in FRAC.items():
        if mot in reste:
            val += f
            break
    # tout en secondes
    if unite.startswith("h"):
        sec = val * 3600
    elif unite.startswith("min") or unite == "min" or unite.startswith("m"):
        sec = val * 60
    else:
        sec = val
    res = {"heures": sec / 3600, "minutes": sec / 60, "secondes": sec}[cible]
    return f"{_fmt(res)} {cible}."


def _date_relative(texte):
    """« quel jour serai-je dans 100 jours », « dans 3 semaines »."""
    m = re.search(r"dans\s+(\d+)\s+(jours?|semaines?|mois|ans?|annees?)", texte)
    if not m or ("jour" not in texte and "date" not in texte and "quand" not in texte):
        return None
    n, unite = int(m.group(1)), m.group(2)
    jours = {"jour": 1, "jours": 1, "semaine": 7, "semaines": 7, "mois": 30,
             "an": 365, "ans": 365, "annee": 365, "annees": 365}[unite]
    cible = date.today() + timedelta(days=n * jours)
    noms = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    mois = ["", "janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
            "aout", "septembre", "octobre", "novembre", "decembre"]
    return (f"Ce sera un {noms[cible.weekday()]} "
            f"({cible.day} {mois[cible.month]} {cible.year}).")


def _probleme(texte):
    """Petit probleme en langage naturel : « j'ai 3 pommes, j'en achete 5 »."""
    t = _sa(texte.lower())
    if not re.search(r"combien|en tout|au total|il (?:me )?reste|ensemble", t):
        return None
    nums = [int(n) for n in re.findall(r"\d+", t)]
    if len(nums) < 2:
        return None

    # multiplication : « 4 paquets de 6 », « 3 fois 8 bonbons », « chaque ... »
    if re.search(r"\bfois\b|paquets? de|boites? de|groupes? de|sachets? de|"
                 r"chaque|par jour|par semaine|douzaines? de", t):
        r = nums[0]
        for n in nums[1:]:
            r *= n
        return f"Ca fait {r}.  ({' x '.join(map(str, nums))} = {r})"
    # division / partage : « partager 20 bonbons entre 4 »
    if re.search(r"partage|partager|divise|repartir|repartis|entre \d|"
                 r"chacun|part egale", t):
        if nums[1] != 0:
            q, reste = divmod(nums[0], nums[1])
            det = f" (il en reste {reste})" if reste else ""
            return f"Chacun en a {q}.{det}  ({nums[0]} / {nums[1]})"
    # soustraction : « j'en mange 2 », « il en perd 3 », « il en reste »
    if re.search(r"mange|perd|perds|enleve|donne|retire|casse|vend|tombe|"
                 r"depense|reste|il en reste|de moins|sont partis|s'envole", t):
        r = nums[0]
        for n in nums[1:]:
            r -= n
        return f"Il en reste {r}.  ({nums[0]} - {' - '.join(map(str, nums[1:]))} = {r})"
    # sinon : addition (« achete », « gagne », « ajoute », « et », « de plus »)
    r = sum(nums)
    return f"Ca fait {r} en tout.  ({' + '.join(map(str, nums))} = {r})"


def repondre(texte):
    t = _sa(texte.lower())

    d = _duree_en(t)
    if d:
        return d

    pb = _probleme(t)
    if pb:
        return pb

    dr = _date_relative(t)
    if dr:
        return dr

    # « le double de la racine de 144 », « la moitie de 3 fois 8 »...
    m = re.search(r"(?:combien (?:font|vaut|fait)\s+|calcule\s+|)?"
                  r"((?:le |la |du )?(?:double|triple|quadruple|moitie|tiers|"
                  r"quart|carre|cube|racine)\s+(?:carree\s+)?(?:de|d').+)", t)
    if m:
        v = _valeur(m.group(1))
        if v is not None:
            return f"{m.group(1).strip()} = {_fmt(v)}."

    # operation en toutes lettres : « 3 fois 8 plus 2 »
    if re.search(r"\d.*\b(plus|moins|fois|divise par|multiplie par)\b.*\d", t) \
            and not re.search(r"[+\-*/]", t):
        v = _valeur(t.replace("combien font", "").replace("calcule", "")
                    .replace("?", ""))
        if v is not None:
            return f"Ca fait {_fmt(v)}."
    return None
