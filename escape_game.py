# -*- coding: utf-8 -*-
"""
Escape Game texte — tu es enferme, trouve comment sortir !

Tape des actions en francais : regarder, examiner <objet>, prendre <objet>,
inventaire, code <chiffres>, aide. Resous les enigmes et echappe-toi.
Hors-ligne, gratuit. Meme interface que tes autres bots.

LANCER :  python escape_game.py     (pip install pygame)
"""

import os
import re
import sys
import json
import pygame


def _strip_accents(s):
    return s.translate(str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc"))


_HERE = os.path.dirname(os.path.abspath(__file__))
CONV_FILE = os.path.join(_HERE, "escape_conversations.json")

CODE = "472"   # pot=4, tableau=7, livre=2


def _fresh_state():
    return {"has_key": False, "drawer": False, "d1": False, "d2": False,
            "d3": False, "inv": [], "win": False}


def room_desc():
    return ("Tu es enferme dans une piece mysterieuse. Tu vois : un TAPIS use, "
            "un BUREAU avec un tiroir, un grand TABLEAU au mur, une "
            "BIBLIOTHEQUE pleine de livres, un POT de fleur, et une PORTE "
            "fermee par un cadenas a 3 chiffres.")


def start_message():
    return ("ESCAPE GAME - Echappe-toi de cette piece !\n"
            "Commandes : regarder, examiner <objet>, prendre <objet>, "
            "inventaire, code <chiffres>, aide.\n\n" + room_desc())


def _hint(st):
    if not st["has_key"]:
        return "Indice : le sol cache parfois des choses... un TAPIS, ca se souleve."
    if not st["drawer"]:
        return "Indice : tu as une cle. Qu'est-ce qui est verrouille par ici ?"
    if not (st["d1"] and st["d2"] and st["d3"]):
        return "Indice : fouille le POT, le TABLEAU et un LIVRE pour les 3 chiffres."
    return "Indice : tu as tout ! Entre le code sur la porte, ex: « code 123 »."


def process(st, text):
    t = _strip_accents(text.lower())

    if st["win"]:
        if "recommenc" in t or "rejou" in t:
            st.update(_fresh_state())
            return "Nouvelle partie !\n\n" + room_desc()
        return "Tu es deja sorti ! Tape « recommencer » pour rejouer."

    if "recommenc" in t or "rejou" in t:
        st.update(_fresh_state())
        return "On recommence !\n\n" + room_desc()

    # tentative de code (3 chiffres)
    dg = re.sub(r"\D", "", t)
    if len(dg) >= 3:
        guess = dg[:3]
        if guess == CODE:
            st["win"] = True
            return ("CLIC ! Le cadenas s'ouvre, la porte grince... TU ES LIBRE ! "
                    "Bravo, tu t'es echappe ! (tape « recommencer » pour rejouer)")
        return f"Tu essaies le code {guess}... CLAC. Rien. Ce n'est pas le bon."

    if "inventaire" in t or "sac" in t:
        return ("Ton sac est vide." if not st["inv"]
                else "Dans ton sac : " + ", ".join(st["inv"]) + ".")

    if "aide" in t or "indice" in t:
        return _hint(st)

    # TAPIS
    if "tapis" in t:
        if st["has_key"]:
            return "Tu as deja recupere la cle qui etait sous le tapis."
        st["has_key"] = True
        st["inv"].append("cle")
        return "Tu souleves le tapis... une petite CLE etait cachee dessous ! (prise)"

    # BUREAU / TIROIR
    if "tiroir" in t or "bureau" in t:
        if st["drawer"]:
            return ("Le tiroir est ouvert. Le papier dit : « code = pot, puis "
                    "tableau, puis livre ».")
        if st["has_key"]:
            st["drawer"] = True
            st["inv"].append("papier (ordre du code)")
            return ("Avec la cle, tu ouvres le tiroir ! Dedans, un papier : "
                    "« Le code a 3 chiffres : d'abord le POT, puis le TABLEAU, "
                    "puis le LIVRE. »")
        return "Le tiroir est verrouille. Il te faudrait une cle..."

    # POT
    if "pot" in t:
        if not st["d1"]:
            st["d1"] = True
            return "Tu fouilles le pot de fleur... grave dans la terre : 1er chiffre = 4."
        return "Tu connais deja le 1er chiffre (4)."

    # TABLEAU
    if "tableau" in t:
        if not st["d2"]:
            st["d2"] = True
            return "Tu regardes derriere le tableau... une inscription : 2e chiffre = 7."
        return "Tu connais deja le 2e chiffre (7)."

    # LIVRE / BIBLIOTHEQUE
    if "livre" in t or "biblio" in t:
        if not st["d3"]:
            st["d3"] = True
            return "Tu ouvres un vieux livre... une page cornee indique : 3e chiffre = 2."
        return "Tu connais deja le 3e chiffre (2)."

    # PORTE
    if "porte" in t or "cadenas" in t or "sortir" in t or "sors" in t:
        return ("La porte est fermee par un cadenas a 3 chiffres. Entre le code, "
                "par exemple : « code 123 ».")

    # REGARDER autour
    if "regard" in t or "autour" in t or "piece" in t or "salle" in t or "ou suis" in t:
        return room_desc()

    return ("Je ne comprends pas. Essaie : regarder, examiner tapis, ouvrir "
            "tiroir, examiner pot / tableau / livre, code <chiffres>, aide.")


# ======================================================================
#  UI PYGAME
# ======================================================================
WIDTH, HEIGHT = 980, 640
FPS = 60
COL_BG        = (22, 24, 26)
COL_SIDEBAR   = (17, 19, 20)
COL_ITEM      = (40, 44, 46)
COL_ITEM_ON   = (54, 60, 62)
COL_TRASH     = (200, 128, 120)
COL_DANGER    = (198, 92, 78)
COL_ASSISTANT = (40, 44, 46)
COL_USER      = (58, 66, 70)
COL_TEXT      = (232, 236, 234)
COL_MUTED     = (146, 156, 154)
COL_GAME      = (120, 220, 170)
COL_INPUT_BG  = (46, 52, 54)
COL_INPUT_BRD = (80, 90, 90)
COL_ACCENT    = (70, 200, 150)
COL_SCROLL    = (80, 90, 90)
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
        pygame.display.set_caption("Escape Game texte")
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
        n = len(getattr(self, "chats", [])) + 1
        st = _fresh_state()
        return {"name": f"Evasion {n}", "state": st,
                "messages": [("assistant", start_message(), True)]}

    def _load_conversations(self):
        try:
            with open(CONV_FILE, encoding="utf-8") as f:
                data = json.load(f)
            chats = []
            for ch in data.get("chats", []):
                msgs = [tuple(m) for m in ch.get("messages", [])]
                st = ch.get("state") or _fresh_state()
                for k, v in _fresh_state().items():
                    st.setdefault(k, v)
                if not msgs:
                    msgs = [("assistant", start_message(), True)]
                chats.append({"name": ch.get("name", "Evasion"),
                              "state": st, "messages": msgs})
            if chats:
                return chats
        except Exception:  # noqa: BLE001
            pass
        return [self._new_chat()]

    def _save_conversations(self):
        data = {"chats": [{"name": c["name"], "state": c.get("state", {}),
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
            self.chats = [self._new_chat()]
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
        if not text:
            return
        chat = self.chats[self.active]
        chat["messages"].append(("user", text, False))
        st = chat["state"]
        msg = process(st, text)
        chat["state"] = st
        chat["messages"].append(("assistant", msg, st.get("win", False)))
        self.input_text = ""
        self.scroll = 0

    def update(self):
        self.cursor_timer += 1
        if self.cursor_timer >= 30:
            self.cursor_timer = 0
            self.cursor_visible = not self.cursor_visible
        if self.saved_timer > 0:
            self.saved_timer -= 1

    def draw_message(self, surface, role, text, is_win, y, content_w):
        is_user = role == "user"
        bubble_col = COL_USER if is_user else COL_ASSISTANT
        txt_col = COL_GAME if is_win else COL_TEXT
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
        label = "Toi" if is_user else "Narrateur"
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

        self.screen.blit(self.font_title.render("Escape Game texte", True, COL_GAME),
                         (PAD, 12))
        sub = self.font_small.render(
            "tape des actions pour t'echapper  •  « aide » si tu bloques",
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

        self.max_scroll = max(0, total_h - view_h)
        self.scroll = max(0, min(self.scroll, self.max_scroll))
        offset = total_h - view_h - self.scroll
        if total_h <= view_h:
            offset = 0

        y = PAD - offset
        for (role, text, is_win), hgt in zip(self.messages, heights):
            if y + hgt > 0 and y < view_h:
                self.draw_message(chat_surf, role, text, is_win, y, content_w)
            y += hgt

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
            ph = self.font.render("Ton action (ex: examiner tapis)...", True, COL_MUTED)
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

        self.screen.blit(self.font_small.render("EVASIONS", True, COL_MUTED),
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
