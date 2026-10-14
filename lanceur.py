# -*- coding: utf-8 -*-
"""
Le Lanceur — un menu unique pour ouvrir tous tes bots d'un clic.

Clique sur un bouton : le bot s'ouvre dans sa propre fenetre.
Defilement : molette, fleches haut/bas, Page Haut/Bas, Debut/Fin.
Echap pour quitter.

LANCER :  python lanceur.py     (pip install pygame)
"""

import os
import sys
import math
import subprocess
import pygame

_HERE = os.path.dirname(os.path.abspath(__file__))

# (fichier, nom affiche)  -- seuls ceux qui existent seront montres
BOTS = [
    ("chatgpt_inverseur_maison.py", "Inverseur / Troll"),
    ("assistant_verite.py",         "Assistant Verite"),
    ("clash_bot.py",                "Clash Bot"),
    ("la_voyante.py",               "La Voyante"),
    ("aventure_heros.py",           "Aventure dont tu es le heros"),
    ("traducteur_secret.py",        "Traducteur Secret"),
    ("pokedex_maison.py",           "Pokedex maison"),
    ("devineur_20questions.py",     "Devineur (20 questions)"),
    ("chef_farfelu.py",             "Chef farfelu"),
    ("tamagotchi.py",               "Tamagotchi"),
    ("generateur_superheros.py",    "Generateur de super-heros"),
    ("tu_preferes.py",              "Tu preferes... ?"),
    ("generateur_excuses.py",       "Generateur d'excuses"),
    ("pierre_feuille_ciseaux.py",   "Pierre-Feuille-Ciseaux"),
    ("generateur_images.py",        "Generateur d'images IA"),
    ("parle_bizarre.py",            "Le bot qui parle bizarre"),
    ("juge_tribunal.py",            "Le Juge du tribunal"),
    ("boule_magique.py",            "La Boule Magique"),
    ("meteo_farfelue.py",           "La Meteo farfelue"),
    ("deux_verites_un_mensonge.py", "Deux verites, un mensonge"),
    ("escape_game.py",              "Escape Game texte"),
    ("action_ou_verite.py",         "Action ou Verite"),
    ("detecteur_mensonges.py",      "Detecteur de mensonges"),
    ("carte_au_tresor.py",          "La Carte au tresor"),
    ("bulletin_farfelu.py",         "Bulletin scolaire farfelu"),
    ("age_planetes.py",             "Ton age sur les planetes"),
    ("menu_cantine.py",             "Menu de cantine improbable"),
    ("theories_farfelues.py",       "Theories farfelues"),
    ("traducteur_parent_ado.py",    "Traducteur parent <-> ado"),
    ("ia_apprenante.py",            "*** L'IA APPRENANTE ***"),
    ("reseau_neurones.py",          "*** RESEAU DE NEURONES ***"),
]


def _available():
    return [(f, name) for (f, name) in BOTS if os.path.exists(os.path.join(_HERE, f))]


def launch(filename):
    path = os.path.join(_HERE, filename)
    try:
        subprocess.Popen([sys.executable, path], cwd=_HERE)
        return True
    except Exception:  # noqa: BLE001
        return False


# ---------- UI ----------
WIDTH, HEIGHT = 760, 620
FPS = 60
COL_BG      = (28, 30, 36)
COL_TITLE   = (255, 210, 90)
COL_MUTED   = (150, 156, 172)
COL_BTN     = (48, 54, 72)
COL_BTN_HOV = (74, 86, 122)
COL_BTN_BRD = (90, 98, 126)
COL_TEXT    = (236, 238, 246)
COL_OK      = (80, 205, 140)
COL_SCROLL  = (90, 98, 126)
PAD = 18
COLS = 3
BTN_H = 44
GAP = 10
TOP = 92
FOOTER = 30


def main():
    pygame.init()
    pygame.display.set_caption("Mes Bots - Lanceur")
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("segoeui,arial,sans", 16, bold=True)
    font_t = pygame.font.SysFont("segoeui,arial,sans", 26, bold=True)
    font_s = pygame.font.SysFont("segoeui,arial,sans", 14)

    bots = _available()
    msg = ""
    msg_timer = 0
    scroll = 0
    running = True

    while running:
        w, h = screen.get_size()
        mouse = pygame.mouse.get_pos()

        btn_w = (w - PAD * 2 - GAP * (COLS - 1)) / COLS
        rows = max(1, math.ceil(len(bots) / COLS))
        content_h = rows * (BTN_H + GAP)
        view_h = max(50, h - TOP - FOOTER)
        max_scroll = max(0, content_h - view_h)
        scroll = max(0, min(scroll, max_scroll))

        rects = []
        for i, (file, name) in enumerate(bots):
            col = i % COLS
            row = i // COLS
            x = PAD + col * (btn_w + GAP)
            y = TOP + row * (BTN_H + GAP) - scroll
            rects.append((pygame.Rect(int(x), int(y), int(btn_w), BTN_H), file, name))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.MOUSEWHEEL:
                scroll -= event.y * 45
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for rect, file, name in rects:
                    if rect.collidepoint(event.pos) and rect.bottom > TOP \
                            and rect.top < h - FOOTER:
                        ok = launch(file)
                        msg = (f"Lance : {name}" if ok
                               else f"Impossible de lancer {name}")
                        msg_timer = 180
                        break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_DOWN:
                    scroll += 45
                elif event.key == pygame.K_UP:
                    scroll -= 45
                elif event.key == pygame.K_PAGEDOWN:
                    scroll += view_h
                elif event.key == pygame.K_PAGEUP:
                    scroll -= view_h
                elif event.key == pygame.K_HOME:
                    scroll = 0
                elif event.key == pygame.K_END:
                    scroll = max_scroll
        scroll = max(0, min(scroll, max_scroll))

        # ---- dessin ----
        screen.fill(COL_BG)

        # boutons (clippes dans la zone visible)
        area = pygame.Rect(0, TOP, w, view_h)
        old_clip = screen.get_clip()
        screen.set_clip(area)
        for rect, file, name in rects:
            if rect.bottom < TOP or rect.top > TOP + view_h:
                continue
            hov = rect.collidepoint(mouse) and area.collidepoint(mouse)
            pygame.draw.rect(screen, COL_BTN_HOV if hov else COL_BTN, rect,
                             border_radius=10)
            pygame.draw.rect(screen, COL_BTN_BRD, rect, 1, border_radius=10)
            label = name
            while font.size(label)[0] > rect.width - 16 and len(label) > 1:
                label = label[:-1]
            img = font.render(label, True, COL_TEXT)
            screen.blit(img, (rect.centerx - img.get_width() // 2,
                              rect.centery - img.get_height() // 2))
        screen.set_clip(old_clip)

        # en-tete (par-dessus)
        pygame.draw.rect(screen, COL_BG, (0, 0, w, TOP))
        screen.blit(font_t.render("Mes Bots", True, COL_TITLE), (PAD, 18))
        screen.blit(font_s.render(
            f"{len(bots)} bots  -  clique pour ouvrir  -  molette / fleches pour "
            "defiler  -  Echap pour quitter", True, COL_MUTED), (PAD, 56))
        pygame.draw.line(screen, COL_BTN_BRD, (0, TOP - 4), (w, TOP - 4), 1)

        # barre de defilement
        if max_scroll > 0:
            th = max(30, view_h * view_h / content_h)
            ty = TOP + (view_h - th) * (scroll / max_scroll)
            pygame.draw.rect(screen, COL_SCROLL, (w - 7, ty, 4, th), border_radius=2)

        if msg_timer > 0:
            msg_timer -= 1
            screen.blit(font_s.render(msg, True, COL_OK), (PAD, h - 24))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
