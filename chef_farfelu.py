# -*- coding: utf-8 -*-
"""
Le Chef farfelu — donne des ingredients, recois une recette n'importe quoi.

Nom du plat, ingredients avec quantites absurdes, etapes loufoques et le mot
du chef. Hors-ligne, gratuit. Meme interface que tes autres bots.

LANCER :  python chef_farfelu.py     (pip install pygame)
"""

import os
import re
import sys
import json
import random
import pygame


def _strip_accents(s):
    return s.translate(str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc"))


_HERE = os.path.dirname(os.path.abspath(__file__))
CONV_FILE = os.path.join(_HERE, "chef_conversations.json")

# ---------- LE GENERATEUR DE RECETTES ----------
PLATS = ["Gratin", "Soupe", "Tarte", "Mousse", "Burger", "Smoothie", "Ragout",
         "Cake", "Salade", "Fondue", "Omelette", "Milkshake", "Pizza", "Flan"]
ADJ = ["surprise", "magique", "explosif", "extra-terrestre", "revisite",
       "du chef", "flambe", "givre", "turbo", "royal", "interdimensionnel",
       "de competition"]
QTE = ["3 cuilleres a soupe de", "un gros morceau de", "une pincee de",
       "2 kilos de", "un soupcon de", "500 g de", "une louche de",
       "une montagne de", "12", "un demi", "une brouette de", "3 gouttes de"]
ABSURD = ["chaussette propre (important)", "larmes de licorne",
          "poussiere d'etoile", "chewing-gum a la fraise",
          "confiture de cornichon", "eau de pluie de mardi", "peluche fondue",
          "sirop de brouillard", "cailloux polis", "mayonnaise du futur",
          "glacon carre parfait", "sel de dinosaure"]
STEPS = [
    "Melangez {ing} avec {abs} en chantant votre chanson preferee.",
    "Faites cuire {ing} a feu doux jusqu'a ce que ca sente vraiment bizarre.",
    "Ajoutez {abs} et remuez dans le sens des aiguilles d'une montre (crucial).",
    "Laissez reposer au frigo, a cote d'une {abs}, pour le gout.",
    "Saupoudrez de {abs} et decorez artistiquement avec {ing}.",
    "Ecrasez {ing} avec le poing en criant « CUISINE ! ».",
    "Faites sauter le tout dans la poele... et rattrapez-le, c'est le plus dur.",
    "Gouttez, grimacez, puis faites gouter a quelqu'un d'autre au cas ou.",
    "Servez chaud, froid ou tiede : de toute facon personne ne saura.",
    "Ajoutez {ing} au dernier moment pour l'effet dramatique.",
]
COMMENTS = [
    "Un delice... enfin, je crois.",
    "Etoile Michelin garantie (dans un univers parallele).",
    "Mon chat a adore. Mais bon, mon chat mange tout.",
    "A ne surtout pas refaire. Ou si. A toi de voir.",
    "Bon appetit, et surtout bonne chance.",
    "Recette approuvee par personne, mais approuvee quand meme.",
]


def _ingredients(text):
    parts = re.split(r",|;| et | avec | plus | \+ ", text, flags=re.I)
    ings = [p.strip() for p in parts if p.strip()]
    return ings or [text.strip() or "mystere"]


def recette(text):
    ings = _ingredients(text)
    main = ings[0]
    plat = random.choice(PLATS)
    adj = random.choice(ADJ)
    liaison = "au" if not main[:1].lower() in "aeiou" else "a l'"
    name = f"{plat} {adj} {liaison} {main}"

    diff = random.randint(1, 5)
    temps = random.choice([5, 10, 15, 25, 40, 60, 90, 120])

    lines = [f"=== {name.upper()} ===",
             f"Difficulte : {'#' * diff}{'-' * (5 - diff)}     Temps : {temps} min",
             "",
             "INGREDIENTS :"]
    for ing in ings:
        lines.append(f"  - {random.choice(QTE)} {ing}")
    for extra in random.sample(ABSURD, k=2):
        lines.append(f"  - {random.choice(QTE)} {extra}")

    lines.append("")
    lines.append("PREPARATION :")
    chosen = random.sample(STEPS, k=min(5, len(STEPS)))
    for i, tmpl in enumerate(chosen, 1):
        step = tmpl.format(ing=random.choice(ings), abs=random.choice(ABSURD))
        lines.append(f"  {i}. {step}")

    lines.append("")
    lines.append(f"Le mot du chef : \"{random.choice(COMMENTS)}\"")
    return "\n".join(lines)


def respond(text, history=None):
    text = text.strip()
    if not text:
        return "Donne-moi des ingredients (ex: banane, chocolat, chaussette) !", False
    return recette(text), True


# ======================================================================
#  UI PYGAME
# ======================================================================
WIDTH, HEIGHT = 980, 660
FPS = 60
COL_BG        = (34, 30, 26)
COL_SIDEBAR   = (26, 23, 20)
COL_ITEM      = (54, 48, 40)
COL_ITEM_ON   = (74, 64, 52)
COL_TRASH     = (210, 130, 110)
COL_DANGER    = (205, 95, 75)
COL_ASSISTANT = (52, 46, 40)
COL_USER      = (86, 74, 60)
COL_TEXT      = (240, 236, 228)
COL_MUTED     = (166, 158, 144)
COL_DISH      = (255, 190, 110)
COL_INPUT_BG  = (62, 56, 48)
COL_INPUT_BRD = (94, 86, 74)
COL_ACCENT    = (236, 150, 60)
COL_SCROLL    = (94, 86, 74)
PAD = 16
SIDEBAR_W = 240

GREETING = ("Bienvenue en cuisine ! Donne-moi des ingredients (separes par des "
            "virgules, ex: banane, chocolat, chaussette) et je t'invente une "
            "recette... disons... originale. A tes fourneaux !")


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
        pygame.display.set_caption("Le Chef farfelu")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        pygame.key.start_text_input()

        self.font = pygame.font.SysFont("consolas,couriernew,monospace", 19)
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

    # ---------- conversations ----------
    def _new_chat(self):
        return {"name": f"Recette {len(self.chats) + 1}",
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
                chats.append({"name": ch.get("name", "Recette"), "messages": msgs})
            if chats:
                return chats
        except Exception:  # noqa: BLE001
            pass
        return [{"name": "Recette 1", "messages": [("assistant", GREETING, False)]}]

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
        card, ok = respond(text)
        chat["messages"].append(("assistant", card, ok))
        self.input_text = ""
        self.scroll = 0

    def update(self):
        self.cursor_timer += 1
        if self.cursor_timer >= 30:
            self.cursor_timer = 0
            self.cursor_visible = not self.cursor_visible
        if self.saved_timer > 0:
            self.saved_timer -= 1

    def draw_message(self, surface, role, text, is_dish, y, content_w):
        is_user = role == "user"
        bubble_col = COL_USER if is_user else COL_ASSISTANT
        txt_col = COL_DISH if is_dish else COL_TEXT
        max_text_w = int(content_w * 0.82)
        lines = wrap_text(text, self.font, max_text_w)
        line_h = self.font.get_linesize()
        text_h = line_h * len(lines)
        bubble_w = max((self.font.size(l)[0] for l in lines), default=0) + PAD * 2
        bubble_w = min(bubble_w, max_text_w + PAD * 2)
        bubble_h = text_h + PAD * 2
        x = (PAD + content_w - bubble_w) if is_user else PAD
        pygame.draw.rect(surface, bubble_col,
                         pygame.Rect(x, y, bubble_w, bubble_h), border_radius=14)
        label = "Toi" if is_user else "Le Chef"
        surface.blit(self.font_small.render(label, True, COL_MUTED), (x + 4, y - 18))
        ty = y + PAD
        for line in lines:
            surface.blit(self.font.render(line, True, txt_col), (x + PAD, ty))
            ty += line_h
        return bubble_h + 34

    def _measure(self, text, content_w):
        max_text_w = int(content_w * 0.82)
        lines = wrap_text(text, self.font, max_text_w)
        return self.font.get_linesize() * len(lines) + PAD * 2 + 34

    def draw(self):
        self.screen.fill(COL_BG)
        w, h = self.screen.get_size()
        sidebar_x = max(360, w - SIDEBAR_W)
        chat_w = sidebar_x
        content_w = chat_w - PAD * 2

        self.screen.blit(self.font_title.render("Le Chef farfelu", True, COL_DISH),
                         (PAD, 12))
        sub = self.font_small.render(
            "donne des ingredients (avec des virgules), recois une recette folle",
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
        for (role, text, is_dish), hgt in zip(self.messages, heights):
            if y + hgt > 0 and y < view_h:
                self.draw_message(chat_surf, role, text, is_dish, y, content_w)
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
            ph = self.font.render("Ingredients (ex: banane, chocolat)...", True, COL_MUTED)
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

        self.screen.blit(self.font_small.render("RECETTES", True, COL_MUTED),
                         (x0 + 14, 16))

        self._new_btn = pygame.Rect(x0 + 12, 38, inner_w, 34)
        pygame.draw.rect(self.screen, COL_ITEM, self._new_btn, border_radius=9)
        self.screen.blit(self.font_small.render("+  Nouvelle recette", True, COL_TEXT),
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
