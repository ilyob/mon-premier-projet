# -*- coding: utf-8 -*-
"""
CONJUGAISON — moteur de regles pour conjuguer les verbes francais.

Ce ne sont pas des reponses apprises : ce sont de VRAIES regles. L'IA peut
donc conjuguer un verbe jamais vu (s'il suit une regle connue).

Temps geres :
  present, imparfait, futur, conditionnel, subjonctif, imperatif,
  passe compose, plus-que-parfait, futur anterieur, conditionnel passe.

Couverture :
  - tous les verbes reguliers (1er groupe -er, 2e groupe -ir)
  - familles : -dre, -uire, -eindre/-aindre/-oindre, -cevoir
  - une trentaine de verbes irreguliers (etre, avoir, aller, faire...)
  - tous les COMPOSES d'un verbe connu (devenir, permettre, comprendre...)

Utilise :  reponse = repondre("conjugue prendre au subjonctif")
"""

import re

PRON = ["je", "tu", "il", "nous", "vous", "ils"]


def _sa(s):
    return s.translate(str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc"))


def _je(f):
    return ("j'" if f[:1].lower() in "aeiouyhàâäéèêëîïôö" else "je ") + f


# ---------- PRESENT : verbes irreguliers de base ----------
IRREG = {
    "etre": ["suis", "es", "est", "sommes", "êtes", "sont"],
    "avoir": ["ai", "as", "a", "avons", "avez", "ont"],
    "aller": ["vais", "vas", "va", "allons", "allez", "vont"],
    "faire": ["fais", "fais", "fait", "faisons", "faites", "font"],
    "dire": ["dis", "dis", "dit", "disons", "dites", "disent"],
    "pouvoir": ["peux", "peux", "peut", "pouvons", "pouvez", "peuvent"],
    "vouloir": ["veux", "veux", "veut", "voulons", "voulez", "veulent"],
    "devoir": ["dois", "dois", "doit", "devons", "devez", "doivent"],
    "savoir": ["sais", "sais", "sait", "savons", "savez", "savent"],
    "voir": ["vois", "vois", "voit", "voyons", "voyez", "voient"],
    "venir": ["viens", "viens", "vient", "venons", "venez", "viennent"],
    "tenir": ["tiens", "tiens", "tient", "tenons", "tenez", "tiennent"],
    "prendre": ["prends", "prends", "prend", "prenons", "prenez", "prennent"],
    "mettre": ["mets", "mets", "met", "mettons", "mettez", "mettent"],
    "partir": ["pars", "pars", "part", "partons", "partez", "partent"],
    "sortir": ["sors", "sors", "sort", "sortons", "sortez", "sortent"],
    "dormir": ["dors", "dors", "dort", "dormons", "dormez", "dorment"],
    "servir": ["sers", "sers", "sert", "servons", "servez", "servent"],
    "sentir": ["sens", "sens", "sent", "sentons", "sentez", "sentent"],
    "mentir": ["mens", "mens", "ment", "mentons", "mentez", "mentent"],
    "boire": ["bois", "bois", "boit", "buvons", "buvez", "boivent"],
    "lire": ["lis", "lis", "lit", "lisons", "lisez", "lisent"],
    "ecrire": ["écris", "écris", "écrit", "écrivons", "écrivez", "écrivent"],
    "connaitre": ["connais", "connais", "connaît", "connaissons",
                  "connaissez", "connaissent"],
    "paraitre": ["parais", "parais", "paraît", "paraissons",
                 "paraissez", "paraissent"],
    "courir": ["cours", "cours", "court", "courons", "courez", "courent"],
    "ouvrir": ["ouvre", "ouvres", "ouvre", "ouvrons", "ouvrez", "ouvrent"],
    "couvrir": ["couvre", "couvres", "couvre", "couvrons", "couvrez", "couvrent"],
    "offrir": ["offre", "offres", "offre", "offrons", "offrez", "offrent"],
    "souffrir": ["souffre", "souffres", "souffre", "souffrons",
                 "souffrez", "souffrent"],
    "cueillir": ["cueille", "cueilles", "cueille", "cueillons",
                 "cueillez", "cueillent"],
    "croire": ["crois", "crois", "croit", "croyons", "croyez", "croient"],
    "rire": ["ris", "ris", "rit", "rions", "riez", "rient"],
    "suivre": ["suis", "suis", "suit", "suivons", "suivez", "suivent"],
    "vivre": ["vis", "vis", "vit", "vivons", "vivez", "vivent"],
    "plaire": ["plais", "plais", "plaît", "plaisons", "plaisez", "plaisent"],
    "recevoir": ["reçois", "reçois", "reçoit", "recevons", "recevez", "reçoivent"],
    "mourir": ["meurs", "meurs", "meurt", "mourons", "mourez", "meurent"],
    "naitre": ["nais", "nais", "naît", "naissons", "naissez", "naissent"],
    "battre": ["bats", "bats", "bat", "battons", "battez", "battent"],
    "vaincre": ["vaincs", "vaincs", "vainc", "vainquons", "vainquez", "vainquent"],
    "resoudre": ["résous", "résous", "résout", "résolvons", "résolvez", "résolvent"],
    "coudre": ["couds", "couds", "coud", "cousons", "cousez", "cousent"],
    "moudre": ["mouds", "mouds", "moud", "moulons", "moulez", "moulent"],
    "falloir": ["", "", "faut", "", "", ""],
    "pleuvoir": ["", "", "pleut", "", "", ""],
    "valoir": ["vaux", "vaux", "vaut", "valons", "valez", "valent"],
}

GROUP2 = {"finir", "choisir", "grandir", "reussir", "remplir", "reflechir",
          "obeir", "punir", "ralentir", "applaudir", "atterrir", "avertir",
          "batir", "definir", "garantir", "nourrir", "reagir", "rougir",
          "salir", "unir", "guerir", "maigrir", "grossir", "vieillir",
          "agir", "reflechir", "avertir", "franchir", "trahir", "saisir"}

# composes : ces bases servent a conjuguer devenir, permettre, comprendre...
COMP_BASES = ["venir", "tenir", "mettre", "prendre", "faire", "voir",
              "courir", "couvrir", "ouvrir", "offrir", "connaitre",
              "paraitre", "dormir", "sentir", "partir", "servir", "battre"]

# participes passes irreguliers
PART = {
    "etre": "été", "avoir": "eu", "faire": "fait", "dire": "dit",
    "prendre": "pris", "mettre": "mis", "voir": "vu", "savoir": "su",
    "pouvoir": "pu", "vouloir": "voulu", "devoir": "dû", "venir": "venu",
    "tenir": "tenu", "boire": "bu", "lire": "lu", "ecrire": "écrit",
    "connaitre": "connu", "paraitre": "paru", "aller": "allé",
    "courir": "couru", "ouvrir": "ouvert", "couvrir": "couvert",
    "offrir": "offert", "souffrir": "souffert", "cueillir": "cueilli",
    "croire": "cru", "rire": "ri", "suivre": "suivi", "vivre": "vécu",
    "plaire": "plu", "recevoir": "reçu", "mourir": "mort", "naitre": "né",
    "battre": "battu", "vaincre": "vaincu", "resoudre": "résolu",
    "coudre": "cousu", "moudre": "moulu", "valoir": "valu",
    "falloir": "fallu", "pleuvoir": "plu", "servir": "servi",
    "sentir": "senti", "mentir": "menti", "partir": "parti", "sortir": "sorti",
    "dormir": "dormi",
}

# radicaux du futur (irreguliers)
FUTUR_STEM = {
    "etre": "ser", "avoir": "aur", "aller": "ir", "faire": "fer",
    "pouvoir": "pourr", "vouloir": "voudr", "devoir": "devr",
    "savoir": "saur", "voir": "verr", "venir": "viendr", "tenir": "tiendr",
    "envoyer": "enverr", "courir": "courr", "mourir": "mourr",
    "recevoir": "recevr", "falloir": "faudr", "valoir": "vaudr",
    "cueillir": "cueiller", "pleuvoir": "pleuvr", "vaincre": "vaincr",
}

# auxiliaire ETRE au passe compose
ETRE_AUX = {"aller", "venir", "arriver", "partir", "entrer", "sortir",
            "monter", "descendre", "rester", "tomber", "naitre", "mourir",
            "retourner", "devenir", "revenir", "intervenir", "parvenir"}

# subjonctif present irregulier
SUBJ = {
    "etre": ["sois", "sois", "soit", "soyons", "soyez", "soient"],
    "avoir": ["aie", "aies", "ait", "ayons", "ayez", "aient"],
    "aller": ["aille", "ailles", "aille", "allions", "alliez", "aillent"],
    "faire": ["fasse", "fasses", "fasse", "fassions", "fassiez", "fassent"],
    "pouvoir": ["puisse", "puisses", "puisse", "puissions", "puissiez",
                "puissent"],
    "savoir": ["sache", "saches", "sache", "sachions", "sachiez", "sachent"],
    "vouloir": ["veuille", "veuilles", "veuille", "voulions", "vouliez",
                "veuillent"],
    "valoir": ["vaille", "vailles", "vaille", "valions", "valiez", "vaillent"],
    "falloir": ["", "", "faille", "", "", ""],
    "pleuvoir": ["", "", "pleuve", "", "", ""],
}
IMPER_IRREG = {
    "etre": ["sois", "soyons", "soyez"],
    "avoir": ["aie", "ayons", "ayez"],
    "savoir": ["sache", "sachons", "sachez"],
    "vouloir": ["veuille", "veuillons", "veuillez"],
    "aller": ["va", "allons", "allez"],
}


# ---------- resolveur de composes ----------
def _compose(v, key):
    for base in COMP_BASES:
        if key.endswith(base) and key != base and len(key) > len(base):
            return base, v[:len(v) - len(base)]
    return None, None


# ---------- PRESENT ----------
def _present(v, key):
    if key in IRREG:
        return IRREG[key]
    base, pref = _compose(v, key)
    if base:
        return [pref + f if f else "" for f in IRREG[base]]
    if v.endswith("er") and key != "aller":
        st = v[:-2]
        nous = st + "ons"
        if v.endswith("ger"):
            nous = st + "eons"
        elif v.endswith("cer"):
            nous = st[:-1] + "çons"
        return [st + "e", st + "es", st + "e", nous, st + "ez", st + "ent"]
    if key in GROUP2:
        st = v[:-2]
        return [st + "is", st + "is", st + "it", st + "issons",
                st + "issez", st + "issent"]
    if v.endswith("cevoir"):
        st = v[:-6]
        return [st + "çois", st + "çois", st + "çoit", st + "cevons",
                st + "cevez", st + "çoivent"]
    if v.endswith("uire"):
        st = v[:-2]                      # conduire -> condui
        return [st + "s", st + "s", st + "t", st + "sons", st + "sez", st + "sent"]
    for term, sng, plr in (("eindre", "ein", "eign"), ("aindre", "ain", "aign"),
                           ("oindre", "oin", "oign")):
        if v.endswith(term):
            r = v[:-len(term)]
            return [r + sng + "s", r + sng + "s", r + sng + "t",
                    r + plr + "ons", r + plr + "ez", r + plr + "ent"]
    if v.endswith("dre"):
        st = v[:-2]
        return [st + "s", st + "s", st, st + "ons", st + "ez", st + "ent"]
    return None


# ---------- PARTICIPE ----------
def _participe(v, key):
    if key in PART:
        return PART[key]
    base, pref = _compose(v, key)
    if base and base in PART:
        return pref + PART[base]
    if v.endswith("er"):
        return v[:-2] + "é"
    if key in GROUP2 or v.endswith("ir"):
        return v[:-1]
    if v.endswith("uire"):
        return v[:-2] + "t"              # conduire -> conduit
    for term, part in (("eindre", "eint"), ("aindre", "aint"), ("oindre", "oint")):
        if v.endswith(term):
            return v[:-len(term)] + part
    if v.endswith("dre"):
        return v[:-2] + "u"
    return None


# ---------- radical du FUTUR / CONDITIONNEL ----------
def _futur_stem(v, key):
    if key in FUTUR_STEM:
        return FUTUR_STEM[key]
    base, pref = _compose(v, key)
    if base and base in FUTUR_STEM:
        return pref + FUTUR_STEM[base]
    if v.endswith("er") or key in GROUP2 or v.endswith("ir"):
        return v
    if v.endswith("cevoir"):
        return v[:-6] + "cevr"
    if v.endswith("re"):
        return v[:-1]
    if v.endswith("oir"):
        return None
    return None


def _futur(v, key):
    st = _futur_stem(v, key)
    if st is None:
        return None
    e = ["ai", "as", "a", "ons", "ez", "ont"]
    return [st + x for x in e]


def _conditionnel(v, key):
    st = _futur_stem(v, key)
    if st is None:
        return None
    e = ["ais", "ais", "ait", "ions", "iez", "aient"]
    return [st + x for x in e]


# ---------- IMPARFAIT ----------
def _imparfait(v, key):
    if key == "etre":
        return ["étais", "étais", "était", "étions", "étiez", "étaient"]
    pres = _present(v, key)
    if not pres or not pres[3].endswith("ons"):
        return None
    rad = pres[3][:-3]
    ri = rad
    if rad.endswith("ge"):
        ri = rad[:-1]
    elif rad.endswith("ç"):
        ri = rad[:-1] + "c"
    return [rad + "ais", rad + "ais", rad + "ait", ri + "ions",
            ri + "iez", rad + "aient"]


# ---------- PASSE SIMPLE ----------
PS_IRREG = {
    "etre": ["fus", "fus", "fut", "fûmes", "fûtes", "furent"],
    "avoir": ["eus", "eus", "eut", "eûmes", "eûtes", "eurent"],
    "faire": ["fis", "fis", "fit", "fîmes", "fîtes", "firent"],
    "dire": ["dis", "dis", "dit", "dîmes", "dîtes", "dirent"],
    "voir": ["vis", "vis", "vit", "vîmes", "vîtes", "virent"],
    "prendre": ["pris", "pris", "prit", "prîmes", "prîtes", "prirent"],
    "mettre": ["mis", "mis", "mit", "mîmes", "mîtes", "mirent"],
    "ecrire": ["écrivis", "écrivis", "écrivit", "écrivîmes", "écrivîtes",
               "écrivirent"],
    "conduire": ["conduisis", "conduisis", "conduisit", "conduisîmes",
                 "conduisîtes", "conduisirent"],
    "craindre": ["craignis", "craignis", "craignit", "craignîmes",
                 "craignîtes", "craignirent"],
    "peindre": ["peignis", "peignis", "peignit", "peignîmes", "peignîtes",
                "peignirent"],
    "joindre": ["joignis", "joignis", "joignit", "joignîmes", "joignîtes",
                "joignirent"],
    "naitre": ["naquis", "naquis", "naquit", "naquîmes", "naquîtes",
               "naquirent"],
    "venir": ["vins", "vins", "vint", "vînmes", "vîntes", "vinrent"],
    "tenir": ["tins", "tins", "tint", "tînmes", "tîntes", "tinrent"],
    "mourir": ["mourus", "mourus", "mourut", "mourûmes", "mourûtes",
               "moururent"],
    "coudre": ["cousis", "cousis", "cousit", "cousîmes", "cousîtes",
               "cousirent"],
    "vaincre": ["vainquis", "vainquis", "vainquit", "vainquîmes", "vainquîtes",
                "vainquirent"],
    "battre": ["battis", "battis", "battit", "battîmes", "battîtes",
               "battirent"],
    "falloir": ["", "", "fallut", "", "", ""],
    "pleuvoir": ["", "", "plut", "", "", ""],
}


def _passe_simple(v, key):
    if key in PS_IRREG:
        return PS_IRREG[key]
    base, pref = _compose(v, key)
    if base and base in PS_IRREG:
        return [pref + f if f else "" for f in PS_IRREG[base]]
    if v.endswith("er"):                 # 1er groupe (aller compris)
        b = v[:-2]
        if v.endswith("ger"):
            return [b + "eai", b + "eas", b + "ea", b + "eâmes", b + "eâtes",
                    b + "èrent"]
        if v.endswith("cer"):
            c = b[:-1]
            return [c + "çai", c + "ças", c + "ça", c + "çâmes", c + "çâtes",
                    b + "èrent"]
        return [b + "ai", b + "as", b + "a", b + "âmes", b + "âtes", b + "èrent"]
    if key in GROUP2:
        st = v[:-2]
        return [st + "is", st + "is", st + "it", st + "îmes", st + "îtes",
                st + "irent"]
    # 3e groupe : le passe simple en -u se devine grace au participe (bu, connu...)
    part = _participe(v, key)
    if part and part.endswith("u"):
        st = part[:-1]
        return [st + "us", st + "us", st + "ut", st + "ûmes", st + "ûtes",
                st + "urent"]
    return None


# ---------- SUBJONCTIF PRESENT ----------
def _subjonctif(v, key):
    if key in SUBJ:
        return SUBJ[key]
    base, pref = _compose(v, key)
    if base and base in SUBJ:
        return [pref + f if f else "" for f in SUBJ[base]]
    pres = _present(v, key)
    if not pres or not pres[5].endswith("ent") or not pres[3].endswith("ons"):
        return None
    r = pres[5][:-3]        # radical du « ils » (finiss, prenn, viennent->vienn)
    rn = pres[3][:-3]       # radical du « nous » (pour nous/vous)
    return [r + "e", r + "es", r + "e", rn + "ions", rn + "iez", r + "ent"]


# ---------- SUBJONCTIF IMPARFAIT (a partir du passe simple) ----------
def _subjonctif_imparfait(v, key):
    ps = _passe_simple(v, key)
    if not ps or not ps[0]:
        return None
    ps0 = ps[0]
    if ps0.endswith("ai"):                       # 1er groupe : que je mangeasse
        s = ps0[:-2]
        return [s + "asse", s + "asses", s + "ât", s + "assions",
                s + "assiez", s + "assent"]
    base = ps0[:-1] if ps0.endswith("s") else ps0
    last = base[-1] if base else ""
    if last == "i":
        il = base[:-1] + "ît"
    elif last == "u":
        il = base[:-1] + "ût"
    elif last == "n":
        il = base[:-2] + "înt"           # vin -> vînt
    else:
        il = base + "t"
    return [base + "sse", base + "sses", il, base + "ssions",
            base + "ssiez", base + "ssent"]


# ---------- IMPERATIF ----------
def _imperatif(v, key):
    if key in IMPER_IRREG:
        return IMPER_IRREG[key]
    pres = _present(v, key)
    if not pres:
        return None
    tu = pres[1]
    if v.endswith("er") or key in ("ouvrir", "couvrir", "offrir", "souffrir",
                                   "cueillir") or key == "aller":
        tu = pres[0]        # pas de « s » (mange, ouvre, va)
    return [tu, pres[3], pres[4]]


# ---------- temps composes ----------
def _aux(v, key):
    return "etre" if key in ETRE_AUX else "avoir"


def _compose_temps(v, key, aux_forms, accord=False):
    part = _participe(v, key)
    if part is None:
        return None
    out = []
    for pron, a in zip(PRON, aux_forms):
        acc = "(e)" if (accord and _aux(v, key) == "etre") else ""
        debut = _je(a) if pron == "je" else f"{pron} {a}"
        out.append(f"{debut} {part}{acc}")
    return out


def _passe_compose(v, key):
    a = IRREG[_aux(v, key)]
    return _compose_temps(v, key, a, accord=True)


def _plus_que_parfait(v, key):
    a = _imparfait(_aux(v, key), _aux(v, key))
    return _compose_temps(v, key, a, accord=True)


def _futur_anterieur(v, key):
    a = _futur(_aux(v, key), _aux(v, key))
    return _compose_temps(v, key, a, accord=True)


def _conditionnel_passe(v, key):
    a = _conditionnel(_aux(v, key), _aux(v, key))
    return _compose_temps(v, key, a, accord=True)


# ---------- table des temps ----------
COMPOSE_FN = {_passe_compose, _plus_que_parfait, _futur_anterieur,
              _conditionnel_passe}
TEMPS = {
    "present": ("présent", _present),
    "imparfait": ("imparfait", _imparfait),
    "passe simple": ("passé simple", _passe_simple),
    "futur": ("futur", _futur),
    "conditionnel": ("conditionnel", _conditionnel),
    "subjonctif": ("subjonctif présent", _subjonctif),
    "subjonctif imparfait": ("subjonctif imparfait", _subjonctif_imparfait),
    "imperatif": ("impératif", _imperatif),
    "passe compose": ("passé composé", _passe_compose),
    "plus-que-parfait": ("plus-que-parfait", _plus_que_parfait),
    "futur anterieur": ("futur antérieur", _futur_anterieur),
    "conditionnel passe": ("conditionnel passé", _conditionnel_passe),
}


def conjuguer(verbe, temps="present"):
    v = verbe.strip().lower()
    key = _sa(v)
    nom, fn = TEMPS.get(temps, TEMPS["present"])
    formes = fn(v, key)
    if not formes:
        return None
    prep = "à l'" if nom[:1] in "aeiouy" else "au "
    lignes = [f"Conjugaison de « {v} » {prep}{nom} :"]
    if fn is _imperatif:
        for pron, f in zip(("(tu)", "(nous)", "(vous)"), formes):
            if f:
                lignes.append(f"  {f} !")
        return "\n".join(lignes)
    if fn in COMPOSE_FN:
        for f in formes:
            if f.strip():
                lignes.append("  " + f)
        return "\n".join(lignes)
    for pron, f in zip(PRON, formes):
        if not f:
            continue
        lignes.append("  " + (_je(f) if pron == "je" else f"{pron} {f}"))
    return "\n".join(lignes)


# ---------- detection dans une phrase ----------
_TEMPS_MOTS = [
    ("subjonctif imparfait", ("subjonctif imparfait", "subjonctif de l'imparfait")),
    ("plus-que-parfait", ("plus-que-parfait", "plus que parfait")),
    ("conditionnel passe", ("conditionnel passe", "conditionnel passé")),
    ("futur anterieur", ("futur anterieur", "futur antérieur")),
    ("passe compose", ("passe compose", "passe-compose", "compose")),
    ("passe simple", ("passe simple", "passe-simple")),
    ("imparfait", ("imparfait",)),
    ("conditionnel", ("conditionnel",)),
    ("subjonctif", ("subjonctif",)),
    ("imperatif", ("imperatif", "impératif")),
    ("futur", ("futur",)),
    ("present", ("present",)),
]


def repondre(texte):
    t = _sa(texte.lower())
    if not re.search(r"\bconjug", t):
        return None
    temps = "present"
    for nom, mots in _TEMPS_MOTS:
        if any(m in t for m in mots):
            temps = nom
            break
    verbes = re.findall(r"\b([a-z]{3,}(?:er|ir|re|oir))\b", t)
    verbes = [w for w in verbes if w not in ("conjuguer",)] or verbes
    if not verbes:
        m = re.search(r"conjug\w*\s+(?:le verbe\s+|moi\s+)?([a-z]+)", t)
        verbes = [m.group(1)] if m else []
    if not verbes:
        return "Quel verbe veux-tu que je conjugue, et a quel temps ?"
    r = conjuguer(verbes[-1], temps)
    if r:
        return r
    return (f"Je ne sais pas encore conjuguer « {verbes[-1]} » — c'est un "
            "verbe irregulier que je ne connais pas. Mais je gere tous les "
            "verbes en -er, en -ir, et plein d'irreguliers !")
