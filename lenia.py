"""
Lenia - automate cellulaire continu (inspire des travaux de Bert Chan),
avec un mode "laboratoire d'evolution" ou une population de creatures
aux parametres differents (genomes) est selectionnee generation apres
generation pour sa capacite a survivre et a se deplacer.

Dependances :
    pip install pygame numpy

Lancement :
    python lenia.py
"""

import sys
import numpy as np
import pygame

# ---------------------------------------------------------------- parametres
GRID = 192          # taille de la grille (GRID x GRID) en mode libre
SCALE = 4           # pixels par cellule en mode libre
HUD_H = 150         # hauteur du bandeau d'infos (avec barre de vitesse)
W, H = GRID * SCALE, GRID * SCALE
FPS = 60

BG = (12, 12, 18)
FG = (225, 228, 240)
DIM = (120, 126, 150)
ACCENT = (240, 200, 70)
GOOD = (110, 210, 140)
BAD = (200, 90, 90)

T_MIN, T_MAX = 1.0, 60.0   # bornes de la "vitesse" (T petit = rapide)

# ------------------------------------------------------- laboratoire d'evolution
POP_COLS, POP_ROWS = 5, 4          # disposition de la population (20 individus)
POP_N = POP_COLS * POP_ROWS
POP_SIZE = 56                      # resolution de chaque mini-simulation
GEN_STEPS = 360                    # duree d'une generation, en pas de simulation
WARMUP = 25                        # pas ignores avant de mesurer le deplacement
SUBSTEPS = 3                       # pas de simulation calcules par image affichee
ELITE_FRAC = 0.25                  # fraction de la population conservee telle quelle


def t_to_frac(t):
    """Convertit T en position de curseur [0,1] (0=lent, 1=rapide), echelle log."""
    t = np.clip(t, T_MIN, T_MAX)
    return 1.0 - (np.log(t) - np.log(T_MIN)) / (np.log(T_MAX) - np.log(T_MIN))


def frac_to_t(f):
    """Convertit une position de curseur [0,1] en T, echelle log."""
    f = np.clip(f, 0.0, 1.0)
    return float(T_MIN * (T_MAX / T_MIN) ** (1.0 - f))


# ------------------------------------------------------------------ presets
# R     : rayon du noyau
# T     : "temps" -> dt = 1/T (plus grand = evolution plus douce)
# mu/s  : centre et largeur de la fonction de croissance
# betas : poids des anneaux concentriques du noyau
PRESETS = [
    dict(name="Orbium",   R=13, T=10, mu=0.150, sigma=0.0170, betas=[1.0]),
    dict(name="Anneaux",  R=18, T=10, mu=0.220, sigma=0.0300, betas=[1.0, 0.66]),
    dict(name="Tissu",    R=16, T=12, mu=0.280, sigma=0.0480, betas=[0.5, 1.0, 0.66]),
    dict(name="Nuages",   R=20, T=8,  mu=0.310, sigma=0.0580, betas=[1.0, 0.33, 0.66]),
]


def bell(x, m, s):
    """Cloche gaussienne normalisee a 1 en x = m."""
    return np.exp(-(((x - m) / s) ** 2) / 2)


def build_kernel(R, betas, n):
    """Construit le noyau annulaire et retourne sa FFT (pret pour convolution)."""
    xs = np.arange(n) - n // 2
    X, Y = np.meshgrid(xs, xs)
    B = len(betas)
    D = np.sqrt(X ** 2 + Y ** 2) / R * B          # distance en "numero d'anneau"
    idx = np.clip(D.astype(int), 0, B - 1)
    weights = np.asarray(betas, dtype=float)[idx]
    K = (D < B) * weights * bell(D % 1, 0.5, 0.15)
    total = K.sum()
    if total == 0:
        total = 1.0
    K = K / total
    return K, np.fft.rfft2(np.fft.fftshift(K))


def make_palette():
    """LUT 256 couleurs : noir -> bleu profond -> turquoise -> jaune -> blanc."""
    stops = [
        (0.00, (8, 8, 20)),
        (0.25, (20, 40, 110)),
        (0.50, (20, 160, 170)),
        (0.75, (240, 200, 70)),
        (1.00, (255, 255, 245)),
    ]
    lut = np.zeros((256, 3), dtype=np.uint8)
    for i in range(256):
        t = i / 255.0
        for j in range(len(stops) - 1):
            t0, c0 = stops[j]
            t1, c1 = stops[j + 1]
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0)
                lut[i] = [int(c0[k] + (c1[k] - c0[k]) * f) for k in range(3)]
                break
    return lut


class Lenia:
    """Simulation libre : une seule grille haute resolution, pilotable a la main."""

    def __init__(self, preset):
        self.load_preset(preset)
        self.A = np.zeros((GRID, GRID))
        self.seed()

    def load_preset(self, p):
        self.name = p["name"]
        self.R = p["R"]
        self.T = p["T"]
        self.mu = p["mu"]
        self.sigma = p["sigma"]
        self.betas = list(p["betas"])
        self.rebuild()

    def rebuild(self):
        self.K, self.fK = build_kernel(self.R, self.betas, GRID)

    def seed(self, n_blobs=3):
        """Depose quelques taches de bruit grossier au centre."""
        self.A[:] = 0
        size = self.R * 4
        for _ in range(n_blobs):
            small = np.random.rand(size // self.R * 2, size // self.R * 2)
            blob = np.repeat(np.repeat(small, self.R // 2, axis=0), self.R // 2, axis=1)
            bh, bw = blob.shape
            cy = np.random.randint(GRID // 4, 3 * GRID // 4 - bh)
            cx = np.random.randint(GRID // 4, 3 * GRID // 4 - bw)
            self.A[cy:cy + bh, cx:cx + bw] = np.maximum(
                self.A[cy:cy + bh, cx:cx + bw], blob
            )

    def clear(self):
        self.A[:] = 0

    def paint(self, cx, cy, radius, value=1.0):
        """Peint un disque doux (ou efface si value = 0)."""
        y, x = np.ogrid[-cy:GRID - cy, -cx:GRID - cx]
        d = np.sqrt(x * x + y * y)
        mask = d <= radius
        soft = np.clip(1.0 - d / max(radius, 1e-6), 0, 1)
        if value > 0:
            self.A[mask] = np.maximum(self.A[mask], (soft * value)[mask])
        else:
            self.A[mask] = 0.0

    def step(self):
        U = np.real(np.fft.irfft2(self.fK * np.fft.rfft2(self.A), s=self.A.shape))
        G = bell(U, self.mu, self.sigma) * 2 - 1      # croissance dans [-1, 1]
        self.A = np.clip(self.A + G / self.T, 0, 1)


# ==================================================================
#                     LABORATOIRE D'EVOLUTION
# ==================================================================

def random_genome():
    """Genome aleatoire : R, T, mu, sigma et 1 a 3 anneaux (betas)."""
    nb = np.random.randint(1, 4)
    return dict(
        R=int(np.random.randint(6, 18)),
        T=float(np.random.uniform(6, 18)),
        mu=float(np.random.uniform(0.08, 0.35)),
        sigma=float(np.random.uniform(0.012, 0.05)),
        betas=[float(b) for b in np.random.uniform(0.4, 1.0, size=nb)],
    )


def mutate_genome(g):
    """Copie mutee d'un genome (petits pas, avec parfois un anneau en plus/moins)."""
    ng = dict(g)
    ng["R"] = int(np.clip(g["R"] + np.random.randint(-2, 3), 4, POP_SIZE // 2 - 2))
    ng["T"] = float(np.clip(g["T"] + np.random.normal(0, 1.3), 3, 30))
    ng["mu"] = float(np.clip(g["mu"] + np.random.normal(0, 0.018), 0.02, 0.5))
    ng["sigma"] = float(np.clip(g["sigma"] + np.random.normal(0, 0.007), 0.004, 0.12))

    betas = [float(np.clip(b + np.random.normal(0, 0.15), 0.05, 1.0)) for b in g["betas"]]
    if np.random.rand() < 0.12 and len(betas) < 3:
        betas.append(float(np.random.uniform(0.2, 1.0)))
    if np.random.rand() < 0.08 and len(betas) > 1:
        betas.pop(np.random.randint(len(betas)))
    ng["betas"] = betas
    return ng


class Population:
    """Une population de mini-Lenia simules en parallele (calcul vectorise)."""

    def __init__(self, n=POP_N, size=POP_SIZE):
        self.n = n
        self.size = size
        self.generation = 1
        self.genomes = [random_genome() for _ in range(n)]
        self.last_fitness = np.zeros(n)
        self.last_mass = np.zeros(n)
        self.best_genome_ever = None
        self.best_fitness_ever = -1e9
        self.best_generation_ever = 0
        self.build_kernels()
        self.start_generation()

    def build_kernels(self):
        fKs = []
        for g in self.genomes:
            _, fK = build_kernel(g["R"], g["betas"], self.size)
            fKs.append(fK)
        self.fK = np.stack(fKs, axis=0)
        self.mu = np.array([g["mu"] for g in self.genomes])
        self.sigma = np.array([g["sigma"] for g in self.genomes])
        self.T = np.array([g["T"] for g in self.genomes])

    def start_generation(self):
        """Prepare un terrain de depart identique pour tous les individus
        (equite : les differences de resultat viennent du genome, pas du hasard)."""
        n = self.size
        pattern = np.zeros((n, n))
        for _ in range(3):
            small = np.random.rand(6, 6)
            blob = np.repeat(np.repeat(small, 4, axis=0), 4, axis=1)
            bh, bw = blob.shape
            cy = np.random.randint(n // 4, 3 * n // 4 - bh)
            cx = np.random.randint(n // 4, 3 * n // 4 - bw)
            pattern[cy:cy + bh, cx:cx + bw] = np.maximum(
                pattern[cy:cy + bh, cx:cx + bw], blob
            )
        self.A = np.repeat(pattern[None, :, :], self.n, axis=0)
        self.step_count = 0
        self.prev_centroid = None
        self.total_move = np.zeros(self.n)
        ys, xs = np.mgrid[0:n, 0:n]
        self._ys = ys.astype(float)
        self._xs = xs.astype(float)

    def step(self):
        Afft = np.fft.rfft2(self.A, axes=(1, 2))
        U = np.real(np.fft.irfft2(
            self.fK * Afft, s=(self.size, self.size), axes=(1, 2)
        ))
        G = bell(U, self.mu[:, None, None], self.sigma[:, None, None]) * 2 - 1
        self.A = np.clip(self.A + G / self.T[:, None, None], 0, 1)

    def tick(self):
        """Avance d'un pas, mesure le deplacement, renvoie True si generation finie."""
        self.step()
        self.step_count += 1

        if self.step_count > WARMUP:
            mass = self.A.sum(axis=(1, 2))
            alive = mass > 1e-3
            safe_mass = np.where(alive, mass, 1.0)
            cy = (self.A * self._ys).sum(axis=(1, 2)) / safe_mass
            cx = (self.A * self._xs).sum(axis=(1, 2)) / safe_mass
            if self.prev_centroid is not None:
                dy = cy - self.prev_centroid[:, 0]
                dx = cx - self.prev_centroid[:, 1]
                dist = np.sqrt(dx ** 2 + dy ** 2)
                dist = np.where(dist > self.size * 0.4, 0, dist)  # ignore les sauts (bord toroidal)
                self.total_move += np.where(alive, dist, 0)
            self.prev_centroid = np.stack([cy, cx], axis=1)

        return self.step_count >= GEN_STEPS

    def current_mass(self):
        return self.A.sum(axis=(1, 2)) / (self.size * self.size)

    def evaluate(self):
        mass = self.current_mass()
        alive = (mass > 0.015) & (mass < 0.85)
        avg_speed = self.total_move / max(1, GEN_STEPS - WARMUP)
        fitness = np.where(alive, avg_speed, -1.0)
        return fitness, mass

    def evolve(self):
        """Classe la population, garde une elite, remplit le reste par mutation."""
        fitness, mass = self.evaluate()
        order = np.argsort(-fitness)
        self.genomes = [self.genomes[i] for i in order]
        self.last_fitness = fitness[order]
        self.last_mass = mass[order]

        if self.last_fitness[0] > self.best_fitness_ever:
            self.best_fitness_ever = float(self.last_fitness[0])
            self.best_genome_ever = dict(self.genomes[0])
            self.best_generation_ever = self.generation

        elite = max(2, int(self.n * ELITE_FRAC))
        pool = max(elite, self.n // 2)
        new_genomes = [dict(g) for g in self.genomes[:elite]]
        while len(new_genomes) < self.n:
            parent = self.genomes[np.random.randint(0, pool)]
            new_genomes.append(mutate_genome(parent))
        self.genomes = new_genomes

        self.generation += 1
        self.build_kernels()
        self.start_generation()


def genome_to_preset(g, gen):
    p = dict(g)
    p["name"] = f"Evolue (gen {gen})"
    return p


def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H + HUD_H))
    pygame.display.set_caption("Lenia - automate cellulaire continu")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas,menlo,monospace", 15)
    small = pygame.font.SysFont("consolas,menlo,monospace", 13)
    tiny = pygame.font.SysFont("consolas,menlo,monospace", 11)

    lut = make_palette()
    preset_idx = 0
    world = Lenia(PRESETS[preset_idx])
    population = None            # cree a la demande (touche E)

    mode = "free"                # "free" ou "evo"
    paused = False
    show_kernel = False
    brush = 8
    step_once = False

    # camera : zoom et coin haut-gauche visible (en cellules, flottant)
    zoom = 1.0
    ox, oy = 0.0, 0.0
    panning = False
    pan_anchor = (0, 0)
    dragging_speed = False

    slider_rect = pygame.Rect(14, H + HUD_H - 34, W - 28, 14)

    def apply_slider(px):
        f = (px - slider_rect.x) / slider_rect.w
        world.T = frac_to_t(f)

    def cell_px():
        return SCALE * zoom

    def clamp_view():
        """Garde la vue a l'interieur de la grille."""
        nonlocal ox, oy
        view = GRID / zoom
        ox = float(np.clip(ox, 0, max(0.0, GRID - view)))
        oy = float(np.clip(oy, 0, max(0.0, GRID - view)))

    def screen_to_grid(px, py):
        return ox + px / cell_px(), oy + py / cell_px()

    def set_zoom(new_zoom, anchor):
        """Zoome en gardant le point de la grille sous 'anchor' immobile."""
        nonlocal zoom, ox, oy
        ax, ay = anchor
        gx, gy = screen_to_grid(ax, ay)
        zoom = float(np.clip(new_zoom, 1.0, 16.0))
        ox = gx - ax / cell_px()
        oy = gy - ay / cell_px()
        clamp_view()

    def load_into_world(genome, label):
        world.load_preset(genome_to_preset(genome, label))
        world.seed()

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.quit()
                    sys.exit()
                elif e.key == pygame.K_SPACE:
                    paused = not paused
                elif e.key == pygame.K_e:
                    if population is None:
                        population = Population()
                    mode = "evo" if mode == "free" else "free"
                elif e.key == pygame.K_l and mode == "evo" and population is not None \
                        and population.best_genome_ever is not None:
                    load_into_world(population.best_genome_ever,
                                     population.best_generation_ever)
                    mode = "free"
                    zoom, ox, oy = 1.0, 0.0, 0.0
                elif e.key == pygame.K_n:
                    step_once = True
                elif e.key == pygame.K_r:
                    if mode == "free":
                        world.seed()
                    else:
                        population = Population()
                elif e.key == pygame.K_c and mode == "free":
                    world.clear()
                elif e.key in (pygame.K_0, pygame.K_KP0) and mode == "free":
                    zoom, ox, oy = 1.0, 0.0, 0.0
                elif e.key == pygame.K_k and mode == "free":
                    show_kernel = not show_kernel
                elif e.key == pygame.K_s:
                    pygame.image.save(screen, "lenia_capture.png")
                elif pygame.K_1 <= e.key <= pygame.K_4 and mode == "free":
                    preset_idx = e.key - pygame.K_1
                    if preset_idx < len(PRESETS):
                        world.load_preset(PRESETS[preset_idx])
                        world.seed()

            elif e.type == pygame.MOUSEWHEEL and mode == "free":
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_SHIFT:
                    brush = int(np.clip(brush + e.y, 2, 40))
                else:
                    px, py = pygame.mouse.get_pos()
                    py = min(py, H - 1)
                    set_zoom(zoom * (1.15 ** e.y), (px, py))

            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if slider_rect.collidepoint(e.pos):
                    dragging_speed = True
                    apply_slider(e.pos[0])

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                dragging_speed = False

            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 2 and mode == "free":
                panning = True
                pan_anchor = e.pos

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 2:
                panning = False

            elif e.type == pygame.MOUSEMOTION and dragging_speed:
                apply_slider(e.pos[0])

            elif e.type == pygame.MOUSEMOTION and panning and mode == "free":
                dx, dy = e.rel
                ox -= dx / cell_px()
                oy -= dy / cell_px()
                clamp_view()

        if mode == "free":
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]:
                world.mu = float(np.clip(world.mu + 0.0008, 0.0, 0.6))
            if keys[pygame.K_DOWN]:
                world.mu = float(np.clip(world.mu - 0.0008, 0.0, 0.6))
            if keys[pygame.K_RIGHT]:
                world.sigma = float(np.clip(world.sigma + 0.0002, 0.001, 0.15))
            if keys[pygame.K_LEFT]:
                world.sigma = float(np.clip(world.sigma - 0.0002, 0.001, 0.15))
            if keys[pygame.K_LEFTBRACKET]:
                world.T = float(np.clip(world.T - 0.1, 1, 60))
            if keys[pygame.K_RIGHTBRACKET]:
                world.T = float(np.clip(world.T + 0.1, 1, 60))

        mx, my = pygame.mouse.get_pos()
        btn = pygame.mouse.get_pressed()
        if mode == "free" and my < H and (btn[0] or btn[2]) and not panning:
            gx, gy = screen_to_grid(mx, my)
            world.paint(int(gx), int(gy), brush, 1.0 if btn[0] else 0.0)

        # -------------------------------------------------------- simulation
        if mode == "free":
            if not paused or step_once:
                world.step()
                step_once = False
        else:
            if not paused or step_once:
                for _ in range(SUBSTEPS if not step_once else 1):
                    finished = population.tick()
                    if finished:
                        population.evolve()
                        break
                step_once = False

        # ------------------------------------------------------------ rendu
        if mode == "free":
            cp = cell_px()
            view = GRID / zoom                    # nb de cellules visibles par cote
            x0, y0 = int(ox), int(oy)             # premiere cellule visible (entiere)
            n = int(np.ceil(view)) + 1            # une cellule de marge
            n = min(n, GRID)
            x0 = min(x0, GRID - n)
            y0 = min(y0, GRID - n)

            sub = world.A[y0:y0 + n, x0:x0 + n]
            rgb = lut[(sub * 255).astype(np.uint8)]
            surf = pygame.surfarray.make_surface(np.transpose(rgb, (1, 0, 2)))
            surf = pygame.transform.scale(surf, (int(n * cp) + 1, int(n * cp) + 1))
            screen.blit(surf, (-(ox - x0) * cp, -(oy - y0) * cp))

            if show_kernel:
                kn = world.K / (world.K.max() or 1)
                crop = world.R * 3
                c = GRID // 2
                sub = kn[c - crop:c + crop, c - crop:c + crop]
                ki = (sub * 255).astype(np.uint8)
                ks = pygame.surfarray.make_surface(
                    np.transpose(lut[ki], (1, 0, 2))
                )
                ks = pygame.transform.scale(ks, (140, 140))
                screen.blit(ks, (W - 150, 10))
                pygame.draw.rect(screen, DIM, (W - 150, 10, 140, 140), 1)

            if my < H:
                pygame.draw.circle(screen, (255, 255, 255), (mx, my),
                                   max(1, int(brush * cp)), 1)
        else:
            screen.fill(BG, (0, 0, W, H))
            pad = 6
            pw = W // POP_COLS
            ph = H // POP_ROWS
            fitness_now, mass_now = population.evaluate()
            ranked = np.argsort(-fitness_now)
            rank_of = np.empty(population.n, dtype=int)
            rank_of[ranked] = np.arange(population.n)

            for i in range(population.n):
                col = i % POP_COLS
                row = i // POP_COLS
                px0, py0 = col * pw, row * ph
                cell = population.A[i]
                rgb = lut[(cell * 255).astype(np.uint8)]
                surf = pygame.surfarray.make_surface(np.transpose(rgb, (1, 0, 2)))
                surf = pygame.transform.scale(surf, (pw - pad, ph - pad))
                screen.blit(surf, (px0 + pad // 2, py0 + pad // 2))

                mass = mass_now[i]
                alive = 0.015 < mass < 0.85
                border = GOOD if alive else BAD
                if rank_of[i] == 0:
                    border = ACCENT
                pygame.draw.rect(
                    screen, border,
                    (px0 + pad // 2, py0 + pad // 2, pw - pad, ph - pad), 2
                )
                tag = tiny.render(f"#{i}  m={mass:.2f}", True, FG)
                screen.blit(tag, (px0 + pad, py0 + pad))

            # barre de progression de la generation en cours
            prog = min(1.0, population.step_count / GEN_STEPS)
            bar = pygame.Rect(0, H - 6, int(W * prog), 6)
            pygame.draw.rect(screen, ACCENT, bar)

        # ------------------------------------------------------------- HUD
        pygame.draw.rect(screen, BG, (0, H, W, HUD_H))
        pygame.draw.line(screen, (40, 42, 55), (0, H), (W, H))

        if mode == "free":
            mass = world.A.sum() / (GRID * GRID)
            l1 = (f"[MODE LIBRE] [{preset_idx + 1}] {world.name}    "
                  f"R={world.R}  T={world.T:.1f}  mu={world.mu:.4f}  "
                  f"sigma={world.sigma:.4f}  masse={mass:.4f}")
            l2 = "ESPACE pause   N pas-a-pas   R reseed   C effacer   1-4 presets   K noyau   S capture   E evolution"
            l3 = ("HAUT/BAS mu   GAUCHE/DROITE sigma   molette ZOOM   "
                  "Maj+molette pinceau   clic milieu deplacer   0 recentrer")
            l4 = (f"{clock.get_fps():5.1f} fps   zoom x{zoom:.2f}   pinceau={brush}   "
                  f"{'PAUSE' if paused else 'EN COURS'}")

            for i, (txt, f, col) in enumerate([
                (l1, font, FG), (l2, small, DIM), (l3, small, DIM), (l4, small, FG)
            ]):
                screen.blit(f.render(txt, True, col), (12, H + 10 + i * 22))

            # --- barre de vitesse (glissable a la souris) ---
            speed_label = small.render(
                f"VITESSE  (T={world.T:4.1f}, lisser={1/world.T:.3f})", True, DIM
            )
            screen.blit(speed_label, (slider_rect.x, slider_rect.y - 18))

            pygame.draw.rect(screen, (34, 36, 48), slider_rect, border_radius=7)
            frac = t_to_frac(world.T)
            fill_w = int(slider_rect.w * frac)
            if fill_w > 0:
                fill_rect = pygame.Rect(slider_rect.x, slider_rect.y, fill_w, slider_rect.h)
                pygame.draw.rect(screen, ACCENT, fill_rect, border_radius=7)
            pygame.draw.rect(screen, (60, 63, 80), slider_rect, 1, border_radius=7)

            knob_x = slider_rect.x + fill_w
            knob_y = slider_rect.y + slider_rect.h // 2
            knob_r = 11 if dragging_speed else 9
            pygame.draw.circle(screen, (255, 255, 255), (knob_x, knob_y), knob_r)
            pygame.draw.circle(screen, ACCENT, (knob_x, knob_y), knob_r, 2)

            lente = small.render("lent", True, DIM)
            rapide = small.render("rapide", True, DIM)
            screen.blit(lente, (slider_rect.x, slider_rect.bottom + 3))
            screen.blit(rapide, (slider_rect.right - rapide.get_width(), slider_rect.bottom + 3))

        else:
            best = population.best_genome_ever
            best_txt = "aucune (attends la fin de la 1ere generation)"
            if best is not None:
                betas_txt = ",".join(f"{b:.2f}" for b in best["betas"])
                best_txt = (f"gen {population.best_generation_ever}  vitesse={population.best_fitness_ever:.3f}  "
                            f"R={best['R']} T={best['T']:.1f} mu={best['mu']:.3f} "
                            f"sigma={best['sigma']:.3f} betas=[{betas_txt}]")

            l1 = f"[LABORATOIRE D'EVOLUTION]  generation {population.generation}   population={population.n}"
            l2 = f"meilleur jamais vu : {best_txt}"
            l3 = ("ESPACE pause   R nouvelle population   E retour au mode libre   "
                  "L charger le meilleur dans le mode libre pour l'observer en detail")
            l4 = (f"{clock.get_fps():5.1f} fps   progression generation : "
                  f"{min(100, int(100 * population.step_count / GEN_STEPS))}%   "
                  f"{'PAUSE' if paused else 'EN COURS'}     "
                  f"contour vert = vivant, rouge = eteint/explose, or = meilleur du lot")

            for i, (txt, f, col) in enumerate([
                (l1, font, FG), (l2, small, DIM), (l3, small, DIM), (l4, small, FG)
            ]):
                screen.blit(f.render(txt, True, col), (12, H + 10 + i * 22))

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()