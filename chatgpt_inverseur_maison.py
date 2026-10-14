# -*- coding: utf-8 -*-
"""
ChatGPT Inverseur — MINI-IA MAISON (par Claude, sans API, sans internet)

  - QUESTIONS    -> reponse FAUSSE mais dans le theme
  - AFFIRMATIONS -> l'exact contraire
  - imperatifs, oui<->non, apprentissage de mots
  - conjugaison automatique de etre/avoir selon le sujet
  - MENU a droite : plusieurs conversations (nouveau / ouvrir)
  - bouton ENREGISTRER : sauve tout dans conversations.json

Tout tourne hors-ligne. LANCER :  python chatgpt_inverseur_maison.py
(pip install pygame)
"""

import os
import re
import sys
import json
import random
import threading
import urllib.parse
import urllib.request
import pygame

# ======================================================================
#  MINI-IA : moteur
# ======================================================================
_PAIRS = [
    ("oui", "non"), ("vrai", "faux"), ("bon", "mauvais"), ("bien", "mal"),
    ("grand", "petit"), ("gros", "mince"), ("haut", "bas"), ("chaud", "froid"),
    ("jour", "nuit"), ("noir", "blanc"), ("beau", "laid"), ("riche", "pauvre"),
    ("fort", "faible"), ("rapide", "lent"), ("plein", "vide"), ("ouvert", "ferme"),
    ("jeune", "vieux"), ("nouveau", "ancien"), ("facile", "difficile"),
    ("content", "triste"), ("heureux", "malheureux"), ("gagner", "perdre"),
    ("monter", "descendre"), ("commencer", "finir"), ("toujours", "jamais"),
    ("tout", "rien"), ("avant", "apres"), ("gauche", "droite"),
    ("dedans", "dehors"), ("dessus", "dessous"), ("possible", "impossible"),
    ("vivant", "mort"), ("present", "absent"), ("premier", "dernier"),
    ("entrer", "sortir"), ("acheter", "vendre"), ("ami", "ennemi"),
    ("guerre", "paix"), ("verite", "mensonge"), ("mouille", "sec"),
    ("propre", "sale"), ("dur", "mou"), ("lourd", "leger"), ("clair", "sombre"),
    ("long", "court"), ("large", "etroit"), ("proche", "loin"), ("tot", "tard"),
    ("souvent", "rarement"), ("augmenter", "diminuer"), ("accepter", "refuser"),
    ("aimer", "detester"), ("adorer", "detester"), ("intello", "bete"),
    ("intelligent", "stupide"), ("ouvrir", "fermer"), ("allumer", "eteindre"),
    ("gentil", "mechant"), ("humide", "sec"), ("meilleur", "pire"),
    ("succes", "echec"), ("reussir", "echouer"), ("legal", "illegal"),
    ("utile", "inutile"), ("normal", "anormal"), ("beaucoup", "peu"),
    ("bleu", "rouge"), ("droit", "tordu"), ("chance", "malchance"),
    ("amour", "haine"), ("rire", "pleurer"), ("parler", "taire"),
    ("donner", "prendre"), ("arriver", "partir"), ("naitre", "mourir"),
    ("construire", "detruire"), ("pousser", "tirer"), ("cher", "gratuit"),
    ("fatigue", "repose"), ("malade", "sain"), ("courageux", "peureux"),
    ("poli", "impoli"), ("calme", "agite"), ("doux", "brutal"),
    ("epais", "fin"), ("actif", "passif"), ("public", "prive"),
]


def _strip_accents(s):
    return s.translate(str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc"))


ANTO = {}
for _a, _b in _PAIRS:
    ANTO[_a] = _b
    ANTO[_b] = _a

_HERE = os.path.dirname(os.path.abspath(__file__))
LEARN_FILE = os.path.join(_HERE, "antonymes_appris.json")
CONV_FILE = os.path.join(_HERE, "conversations.json")


def load_learned():
    try:
        with open(LEARN_FILE, encoding="utf-8") as f:
            for k, v in json.load(f).items():
                ANTO[_strip_accents(k)] = v
                ANTO[_strip_accents(v)] = k
    except Exception:  # noqa: BLE001
        pass


def save_learned(x, y):
    data = {}
    try:
        with open(LEARN_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:  # noqa: BLE001
        pass
    data[x] = y
    try:
        with open(LEARN_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:  # noqa: BLE001
        pass


NEG_VERB = {
    "est": "n'est pas", "sont": "ne sont pas", "es": "n'es pas",
    "suis": "ne suis pas", "sommes": "ne sommes pas", "etes": "n'etes pas",
    "a": "n'a pas", "as": "n'as pas", "ai": "n'ai pas", "avons": "n'avons pas",
    "ont": "n'ont pas", "avez": "n'avez pas", "peut": "ne peut pas",
    "peux": "ne peux pas", "peuvent": "ne peuvent pas", "veut": "ne veut pas",
    "veux": "ne veux pas", "veulent": "ne veulent pas", "fait": "ne fait pas",
    "fais": "ne fais pas", "font": "ne font pas", "va": "ne va pas",
    "vais": "ne vais pas", "vont": "ne vont pas", "doit": "ne doit pas",
    "dois": "ne dois pas", "doivent": "ne doivent pas", "sait": "ne sait pas",
    "sais": "ne sais pas", "savent": "ne savent pas", "existe": "n'existe pas",
    "existent": "n'existent pas", "marche": "ne marche pas", "aime": "n'aime pas",
    "aimes": "n'aimes pas", "adore": "n'adore pas", "pense": "ne pense pas",
    "crois": "ne crois pas", "croit": "ne croit pas",
}

NEG_TOKENS = {"ne", "n'", "pas", "plus", "jamais", "aucun", "aucune",
              "rien", "personne", "ni", "point"}
STRONG_NEG = {"ne", "n'", "pas", "point"}
SUBJ = {"je", "j'", "tu", "il", "elle", "on", "nous", "vous", "ils",
        "elles", "ce", "c'", "ca"}
OBJ_PRON = {"me", "m'", "te", "t'", "se", "s'", "le", "la", "les",
            "lui", "leur", "nous", "vous", "y", "en"}
IMP_PRON = {"me": "moi", "m'": "moi", "te": "toi", "t'": "toi", "nous": "nous",
            "vous": "vous", "le": "le", "la": "la", "les": "les", "lui": "lui",
            "leur": "leur", "y": "y", "en": "en"}
AMBIG = {"toujours", "jamais", "souvent", "rarement", "plus", "moins",
         "beaucoup", "peu", "tout", "rien", "oui", "non"}

# conjugaison de etre / avoir selon le sujet
SUBJ_ETRE = {"je": "suis", "j'": "suis", "tu": "es", "il": "est", "elle": "est",
             "on": "est", "ce": "est", "c'": "est", "ca": "est",
             "nous": "sommes", "vous": "etes", "ils": "sont", "elles": "sont"}
SUBJ_AVOIR = {"je": "ai", "j'": "ai", "tu": "as", "il": "a", "elle": "a",
              "on": "a", "ce": "a", "c'": "a", "ca": "a", "nous": "avons",
              "vous": "avez", "ils": "ont", "elles": "ont"}
ETRE_FORMS = {"suis", "es", "est", "sommes", "etes", "sont"}
AVOIR_FORMS = {"ai", "as", "a", "avons", "avez", "ont"}

_ELIDE_FULL = {"j'": "je", "n'": "ne", "c'": "ce", "d'": "de", "l'": "le",
               "s'": "se", "m'": "me", "t'": "te", "qu'": "que"}
_FULL_ELIDE = {"je": "j'", "ne": "n'", "ce": "c'", "de": "d'", "le": "l'",
               "la": "l'", "se": "s'", "me": "m'", "te": "t'", "que": "qu'"}
_VOWELS = "aeiouyàâäéèêëîïôöùûüh"
_CONS = "bcdfghjklmnpqrstvwxzç"


def _tok(t):
    return re.findall(r"[A-Za-zÀ-ÿ]+'|[A-Za-zÀ-ÿ]+|[^\sA-Za-zÀ-ÿ']+|\s+", t)


def _reelide(text):
    pat = re.compile(r"\b(je|ne|de|ce|le|la|se|me|te|que)\s+(?=[" + _VOWELS + "])",
                     re.IGNORECASE)

    def rep(m):
        w = m.group(1)
        el = _FULL_ELIDE[w.lower()]
        return el.capitalize() if w[:1].isupper() else el

    return pat.sub(rep, text)


def _cleanup(t):
    t = re.sub(r"\s{2,}", " ", t).strip()
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    t = _reelide(t)
    # corrige une elision impossible devant consonne : "j'suis" -> "je suis"
    t = re.sub(r"\b([Jj])'(?=[" + _CONS + "])", r"\1e ", t)
    t = re.sub(r"\b([Cc])'(?=[" + _CONS + "])", r"\1e ", t)
    return t


def _fix_agreement(text):
    """Accorde etre/avoir avec le sujet le plus proche."""
    toks = _tok(text)
    subj = None
    for i, t in enumerate(toks):
        b = _strip_accents(t.lower())
        if b in SUBJ_ETRE:
            subj = b
        elif subj and b in ETRE_FORMS:
            nf = SUBJ_ETRE[subj]
            toks[i] = nf.capitalize() if t[:1].isupper() else nf
            subj = None
        elif subj and b in AVOIR_FORMS:
            nf = SUBJ_AVOIR[subj]
            toks[i] = nf.capitalize() if t[:1].isupper() else nf
            subj = None
    return "".join(toks)


def _flip_ouinon(tokens):
    out = []
    for t in tokens:
        b = _strip_accents(t.lower())
        if b == "oui":
            out.append("Non" if t[:1].isupper() else "non")
        elif b == "non":
            out.append("Oui" if t[:1].isupper() else "oui")
        else:
            out.append(t)
    return out


def _swap_antonyms(tokens):
    out, ch = [], False
    for t in tokens:
        k = _strip_accents(t.lower())
        if k in ANTO and k not in AMBIG:
            r = ANTO[k]
            r = r.capitalize() if t[:1].isupper() else r
            out.append(r)
            ch = True
        else:
            out.append(t)
    return out, ch


def _has(tokens, s):
    return any(_strip_accents(t.lower()) in s for t in tokens)


def _has_verb(tokens):
    return any(_strip_accents(t.lower()) in NEG_VERB for t in tokens)


def _remove_negation(tokens):
    return _cleanup("".join(t for t in tokens
                            if _strip_accents(t.lower()) not in NEG_TOKENS))


def _add_negation(tokens):
    out, neg = [], False
    for t in tokens:
        b = _strip_accents(t.lower())
        if not neg and b in NEG_VERB:
            rep = NEG_VERB[b]
            if t[:1].isupper():
                rep = rep[0].upper() + rep[1:]
            for j in range(len(out) - 1, -1, -1):
                if out[j].strip() == "":
                    continue
                p = out[j]
                if p.lower() in _ELIDE_FULL:
                    f = _ELIDE_FULL[p.lower()]
                    f = f.capitalize() if p[:1].isupper() else f
                    out[j] = f + " "
                break
            out.append(rep)
            neg = True
        else:
            out.append(t)
    if not neg:
        return "il est faux de dire que " + "".join(tokens).strip()
    return "".join(out)


def _invert_imperative(tokens):
    words = [w for w in tokens if w.strip() and re.match(r"[A-Za-zÀ-ÿ]", w)]
    words = [w for w in words
             if _strip_accents(w.lower()) not in {"ne", "n'", "pas", "plus", "jamais"}]
    prons, verb, rest = [], None, []
    for w in words:
        if verb is None and _strip_accents(w.lower()) in OBJ_PRON:
            prons.append(w)
        elif verb is None:
            verb = w
        else:
            rest.append(w)
    if verb is None:
        return _cleanup(" ".join(words))
    tail = "".join("-" + IMP_PRON.get(_strip_accents(p.lower()), p) for p in prons)
    res = verb + tail
    if rest:
        res += " " + " ".join(rest)
    return res


_TEACH = [
    re.compile(r"le contraire de\s+([A-Za-zÀ-ÿ'-]+)\s+(?:c'est|c est|est|:)\s+([A-Za-zÀ-ÿ'-]+)", re.I),
    re.compile(r"([A-Za-zÀ-ÿ'-]+)\s+(?:c'est|c est|est)\s+le contraire de\s+([A-Za-zÀ-ÿ'-]+)", re.I),
]


def detect_teach(text):
    for pat in _TEACH:
        m = pat.search(text)
        if m:
            x, y = m.group(1).strip().lower(), m.group(2).strip().lower()
            if x and y and x != y:
                return x, y
    return None


# ---------- MODE QUESTION ----------
Q_STOP = {"le", "la", "les", "un", "une", "des", "de", "du", "est", "es", "sont",
          "que", "qui", "quoi", "quel", "quelle", "quels", "quelles", "ou", "quand",
          "comment", "pourquoi", "combien", "a", "as", "il", "elle", "on", "ce",
          "cette", "ces", "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa",
          "ses", "en", "et", "avec", "pour", "dans", "sur", "se", "ne", "pas",
          "fait", "font", "y", "au", "aux", "tu", "je", "nous", "vous", "ils",
          "elles", "c", "d", "l", "n", "s", "j", "t", "m", "qu",
          "parle", "parler", "moi", "toi", "explique", "expliquer", "raconte",
          "dis", "dire", "definis", "definir", "presente", "montre", "donne",
          "propos", "sujet", "info", "infos", "informations", "expliques"}
CITIES = ["Marseille", "Lyon", "Bordeaux", "Camembert-sur-Loire", "Berlin",
          "Tombouctou", "Petaouchnok", "Trifouillis-les-Oies"]
PLACES = ["a Marseille", "au fond du jardin", "sur la Lune", "dans ton frigo",
          "au Pole Nord", "sous ton lit", "a Bourg-en-Bresse"]
PERS = ["Napoleon", "ton prof de sport", "un pigeon tres malin", "Cleopatre",
        "Kevin du 3e etage", "mon cousin", "Jul"]
DATES = ["en 1492", "un mardi de novembre", "l'annee prochaine",
         "pendant la prehistoire", "a 17h37 pile", "au Moyen Age"]
DEFS = ["une sorte de fromage", "un petit animal du Perou",
        "une danse traditionnelle bretonne", "un jeu de societe des annees 80",
        "une maladie des plantes", "un outil de jardinage"]
NUMS = [3, 7, 12, 42, 99, 17, 5000, 1, 28]


def _qwords(text):
    return [w for w in re.findall(r"[A-Za-zÀ-ÿ0-9+]+", text)
            if _strip_accents(w.lower()) not in Q_STOP and len(w) > 1]


def is_question(text):
    t = _strip_accents(text.strip().lower())
    if text.strip().endswith("?"):
        return True
    # demandes d'info ("parle-moi de...", "explique...", "raconte...", "dis-moi...")
    if re.match(r"^(parle|explique|expliques|raconte|dis|definis|definit|"
                r"presente|montre|donne|c'est quoi)\b", t):
        return True
    return bool(re.match(
        r"^(qui|que|quoi|quel|quelle|quels|quelles|ou|quand|comment|pourquoi|"
        r"combien|est-ce|qu'est-ce|as-tu|es-tu|peux-tu|c'est quoi)\b", t))


def answer_question_specific(text):
    """Reponse fausse pour une categorie connue, sinon None (=pas compris)."""
    t = _strip_accents(text.lower())
    kws = _qwords(text)
    kw = kws[-1] if kws else "ca"

    if re.search(r"c'est quoi|qu'est-ce", t):
        return f"{kw.capitalize()}, c'est {random.choice(DEFS)}, evidemment."
    if "capitale" in t:
        m = re.search(r"capitale\s+(?:de |d'|du |des )?([A-Za-zÀ-ÿ' -]+?)\s*\??$",
                      text.strip(), re.I)
        pays = m.group(1).strip() if m else None
        suffix = f" de {pays}" if pays else ""
        return f"La capitale{suffix}, c'est {random.choice(CITIES)}, tout le monde le sait."
    if re.search(r"\d+\s*[-+x*/]\s*\d+", t):
        return f"Ca fait {random.choice(NUMS)}, c'est mathematique."
    if re.search(r"\bcombien\b", t):
        m = re.search(r"combien d[e'] ?([A-Za-zÀ-ÿ']+)", t)
        obj = m.group(1) if m else kw
        return f"Exactement {random.choice(NUMS)} {obj}, ni plus ni moins."
    if re.search(r"\bquand\b", t):
        return f"{random.choice(DATES).capitalize()}, sans aucun doute."
    if re.search(r"\bqui\b", t):
        return f"C'est {random.choice(PERS)}, c'est bien connu."
    if re.search(r"\bpourquoi\b", t):
        return f"Parce que {kw} a toujours ete comme ca, depuis la nuit des temps."
    if re.search(r"\bcomment\b", t):
        return f"Tres simplement : avec beaucoup de {kw} et un peu de chance."
    if re.match(r"^ou\b", t) or re.search(r"\bou\b (est|se|sont|es|va|vont|se trouve)", t):
        return f"Ca se trouve {random.choice(PLACES)}, evidemment."
    return None  # pas compris -> on ira chercher sur Wikipedia


def generic_fallback(text):
    kws = _qwords(text)
    kw = kws[-1] if kws else "ca"
    return random.choice([
        f"Concernant {kw} : absolument pas, c'est prouve.",
        "Bien sur que oui... enfin non, pas du tout.",
        f"Ca depend de la couleur de tes chaussettes, mais je dirais non pour {kw}.",
    ])


def answer_question(text):
    """Ancienne interface synchrone (specifique, sinon generique)."""
    return answer_question_specific(text) or generic_fallback(text)


def wiki_lookup(text):
    """Cherche le vrai sujet sur Wikipedia FR. Renvoie un titre ou None."""
    query = " ".join(_qwords(text)) or text.strip("? ")
    if not query:
        return None
    try:
        url = "https://fr.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
            {"action": "query", "list": "search", "srsearch": query,
             "format": "json", "srlimit": 1})
        req = urllib.request.Request(
            url, headers={"User-Agent": "MiniIA-Troll/1.0 (projet educatif)"})
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read().decode("utf-8"))
        hits = data.get("query", {}).get("search", [])
        if hits:
            return hits[0]["title"]
    except Exception:  # noqa: BLE001  (pas d'internet, timeout, etc.)
        pass
    return None


def fake_from_wiki(title):
    """A partir du vrai sujet trouve, fabrique une reponse FAUSSE mais dans le theme."""
    return random.choice([
        f"{title} ? Tout le monde sait que ça a été invente par "
        f"{random.choice(PERS)}, {random.choice(DATES)}.",
        f"{title}, c'est evidemment {random.choice(DEFS)}.",
        f"Alors {title}... en realite ça se trouve {random.choice(PLACES)}, "
        f"tout simplement.",
        f"{title} ? Facile : il en existe exactement {random.choice(NUMS)} "
        f"dans le monde entier.",
    ])


def respond(text):
    """Orchestrateur (appele en arriere-plan) : renvoie (texte, is_special)."""
    text = text.strip()
    if not text:
        return "Tu n'as rien dit. Donc, techniquement, tu as tout dit.", False
    if detect_teach(text):
        return invert(text)                 # apprentissage
    if is_question(text):
        spec = answer_question_specific(text)
        if spec is not None:
            return spec, True               # categorie connue
        title = wiki_lookup(text)           # pas compris -> recherche
        if title:
            return fake_from_wiki(title), True
        return generic_fallback(text), True  # hors-ligne / rien trouve
    return invert(text)                     # phrase -> contraire


def invert(text):
    """Renvoie (texte, is_special)."""
    text = text.strip()
    if not text:
        return "Tu n'as rien dit. Donc, techniquement, tu as tout dit.", False

    teach = detect_teach(text)
    if teach:
        x, y = teach
        ANTO[_strip_accents(x)] = y
        ANTO[_strip_accents(y)] = x
        save_learned(x, y)
        return (f"C'est note : desormais le contraire de « {x} » c'est « {y} » "
                f"(et inversement). Merci, j'apprends !"), True

    if is_question(text):
        return answer_question(text), True

    tokens = _flip_ouinon(_tok(text))
    is_imp = _has(tokens, {"ne", "n'"}) and _has(tokens, {"pas"}) \
        and not _has(tokens, SUBJ)

    if is_imp:
        core = _cleanup(_invert_imperative(tokens))
    elif _has(tokens, STRONG_NEG):
        core = _remove_negation(tokens)
    else:
        swapped, changed = _swap_antonyms(tokens)
        if changed:
            core = _cleanup("".join(swapped))
        elif _has_verb(tokens):
            core = _cleanup(_add_negation(tokens))
        else:
            core = _cleanup("".join(tokens))

    # accorde etre/avoir avec le sujet, puis nettoie
    core = _cleanup(_fix_agreement(core))

    if core:
        core = core[0].upper() + core[1:]
    core = re.sub(r"^(Oui|Non) ", r"\1, ", core)
    if core and core[-1] not in ".!?":
        core += "."
    return "Faux. En realite : " + core, False


# ======================================================================
#  UI PYGAME
# ======================================================================
WIDTH, HEIGHT = 980, 640
FPS = 60
COL_BG        = (33, 33, 33)
COL_SIDEBAR   = (24, 24, 28)
COL_ITEM      = (44, 45, 55)
COL_ITEM_ON   = (60, 62, 78)
COL_TRASH     = (205, 120, 120)
COL_DANGER    = (200, 80, 80)
COL_ASSISTANT = (52, 53, 65)
COL_USER      = (67, 76, 99)
COL_TEXT      = (236, 236, 241)
COL_MUTED     = (142, 142, 160)
COL_SPECIAL   = (150, 210, 160)
COL_INPUT_BG  = (64, 65, 79)
COL_INPUT_BRD = (86, 88, 105)
COL_ACCENT    = (25, 195, 125)
COL_SCROLL    = (86, 88, 105)
PAD = 16
SIDEBAR_W = 240

GREETING = ("Salut ! Pose-moi une question (je repondrai un truc faux mais dans "
            "le theme), ou dis une phrase (je repondrai l'exact contraire). "
            "Apprends-moi un mot avec « le contraire de vite c'est doucement ».")


def wrap_text(text, font, max_width):
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            trial = word if current == "" else current + " " + word
            if font.size(trial)[0] <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                while font.size(word)[0] > max_width and len(word) > 1:
                    cut = len(word)
                    while cut > 1 and font.size(word[:cut])[0] > max_width:
                        cut -= 1
                    lines.append(word[:cut])
                    word = word[cut:]
                current = word
        lines.append(current)
    return lines


def _clipboard_text():
    """Renvoie le texte du presse-papiers (pour Ctrl+V), ou ''."""
    try:
        import pygame.scrap as scrap
        try:
            scrap.init()
        except Exception:  # noqa: BLE001
            pass
        if hasattr(scrap, "get_text"):
            txt = scrap.get_text() or ""
        else:
            data = scrap.get(pygame.SCRAP_TEXT)
            txt = data.decode("utf-8", "ignore") if data else ""
    except Exception:  # noqa: BLE001
        txt = ""
    return txt.replace("\x00", "").replace("\r", " ").replace("\n", " ").strip()


def _set_clipboard(text):
    """Copie du texte dans le presse-papiers (pour Ctrl+C)."""
    try:
        import pygame.scrap as scrap
        try:
            scrap.init()
        except Exception:  # noqa: BLE001
            pass
        if hasattr(scrap, "put_text"):
            scrap.put_text(text or "")
        else:
            if hasattr(scrap, "set_mode"):
                try:
                    scrap.set_mode(pygame.SCRAP_CLIPBOARD)
                except Exception:  # noqa: BLE001
                    pass
            scrap.put(pygame.SCRAP_TEXT, (text or "").encode("utf-8"))
    except Exception:  # noqa: BLE001
        pass


class ChatApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("ChatGPT Inverseur — mini-IA maison")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        pygame.key.start_text_input()
        load_learned()

        self.font = pygame.font.SysFont("segoeui,arial,sans", 20)
        self.font_small = pygame.font.SysFont("segoeui,arial,sans", 15)
        self.font_title = pygame.font.SysFont("segoeui,arial,sans", 22, bold=True)

        self.chats = self._load_conversations()
        self.active = 0
        self.input_text = ""
        self.scroll = 0
        self.max_scroll = 0
        self.cursor_visible = True
        self.cursor_timer = 0
        self.thinking = False
        self._result = None
        self._lock = threading.Lock()
        self.saved_timer = 0
        self._chat_rects = []
        self._trash_rects = []
        self._new_btn = None
        self._save_btn = None
        self._send_btn = None
        self._pending_delete = None   # index en attente de confirmation
        self._confirm_yes = None
        self._confirm_no = None
        pygame.key.set_repeat(300, 30)

    # ---------- conversations ----------
    def _new_chat(self):
        return {"name": f"Chat {len(self.chats) + 1}",
                "messages": [("assistant", GREETING, False)]}

    def _load_conversations(self):
        try:
            with open(CONV_FILE, encoding="utf-8") as f:
                data = json.load(f)
            chats = []
            for ch in data.get("chats", []):
                msgs = [tuple(m) for m in ch.get("messages", [])]
                if not msgs:
                    msgs = [("assistant", GREETING, False)]
                chats.append({"name": ch.get("name", "Chat"), "messages": msgs})
            if chats:
                return chats
        except Exception:  # noqa: BLE001
            pass
        return [{"name": "Chat 1", "messages": [("assistant", GREETING, False)]}]

    def _save_conversations(self):
        data = {"chats": [{"name": c["name"],
                           "messages": [list(m) for m in c["messages"]]}
                          for c in self.chats]}
        try:
            with open(CONV_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.saved_timer = 120
        except Exception:  # noqa: BLE001
            self.saved_timer = 0

    @property
    def messages(self):
        return self.chats[self.active]["messages"]

    def new_conversation(self):
        self.chats.append(self._new_chat())
        self.active = len(self.chats) - 1
        self.scroll = 0
        self.input_text = ""

    def open_conversation(self, idx):
        if 0 <= idx < len(self.chats):
            self.active = idx
            self.scroll = 0
            self.input_text = ""

    def delete_conversation(self, idx):
        """Supprime DEFINITIVEMENT la conversation (liste + fichier)."""
        if not (0 <= idx < len(self.chats)):
            return
        del self.chats[idx]
        if not self.chats:
            self.chats = [{"name": "Chat 1",
                           "messages": [("assistant", GREETING, False)]}]
            self.active = 0
        elif self.active >= len(self.chats):
            self.active = len(self.chats) - 1
        elif idx < self.active:
            self.active -= 1
        self.scroll = 0
        self._save_conversations()  # ecrase le fichier -> suppression definitive

    @property
    def input_h(self):
        return 52

    def send(self):
        text = self.input_text.strip()
        if not text or self.thinking:
            return
        chat = self.chats[self.active]
        chat["messages"].append(("user", text, False))
        if chat["name"].startswith("Chat ") and \
                sum(1 for m in chat["messages"] if m[0] == "user") == 1:
            chat["name"] = (text[:20] + "…") if len(text) > 20 else text
        self.input_text = ""
        self.thinking = True
        self._result = None
        self.scroll = 0
        threading.Thread(target=self._worker, args=(text,), daemon=True).start()

    def _worker(self, text):
        res = respond(text)
        with self._lock:
            self._result = res

    def update(self):
        self.cursor_timer += 1
        if self.cursor_timer >= 30:
            self.cursor_timer = 0
            self.cursor_visible = not self.cursor_visible
        if self.saved_timer > 0:
            self.saved_timer -= 1
        if self.thinking:
            with self._lock:
                res = self._result
            if res is not None:
                txt, is_special = res
                self.messages.append(("assistant", txt, is_special))
                self._result = None
                self.thinking = False
                self.scroll = 0

    def draw_message(self, surface, role, text, is_special, y, content_w):
        is_user = role == "user"
        bubble_col = COL_USER if is_user else COL_ASSISTANT
        txt_col = COL_SPECIAL if is_special else COL_TEXT
        max_text_w = int(content_w * 0.78)
        lines = wrap_text(text, self.font, max_text_w)
        line_h = self.font.get_linesize()
        text_h = line_h * len(lines)
        bubble_w = max((self.font.size(l)[0] for l in lines), default=0) + PAD * 2
        bubble_w = min(bubble_w, max_text_w + PAD * 2)
        bubble_h = text_h + PAD * 2
        x = (PAD + content_w - bubble_w) if is_user else PAD
        pygame.draw.rect(surface, bubble_col,
                         pygame.Rect(x, y, bubble_w, bubble_h), border_radius=14)
        label = "Toi" if is_user else "Mini-IA Inverseur"
        surface.blit(self.font_small.render(label, True, COL_MUTED), (x + 4, y - 18))
        ty = y + PAD
        for line in lines:
            surface.blit(self.font.render(line, True, txt_col), (x + PAD, ty))
            ty += line_h
        return bubble_h + 34

    def _measure(self, text, content_w):
        max_text_w = int(content_w * 0.78)
        lines = wrap_text(text, self.font, max_text_w)
        return self.font.get_linesize() * len(lines) + PAD * 2 + 34

    # ---------- dessin ----------
    def draw(self):
        self.screen.fill(COL_BG)
        w, h = self.screen.get_size()
        sidebar_x = max(360, w - SIDEBAR_W)
        chat_w = sidebar_x
        content_w = chat_w - PAD * 2

        self.screen.blit(self.font_title.render("Mini-IA Inverseur", True, COL_TEXT),
                         (PAD, 12))
        sub = self.font_small.render(
            "questions -> faux mais dans le theme  •  phrases -> le contraire",
            True, COL_MUTED)
        self.screen.blit(sub, (PAD, 40))
        pygame.draw.line(self.screen, COL_INPUT_BRD, (0, 62), (chat_w, 62), 1)

        top = 74
        bottom = h - (self.input_h + PAD * 2)
        view_h = bottom - top
        chat_surf = pygame.Surface((chat_w, max(view_h, 10)), pygame.SRCALPHA)

        total_h = PAD
        heights = []
        for role, text, _s in self.messages:
            hgt = self._measure(text, content_w)
            heights.append(hgt)
            total_h += hgt
        if self.thinking:
            total_h += 36

        self.max_scroll = max(0, total_h - view_h)
        self.scroll = max(0, min(self.scroll, self.max_scroll))
        offset = total_h - view_h - self.scroll
        if total_h <= view_h:
            offset = 0

        y = PAD - offset
        for (role, text, is_special), hgt in zip(self.messages, heights):
            if y + hgt > 0 and y < view_h:
                self.draw_message(chat_surf, role, text, is_special, y, content_w)
            y += hgt

        if self.thinking:
            dots = "." * (1 + (pygame.time.get_ticks() // 300) % 3)
            chat_surf.blit(self.font.render("Je reflechis" + dots, True, COL_MUTED),
                           (PAD, y + 4))

        self.screen.blit(chat_surf, (0, top))

        if self.max_scroll > 0:
            thumb_h = max(30, view_h * view_h / total_h)
            thumb_y = top + (view_h - thumb_h) * (1 - self.scroll / self.max_scroll)
            pygame.draw.rect(self.screen, COL_SCROLL,
                             (chat_w - 8, thumb_y, 4, thumb_h), border_radius=2)

        ibox = pygame.Rect(PAD, h - self.input_h - PAD, content_w, self.input_h)
        pygame.draw.rect(self.screen, COL_INPUT_BG, ibox, border_radius=14)
        pygame.draw.rect(self.screen, COL_INPUT_BRD, ibox, 1, border_radius=14)
        if not self.input_text and not self.thinking:
            ph = self.font.render("Pose une question ou dis une phrase...", True, COL_MUTED)
            self.screen.blit(ph, (ibox.x + 16, ibox.y + 14))
        else:
            avail = ibox.width - 60
            shown = self.input_text
            while self.font.size(shown)[0] > avail and shown:
                shown = shown[1:]
            self.screen.blit(self.font.render(shown, True, COL_TEXT),
                             (ibox.x + 16, ibox.y + 14))
            if self.cursor_visible:
                cx = ibox.x + 16 + self.font.size(shown)[0] + 1
                pygame.draw.line(self.screen, COL_TEXT,
                                 (cx, ibox.y + 12), (cx, ibox.y + self.input_h - 12), 2)
        btn = pygame.Rect(ibox.right - 44, ibox.y + 8, 36, self.input_h - 16)
        pygame.draw.rect(self.screen, COL_ACCENT, btn, border_radius=10)
        cx, cy = btn.center
        pygame.draw.polygon(self.screen, COL_BG,
                            [(cx - 5, cy + 5), (cx, cy - 6), (cx + 5, cy + 5)])
        self._send_btn = btn

        self._draw_sidebar(sidebar_x, w, h)
        if self._pending_delete is not None:
            self._draw_confirm(w, h)
        pygame.display.flip()

    def _draw_confirm(self, w, h):
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        bw, bh = 400, 180
        box = pygame.Rect((w - bw) // 2, (h - bh) // 2, bw, bh)
        pygame.draw.rect(self.screen, COL_ASSISTANT, box, border_radius=16)
        pygame.draw.rect(self.screen, COL_INPUT_BRD, box, 1, border_radius=16)

        t1 = self.font_title.render("Es-tu sur ?", True, COL_TEXT)
        self.screen.blit(t1, (box.centerx - t1.get_width() // 2, box.y + 22))
        name = ""
        if 0 <= self._pending_delete < len(self.chats):
            name = self.chats[self._pending_delete]["name"]
        disp = name
        while self.font_small.size(disp)[0] > bw - 70 and len(disp) > 1:
            disp = disp[:-1]
        t2 = self.font_small.render(f"Supprimer « {disp} » definitivement ?",
                                    True, COL_MUTED)
        self.screen.blit(t2, (box.centerx - t2.get_width() // 2, box.y + 66))

        self._confirm_no = pygame.Rect(box.x + 26, box.bottom - 58, 160, 40)
        self._confirm_yes = pygame.Rect(box.right - 186, box.bottom - 58, 160, 40)
        pygame.draw.rect(self.screen, COL_ITEM, self._confirm_no, border_radius=10)
        pygame.draw.rect(self.screen, COL_DANGER, self._confirm_yes, border_radius=10)
        no = self.font_small.render("Annuler", True, COL_TEXT)
        yes = self.font_small.render("Supprimer", True, COL_TEXT)
        self.screen.blit(no, (self._confirm_no.centerx - no.get_width() // 2,
                              self._confirm_no.y + 11))
        self.screen.blit(yes, (self._confirm_yes.centerx - yes.get_width() // 2,
                               self._confirm_yes.y + 11))

    def _handle_confirm(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._confirm_yes and self._confirm_yes.collidepoint(pos):
                idx = self._pending_delete
                self._pending_delete = None
                self.delete_conversation(idx)
            elif self._confirm_no and self._confirm_no.collidepoint(pos):
                self._pending_delete = None
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_n):
                self._pending_delete = None
            elif event.key in (pygame.K_RETURN, pygame.K_y):
                idx = self._pending_delete
                self._pending_delete = None
                self.delete_conversation(idx)
        return True

    def _draw_sidebar(self, x0, w, h):
        pygame.draw.rect(self.screen, COL_SIDEBAR, (x0, 0, w - x0, h))
        pygame.draw.line(self.screen, COL_INPUT_BRD, (x0, 0), (x0, h), 1)
        inner_w = (w - x0) - 24

        self.screen.blit(self.font_small.render("CONVERSATIONS", True, COL_MUTED),
                         (x0 + 14, 16))

        self._new_btn = pygame.Rect(x0 + 12, 38, inner_w, 34)
        pygame.draw.rect(self.screen, COL_ITEM, self._new_btn, border_radius=9)
        self.screen.blit(self.font_small.render("+  Nouveau chat", True, COL_TEXT),
                         (self._new_btn.x + 12, self._new_btn.y + 9))

        self._chat_rects = []
        self._trash_rects = []
        y = 84
        list_bottom = h - 64
        for i, ch in enumerate(self.chats):
            if y + 34 > list_bottom:
                break
            r = pygame.Rect(x0 + 12, y, inner_w, 32)
            pygame.draw.rect(self.screen,
                             COL_ITEM_ON if i == self.active else COL_SIDEBAR,
                             r, border_radius=9)
            name = ch["name"]
            while self.font_small.size(name)[0] > inner_w - 44 and len(name) > 1:
                name = name[:-1]
            self.screen.blit(self.font_small.render(name, True, COL_TEXT),
                             (r.x + 10, r.y + 8))
            trash = pygame.Rect(r.right - 28, r.y + 4, 24, 24)
            self._draw_trash(trash.centerx, trash.centery)
            self._trash_rects.append((trash, i))
            self._chat_rects.append((r, i))
            y += 38

        self._draw_save_and_footer(x0, w, h, inner_w)

    def _draw_trash(self, cx, cy):
        col = COL_TRASH
        pygame.draw.rect(self.screen, col, (cx - 6, cy - 4, 12, 2))       # couvercle
        pygame.draw.rect(self.screen, col, (cx - 2, cy - 7, 4, 2))        # poignee
        body = pygame.Rect(cx - 5, cy - 1, 10, 11)
        pygame.draw.rect(self.screen, col, body, 1, border_radius=2)      # bac
        pygame.draw.line(self.screen, col, (cx - 2, cy + 1), (cx - 2, cy + 8))
        pygame.draw.line(self.screen, col, (cx + 2, cy + 1), (cx + 2, cy + 8))

    def _draw_save_and_footer(self, x0, w, h, inner_w):
        self._save_btn = pygame.Rect(x0 + 12, h - 50, inner_w, 36)
        pygame.draw.rect(self.screen, COL_ACCENT, self._save_btn, border_radius=10)
        label = "Enregistre !" if self.saved_timer > 0 else "Enregistrer"
        img = self.font_small.render(label, True, COL_BG)
        self.screen.blit(img, (self._save_btn.centerx - img.get_width() // 2,
                               self._save_btn.y + 10))

    # ---------- evenements ----------
    def handle(self, event):
        global WIDTH, HEIGHT
        if event.type == pygame.QUIT:
            self._save_conversations()
            return False
        # fenetre de confirmation ouverte : elle capte tout
        if self._pending_delete is not None:
            return self._handle_confirm(event)
        if event.type == pygame.VIDEORESIZE:
            WIDTH, HEIGHT = event.w, event.h
            self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.scroll + event.y * 40, self.max_scroll))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._new_btn and self._new_btn.collidepoint(pos):
                self.new_conversation()
            elif self._save_btn and self._save_btn.collidepoint(pos):
                self._save_conversations()
            elif self._send_btn and self._send_btn.collidepoint(pos):
                self.send()
            else:
                # corbeille d'abord (elle est a l'interieur de la ligne)
                for tr, i in self._trash_rects:
                    if tr.collidepoint(pos):
                        self._pending_delete = i   # demande confirmation
                        break
                else:
                    for r, i in self._chat_rects:
                        if r.collidepoint(pos):
                            self.open_conversation(i)
                            break
        elif event.type == pygame.TEXTINPUT:
            if len(self.input_text) < 500:
                self.input_text += event.text
        elif event.type == pygame.KEYDOWN:
            if (event.mod & pygame.KMOD_CTRL) and event.key == pygame.K_v:
                paste = _clipboard_text()
                if paste:
                    self.input_text = (self.input_text + paste)[:500]
            elif (event.mod & pygame.KMOD_CTRL) and event.key == pygame.K_c:
                to_copy = self.input_text.strip()
                if not to_copy:
                    for role, txt, *_rest in reversed(self.messages):
                        if role == "assistant":
                            to_copy = txt
                            break
                _set_clipboard(to_copy)
            elif event.key == pygame.K_RETURN:
                self.send()
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.key == pygame.K_ESCAPE:
                self._save_conversations()
                return False
        return True

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if not self.handle(event):
                    running = False
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    ChatApp().run()
