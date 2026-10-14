# -*- coding: utf-8 -*-
"""
Assistant Verite — l'oppose du troll : il dit la VRAIE reponse.

  - calcule les operations mathematiques
  - repond aux questions en cherchant sur Wikipedia (FR)
  - dit honnetement quand il ne trouve pas
  - MENU a droite : plusieurs conversations (nouveau / ouvrir / corbeille)
  - bouton ENREGISTRER : sauve tout dans verite_conversations.json

LANCER :  python assistant_verite.py     (pip install pygame)
La recherche a besoin d'internet ; le reste marche hors-ligne.
"""

import os
import re
import sys
import json
import math
import random
import threading
import urllib.parse
import urllib.request
from datetime import datetime
import pygame


def _strip_accents(s):
    return s.translate(str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc"))


_HERE = os.path.dirname(os.path.abspath(__file__))
CONV_FILE = os.path.join(_HERE, "verite_conversations.json")

# mots ignores pour construire la requete Wikipedia
Q_STOP = {"le", "la", "les", "un", "une", "des", "de", "du", "est", "es", "sont",
          "que", "qui", "quoi", "quel", "quelle", "quels", "quelles", "ou", "quand",
          "comment", "pourquoi", "combien", "a", "as", "il", "elle", "on", "ce",
          "cette", "ces", "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa",
          "ses", "en", "et", "avec", "pour", "dans", "sur", "se", "ne", "pas",
          "fait", "font", "y", "au", "aux", "tu", "je", "nous", "vous", "ils",
          "elles", "c", "d", "l", "n", "s", "j", "t", "m", "qu",
          "parle", "parler", "moi", "toi", "explique", "expliquer", "expliques",
          "raconte", "dis", "dire", "definis", "definir", "presente", "montre",
          "donne", "propos", "sujet", "info", "infos", "informations", "signifie",
          "veut", "designe", "connais", "sais"}

GREET_RE = re.compile(
    r"\b(bonjour|bonsoir|salut|coucou|hello|hey|yo|ca va|comment vas|"
    r"comment tu vas|merci|au revoir|bye)\b")
SILENCE_RE = re.compile(
    r"\b(tais[- ]?toi|silence|chut|la ferme|ferme[- ]?la|"
    r"arrete de parler|arrete de causer|stp tais)\b")
SILENCE_REPLIES = [
    "Ok, je me tais ! (mais je reste la si tu as une question)",
    "D'accord, chut. :)",
    "Silence radio. Appelle-moi quand tu veux savoir un truc !",
]
GREET_REPLIES = [
    "Salut ! Pose-moi une question, je te reponds la verite.",
    "Bonjour ! Qu'est-ce que tu veux savoir ?",
    "Coucou ! Je suis la pour repondre a tes questions, vraiment cette fois. :)",
]


def _qwords(text):
    return [w for w in re.findall(r"[A-Za-zÀ-ÿ0-9+]+", text)
            if _strip_accents(w.lower()) not in Q_STOP and len(w) > 1]


def try_math(text):
    """Si le message contient un calcul, renvoie 'expr = resultat', sinon None."""
    t = text.lower().replace("×", "*").replace("÷", "/").replace(",", ".")
    t = re.sub(r"\bfois\b", "*", t)
    t = re.sub(r"\bplus\b", "+", t)
    t = re.sub(r"\bmoins\b", "-", t)
    m = re.search(r"[0-9][0-9\.\s\+\-\*/\(\)]*[0-9]", t)
    if not m:
        return None
    expr = m.group(0).strip()
    if not re.search(r"[\+\-\*/]", expr):
        return None
    if not re.fullmatch(r"[0-9\.\s\+\-\*/\(\)]+", expr):
        return None
    try:
        val = eval(expr, {"__builtins__": {}}, {})  # noqa: S307 (expr filtree)
    except Exception:  # noqa: BLE001
        return None
    if isinstance(val, float) and val.is_integer():
        val = int(val)
    elif isinstance(val, float):
        val = round(val, 6)
    return f"{expr} = {val}"


def _wiki_get(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "AssistantVerite/1.0 (projet educatif)"})
    with urllib.request.urlopen(req, timeout=7) as r:
        return json.loads(r.read().decode("utf-8"))


# mots-cles "aspect" : cherchent une SECTION de l'article, pas le resume general
ASPECT_SECTIONS = {
    "alimentation": ["alimentation", "regime", "nourriture", "nutrition"],
    "nourriture": ["alimentation", "regime", "nourriture"],
    "regime": ["alimentation", "regime"],
    "reproduction": ["reproduction", "cycle"],
    "habitat": ["habitat", "repartition", "distribution", "aire"],
    "repartition": ["repartition", "habitat", "distribution"],
    "taille": ["taille", "description", "morphologie", "caracteristiques", "anatomie"],
    "poids": ["poids", "description", "morphologie"],
    "vitesse": ["vitesse", "locomotion", "deplacement"],
    "histoire": ["histoire", "historique"],
    "origine": ["origine", "etymologie", "histoire"],
    "predateur": ["predateur", "menace", "danger"],
    "predateurs": ["predateur", "menace", "danger"],
    "comportement": ["comportement", "mode de vie", "ethologie"],
    "description": ["description", "morphologie", "anatomie", "caracteristiques"],
    "anatomie": ["anatomie", "morphologie", "description"],
    "symptome": ["symptome", "signe", "clinique"],
    "symptomes": ["symptome", "signe", "clinique"],
    "traitement": ["traitement", "prise en charge", "therapie"],
    "cause": ["cause", "origine", "etiologie"],
    "causes": ["cause", "origine", "etiologie"],
    "utilisation": ["utilisation", "usage", "emploi"],
    "fonctionnement": ["fonctionnement", "principe"],
    "longevite": ["longevite", "duree de vie"],
    "classification": ["classification", "taxonomie", "systematique"],
    "etymologie": ["etymologie", "nom", "denomination"],
    "danger": ["danger", "risque", "menace"],
    "dangers": ["danger", "risque", "menace"],
}
ASPECTS = set(ASPECT_SECTIONS.keys())


def _strip_html(html):
    import html as _html
    h = re.sub(r"(?is)<(script|style|sup|table)[^>]*>.*?</\1>", " ", html)
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    h = _html.unescape(h)
    h = re.sub(r"\[\s*modifier[^\]]*\]", " ", h, flags=re.I)
    h = re.sub(r"\[\d+\]", " ", h)
    return re.sub(r"\s+", " ", h).strip()


def _wiki_aspect(subject, aspect):
    """Cherche une SECTION precise (ex: 'Alimentation') dans les articles du sujet."""
    keys = ASPECT_SECTIONS.get(aspect, [aspect])
    try:
        surl = "https://fr.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
            {"action": "query", "list": "search", "srsearch": subject,
             "format": "json", "srlimit": 4})
        hits = _wiki_get(surl).get("query", {}).get("search", [])
        # on teste plusieurs articles candidats jusqu'a trouver la bonne section
        for hit in hits:
            title = hit["title"]
            purl = "https://fr.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
                {"action": "parse", "page": title, "prop": "sections",
                 "format": "json", "formatversion": "2"})
            sections = _wiki_get(purl).get("parse", {}).get("sections", [])
            for sec in sections:
                line = _strip_accents(sec.get("line", "").lower())
                if any(k in line for k in keys):
                    idx = sec.get("index")
                    if not idx:
                        continue
                    turl = "https://fr.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
                        {"action": "parse", "page": title, "section": idx,
                         "prop": "text", "format": "json", "formatversion": "2"})
                    html = _wiki_get(turl).get("parse", {}).get("text", "")
                    txt = _strip_html(html)
                    if len(txt) < 25:
                        continue
                    sents = re.split(r"(?<=[.!?])\s+", txt)
                    short = " ".join(sents[:3]).strip()
                    return (f"{short}\n\n(source : Wikipedia - « {title} », "
                            f"section « {sec.get('line')} »)")
        return None
    except Exception:  # noqa: BLE001
        return None


def wiki_answer(text):
    """Cherche le vrai sujet sur Wikipedia FR et renvoie un resume, ou None."""
    kws = _qwords(text)
    # si un mot-cle d'aspect est present (ex: "alimentation baleine"),
    # on va chercher la SECTION correspondante plutot que le resume general
    aspects = [w for w in kws if _strip_accents(w.lower()) in ASPECTS]
    subject_kws = [w for w in kws if _strip_accents(w.lower()) not in ASPECTS]
    if aspects and subject_kws:
        res = _wiki_aspect(" ".join(subject_kws),
                           _strip_accents(aspects[0].lower()))
        if res:
            return res
    query = " ".join(kws) or text.strip("? ")
    if not query:
        return None
    try:
        search_url = "https://fr.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
            {"action": "query", "list": "search", "srsearch": query,
             "format": "json", "srlimit": 5})
        data = _wiki_get(search_url)
        hits = data.get("query", {}).get("search", [])
        # on parcourt les resultats et on ignore les pages d'homonymie
        for hit in hits:
            title = hit["title"]
            try:
                summ = _wiki_get(
                    "https://fr.wikipedia.org/api/rest_v1/page/summary/"
                    + urllib.parse.quote(title))
            except Exception:  # noqa: BLE001
                continue
            if summ.get("type") == "disambiguation":
                continue  # page "plusieurs sens" -> on saute
            extract = (summ.get("extract") or "").strip()
            if len(extract) < 20:
                continue
            sentences = re.split(r"(?<=[.!?])\s+", extract)
            short = " ".join(sentences[:2]).strip()
            return f"{short}\n\n(source : Wikipedia — « {title} »)"
        return None
    except Exception:  # noqa: BLE001  (offline, timeout...)
        return None


# ---------- INTENTIONS : demandes concretes que le bot fait lui-meme ----------
_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout",
         "septembre", "octobre", "novembre", "decembre"]


def _today_str():
    n = datetime.now()
    return f"Nous sommes le {_JOURS[n.weekday()]} {n.day} {_MOIS[n.month - 1]} {n.year}."


def _prev_random(history):
    """La derniere reponse de l'assistant parlait-elle d'aleatoire ?"""
    for role, t in reversed(history or []):
        if role == "assistant":
            b = _strip_accents(t.lower())
            return ("aleatoire" in b) or ("hasard" in b) or ("nombre" in b)
    return False


def _rand_num(text):
    t = _strip_accents(text.lower())
    m = re.search(r"entre\s+(\d+)\s*(?:et|a|-)\s*(\d+)", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        lo, hi = min(a, b), max(a, b)
    else:
        lo, hi = 1, 100
    return f"Voici un nombre aleatoire entre {lo} et {hi} : {random.randint(lo, hi)}."


def detect_intent(text, history):
    """Renvoie une reponse-action, ou None si ce n'est pas une demande connue."""
    low = text.lower()
    t = _strip_accents(low)

    # suivi contextuel : "donne(s) en un", "encore", "un autre"... apres l'aleatoire
    if _prev_random(history) and len(t) < 30 and \
            re.search(r"\b(donne|donnes|encore|refais|relance|autre|vas-y|ok|un)\b", t):
        return _rand_num(text)

    # nombre au hasard
    if re.search(r"\b(nombre|chiffre)s?\b", t) and (
            re.search(r"aleatoire|hasard|random", t)
            or re.search(r"entre\s+\d+", t)
            or re.search(r"\b(donne|donnes|tire|genere|choisis|balance)\b", t)):
        return _rand_num(text)

    # lancer un de
    if re.search(r"\bd[ée]s?\b", low) and re.search(r"lanc|jett|roul|tire|joue", low):
        faces = 6
        m = re.search(r"(\d+)\s*faces", low)
        if m:
            faces = max(2, int(m.group(1)))
        return f"Le de tombe sur : {random.randint(1, faces)}."

    # pile ou face
    if re.search(r"pile ou face|pile-face|pile/face", t) or \
            (re.search(r"\bpiece\b", t) and re.search(r"lanc|jett|tire", t)):
        return "C'est... " + random.choice(["Pile", "Face"]) + " !"

    # heure
    if re.search(r"\bheure\b", t) and re.search(r"quelle|il est|donne|dis|c'est|sais", t):
        return "Il est " + datetime.now().strftime("%H:%M") + "."

    # jour / date
    if re.search(r"\b(jour|date)\b", t) and re.search(
            r"quel|quelle|aujourd|on est|c'est|sommes|donne|dis", t):
        return _today_str()

    return None


# ---------- OPERATIONS MATHS en langage naturel ----------
def _n(x):
    x = float(x)
    return str(int(x)) if x.is_integer() else str(x)


def _fmt(label, val):
    if isinstance(val, float):
        val = int(val) if val.is_integer() else round(val, 6)
    return f"{label} = {val}."


def solve_task(text):
    """Reconnait une operation demandee en francais et la calcule. Sinon None."""
    t = _strip_accents(text.lower()).replace(",", ".")

    if "racine" in t:
        m = re.search(r"racine\s*(?:carree)?\s*(?:de\s*)?(-?\d+\.?\d*)", t)
        if m:
            x = float(m.group(1))
            if x < 0:
                return "La racine carree d'un nombre negatif n'existe pas (dans les reels)."
            return _fmt(f"La racine carree de {_n(x)}", math.sqrt(x))

    m = re.search(r"(-?\d+\.?\d*)\s*(?:puissance|exposant|\^|\*\*)\s*(-?\d+\.?\d*)", t)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return _fmt(f"{_n(a)} puissance {_n(b)}", a ** b)

    m = re.search(r"(-?\d+\.?\d*)\s*au\s*carre", t)
    if m:
        a = float(m.group(1))
        return _fmt(f"{_n(a)} au carre", a * a)

    m = re.search(r"(-?\d+\.?\d*)\s*au\s*cube", t)
    if m:
        a = float(m.group(1))
        return _fmt(f"{_n(a)} au cube", a ** 3)

    if "factorielle" in t:
        m = re.search(r"factorielle\s*(?:de\s*)?(\d+)", t)
        if m:
            n = int(m.group(1))
            if n > 170:
                return "C'est bien trop grand pour etre calcule ici."
            return _fmt(f"La factorielle de {n}", math.factorial(n))

    m = re.search(r"(-?\d+\.?\d*)\s*(?:%|pour\s*cent)\s*(?:de\s*)?(-?\d+\.?\d*)", t)
    if m:
        p, y = float(m.group(1)), float(m.group(2))
        return _fmt(f"{_n(p)}% de {_n(y)}", p / 100 * y)

    if "valeur absolue" in t:
        m = re.search(r"valeur absolue\s*(?:de\s*)?(-?\d+\.?\d*)", t)
        if m:
            a = float(m.group(1))
            return _fmt(f"La valeur absolue de {_n(a)}", abs(a))

    if "arrondi" in t:
        m = re.search(r"arrondi\s*(?:de\s*)?(-?\d+\.?\d*)", t)
        if m:
            a = float(m.group(1))
            return _fmt(f"L'arrondi de {_n(a)}", round(a))

    if "moyenne" in t:
        nums = re.findall(r"-?\d+\.?\d*", t)
        if len(nums) >= 2:
            vals = [float(x) for x in nums]
            return _fmt("La moyenne de " + ", ".join(_n(v) for v in vals),
                        sum(vals) / len(vals))

    for name, fn in (("cosinus", math.cos), ("sinus", math.sin),
                     ("tangente", math.tan)):
        if name in t:
            m = re.search(name + r"\s*(?:de\s*)?(-?\d+\.?\d*)", t)
            if m:
                a = float(m.group(1))
                return _fmt(f"Le {name} de {_n(a)} degres", fn(math.radians(a)))

    return None


def respond(text, history=None):
    """Renvoie (texte, is_fact). is_fact=True quand c'est une reponse factuelle."""
    text = text.strip()
    if not text:
        return "Pose-moi une question et je te reponds la verite.", False
    if SILENCE_RE.search(_strip_accents(text.lower())):
        return random.choice(SILENCE_REPLIES), False
    if GREET_RE.search(_strip_accents(text.lower())) and len(text) < 40:
        return random.choice(GREET_REPLIES), False
    task = solve_task(text)
    if task:
        return task, True
    calc = try_math(text)
    if calc:
        return calc, True
    intent = detect_intent(text, history or [])
    if intent is not None:
        return intent, True
    ans = wiki_answer(text)
    if ans:
        return ans, True
    return ("Je n'ai pas trouve d'information fiable la-dessus (ou pas "
            "d'internet). Essaie de reformuler ou d'etre plus precis."), False


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
COL_FACT      = (150, 200, 235)
COL_INPUT_BG  = (64, 65, 79)
COL_INPUT_BRD = (86, 88, 105)
COL_ACCENT    = (25, 195, 125)
COL_SCROLL    = (86, 88, 105)
PAD = 16
SIDEBAR_W = 240

GREETING = ("Bonjour ! Je suis l'Assistant Verite. Pose-moi une question "
            "(ex: « c'est quoi un tardigrade ? », « combien font 12*8 ? », "
            "« parle-moi de la Lune ») et je te reponds la vraie info, en "
            "cherchant sur Wikipedia si besoin.")


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
        pygame.display.set_caption("Assistant Verite")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        pygame.key.start_text_input()

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
        self._pending_delete = None
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
        self._save_conversations()

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
        history = [(r, tx) for (r, tx, _e) in chat["messages"][:-1]]
        self.input_text = ""
        self.thinking = True
        self._result = None
        self.scroll = 0
        threading.Thread(target=self._worker, args=(text, history), daemon=True).start()

    def _worker(self, text, history):
        res = respond(text, history)
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
                txt, is_fact = res
                self.messages.append(("assistant", txt, is_fact))
                self._result = None
                self.thinking = False
                self.scroll = 0

    def draw_message(self, surface, role, text, is_fact, y, content_w):
        is_user = role == "user"
        bubble_col = COL_USER if is_user else COL_ASSISTANT
        txt_col = COL_FACT if is_fact else COL_TEXT
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
        label = "Toi" if is_user else "Assistant Verite"
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

    def draw(self):
        self.screen.fill(COL_BG)
        w, h = self.screen.get_size()
        sidebar_x = max(360, w - SIDEBAR_W)
        chat_w = sidebar_x
        content_w = chat_w - PAD * 2

        self.screen.blit(self.font_title.render("Assistant Verite", True, COL_TEXT),
                         (PAD, 12))
        sub = self.font_small.render(
            "dit toujours la verite  •  calcule et cherche sur Wikipedia",
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
        for (role, text, is_fact), hgt in zip(self.messages, heights):
            if y + hgt > 0 and y < view_h:
                self.draw_message(chat_surf, role, text, is_fact, y, content_w)
            y += hgt

        if self.thinking:
            dots = "." * (1 + (pygame.time.get_ticks() // 300) % 3)
            chat_surf.blit(self.font.render("Je cherche" + dots, True, COL_MUTED),
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
            ph = self.font.render("Pose une question...", True, COL_MUTED)
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
        pygame.draw.rect(self.screen, col, (cx - 6, cy - 4, 12, 2))
        pygame.draw.rect(self.screen, col, (cx - 2, cy - 7, 4, 2))
        pygame.draw.rect(self.screen, col, pygame.Rect(cx - 5, cy - 1, 10, 11),
                         1, border_radius=2)
        pygame.draw.line(self.screen, col, (cx - 2, cy + 1), (cx - 2, cy + 8))
        pygame.draw.line(self.screen, col, (cx + 2, cy + 1), (cx + 2, cy + 8))

    def _draw_save_and_footer(self, x0, w, h, inner_w):
        self._save_btn = pygame.Rect(x0 + 12, h - 50, inner_w, 36)
        pygame.draw.rect(self.screen, COL_ACCENT, self._save_btn, border_radius=10)
        label = "Enregistre !" if self.saved_timer > 0 else "Enregistrer"
        img = self.font_small.render(label, True, COL_BG)
        self.screen.blit(img, (self._save_btn.centerx - img.get_width() // 2,
                               self._save_btn.y + 10))

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

    # ---------- evenements ----------
    def handle(self, event):
        global WIDTH, HEIGHT
        if event.type == pygame.QUIT:
            self._save_conversations()
            return False
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
                for tr, i in self._trash_rects:
                    if tr.collidepoint(pos):
                        self._pending_delete = i
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
