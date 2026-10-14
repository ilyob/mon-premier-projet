# -*- coding: utf-8 -*-
"""
Le Devineur (20 questions) — pense a un animal, il le devine !

Il pose des questions OUI / NON (tu peux aussi repondre « je sais pas ») et
elimine les animaux jusqu'a trouver. Hors-ligne, gratuit. Meme interface que
tes autres bots (plusieurs parties, enregistrer, corbeille).

LANCER :  python devineur_20questions.py     (pip install pygame)
"""

import os
import re
import sys
import json
import threading
import urllib.parse
import urllib.request
import pygame


def _strip_accents(s):
    return s.translate(str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc"))


_HERE = os.path.dirname(os.path.abspath(__file__))
CONV_FILE = os.path.join(_HERE, "devineur_conversations.json")

# ---------- LA BASE DE CONNAISSANCES ----------
ATTRS = ["mammifere", "eau", "voler", "compagnie", "grand",
         "viande", "afrique", "poils", "ferme", "insecte"]
QUESTIONS = {
    "mammifere": "Est-ce que c'est un mammifere ?",
    "eau": "Est-ce qu'il vit dans l'eau ?",
    "voler": "Est-ce qu'il peut voler ?",
    "compagnie": "Est-ce qu'on peut l'avoir comme animal de compagnie ?",
    "grand": "Est-ce qu'il est plus grand qu'un humain ?",
    "viande": "Est-ce qu'il mange de la viande ou des insectes ?",
    "afrique": "Est-ce un animal SAUVAGE de la savane africaine (lion, girafe...) ?",
    "poils": "Est-ce que son corps est couvert de poils ou de fourrure ?",
    "ferme": "Est-ce qu'on le trouve dans une ferme ?",
    "insecte": "Est-ce que c'est un insecte ?",
}


def _A(*vals):
    return dict(zip(ATTRS, vals))


#                    mam eau vol cmp grd via afr poi frm ins
ANIMALS = {
    "chien":     _A(1, 0, 0, 1, 0, 1, 0, 1, 0, 0),
    "chat":      _A(1, 0, 0, 1, 0, 1, 0, 1, 0, 0),
    "lapin":     _A(1, 0, 0, 1, 0, 0, 0, 1, 1, 0),
    "souris":    _A(1, 0, 0, 1, 0, 0, 0, 1, 0, 0),
    "cheval":    _A(1, 0, 0, 1, 1, 0, 0, 1, 1, 0),
    "vache":     _A(1, 0, 0, 0, 1, 0, 0, 1, 1, 0),
    "mouton":    _A(1, 0, 0, 0, 0, 0, 0, 1, 1, 0),
    "cochon":    _A(1, 0, 0, 0, 0, 0, 0, 1, 1, 0),
    "lion":      _A(1, 0, 0, 0, 1, 1, 1, 1, 0, 0),
    "girafe":    _A(1, 0, 0, 0, 1, 0, 1, 1, 0, 0),
    "elephant":  _A(1, 0, 0, 0, 1, 0, 1, 0, 0, 0),
    "singe":     _A(1, 0, 0, 0, 0, 0, 1, 1, 0, 0),
    "dauphin":   _A(1, 1, 0, 0, 1, 1, 0, 0, 0, 0),
    "baleine":   _A(1, 1, 0, 0, 1, 1, 0, 0, 0, 0),
    "requin":    _A(0, 1, 0, 0, 1, 1, 0, 0, 0, 0),
    "poisson":   _A(0, 1, 0, 1, 0, 0, 0, 0, 0, 0),
    "tortue":    _A(0, 1, 0, 1, 0, 0, 0, 0, 0, 0),
    "grenouille": _A(0, 1, 0, 0, 0, 1, 0, 0, 0, 0),
    "pingouin":  _A(0, 1, 0, 0, 0, 1, 0, 0, 0, 0),
    "aigle":     _A(0, 0, 1, 0, 0, 1, 0, 0, 0, 0),
    "perroquet": _A(0, 0, 1, 1, 0, 0, 0, 0, 0, 0),
    "poule":     _A(0, 0, 0, 0, 0, 0, 0, 0, 1, 0),
    "serpent":   _A(0, 0, 0, 1, 0, 1, 0, 0, 0, 0),
    "araignee":  _A(0, 0, 0, 0, 0, 1, 0, 0, 0, 0),
    "abeille":   _A(0, 0, 1, 0, 0, 0, 0, 0, 0, 1),
    "papillon":  _A(0, 0, 1, 0, 0, 0, 0, 0, 0, 1),
    "homme":     _A(1, 0, 0, 0, 0, 1, 0, 0, 0, 0),
    "tigre":     _A(1, 0, 0, 0, 1, 1, 0, 1, 0, 0),
    "ours":      _A(1, 0, 0, 0, 1, 1, 0, 1, 0, 0),
    "loup":      _A(1, 0, 0, 0, 0, 1, 0, 1, 0, 0),
    "renard":    _A(1, 0, 0, 0, 0, 1, 0, 1, 0, 0),
    "hamster":   _A(1, 0, 0, 1, 0, 0, 0, 1, 0, 0),
    "canard":    _A(0, 1, 1, 0, 0, 0, 0, 0, 1, 0),
    "crocodile": _A(0, 1, 0, 0, 1, 1, 1, 0, 0, 0),
    "escargot":  _A(0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
}

# ---------- MEMOIRE : animaux appris via Wikipedia ----------
LEARN_FILE = os.path.join(_HERE, "devineur_appris.json")


def load_learned():
    try:
        with open(LEARN_FILE, encoding="utf-8") as f:
            for name, attrs in json.load(f).items():
                ANIMALS[name] = {a: int(attrs.get(a, 0)) for a in ATTRS}
    except Exception:  # noqa: BLE001
        pass


def save_learned(name, attrs):
    data = {}
    try:
        with open(LEARN_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:  # noqa: BLE001
        pass
    data[name] = attrs
    try:
        with open(LEARN_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:  # noqa: BLE001
        pass


def _wiki_get(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Devineur/1.0 (projet educatif)"})
    with urllib.request.urlopen(req, timeout=7) as r:
        return json.loads(r.read().decode("utf-8"))


def wiki_summary(query):
    try:
        surl = "https://fr.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
            {"action": "query", "list": "search", "srsearch": query,
             "format": "json", "srlimit": 1})
        hits = _wiki_get(surl).get("query", {}).get("search", [])
        if not hits:
            return None
        title = hits[0]["title"]
        s = _wiki_get("https://fr.wikipedia.org/api/rest_v1/page/summary/"
                      + urllib.parse.quote(title))
        return (s.get("extract") or "").strip() or None
    except Exception:  # noqa: BLE001
        return None


def _derive_attrs(text):
    """Deduit les caracteristiques d'un animal a partir du texte Wikipedia."""
    t = _strip_accents(text.lower())

    def has(*words):
        return any(w in t for w in words)

    mammifere = 1 if has("mammifere") else 0
    eau = 1 if has("aquatique", "marin", "poisson", "ocean", " mer ", "eau douce",
                   "riviere", "amphibien", "cetace") else 0
    voler = 1 if has("oiseau", " vole", "volant", " aile", "volatile") else 0
    insecte = 1 if has("insecte") else 0
    compagnie = 1 if has("animal de compagnie", "domestique", "apprivois") else 0
    grand = 1 if has("geant", "enorme", "tonnes", "metres de haut",
                     "plus grand") else 0
    viande = 1 if has("carnivore", "predateur", "carnassier", "insectivore",
                      "piscivore", "rapace", "chasse") else 0
    afrique = 1 if has("savane") else 0
    poils = 1 if (has("fourrure", "pelage", "poils") or (mammifere and not eau)) else 0
    ferme = 1 if has("elevage", "ferme", "betail", "domestique") else 0
    return _A(mammifere, eau, voler, compagnie, grand, viande, afrique,
              poils, ferme, insecte)


def _mistake_message(state, name, key):
    """L'animal est deja connu : c'est donc une erreur dans les reponses."""
    attrs = ANIMALS[key]
    answers = state.get("answers", {})
    for attr in state.get("asked", []):
        ans = answers.get(attr)
        if ans == "oui" and attrs[attr] == 0:
            return (f"Attends... je connais {name.upper()} ! Tu t'es trompe : "
                    f"a « {QUESTIONS[attr]} » tu as dit OUI, alors que pour "
                    f"{name} c'est NON. Rejoue, tu vas voir !")
        if ans == "non" and attrs[attr] == 1:
            return (f"Attends... je connais {name.upper()} ! Tu t'es trompe : "
                    f"a « {QUESTIONS[attr]} » tu as dit NON, alors que pour "
                    f"{name} c'est OUI. Rejoue, tu vas voir !")
    if key in state.get("rejected", []):
        return (f"Ha ! Je connais {name.upper()} : je l'avais devine et tu as "
                "repondu NON. Petit farceur ! Tape quelque chose pour rejouer.")
    return (f"Tiens, je connais {name.upper()} pourtant... on s'est loupe quelque "
            "part. Tape quelque chose pour rejouer.")


def learn_animal(state, raw):
    """Apprend un animal via Wikipedia et le memorise. Renvoie le message."""
    name = re.sub(r"^(un |une |le |la |l'|les |des |du |c'est )", "",
                  raw.strip().lower()).strip(" .!?")
    state["phase"] = "done"
    if not name:
        return "Pas de nom... tant pis ! Tape quelque chose pour rejouer."
    key = _strip_accents(name)
    if key in ANIMALS:                      # deja connu -> c'est une erreur de reponse
        return _mistake_message(state, name, key)
    extract = wiki_summary(name + " animal") or wiki_summary(name)
    if not extract:
        return (f"Je n'ai pas trouve « {name} » sur Wikipedia (ou pas d'internet). "
                "Tape quelque chose pour rejouer.")
    key = _strip_accents(name)
    ANIMALS[key] = _derive_attrs(extract)
    save_learned(key, ANIMALS[key])
    return (f"Merci ! J'ai appris ce qu'est « {name} » grace a Wikipedia, "
            "je le retiendrai pour les prochaines parties. Tape quelque chose "
            "pour rejouer.")


load_learned()


def best_attribute(rem, asked):
    """La question qui separe le mieux les animaux restants (ou None)."""
    best, best_score = None, 10 ** 9
    for attr in ATTRS:
        if attr in asked:
            continue
        yes = sum(1 for a in rem if ANIMALS[a][attr] == 1)
        no = len(rem) - yes
        if yes == 0 or no == 0:
            continue                       # ne separe rien -> inutile
        score = abs(yes - no)
        if score < best_score:
            best_score, best = score, attr
    return best


def parse_yes_no(text):
    t = _strip_accents(text.strip().lower())
    if t in ("o", "y") or re.search(
            r"\b(oui|ouais|ouaip|yep|yes|si|vrai|exact|carrement|ouii)\b", t):
        return "oui"
    if t in ("n",) or re.search(r"\b(non|nan|nope|no|faux|pas|jamais)\b", t):
        return "non"
    return "?"


def _fresh_state():
    remaining = list(ANIMALS.keys())
    attr = best_attribute(remaining, [])
    return {"remaining": remaining, "asked": [attr], "count": 1,
            "phase": "ask", "pending": attr, "answers": {}, "rejected": []}


def start_message(state):
    return ("Pense a un animal et garde-le bien en tete ! Reponds par OUI, NON, "
            "ou « je sais pas ».\n\nQuestion 1 : " + QUESTIONS[state["pending"]])


def _after_filter(state):
    rem = state["remaining"]
    if not rem:
        state["phase"] = "learn"
        return ("Je seche ! Quel etait ton animal ? Ecris son nom, "
                "j'irai l'apprendre sur Wikipedia pour la prochaine fois.")
    if len(rem) == 1:
        state["phase"] = "guess"
        state["pending"] = rem[0]
        state["count"] += 1
        return f"Je crois savoir... C'est un {rem[0].upper()} ? (oui / non)"
    attr = best_attribute(rem, state["asked"])
    if attr is None or state["count"] >= 20:
        state["phase"] = "guess"
        state["pending"] = rem[0]
        state["count"] += 1
        return f"Hmm, je tente : c'est un {rem[0].upper()} ? (oui / non)"
    state["asked"].append(attr)
    state["pending"] = attr
    state["count"] += 1
    return f"Question {state['count']} : {QUESTIONS[attr]}"


def step(state, text):
    if state["phase"] == "done":
        state.update(_fresh_state())
        return start_message(state)

    ans = parse_yes_no(text)

    if state["phase"] == "guess":
        guess = state["pending"]
        if ans == "oui":
            state["phase"] = "done"
            return (f"Gagne ! C'etait bien {guess.upper()} ! "
                    f"(trouve en {state['count']} questions)  —  "
                    f"tape quelque chose pour rejouer.")
        state.setdefault("rejected", []).append(guess)
        state["remaining"] = [a for a in state["remaining"] if a != guess]
        return _after_filter(state)

    # phase "ask"
    attr = state["pending"]
    state.setdefault("answers", {})[attr] = ans   # on retient ta reponse
    if ans == "oui":
        state["remaining"] = [a for a in state["remaining"] if ANIMALS[a][attr] == 1]
    elif ans == "non":
        state["remaining"] = [a for a in state["remaining"] if ANIMALS[a][attr] == 0]
    # "?" : on ne filtre pas
    return _after_filter(state)


# ======================================================================
#  UI PYGAME
# ======================================================================
WIDTH, HEIGHT = 980, 640
FPS = 60
COL_BG        = (30, 32, 40)
COL_SIDEBAR   = (23, 25, 32)
COL_ITEM      = (46, 50, 62)
COL_ITEM_ON   = (62, 68, 86)
COL_TRASH     = (205, 125, 120)
COL_DANGER    = (200, 90, 80)
COL_ASSISTANT = (48, 52, 64)
COL_USER      = (66, 74, 98)
COL_TEXT      = (236, 238, 244)
COL_MUTED     = (150, 156, 170)
COL_GUESS     = (140, 220, 255)
COL_INPUT_BG  = (56, 60, 74)
COL_INPUT_BRD = (88, 94, 112)
COL_ACCENT    = (90, 160, 245)
COL_SCROLL    = (88, 94, 112)
PAD = 16
SIDEBAR_W = 240


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
        pygame.display.set_caption("Le Devineur (20 questions)")
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
        self.saved_timer = 0
        self.thinking = False
        self._result = None
        self._lock = threading.Lock()
        self._chat_rects = []
        self._trash_rects = []
        self._new_btn = None
        self._save_btn = None
        self._send_btn = None
        self._pending_delete = None
        self._confirm_yes = None
        self._confirm_no = None
        pygame.key.set_repeat(300, 30)

    # ---------- parties ----------
    def _new_chat(self):
        st = _fresh_state()
        return {"name": f"Partie {len(self.chats) + 1}", "state": st,
                "messages": [("assistant", start_message(st), False)]}

    def _load_conversations(self):
        try:
            with open(CONV_FILE, encoding="utf-8") as f:
                data = json.load(f)
            chats = []
            for ch in data.get("chats", []):
                msgs = [tuple(m) for m in ch.get("messages", [])]
                st = ch.get("state") or _fresh_state()
                if not msgs:
                    msgs = [("assistant", start_message(st), False)]
                chats.append({"name": ch.get("name", "Partie"),
                              "state": st, "messages": msgs})
            if chats:
                return chats
        except Exception:  # noqa: BLE001
            pass
        return [self._first_chat()]

    def _first_chat(self):
        st = _fresh_state()
        return {"name": "Partie 1", "state": st,
                "messages": [("assistant", start_message(st), False)]}

    def _save_conversations(self):
        data = {"chats": [{"name": c["name"], "state": c.get("state", _fresh_state()),
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
            self.chats = [self._first_chat()]
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
        st = chat["state"]
        self.input_text = ""
        self.scroll = 0
        if st.get("phase") == "learn":
            # apprentissage via Wikipedia -> en arriere-plan
            self.thinking = True
            self._result = None
            threading.Thread(target=self._worker, args=(chat, text),
                             daemon=True).start()
        else:
            msg = step(st, text)
            special = st["phase"] in ("guess", "done", "learn")
            chat["messages"].append(("assistant", msg, special))

    def _worker(self, chat, text):
        msg = learn_animal(chat["state"], text)
        with self._lock:
            self._result = (chat, msg)

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
                chat, msg = res
                chat["messages"].append(("assistant", msg, True))
                self._result = None
                self.thinking = False
                self.scroll = 0

    def draw_message(self, surface, role, text, guess, y, content_w):
        is_user = role == "user"
        bubble_col = COL_USER if is_user else COL_ASSISTANT
        txt_col = COL_GUESS if guess else COL_TEXT
        max_text_w = int(content_w * 0.80)
        lines = wrap_text(text, self.font, max_text_w)
        line_h = self.font.get_linesize()
        text_h = line_h * len(lines)
        bubble_w = max((self.font.size(l)[0] for l in lines), default=0) + PAD * 2
        bubble_w = min(bubble_w, max_text_w + PAD * 2)
        bubble_h = text_h + PAD * 2
        x = (PAD + content_w - bubble_w) if is_user else PAD
        pygame.draw.rect(surface, bubble_col,
                         pygame.Rect(x, y, bubble_w, bubble_h), border_radius=14)
        label = "Toi" if is_user else "Le Devineur"
        surface.blit(self.font_small.render(label, True, COL_MUTED), (x + 4, y - 18))
        ty = y + PAD
        for line in lines:
            surface.blit(self.font.render(line, True, txt_col), (x + PAD, ty))
            ty += line_h
        return bubble_h + 34

    def _measure(self, text, content_w):
        max_text_w = int(content_w * 0.80)
        lines = wrap_text(text, self.font, max_text_w)
        return self.font.get_linesize() * len(lines) + PAD * 2 + 34

    def draw(self):
        self.screen.fill(COL_BG)
        w, h = self.screen.get_size()
        sidebar_x = max(360, w - SIDEBAR_W)
        chat_w = sidebar_x
        content_w = chat_w - PAD * 2

        self.screen.blit(self.font_title.render("Le Devineur (20 questions)",
                                                True, COL_GUESS), (PAD, 12))
        sub = self.font_small.render(
            "pense a un animal, je le devine  •  reponds oui / non / je sais pas",
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
        for (role, text, guess), hgt in zip(self.messages, heights):
            if y + hgt > 0 and y < view_h:
                self.draw_message(chat_surf, role, text, guess, y, content_w)
            y += hgt

        if self.thinking:
            dots = "." * (1 + (pygame.time.get_ticks() // 300) % 3)
            chat_surf.blit(self.font.render("Je cherche sur Wikipedia" + dots,
                                            True, COL_MUTED), (PAD, y + 4))

        self.screen.blit(chat_surf, (0, top))

        if self.max_scroll > 0:
            thumb_h = max(30, view_h * view_h / total_h)
            thumb_y = top + (view_h - thumb_h) * (1 - self.scroll / self.max_scroll)
            pygame.draw.rect(self.screen, COL_SCROLL,
                             (chat_w - 8, thumb_y, 4, thumb_h), border_radius=2)

        ibox = pygame.Rect(PAD, h - self.input_h - PAD, content_w, self.input_h)
        pygame.draw.rect(self.screen, COL_INPUT_BG, ibox, border_radius=14)
        pygame.draw.rect(self.screen, COL_INPUT_BRD, ibox, 1, border_radius=14)
        if not self.input_text:
            ph = self.font.render("Reponds oui / non / je sais pas...", True, COL_MUTED)
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

        self.screen.blit(self.font_small.render("PARTIES", True, COL_MUTED),
                         (x0 + 14, 16))

        self._new_btn = pygame.Rect(x0 + 12, 38, inner_w, 34)
        pygame.draw.rect(self.screen, COL_ITEM, self._new_btn, border_radius=9)
        self.screen.blit(self.font_small.render("+  Nouvelle partie", True, COL_TEXT),
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
