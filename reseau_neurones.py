# -*- coding: utf-8 -*-
"""
LE RESEAU DE NEURONES — une VRAIE IA que tu entraines en dessinant.

Tu dessines une forme (un chiffre, un coeur, une croix...), tu lui dis ce que
c'est, et il APPREND a la reconnaitre. Tout est code a la main : neurones,
propagation avant, retropropagation, descente de gradient. Aucune bibliotheque
d'IA, aucune connexion internet.

  - Dessine avec la souris (clic gauche = dessiner, clic droit = gommer)
  - Ecris le nom de la forme et Entree  -> ajoute un exemple et entraine
  - Bouton DEVINER (ou barre espace)    -> il predit ce que tu as dessine
  - Bouton ENTRAINER                    -> plus d'entrainement (meilleure IA)
  - Bouton EFFACER                      -> vide le dessin
  Le cerveau est sauve dans cerveau_reseau.json (il se souvient !)

LANCER :  python reseau_neurones.py     (pip install pygame)
"""

import os
import sys
import json
import math
import random
import threading
import pygame

_HERE = os.path.dirname(os.path.abspath(__file__))
BRAIN_FILE = os.path.join(_HERE, "cerveau_reseau.json")

GRID = 20                 # dessin 20x20 = 400 entrees (pixels plus fins)
N_IN = GRID * GRID
N_HID = 30                # neurones caches
LR = 0.12                 # vitesse d'apprentissage


# ======================================================================
#  LE RESEAU DE NEURONES (tout est fait a la main)
# ======================================================================
class Reseau:
    def __init__(self):
        self.labels = []                    # noms des classes
        self.samples = []                   # [(pixels[], index_label)]
        self.W1 = [[random.uniform(-0.3, 0.3) for _ in range(N_IN)]
                   for _ in range(N_HID)]
        self.b1 = [0.0] * N_HID
        self.W2 = []                        # une ligne par classe
        self.b2 = []
        self.epochs = 0
        self.load()

    # ---------- structure ----------
    def add_label(self, name):
        self.labels.append(name)
        self.W2.append([random.uniform(-0.3, 0.3) for _ in range(N_HID)])
        self.b2.append(0.0)
        return len(self.labels) - 1

    # ---------- propagation avant ----------
    def forward(self, x):
        h = []
        for j in range(N_HID):
            s = self.b1[j]
            wj = self.W1[j]
            for i, xi in enumerate(x):
                if xi:                       # les pixels vides ne comptent pas
                    s += wj[i] * xi
            h.append(math.tanh(s))
        o = []
        for k in range(len(self.labels)):
            s = self.b2[k]
            wk = self.W2[k]
            for j in range(N_HID):
                s += wk[j] * h[j]
            o.append(s)
        # softmax (probabilites)
        mx = max(o) if o else 0.0
        ex = [math.exp(v - mx) for v in o]
        tot = sum(ex) or 1.0
        p = [v / tot for v in ex]
        return h, p

    # ---------- retropropagation ----------
    def train_one(self, x, target, lr=LR):
        h, p = self.forward(x)
        n_out = len(self.labels)
        # erreur en sortie : dL/do = p - cible
        do = [p[k] - (1.0 if k == target else 0.0) for k in range(n_out)]
        # gradient vers la couche cachee (avec les anciens poids)
        dh = [0.0] * N_HID
        for j in range(N_HID):
            s = 0.0
            for k in range(n_out):
                s += do[k] * self.W2[k][j]
            dh[j] = s * (1.0 - h[j] * h[j])          # derivee de tanh
        # mise a jour W2 / b2
        for k in range(n_out):
            wk = self.W2[k]
            dk = do[k]
            for j in range(N_HID):
                wk[j] -= lr * dk * h[j]
            self.b2[k] -= lr * dk
        # mise a jour W1 / b1
        for j in range(N_HID):
            dj = dh[j]
            if dj == 0.0:
                continue
            wj = self.W1[j]
            for i, xi in enumerate(x):
                if xi:
                    wj[i] -= lr * dj * xi
            self.b1[j] -= lr * dj
        return -math.log(max(1e-9, p[target]))       # perte

    def train(self, epochs=25, progress=None):
        if not self.samples or not self.labels:
            return 0.0
        loss = 0.0
        for e in range(epochs):
            random.shuffle(self.samples)
            loss = 0.0
            for x, t in self.samples:
                loss += self.train_one(x, t)
            loss /= len(self.samples)
            self.epochs += 1
            if progress:
                progress(e + 1, epochs, loss)
        return loss

    def predict(self, x):
        if not self.labels:
            return None, []
        _h, p = self.forward(x)
        best = max(range(len(p)), key=lambda k: p[k])
        return best, p

    def accuracy(self):
        if not self.samples:
            return 0.0
        ok = 0
        for x, t in self.samples:
            b, _ = self.predict(x)
            if b == t:
                ok += 1
        return ok / len(self.samples)

    # ---------- persistance ----------
    def save(self):
        try:
            data = {"labels": self.labels, "W1": self.W1, "b1": self.b1,
                    "W2": self.W2, "b2": self.b2, "epochs": self.epochs,
                    "samples": [["".join("1" if v else "0" for v in x), t]
                                for x, t in self.samples]}
            with open(BRAIN_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:  # noqa: BLE001
            pass

    def load(self):
        try:
            with open(BRAIN_FILE, encoding="utf-8") as f:
                d = json.load(f)
            W1 = d.get("W1", [])
            # securite : si la taille du dessin a change, l'ancien cerveau
            # n'est plus compatible -> on repart proprement de zero
            if (len(W1) != N_HID or not W1 or len(W1[0]) != N_IN):
                return
            self.labels = d.get("labels", [])
            self.W1 = W1
            self.b1 = d.get("b1", self.b1)
            self.W2 = d.get("W2", [])
            self.b2 = d.get("b2", [])
            self.epochs = d.get("epochs", 0)
            self.samples = [([1.0 if c == "1" else 0.0 for c in s], t)
                            for s, t in d.get("samples", [])
                            if len(s) == N_IN and 0 <= t < len(self.labels)]
        except Exception:  # noqa: BLE001
            pass


NET = Reseau()

# ======================================================================
#  UI PYGAME
# ======================================================================
WIDTH, HEIGHT = 1020, 700
FPS = 60
COL_BG      = (22, 24, 32)
COL_PANEL   = (32, 36, 48)
COL_GRIDBG  = (250, 250, 252)
COL_INK     = (30, 32, 44)
COL_LINE    = (215, 218, 228)
COL_TEXT    = (234, 238, 248)
COL_MUTED   = (150, 158, 178)
COL_ACCENT  = (110, 200, 255)
COL_OK      = (120, 225, 150)
COL_WARN    = (255, 190, 110)
COL_BTN     = (52, 58, 76)
COL_BTN_HOV = (72, 80, 104)
PAD = 16
CELL = 18                 # cases plus petites


class NetApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Le Reseau de neurones - IA qui apprend")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        pygame.key.start_text_input()

        self.font = pygame.font.SysFont("segoeui,arial,sans", 18)
        self.font_s = pygame.font.SysFont("segoeui,arial,sans", 14)
        self.font_t = pygame.font.SysFont("segoeui,arial,sans", 23, bold=True)
        self.font_m = pygame.font.SysFont("consolas,couriernew,monospace", 16)

        self.grid = [0.0] * N_IN
        self.label_text = ""
        self.msg = "Dessine une forme, donne-lui un nom, et je l'apprendrai !"
        self.pred = None            # (index, probabilites)
        self.training = False
        self.train_info = ""
        self._lock = threading.Lock()
        self._btns = {}
        self.drawing = 0            # 1 = dessine, -1 = gomme
        pygame.key.set_repeat(300, 30)

    # ---------- dessin ----------
    def clear(self):
        self.grid = [0.0] * N_IN
        self.pred = None

    def paint(self, mx, my, gx, gy, value):
        col = (mx - gx) // CELL
        row = (my - gy) // CELL
        if 0 <= col < GRID and 0 <= row < GRID:
            # pinceau 2x2 pour un trait plus epais
            for dy in (0, 1):
                for dx in (0, 1):
                    c, r = col + dx, row + dy
                    if 0 <= c < GRID and 0 <= r < GRID:
                        self.grid[r * GRID + c] = value

    # ---------- actions ----------
    def add_sample(self):
        name = self.label_text.strip()
        if not name:
            self.msg = "Ecris d'abord le nom de la forme dessinee."
            return
        if not any(self.grid):
            self.msg = "Dessine quelque chose avant de l'apprendre !"
            return
        if name in NET.labels:
            idx = NET.labels.index(name)
        else:
            idx = NET.add_label(name)
        NET.samples.append((list(self.grid), idx))
        self.msg = f"Exemple ajoute pour « {name} » ({sum(1 for _x, t in NET.samples if t == idx)} au total). J'apprends..."
        self.label_text = ""
        self.start_training(20)

    def start_training(self, epochs):
        if self.training or not NET.samples:
            return
        self.training = True
        self.train_info = "Entrainement..."

        def work():
            def prog(e, tot, loss):
                with self._lock:
                    self.train_info = f"Entrainement {e}/{tot}  (erreur {loss:.3f})"
            NET.train(epochs, prog)
            NET.save()
            with self._lock:
                self.train_info = ""
                self.training = False

        threading.Thread(target=work, daemon=True).start()

    def guess(self):
        if not NET.labels:
            self.msg = "Je ne connais encore aucune forme. Apprends-m'en une !"
            return
        if not any(self.grid):
            self.msg = "Dessine quelque chose d'abord !"
            return
        best, p = NET.predict(self.grid)
        self.pred = (best, p)
        conf = p[best] * 100
        self.msg = f"Je pense que c'est « {NET.labels[best]} » ({conf:.0f}% sur)."

    def forget_all(self):
        NET.labels.clear()
        NET.samples.clear()
        NET.W2.clear()
        NET.b2.clear()
        NET.W1 = [[random.uniform(-0.3, 0.3) for _ in range(N_IN)]
                  for _ in range(N_HID)]
        NET.b1 = [0.0] * N_HID
        NET.epochs = 0
        NET.save()
        self.pred = None
        self.msg = "J'ai tout oublie. On recommence de zero !"

    # ---------- dessin ecran ----------
    def draw(self):
        self.screen.fill(COL_BG)
        w, h = self.screen.get_size()

        self.screen.blit(self.font_t.render("Le Reseau de neurones", True, COL_ACCENT),
                         (PAD, 12))
        self.screen.blit(self.font_s.render(
            f"une vraie IA : {N_IN} entrees -> {N_HID} neurones caches -> "
            f"{len(NET.labels)} sorties  •  {NET.epochs} cycles d'entrainement",
            True, COL_MUTED), (PAD, 42))

        # --- grille de dessin ---
        gx, gy = PAD, 76
        size = GRID * CELL
        pygame.draw.rect(self.screen, COL_GRIDBG, (gx - 4, gy - 4, size + 8, size + 8),
                         border_radius=8)
        for r in range(GRID):
            for c in range(GRID):
                v = self.grid[r * GRID + c]
                if v:
                    pygame.draw.rect(self.screen, COL_INK,
                                     (gx + c * CELL, gy + r * CELL, CELL, CELL))
        for i in range(GRID + 1):
            pygame.draw.line(self.screen, COL_LINE, (gx, gy + i * CELL),
                             (gx + size, gy + i * CELL))
            pygame.draw.line(self.screen, COL_LINE, (gx + i * CELL, gy),
                             (gx + i * CELL, gy + size))
        self._grid_pos = (gx, gy)

        self.screen.blit(self.font_s.render(
            "clic gauche = dessiner   -   clic droit = gommer", True, COL_MUTED),
            (gx, gy + size + 8))

        # --- boutons ---
        by = gy + size + 34
        self._btns = {}
        for i, (key, txt) in enumerate([("learn", "Apprendre"),
                                        ("guess", "Deviner"),
                                        ("train", "Entrainer +"),
                                        ("clear", "Effacer"),
                                        ("forget", "Tout oublier")]):
            r = pygame.Rect(gx + (i % 3) * 128, by + (i // 3) * 44, 120, 36)
            hov = r.collidepoint(pygame.mouse.get_pos())
            col = COL_BTN_HOV if hov else COL_BTN
            if key == "forget":
                col = (90, 50, 55) if not hov else (120, 62, 68)
            pygame.draw.rect(self.screen, col, r, border_radius=9)
            img = self.font_s.render(txt, True, COL_TEXT)
            self.screen.blit(img, (r.centerx - img.get_width() // 2,
                                   r.centery - img.get_height() // 2))
            self._btns[key] = r

        # --- champ nom ---
        iy = by + 96
        ibox = pygame.Rect(gx, iy, 372, 40)
        pygame.draw.rect(self.screen, COL_PANEL, ibox, border_radius=10)
        pygame.draw.rect(self.screen, COL_BTN_HOV, ibox, 1, border_radius=10)
        txt = self.label_text or "nom de la forme (ex: coeur) puis Entree"
        col = COL_TEXT if self.label_text else COL_MUTED
        self.screen.blit(self.font.render(txt[:34], True, col), (ibox.x + 10, ibox.y + 9))

        # --- panneau droit ---
        px = gx + size + 40
        pw = max(240, w - px - PAD)
        panel = pygame.Rect(px, 76, pw, h - 76 - PAD)
        pygame.draw.rect(self.screen, COL_PANEL, panel, border_radius=12)

        y = panel.y + 14
        self.screen.blit(self.font.render("Ce que je connais", True, COL_ACCENT),
                         (px + 14, y))
        y += 30
        if not NET.labels:
            self.screen.blit(self.font_s.render("(rien pour l'instant)", True, COL_MUTED),
                             (px + 14, y))
            y += 22
        for k, name in enumerate(NET.labels):
            n = sum(1 for _x, t in NET.samples if t == k)
            prob = self.pred[1][k] if self.pred and k < len(self.pred[1]) else 0.0
            barw = int((pw - 130) * prob)
            is_best = self.pred and self.pred[0] == k
            pygame.draw.rect(self.screen, (46, 52, 68),
                             (px + 14, y + 4, pw - 120, 14), border_radius=7)
            if barw > 0:
                pygame.draw.rect(self.screen, COL_OK if is_best else COL_ACCENT,
                                 (px + 14, y + 4, barw, 14), border_radius=7)
            self.screen.blit(self.font_s.render(f"{name} ({n})", True,
                                                COL_OK if is_best else COL_TEXT),
                             (px + 14, y - 12))
            if self.pred:
                self.screen.blit(self.font_s.render(f"{prob * 100:3.0f}%", True, COL_MUTED),
                                 (px + pw - 96, y - 2))
            y += 40
            if y > panel.bottom - 90:
                break

        # infos bas de panneau
        acc = NET.accuracy() * 100 if NET.samples else 0
        self.screen.blit(self.font_s.render(
            f"Exemples appris : {len(NET.samples)}", True, COL_MUTED),
            (px + 14, panel.bottom - 78))
        self.screen.blit(self.font_s.render(
            f"Reussite sur ses exemples : {acc:.0f}%", True,
            COL_OK if acc > 80 else COL_WARN), (px + 14, panel.bottom - 56))
        with self._lock:
            info = self.train_info
        if info:
            self.screen.blit(self.font_s.render(info, True, COL_WARN),
                             (px + 14, panel.bottom - 34))

        # message
        self.screen.blit(self.font.render(self.msg[:90], True, COL_TEXT),
                         (PAD, h - 30))
        pygame.display.flip()

    # ---------- evenements ----------
    def handle(self, e):
        if e.type == pygame.QUIT:
            NET.save()
            return False
        if e.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)
        elif e.type == pygame.MOUSEBUTTONDOWN:
            gx, gy = self._grid_pos
            if e.button == 1:
                for key, r in self._btns.items():
                    if r.collidepoint(e.pos):
                        {"learn": self.add_sample, "guess": self.guess,
                         "train": lambda: self.start_training(40),
                         "clear": self.clear, "forget": self.forget_all}[key]()
                        return True
                self.drawing = 1
                self.paint(e.pos[0], e.pos[1], gx, gy, 1.0)
            elif e.button == 3:
                self.drawing = -1
                self.paint(e.pos[0], e.pos[1], gx, gy, 0.0)
        elif e.type == pygame.MOUSEBUTTONUP:
            self.drawing = 0
        elif e.type == pygame.MOUSEMOTION and self.drawing:
            gx, gy = self._grid_pos
            self.paint(e.pos[0], e.pos[1], gx, gy,
                       1.0 if self.drawing > 0 else 0.0)
        elif e.type == pygame.TEXTINPUT:
            if len(self.label_text) < 24:
                self.label_text += e.text
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_RETURN:
                self.add_sample()
            elif e.key == pygame.K_BACKSPACE:
                self.label_text = self.label_text[:-1]
            elif e.key == pygame.K_SPACE and not self.label_text:
                self.guess()
            elif e.key == pygame.K_ESCAPE:
                NET.save()
                return False
        return True

    def run(self):
        self._grid_pos = (PAD, 76)
        running = True
        while running:
            for e in pygame.event.get():
                if not self.handle(e):
                    running = False
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    NetApp().run()
