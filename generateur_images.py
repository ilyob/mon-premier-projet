# -*- coding: utf-8 -*-
"""
Le Generateur d'images IA — decris une image, une IA la cree.

Tape une description (ex: "un chat astronaute qui mange une pizza"), le bot
l'envoie a un service gratuit et SANS CLE (Pollinations.ai), telecharge
l'image generee, l'affiche et la sauvegarde dans le dossier "images_ia".

Internet requis. LANCER :  python generateur_images.py   (pip install pygame)
"""

import os
import re
import sys
import json
import time
import random
import threading
import urllib.parse
import urllib.request
import pygame


def _strip_accents(s):
    return s.translate(str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc"))


_HERE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(_HERE, "images_ia")
GALLERY_FILE = os.path.join(IMG_DIR, "gallery.json")


def _safe_name(prompt):
    s = re.sub(r"[^A-Za-z0-9]+", "_", _strip_accents(prompt.lower()))
    return (s[:40].strip("_") or "image")


def download_image(prompt):
    """Genere et telecharge une image. Renvoie (fichier, erreur)."""
    try:
        url = ("https://image.pollinations.ai/prompt/"
               + urllib.parse.quote(prompt)
               + "?width=640&height=640&nologo=true&seed="
               + str(random.randint(1, 999999)))
        req = urllib.request.Request(url, headers={"User-Agent": "GenImg/1.0"})
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read()
        if not data or len(data) < 500:
            return None, "Reponse vide du service. Reessaie."
        os.makedirs(IMG_DIR, exist_ok=True)
        fname = f"{_safe_name(prompt)}_{int(time.time())}.jpg"
        path = os.path.join(IMG_DIR, fname)
        with open(path, "wb") as f:
            f.write(data)
        return path, None
    except Exception:  # noqa: BLE001
        return None, "Erreur : pas d'internet, ou service indisponible."


# ======================================================================
#  UI PYGAME
# ======================================================================
WIDTH, HEIGHT = 1000, 700
FPS = 60
COL_BG        = (30, 26, 38)
COL_SIDEBAR   = (23, 20, 30)
COL_ITEM      = (48, 42, 62)
COL_ITEM_ON   = (66, 56, 88)
COL_TEXT      = (238, 234, 246)
COL_MUTED     = (160, 150, 180)
COL_ERR       = (240, 150, 150)
COL_FRAME     = (90, 80, 120)
COL_INPUT_BG  = (56, 50, 74)
COL_INPUT_BRD = (92, 84, 120)
COL_ACCENT    = (200, 120, 235)
PAD = 16
SIDEBAR_W = 250


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


class ImageApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Le Generateur d'images IA")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        pygame.key.start_text_input()

        self.font = pygame.font.SysFont("segoeui,arial,sans", 20)
        self.font_small = pygame.font.SysFont("segoeui,arial,sans", 15)
        self.font_title = pygame.font.SysFont("segoeui,arial,sans", 22, bold=True)

        self.items = self._load_gallery()     # [{"prompt","file","surface"}]
        self.current = len(self.items) - 1
        if 0 <= self.current < len(self.items):
            self._load_surface(self.current)
        self.input_text = ""
        self.cursor_visible = True
        self.cursor_timer = 0
        self.thinking = False
        self.error_msg = ""
        self._result = None
        self._lock = threading.Lock()
        self._item_rects = []
        self._send_btn = None
        pygame.key.set_repeat(300, 30)

    # ---------- galerie ----------
    def _load_gallery(self):
        try:
            with open(GALLERY_FILE, encoding="utf-8") as f:
                data = json.load(f)
            items = []
            for it in data:
                path = it.get("file", "")
                if path and os.path.exists(path):
                    items.append({"prompt": it.get("prompt", ""),
                                  "file": path, "surface": None})
            return items
        except Exception:  # noqa: BLE001
            return []

    def _save_gallery(self):
        try:
            os.makedirs(IMG_DIR, exist_ok=True)
            data = [{"prompt": it["prompt"], "file": it["file"]} for it in self.items]
            with open(GALLERY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:  # noqa: BLE001
            pass

    def _load_surface(self, idx):
        it = self.items[idx]
        if it["surface"] is None and it["file"] and os.path.exists(it["file"]):
            try:
                it["surface"] = pygame.image.load(it["file"]).convert()
            except Exception:  # noqa: BLE001
                it["surface"] = None

    # ---------- generation ----------
    def generate(self):
        prompt = self.input_text.strip()
        if not prompt or self.thinking:
            return
        self.input_text = ""
        self.error_msg = ""
        self.thinking = True
        self._result = None
        threading.Thread(target=self._worker, args=(prompt,), daemon=True).start()

    def _worker(self, prompt):
        path, err = download_image(prompt)
        with self._lock:
            self._result = (prompt, path, err)

    def update(self):
        self.cursor_timer += 1
        if self.cursor_timer >= 30:
            self.cursor_timer = 0
            self.cursor_visible = not self.cursor_visible
        if self.thinking:
            with self._lock:
                res = self._result
            if res is not None:
                prompt, path, err = res
                self.thinking = False
                self._result = None
                if err:
                    self.error_msg = err
                elif path:
                    surf = None
                    try:
                        surf = pygame.image.load(path).convert()
                    except Exception:  # noqa: BLE001
                        surf = None
                    if surf is not None:
                        self.items.append({"prompt": prompt, "file": path,
                                           "surface": surf})
                        self.current = len(self.items) - 1
                        self._save_gallery()
                    else:
                        self.error_msg = "Image telechargee mais illisible."

    def open_item(self, idx):
        if 0 <= idx < len(self.items):
            self.current = idx
            self._load_surface(idx)
            self.error_msg = ""

    # ---------- dessin ----------
    def draw(self):
        self.screen.fill(COL_BG)
        w, h = self.screen.get_size()
        sidebar_x = max(420, w - SIDEBAR_W)
        chat_w = sidebar_x
        input_h = 52

        self.screen.blit(self.font_title.render("Le Generateur d'images IA",
                                                True, COL_ACCENT), (PAD, 12))
        sub = self.font_small.render(
            "decris une image, une IA la cree (via Pollinations, gratuit)",
            True, COL_MUTED)
        self.screen.blit(sub, (PAD, 40))
        pygame.draw.line(self.screen, COL_INPUT_BRD, (0, 62), (chat_w, 62), 1)

        # zone image
        area = pygame.Rect(PAD, 74, chat_w - PAD * 2,
                           h - 74 - input_h - PAD * 2 - 8)
        pygame.draw.rect(self.screen, (24, 21, 30), area, border_radius=12)
        pygame.draw.rect(self.screen, COL_FRAME, area, 1, border_radius=12)

        if self.thinking:
            dots = "." * (1 + (pygame.time.get_ticks() // 300) % 3)
            t = self.font.render("Generation en cours" + dots, True, COL_MUTED)
            self.screen.blit(t, (area.centerx - t.get_width() // 2,
                                 area.centery - 10))
        elif self.error_msg:
            t = self.font.render(self.error_msg, True, COL_ERR)
            self.screen.blit(t, (area.centerx - t.get_width() // 2,
                                 area.centery - 10))
        elif 0 <= self.current < len(self.items) and self.items[self.current]["surface"]:
            surf = self.items[self.current]["surface"]
            iw, ih = surf.get_size()
            cap_h = 28
            avail = pygame.Rect(area.x + 8, area.y + 8,
                                area.w - 16, area.h - 16 - cap_h)
            scale = min(avail.w / iw, avail.h / ih)
            nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
            try:
                scaled = pygame.transform.smoothscale(surf, (nw, nh))
            except Exception:  # noqa: BLE001
                scaled = pygame.transform.scale(surf, (nw, nh))
            self.screen.blit(scaled, (avail.centerx - nw // 2,
                                      avail.y + (avail.h - nh) // 2))
            cap = self.items[self.current]["prompt"]
            ci = self.font_small.render("« " + cap[:80] + " »", True, COL_MUTED)
            self.screen.blit(ci, (area.centerx - ci.get_width() // 2,
                                  area.bottom - cap_h + 4))
        else:
            t = self.font.render("Tape une description et appuie sur Entree",
                                 True, COL_MUTED)
            self.screen.blit(t, (area.centerx - t.get_width() // 2,
                                 area.centery - 10))

        # zone de saisie
        ibox = pygame.Rect(PAD, h - input_h - PAD, chat_w - PAD * 2, input_h)
        pygame.draw.rect(self.screen, COL_INPUT_BG, ibox, border_radius=14)
        pygame.draw.rect(self.screen, COL_INPUT_BRD, ibox, 1, border_radius=14)
        if not self.input_text and not self.thinking:
            ph = self.font.render("Ex: un chat astronaute qui mange une pizza...",
                                  True, COL_MUTED)
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
                                 (cx, ibox.y + 12), (cx, ibox.y + input_h - 12), 2)
        btn = pygame.Rect(ibox.right - 44, ibox.y + 8, 36, input_h - 16)
        pygame.draw.rect(self.screen, COL_ACCENT, btn, border_radius=10)
        cx, cy = btn.center
        pygame.draw.polygon(self.screen, COL_BG,
                            [(cx - 5, cy + 5), (cx, cy - 6), (cx + 5, cy + 5)])
        self._send_btn = btn

        self._draw_sidebar(sidebar_x, w, h)
        pygame.display.flip()

    def _draw_sidebar(self, x0, w, h):
        pygame.draw.rect(self.screen, COL_SIDEBAR, (x0, 0, w - x0, h))
        pygame.draw.line(self.screen, COL_INPUT_BRD, (x0, 0), (x0, h), 1)
        inner_w = (w - x0) - 24
        self.screen.blit(self.font_small.render("MES IMAGES", True, COL_MUTED),
                         (x0 + 14, 16))

        self._item_rects = []
        y = 44
        # les plus recentes en haut
        for i in range(len(self.items) - 1, -1, -1):
            if y + 30 > h - 40:
                break
            r = pygame.Rect(x0 + 12, y, inner_w, 30)
            pygame.draw.rect(self.screen,
                             COL_ITEM_ON if i == self.current else COL_ITEM,
                             r, border_radius=8)
            name = self.items[i]["prompt"]
            while self.font_small.size(name)[0] > inner_w - 16 and len(name) > 1:
                name = name[:-1]
            self.screen.blit(self.font_small.render(name, True, COL_TEXT),
                             (r.x + 8, r.y + 7))
            self._item_rects.append((r, i))
            y += 34

        note = self.font_small.render("Images sauvees dans: images_ia",
                                      True, COL_MUTED)
        self.screen.blit(note, (x0 + 14, h - 30))

    # ---------- evenements ----------
    def handle(self, event):
        global WIDTH, HEIGHT
        if event.type == pygame.QUIT:
            self._save_gallery()
            return False
        if event.type == pygame.VIDEORESIZE:
            WIDTH, HEIGHT = event.w, event.h
            self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._send_btn and self._send_btn.collidepoint(pos):
                self.generate()
            else:
                for r, i in self._item_rects:
                    if r.collidepoint(pos):
                        self.open_item(i)
                        break
        elif event.type == pygame.TEXTINPUT:
            if len(self.input_text) < 400:
                self.input_text += event.text
        elif event.type == pygame.KEYDOWN:
            if (event.mod & pygame.KMOD_CTRL) and event.key == pygame.K_v:
                paste = _clipboard_text()
                if paste:
                    self.input_text = (self.input_text + paste)[:400]
            elif event.key == pygame.K_RETURN:
                self.generate()
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.key == pygame.K_ESCAPE:
                self._save_gallery()
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
    ImageApp().run()
