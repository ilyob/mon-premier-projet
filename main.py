import pygame
import random
import math
import os
import sys
import pickle

# Dossier de base : à côté du .py normalement, ou à côté de l'.exe si le jeu est
# transformé en exécutable (PyInstaller). Sert à trouver le dossier "textures"
# et à ranger la sauvegarde au bon endroit, même depuis une clé USB.
if getattr(sys, "frozen", False):
    DOSSIER_BASE = os.path.dirname(sys.executable)
else:
    try:
        DOSSIER_BASE = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        DOSSIER_BASE = os.path.abspath(".")

pygame.init()

TAILLE_BLOC = 40
TAILLE_CHUNK = 16

# Portée du joueur : on ne peut casser un bloc ou toucher un mob à l'épée
# que dans un rayon de 10 blocs.
PORTEE = 10
PORTEE_PX = PORTEE * TAILLE_BLOC

# Vrai plein écran : résolution native de l'écran, sans bordures
fenetre = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
LARGEUR, HAUTEUR = fenetre.get_size()
pygame.display.set_caption("Minecraft 2D")
horloge = pygame.time.Clock()

police = pygame.font.SysFont(None, 28)
police_titre = pygame.font.SysFont(None, 40)

HERBE = (50, 180, 50)
TERRE = (130, 80, 40)
PIERRE = (120, 120, 120)
CIEL = (135, 206, 235)
BOIS = (90, 60, 30)
FEUILLES = (40, 150, 40)
EAU = (30, 100, 200)

# Minerais : couleurs inspirées des textures de Minecraft (pierre + pépites colorées)
CHARBON = (45, 45, 45)
FER = (216, 175, 147)
OR = (250, 210, 60)
REDSTONE = (170, 20, 20)
LAPIS = (30, 70, 200)
DIAMANT = (80, 220, 220)

# Profondeur générée d'emblée pour chaque colonne de chunk. Au-delà, le monde
# est étendu vers le bas à la demande (voir etendre_chunk) : il est donc infini
# verticalement, comme il est déjà infini horizontalement.
PROFONDEUR_INITIALE = 96

# Profondeur minimale (en blocs sous la surface) et rareté (1 chance sur N) de chaque minerai.
# Basé sur la génération réelle de Minecraft : le charbon est commun et peu profond,
# le fer est un peu plus profond, l'or/redstone/lapis nécessitent de creuser bien plus bas,
# et le diamant (le plus rare) n'apparaît que tout en bas du monde, comme dans le jeu original
# où il se concentre près de la limite inférieure de la carte (autour de Y=-59).
MINERAIS = [
    # (type_bloc, profondeur_min, rareté)
    (12, 22, 180),  # Diamant : très profond, très rare
    (10, 18, 70),   # Redstone : profond, rare
    (11, 14, 80),   # Lapis : profond, rare
    (9, 12, 70),    # Or : assez profond, peu commun
    (8, 4, 28),     # Fer : profondeur moyenne, courant
    (7, 2, 18),     # Charbon : peu profond, très courant
]

def tirer_bloc_souterrain(profondeur):
    # Teste les minerais du plus rare (diamant) au plus commun (charbon) pour
    # respecter leurs zones de profondeur sans qu'un minerai commun n'écrase un rare.
    for type_bloc, profondeur_min, rarete in MINERAIS:
        if profondeur >= profondeur_min and random.randint(1, rarete) == 1:
            return type_bloc
    return 3

def generer_chunk(chunk_x, hauteur_precedente):
    hauteur_actuelle = hauteur_precedente
    hauteurs = []
    random.seed(graine + chunk_x * 1000)

    for i in range(TAILLE_CHUNK):
        variation = random.randint(-1, 1)
        hauteur_actuelle = hauteur_actuelle + variation
        if hauteur_actuelle < 10:
            hauteur_actuelle = 10
        if hauteur_actuelle > 25:
            hauteur_actuelle = 25
        hauteurs.append(hauteur_actuelle)

    chunk = []
    for ligne in range(PROFONDEUR_INITIALE):
        rangee = []
        for colonne in range(TAILLE_CHUNK):
            surface = hauteurs[colonne]
            if ligne == surface:
                rangee.append(1)
            elif ligne > surface and ligne < surface + 3:
                rangee.append(2)
            elif ligne >= surface + 3:
                rangee.append(tirer_bloc_souterrain(ligne - surface))
            else:
                rangee.append(0)
        chunk.append(rangee)

    # Grottes : on creuse des tunnels sinueux dans la pierre
    nb_grottes = random.randint(1, 3)
    for _ in range(nb_grottes):
        # Point de départ de la grotte dans la pierre
        gx = random.randint(0, TAILLE_CHUNK - 1)
        gy = random.randint(hauteurs[gx] + 5, PROFONDEUR_INITIALE - 5)
        longueur = random.randint(20, 60)
        rayon = random.randint(1, 2)
        angle = random.uniform(0, 2 * math.pi)

        for _ in range(longueur):
            # Creuser un cercle à la position actuelle
            for dy in range(-rayon, rayon + 1):
                for dx in range(-rayon, rayon + 1):
                    if dx * dx + dy * dy <= rayon * rayon:
                        cx = int(gx + dx)
                        cy = int(gy + dy)
                        if 0 <= cx < TAILLE_CHUNK and 0 <= cy < PROFONDEUR_INITIALE:
                            if chunk[cy][cx] in [2, 3]:
                                chunk[cy][cx] = 0

            # Avancer dans la direction du tunnel avec légère déviation
            angle += random.uniform(-0.4, 0.4)
            gx += math.cos(angle)
            gy += math.sin(angle) * 0.5  # moins de déviation verticale

            # Rester dans les limites
            gx = max(0, min(TAILLE_CHUNK - 1, gx))
            gy = max(hauteurs[int(max(0, min(TAILLE_CHUNK-1, gx)))] + 3, min(PROFONDEUR_INITIALE - 3, gy))

    # Arbres
    for colonne in range(1, TAILLE_CHUNK - 1):
        if random.randint(1, 8) == 1:
            surface = hauteurs[colonne]
            hauteur_tronc = random.randint(3, 5)
            for h in range(1, hauteur_tronc + 1):
                ligne_tronc = surface - h
                if 0 <= ligne_tronc < PROFONDEUR_INITIALE:
                    chunk[ligne_tronc][colonne] = 4
            sommet = surface - hauteur_tronc
            for dx in range(-2, 3):
                for dy in range(-2, 1):
                    lf = sommet + dy
                    cf = colonne + dx
                    if 0 <= lf < PROFONDEUR_INITIALE and 0 <= cf < TAILLE_CHUNK:
                        if chunk[lf][cf] == 0:
                            chunk[lf][cf] = 5

    # Lacs
    for colonne in range(1, TAILLE_CHUNK - 2):
        if random.randint(1, 15) == 1:
            largeur_lac = random.randint(2, 4)
            surface = hauteurs[colonne]
            for dc in range(largeur_lac):
                if colonne + dc < TAILLE_CHUNK:
                    if 0 <= surface < PROFONDEUR_INITIALE:
                        chunk[surface][colonne + dc] = 6

    random.seed()
    return chunk, hauteur_actuelle, hauteurs

def couleur_bloc(type_bloc):
    if type_bloc == 1: return HERBE
    if type_bloc == 2: return TERRE
    if type_bloc == 3: return PIERRE
    if type_bloc == 4: return BOIS
    if type_bloc == 5: return FEUILLES
    if type_bloc == 6: return EAU
    if type_bloc == 7: return CHARBON
    if type_bloc == 8: return FER
    if type_bloc == 9: return OR
    if type_bloc == 10: return REDSTONE
    if type_bloc == 11: return LAPIS
    if type_bloc == 12: return DIAMANT
    if type_bloc == 20: return (150, 100, 55)   # Bâton
    if type_bloc == 21: return (200, 205, 215)  # Épée
    if type_bloc == 22: return (175, 180, 190)  # Pioche
    if type_bloc == 23: return (255, 200, 60)   # Torche
    if type_bloc == 24: return (160, 110, 60)   # Établi
    if 30 <= type_bloc <= 33: return (190, 190, 200)  # Armure fer
    if 34 <= type_bloc <= 37: return (95, 210, 210)   # Armure diamant
    if type_bloc == 40: return (150, 110, 60)   # Arc
    if type_bloc == 41: return (210, 210, 210)  # Flèche
    if type_bloc == 42: return (235, 235, 235)  # Ficelle
    if type_bloc == 25: return (200, 60, 70)    # Lit (pied)
    if type_bloc == 27: return (200, 60, 70)    # Lit (tête)
    if type_bloc == 26: return (150, 105, 55)   # Coffre
    if 43 <= type_bloc <= 46: return (250, 210, 60)  # Armure or
    if type_bloc == 50: return (220, 220, 228)  # Lingot de fer
    if type_bloc == 53: return (150, 150, 160)  # Hache
    if type_bloc == 54: return (170, 170, 180)  # Pelle
    if type_bloc == 55: return (90, 90, 95)     # Fourneau
    if type_bloc == 60: return (215, 100, 95)   # Viande crue
    if type_bloc == 61: return (150, 90, 55)    # Viande cuite
    return None

def nom_bloc(type_bloc):
    if type_bloc == 1: return "Herbe"
    if type_bloc == 2: return "Terre"
    if type_bloc == 3: return "Pierre"
    if type_bloc == 4: return "Bois"
    if type_bloc == 5: return "Feuilles"
    if type_bloc == 7: return "Charbon"
    if type_bloc == 8: return "Fer"
    if type_bloc == 9: return "Or"
    if type_bloc == 10: return "Redstone"
    if type_bloc == 11: return "Lapis"
    if type_bloc == 12: return "Diamant"
    if type_bloc == 20: return "Bâton"
    if type_bloc == 21: return "Épée"
    if type_bloc == 22: return "Pioche"
    if type_bloc == 23: return "Torche"
    if type_bloc == 24: return "Établi"
    if type_bloc == 30: return "Casque fer"
    if type_bloc == 31: return "Plastron fer"
    if type_bloc == 32: return "Jambières fer"
    if type_bloc == 33: return "Bottes fer"
    if type_bloc == 34: return "Casque diamant"
    if type_bloc == 35: return "Plastron diamant"
    if type_bloc == 36: return "Jambières diamant"
    if type_bloc == 37: return "Bottes diamant"
    if type_bloc == 40: return "Arc"
    if type_bloc == 41: return "Flèche"
    if type_bloc == 42: return "Ficelle"
    if type_bloc == 25: return "Lit"
    if type_bloc == 26: return "Coffre"
    if type_bloc == 43: return "Casque or"
    if type_bloc == 44: return "Plastron or"
    if type_bloc == 45: return "Jambières or"
    if type_bloc == 46: return "Bottes or"
    if type_bloc == 50: return "Lingot de fer"
    if type_bloc == 53: return "Hache"
    if type_bloc == 54: return "Pelle"
    if type_bloc == 55: return "Fourneau"
    if type_bloc == 60: return "Viande crue"
    if type_bloc == 61: return "Viande cuite"
    return ""

# ---------------------------------------------------------------------------
# Textures procédurales : chaque bloc est pré-dessiné UNE fois dans une petite
# Surface (grain + détails) puis réutilisé, pour un rendu moins plat sans images.
# ---------------------------------------------------------------------------
def _melange(c, d):
    return tuple(max(0, min(255, v + d)) for v in c)

def _grain(surf, couleur, n, taille=4, amp=22, y0=0, y1=TAILLE_BLOC):
    for _ in range(n):
        x = random.randint(0, TAILLE_BLOC - taille)
        y = random.randint(y0, max(y0, y1 - taille))
        pygame.draw.rect(surf, _melange(couleur, random.randint(-amp, amp)),
                         (x, y, taille, taille))

def generer_texture(type_bloc):
    random.seed(7000 + type_bloc)          # motif stable (pas de scintillement)
    surf = pygame.Surface((TAILLE_BLOC, TAILLE_BLOC))
    if type_bloc == 1:                     # Herbe : terre + couche d'herbe en haut
        surf.fill(TERRE)
        _grain(surf, TERRE, 30, 4, 18)
        h = TAILLE_BLOC // 3
        pygame.draw.rect(surf, HERBE, (0, 0, TAILLE_BLOC, h))
        _grain(surf, HERBE, 24, 3, 28, 0, h + 3)
        for _ in range(10):                # brins qui dépassent
            x = random.randint(0, TAILLE_BLOC - 2)
            pygame.draw.rect(surf, _melange(HERBE, 30), (x, h, 2, 4))
    elif type_bloc == 2:                   # Terre
        surf.fill(TERRE)
        _grain(surf, TERRE, 48, 4, 24)
    elif type_bloc == 3:                   # Pierre + fissures
        surf.fill(PIERRE)
        _grain(surf, PIERRE, 52, 4, 22)
        for _ in range(2):
            x = random.randint(6, TAILLE_BLOC - 6)
            pygame.draw.line(surf, _melange(PIERRE, -40),
                             (x, random.randint(0, 8)), (x + random.randint(-6, 6), TAILLE_BLOC - 6), 1)
    elif type_bloc == 4:                   # Bois : veines verticales
        surf.fill(BOIS)
        _grain(surf, BOIS, 22, 3, 16)
        for x in range(4, TAILLE_BLOC, 9):
            pygame.draw.line(surf, _melange(BOIS, -28), (x, 0), (x, TAILLE_BLOC), 2)
            pygame.draw.line(surf, _melange(BOIS, 18), (x + 3, 0), (x + 3, TAILLE_BLOC), 1)
    elif type_bloc == 5:                   # Feuilles
        surf.fill(FEUILLES)
        _grain(surf, FEUILLES, 60, 3, 34)
    elif 7 <= type_bloc <= 12:             # Minerai : pierre grainée + pépites
        surf.fill(PIERRE)
        _grain(surf, PIERRE, 44, 4, 22)
        coul = couleur_bloc(type_bloc)
        for (dpx, dpy) in [(7, 8), (22, 9), (9, 23), (24, 25)]:
            pygame.draw.rect(surf, coul, (dpx, dpy, 8, 8))
            pygame.draw.rect(surf, _melange(coul, 45), (dpx, dpy, 3, 3))     # reflet
            pygame.draw.rect(surf, _melange(coul, -45), (dpx + 5, dpy + 5, 3, 3))  # ombre
    else:
        surf.fill(couleur_bloc(type_bloc) or (150, 150, 150))
    pygame.draw.rect(surf, (0, 0, 0), (0, 0, TAILLE_BLOC, TAILLE_BLOC), 1)
    random.seed()
    return surf

# Chargement des textures depuis un dossier "textures/" à côté du jeu.
# Priorité : 1) fichier individuel (herbe.png…)  2) tuile de l'image combinée
# (textures.png découpée)  3) texture procédurale dessinée en code (repli).
NOMS_FICHIERS = {
    1: "herbe.png", 2: "terre.png", 3: "pierre.png", 4: "bois.png", 5: "feuilles.png",
    7: "charbon.png", 8: "fer.png", 9: "or.png", 10: "redstone.png",
    11: "lapis.png", 12: "diamant.png",
}
DOSSIER_TEXTURES = os.path.join(DOSSIER_BASE, "textures")

# Ce que représente CHAQUE tuile de l'image combinée, de HAUT en BAS (0 = ignorée).
# Blocs : 1 herbe, 2 terre, 3 pierre, 4 bois, 5 feuilles, 6 eau, 7 charbon,
# 8 fer, 12 diamant. (Modifie cette liste si une texture tombe sur le mauvais bloc.)
ORDRE_ATLAS = [
    1,    # tuile 1  : terre avec herbe
    0,    # tuile 2
    2,    # tuile 3  : terre
    3,    # tuile 4  : pierre
    4,    # tuile 5  : bois
    0,    # tuile 6
    5,    # tuile 7  : feuilles
    6,    # tuile 8  : eau (image 1)
    0,    # tuile 9  : eau (image 2, animation)
    0,    # tuile 10 : eau (image 3, animation)
    0,    # tuile 11
    0,    # tuile 12
    0,    # tuile 13
    0,    # tuile 14
    7,    # tuile 15 : charbon
    8,    # tuile 16 : fer
    12,   # tuile 17 : diamant
]

def _charger_atlas():
    # Cherche une image combinée (textures.png/…) et la découpe en tuiles carrées.
    tuiles = []
    for nom in ("textures", "atlas", "blocs"):
        for ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ""):
            chemin = os.path.join(DOSSIER_TEXTURES, nom + ext)
            if os.path.isfile(chemin):
                try:
                    img = pygame.image.load(chemin).convert_alpha()
                    larg = img.get_width()
                    for i in range(img.get_height() // larg):
                        tuile = img.subsurface((0, i * larg, larg, larg)).copy()
                        tuiles.append(pygame.transform.scale(tuile, (TAILLE_BLOC, TAILLE_BLOC)))
                    return tuiles
                except Exception:
                    pass
    return tuiles

ATLAS_TUILES = _charger_atlas()

def charger_texture(type_bloc):
    # 1) fichier individuel
    chemin = os.path.join(DOSSIER_TEXTURES, NOMS_FICHIERS.get(type_bloc, ""))
    try:
        return pygame.transform.scale(pygame.image.load(chemin).convert_alpha(),
                                      (TAILLE_BLOC, TAILLE_BLOC))
    except Exception:
        pass
    # 2) tuile de l'image combinée
    if type_bloc in ORDRE_ATLAS:
        idx = ORDRE_ATLAS.index(type_bloc)
        if idx < len(ATLAS_TUILES):
            return ATLAS_TUILES[idx]
    # 3) repli procédural
    return generer_texture(type_bloc)

TEXTURES = {t: charger_texture(t) for t in NOMS_FICHIERS}

# Eau animée : tuiles 8, 9, 10 de l'atlas (indices 7, 8, 9).
EAU_FRAMES = [ATLAS_TUILES[i] for i in (7, 8, 9) if i < len(ATLAS_TUILES)]

police_petite = pygame.font.SysFont(None, 22)

def dessiner_texte(surface, texte, police_utilisee, x, y,
                   couleur_texte=(255, 255, 255), couleur_fond=(0, 0, 0, 175),
                   marge=5, centre=False):
    # Dessine un texte sur un rectangle semi-transparent contrasté pour
    # garantir sa lisibilité quel que soit le décor derrière.
    rendu = police_utilisee.render(texte, True, couleur_texte)
    if centre:
        x = x - rendu.get_width() // 2
    fond = pygame.Surface((rendu.get_width() + marge * 2,
                           rendu.get_height() + marge * 2), pygame.SRCALPHA)
    fond.fill(couleur_fond)
    surface.blit(fond, (x - marge, y - marge))
    surface.blit(rendu, (x, y))
    return rendu

def texte_ombre(surface, texte, police_utilisee, x, y, couleur=(255, 255, 255)):
    # Texte avec ombre portée, façon Minecraft (lisible sur n'importe quel fond).
    ombre = police_utilisee.render(texte, True, (30, 30, 30))
    surface.blit(ombre, (x + 1, y + 1))
    rendu = police_utilisee.render(texte, True, couleur)
    surface.blit(rendu, (x, y))
    return rendu

def dessiner_slot(surface, x, y, taille, selectionne=False):
    # Case d'inventaire style Minecraft : fond gris clair translucide + relief biseauté.
    fond = pygame.Surface((taille, taille), pygame.SRCALPHA)
    fond.fill((175, 175, 175, 130))
    surface.blit(fond, (x, y))
    pygame.draw.line(surface, (235, 235, 235), (x, y), (x + taille - 1, y))
    pygame.draw.line(surface, (235, 235, 235), (x, y), (x, y + taille - 1))
    pygame.draw.line(surface, (90, 90, 90), (x, y + taille - 1), (x + taille - 1, y + taille - 1))
    pygame.draw.line(surface, (90, 90, 90), (x + taille - 1, y), (x + taille - 1, y + taille - 1))
    if selectionne:
        pygame.draw.rect(surface, (255, 255, 255), (x - 2, y - 2, taille + 4, taille + 4), 3)

def dessiner_item(surface, x, y, taille, type_bloc):
    # Dessine l'icône d'un objet centré dans une case (bloc, minerai ou objet crafté).
    marge = 9
    ix = x + marge
    iy = y + marge
    s = taille - 2 * marge
    if type_bloc in TEXTURES:
        surface.blit(pygame.transform.scale(TEXTURES[type_bloc], (s, s)), (ix, iy))
    else:
        coul = couleur_bloc(type_bloc) or (150, 150, 150)
        pygame.draw.rect(surface, coul, (ix, iy, s, s))
        pygame.draw.rect(surface, (0, 0, 0), (ix, iy, s, s), 1)

def dessiner_steve(surface, x, y, w, h, equip=None, phase=0.0, avec_epee=False, regard=1):
    # Dessine le personnage (tête, tee-shirt, bras, jambes) proportionnellement à
    # w x h, avec les pièces d'armure par-dessus. `phase` anime la marche : les
    # jambes et les bras se balancent (sens opposés) quand phase varie.
    PEAU = (150, 110, 80)
    SHIRT = (60, 140, 150)
    JEAN = (60, 70, 160)
    tete_h = max(6, int(h * 0.30))
    corps_h = max(6, int(h * 0.40))
    jambe_h = h - tete_h - corps_h
    tete_w = int(w * 0.5)
    corps_w = int(w * 0.5)
    bras_w = max(4, (w - corps_w) // 2)
    tx = x + (w - tete_w) // 2
    cx = x + (w - corps_w) // 2
    cy = y + tete_h
    ly = cy + corps_h
    jambe_w = max(4, corps_w // 2 - 1)
    bras_h = int(corps_h * 0.9)
    # Balancement de marche : les membres PIVOTENT autour de la hanche / l'épaule.
    ang = math.sin(phase) * 0.45     # angle max ≈ 26°

    def membre(px, py, longueur, angle, largeur, couleur, bout_couleur, bout_r):
        # Membre articulé : segment épais qui pivote autour de (px, py),
        # avec une articulation ronde en haut et un bout arrondi (pied/main).
        ex = px + math.sin(angle) * longueur
        ey = py + math.cos(angle) * longueur
        pygame.draw.circle(surface, couleur, (int(px), int(py)), largeur // 2)
        pygame.draw.line(surface, couleur, (int(px), int(py)), (int(ex), int(ey)), largeur)
        pygame.draw.circle(surface, bout_couleur, (int(ex), int(ey)), bout_r)

    main_r = max(3, bras_w // 2)
    shg = cx + bras_w // 2                 # épaule gauche (à l'intérieur du torse)
    shd = cx + corps_w - bras_w // 2       # épaule droite
    sh_y = cy + 2
    hg_x = cx + jambe_w // 2 + 1           # hanche gauche
    hd_x = cx + corps_w - jambe_w // 2 - 1  # hanche droite
    ang_g, ang_d = -ang, ang               # balancement des bras (opposés)
    ang_jg, ang_jd = ang, -ang             # balancement des jambes (opposés)

    def assombrir(c, f=0.55):
        return (int(c[0] * f), int(c[1] * f), int(c[2] * f))

    def dessiner_epee(hx, hy, a, clair):
        lame = h * 0.38
        bx2 = hx + math.sin(a) * lame
        by2 = hy + math.cos(a) * lame
        perp = a + math.pi / 2
        g = max(4, w // 6)
        lame_c = (215, 215, 225) if clair else (150, 150, 160)
        pygame.draw.line(surface, (110, 70, 30),
                         (int(hx + math.sin(perp) * g), int(hy + math.cos(perp) * g)),
                         (int(hx - math.sin(perp) * g), int(hy - math.cos(perp) * g)), 3)
        pygame.draw.line(surface, lame_c, (int(hx), int(hy)), (int(bx2), int(by2)), max(3, w // 9))
        pygame.draw.circle(surface, lame_c, (int(bx2), int(by2)), max(2, w // 16))

    def bras(sx, a, devant):
        coul = SHIRT if devant else assombrir(SHIRT)
        mcoul = PEAU if devant else assombrir(PEAU)
        membre(sx, sh_y, bras_h, a, bras_w, coul, mcoul, main_r)
        if avec_epee and sx == shd:        # l'épée est tenue par le bras droit
            dessiner_epee(sx + math.sin(a) * bras_h, sh_y + math.cos(a) * bras_h, a, devant)

    def jambe(hx, a, devant):
        coul = JEAN if devant else assombrir(JEAN)
        membre(hx, ly, jambe_h, a, jambe_w, coul, coul, jambe_w // 2)
        # L'armure des jambes SUIT la jambe (elle pivote avec elle).
        if equip:
            def pt(f):
                return (int(hx + math.sin(a) * jambe_h * f), int(ly + math.cos(a) * jambe_h * f))
            if equip.get("jambieres"):
                cj = couleur_bloc(equip["jambieres"])
                if not devant:
                    cj = assombrir(cj)
                pygame.draw.line(surface, cj, pt(0.0), pt(0.55), jambe_w + 2)
            if equip.get("bottes"):
                cb = couleur_bloc(equip["bottes"])
                if not devant:
                    cb = assombrir(cb)
                pygame.draw.line(surface, cb, pt(0.72), pt(1.0), jambe_w + 3)
                pygame.draw.circle(surface, cb, pt(1.0), (jambe_w + 3) // 2)

    face = 1 if regard >= 0 else -1
    # tête
    pygame.draw.rect(surface, PEAU, (tx, y, tete_w, tete_h))
    if face == 1:
        # On regarde à droite : le bras/la jambe DROITE passe DERRIÈRE le corps.
        jambe(hd_x, ang_jd, False)
        bras(shd, ang_d, False)
        pygame.draw.rect(surface, SHIRT, (cx, cy, corps_w, corps_h))
        jambe(hg_x, ang_jg, True)
        bras(shg, ang_g, True)
    else:
        # On regarde à gauche : côté GAUCHE derrière.
        jambe(hg_x, ang_jg, False)
        bras(shg, ang_g, False)
        pygame.draw.rect(surface, SHIRT, (cx, cy, corps_w, corps_h))
        jambe(hd_x, ang_jd, True)
        bras(shd, ang_d, True)

    if equip:
        # Casque (tête) et plastron (torse) restent fixes ; les jambières et
        # bottes sont désormais dessinées dans jambe() pour suivre les jambes.
        if equip.get("casque"):
            pygame.draw.rect(surface, couleur_bloc(equip["casque"]),
                             (tx - 1, y - 1, tete_w + 2, max(3, tete_h // 2)))
        if equip.get("plastron"):
            cp = couleur_bloc(equip["plastron"])
            pygame.draw.rect(surface, cp, (cx - 1, cy - 1, corps_w + 2, corps_h + 2))
            pygame.draw.rect(surface, assombrir(cp, 0.7),
                             (cx - 1, cy - 1, corps_w + 2, corps_h + 2), 2)

# Recettes façonnées : "motif" = boîte englobante minimale des ingrédients dans
# la grille (0 = case vide). La recette est reconnue où qu'elle soit placée dans
# le carré 3x3. "resultat" = (type, quantité).
RECETTES = [
    {"nom": "Bâtons", "motif": ((4,), (4,)), "resultat": (20, 4)},
    {"nom": "Établi", "motif": ((4, 4), (4, 4)), "resultat": (24, 1)},
    {"nom": "Torches", "motif": ((7,), (20,)), "resultat": (23, 4)},
    {"nom": "Lit", "motif": ((5, 5, 5), (4, 4, 4)), "resultat": (25, 1)},
    {"nom": "Coffre", "motif": ((4, 4, 4), (4, 0, 4), (4, 4, 4)), "resultat": (26, 1)},
    {"nom": "Épée (pierre)", "motif": ((3,), (3,), (20,)), "resultat": (21, 1)},
    {"nom": "Épée (bois)", "motif": ((4,), (4,), (20,)), "resultat": (21, 1)},
    {"nom": "Pioche", "motif": ((3, 3, 3), (0, 20, 0), (0, 20, 0)), "resultat": (22, 1)},
    {"nom": "Hache", "motif": ((3, 3), (3, 20), (0, 20)), "resultat": (53, 1)},
    {"nom": "Pelle", "motif": ((3,), (20,), (20,)), "resultat": (54, 1)},
    {"nom": "Fourneau", "motif": ((3, 3, 3), (3, 0, 3), (3, 3, 3)), "resultat": (55, 1)},
    # --- Armure de fer : nécessite des LINGOTS (50) fondus au fourneau ---
    {"nom": "Casque fer", "motif": ((50, 50, 50), (50, 0, 50)), "resultat": (30, 1)},
    {"nom": "Plastron fer", "motif": ((50, 0, 50), (50, 50, 50), (50, 50, 50)), "resultat": (31, 1)},
    {"nom": "Jambières fer", "motif": ((50, 50, 50), (50, 0, 50), (50, 0, 50)), "resultat": (32, 1)},
    {"nom": "Bottes fer", "motif": ((50, 0, 50), (50, 0, 50)), "resultat": (33, 1)},
    # --- Arc et flèches (ficelle = 42, lâchée par les araignées) ---
    {"nom": "Arc", "motif": ((0, 20, 42), (20, 0, 42), (0, 20, 42)), "resultat": (40, 1)},
    {"nom": "Flèches", "motif": ((3,), (20,), (42,)), "resultat": (41, 4)},
    {"nom": "Casque diamant", "motif": ((12, 12, 12), (12, 0, 12)), "resultat": (34, 1)},
    {"nom": "Plastron diamant", "motif": ((12, 0, 12), (12, 12, 12), (12, 12, 12)), "resultat": (35, 1)},
    {"nom": "Jambières diamant", "motif": ((12, 12, 12), (12, 0, 12), (12, 0, 12)), "resultat": (36, 1)},
    {"nom": "Bottes diamant", "motif": ((12, 0, 12), (12, 0, 12)), "resultat": (37, 1)},
    # --- Armure en or (matériau or = 9) ---
    {"nom": "Casque or", "motif": ((9, 9, 9), (9, 0, 9)), "resultat": (43, 1)},
    {"nom": "Plastron or", "motif": ((9, 0, 9), (9, 9, 9), (9, 9, 9)), "resultat": (44, 1)},
    {"nom": "Jambières or", "motif": ((9, 9, 9), (9, 0, 9), (9, 0, 9)), "resultat": (45, 1)},
    {"nom": "Bottes or", "motif": ((9, 0, 9), (9, 0, 9)), "resultat": (46, 1)},
]

# Pièce d'armure -> (emplacement, points de protection = coups absorbés).
ARMURES = {
    30: ("casque", 3), 31: ("plastron", 4), 32: ("jambieres", 3), 33: ("bottes", 2),
    34: ("casque", 5), 35: ("plastron", 7), 36: ("jambieres", 5), 37: ("bottes", 3),
    43: ("casque", 2), 44: ("plastron", 3), 45: ("jambieres", 2), 46: ("bottes", 2),
}

def trouver_recette(grille):
    cases = [(r, c) for r in range(3) for c in range(3) if grille[r][c] != 0]
    if not cases:
        return None
    rmin = min(r for r, c in cases)
    rmax = max(r for r, c in cases)
    cmin = min(c for r, c in cases)
    cmax = max(c for r, c in cases)
    motif = tuple(tuple(grille[r][c] for c in range(cmin, cmax + 1))
                  for r in range(rmin, rmax + 1))
    for recette in RECETTES:
        if recette["motif"] == motif:
            return recette
    return None

chunks = {}
# Blocs posés au-dessus du monde (y < 0), pour construire des bases aériennes
# à l'infini. Stockés à part car les chunks ne gèrent que y >= 0.
blocs_hauts = {}
hauteur_courante = 18
graine = random.randint(0, 10000)

def get_chunk(cx):
    if cx not in chunks:
        global hauteur_courante
        chunk, hauteur_courante, hauteurs = generer_chunk(cx, hauteur_courante)
        chunks[cx] = {"blocs": chunk, "hauteurs": hauteurs,
                      "profondeur": PROFONDEUR_INITIALE}
    return chunks[cx]

def etendre_chunk(cx, cible):
    # Génère de la profondeur à la demande, par tranches, pour que le monde soit
    # infini vers le bas. Chaque tranche est remplie de pierre/minerais (selon la
    # profondeur) puis creusée de quelques grottes.
    chunk = chunks[cx]
    blocs = chunk["blocs"]
    hauteurs = chunk["hauteurs"]
    while chunk["profondeur"] <= cible:
        debut = chunk["profondeur"]
        fin = debut + TAILLE_CHUNK
        random.seed(graine + cx * 1000 + debut * 7)

        for y in range(debut, fin):
            rangee = []
            for col in range(TAILLE_CHUNK):
                rangee.append(tirer_bloc_souterrain(y - hauteurs[col]))
            blocs.append(rangee)

        for _ in range(random.randint(0, 2)):
            gx = random.randint(0, TAILLE_CHUNK - 1)
            gy = random.randint(debut + 1, fin - 2)
            longueur = random.randint(15, 40)
            rayon = random.randint(1, 2)
            angle = random.uniform(0, 2 * math.pi)
            for _ in range(longueur):
                for dy in range(-rayon, rayon + 1):
                    for dx in range(-rayon, rayon + 1):
                        if dx * dx + dy * dy <= rayon * rayon:
                            cxx = int(gx + dx)
                            cyy = int(gy + dy)
                            if 0 <= cxx < TAILLE_CHUNK and debut <= cyy < fin:
                                if blocs[cyy][cxx] not in (0,):
                                    blocs[cyy][cxx] = 0
                angle += random.uniform(-0.4, 0.4)
                gx += math.cos(angle)
                gy += math.sin(angle) * 0.6
                gx = max(0, min(TAILLE_CHUNK - 1, gx))
                gy = max(debut + 1, min(fin - 2, gy))

        chunk["profondeur"] = fin
    random.seed()

for i in range(-3, 4):
    get_chunk(i)

def get_bloc(x_monde, y_monde):
    if y_monde < 0:
        return blocs_hauts.get((x_monde, y_monde), 0)   # ciel : blocs posés en hauteur
    cx = x_monde // TAILLE_CHUNK
    col = x_monde % TAILLE_CHUNK
    if col < 0:
        cx -= 1
        col += TAILLE_CHUNK
    chunk = get_chunk(cx)
    if y_monde >= chunk["profondeur"]:
        etendre_chunk(cx, y_monde)
    return chunk["blocs"][y_monde][col]

def set_bloc(x_monde, y_monde, valeur):
    if y_monde < 0:
        if valeur == 0:
            blocs_hauts.pop((x_monde, y_monde), None)
        else:
            blocs_hauts[(x_monde, y_monde)] = valeur
        return
    cx = x_monde // TAILLE_CHUNK
    col = x_monde % TAILLE_CHUNK
    if col < 0:
        cx -= 1
        col += TAILLE_CHUNK
    if cx in chunks:
        chunk = chunks[cx]
        if y_monde >= chunk["profondeur"]:
            etendre_chunk(cx, y_monde)
        chunk["blocs"][y_monde][col] = valeur

def _traversable(bloc):
    # Air (0) et eau (6) laissent passer les mobs ; tout le reste est solide.
    return bloc == 0 or bloc == 6

def mob_gravite(m, taille):
    """Applique la gravité, gère la collision sol ET plafond.
    Renvoie True si le mob repose sur le sol."""
    m["vitesse_y"] += gravite
    m["y"] += m["vitesse_y"]

    col_g = int(m["x"] // TAILLE_BLOC)
    col_d = int((m["x"] + taille - 1) // TAILLE_BLOC)

    if m["vitesse_y"] >= 0:
        lig_bas = int((m["y"] + taille) // TAILLE_BLOC)
        if not _traversable(get_bloc(col_g, lig_bas)) or not _traversable(get_bloc(col_d, lig_bas)):
            m["y"] = lig_bas * TAILLE_BLOC - taille
            m["vitesse_y"] = 0
    else:
        lig_haut = int(m["y"] // TAILLE_BLOC)
        if not _traversable(get_bloc(col_g, lig_haut)) or not _traversable(get_bloc(col_d, lig_haut)):
            m["y"] = (lig_haut + 1) * TAILLE_BLOC
            m["vitesse_y"] = 0

    lig_sous = int((m["y"] + taille) // TAILLE_BLOC)
    col_g = int(m["x"] // TAILLE_BLOC)
    col_d = int((m["x"] + taille - 1) // TAILLE_BLOC)
    return not _traversable(get_bloc(col_g, lig_sous)) or not _traversable(get_bloc(col_d, lig_sous))

def mob_deplacer_x(m, dx, taille):
    """Déplace le mob horizontalement SANS jamais traverser un bloc (collision
    vérifiée avant le mouvement, puis calage contre le mur). dx peut valoir
    plusieurs pixels. Renvoie True si un mur a bloqué le déplacement."""
    if dx == 0:
        return False
    lig_h = int(m["y"] // TAILLE_BLOC)
    lig_b = int((m["y"] + taille - 1) // TAILLE_BLOC)
    nx = m["x"] + dx
    if dx > 0:
        col_avant = int((nx + taille - 1) // TAILLE_BLOC)
        if not _traversable(get_bloc(col_avant, lig_h)) or not _traversable(get_bloc(col_avant, lig_b)):
            m["x"] = col_avant * TAILLE_BLOC - taille   # calé contre le mur
            return True
    else:
        col_avant = int(nx // TAILLE_BLOC)
        if not _traversable(get_bloc(col_avant, lig_h)) or not _traversable(get_bloc(col_avant, lig_b)):
            m["x"] = (col_avant + 1) * TAILLE_BLOC       # calé contre le mur
            return True
    m["x"] = nx
    return False

def mob_marche_franchissable(m, taille, direction):
    """Vrai si l'obstacle devant est une marche d'UN seul bloc, dégagée au-dessus
    (et avec de la place au-dessus de la tête) : donc réellement sautable."""
    lig_h = int(m["y"] // TAILLE_BLOC)
    lig_b = int((m["y"] + taille - 1) // TAILLE_BLOC)
    col_g = int(m["x"] // TAILLE_BLOC)
    col_d = int((m["x"] + taille - 1) // TAILLE_BLOC)
    col_avant = (col_d + 1) if direction > 0 else (col_g - 1)
    b_marche = get_bloc(col_avant, lig_b)          # bloc devant, au niveau des pieds
    b_dessus = get_bloc(col_avant, lig_b - 1)      # une case au-dessus de la marche
    b_tete_g = get_bloc(col_g, lig_h - 1)          # dégagement au-dessus du mob
    b_tete_d = get_bloc(col_d, lig_h - 1)
    return (not _traversable(b_marche)) and _traversable(b_dessus) \
        and _traversable(b_tete_g) and _traversable(b_tete_d)

def bloc_accessible(x_monde, y_monde):
    # Un bloc n'est accessible (donc minable) que s'il possède au moins une
    # face exposée : un voisin (haut, bas, gauche, droite) vide (air) ou eau.
    # S'il est complètement enfermé par d'autres blocs solides, il ne l'est pas.
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        voisin = get_bloc(x_monde + dx, y_monde + dy)
        if voisin == 0 or voisin == 6:
            return True
    return False

def update_eau(joueur_x, joueur_y):
    centre_x = int(joueur_x // TAILLE_BLOC)
    centre_y = int(joueur_y // TAILLE_BLOC)
    portee = 20

    blocs_eau = []
    for y in range(centre_y + portee, max(0, centre_y - portee), -1):
        for x in range(centre_x - portee, centre_x + portee):
            if get_bloc(x, y) == 6:
                blocs_eau.append((x, y))

    a_ajouter = []
    a_supprimer = []

    for (x, y) in blocs_eau:
        if (x, y) in a_supprimer:
            continue
        dessous = get_bloc(x, y + 1)
        if dessous == 0:
            if (x, y + 1) not in a_ajouter:
                a_supprimer.append((x, y))
                a_ajouter.append((x, y + 1))
        elif dessous != 0 and dessous != 6:
            gauche = get_bloc(x - 1, y)
            droite = get_bloc(x + 1, y)
            if gauche == 0 and (x - 1, y) not in a_ajouter:
                a_ajouter.append((x - 1, y))
            if droite == 0 and (x + 1, y) not in a_ajouter:
                a_ajouter.append((x + 1, y))

    for (x, y) in a_supprimer:
        set_bloc(x, y, 0)
    for (x, y) in a_ajouter:
        set_bloc(x, y, 6)

inventaire = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0,
              20: 0, 21: 0, 22: 0, 23: 0, 24: 0, 41: 0, 42: 0,
              30: 0, 31: 0, 32: 0, 33: 0, 34: 0, 35: 0, 36: 0, 37: 0,
              43: 0, 44: 0, 45: 0, 46: 0, 25: 0, 26: 0,
              50: 0, 53: 0, 54: 0, 55: 0, 60: 0, 61: 0}
regen_timer = 0     # régénération de vie en survie

# Fourneau : un état partagé (entrée / combustible / résultat) + progression.
four_ouvert = False
four_in = [0, 0]     # [type, quantité] à fondre
four_fuel = [0, 0]   # [type, quantité] combustible (charbon = 7)
four_out = [0, 0]    # [type, quantité] résultat
four_progres = 0
DUREE_FUSION = 120   # temps pour fondre 1 objet (frames)
FUSION = {8: 50, 60: 61}   # minerai de fer -> lingot ; viande crue -> cuite
# Barre rapide de 8 cases personnalisables : chaque case pointe vers un type
# d'objet (0 = vide). Organisable dans le menu E.
hotbar = [0, 0, 0, 0, 0, 0, 0, 0]   # se remplit toute seule quand on récolte
slot_actif = 0
bloc_selectionne = hotbar[slot_actif]
# Types réellement posables au clic droit (lit/coffre/four ont leurs touches).
POSABLES = {1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12}
epee = False
arc = False

# Coffre de rangement (stockage partagé) + son menu
coffre = {}
coffre_ouvert = False

# État du craft (grille 3x3 partagée par le menu unique)
grille_craft = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
item_en_main = 0   # ingrédient choisi pour être posé dans la grille

# Armure : pièces équipées et pool de protection (nombre de coups absorbés).
equipement = {"casque": 0, "plastron": 0, "jambieres": 0, "bottes": 0}
armure = 0
armure_max = 0

# Géométrie de la hotbar (8 cases) : partagée entre affichage et clics souris.
NB_HOTBAR = 8
SLOT = 56
ICON = SLOT - 14
HOT_X = LARGEUR // 2 - (NB_HOTBAR * SLOT) // 2
HOT_Y = HAUTEUR - SLOT - 12

# Géométrie du menu de craft (3x3), partagée entre affichage et clics souris.
CRAFT_SLOT = 52
CRAFT_MENU_W = 560
CRAFT_MENU_H = 470
CRAFT_MX = LARGEUR // 2 - CRAFT_MENU_W // 2
CRAFT_MY = HAUTEUR // 2 - CRAFT_MENU_H // 2
CRAFT_GX = CRAFT_MX + 40
CRAFT_GY = CRAFT_MY + 80
CRAFT_OUT_X = CRAFT_GX + 3 * CRAFT_SLOT + 80
CRAFT_OUT_Y = CRAFT_GY + CRAFT_SLOT
CRAFT_INV = [1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 20, 42]
CRAFT_INV_COLS = 8
CRAFT_INV_SLOT = 48
CRAFT_INV_X = CRAFT_MX + 40
CRAFT_INV_Y = CRAFT_GY + 3 * CRAFT_SLOT + 45

# --- Menu unique (touche E ou I) : armure + aperçu + fabrication 3x3 + sac ---
inventaire_ouvert = False

ARMURE_SLOTS = ["casque", "plastron", "jambieres", "bottes"]
INV_MENU_W = 720
INV_MENU_H = 660
INV_MX = LARGEUR // 2 - INV_MENU_W // 2
INV_MY = HAUTEUR // 2 - INV_MENU_H // 2
ARM_SLOT = 56
ARM_X = INV_MX + 25
ARM_Y = INV_MY + 60
PREVIEW_X = INV_MX + 110
PREVIEW_Y = INV_MY + 55
# Grille de fabrication 3x3 (haut-droite)
IGRID_SLOT = 52
IGRID_X = INV_MX + 300
IGRID_Y = INV_MY + 70
IGRID_OUT_X = IGRID_X + 3 * IGRID_SLOT + 60
IGRID_OUT_Y = IGRID_Y + IGRID_SLOT
# Barre rapide dans le menu E (pour l'organiser) + grille du sac (bas)
SAC_COLS = 10
SAC_ROWS = 3
SAC_SLOT = 60
SAC_X = INV_MX + 25
EHOT_X = INV_MX + 25
EHOT_Y = INV_MY + 300
SAC_Y = INV_MY + 390
# Cases fixes du sac (survie) : chaque case contient un type d'objet (0 = vide),
# arrangeables librement. Les quantités viennent d'inventaire.
sac_slots = [0] * (SAC_ROWS * SAC_COLS)
# Tous les objets pouvant se trouver dans le sac.
INV_TOUS = [1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 20, 21, 22, 23, 24, 25, 26,
            50, 53, 54, 55, 60, 61,
            41, 42, 30, 31, 32, 33, 34, 35, 36, 37, 43, 44, 45, 46]

# --- Menu du coffre (touche C) : sac en haut, coffre en bas ---
COF_MENU_W = 680
COF_MENU_H = 480
COF_MX = LARGEUR // 2 - COF_MENU_W // 2
COF_MY = HAUTEUR // 2 - COF_MENU_H // 2
COF_COLS = 10
COF_SLOT = 60
CSAC_X = COF_MX + 25
CSAC_Y = COF_MY + 70
CCOF_X = COF_MX + 25
CCOF_Y = COF_MY + 270

# --- Menu du fourneau : entrée (haut), combustible (bas), résultat (droite) ---
FOUR_MENU_W = 560
FOUR_MENU_H = 470
FOUR_MX = LARGEUR // 2 - FOUR_MENU_W // 2
FOUR_MY = HAUTEUR // 2 - FOUR_MENU_H // 2
FOUR_SLOT = 62
FOUR_IN_X = FOUR_MX + 90
FOUR_IN_Y = FOUR_MY + 60
FOUR_FUEL_X = FOUR_MX + 90
FOUR_FUEL_Y = FOUR_MY + 190
FOUR_OUT_X = FOUR_MX + 340
FOUR_OUT_Y = FOUR_MY + 125
FSAC_COLS = 8
FSAC_SLOT = 56
FSAC_X = FOUR_MX + 30
FSAC_Y = FOUR_MY + 300

def recompute_armure():
    global armure_max, armure
    armure_max = sum(ARMURES[t][1] for t in equipement.values() if t != 0)
    armure = armure_max

joueur_x = 0
joueur_y = 0
# Le joueur fait 1 bloc de large et 2 blocs de haut (boîte de collision).
taille_joueur = 34            # largeur
hauteur_joueur = 2 * TAILLE_BLOC - 4   # hauteur (≈ 2 blocs)
phase_marche = 0.0            # phase d'animation de marche
regard = 1                    # 1 = droite, -1 = gauche
vitesse_y = 0
gravite = 0.5
peut_sauter = False
dans_eau = False
camera_x = 0
camera_y = 0
vies = 5
invincible = 0
faim = 100
faim_timer = 0
eau_timer = 0

message_info = ""
message_timer = 0

heure = 0
DUREE_CYCLE = 18000
spawn_timer = 0
est_nuit = False

taille_zombi = 35
zombis = []

taille_squelette = 35
squelettes = []
fleches = []   # projectiles : {"x","y","vx","vy","joueur"(bool)}

taille_araignee = 30
araignees = []

# Torches posées dans le monde : ensemble de cases (col, ligne). Elles ne
# bloquent pas les déplacements et empêchent les monstres d'apparaître à ≤ 5 blocs.
torches_posees = set()

# Masque de lumière (dégradé radial) qu'une torche soustrait au voile sombre
# pour éclairer réellement autour d'elle.
LIGHT_R = TAILLE_BLOC * 4
masque_lumiere = pygame.Surface((LIGHT_R * 2, LIGHT_R * 2), pygame.SRCALPHA)
for _r in range(LIGHT_R, 0, -1):
    _a = int(235 * (1 - _r / LIGHT_R) ** 1.4)
    pygame.draw.circle(masque_lumiere, (0, 0, 0, _a), (LIGHT_R, LIGHT_R), _r)

def cellule_curseur_valide():
    # Renvoie (col, ligne, ok) pour la case sous le curseur : ok = à portée,
    # vide, et sans torche déjà posée. Sert à poser lit / coffre / torche.
    mxp, myp = pygame.mouse.get_pos()
    cxx = (mxp + camera_x) // TAILLE_BLOC
    cyy = (myp + camera_y) // TAILLE_BLOC
    pcx = (joueur_x + taille_joueur / 2) / TAILLE_BLOC
    pcy = (joueur_y + hauteur_joueur / 2) / TAILLE_BLOC
    ok = (math.hypot(cxx + 0.5 - pcx, cyy + 0.5 - pcy) <= PORTEE
          and get_bloc(cxx, cyy) in (0, 6) and (cxx, cyy) not in torches_posees)
    return cxx, cyy, ok

taille_cochon = 35
cochons = []
for i in range(4):
    cx_c = random.randint(-5, 5) * TAILLE_CHUNK * TAILLE_BLOC
    cochons.append({"x": cx_c, "y": 0, "vitesse_y": 0, "direction": 1})

# ---------------------------------------------------------------------------
# Sauvegarde / chargement de la partie (fichier à côté du jeu / de l'exe)
# ---------------------------------------------------------------------------
DOSSIER_JEU = DOSSIER_BASE
SAVE_PATH = os.path.join(DOSSIER_JEU, "sauvegarde.dat")

# Variables globales à sauvegarder (mêmes noms que dans le jeu).
CLES_SAUVEGARDE = [
    "graine", "hauteur_courante", "chunks", "blocs_hauts", "torches_posees",
    "inventaire", "hotbar", "sac_slots", "equipement", "coffre",
    "four_in", "four_fuel", "four_out", "four_progres",
    "epee", "arc", "armure", "armure_max",
    "joueur_x", "joueur_y", "vitesse_y", "vies", "faim", "heure", "est_nuit",
    "mode", "slot_actif", "regard",
]

def sauvegarder_partie():
    try:
        data = {k: globals()[k] for k in CLES_SAUVEGARDE}
        with open(SAVE_PATH, "wb") as f:
            pickle.dump(data, f)
        return True
    except Exception:
        return False

def charger_partie():
    try:
        with open(SAVE_PATH, "rb") as f:
            data = pickle.load(f)
        globals().update(data)
        # On complète l'inventaire avec les éventuelles nouvelles clés d'objets.
        for _k in INV_TOUS:
            inventaire.setdefault(_k, 0)
        return True
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Menu de démarrage : Continuer / Créatif / Survie
# ---------------------------------------------------------------------------
police_menu = pygame.font.SysFont(None, 90)
mode = None
sauvegarde_existe = os.path.isfile(SAVE_PATH)
BTN_W, BTN_H = 320, 90
btn_cont = pygame.Rect(LARGEUR // 2 - BTN_W // 2, HAUTEUR // 2 - 130, BTN_W, BTN_H)
btn_crea = pygame.Rect(LARGEUR // 2 - BTN_W - 30, HAUTEUR // 2 + 10, BTN_W, BTN_H)
btn_surv = pygame.Rect(LARGEUR // 2 + 30, HAUTEUR // 2 + 10, BTN_W, BTN_H)

en_menu = True
while en_menu:
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            pygame.quit()
            raise SystemExit
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = pygame.mouse.get_pos()
            if sauvegarde_existe and btn_cont.collidepoint(mx, my):
                if charger_partie():
                    en_menu = False
            elif btn_crea.collidepoint(mx, my):
                mode = "creatif"
                en_menu = False
            elif btn_surv.collidepoint(mx, my):
                mode = "survie"
                en_menu = False

    fenetre.fill((120, 180, 235))
    titre = police_menu.render("Minecraft 2D", True, (255, 255, 255))
    fenetre.blit(titre, (LARGEUR // 2 - titre.get_width() // 2, HAUTEUR // 2 - 240))
    mpos = pygame.mouse.get_pos()
    boutons = [(btn_crea, "Créatif", (70, 140, 220)), (btn_surv, "Survie", (70, 180, 90))]
    if sauvegarde_existe:
        boutons.append((btn_cont, "Continuer", (210, 160, 40)))
    for rect, txt, coul in boutons:
        c = tuple(min(255, v + 30) for v in coul) if rect.collidepoint(mpos) else coul
        pygame.draw.rect(fenetre, c, rect, border_radius=12)
        pygame.draw.rect(fenetre, (0, 0, 0), rect, 3, border_radius=12)
        t = police_titre.render(txt, True, (255, 255, 255))
        fenetre.blit(t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2))
    sous = police.render("Créatif : vol, invincible, blocs infinis, sans faim", True, (255, 255, 255))
    fenetre.blit(sous, (LARGEUR // 2 - sous.get_width() // 2, HAUTEUR // 2 + 120))
    pygame.display.flip()
    horloge.tick(60)

creatif = (mode == "creatif")

partie_perdue = False
en_cours = True
while en_cours:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            en_cours = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                en_cours = False
            if event.key == pygame.K_F5:
                # Sauvegarde manuelle.
                message_info = "Partie sauvegardée !" if sauvegarder_partie() else "Échec de la sauvegarde"
                message_timer = 120
            if event.key == pygame.K_m:
                # Basculer Créatif <-> Survie en pleine partie.
                creatif = not creatif
                mode = "creatif" if creatif else "survie"
                if creatif:
                    vies = 5
                    faim = 100
                message_info = "Mode " + ("Créatif" if creatif else "Survie")
                message_timer = 90
            touches_num = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                           pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8)
            if event.key in touches_num:
                slot_actif = touches_num.index(event.key)
                bloc_selectionne = hotbar[slot_actif]
            if event.key in (pygame.K_e, pygame.K_i):
                inventaire_ouvert = not inventaire_ouvert
                coffre_ouvert = False
                four_ouvert = False
                if not inventaire_ouvert:
                    # On rend les ingrédients laissés dans la grille à l'inventaire.
                    for r in range(3):
                        for c in range(3):
                            if grille_craft[r][c] != 0:
                                inventaire[grille_craft[r][c]] += 1
                                grille_craft[r][c] = 0
                    item_en_main = 0
            if event.key == pygame.K_c:
                # Coffre ouvert -> fermer. Sinon -> poser un coffre (clic droit dessus pour l'ouvrir).
                four_ouvert = False
                if coffre_ouvert:
                    coffre_ouvert = False
                elif not inventaire_ouvert:
                    if inventaire.get(26, 0) <= 0:
                        message_info = "Tu n'as pas de coffre (8 bois en anneau)"
                        message_timer = 120
                    else:
                        cxx, cyy, ok = cellule_curseur_valide()
                        if ok:
                            set_bloc(cxx, cyy, 26)
                            inventaire[26] -= 1
                        else:
                            message_info = "Pose sur une case vide, à portée"
                            message_timer = 90
            if event.key == pygame.K_l and not inventaire_ouvert and not coffre_ouvert:
                # Poser un lit de 2 blocs de large (pied + tête).
                if inventaire.get(25, 0) <= 0:
                    message_info = "Il te faut un lit (3 feuilles + 3 bois)"
                    message_timer = 120
                else:
                    cxx, cyy, ok = cellule_curseur_valide()
                    # La 2e case (tête) est posée du côté du regard.
                    cxx2 = cxx + (1 if regard >= 0 else -1)
                    ok2 = get_bloc(cxx2, cyy) == 0 and (cxx2, cyy) not in torches_posees
                    if ok and ok2:
                        set_bloc(cxx, cyy, 25)        # pied
                        set_bloc(cxx2, cyy, 27)       # tête
                        inventaire[25] -= 1
                    else:
                        message_info = "Il faut 2 cases vides côte à côte, à portée"
                        message_timer = 90
            if event.key == pygame.K_t and not inventaire_ouvert and not coffre_ouvert:
                # Poser une torche à l'emplacement du curseur (dans la portée).
                if inventaire.get(23, 0) <= 0:
                    message_info = "Tu n'as pas de torche"
                    message_timer = 90
                else:
                    cxx, cyy, ok = cellule_curseur_valide()
                    if ok:
                        torches_posees.add((cxx, cyy))
                        inventaire[23] -= 1
                    else:
                        message_info = "Pose sur une case vide, à portée"
                        message_timer = 90
            if event.key == pygame.K_g and four_ouvert:
                four_ouvert = False   # refermer le fourneau
            elif event.key == pygame.K_g and not inventaire_ouvert and not coffre_ouvert:
                # Poser un fourneau à l'emplacement du curseur.
                if inventaire.get(55, 0) <= 0:
                    message_info = "Tu n'as pas de fourneau (8 pierres en anneau)"
                    message_timer = 120
                else:
                    cxx, cyy, ok = cellule_curseur_valide()
                    if ok:
                        set_bloc(cxx, cyy, 55)
                        inventaire[55] -= 1
                    else:
                        message_info = "Pose sur une case vide, à portée"
                        message_timer = 90
            if event.key == pygame.K_f and faim < 100:
                # Manger : la viande cuite (fourneau) rassasie plus que la crue.
                if inventaire.get(61, 0) > 0:
                    inventaire[61] -= 1
                    faim = min(100, faim + 60)
                elif inventaire.get(60, 0) > 0:
                    inventaire[60] -= 1
                    faim = min(100, faim + 30)
            if event.key == pygame.K_SPACE and not inventaire_ouvert and not coffre_ouvert and not four_ouvert:
                # Tirer une flèche vers le curseur. En créatif : arc et flèches infinis.
                if creatif or (arc and inventaire.get(41, 0) > 0):
                    sxs, sys_ = pygame.mouse.get_pos()
                    px = joueur_x + taille_joueur / 2
                    py = joueur_y + hauteur_joueur / 2
                    dx = (sxs + camera_x) - px
                    dy = (sys_ + camera_y) - py
                    d = math.hypot(dx, dy) or 1
                    fleches.append({"x": px, "y": py,
                                    "vx": dx / d * 14, "vy": dy / d * 14,
                                    "joueur": True})
                    if not creatif:
                        inventaire[41] -= 1

        if event.type == pygame.MOUSEBUTTONDOWN:
            souris_x, souris_y = pygame.mouse.get_pos()

            if inventaire_ouvert:
                if event.button == 1:
                    traite = False

                    # 1) Clic sur un emplacement d'armure : équiper la pièce tenue
                    #    (si elle correspond), sinon reprendre la pièce portée.
                    for i, slot in enumerate(ARMURE_SLOTS):
                        ax = ARM_X
                        ay = ARM_Y + i * (ARM_SLOT + 8)
                        if ax <= souris_x <= ax + ARM_SLOT and ay <= souris_y <= ay + ARM_SLOT:
                            traite = True
                            if item_en_main != 0 and item_en_main in ARMURES and ARMURES[item_en_main][0] == slot:
                                equipement[slot], item_en_main = item_en_main, equipement[slot]
                                recompute_armure()
                            elif item_en_main == 0 and equipement[slot] != 0:
                                item_en_main = equipement[slot]
                                equipement[slot] = 0
                                recompute_armure()
                            break

                    # 1b) Clic sur la barre rapide -> échanger main <-> case
                    if not traite:
                        for i in range(NB_HOTBAR):
                            hx = EHOT_X + i * SAC_SLOT
                            if hx <= souris_x <= hx + SAC_SLOT and EHOT_Y <= souris_y <= EHOT_Y + SAC_SLOT:
                                traite = True
                                hotbar[i], item_en_main = item_en_main, hotbar[i]
                                if i == slot_actif:
                                    bloc_selectionne = hotbar[slot_actif]
                                break

                    # 2) Clic sur une case de la grille de fabrication 3x3
                    if not traite:
                        for r in range(3):
                            for c in range(3):
                                gx = IGRID_X + c * IGRID_SLOT
                                gy = IGRID_Y + r * IGRID_SLOT
                                if gx <= souris_x <= gx + IGRID_SLOT and gy <= souris_y <= gy + IGRID_SLOT:
                                    traite = True
                                    if grille_craft[r][c] != 0:
                                        if not creatif:
                                            inventaire[grille_craft[r][c]] += 1
                                        grille_craft[r][c] = 0
                                    elif item_en_main != 0 and (creatif or inventaire.get(item_en_main, 0) > 0):
                                        grille_craft[r][c] = item_en_main
                                        if not creatif:
                                            inventaire[item_en_main] -= 1

                    # 3) Clic sur le résultat -> fabriquer
                    if not traite:
                        if (IGRID_OUT_X <= souris_x <= IGRID_OUT_X + IGRID_SLOT
                                and IGRID_OUT_Y <= souris_y <= IGRID_OUT_Y + IGRID_SLOT):
                            recette = trouver_recette(grille_craft)
                            if recette:
                                for r in range(3):
                                    for c in range(3):
                                        grille_craft[r][c] = 0
                                rtype, rcount = recette["resultat"]
                                if rtype == 40:
                                    arc = True
                                else:
                                    inventaire[rtype] = inventaire.get(rtype, 0) + rcount
                                    if rtype == 21:
                                        epee = True
                            traite = True

                    # 4) Clic dans le sac : on pose/prend/échange dans la case cliquée.
                    if not traite:
                        col = (souris_x - SAC_X) // SAC_SLOT
                        row = (souris_y - SAC_Y) // SAC_SLOT
                        if (0 <= col < SAC_COLS and 0 <= row < SAC_ROWS
                                and SAC_X <= souris_x and SAC_Y <= souris_y):
                            traite = True
                            idx = row * SAC_COLS + col
                            if creatif:
                                # Palette : prendre le type de la case (ou lâcher si on tient déjà).
                                if item_en_main != 0:
                                    item_en_main = 0
                                else:
                                    palette = [t for t in INV_TOUS if t not in hotbar
                                               and t not in equipement.values()]
                                    if idx < len(palette):
                                        item_en_main = palette[idx]
                            else:
                                # Cases fixes : échange main <-> case du sac.
                                sac_slots[idx], item_en_main = item_en_main, sac_slots[idx]
            elif coffre_ouvert:
                if event.button == 1:
                    # Clic dans le sac -> déposer 1 dans le coffre
                    liste_sac = [t for t in INV_TOUS if inventaire.get(t, 0) > 0]
                    depose = False
                    for idx, t in enumerate(liste_sac):
                        gx = CSAC_X + (idx % COF_COLS) * COF_SLOT
                        gy = CSAC_Y + (idx // COF_COLS) * COF_SLOT
                        if gx <= souris_x <= gx + COF_SLOT and gy <= souris_y <= gy + COF_SLOT:
                            inventaire[t] -= 1
                            coffre[t] = coffre.get(t, 0) + 1
                            depose = True
                            break
                    # Clic dans le coffre -> reprendre 1
                    if not depose:
                        liste_cof = [t for t in INV_TOUS if coffre.get(t, 0) > 0]
                        for idx, t in enumerate(liste_cof):
                            gx = CCOF_X + (idx % COF_COLS) * COF_SLOT
                            gy = CCOF_Y + (idx // COF_COLS) * COF_SLOT
                            if gx <= souris_x <= gx + COF_SLOT and gy <= souris_y <= gy + COF_SLOT:
                                coffre[t] -= 1
                                inventaire[t] = inventaire.get(t, 0) + 1
                                break
            elif four_ouvert:
                if event.button == 1:
                    # Clic sur une case du fourneau -> reprendre tout dans l'inventaire.
                    if FOUR_IN_X <= souris_x <= FOUR_IN_X + FOUR_SLOT and FOUR_IN_Y <= souris_y <= FOUR_IN_Y + FOUR_SLOT:
                        if four_in[1] > 0:
                            inventaire[four_in[0]] = inventaire.get(four_in[0], 0) + four_in[1]
                            four_in = [0, 0]
                    elif FOUR_FUEL_X <= souris_x <= FOUR_FUEL_X + FOUR_SLOT and FOUR_FUEL_Y <= souris_y <= FOUR_FUEL_Y + FOUR_SLOT:
                        if four_fuel[1] > 0:
                            inventaire[four_fuel[0]] = inventaire.get(four_fuel[0], 0) + four_fuel[1]
                            four_fuel = [0, 0]
                    elif FOUR_OUT_X <= souris_x <= FOUR_OUT_X + FOUR_SLOT and FOUR_OUT_Y <= souris_y <= FOUR_OUT_Y + FOUR_SLOT:
                        if four_out[1] > 0:
                            inventaire[four_out[0]] = inventaire.get(four_out[0], 0) + four_out[1]
                            four_out = [0, 0]
                    else:
                        # Clic sur le sac -> déposer (charbon -> combustible ; fondable -> entrée).
                        liste_sac = [t for t in INV_TOUS if inventaire.get(t, 0) > 0]
                        for idx, t in enumerate(liste_sac):
                            gx = FSAC_X + (idx % FSAC_COLS) * FSAC_SLOT
                            gy = FSAC_Y + (idx // FSAC_COLS) * FSAC_SLOT
                            if gx <= souris_x <= gx + FSAC_SLOT and gy <= souris_y <= gy + FSAC_SLOT:
                                if t == 7 and four_fuel[0] in (0, 7):
                                    four_fuel[0] = 7
                                    four_fuel[1] += inventaire[7]
                                    inventaire[7] = 0
                                elif t in FUSION and four_in[0] in (0, t):
                                    four_in[0] = t
                                    four_in[1] += inventaire[t]
                                    inventaire[t] = 0
                                break
            else:
                # Sélection d'une case en cliquant dans la hotbar.
                clic_hotbar = False
                if event.button == 1 and HOT_Y <= souris_y <= HOT_Y + SLOT:
                    for i in range(NB_HOTBAR):
                        sx = HOT_X + i * SLOT
                        if sx <= souris_x <= sx + SLOT:
                            slot_actif = i
                            bloc_selectionne = hotbar[slot_actif]
                            clic_hotbar = True
                            break

                monde_clic_x = (souris_x + camera_x) // TAILLE_BLOC
                monde_clic_y = (souris_y + camera_y) // TAILLE_BLOC

                if event.button == 1 and not clic_hotbar:
                    zombi_tue = False
                    cochon_tue = False

                    if epee:
                        for z in zombis[:]:
                            zx_e = z["x"] - camera_x
                            zy_e = z["y"] - camera_y
                            proche = math.hypot(joueur_x - z["x"], joueur_y - z["y"]) <= PORTEE_PX
                            if proche and zx_e <= souris_x <= zx_e + taille_zombi and zy_e <= souris_y <= zy_e + taille_zombi:
                                zombis.remove(z)
                                zombi_tue = True
                        for s in squelettes[:]:
                            sx_e = s["x"] - camera_x
                            sy_e = s["y"] - camera_y
                            proche = math.hypot(joueur_x - s["x"], joueur_y - s["y"]) <= PORTEE_PX
                            if proche and sx_e <= souris_x <= sx_e + taille_squelette and sy_e <= souris_y <= sy_e + taille_squelette:
                                squelettes.remove(s)
                                inventaire[41] += 2   # flèches récupérées
                                zombi_tue = True
                        for a in araignees[:]:
                            ax_e = a["x"] - camera_x
                            ay_e = a["y"] - camera_y
                            proche = math.hypot(joueur_x - a["x"], joueur_y - a["y"]) <= PORTEE_PX
                            if proche and ax_e <= souris_x <= ax_e + taille_araignee and ay_e <= souris_y <= ay_e + taille_araignee:
                                araignees.remove(a)
                                inventaire[42] += 1   # ficelle récupérée
                                zombi_tue = True
                        for c in cochons[:]:
                            cx_e = c["x"] - camera_x
                            cy_e = c["y"] - camera_y
                            proche = math.hypot(joueur_x - c["x"], joueur_y - c["y"]) <= PORTEE_PX
                            if proche and cx_e <= souris_x <= cx_e + taille_cochon and cy_e <= souris_y <= cy_e + taille_cochon:
                                cochons.remove(c)
                                inventaire[60] += 2
                                cochon_tue = True

                    # Reprendre une torche posée en cliquant dessus
                    if not zombi_tue and not cochon_tue and (monde_clic_x, monde_clic_y) in torches_posees:
                        torches_posees.discard((monde_clic_x, monde_clic_y))
                        inventaire[23] += 1
                        zombi_tue = True   # (empêche de casser le bloc derrière)

                    # Casser un lit : les 2 cases (pied + tête) partent ensemble
                    if not zombi_tue and get_bloc(monde_clic_x, monde_clic_y) in (25, 27):
                        t0 = get_bloc(monde_clic_x, monde_clic_y)
                        partenaire = 27 if t0 == 25 else 25
                        set_bloc(monde_clic_x, monde_clic_y, 0)
                        if get_bloc(monde_clic_x - 1, monde_clic_y) == partenaire:
                            set_bloc(monde_clic_x - 1, monde_clic_y, 0)
                        elif get_bloc(monde_clic_x + 1, monde_clic_y) == partenaire:
                            set_bloc(monde_clic_x + 1, monde_clic_y, 0)
                        inventaire[25] += 1
                        zombi_tue = True

                    if not zombi_tue and not cochon_tue:
                        type_casse = get_bloc(monde_clic_x, monde_clic_y)
                        if type_casse != 0 and type_casse != 6:
                            pcx = (joueur_x + taille_joueur / 2) / TAILLE_BLOC
                            pcy = (joueur_y + hauteur_joueur / 2) / TAILLE_BLOC
                            distance_bloc = math.hypot(monde_clic_x + 0.5 - pcx,
                                                       monde_clic_y + 0.5 - pcy)
                            if distance_bloc > PORTEE:
                                message_info = "Trop loin (10 blocs max)"
                                message_timer = 90
                            elif bloc_accessible(monde_clic_x, monde_clic_y):
                                if type_casse in inventaire:
                                    # Bonus d'outil : pioche->minerais, hache->bois, pelle->terre/herbe
                                    gain = 1
                                    if 7 <= type_casse <= 12 and inventaire.get(22, 0) > 0:
                                        gain = 2
                                    elif type_casse == 4 and inventaire.get(53, 0) > 0:
                                        gain = 2
                                    elif type_casse in (1, 2) and inventaire.get(54, 0) > 0:
                                        gain = 2
                                    inventaire[type_casse] += gain
                                set_bloc(monde_clic_x, monde_clic_y, 0)
                            else:
                                message_info = "Bloc inaccessible : il est enferme"
                                message_timer = 90

                if event.button == 3:
                    cible = get_bloc(monde_clic_x, monde_clic_y)
                    pcx = (joueur_x + taille_joueur / 2) / TAILLE_BLOC
                    pcy = (joueur_y + hauteur_joueur / 2) / TAILLE_BLOC
                    proche_i = math.hypot(monde_clic_x + 0.5 - pcx, monde_clic_y + 0.5 - pcy) <= PORTEE
                    if cible in (25, 27) and proche_i:
                        # Dormir dans le lit posé (la nuit).
                        if not est_nuit:
                            message_info = "Tu ne peux dormir que la nuit"
                            message_timer = 90
                        else:
                            heure = 0
                            est_nuit = False
                            vies = 5
                            faim = min(100, faim + 20)
                            zombis.clear()
                            squelettes.clear()
                            araignees.clear()
                            fleches.clear()
                            message_info = "Tu as bien dormi ! Bonjour :)"
                            message_timer = 120
                    elif cible == 26 and proche_i:
                        # Ouvrir le coffre posé.
                        coffre_ouvert = True
                        inventaire_ouvert = False
                    elif cible == 55 and proche_i:
                        # Ouvrir l'interface du fourneau.
                        four_ouvert = True
                        inventaire_ouvert = False
                        coffre_ouvert = False
                    elif cible == 0 or cible == 6:
                        # Pose sur de l'air OU dans l'eau (le bloc remplace l'eau).
                        bs = hotbar[slot_actif]
                        a_assez = creatif or inventaire.get(bs, 0) > 0
                        if bs != 0 and a_assez:
                            pose_ok = False
                            if bs == 23:
                                # Torche (stockée à part, n'apparaît pas comme un bloc).
                                if (monde_clic_x, monde_clic_y) not in torches_posees:
                                    torches_posees.add((monde_clic_x, monde_clic_y))
                                    pose_ok = True
                            elif bs == 25:
                                # Lit : 2 cases (pied + tête) du côté du regard.
                                cxx2 = monde_clic_x + (1 if regard >= 0 else -1)
                                if get_bloc(cxx2, monde_clic_y) in (0, 6) and (cxx2, monde_clic_y) not in torches_posees:
                                    set_bloc(monde_clic_x, monde_clic_y, 25)
                                    set_bloc(cxx2, monde_clic_y, 27)
                                    pose_ok = True
                                else:
                                    message_info = "Il faut 2 cases vides côte à côte"
                                    message_timer = 90
                            elif bs in (26, 55) or bs in POSABLES:
                                set_bloc(monde_clic_x, monde_clic_y, bs)
                                pose_ok = True
                            if pose_ok and not creatif:
                                inventaire[bs] -= 1

    # Entretien de l'inventaire par cases (survie) : on vide les cases dont le
    # stock est épuisé, puis on range chaque nouvel objet dans la 1re case libre
    # du sac (de haut-gauche à droite).
    if not creatif:
        for _i in range(NB_HOTBAR):
            if hotbar[_i] != 0 and inventaire.get(hotbar[_i], 0) <= 0:
                hotbar[_i] = 0
        for _i in range(len(sac_slots)):
            if sac_slots[_i] != 0 and inventaire.get(sac_slots[_i], 0) <= 0:
                sac_slots[_i] = 0
        if item_en_main != 0 and inventaire.get(item_en_main, 0) <= 0:
            item_en_main = 0
        _portes = set(equipement.values())
        for _t in INV_TOUS:
            if (inventaire.get(_t, 0) > 0 and _t not in hotbar and _t not in sac_slots
                    and _t != item_en_main and _t not in _portes):
                if 0 in hotbar:                       # d'abord la barre rapide
                    hotbar[hotbar.index(0)] = _t
                elif 0 in sac_slots:                  # sinon le sac
                    sac_slots[sac_slots.index(0)] = _t
    bloc_selectionne = hotbar[slot_actif]

    # Fusion du fourneau (tourne en continu, même menu fermé) : besoin d'un objet
    # fondable en entrée, de charbon en combustible, et d'une sortie compatible.
    if four_in[1] > 0 and four_in[0] in FUSION and four_fuel[1] > 0:
        _res = FUSION[four_in[0]]
        if four_out[0] == 0 or four_out[0] == _res:
            four_progres += 1
            if four_progres >= DUREE_FUSION:
                four_progres = 0
                four_in[1] -= 1
                if four_in[1] == 0:
                    four_in[0] = 0
                four_fuel[1] -= 1
                if four_fuel[1] == 0:
                    four_fuel[0] = 0
                four_out[0] = _res
                four_out[1] += 1
        else:
            four_progres = 0
    else:
        four_progres = 0

    if not inventaire_ouvert and not coffre_ouvert and not four_ouvert:
        touches = pygame.key.get_pressed()

        col_milieu = int((joueur_x + taille_joueur // 2) // TAILLE_BLOC)
        # Le joueur fait 2 blocs : on considère qu'il est dans l'eau si le haut OU
        # le bas du corps est immergé, sinon on cesse de nager avant d'être sorti.
        lig_eau_h = int((joueur_y + hauteur_joueur * 0.3) // TAILLE_BLOC)
        lig_eau_b = int((joueur_y + hauteur_joueur - 6) // TAILLE_BLOC)
        dans_eau = get_bloc(col_milieu, lig_eau_h) == 6 or get_bloc(col_milieu, lig_eau_b) == 6

        deplacement_x = 0
        if touches[pygame.K_LEFT]: deplacement_x = -5
        if touches[pygame.K_RIGHT]: deplacement_x = 5
        if dans_eau: deplacement_x = int(deplacement_x * 0.5)

        # Animation de marche : la phase avance tant qu'on se déplace, sinon
        # elle revient à la position debout (neutre).
        if deplacement_x != 0:
            phase_marche += 0.15
            regard = 1 if deplacement_x > 0 else -1
        else:
            phase_marche = 0.0

        joueur_x += deplacement_x

        col_g = int(joueur_x // TAILLE_BLOC)
        col_d = int((joueur_x + taille_joueur) // TAILLE_BLOC)
        # Le joueur fait 2 blocs de haut : on teste haut, milieu ET bas.
        lig_h = int(joueur_y // TAILLE_BLOC)
        lig_m = int((joueur_y + hauteur_joueur // 2) // TAILLE_BLOC)
        lig_b = int((joueur_y + hauteur_joueur - 1) // TAILLE_BLOC)

        def _mur(col):
            for lg in (lig_h, lig_m, lig_b):
                b = get_bloc(col, lg)
                if b != 0 and b != 6:
                    return True
            return False

        if deplacement_x > 0 and _mur(col_d):
            joueur_x = col_d * TAILLE_BLOC - taille_joueur
        if deplacement_x < 0 and _mur(col_g):
            joueur_x = (col_g + 1) * TAILLE_BLOC

        if creatif:
            # Mode créatif : vol libre, aucune gravité.
            vitesse_y = 0
            if touches[pygame.K_UP]:
                vitesse_y = -7
            elif touches[pygame.K_DOWN]:
                vitesse_y = 7
        elif dans_eau:
            vitesse_y += gravite * 0.2
            vitesse_y *= 0.7
            if touches[pygame.K_UP]:
                vitesse_y = -7      # nage vers le haut, assez fort pour sortir
            elif touches[pygame.K_DOWN]:
                vitesse_y = 6
        else:
            if touches[pygame.K_UP] and peut_sauter:
                vitesse_y = -10
                peut_sauter = False
            vitesse_y += gravite

        joueur_y += vitesse_y

        col_g = int(joueur_x // TAILLE_BLOC)
        col_d = int((joueur_x + taille_joueur - 1) // TAILLE_BLOC)
        peut_sauter = False

        if vitesse_y > 0:
            lig_bas = int((joueur_y + hauteur_joueur) // TAILLE_BLOC)
            b_g = get_bloc(col_g, lig_bas)
            b_d = get_bloc(col_d, lig_bas)
            if (b_g != 0 and b_g != 6) or (b_d != 0 and b_d != 6):
                joueur_y = lig_bas * TAILLE_BLOC - hauteur_joueur
                vitesse_y = 0
                peut_sauter = True
        elif vitesse_y < 0:
            lig_haut = int(joueur_y // TAILLE_BLOC)
            b_g = get_bloc(col_g, lig_haut)
            b_d = get_bloc(col_d, lig_haut)
            if (b_g != 0 and b_g != 6) or (b_d != 0 and b_d != 6):
                joueur_y = (lig_haut + 1) * TAILLE_BLOC
                vitesse_y = 0

        chunk_joueur = int(joueur_x) // (TAILLE_CHUNK * TAILLE_BLOC)
        for i in range(-4, 5):
            get_chunk(chunk_joueur + i)

        eau_timer += 1
        if eau_timer >= 10:
            eau_timer = 0
            update_eau(joueur_x, joueur_y)

        heure = (heure + 1) % DUREE_CYCLE
        est_nuit = heure >= DUREE_CYCLE // 2

        if est_nuit:
            spawn_timer += 1
            if spawn_timer >= 300 and (len(zombis) + len(squelettes) + len(araignees)) < 12:
                spawn_timer = 0
                mx = joueur_x + random.choice([-1, 1]) * random.randint(300, 600)
                mcx = int(mx // TAILLE_BLOC)
                mcy = int(joueur_y // TAILLE_BLOC)
                # Une torche à ≤ 5 blocs éclaire la zone : pas d'apparition.
                pres_torche = any(math.hypot(mcx - tx, mcy - ty) <= 5
                                  for (tx, ty) in torches_posees)
                if not pres_torche:
                    tirage = random.random()
                    if tirage < 0.35:
                        squelettes.append({"x": mx, "y": 0, "vitesse_y": 0,
                                           "direction": 1, "tir": random.randint(60, 120)})
                    elif tirage < 0.6:
                        araignees.append({"x": mx, "y": 0, "vitesse_y": 0, "direction": 1})
                    else:
                        zombis.append({"x": mx, "y": 0, "vitesse_y": 0, "direction": 1})
        else:
            spawn_timer = 0

        if not creatif:
            faim_timer += 1
            if faim_timer >= 300:
                faim_timer = 0
                faim -= 5
                if faim < 0:
                    faim = 0

            if faim == 0 and invincible == 0:
                # La faim traverse l'armure (comme dans Minecraft).
                vies -= 1
                invincible = 90

            # Régénération : bien nourri (faim >= 80) -> on récupère des cœurs.
            if faim >= 80 and vies < 5:
                regen_timer += 1
                if regen_timer >= 400:
                    regen_timer = 0
                    vies += 1
                    faim -= 5
            else:
                regen_timer = 0

        for z in zombis[:]:
            if abs(z["x"] - joueur_x) > 1500:
                zombis.remove(z)
                continue

            au_sol_z = mob_gravite(z, taille_zombi)

            dist = math.sqrt((joueur_x - z["x"]) ** 2 + (joueur_y - z["y"]) ** 2)
            if dist < 300:
                z["direction"] = 1 if joueur_x > z["x"] else -1
                dx = z["direction"] * 2
            else:
                if random.randint(1, 60) == 1:
                    z["direction"] *= -1
                dx = z["direction"]

            bloque_z = mob_deplacer_x(z, dx, taille_zombi)
            if bloque_z and au_sol_z and z["vitesse_y"] == 0:
                if mob_marche_franchissable(z, taille_zombi, z["direction"]):
                    z["vitesse_y"] = -9          # marche d'un bloc : il saute
                elif dist >= 300:
                    z["direction"] *= -1         # en errance : demi-tour devant un mur

            if invincible == 0 and not creatif:
                dcx = (joueur_x + taille_joueur / 2) - (z["x"] + taille_zombi / 2)
                dcy = (joueur_y + hauteur_joueur / 2) - (z["y"] + taille_zombi / 2)
                if abs(dcx) < (taille_joueur + taille_zombi) / 2 and abs(dcy) < (hauteur_joueur + taille_zombi) / 2:
                    # L'armure encaisse le coup en priorité, sinon on perd une vie.
                    if armure > 0:
                        armure -= 1
                    else:
                        vies -= 1
                    invincible = 90

        # --- Squelettes : gardent leurs distances et tirent des flèches ---
        for s in squelettes[:]:
            if abs(s["x"] - joueur_x) > 1500:
                squelettes.remove(s)
                continue

            au_sol_s = mob_gravite(s, taille_squelette)

            dist = math.hypot(joueur_x - s["x"], joueur_y - s["y"])
            s["direction"] = 1 if joueur_x > s["x"] else -1
            dx = 0
            if dist > 340:
                dx = s["direction"] * 2          # approche
            elif dist < 190:
                dx = -s["direction"] * 2         # recule pour garder ses distances

            bloque_s = mob_deplacer_x(s, dx, taille_squelette)
            if bloque_s and au_sol_s and s["vitesse_y"] == 0 \
                    and mob_marche_franchissable(s, taille_squelette, 1 if dx > 0 else -1):
                s["vitesse_y"] = -9

            s["tir"] -= 1
            if dist < 560 and s["tir"] <= 0:
                dx = joueur_x - s["x"]
                dy = joueur_y - s["y"]
                d = math.hypot(dx, dy) or 1
                fleches.append({"x": s["x"] + taille_squelette / 2,
                                "y": s["y"] + taille_squelette / 2,
                                "vx": dx / d * 11, "vy": dy / d * 11 - 1.5,
                                "joueur": False})
                s["tir"] = random.randint(90, 150)

        # --- Araignées : rapides, grimpent les murs, lâchent de la ficelle ---
        for a in araignees[:]:
            if abs(a["x"] - joueur_x) > 1400:
                araignees.remove(a)
                continue

            au_sol_a = mob_gravite(a, taille_araignee)

            dist = math.hypot(joueur_x - a["x"], joueur_y - a["y"])
            if dist < 420:
                a["direction"] = 1 if joueur_x > a["x"] else -1
                dx = a["direction"] * 3               # rapide
            else:
                if random.randint(1, 60) == 1:
                    a["direction"] *= -1
                dx = a["direction"] * 2

            bloque_a = mob_deplacer_x(a, dx, taille_araignee)
            if bloque_a:
                a["vitesse_y"] = -7          # l'araignée grimpe le mur

            dcx_a = (joueur_x + taille_joueur / 2) - (a["x"] + taille_araignee / 2)
            dcy_a = (joueur_y + hauteur_joueur / 2) - (a["y"] + taille_araignee / 2)
            if invincible == 0 and not creatif and abs(dcx_a) < (taille_joueur + taille_araignee) / 2 \
                    and abs(dcy_a) < (hauteur_joueur + taille_araignee) / 2:
                if armure > 0:
                    armure -= 1
                else:
                    vies -= 1
                invincible = 90

        # --- Flèches (projectiles) ---
        for f in fleches[:]:
            f["vy"] += 0.25
            f["x"] += f["vx"]
            f["y"] += f["vy"]

            if abs(f["x"] - joueur_x) > 2500:
                fleches.remove(f)
                continue

            bloc_f = get_bloc(int(f["x"] // TAILLE_BLOC), int(f["y"] // TAILLE_BLOC))
            if bloc_f != 0 and bloc_f != 6:
                fleches.remove(f)
                continue

            if f["joueur"]:
                touche = False
                for z in zombis[:]:
                    if abs(f["x"] - (z["x"] + taille_zombi / 2)) < taille_zombi / 2 \
                            and abs(f["y"] - (z["y"] + taille_zombi / 2)) < taille_zombi / 2:
                        zombis.remove(z)
                        touche = True
                        break
                if not touche:
                    for s in squelettes[:]:
                        if abs(f["x"] - (s["x"] + taille_squelette / 2)) < taille_squelette / 2 \
                                and abs(f["y"] - (s["y"] + taille_squelette / 2)) < taille_squelette / 2:
                            squelettes.remove(s)
                            inventaire[41] += 2
                            touche = True
                            break
                if not touche:
                    for a in araignees[:]:
                        if abs(f["x"] - (a["x"] + taille_araignee / 2)) < taille_araignee / 2 \
                                and abs(f["y"] - (a["y"] + taille_araignee / 2)) < taille_araignee / 2:
                            araignees.remove(a)
                            inventaire[42] += 1
                            touche = True
                            break
                if not touche:
                    for co in cochons[:]:
                        if abs(f["x"] - (co["x"] + taille_cochon / 2)) < taille_cochon / 2 \
                                and abs(f["y"] - (co["y"] + taille_cochon / 2)) < taille_cochon / 2:
                            cochons.remove(co)
                            inventaire[60] += 2
                            touche = True
                            break
                if touche:
                    fleches.remove(f)
                    continue
            else:
                if abs(f["x"] - (joueur_x + taille_joueur / 2)) < taille_joueur / 2 + 3 \
                        and abs(f["y"] - (joueur_y + hauteur_joueur / 2)) < hauteur_joueur / 2 + 3:
                    if invincible == 0 and not creatif:
                        if armure > 0:
                            armure -= 1
                        else:
                            vies -= 1
                        invincible = 90
                    fleches.remove(f)
                    continue

        for c in cochons[:]:
            if abs(c["x"] - joueur_x) > 1000:
                cochons.remove(c)
                continue

            # --- Vertical (gravité) ---
            c["vitesse_y"] += gravite
            c["y"] += c["vitesse_y"]

            col_g_c = int(c["x"] // TAILLE_BLOC)
            col_d_c = int((c["x"] + taille_cochon - 1) // TAILLE_BLOC)

            if c["vitesse_y"] >= 0:
                # collision avec le sol
                lig_bas_c = int((c["y"] + taille_cochon) // TAILLE_BLOC)
                b_g = get_bloc(col_g_c, lig_bas_c)
                b_d = get_bloc(col_d_c, lig_bas_c)
                if (b_g != 0 and b_g != 6) or (b_d != 0 and b_d != 6):
                    c["y"] = lig_bas_c * TAILLE_BLOC - taille_cochon
                    c["vitesse_y"] = 0
            else:
                # collision avec un plafond (empêche de rester "coincé" dans un saut)
                lig_haut_c = int(c["y"] // TAILLE_BLOC)
                b_g = get_bloc(col_g_c, lig_haut_c)
                b_d = get_bloc(col_d_c, lig_haut_c)
                if (b_g != 0 and b_g != 6) or (b_d != 0 and b_d != 6):
                    c["y"] = (lig_haut_c + 1) * TAILLE_BLOC
                    c["vitesse_y"] = 0

            # le cochon est-il posé sur le sol ?
            col_g_c = int(c["x"] // TAILLE_BLOC)
            col_d_c = int((c["x"] + taille_cochon - 1) // TAILLE_BLOC)
            lig_sous_c = int((c["y"] + taille_cochon) // TAILLE_BLOC)
            b_sg = get_bloc(col_g_c, lig_sous_c)
            b_sd = get_bloc(col_d_c, lig_sous_c)
            est_au_sol_c = (b_sg != 0 and b_sg != 6) or (b_sd != 0 and b_sd != 6)

            # changement de direction aléatoire
            if random.randint(1, 90) == 1:
                c["direction"] *= -1

            # --- Déplacement horizontal (balayé : on vérifie AVANT de bouger,
            #     le cochon ne peut donc jamais traverser un bloc ni se téléporter) ---
            nx = c["x"] + c["direction"]
            lig_h_c = int(c["y"] // TAILLE_BLOC)
            lig_b_c = int((c["y"] + taille_cochon - 1) // TAILLE_BLOC)
            if c["direction"] > 0:
                col_avant = int((nx + taille_cochon - 1) // TAILLE_BLOC)
            else:
                col_avant = int(nx // TAILLE_BLOC)
            b_h = get_bloc(col_avant, lig_h_c)
            b_b = get_bloc(col_avant, lig_b_c)
            bloque_devant = (b_h != 0 and b_h != 6) or (b_b != 0 and b_b != 6)

            if bloque_devant:
                a_saute = False
                # ne sauter que si c'est une marche d'UN seul bloc, dégagée au-dessus
                if est_au_sol_c and c["vitesse_y"] == 0:
                    b_marche = get_bloc(col_avant, lig_b_c)          # bloc devant, au niveau des pieds
                    b_dessus = get_bloc(col_avant, lig_b_c - 1)      # case juste au-dessus de la marche
                    b_tete_g = get_bloc(col_g_c, lig_h_c - 1)        # dégagement au-dessus du cochon
                    b_tete_d = get_bloc(col_d_c, lig_h_c - 1)
                    marche_1bloc = (b_marche != 0 and b_marche != 6) \
                        and (b_dessus == 0 or b_dessus == 6) \
                        and (b_tete_g == 0 or b_tete_g == 6) \
                        and (b_tete_d == 0 or b_tete_d == 6)
                    if marche_1bloc:
                        c["vitesse_y"] = -9
                        a_saute = True
                if not a_saute:
                    c["direction"] *= -1   # demi-tour, on ne bouge pas ce tour-ci
            else:
                c["x"] = nx

        if invincible > 0:
            invincible -= 1

        if len(cochons) < 4 and random.randint(1, 300) == 1:
            cx_c = joueur_x + random.choice([-1, 1]) * random.randint(300, 600)
            cochons.append({"x": cx_c, "y": 0, "vitesse_y": 0, "direction": 1})

    camera_x = int(joueur_x - LARGEUR // 2 + taille_joueur // 2)
    camera_y = int(joueur_y - HAUTEUR // 2 + hauteur_joueur // 2)
    # Aucune limite verticale : le monde est infini vers le bas ET vers le haut
    # (bases aériennes), la caméra suit librement le joueur.

    if heure < DUREE_CYCLE // 2:
        progression = heure / (DUREE_CYCLE // 2)
        if progression < 0.1:
            obscurite = int(180 * (1 - progression / 0.1))
        elif progression > 0.9:
            obscurite = int(180 * ((progression - 0.9) / 0.1))
        else:
            obscurite = 0
    else:
        obscurite = 180

    # Plus sombre sous terre
    profondeur = int(joueur_y // TAILLE_BLOC)
    chunk_j = int(joueur_x) // (TAILLE_CHUNK * TAILLE_BLOC)
    col_j = int(joueur_x // TAILLE_BLOC) % TAILLE_CHUNK
    if col_j < 0:
        col_j += TAILLE_CHUNK
    if chunk_j in chunks:
        hauteur_surface = chunks[chunk_j]["hauteurs"][min(col_j, TAILLE_CHUNK - 1)]
        sous_terre = profondeur > hauteur_surface + 2
    else:
        sous_terre = False

    obscurite_finale = obscurite
    if sous_terre:
        profondeur_relative = profondeur - hauteur_surface
        extra_obscurite = min(150, profondeur_relative * 8)
        obscurite_finale = min(220, obscurite + extra_obscurite)

    if obscurite == 0 and not sous_terre:
        ciel_couleur = CIEL
    else:
        ratio = obscurite / 180
        r = int(135 * (1 - ratio) + 10 * ratio)
        g = int(206 * (1 - ratio) + 10 * ratio)
        b = int(235 * (1 - ratio) + 30 * ratio)
        ciel_couleur = (r, g, b)

    fenetre.fill(ciel_couleur)

    col_debut = camera_x // TAILLE_BLOC - 1
    col_fin = (camera_x + LARGEUR) // TAILLE_BLOC + 1
    # lig_debut peut être négatif : on affiche aussi les blocs posés dans le ciel.
    lig_debut = camera_y // TAILLE_BLOC - 1
    lig_fin = (camera_y + HAUTEUR) // TAILLE_BLOC + 2

    for ligne in range(lig_debut, lig_fin):
        for col in range(col_debut, col_fin):
            type_bloc = get_bloc(col, ligne)
            if type_bloc != 0:
                couleur = couleur_bloc(type_bloc)
                pos_x = col * TAILLE_BLOC - camera_x
                pos_y = ligne * TAILLE_BLOC - camera_y
                if type_bloc == 6:
                    if EAU_FRAMES:
                        frame = EAU_FRAMES[(pygame.time.get_ticks() // 300) % len(EAU_FRAMES)]
                        fenetre.blit(frame, (pos_x, pos_y))
                    else:
                        pygame.draw.rect(fenetre, (30, 100, 200), (pos_x, pos_y, TAILLE_BLOC, TAILLE_BLOC))
                        surf_eau = pygame.Surface((TAILLE_BLOC, TAILLE_BLOC), pygame.SRCALPHA)
                        surf_eau.fill((30, 100, 220, 150))
                        fenetre.blit(surf_eau, (pos_x, pos_y))
                elif type_bloc in (25, 27):
                    # Lit (2 blocs) : cadre bois + matelas rouge ; oreiller côté tête (27)
                    pygame.draw.rect(fenetre, (120, 80, 50), (pos_x, pos_y + TAILLE_BLOC // 2, TAILLE_BLOC, TAILLE_BLOC // 2))
                    pygame.draw.rect(fenetre, (200, 60, 70), (pos_x + 1, pos_y + TAILLE_BLOC // 3, TAILLE_BLOC - 2, TAILLE_BLOC // 2))
                    if type_bloc == 27:
                        pygame.draw.rect(fenetre, (240, 240, 240),
                                         (pos_x + 3, pos_y + TAILLE_BLOC // 3, 11, TAILLE_BLOC // 2 - 2))
                    pygame.draw.rect(fenetre, (0, 0, 0), (pos_x, pos_y, TAILLE_BLOC, TAILLE_BLOC), 1)
                elif type_bloc == 26:
                    # Coffre : caisse en bois avec couvercle et loquet
                    pygame.draw.rect(fenetre, (150, 105, 55), (pos_x + 2, pos_y + 5, TAILLE_BLOC - 4, TAILLE_BLOC - 7))
                    pygame.draw.rect(fenetre, (110, 75, 35), (pos_x + 2, pos_y + 5, TAILLE_BLOC - 4, 11))
                    pygame.draw.rect(fenetre, (60, 45, 20), (pos_x + TAILLE_BLOC // 2 - 3, pos_y + 12, 6, 9))
                    pygame.draw.rect(fenetre, (0, 0, 0), (pos_x, pos_y, TAILLE_BLOC, TAILLE_BLOC), 1)
                elif type_bloc == 55:
                    # Fourneau : bloc de pierre avec une ouverture sombre + braises
                    pygame.draw.rect(fenetre, (95, 95, 100), (pos_x, pos_y, TAILLE_BLOC, TAILLE_BLOC))
                    for _dp in ((6, 6), (26, 8), (10, 26), (24, 24)):
                        pygame.draw.rect(fenetre, (75, 75, 80), (pos_x + _dp[0], pos_y + _dp[1], 5, 5))
                    pygame.draw.rect(fenetre, (30, 25, 25), (pos_x + 9, pos_y + 16, TAILLE_BLOC - 18, TAILLE_BLOC - 22))
                    pygame.draw.rect(fenetre, (255, 150, 40), (pos_x + 12, pos_y + TAILLE_BLOC - 12, TAILLE_BLOC - 24, 5))
                    pygame.draw.rect(fenetre, (0, 0, 0), (pos_x, pos_y, TAILLE_BLOC, TAILLE_BLOC), 1)
                elif type_bloc in TEXTURES:
                    # Texture procédurale pré-générée (herbe, terre, pierre, bois, minerais…)
                    fenetre.blit(TEXTURES[type_bloc], (pos_x, pos_y))
                else:
                    pygame.draw.rect(fenetre, couleur, (pos_x, pos_y, TAILLE_BLOC, TAILLE_BLOC))
                    pygame.draw.rect(fenetre, (0, 0, 0), (pos_x, pos_y, TAILLE_BLOC, TAILLE_BLOC), 1)

    # Torches posées (bâton + flamme + halo lumineux)
    for (tx, ty) in torches_posees:
        px = tx * TAILLE_BLOC - camera_x
        py = ty * TAILLE_BLOC - camera_y
        if -TAILLE_BLOC <= px <= LARGEUR and -TAILLE_BLOC <= py <= HAUTEUR:
            cxp = px + TAILLE_BLOC // 2
            halo = pygame.Surface((TAILLE_BLOC * 3, TAILLE_BLOC * 3), pygame.SRCALPHA)
            pygame.draw.circle(halo, (255, 200, 90, 45), (TAILLE_BLOC * 3 // 2, TAILLE_BLOC * 3 // 2), TAILLE_BLOC * 3 // 2)
            fenetre.blit(halo, (cxp - TAILLE_BLOC * 3 // 2, py + 10 - TAILLE_BLOC * 3 // 2))
            pygame.draw.rect(fenetre, (120, 80, 40), (cxp - 3, py + 12, 6, TAILLE_BLOC - 14))
            pygame.draw.circle(fenetre, (255, 160, 30), (cxp, py + 12), 7)
            pygame.draw.circle(fenetre, (255, 240, 130), (cxp, py + 11), 4)

    for z in zombis:
        zx_e = z["x"] - camera_x
        zy_e = z["y"] - camera_y
        pygame.draw.rect(fenetre, (50, 150, 50), (zx_e, zy_e, taille_zombi, taille_zombi))
        pygame.draw.circle(fenetre, (255, 0, 0), (int(zx_e + 10), int(zy_e + 12)), 4)
        pygame.draw.circle(fenetre, (255, 0, 0), (int(zx_e + 25), int(zy_e + 12)), 4)
        pygame.draw.line(fenetre, (0, 0, 0), (int(zx_e + 8), int(zy_e + 22)), (int(zx_e + 27), int(zy_e + 22)), 2)

    for s in squelettes:
        sx_e = s["x"] - camera_x
        sy_e = s["y"] - camera_y
        pygame.draw.rect(fenetre, (225, 225, 225), (sx_e, sy_e, taille_squelette, taille_squelette))
        pygame.draw.circle(fenetre, (40, 40, 40), (int(sx_e + 11), int(sy_e + 13)), 4)
        pygame.draw.circle(fenetre, (40, 40, 40), (int(sx_e + 24), int(sy_e + 13)), 4)
        # côtes
        for cy in range(20, taille_squelette - 2, 5):
            pygame.draw.line(fenetre, (150, 150, 150), (sx_e + 6, sy_e + cy), (sx_e + taille_squelette - 6, sy_e + cy), 1)
        # petit arc
        arc_x = sx_e + (taille_squelette if s.get("direction", 1) > 0 else -6)
        pygame.draw.arc(fenetre, (120, 80, 40),
                        (arc_x - 4, sy_e + 6, 12, taille_squelette - 10), -1.4, 1.4, 2)

    for a in araignees:
        ax_e = a["x"] - camera_x
        ay_e = a["y"] - camera_y
        pygame.draw.rect(fenetre, (40, 40, 45), (ax_e + 4, ay_e + 6, taille_araignee - 8, taille_araignee - 12))
        pygame.draw.circle(fenetre, (60, 60, 70), (int(ax_e + taille_araignee // 2), int(ay_e + 10)), 6)
        pygame.draw.circle(fenetre, (200, 30, 30), (int(ax_e + taille_araignee // 2 - 3), int(ay_e + 9)), 2)
        pygame.draw.circle(fenetre, (200, 30, 30), (int(ax_e + taille_araignee // 2 + 3), int(ay_e + 9)), 2)
        for dy in (10, 16, 22):
            pygame.draw.line(fenetre, (20, 20, 25), (ax_e + 4, ay_e + dy), (ax_e - 4, ay_e + dy - 3), 2)
            pygame.draw.line(fenetre, (20, 20, 25), (ax_e + taille_araignee - 4, ay_e + dy), (ax_e + taille_araignee + 4, ay_e + dy - 3), 2)

    for f in fleches:
        fx_e = f["x"] - camera_x
        fy_e = f["y"] - camera_y
        vx, vy = f["vx"], f["vy"]
        n = math.hypot(vx, vy) or 1
        ex = fx_e - vx / n * 10
        ey = fy_e - vy / n * 10
        pygame.draw.line(fenetre, (120, 90, 55), (fx_e, fy_e), (ex, ey), 3)
        pygame.draw.circle(fenetre, (230, 230, 230), (int(fx_e), int(fy_e)), 3)

    for c in cochons:
        cx_e = c["x"] - camera_x
        cy_e = c["y"] - camera_y
        pygame.draw.rect(fenetre, (255, 180, 180), (cx_e, cy_e + 10, taille_cochon, taille_cochon - 10))
        pygame.draw.rect(fenetre, (255, 180, 180), (cx_e + 5, cy_e, taille_cochon - 10, 20))
        pygame.draw.circle(fenetre, (255, 120, 120), (int(cx_e + taille_cochon // 2), int(cy_e + 16)), 6)
        pygame.draw.circle(fenetre, (0, 0, 0), (int(cx_e + 10), int(cy_e + 8)), 3)
        pygame.draw.circle(fenetre, (0, 0, 0), (int(cx_e + 25), int(cy_e + 8)), 3)
        pygame.draw.rect(fenetre, (255, 140, 140), (cx_e + 3, cy_e + taille_cochon - 5, 8, 8))
        pygame.draw.rect(fenetre, (255, 140, 140), (cx_e + taille_cochon - 11, cy_e + taille_cochon - 5, 8, 8))

    if invincible == 0 or invincible % 10 < 5:
        # Le personnage remplit sa boîte de collision (1 bloc large, 2 blocs haut).
        jx = joueur_x - camera_x
        jy = joueur_y - camera_y
        dessiner_steve(fenetre, jx, jy, taille_joueur, hauteur_joueur,
                       equipement, phase_marche, epee, regard)

    if obscurite_finale > 0:
        voile = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
        voile.fill((0, 0, 10, obscurite_finale))
        # Chaque torche perce un halo lumineux dans le voile (éclairage réel).
        for (tx, ty) in torches_posees:
            lx = tx * TAILLE_BLOC + TAILLE_BLOC // 2 - camera_x
            ly_t = ty * TAILLE_BLOC + 12 - camera_y
            if -LIGHT_R <= lx <= LARGEUR + LIGHT_R and -LIGHT_R <= ly_t <= HAUTEUR + LIGHT_R:
                voile.blit(masque_lumiere, (lx - LIGHT_R, ly_t - LIGHT_R),
                           special_flags=pygame.BLEND_RGBA_SUB)
        fenetre.blit(voile, (0, 0))

    # --- Barre rapide : 8 cases personnalisables, case active surlignée ---
    for i in range(NB_HOTBAR):
        sx = HOT_X + i * SLOT
        type_bloc = hotbar[i]
        dessiner_slot(fenetre, sx, HOT_Y, SLOT, i == slot_actif)
        ix = sx + (SLOT - ICON) // 2
        iy = HOT_Y + (SLOT - ICON) // 2
        # On n'affiche l'icône que si on possède l'objet (ou en créatif).
        if type_bloc != 0 and (creatif or inventaire.get(type_bloc, 0) > 0):
            if type_bloc in TEXTURES:
                fenetre.blit(pygame.transform.scale(TEXTURES[type_bloc], (ICON, ICON)), (ix, iy))
            else:
                dessiner_item(fenetre, sx, HOT_Y, SLOT, type_bloc)
        texte_ombre(fenetre, str(i + 1), police_petite, sx + 4, HOT_Y + 3)
        if type_bloc != 0 and (creatif or inventaire.get(type_bloc, 0) > 0):
            qte = "oo" if creatif else str(inventaire.get(type_bloc, 0))
            largeur_q = police.size(qte)[0]
            texte_ombre(fenetre, qte, police, sx + SLOT - largeur_q - 5,
                        HOT_Y + SLOT - 24)

    # --- Minerais : rangée de cases en haut à gauche, même style ---
    min_slot = 46
    min_icon = min_slot - 14
    min_blocs = [7, 8, 9, 10, 11, 12]
    mx0, my0 = 12, 12
    for i, type_bloc in enumerate(min_blocs):
        sx = mx0 + i * min_slot
        dessiner_slot(fenetre, sx, my0, min_slot, False)
        ix = sx + (min_slot - min_icon) // 2
        iy = my0 + (min_slot - min_icon) // 2
        if type_bloc in TEXTURES:
            fenetre.blit(pygame.transform.scale(TEXTURES[type_bloc], (min_icon, min_icon)), (ix, iy))
        else:
            pygame.draw.rect(fenetre, PIERRE, (ix, iy, min_icon, min_icon))
            pygame.draw.rect(fenetre, couleur_bloc(type_bloc),
                             (ix + min_icon // 2 - 6, iy + min_icon // 2 - 6, 12, 12))
            pygame.draw.rect(fenetre, (0, 0, 0), (ix, iy, min_icon, min_icon), 1)
        if inventaire[type_bloc] > 0:
            qte = str(inventaire[type_bloc])
            largeur_q = police_petite.size(qte)[0]
            texte_ombre(fenetre, qte, police_petite, sx + min_slot - largeur_q - 4,
                        my0 + min_slot - 20)

    # Panneau d'état bas-gauche : fond contrasté pour une lisibilité constante.
    panneau_statut = pygame.Surface((300, 150), pygame.SRCALPHA)
    panneau_statut.fill((0, 0, 0, 180))
    fenetre.blit(panneau_statut, (5, HAUTEUR - 153))

    if epee:
        texte_epee = police.render("Épée : OK", True, (200, 200, 255))
        fenetre.blit(texte_epee, (12, HAUTEUR - 146))

    if arc:
        txt_arc = "Arc : OK   Flèches : " + str(inventaire.get(41, 0)) + "  (ESPACE)"
    else:
        txt_arc = "Flèches : " + str(inventaire.get(41, 0))
    fenetre.blit(police.render(txt_arc, True, (200, 230, 200)), (12, HAUTEUR - 118))

    texte_viande = police.render("Viande : " + str(inventaire.get(60, 0)) + " crue / " + str(inventaire.get(61, 0)) + " cuite (F)", True, (255, 170, 170))
    fenetre.blit(texte_viande, (12, HAUTEUR - 90))

    label_arm = police.render("Armure :", True, (170, 200, 255))
    fenetre.blit(label_arm, (12, HAUTEUR - 62))
    if armure_max > 0:
        bx, by, bw = 108, HAUTEUR - 60, 120
        pygame.draw.rect(fenetre, (70, 70, 80), (bx, by, bw, 14))
        pygame.draw.rect(fenetre, (120, 170, 230), (bx, by, int(bw * armure / armure_max), 14))
        pygame.draw.rect(fenetre, (0, 0, 0), (bx, by, bw, 14), 1)
        val = police_petite.render(str(armure) + "/" + str(armure_max), True, (255, 255, 255))
        fenetre.blit(val, (bx + bw + 8, by - 2))
    else:
        aucune = police_petite.render("aucune", True, (150, 150, 160))
        fenetre.blit(aucune, (108, HAUTEUR - 60))

    if not creatif:      # pas de barre de vie en créatif (immortel)
        label_vies = police.render("Vies :", True, (255, 90, 90))
        fenetre.blit(label_vies, (12, HAUTEUR - 32))
        for i in range(vies):
            pygame.draw.circle(fenetre, (230, 40, 40), (78 + i * 18, HAUTEUR - 22), 6)

    if not creatif:      # pas de barre de faim en créatif
        pygame.draw.rect(fenetre, (80, 80, 80), (LARGEUR - 210, HAUTEUR - 30, 200, 20))
        couleur_faim = (50, 200, 50) if faim > 50 else (255, 165, 0) if faim > 25 else (200, 0, 0)
        pygame.draw.rect(fenetre, couleur_faim, (LARGEUR - 210, HAUTEUR - 30, int(faim * 2), 20))
        pygame.draw.rect(fenetre, (0, 0, 0), (LARGEUR - 210, HAUTEUR - 30, 200, 20), 2)
        dessiner_texte(fenetre, "Faim", police, LARGEUR - 245, HAUTEUR - 28,
                       couleur_texte=(255, 255, 255))

    if est_nuit:
        dessiner_texte(fenetre, "Nuit", police, LARGEUR // 2, 12,
                       couleur_texte=(200, 200, 255), centre=True)
    else:
        dessiner_texte(fenetre, "Jour", police, LARGEUR // 2, 12,
                       couleur_texte=(255, 220, 0), centre=True)

    if inventaire_ouvert:
        fond_menu = pygame.Surface((INV_MENU_W, INV_MENU_H), pygame.SRCALPHA)
        fond_menu.fill((35, 35, 40, 240))
        fenetre.blit(fond_menu, (INV_MX, INV_MY))
        pygame.draw.rect(fenetre, (0, 0, 0), (INV_MX, INV_MY, INV_MENU_W, INV_MENU_H), 3)
        fenetre.blit(police_titre.render("Inventaire", True, (255, 255, 255)),
                     (INV_MX + 20, INV_MY + 18))

        # Emplacements d'armure (colonne de gauche)
        noms_slot = {"casque": "Casque", "plastron": "Plastron",
                     "jambieres": "Jambières", "bottes": "Bottes"}
        for i, slot in enumerate(ARMURE_SLOTS):
            ay = ARM_Y + i * (ARM_SLOT + 8)
            dessiner_slot(fenetre, ARM_X, ay, ARM_SLOT)
            if equipement[slot] != 0:
                dessiner_item(fenetre, ARM_X, ay, ARM_SLOT, equipement[slot])
            else:
                dessiner_texte(fenetre, noms_slot[slot][:4], police_petite,
                               ARM_X + 6, ay + ARM_SLOT // 2 - 8,
                               couleur_texte=(120, 120, 130),
                               couleur_fond=(0, 0, 0, 0), marge=0)

        # Aperçu du personnage (même dessin que le joueur en jeu, armure comprise)
        px, py = PREVIEW_X, PREVIEW_Y
        pygame.draw.rect(fenetre, (60, 60, 70), (px - 10, py - 5, 110, 210))
        dessiner_steve(fenetre, px + 15, py + 5, 70, 185, equipement)

        # Grille de fabrication 3x3 ("Fabrication")
        fenetre.blit(police.render("Fabrication", True, (230, 230, 230)),
                     (IGRID_X, IGRID_Y - 30))
        for r in range(3):
            for c in range(3):
                cx = IGRID_X + c * IGRID_SLOT
                cy = IGRID_Y + r * IGRID_SLOT
                dessiner_slot(fenetre, cx, cy, IGRID_SLOT)
                if grille_craft[r][c] != 0:
                    dessiner_item(fenetre, cx, cy, IGRID_SLOT, grille_craft[r][c])
        fx = IGRID_X + 3 * IGRID_SLOT + 8
        fyc = IGRID_OUT_Y + IGRID_SLOT // 2
        pygame.draw.rect(fenetre, (255, 255, 255), (fx, fyc - 4, 28, 8))
        pygame.draw.polygon(fenetre, (255, 255, 255),
                            [(fx + 28, fyc - 12), (fx + 28, fyc + 12), (fx + 44, fyc)])
        dessiner_slot(fenetre, IGRID_OUT_X, IGRID_OUT_Y, IGRID_SLOT)
        rec_p = trouver_recette(grille_craft)
        if rec_p:
            rt, rcp = rec_p["resultat"]
            dessiner_item(fenetre, IGRID_OUT_X, IGRID_OUT_Y, IGRID_SLOT, rt)
            if rcp > 1:
                texte_ombre(fenetre, str(rcp), police,
                            IGRID_OUT_X + IGRID_SLOT - 20, IGRID_OUT_Y + IGRID_SLOT - 24)
            dessiner_texte(fenetre, rec_p["nom"], police_petite,
                           IGRID_OUT_X - 10, IGRID_OUT_Y - 26)

        # Barre rapide (organisable) : 8 cases, la case active surlignée
        fenetre.blit(police.render("Barre rapide (glisse tes objets ici)", True, (230, 230, 230)),
                     (EHOT_X, EHOT_Y - 28))
        for i in range(NB_HOTBAR):
            hx = EHOT_X + i * SAC_SLOT
            dessiner_slot(fenetre, hx, EHOT_Y, SAC_SLOT, i == slot_actif)
            # Icône affichée seulement si on possède l'objet (ou en créatif).
            if hotbar[i] != 0 and (creatif or inventaire.get(hotbar[i], 0) > 0):
                dessiner_item(fenetre, hx, EHOT_Y, SAC_SLOT, hotbar[i])
                q = "oo" if creatif else str(inventaire.get(hotbar[i], 0))
                texte_ombre(fenetre, q, police_petite, hx + SAC_SLOT - 20, EHOT_Y + SAC_SLOT - 20)
            texte_ombre(fenetre, str(i + 1), police_petite, hx + 4, EHOT_Y + 3)

        # Sac : cases fixes rangeables (survie) ou palette de tout (créatif)
        fenetre.blit(police.render("Sac", True, (230, 230, 230)), (SAC_X, SAC_Y - 30))
        for i in range(SAC_ROWS * SAC_COLS):
            gx = SAC_X + (i % SAC_COLS) * SAC_SLOT
            gy = SAC_Y + (i // SAC_COLS) * SAC_SLOT
            dessiner_slot(fenetre, gx, gy, SAC_SLOT)
        if creatif:
            palette = [t for t in INV_TOUS if t not in hotbar and t not in equipement.values()]
            for idx, t in enumerate(palette):
                if idx >= SAC_ROWS * SAC_COLS:
                    break
                gx = SAC_X + (idx % SAC_COLS) * SAC_SLOT
                gy = SAC_Y + (idx // SAC_COLS) * SAC_SLOT
                dessiner_item(fenetre, gx, gy, SAC_SLOT, t)
                texte_ombre(fenetre, "oo", police_petite, gx + SAC_SLOT - 20, gy + SAC_SLOT - 20)
        else:
            for idx, t in enumerate(sac_slots):
                if t != 0 and inventaire.get(t, 0) > 0:
                    gx = SAC_X + (idx % SAC_COLS) * SAC_SLOT
                    gy = SAC_Y + (idx // SAC_COLS) * SAC_SLOT
                    dessiner_item(fenetre, gx, gy, SAC_SLOT, t)
                    texte_ombre(fenetre, str(inventaire.get(t, 0)), police_petite,
                                gx + SAC_SLOT - 20, gy + SAC_SLOT - 20)

        dessiner_texte(fenetre,
                       "Clique une case pour prendre l'objet ; reclique une autre case (sac, barre, armure, "
                       "craft) pour l'y poser ou l'échanger. (E ou I : fermer)",
                       police_petite, INV_MX + 20, INV_MY + INV_MENU_H - 28,
                       couleur_fond=(0, 0, 0, 0), marge=0)

        # Infobulle : nom de l'item/bloc survolé par la souris
        msx, msy = pygame.mouse.get_pos()
        survol = 0
        for i, slot in enumerate(ARMURE_SLOTS):
            ay = ARM_Y + i * (ARM_SLOT + 8)
            if ARM_X <= msx <= ARM_X + ARM_SLOT and ay <= msy <= ay + ARM_SLOT:
                survol = equipement[slot]
        for r in range(3):
            for c in range(3):
                gx = IGRID_X + c * IGRID_SLOT
                gy = IGRID_Y + r * IGRID_SLOT
                if gx <= msx <= gx + IGRID_SLOT and gy <= msy <= gy + IGRID_SLOT:
                    survol = grille_craft[r][c]
        rec_h = trouver_recette(grille_craft)
        if rec_h and IGRID_OUT_X <= msx <= IGRID_OUT_X + IGRID_SLOT \
                and IGRID_OUT_Y <= msy <= IGRID_OUT_Y + IGRID_SLOT:
            survol = rec_h["resultat"][0]
        for i in range(NB_HOTBAR):
            hx = EHOT_X + i * SAC_SLOT
            if hx <= msx <= hx + SAC_SLOT and EHOT_Y <= msy <= EHOT_Y + SAC_SLOT:
                survol = hotbar[i]
        if creatif:
            liste_h = [t for t in INV_TOUS if t not in hotbar and t not in equipement.values()]
        else:
            liste_h = sac_slots
        for idx, t in enumerate(liste_h):
            if t == 0:
                continue
            gx = SAC_X + (idx % SAC_COLS) * SAC_SLOT
            gy = SAC_Y + (idx // SAC_COLS) * SAC_SLOT
            if gx <= msx <= gx + SAC_SLOT and gy <= msy <= gy + SAC_SLOT:
                survol = t
        if item_en_main != 0:
            # L'objet pris en main SUIT le curseur jusqu'au prochain clic.
            dessiner_item(fenetre, msx - 24, msy - 24, 48, item_en_main)
        elif survol != 0 and nom_bloc(survol):
            dessiner_texte(fenetre, nom_bloc(survol), police, msx + 16, msy + 4,
                           couleur_texte=(255, 255, 255), couleur_fond=(0, 0, 0, 230))

    if coffre_ouvert:
        fond_menu = pygame.Surface((COF_MENU_W, COF_MENU_H), pygame.SRCALPHA)
        fond_menu.fill((35, 35, 40, 240))
        fenetre.blit(fond_menu, (COF_MX, COF_MY))
        pygame.draw.rect(fenetre, (0, 0, 0), (COF_MX, COF_MY, COF_MENU_W, COF_MENU_H), 3)
        fenetre.blit(police_titre.render("Coffre", True, (255, 255, 255)),
                     (COF_MX + 20, COF_MY + 16))

        # Rangée du sac (en haut)
        fenetre.blit(police.render("Ton sac", True, (230, 230, 230)), (CSAC_X, CSAC_Y - 28))
        for i in range(2 * COF_COLS):
            gx = CSAC_X + (i % COF_COLS) * COF_SLOT
            gy = CSAC_Y + (i // COF_COLS) * COF_SLOT
            dessiner_slot(fenetre, gx, gy, COF_SLOT)
        liste_sac = [t for t in INV_TOUS if inventaire.get(t, 0) > 0]
        for idx, t in enumerate(liste_sac):
            gx = CSAC_X + (idx % COF_COLS) * COF_SLOT
            gy = CSAC_Y + (idx // COF_COLS) * COF_SLOT
            dessiner_slot(fenetre, gx, gy, COF_SLOT)
            dessiner_item(fenetre, gx, gy, COF_SLOT, t)
            texte_ombre(fenetre, str(inventaire.get(t, 0)), police_petite,
                        gx + COF_SLOT - 20, gy + COF_SLOT - 20)

        # Rangée du coffre (en bas)
        fenetre.blit(police.render("Coffre (rangement)", True, (230, 230, 230)),
                     (CCOF_X, CCOF_Y - 28))
        for i in range(2 * COF_COLS):
            gx = CCOF_X + (i % COF_COLS) * COF_SLOT
            gy = CCOF_Y + (i // COF_COLS) * COF_SLOT
            dessiner_slot(fenetre, gx, gy, COF_SLOT)
        liste_cof = [t for t in INV_TOUS if coffre.get(t, 0) > 0]
        for idx, t in enumerate(liste_cof):
            gx = CCOF_X + (idx % COF_COLS) * COF_SLOT
            gy = CCOF_Y + (idx // COF_COLS) * COF_SLOT
            dessiner_slot(fenetre, gx, gy, COF_SLOT)
            dessiner_item(fenetre, gx, gy, COF_SLOT, t)
            texte_ombre(fenetre, str(coffre.get(t, 0)), police_petite,
                        gx + COF_SLOT - 20, gy + COF_SLOT - 20)

        dessiner_texte(fenetre,
                       "Clique un objet du sac pour le ranger, un objet du coffre pour le reprendre. (C : fermer)",
                       police_petite, COF_MX + 20, COF_MY + COF_MENU_H - 26,
                       couleur_fond=(0, 0, 0, 0), marge=0)

        # Infobulle : nom de l'objet survolé (sac en haut, coffre en bas)
        msx, msy = pygame.mouse.get_pos()
        survol = 0
        for idx, t in enumerate(liste_sac):
            gx = CSAC_X + (idx % COF_COLS) * COF_SLOT
            gy = CSAC_Y + (idx // COF_COLS) * COF_SLOT
            if gx <= msx <= gx + COF_SLOT and gy <= msy <= gy + COF_SLOT:
                survol = t
        for idx, t in enumerate(liste_cof):
            gx = CCOF_X + (idx % COF_COLS) * COF_SLOT
            gy = CCOF_Y + (idx // COF_COLS) * COF_SLOT
            if gx <= msx <= gx + COF_SLOT and gy <= msy <= gy + COF_SLOT:
                survol = t
        if survol != 0 and nom_bloc(survol):
            dessiner_texte(fenetre, nom_bloc(survol), police, msx + 16, msy + 4,
                           couleur_texte=(255, 255, 255), couleur_fond=(0, 0, 0, 230))

    if four_ouvert:
        fond_menu = pygame.Surface((FOUR_MENU_W, FOUR_MENU_H), pygame.SRCALPHA)
        fond_menu.fill((35, 35, 40, 240))
        fenetre.blit(fond_menu, (FOUR_MX, FOUR_MY))
        pygame.draw.rect(fenetre, (0, 0, 0), (FOUR_MX, FOUR_MY, FOUR_MENU_W, FOUR_MENU_H), 3)
        fenetre.blit(police_titre.render("Fourneau", True, (255, 255, 255)), (FOUR_MX + 20, FOUR_MY + 14))

        def _case_four(x, y, contenu, etiquette):
            dessiner_slot(fenetre, x, y, FOUR_SLOT)
            if contenu[1] > 0:
                dessiner_item(fenetre, x, y, FOUR_SLOT, contenu[0])
                texte_ombre(fenetre, str(contenu[1]), police_petite,
                            x + FOUR_SLOT - 20, y + FOUR_SLOT - 20)
            dessiner_texte(fenetre, etiquette, police_petite, x - 4, y - 24,
                           couleur_fond=(0, 0, 0, 0), marge=0)

        _case_four(FOUR_IN_X, FOUR_IN_Y, four_in, "À fondre")
        _case_four(FOUR_FUEL_X, FOUR_FUEL_Y, four_fuel, "Charbon")
        _case_four(FOUR_OUT_X, FOUR_OUT_Y, four_out, "Résultat")

        # Flamme sous la case combustible (allumée si ça fond)
        fx = FOUR_FUEL_X + FOUR_SLOT // 2
        allume = four_progres > 0
        pygame.draw.circle(fenetre, (255, 150, 30) if allume else (90, 80, 70), (fx, FOUR_FUEL_Y - 12), 8)
        if allume:
            pygame.draw.circle(fenetre, (255, 230, 120), (fx, FOUR_FUEL_Y - 13), 4)

        # Flèche de progression entre entrée et résultat
        ax = FOUR_IN_X + FOUR_SLOT + 30
        ay = FOUR_IN_Y + FOUR_SLOT + 20
        pygame.draw.rect(fenetre, (70, 70, 75), (ax, ay, 180, 16))
        pygame.draw.rect(fenetre, (120, 200, 90), (ax, ay, int(180 * four_progres / DUREE_FUSION), 16))
        pygame.draw.rect(fenetre, (0, 0, 0), (ax, ay, 180, 16), 1)
        pygame.draw.polygon(fenetre, (200, 200, 200),
                            [(ax + 185, ay - 6), (ax + 185, ay + 22), (ax + 205, ay + 8)])

        # Sac : clique un objet pour le déposer (charbon -> combustible, fondable -> entrée)
        fenetre.blit(police.render("Ton sac (clique pour déposer)", True, (230, 230, 230)),
                     (FSAC_X, FSAC_Y - 28))
        liste_sac = [t for t in INV_TOUS if inventaire.get(t, 0) > 0]
        for i in range(2 * FSAC_COLS):
            gx = FSAC_X + (i % FSAC_COLS) * FSAC_SLOT
            gy = FSAC_Y + (i // FSAC_COLS) * FSAC_SLOT
            dessiner_slot(fenetre, gx, gy, FSAC_SLOT)
        for idx, t in enumerate(liste_sac):
            if idx >= 2 * FSAC_COLS:
                break
            gx = FSAC_X + (idx % FSAC_COLS) * FSAC_SLOT
            gy = FSAC_Y + (idx // FSAC_COLS) * FSAC_SLOT
            dessiner_item(fenetre, gx, gy, FSAC_SLOT, t)
            texte_ombre(fenetre, str(inventaire.get(t, 0)), police_petite,
                        gx + FSAC_SLOT - 20, gy + FSAC_SLOT - 20)

        dessiner_texte(fenetre,
                       "Charbon -> combustible, minerai de fer / viande crue -> à fondre. "
                       "Clique une case du four pour reprendre. (G : fermer)",
                       police_petite, FOUR_MX + 20, FOUR_MY + FOUR_MENU_H - 26,
                       couleur_fond=(0, 0, 0, 0), marge=0)

    if message_timer > 0:
        dessiner_texte(fenetre, message_info, police, LARGEUR // 2, HAUTEUR - 130,
                       couleur_texte=(255, 200, 120), centre=True)
        message_timer -= 1

    if vies <= 0:
        texte_go = pygame.font.SysFont(None, 80).render("GAME OVER", True, (200, 0, 0))
        fenetre.blit(texte_go, (LARGEUR // 2 - 200, HAUTEUR // 2 - 40))
        pygame.display.flip()
        pygame.time.wait(3000)
        partie_perdue = True
        en_cours = False

    pygame.display.flip()
    horloge.tick(60)

# À la fermeture : on sauvegarde (sauf partie perdue -> on efface l'ancienne).
if partie_perdue:
    try:
        os.remove(SAVE_PATH)
    except OSError:
        pass
else:
    sauvegarder_partie()

pygame.quit()