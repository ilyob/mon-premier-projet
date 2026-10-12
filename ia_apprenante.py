# -*- coding: utf-8 -*-
"""
L'IA APPRENANTE — un chatbot qui apprend VRAIMENT, tout seul, hors-ligne.

Comment ca marche (vraie mecanique d'apprentissage) :
  1) MEMOIRE : il stocke des paires (ce que tu dis -> ce qu'il doit repondre).
  2) RECHERCHE : il compare ta phrase a tout ce qu'il connait (similarite des
     mots) et choisit la reponse la plus proche.
  3) MARKOV : il apprend aussi comment les mots s'enchainent, et sait inventer
     des phrases nouvelles a partir de tout ce qu'il a lu.
  4) RENFORCEMENT : dis « bien » ou « pas bien » -> il augmente ou baisse le
     score de sa derniere reponse. Les mauvaises finissent oubliees.
  5) MEMOIRE PERSISTANTE : son cerveau est sauve dans cerveau_ia.json.

Commandes utiles :
  - « apprends: bonjour = salut ! »   (apprentissage direct)
  - « bien » / « pas bien »           (recompense / punition)
  - « cerveau »                       (voir ce qu'il sait)
  - « oublie tout »                   (remise a zero, avec confirmation)

LANCER :  python ia_apprenante.py     (pip install pygame)
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
import pygame


def _strip_accents(s):
    return s.translate(str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc"))


_HERE = os.path.dirname(os.path.abspath(__file__))
CONV_FILE = os.path.join(_HERE, "ia_conversations.json")
BRAIN_FILE = os.path.join(_HERE, "cerveau_ia.json")

SYMBOLS = set("+-*/=^%<>")
STOP = {"le", "la", "les", "un", "une", "des", "de", "du", "a", "au", "aux",
        "et", "ou", "je", "tu", "il", "elle", "on", "nous", "vous", "ils",
        "est", "es", "que", "qui", "ce", "se", "en", "pour", "dans", "sur",
        "maintenant", "aussi", "alors", "puis", "ensuite", "moi", "toi",
        "parle", "raconte", "dis", "explique", "montre"}

# synonymes / mots familiers ramenes a un mot standard (les deux cotes sont
# normalises, donc « c'est quoi ton boulot » retrouve « travail »)
SYN = {"auto": "voiture", "bagnole": "voiture", "caisse": "voiture",
       "velo": "bicyclette", "boulot": "travail", "taf": "travail",
       "job": "travail", "fric": "argent", "thune": "argent",
       "pognon": "argent", "sous": "argent", "gamin": "enfant",
       "gosse": "enfant", "mome": "enfant", "toubib": "medecin",
       "docteur": "medecin", "bouquin": "livre", "fac": "universite",
       "prof": "professeur", "instit": "professeur", "pdg": "patron",
       "ceo": "patron", "dirigeant": "patron", "flotte": "eau",
       "clebs": "chien", "clebard": "chien", "matou": "chat",
       "ordi": "ordinateur", "photo": "image", "bahut": "lycee"}

# mots qui posent une question SUR un sujet (« capitale » de quoi ? -> du sujet courant)
PROP_WORDS = {"capitale", "capitales", "population", "habitants", "monnaie",
              "drapeau", "president", "presidente", "langue", "langues",
              "superficie", "surface", "taille", "continent", "hymne", "roi",
              "reine", "dirigeant", "religion", "climat", "fleuve", "montagne",
              "economie", "histoire", "gouvernement", "region", "regions",
              "nombre", "age", "couleur", "prix", "auteur", "date", "sens",
              "definition", "signification"}

# petits mots de conversation : ne doivent JAMAIS devenir un « sujet »
SMALLTALK = {"bonjour", "salut", "coucou", "bonsoir", "merci", "oui", "non",
             "ok", "ca", "va", "cerveau", "aide", "pardon", "desole", "lol",
             "mdr", "bien", "pas", "stats", "quoi", "neuf", "passe", "annule"}


def _norm(text):
    # on unifie les apostrophes (' ` ') et les tirets bizarres
    text = text.replace("’", "'").replace("ʼ", "'").replace("`", "'")
    text = text.replace("‑", "-").replace("–", "-")
    return re.sub(r"\s+", " ", _strip_accents(text.lower()).strip())


def _tok(text):
    # on garde les mots, les nombres ET les symboles (+ - * / = ...)
    words = re.findall(r"[a-z0-9]+|[+\-*/=^%<>]", _strip_accents(text.lower()))
    # on ne jette que les lettres seules (a, l, d...), pas les chiffres/symboles
    return [w for w in words if not (len(w) == 1 and w.isalpha())]


def _keywords(text):
    toks = [SYN.get(w, w) for w in _tok(text)]
    return [w for w in toks if w not in STOP] or toks


def _lev(a, b):
    """Distance d'edition (nombre de corrections pour passer de a a b)."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if abs(la - lb) > 2:
        return 3
    prev = list(range(lb + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[lb]


def _fuzzy_eq(a, b):
    """Deux mots « presque pareils » (tolere une faute de frappe). Jamais sur
    des chiffres ou des symboles : un calcul doit rester exact."""
    if a == b:
        return True
    if not (a.isalpha() and b.isalpha()):
        return False
    if len(a) < 3 or len(b) < 3 or a[0] != b[0]:
        return False
    return _lev(a, b) <= (1 if max(len(a), len(b)) <= 5 else 2)


def _extract_subject(text):
    """Le sujet principal d'un message (pour la memoire du contexte)."""
    low = _norm(text)
    m = re.search(r"\b(?:de |du |des |d')(?:l'|l |la |le |les )?([a-z]{3,})", low)
    if m:
        return m.group(1)
    kws = [w for w in _keywords(low) if w.isalpha() and len(w) >= 3]
    if "?" in text and kws:
        return kws[-1]
    # sujet « nu » : un nom seul (« espagne », « burkina faso ») devient le sujet,
    # mais pas un mot-propriete (« capitale ») ni un mot de conversation
    if 1 <= len(kws) <= 2 and not any(w in PROP_WORDS or w in SMALLTALK
                                      for w in kws):
        return " ".join(kws)
    return None


def _singulier(w):
    """Passe un mot au singulier approximatif (chevaux -> cheval, chats -> chat)."""
    if w.endswith("aux"):
        return w[:-3] + "al"
    if w.endswith("x") and len(w) > 3:
        return w[:-1]
    if w.endswith("s") and len(w) > 3 and not w.endswith("ois"):
        return w[:-1]
    return w


def _is_expr(text):
    """Vrai si c'est un calcul (que des chiffres/symboles, aucune lettre)."""
    t = _norm(text)
    return bool(t) and not re.search(r"[a-z]", t) and bool(re.search(r"[0-9]", t))


# ======================================================================
#  RECHERCHE EN LIGNE (Wikipedia) — quand elle ne comprend pas
# ======================================================================
def _wiki_get(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "IA-Apprenante/1.0 (projet educatif)"})
    with urllib.request.urlopen(req, timeout=7) as r:
        return json.loads(r.read().decode("utf-8"))


try:
    import sources_web            # toutes les sources (meteo, pays, wikis...)
except Exception:  # noqa: BLE001
    sources_web = None

try:
    import conjugaison            # moteur de conjugaison (des regles !)
except Exception:  # noqa: BLE001
    conjugaison = None

try:
    import regles                 # pluriels, feminins, nombres, romains... (des regles !)
except Exception:  # noqa: BLE001
    regles = None

try:
    import regles_plus            # maths avancees, dates, codes secrets... (des regles !)
except Exception:  # noqa: BLE001
    regles_plus = None

try:
    import generateur_images as gen_images   # generation d'images (Pollinations)
except Exception:  # noqa: BLE001
    gen_images = None

try:
    import raisonnement            # raisonnement en plusieurs etapes
except Exception:  # noqa: BLE001
    raisonnement = None


# dictionnaire de secours FR->EN (si l'API de traduction est injoignable)
IMG_DICT = {
    "un": "a", "une": "a", "le": "the", "la": "the", "les": "the", "des": "",
    "du": "", "de": "", "d": "", "l": "", "et": "and", "avec": "with", "dans": "in",
    "sur": "on", "sous": "under", "pour": "for", "au": "at", "aux": "at",
    "qui": "that", "mange": "eating", "mangeant": "eating", "vole": "flying",
    "volant": "flying", "court": "running", "dort": "sleeping", "danse": "dancing",
    "roi": "king", "reine": "queen", "prince": "prince", "princesse": "princess",
    "chat": "cat", "chien": "dog", "cheval": "horse", "oiseau": "bird",
    "poisson": "fish", "dragon": "dragon", "licorne": "unicorn",
    "monstre": "monster", "robot": "robot", "voiture": "car", "maison": "house",
    "chateau": "castle", "foret": "forest", "montagne": "mountain", "mer": "sea",
    "ocean": "ocean", "plage": "beach", "ville": "city", "arbre": "tree",
    "fleur": "flower", "soleil": "sun", "lune": "moon", "etoile": "star",
    "etoiles": "stars", "espace": "space", "fusee": "rocket",
    "vaisseau": "spaceship", "astronaute": "astronaut", "renard": "fox",
    "lion": "lion", "tigre": "tiger", "ours": "bear", "loup": "wolf",
    "elephant": "elephant", "souris": "mouse", "lapin": "rabbit",
    "papillon": "butterfly", "serpent": "snake", "requin": "shark",
    "baleine": "whale", "pizza": "pizza", "guerrier": "warrior",
    "chevalier": "knight", "sorciere": "witch", "magicien": "wizard",
    "fantome": "ghost", "zombie": "zombie", "epee": "sword", "couronne": "crown",
    "tresor": "treasure", "pirate": "pirate", "bateau": "boat", "avion": "plane",
    "train": "train", "ciel": "sky", "nuage": "cloud", "pluie": "rain",
    "neige": "snow", "feu": "fire", "glace": "ice", "eau": "water",
    "coucher": "sunset", "lever": "sunrise", "rouge": "red", "bleu": "blue",
    "vert": "green", "jaune": "yellow", "orange": "orange", "rose": "pink",
    "violet": "purple", "noir": "black", "blanc": "white", "gris": "gray",
    "marron": "brown", "dore": "golden", "or": "gold", "argent": "silver",
    "grand": "big", "petit": "small", "mignon": "cute", "effrayant": "scary",
    "geant": "giant", "magique": "magical", "medieval": "medieval",
    "ancien": "ancient", "moderne": "modern", "roux": "red", "mechant": "evil",
    "gentil": "kind", "rapide": "fast", "beau": "beautiful", "joli": "pretty",
    "colore": "colorful", "sombre": "dark", "brillant": "shiny",
    # animaux
    "araignee": "spider", "abeille": "bee", "fourmi": "ant",
    "coccinelle": "ladybug", "escargot": "snail", "grenouille": "frog",
    "tortue": "turtle", "canard": "duck", "poule": "hen", "coq": "rooster",
    "vache": "cow", "cochon": "pig", "mouton": "sheep", "chevre": "goat",
    "singe": "monkey", "girafe": "giraffe", "zebre": "zebra",
    "hippopotame": "hippo", "rhinoceros": "rhino", "crocodile": "crocodile",
    "dauphin": "dolphin", "pieuvre": "octopus", "crabe": "crab",
    "hibou": "owl", "aigle": "eagle", "perroquet": "parrot",
    "pingouin": "penguin", "manchot": "penguin", "chameau": "camel",
    "kangourou": "kangaroo", "panda": "panda", "koala": "koala",
    "herisson": "hedgehog", "ecureuil": "squirrel", "dinosaure": "dinosaur",
    "abeilles": "bees", "grenouilles": "frogs", "vautour": "vulture",
    "corbeau": "crow", "cygne": "swan", "flamant": "flamingo", "paon": "peacock",
    "scorpion": "scorpion", "meduse": "jellyfish", "etoile de mer": "starfish",
    # objets
    "gateau": "cake", "livre": "book", "ballon": "balloon", "velo": "bicycle",
    "moto": "motorcycle", "camion": "truck", "helicoptere": "helicopter",
    "ordinateur": "computer", "telephone": "phone", "guitare": "guitar",
    "piano": "piano", "horloge": "clock", "lampe": "lamp", "cle": "key",
    "parapluie": "umbrella", "cadeau": "gift", "bougie": "candle",
    "lunettes": "glasses", "chapeau": "hat", "montre": "watch",
    # nature / lieux
    "riviere": "river", "lac": "lake", "ile": "island", "volcan": "volcano",
    "desert": "desert", "jungle": "jungle", "grotte": "cave",
    "cascade": "waterfall", "champ": "field", "jardin": "garden",
    "pont": "bridge", "route": "road", "phare": "lighthouse",
    # personnages / fantastique
    "fee": "fairy", "elfe": "elf", "nain": "dwarf", "vampire": "vampire",
    "extraterrestre": "alien", "ninja": "ninja", "samourai": "samurai",
    "cowboy": "cowboy", "sirene": "mermaid", "ange": "angel", "diable": "devil",
    "squelette": "skeleton", "momie": "mummy", "geante": "giant",
    "fille": "girl", "garcon": "boy", "femme": "woman", "homme": "man",
    "bebe": "baby", "vieux": "old"}


def _google_traduire(texte, sl="fr", tl="en"):
    """Google Traduction via l'endpoint gratuit (sans cle), celui du site web."""
    url = "https://translate.googleapis.com/translate_a/single?" + \
        urllib.parse.urlencode({"client": "gtx", "sl": sl, "tl": tl,
                                "dt": "t", "q": texte})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.loads(r.read().decode("utf-8"))
    return "".join(seg[0] for seg in data[0] if seg and seg[0]).strip()


def _mymemory_traduire(texte, sl="fr", tl="en"):
    """Traduction de secours (MyMemory, gratuit sans cle)."""
    url = "https://api.mymemory.translated.net/get?" + urllib.parse.urlencode(
        {"q": texte, "langpair": f"{sl}|{tl}"})
    req = urllib.request.Request(url, headers={"User-Agent": "IA-App/1.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.loads(r.read().decode("utf-8"))
    trad = ((data.get("responseData") or {}).get("translatedText") or "").strip()
    if "WARNING" in trad.upper() or "INVALID" in trad.upper() or "QUOTA" in trad.upper():
        return ""
    return trad


# petits mots typiques de chaque langue -> pour deviner la langue
_MOTS_EN = {"the", "what", "is", "are", "how", "you", "your", "who", "where",
            "when", "why", "can", "does", "do", "tell", "draw", "give", "please",
            "hello", "hi", "thanks", "name", "old", "like", "make", "picture",
            "and", "of", "with", "my", "capital", "population"}
_MOTS_FR = {"le", "la", "les", "est", "quoi", "comment", "tu", "je", "une",
            "pour", "quel", "quelle", "dans", "qui", "merci", "bonjour", "salut",
            "dessine", "combien", "capitale", "ton", "mon", "avec", "des"}


def _langue_en(texte):
    """Devine si le message est en anglais (heuristique par mots typiques)."""
    mots = re.findall(r"[a-zà-ÿ']+", _strip_accents(texte.lower()))
    if not mots:
        return False
    en = sum(1 for w in mots if w in _MOTS_EN)
    fr = sum(1 for w in mots if w in _MOTS_FR)
    return en >= 2 and en > fr


def _traduire(texte, sl, tl):
    """Traduit dans un sens quelconque (Google puis MyMemory). Vide si echec."""
    texte = texte.strip()
    if not texte:
        return ""
    for service in (_google_traduire, _mymemory_traduire):
        try:
            trad = service(texte, sl, tl)
            if trad:
                return trad
        except Exception:  # noqa: BLE001
            pass
    return ""


def _traduire_en(texte):
    """Traduit le texte en anglais (meilleures images).
    1) Google Traduction (gratuit), 2) MyMemory, 3) dictionnaire hors-ligne."""
    texte = texte.strip()
    if not texte:
        return texte
    # 1) et 2) : services en ligne, Google d'abord
    for service in (_google_traduire, _mymemory_traduire):
        try:
            trad = service(texte)
            if trad:
                return trad
        except Exception:  # noqa: BLE001
            pass
    # 3) repli hors-ligne : un mot connu, sinon mot a mot
    coeur = [w for w in re.findall(r"[a-zà-ÿ]+", _strip_accents(texte.lower()))
             if w not in ("un", "une", "le", "la", "les", "des", "du", "de",
                          "d", "l")]
    if len(coeur) == 1 and IMG_DICT.get(coeur[0]):
        return IMG_DICT[coeur[0]]
    mots = re.findall(r"[a-zà-ÿ]+", _strip_accents(texte.lower()))
    return " ".join(IMG_DICT.get(w, w) for w in mots if IMG_DICT.get(w, w)) or texte


# styles d'image -> mots-cles anglais pour le modele
STYLE_MAP = [
    (r"pixel[- ]?art", "pixel art, 8-bit"),
    (r"aquarelle", "watercolor painting"),
    (r"peinture a l'huile|huile", "oil painting"),
    (r"(?:tres )?realiste|photo(?:realiste)?", "photorealistic, realistic, detailed"),
    (r"manga|anime", "anime manga style"),
    (r"dessin anime|cartoon|dessin-anime", "cartoon style"),
    (r"bande dessinee|\bbd\b|comics?", "comic book style"),
    (r"crayon|croquis|esquisse", "pencil sketch"),
    (r"3d|rendu 3d", "3d render, octane"),
    (r"minecraft", "minecraft blocky voxel style"),
    (r"lego", "lego bricks style"),
    (r"peinture", "painting, artistic"),
    (r"noir et blanc", "black and white"),
    (r"neon|cyberpunk", "cyberpunk, neon lights"),
    (r"fantasy|fantastique|medieval fantasy", "fantasy art, epic"),
]


def _extract_style(prompt):
    """Detecte un style (« en pixel art », « style aquarelle »...) dans la
    demande. Renvoie (sujet_sans_style, mots_cles_anglais_ou_None)."""
    low = _norm(prompt)
    for motif, tag in STYLE_MAP:
        if re.search(r"\b(?:en |style |facon |dans un style )?(?:" + motif + r")\b",
                     low):
            # on retire l'expression de style du sujet
            clean = re.sub(r"\b(?:en |style |facon |dans un style )?(?:" + motif
                           + r")\b", " ", low)
            clean = re.sub(r"\s+", " ", clean).strip(" ,")
            return (clean or prompt), tag
    return prompt, None


def _image_request(text):
    """Detecte « dessine-moi X », « genere une image de X »... Renvoie le sujet."""
    low = _norm(text)
    m = re.search(
        r"(?:dessine(?:-?moi)?|dessin de|peins(?:-?moi)?|"
        r"(?:genere|cree|fais|montre)(?:-?moi)?(?:\s+une)?\s+"
        r"(?:image|dessin|illustration|photo)(?:\s+de)?|"
        r"une? (?:image|illustration|photo|dessin) de|image de|photo de|"
        r"draw(?:\s+me)?|paint|generate\s+(?:an?\s+)?(?:image|picture|drawing)"
        r"(?:\s+of)?|(?:an?\s+)?(?:image|picture|drawing)\s+of)"
        r"\s*(?:d'|de |du |des |la |le |les |l'|un |une |an |a |the |of )?(.+)",
        low)
    if m:
        prompt = m.group(1).strip(" ?.!,")
        if len(prompt) >= 2:
            return prompt
    return None


def _video_request(text):
    """Detecte « fais une video/gif de X », « anime X ». Renvoie le sujet."""
    low = _norm(text)
    m = (re.search(r"(?:fais|cree|genere|fabrique)(?:-?moi)?\s+(?:une |un |moi )?"
                   r"(?:mini[- ])?(?:video|gif|animation|petite video)"
                   r"\s+(?:de |d'|du |des |un |une |qui |avec )?(.+)", low)
         or re.search(r"anime(?:-?moi)?\s+(.+)", low)
         or re.search(r"(?:video|gif|animation) de (.+)", low)
         or re.search(r"make(?:\s+me)?\s+(?:a |an )?(?:video|gif|animation)"
                      r"(?:\s+of)?\s+(.+)", low))
    if m:
        prompt = m.group(1).strip(" ?.!,")
        if len(prompt) >= 2:
            return prompt
    return None


def _assembler_gif(frames, out_dir):
    """Assemble des images en un .gif anime (via Pillow). Renvoie le chemin ou None."""
    try:
        from PIL import Image
    except Exception:  # noqa: BLE001
        return None
    try:
        imgs = [Image.open(p).convert("RGB") for p in frames]
        if not imgs:
            return None
        import time as _t
        gif_path = os.path.join(out_dir, f"video_{int(_t.time())}.gif")
        imgs[0].save(gif_path, save_all=True, append_images=imgs[1:],
                     duration=220, loop=0)
        return gif_path
    except Exception:  # noqa: BLE001
        return None


_MOIS_RE = (r"(?:janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|"
            r"octobre|novembre|decembre)")


def _reponse_ciblee(question, texte):
    """Si la question attend une DATE ou un NOMBRE, on l'extrait du texte web
    au lieu de recopier tout le resume. Renvoie une reponse courte ou None."""
    q = _strip_accents(question.lower())
    txt = _strip_accents(texte)

    # --- DATE / ANNEE ---
    if re.search(r"\bquand\b|quelle annee|en quelle annee|quel jour|"
                 r"date de (?:naissance|mort|creation|sortie)|\bne\b|\bnee\b", q):
        for motif in (r"\b\d{1,2}(?:er)?\s+" + _MOIS_RE + r"\s+\d{3,4}",
                      r"\b\d{1,2}(?:er)?\s+" + _MOIS_RE,
                      r"\ben\s+(\d{3,4})\b", r"\b\d{3,4}\b"):
            m = re.search(motif, txt)
            if m:
                return "D'apres ce que j'ai trouve : " + m.group(0).replace(
                    "en ", "").strip() + "."

    # --- NOMBRE / QUANTITE ---
    if re.search(r"\bcombien\b|population|nombre|hauteur|longueur|superficie|"
                 r"poids|distance|habitants|taille|surface|altitude|profondeur", q):
        # cas population / habitants : le nombre est colle a « habitants »
        if re.search(r"population|habitant", q):
            m = (re.search(r"(\d[\d  .  ]*\d|\d)\s*(millions?|milliards?)?"
                           r"\s*(?:d'|de )?habitants?", txt)
                 or re.search(r"population[^.]{0,60}?(\d[\d  .  ]*\d|\d)"
                              r"\s*(millions?|milliards?)?", txt))
            if m:
                num = re.sub(r"\s+", " ", m.group(1)).strip()
                mult = re.search(r"millions?|milliards?", m.group(0))
                suffixe = (" " + mult.group(0)) if mult else ""
                return (f"D'apres ce que j'ai trouve : {num}{suffixe} "
                        "d'habitants.")
        # autres cas : on coupe a partir du mot-cle (le nombre vient apres)
        cle = next((k for k in ("superficie", "surface", "hauteur", "altitude",
                                "longueur", "distance", "poids", "profondeur")
                    if k in q), None)
        if cle:
            pos = txt.find(cle)
            if pos != -1:
                txt = txt[pos:]
        best = None
        for mm in re.finditer(
                r"(\d[\d  . ]*\d|\d)\s*"
                r"(millions?|milliards?|km2|km²|km|metres?|m\b|kg|tonnes?|"
                r"habitants?|%)?", txt):
            val = re.sub(r"\s+", " ", mm.group(0)).strip()
            chiffres = re.sub(r"\D", "", mm.group(1))
            if mm.group(2) or len(chiffres) >= 3:      # a une unite ou est grand
                return "D'apres ce que j'ai trouve : " + val + "."
            if best is None:
                best = val
        if best:
            return "D'apres ce que j'ai trouve : " + best + "."
    return None


def _num_from_text(s):
    """« 47 millions d'habitants » -> 47000000 ; « 505 990 km2 » -> 505990."""
    if not s:
        return None
    low = _strip_accents(s.lower())
    m = re.search(r"\d[\d  . ]*\d|\d", low)
    if not m:
        return None
    val = float(re.sub(r"[^\d]", "", m.group(0)))
    if "milliard" in low:
        val *= 1e9
    elif "million" in low:
        val *= 1e6
    return val


ATTR_KW = {"grand": "superficie", "grande": "superficie", "gros": "superficie",
           "grosse": "superficie", "petit": "superficie", "petite": "superficie",
           "peuple": "population", "peuplee": "population", "haut": "hauteur",
           "haute": "hauteur", "long": "longueur", "longue": "longueur",
           "lourd": "poids", "lourde": "poids"}


def _comparaison(question):
    """« qui est le plus grand, la France ou l'Espagne ? » -> (e1, e2, attr, petit)."""
    low = _norm(question)
    ma = re.search(r"plus (grand|grande|gros|grosse|petit|petite|peuple|peuplee|"
                   r"haut|haute|long|longue|lourd|lourde)", low)
    if not ma:
        return None
    art = r"(?:l'|la |le |les |l |un |une )?"
    ent = r"([a-zà-ÿ]{3,}(?:[- ](?:de |du |d')?[a-zà-ÿ]{3,}){0,2})"
    me = re.search(art + ent + r"\s+(?:ou|et)\s+" + art + ent, low)
    if not me:
        return None
    e1, e2 = me.group(1).strip(), me.group(2).strip()
    petit = ma.group(1).startswith("petit")
    return e1, e2, ATTR_KW.get(ma.group(1), "superficie"), petit


def _valeur_attribut(entite, attr):
    """Va chercher sur le web la valeur numerique d'un attribut d'une entite."""
    mots = [w for w in _keywords(entite) if len(w) >= 3] or [entite]
    trouve = chercher_web(entite, mots)
    if not trouve:
        return None
    q = f"quelle est la {attr} de {entite}"
    cible = _reponse_ciblee(q, trouve[0])
    if not cible and sources_web is not None:
        try:
            lg = sources_web.wiki("wikipedia", entite, phrases=12)
            if lg:
                cible = _reponse_ciblee(q, lg[0])
        except Exception:  # noqa: BLE001
            pass
    if not cible:
        return None
    val = _num_from_text(cible)
    return (val, cible.replace("D'apres ce que j'ai trouve : ", "").strip(" .")) \
        if val is not None else None


def chercher_web(texte, mots):
    """Essaie toutes les sources. Renvoie (reponse, source) ou None."""
    if sources_web is not None:
        try:
            r = sources_web.chercher(texte, mots)
            if r:
                return r
        except Exception:  # noqa: BLE001
            pass
    w = wiki_answer(texte)          # repli : Wikipedia seul
    return (w, "Wikipedia") if w else None


def wiki_answer(text):
    """Repli simple : cherche sur Wikipedia FR. Renvoie un texte ou None."""
    mots = [w for w in _keywords(text) if len(w) >= 3]
    query = " ".join(mots) or text.strip("? ")
    if not query:
        return None
    try:
        surl = "https://fr.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
            {"action": "query", "list": "search", "srsearch": query,
             "format": "json", "srlimit": 4})
        hits = _wiki_get(surl).get("query", {}).get("search", [])
        for hit in hits:
            titre = hit["title"]
            try:
                s = _wiki_get("https://fr.wikipedia.org/api/rest_v1/page/summary/"
                              + urllib.parse.quote(titre))
            except Exception:  # noqa: BLE001
                continue
            if s.get("type") == "disambiguation":
                continue
            extrait = (s.get("extract") or "").strip()
            if len(extrait) < 25:
                continue
            phrases = re.split(r"(?<=[.!?])\s+", extrait)
            return " ".join(phrases[:2]).strip()
        return None
    except Exception:  # noqa: BLE001
        return None


# ======================================================================
#  LE MOTEUR DE RAISONNEMENT  (des REGLES, pas de la memoire)
# ======================================================================
BOOL_WORDS = {"vrai": "True", "faux": "False", "et": "and", "ou": "or",
              "non": "not", "(": "(", ")": ")"}
PRONOMS = {"je", "tu", "il", "elle", "on", "nous", "vous", "ce", "ca",
           "cela", "ils", "elles", "qui", "quoi"}

FACT_STMT = re.compile(
    r"^(?:un |une |le |la |les |l')?([a-z0-9-]{3,}?)s? (?:est|sont) "
    r"(?:un |une |des |le |la |les |l')?([a-z0-9-]{3,}?)s?$")
FACT_Q = re.compile(
    r"^(?:est-ce qu[e']\s*)?(?:un |une |le |la |les |l')?([a-z0-9-]{3,}?)s? "
    r"(?:est|sont)(?:-il|-elle|-ils|-elles)?\s*"
    r"(?:un |une |des |le |la |les |l')?([a-z0-9-]{3,}?)s?$")


def _try_bool(text):
    """« vrai et faux » -> faux.  Vraie table de verite."""
    toks = re.findall(r"[a-z]+|[()]", text)
    if not toks or not all(t in BOOL_WORDS for t in toks):
        return None
    if not any(t in ("vrai", "faux") for t in toks):
        return None
    try:
        v = eval(" ".join(BOOL_WORDS[t] for t in toks), {"__builtins__": {}}, {})
    except Exception:  # noqa: BLE001
        return None
    return "vrai" if v else "faux"


def _try_calc(text):
    """Calcule VRAIMENT n'importe quelle operation (meme jamais vue)."""
    t = text.replace(",", ".")
    t = re.sub(r"(?<=\d)\s*x\s*(?=\d)", "*", t)
    m = re.search(r"[0-9][0-9\.\s\+\-\*/\(\)%<>=]*[0-9]", t)
    if not m:
        return None
    expr = m.group(0).strip()
    if not re.search(r"[+\-*/%<>=]", expr):
        return None
    expr = re.sub(r"(?<![<>=!])=(?!=)", "==", expr)
    if not re.fullmatch(r"[0-9\.\s\+\-\*/\(\)%<>=]+", expr):
        return None
    try:
        v = eval(expr, {"__builtins__": {}}, {})   # noqa: S307 (expr filtree)
    except ZeroDivisionError:
        return "On ne peut pas diviser par zero !"
    except Exception:  # noqa: BLE001
        return None
    if isinstance(v, bool):
        return "vrai" if v else "faux"
    if isinstance(v, float):
        v = int(v) if v.is_integer() else round(v, 4)
    return str(v)


def _sim(a, b):
    """Similarite entre deux listes de mots (cosinus sur les ensembles)."""
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / math.sqrt(len(sa) * len(sb))


class Brain:
    """Le cerveau : memoire de paires + modele de langage (Markov)."""

    def __init__(self):
        self.pairs = []      # [{"q":..., "a":..., "score":int}]
        self.markov = {}     # mot -> {mot_suivant: compte}
        self.facts = {}      # "chat" -> ["animal"]  (pour raisonner)
        self.awaiting = None  # question en attente d'une reponse apprise
        self.pending = None  # action en attente (ex: "anniversaire" attend une date)
        self.last = None     # index de la derniere paire utilisee
        self.last_query = None  # derniere vraie question (pour les corrections)
        self.last_web_query = None  # dernier sujet cherche en ligne (« dis-m'en plus »)
        self.options = None     # sens possibles proposes a l'utilisateur
        self.context_subject = None  # sujet courant (pour comprendre « et sa capitale ? »)
        self.user = {"prenom": None, "age": None, "aime": [], "deteste": []}
        self.recent = []             # dernieres vraies questions (pour resumer la discussion)
        self.last_web_text = ""      # dernier long texte trouve (pour « resume ca »)
        self.relations = {"a": {}, "mange": {}, "vit": {}}  # relations riches
        self.compte = None           # total en cours d'un probleme (« il t'en reste... »)
        self.load()

    # ---------- RAISONNEMENT : faits et deduction ----------
    def learn_fact(self, a, b):
        self.facts.setdefault(a, [])
        if b not in self.facts[a]:
            self.facts[a].append(b)

    def deduce(self, a, b):
        """Cherche une chaine a -> ... -> b. Renvoie le chemin ou None.
        Tolere les accords : « vivante » = « vivant », « souris » = « souri »."""
        def stem(w):
            return re.sub(r"(?:es|s|e|x)$", "", w)

        # point de depart : gere « souris » capture en « souri »
        depart = a
        if a not in self.facts and (a + "s") in self.facts:
            depart = a + "s"
        cible_stem = stem(b)
        vus = {depart}
        file = [[depart]]
        while file:
            chemin = file.pop(0)
            for suivant in self.facts.get(chemin[-1], []):
                if suivant == b or stem(suivant) == cible_stem:
                    return chemin + [suivant]
                if suivant not in vus:
                    vus.add(suivant)
                    file.append(chemin + [suivant])
        return None

    def _ancetres(self, a):
        """Toutes les categories au-dessus de 'a' (chat -> mammifere, animal...)."""
        depart = a if a in self.facts else (a + "s" if (a + "s") in self.facts else a)
        vus, file = set(), [depart]
        while file:
            x = file.pop(0)
            for s in self.facts.get(x, []):
                if s not in vus:
                    vus.add(s)
                    file.append(s)
        return vus

    def _non(self, a, cible):
        """Peut-on dire NON avec certitude ? « un chat est-il un oiseau ? »."""
        anc = self._ancetres(a)
        if not anc:                          # on ne connait pas 'a' -> on se tait
            return None

        def stem(w):
            return re.sub(r"(?:es|s|e|x)$", "", w)

        cs = stem(cible)
        if cible in anc or cs in {stem(x) for x in anc}:
            return None                      # c'est un OUI, pas un NON
        cats = {c for vals in self.facts.values() for c in vals}
        connu = (cs in {stem(c) for c in cats}
                 or cible in self.facts or (cible + "s") in self.facts)
        if not connu:                        # cible inconnue -> on ne se prononce pas
            return None
        cle = a if a in self.facts else (a + "s" if (a + "s") in self.facts else a)
        proche = next(iter(self.facts.get(cle, [])), None)
        if proche:
            return f"Non. Un {a} est un {proche}, pas un {cible}."
        return f"Non, un {a} n'est pas un {cible}."

    # ---------- relations riches (a / mange / vit) ----------
    def _collecte_rel(self, rel, sujet):
        """Recupere les objets d'une relation, en heritant via la chaine est-un."""
        noeuds = [sujet, _singulier(sujet), sujet + "s"] + list(self._ancetres(sujet))
        res = []
        for n in noeuds:
            for o in self.relations.get(rel, {}).get(n, []):
                if o not in res:
                    res.append(o)
        return res

    def _relations(self, low):
        R = self.relations
        VERBE = {"a": "a", "mange": "mange", "vit": "vit"}

        # ---------- QUESTIONS ----------
        m = (re.search(r"que(?:ls)? mange(?:nt)? (?:un |une |le |la |les |l')?"
                       r"([a-zà-ÿ]{3,})", low)
             or re.search(r"qu'est-ce que (?:le |la |l'|un |une )?([a-zà-ÿ]{3,}) "
                          r"mange", low))
        if m:
            objs = self._collecte_rel("mange", _singulier(m.group(1)))
            if objs:
                return f"Un {_singulier(m.group(1))} mange : {', '.join(objs)}.", "logic"
        m = re.search(r"ou (?:vit|habite|vivent|habitent) (?:un |une |le |la |les |l')?"
                      r"([a-zà-ÿ]{3,})", low)
        if m:
            objs = self._collecte_rel("vit", _singulier(m.group(1)))
            if objs:
                return f"Un {_singulier(m.group(1))} vit dans : {', '.join(objs)}.", "logic"
        m = (re.search(r"que possede(?:nt)? (?:un |une |le |la |l')?([a-zà-ÿ]{3,})", low)
             or re.search(r"qu'est-ce qu'(?:un |une )?([a-zà-ÿ]{3,}) a\b", low)
             or re.search(r"(?:un |une |le |la )?([a-zà-ÿ]{3,}) a quoi", low))
        if m:
            objs = self._collecte_rel("a", _singulier(m.group(1)))
            if objs:
                return f"Un {_singulier(m.group(1))} a : {', '.join(objs)}.", "logic"

        # ---------- APPRENTISSAGE ----------
        def _obj(txt):
            txt = re.sub(r"^(?:des |de la |de l'|du |de |les |la |le |l'|l |d |"
                         r"un |une )+", "", txt.strip(" ?.!"))
            return txt.strip(" ?.!")

        m = re.search(r"\b([a-zà-ÿ]{3,}) (?:mange|mangent|se nourrit de|"
                      r"se nourrissent de) (.+)", low)
        if m and _singulier(m.group(1)) not in PRONOMS:
            s, o = _singulier(m.group(1)), _obj(m.group(2))
            if o:
                R["mange"].setdefault(s, [])
                if o not in R["mange"][s]:
                    R["mange"][s].append(o)
                self.save()
                return f"Compris : un {s} mange {o}. Je le retiens !", "learn"
        m = re.search(r"\b([a-zà-ÿ]{3,}) (?:vit|vivent|habite|habitent) "
                      r"(?:dans |en |au |sur |sous |a )?(.+)", low)
        if m and _singulier(m.group(1)) not in PRONOMS:
            s, o = _singulier(m.group(1)), _obj(m.group(2))
            if o:
                R["vit"].setdefault(s, [])
                if o not in R["vit"][s]:
                    R["vit"][s].append(o)
                self.save()
                return f"Compris : un {s} vit dans {o}. Je le retiens !", "learn"
        m = re.search(r"\b([a-zà-ÿ]{3,}) (?:a|ont|possede|possedent) "
                      r"((?:des |une |un |deux |trois |quatre |cinq |\d).+)", low)
        if m and _singulier(m.group(1)) not in PRONOMS:
            s, o = _singulier(m.group(1)), _obj(m.group(2))
            if o:
                R["a"].setdefault(s, [])
                if o not in R["a"][s]:
                    R["a"][s].append(o)
                self.save()
                return f"Compris : un {s} a {o}. Je le retiens !", "learn"
        return None

    def _calcul_mots(self, low):
        """Petits problemes en langage naturel AVEC memoire du total en cours :
        « j'ai 3 pommes, j'en achete 5 » -> 8, puis « j'en mange 2 » -> 6."""
        action = re.search(r"mange|perd|enleve|donne|retire|casse|vend|depense|"
                           r"achete|gagne|ajoute|recois|recolte|trouve|partage|"
                           r"divise|repartir|paquets? de|boites? de|groupes? de|"
                           r"\bfois\b|de plus|de moins", low)
        total = re.search(r"en tout|au total|ensemble|il (?:me |t')?reste", low)
        if not (action or total):
            return None
        # un vrai calcul ecrit en symboles (7*8, 12-4) -> laisse le moteur de calcul
        if re.search(r"\d\s*[+*/=]\s*\d|\d\s*-\s*\d", low):
            return None
        nums = [int(n) for n in re.findall(r"\d+", low)]

        # quelle operation ?
        if re.search(r"mange|perd|enleve|donne|retire|casse|vend|depense|"
                     r"de moins|reste", low):
            op = "-"
        elif re.search(r"partage|divise|repartir|chacun|entre \d", low):
            op = "/"
        elif re.search(r"\bfois\b|paquets? de|boites? de|groupes? de|chaque", low):
            op = "*"
        else:
            op = "+"

        signe = {"-": "-", "+": "+", "*": "x", "/": "/"}[op]

        def calc(a, b):
            return {"-": a - b, "+": a + b, "*": a * b,
                    "/": (a // b if b else a)}[op]

        # --- SUITE : un seul nombre + un total memorise ---
        if len(nums) == 1 and self.compte is not None \
                and re.search(r"j'en|m'en|il (?:m')?en|en (?:plus|moins)|encore", low):
            avant, n = self.compte, nums[0]
            r = calc(avant, n)
            self.compte = r
            if op == "-":
                return (f"Tu en avais {avant}, tu en enleves {n} : il t'en reste "
                        f"{r}.  ({avant} - {n} = {r})"), "logic"
            return (f"Tu en avais {avant}, et {signe}{n} : ca fait {r}.  "
                    f"({avant} {signe} {n} = {r})"), "logic"

        # --- PROBLEME COMPLET : au moins 2 nombres ---
        if len(nums) >= 2:
            r = nums[0]
            for x in nums[1:]:
                r = calc(r, x)
            self.compte = r
            detail = f" {signe} ".join(map(str, nums))
            mot = "Il t'en reste" if op == "-" else \
                ("Chacun en a" if op == "/" else "Ca fait")
            return f"{mot} {r}.  ({detail} = {r})", "logic"

        # --- suite (« j'en mange 2 ») mais aucun total connu : on demande ---
        if len(nums) == 1 and re.search(r"j'en|m'en|il (?:m')?en", low):
            return ("Tu en avais combien au depart ? Dis-le moi et je calcule "
                    "le reste."), "info"
        return None

    def raisonner(self, texte):
        """Applique des REGLES (conjugaison, calcul, logique, deduction)."""
        low = _norm(texte)

        if conjugaison is not None:
            conj = conjugaison.repondre(texte)
            if conj:
                return conj + "\n(j'ai applique les regles de conjugaison)", "logic"

        calc_mots = self._calcul_mots(low)
        if calc_mots:
            return calc_mots

        if raisonnement is not None:
            multi = raisonnement.repondre(texte)
            if multi:
                return multi + "\n(j'ai raisonne en plusieurs etapes)", "logic"

        if regles is not None:
            reg = regles.repondre(texte)
            if reg:
                return reg + "\n(j'ai applique une regle)", "logic"

        if regles_plus is not None:
            reg = regles_plus.repondre(texte)
            if reg:
                return reg + "\n(j'ai applique une regle)", "logic"

        b = _try_bool(low)
        if b:
            return f"{b}  (j'ai applique la logique)", "logic"

        c = _try_calc(low)
        if c is not None:
            return f"{c}  (je viens de le calculer)", "logic"

        q = low.rstrip("? ").strip()
        if "est-ce" in low or "?" in texte or "-il" in low or "-elle" in low:
            m = FACT_Q.match(q)
            if m:
                a, cible = m.group(1), m.group(2)
                if a not in PRONOMS and cible not in PRONOMS:
                    chemin = self.deduce(a, cible)
                    if chemin:
                        etapes = " et ".join(
                            f"{chemin[i]} est un {chemin[i + 1]}"
                            for i in range(len(chemin) - 1))
                        return f"Oui ! {etapes}. Donc c'est vrai.", "logic"
                    non = self._non(a, cible)
                    if non:
                        return non + "  (j'ai raisonne avec ce que je sais).", "logic"
                    if a in self.facts:
                        return (f"Je ne peux pas le deduire : je ne connais pas "
                                f"de lien entre « {a} » et « {cible} ».", "logic")
                    return None

        m = FACT_STMT.match(q)
        if m:
            a, cat = m.group(1), m.group(2)
            if a not in PRONOMS and cat not in PRONOMS and a != cat:
                self.learn_fact(a, cat)
                self.save()
                return (f"Compris : un {a} est un {cat}. Je le retiens pour "
                        "raisonner !"), "learn"
        return None

    # ---------- persistance ----------
    def load(self):
        try:
            with open(BRAIN_FILE, encoding="utf-8") as f:
                data = json.load(f)
            self.pairs = data.get("pairs", [])
            self.markov = data.get("markov", {})
            self.facts = data.get("facts", {})
            saved = data.get("user")
            if isinstance(saved, dict):
                self.user.update(saved)
            rel = data.get("relations")
            if isinstance(rel, dict):
                for k in ("a", "mange", "vit"):
                    if isinstance(rel.get(k), dict):
                        self.relations[k] = rel[k]
        except Exception:  # noqa: BLE001
            self.pairs, self.markov, self.facts = [], {}, {}

    def save(self):
        try:
            with open(BRAIN_FILE, "w", encoding="utf-8") as f:
                json.dump({"pairs": self.pairs, "markov": self.markov,
                           "facts": self.facts, "user": self.user,
                           "relations": self.relations},
                          f, ensure_ascii=False, indent=1)
        except Exception:  # noqa: BLE001
            pass

    # ---------- apprentissage ----------
    def learn(self, q, a):
        nq = _norm(q)
        # un CALCUL ne se compare qu'a l'identique : « 9+4 » n'est pas « 4+9 »
        if _is_expr(q):
            for p in self.pairs:
                if _norm(p["q"]) == nq:
                    p["a"] = a
                    p["score"] = max(1, p.get("score", 1))
                    return
            self.pairs.append({"q": q.strip(), "a": a.strip(), "score": 1})
            return
        qk = _keywords(q)
        for p in self.pairs:
            if _is_expr(p["q"]):
                continue
            if _sim(qk, _keywords(p["q"])) > 0.92:
                p["a"] = a
                p["score"] = max(1, p.get("score", 1))
                return
        self.pairs.append({"q": q.strip(), "a": a.strip(), "score": 1})

    def markov_train(self, sentence):
        words = _tok(sentence)
        if len(words) < 2:
            return
        prev = "__START__"
        for w in words:
            self.markov.setdefault(prev, {})
            self.markov[prev][w] = self.markov[prev].get(w, 0) + 1
            prev = w
        self.markov.setdefault(prev, {})
        self.markov[prev]["__END__"] = self.markov[prev].get("__END__", 0) + 1

    def markov_gen(self, max_words=14):
        if "__START__" not in self.markov:
            return None

        def pick(d):
            tot = sum(d.values())
            r = random.uniform(0, tot)
            acc = 0
            for k, v in d.items():
                acc += v
                if acc >= r:
                    return k
            return list(d)[-1]

        w = pick(self.markov["__START__"])
        out = [w]
        for _ in range(max_words):
            nxt = self.markov.get(w)
            if not nxt:
                break
            w = pick(nxt)
            if w == "__END__":
                break
            out.append(w)
        return " ".join(out) if len(out) > 2 else None

    # ---------- resume ----------
    def _resumer(self, low):
        """« resume ca » (dernier texte web) ou « de quoi on a parle ? »."""
        # resume de la conversation
        if re.search(r"resume (?:la |notre )?(?:conversation|discussion)|"
                     r"de quoi (?:on|nous) a(?:vons)? parle|on a parle de quoi|"
                     r"quels sujets|de quoi (?:on|nous) parle", low):
            ignore = {"resume", "conversation", "quand", "conjugue", "combien",
                      "comment", "pourquoi", "dessine", "quel", "quelle"}
            sujets = []
            for msg in self.recent:
                s = _extract_subject(msg)
                if s:
                    s = s.split()[-1]          # on garde le mot principal
                if s and s not in sujets and s not in ignore and len(s) >= 3:
                    sujets.append(s)
            if sujets:
                return ("On a parle de : " + ", ".join(sujets[-8:]) + "."), "info"
            return "On vient tout juste de commencer a discuter !", "info"
        # resume du dernier texte trouve
        if re.fullmatch(r"resume|resume[- ]moi(?: ca| cela| tout ca)?|en (?:plus )?"
                        r"court|plus court|en bref|en resume|abrege|resume ca", low):
            if self.last_web_text:
                phrases = re.split(r"(?<=[.!?])\s", self.last_web_text.strip())
                court = phrases[0].strip()
                if court and court[-1] not in ".!?":
                    court += "."
                return "En resume : " + court, "info"
            return ("Il n'y a rien a resumer pour l'instant : pose-moi d'abord "
                    "une question !"), "info"
        return None

    # ---------- memoire sur l'utilisateur ----------
    def _user_memory(self, low):
        """Retient (et restitue) le prenom, l'age et les gouts de l'utilisateur."""
        u = self.user
        # --- apprentissage ---
        m = re.search(r"(?:je m'?appelle|mon (?:nom|prenom) (?:est|c'?est)|"
                      r"appelle[ -]moi)\s+([a-zà-ÿ]{2,})", low)
        if m:
            u["prenom"] = m.group(1).capitalize()
            self.save()
            return f"Enchante {u['prenom']} ! Je m'en souviendrai.", "learn"
        m = re.search(r"j'?ai\s+(\d{1,3})\s+ans?\b", low)
        if m:
            u["age"] = int(m.group(1))
            self.save()
            return f"C'est note : tu as {u['age']} ans.", "learn"
        m = re.search(r"\bje (?:deteste|n'?aime pas)\s+(.+)", low)
        if m:
            g = m.group(1).strip(" ?.!")
            if g and g not in u["deteste"]:
                u["deteste"].append(g)
                self.save()
            return f"D'accord, tu n'aimes pas {g}. Je le retiens.", "learn"
        m = re.search(r"\bj'?(?:aime|adore)\s+(?:bien\s+|beaucoup\s+)?(.+)", low)
        if m:
            g = m.group(1).strip(" ?.!")
            if g and g not in u["aime"]:
                u["aime"].append(g)
                self.save()
            return f"Cool, tu aimes {g} ! Je m'en souviens.", "learn"
        # --- restitution ---
        if re.search(r"comment je m'?appelle|quel est mon (?:nom|prenom)|"
                     r"(?:tu (?:te souviens|connais).*)?mon prenom|"
                     r"tu sais comment je m'?appelle", low):
            return (f"Tu t'appelles {u['prenom']} !" if u["prenom"]
                    else "Je ne connais pas encore ton prenom. Dis-moi "
                    "« je m'appelle ... » !"), "info"
        if re.search(r"quel age j'?ai|mon age|tu sais mon age", low):
            return (f"Tu as {u['age']} ans." if u["age"]
                    else "Tu ne m'as pas encore dit ton age !"), "info"
        if re.search(r"qu'?est-ce que j'?aime|ce que j'?aime|mes gouts|"
                     r"tu sais ce que j'?aime", low):
            if u["aime"] or u["deteste"]:
                out = []
                if u["aime"]:
                    out.append("tu aimes " + ", ".join(u["aime"]))
                if u["deteste"]:
                    out.append("tu n'aimes pas " + ", ".join(u["deteste"]))
                return ("Voici ce que je sais : " + " ; et ".join(out) + ".", "info")
            return "Tu ne m'as encore rien dit sur tes gouts !", "info"
        if re.search(r"que sais-tu sur moi|parle[ -]moi de moi|qui suis[ -]je|"
                     r"quest ce que tu sais sur moi", low):
            bouts = []
            if u["prenom"]:
                bouts.append(f"tu t'appelles {u['prenom']}")
            if u["age"]:
                bouts.append(f"tu as {u['age']} ans")
            if u["aime"]:
                bouts.append("tu aimes " + ", ".join(u["aime"]))
            if u["deteste"]:
                bouts.append("tu n'aimes pas " + ", ".join(u["deteste"]))
            if bouts:
                return ("Ce que je sais sur toi : " + " ; ".join(bouts) + ".",
                        "info")
            return ("Je ne sais encore rien sur toi. Dis-moi ton prenom, ton "
                    "age, ce que tu aimes !"), "info"
        return None

    # ---------- apprentissage automatique de faits ----------
    def _apprendre_fait(self, texte_web):
        """Depuis « Le chat est un mammifere... », elle apprend chat -> mammifere
        pour pouvoir RAISONNER ensuite (deduction). Renvoie (sujet, categorie)."""
        phrase = re.split(r"(?<=[.!?])\s", texte_web.strip())[0]
        phrase = re.sub(r"\([^)]*\)", " ", phrase)      # enleve les parentheses
        low = _norm(phrase)
        m = re.search(r"^\s*(?:le |la |les |l'|un |une )?([a-z]{3,})\s+"
                      r"(?:est|sont|etait|etaient)\s+"
                      r"(?:un|une|des|le|la|les|l')\s+([a-z]{3,})", low)
        if not m:
            return None
        sujet, cat = m.group(1), m.group(2)
        if sujet == cat:
            return None
        self.facts.setdefault(sujet, [])
        if cat not in self.facts[sujet]:
            self.facts[sujet].append(cat)
            self.save()
        return sujet, cat

    # ---------- comparaison de deux choses ----------
    def _comparer(self, question):
        parsed = _comparaison(question)
        if not parsed:
            return None
        e1, e2, attr, petit = parsed
        v1, v2 = _valeur_attribut(e1, attr), _valeur_attribut(e2, attr)
        if not v1 or not v2:
            return None
        (n1, d1), (n2, d2) = v1, v2
        if (n1 > n2) != petit:
            gagnant, gd, autre, ad = e1, d1, e2, d2
        else:
            gagnant, gd, autre, ad = e2, d2, e1, d1
        mot = "petit" if petit else "grand"
        return (f"D'apres leur {attr}, le plus {mot} est {gagnant.capitalize()} "
                f"({gd}), contre {ad} pour {autre.capitalize()}."), "web"

    # ---------- detection de contradiction ----------
    def _contradiction(self, q, a):
        """Cherche une reponse DEJA apprise pour la meme question mais differente.
        Renvoie l'ancienne reponse, ou None."""
        nq = _norm(q)
        qk = _keywords(q)
        for p in self.pairs:
            if _is_expr(p["q"]):
                continue
            meme_q = (_norm(p["q"]) == nq
                      or (len(qk) >= 2 and _sim(qk, _keywords(p["q"])) >= 0.9))
            if meme_q and _norm(p["a"]) != _norm(a):
                return p["a"]
        return None

    # ---------- « est-ce une vraie question a chercher ? » ----------
    def _semble_factuel(self, low, t):
        """Vrai si le message ressemble a une VRAIE question / un sujet a chercher.
        Faux si c'est du bavardage (« je vais bien et toi ? ») -> pas de Wikipedia !"""
        if re.search(r"\b(qui|quoi|quel|quelle|quels|quand|ou|comment|pourquoi|"
                     r"combien|capitale|population|superficie|definition|signifie|"
                     r"c'est quoi|qu'est-ce|est-ce)\b", low):
            return True
        # un nom propre (majuscule pas en tout debut de phrase) = un sujet
        if re.search(r"\S\s+[A-Z][a-zà-ÿ]{2,}", t):
            return True
        # mots de bavardage / d'etat -> pas factuel
        BAVARD = {"vais", "vas", "va", "bien", "mal", "toi", "moi", "suis", "es",
                  "est", "ca", "content", "contente", "triste", "fatigue",
                  "fatiguee", "merci", "salut", "bonjour", "coucou", "bonsoir",
                  "cool", "super", "genial", "oui", "non", "ok", "voila",
                  "alors", "aussi", "ennuie", "faim", "soif", "adore", "aime",
                  "deteste", "heureux", "sympa", "trop", "vraiment", "peux",
                  "veux", "sais", "pense", "crois", "dis", "raconte",
                  "rien", "tres", "grand", "chose", "special", "neuf", "pareil",
                  "tranquille", "habitude", "bof", "normal", "fou", "particulier"}
        kws = [w for w in _keywords(low) if w.isalpha() and len(w) >= 3]
        contenu = [w for w in kws if w not in BAVARD]
        # un sujet « nu » de 1-3 mots de contenu (« napoleon », « les dinosaures »)
        if contenu and len(contenu) <= 3 and not any(w in BAVARD for w in kws):
            return True
        return False

    # ---------- memoire du contexte ----------
    def _apply_context(self, t):
        """Comprend les suites : « et sa capitale ? » apres avoir parle d'un pays.
        Renvoie la question reecrite (ou le texte d'origine si pas d'anaphore)."""
        if not self.context_subject:
            return t
        low = _norm(t)
        poss = re.search(r"\b(sa|son|ses|leur|leurs)\b", low)
        suite = re.match(r"(et|puis|aussi|alors)\b", low)
        kws = _keywords(low)
        content = [w for w in kws if w.isalpha() and len(w) >= 3]
        # tous les mots sont des « proprietes » (capitale, population...) -> anaphore
        all_prop = bool(content) and all(w in PROP_WORDS for w in content)
        # anaphore = possessif, OU relance « et... », OU une propriete seule
        if poss or (suite and len(kws) <= 3) or all_prop:
            nettoye = re.sub(r"\b(et|puis|alors|aussi|sa|son|ses|leur|leurs|"
                             r"la|le|les|du|des|de|quelle|quel|quels|est|sont|"
                             r"ce|cette|ton|ta|tes)\b|\b[ldc]'", " ", low)
            mots = [w for w in _keywords(nettoye)
                    if w.isalpha() and len(w) >= 3
                    and w not in self.context_subject.split()]
            if mots:
                return " ".join(mots) + " " + self.context_subject
        return t

    # ---------- recherche ----------
    def find(self, text):
        # 1) correspondance EXACTE d'abord (indispensable pour « 2*2 », « ok »...)
        n = _norm(text)
        for i, p in enumerate(self.pairs):
            if p.get("score", 1) > -2 and _norm(p["q"]) == n:
                return p["a"], i, 1.0
        # 1bis) un calcul, meme cache dans une phrase (« combien font 3*3 ? »)
        #       et on essaie aussi l'ordre inverse (9+4 = 4+9)
        m = re.search(r"\d+\s*[-+*/x]\s*\d+", n)
        if m:
            expr = m.group(0).replace(" ", "").replace("x", "*")
            cands = [expr]
            c = re.fullmatch(r"(\d+)([+*])(\d+)", expr)
            if c:                      # + et * peuvent s'inverser
                cands.append(f"{c.group(3)}{c.group(2)}{c.group(1)}")
            for i, p in enumerate(self.pairs):
                pq = _norm(p["q"]).replace(" ", "").replace("x", "*")
                if p.get("score", 1) > -2 and pq in cands:
                    return p["a"], i, 1.0

        # 2) sinon, recherche par similarite des mots
        #    (mais un CALCUL exige une correspondance exacte : 1*2 n'est pas 2*2)
        if _is_expr(text):
            return None
        qset = set(_keywords(text))
        if not qset:
            return None

        # IDF : les mots RARES comptent plus que les mots frequents
        df, psets = {}, []
        for p in self.pairs:
            if _is_expr(p["q"]) or p.get("score", 1) <= -2:
                psets.append(None)
                continue
            ks = set(_keywords(p["q"]))
            psets.append(ks)
            for w in ks:
                df[w] = df.get(w, 0) + 1
        ndoc = max(1, sum(1 for k in psets if k))

        def idf(w):
            return math.log(1 + ndoc / (1 + df.get(w, 0)))

        q_norm = math.sqrt(sum(idf(w) ** 2 for w in qset)) or 1.0
        q_tot = sum(idf(w) for w in qset) or 1.0    # poids total de la question
        best, best_s, best_i = None, 0.0, None
        for i, p in enumerate(self.pairs):
            pset = psets[i]
            if not pset:
                continue
            # intersection FLOUE (tolere les fautes) ponderee par l'IDF
            poids, alpha_match, used = 0.0, False, set()
            for qw in qset:
                pw = qw if qw in pset else next(
                    (x for x in pset if x not in used and _fuzzy_eq(qw, x)), None)
                if pw is not None:
                    used.add(pw)
                    poids += idf(qw)
                    if qw.isalpha() and len(qw) >= 2:
                        alpha_match = True
            # une ressemblance uniquement par symboles (* + -) ne compte pas
            if poids == 0 or not alpha_match:
                continue
            # COUVERTURE : au moins la moitie du poids de la question doit matcher
            # (evite que « capitale » seul fasse matcher deux pays differents)
            if poids < 0.5 * q_tot:
                continue
            p_norm = math.sqrt(sum(idf(w) ** 2 for w in pset)) or 1.0
            s = poids / (q_norm * p_norm)            # cosinus pondere par l'IDF
            s += 0.02 * min(5, p.get("score", 1))    # bonus reputation
            mn = min(len(qset), len(pset))
            seuil = 0.30 if mn >= 4 else 0.40 if mn == 3 else 0.55
            if s > best_s and s >= seuil:
                best, best_s, best_i = p, s, i
        if best:
            return best["a"], best_i, best_s
        return None

    # ---------- feedback ----------
    def reward(self, plus):
        if self.last is None or not (0 <= self.last < len(self.pairs)):
            return "Je ne sais pas de quelle reponse tu parles..."
        p = self.pairs[self.last]
        p["score"] = p.get("score", 1) + (1 if plus else -1)
        self.save()
        if plus:
            return f"Merci ! Je retiens que « {p['a']} » est une bonne reponse."
        if p["score"] <= -2:
            self.pairs.pop(self.last)
            self.last = None
            self.save()
            return "Compris, j'oublie cette reponse pour de bon."
        return "D'accord, je m'en souviendrai. Dis-moi ce que j'aurais du repondre !"

    # ---------- infos ----------
    def stats(self):
        mots = set()
        liens = 0
        for k, d in self.markov.items():
            if k != "__START__":
                mots.add(k)
            liens += len(d)
            mots.update(x for x in d if not x.startswith("__"))
        niveau = min(10, 1 + len(self.pairs) // 5)
        lines = ["=== MON CERVEAU ===",
                 f"Reponses apprises : {len(self.pairs)}",
                 f"Mots connus       : {len(mots)}",
                 f"Liens de langage  : {liens}",
                 f"Niveau            : {niveau}/10"]
        if self.pairs:
            lines.append("")
            lines.append("Quelques trucs que je sais :")
            for p in sorted(self.pairs, key=lambda x: -x.get("score", 1))[:5]:
                lines.append(f"  • « {p['q'][:28]} » -> « {p['a'][:32]} »")
        else:
            lines.append("")
            lines.append("Je ne sais encore rien... apprends-moi des choses !")
        return "\n".join(lines)

    # ---------- coeur ----------
    def respond(self, text):
        t = text.strip()
        low = _norm(t)          # minuscules, sans accents, apostrophes unifiees

        if low in ("cerveau", "stats", "memoire", "que sais-tu"):
            self.awaiting = None          # l'utilisateur passe a autre chose
            return self.stats(), "info"

        if low in ("passe", "annule", "laisse tomber", "tant pis", "rien"):
            if self.awaiting or self.pending:
                self.awaiting = self.pending = None
                return "D'accord, on oublie cette question !", "info"

        # --- resolution d'une contradiction en attente ---
        if isinstance(self.pending, tuple) and self.pending[0] == "contradiction":
            _, q, ancienne, nouvelle = self.pending
            if re.match(r"^\s*(2|le nouveau|nouveau|la nouvelle)\b", low) \
                    or "nouveau" in low or "nouvelle" in low:
                self.pending = None
                self.learn(q, nouvelle)
                self.save()
                return f"Ok, je garde la nouvelle : « {nouvelle} ».", "learn"
            if re.match(r"^\s*(1|l'ancien|ancien|la premiere|garde)\b", low) \
                    or "ancien" in low:
                self.pending = None
                return f"Tres bien, je garde l'ancienne : « {ancienne} ».", "learn"
            return ("Dis-moi juste : 1 pour garder l'ancienne reponse, "
                    "2 pour la nouvelle."), "ask"

        # --- une action attend une date (ex: anniversaire) ---
        if self.pending == "anniversaire":
            d = regles_plus._parse_date(t) if regles_plus else None
            if d:
                self.pending = None
                return regles_plus.jours_avant_anniversaire(d), "logic"
            return ("Je n'ai pas compris la date. Ecris-la comme ca : "
                    "25/08/2013  (ou « passe » pour laisser tomber)."), "ask"

        if low in ("oublie tout", "efface tout", "reset"):
            self.pairs, self.markov = [], {}
            self.awaiting = self.last = self.context_subject = None
            self.user = {"prenom": None, "age": None, "aime": [], "deteste": []}
            self.save()
            return "J'ai tout oublie... on repart de zero !", "info"

        if low in ("oublie les tables", "oublie les calculs", "efface les tables",
                   "oublie les tables inutiles"):
            avant = len(self.pairs)
            self.pairs = [p for p in self.pairs if not _is_expr(p["q"])]
            enleve = avant - len(self.pairs)
            self.awaiting = None
            self.save()
            return (f"J'ai oublie {enleve} calculs appris par coeur : je les "
                    "recalcule tout seul maintenant ! Essaie « 7*8 »."), "info"

        if re.fullmatch(r"(bien|super|bravo|parfait|exact|oui c'est ca|top)", low):
            self.awaiting = None
            return self.reward(True), "info"
        if re.fullmatch(r"(pas bien|nul|faux|mauvais|non c'est faux|n'importe quoi)", low):
            self.awaiting = None
            return self.reward(False), "info"

        m = re.match(r"apprends?\s*:\s*(.+?)\s*=\s*(.+)", t, re.I)
        if m:
            self.awaiting = None          # apprentissage direct : on annule l'attente
            q, a = m.group(1).strip(), m.group(2).strip()
            ancienne = self._contradiction(q, a)
            if ancienne:                  # contradiction : on demande quoi garder
                self.pending = ("contradiction", q, ancienne, a)
                return (f"Attends, c'est different de ce que je savais ! Avant, "
                        f"« {q} » = « {ancienne} », et la tu dis « {a} ». "
                        "Lequel je garde ? (tape 1 pour l'ancien, 2 pour le "
                        "nouveau)"), "ask"
            self.learn(q, a)
            self.markov_train(q)
            self.markov_train(a)
            self.save()
            return f"Appris ! Si tu dis « {q} », je repondrai « {a} ».", "learn"

        if self.awaiting:
            q = self.awaiting
            self.awaiting = None
            self.learn(q, t)
            self.markov_train(t)
            self.save()
            return (f"Merci ! J'ai appris quoi repondre a « {q[:40]} ». "
                    "Reessaie pour voir !"), "learn"

        # --- L'UTILISATEUR CHOISIT UN DES SENS PROPOSES ---
        if self.options:
            opts = self.options
            choix = None
            mnum = re.match(r"^\s*([1-9])\b", low)
            if mnum and 1 <= int(mnum.group(1)) <= len(opts):
                choix = opts[int(mnum.group(1)) - 1]
            else:
                for o in opts:
                    ol = _norm(o)
                    if ol in low or (len(low) > 3 and low in ol):
                        choix = o
                        break
            if choix:
                self.options = None
                r = sources_web.page(choix) if sources_web else None
                if r:
                    texte_web, source = r
                    rep = f"{texte_web}\n(source : {source})"
                    self.learn(f"{self.last_query} {choix}", rep)
                    self.save()
                    return rep, "web"
                return f"Je n'ai pas reussi a ouvrir « {choix} ».", "info"
            self.options = None      # ce n'etait pas un choix : on continue

        # --- RELANCE : « dis-m'en plus », « raconte encore »... ---
        if re.match(r"^(dis[ -]?m'?en plus|(raconte|dis|explique|parle)[ -]?"
                    r"(moi |m'?en )?(plus|encore|davantage|en plus)|encore|"
                    r"continue|et apres|et ensuite|d'autres (details|infos)|"
                    r"plus de (details|infos)|developpe)\b", low) \
                and self.last_web_query and sources_web is not None:
            q = " ".join(w for w in _keywords(self.last_web_query) if len(w) >= 3)
            cands = sources_web.candidats(q) if q else []
            if cands:
                r = sources_web.page(cands[0], phrases=5)
                if r:
                    texte_web, source = r
                    return f"{texte_web}\n(source : {source})", "web"
            return "Je n'ai pas plus d'infos la-dessus, desole.", "info"

        # --- CORRECTION : « non, l'animal » -> on relance en precisant ---
        mc = re.match(r"^(?:non|nan|pas ca|pas celui|pas celle|je parle|"
                      r"plutot|je veux dire)\b[ ,'!]*(.+)$", low)
        if mc and self.last_query and len(mc.group(1).strip()) > 2:
            precision = mc.group(1).strip()
            requete = f"{self.last_query} {precision}"
            trouve = chercher_web(requete,
                                  [w for w in _keywords(requete) if len(w) >= 3])
            if trouve:
                texte_web, source = trouve
                rep = f"{texte_web}\n(source : {source})"
                self.learn(requete, rep)
                self.save()
                self.last_query = requete
                return rep, "web"
            return ("Je n'ai rien trouve avec cette precision. "
                    "Tu peux reformuler ?"), "info"

        # --- RESUME : « resume ca », « de quoi on a parle ? » ---
        res = self._resumer(low)
        if res:
            return res

        # --- MEMOIRE SUR L'UTILISATEUR : prenom, age, gouts ---
        um = self._user_memory(low)
        if um:
            return um

        # --- RELATIONS RICHES : « le chat mange des souris », « que mange... » ---
        rel = self._relations(low)
        if rel:
            return rel

        # --- SON NOM : AMIE (acronyme) ---
        if re.search(r"comment (?:tu )?t['\s]?appelles?|"
                     r"comment t['\s]?appelles?-tu|"
                     r"quel est ton (?:nom|prenom)|c'?est quoi ton (?:nom|prenom)|"
                     r"ton (?:nom|prenom) c'?est quoi|tu t['\s]?appelles? comment|"
                     r"tu as un nom|c'?est quoi ton petit nom|ton petit nom", low):
            return ("Je m'appelle AMIE ! C'est un acronyme : j'Apprends, je "
                    "Memorise, j'Imagine et j'Explique. Et ca veut dire « une "
                    "amie » !"), "info"

        # --- BAVARDAGE « et toi ? » (avant tout, pour ne jamais chercher le web) ---
        if re.search(r"\bet toi\b|\bet vous\b", low) and not self._semble_factuel(low, t):
            return ("Moi je vais tres bien, merci de demander ! "
                    "Et toi, quoi de neuf ?"), "info"

        # --- reponses banales (« rien », « bof »...) : surtout PAS de recherche web ---
        if low.strip(" .!?") in (
                "rien", "rien de special", "rien de neuf", "rien de particulier",
                "rien de bien", "pas grand chose", "pas grand-chose", "bof",
                "comme d'habitude", "tranquille", "comme ci comme ca", "ras",
                "rien du tout", "rien de fou"):
            return ("Ah, journee tranquille alors ! Si tu veux, pose-moi une "
                    "question, un calcul, ou demande-moi de dessiner quelque chose."), "info"

        # --- MEMOIRE DU CONTEXTE : « et sa capitale ? » -> sujet precedent ---
        resolu = self._apply_context(t)
        if resolu != t:
            t = resolu                          # relance resolue : on garde le sujet
        else:
            subj = _extract_subject(t)
            if subj:
                self.context_subject = subj     # nouveau sujet courant

        self.last_query = t          # on retient la derniere vraie question
        self.recent.append(t)        # pour resumer la discussion
        self.recent = self.recent[-20:]

        # --- ANNIVERSAIRE : elle demande la date, puis calcule ---
        if regles_plus is not None and re.search(r"anniversaire|annif", low) \
                and "joyeux" not in low:
            d = regles_plus._parse_date(t)
            if d:
                return regles_plus.jours_avant_anniversaire(d), "logic"
            self.pending = "anniversaire"
            return ("Quand es-tu ne(e) ? Donne-moi ta date de naissance "
                    "(ex: 25/08/2013) et je calcule !"), "ask"

        # --- RAISONNEMENT : des regles, pas de la memoire ---
        pense = self.raisonner(t)
        if pense:
            self.last = None
            return pense

        self.markov_train(t)
        found = self.find(t)
        if found:
            answer, idx, score = found
            self.last = idx
            self.save()
            # auto-verification : on annonce si on n'est pas sur
            if score < 0.5:
                return ("Je ne suis pas totalement sure, mais je dirais :\n"
                        + answer + "\n(dis « pas bien » si je me trompe)"), "guess"
            if score < 0.72:
                return "Je pense que : " + answer, "answer"
            return answer, "answer"

        # --- elle ne comprend pas : elle cherche en ligne, et RETIENT ---
        mots = [w for w in _keywords(t) if len(w) >= 3]
        if mots and not _is_expr(t):
            # question de COMPARAISON (« le plus grand, la France ou l'Espagne ? »)
            comp = self._comparer(t)
            if comp:
                return comp

            # BAVARDAGE : on ne va PAS sur Wikipedia pour « je vais bien et toi ? »
            if not self._semble_factuel(low, t):
                if re.search(r"\bet toi\b|\bet vous\b", low):
                    return ("Moi je vais tres bien, merci de demander ! "
                            "Et toi, quoi de neuf ?"), "info"
                self.awaiting = t
                self.save()
                return ("Hmm, je ne sais pas trop quoi repondre a ca. Qu'est-ce "
                        "que j'aurais du dire ? (ecris-le, je le retiens — ou "
                        "tape « passe »)"), "ask"

            # le mot a-t-il plusieurs sens ? -> elle demande de preciser
            if sources_web is not None and len(mots) <= 2:
                for cand in sources_web.candidats(" ".join(mots), limit=2):
                    if sources_web.est_homonymie(cand):
                        sens = sources_web.homonymes(cand, limit=4)
                        if len(sens) >= 2:
                            self.options = sens
                            liste = "\n".join(f"   {i + 1}) {s}"
                                              for i, s in enumerate(sens))
                            return (f"« {t} » peut vouloir dire plusieurs choses. "
                                    f"Tu parles de :\n{liste}\n"
                                    "(reponds par le numero, ou precise)"), "ask"
                        break

            trouve = chercher_web(t, mots)
            if trouve:
                texte_web, source = trouve
                # 1) reponse CIBLEE (date / nombre) si la question en attend une
                cible = _reponse_ciblee(t, texte_web)
                if not cible and sources_web is not None and re.search(
                        r"\bquand\b|\bcombien\b|quelle annee|population|"
                        r"superficie|hauteur|habitants", low):
                    try:                    # extrait plus long pour trouver la valeur
                        lg = sources_web.wiki("wikipedia", " ".join(mots), phrases=12)
                        if lg:
                            cible = _reponse_ciblee(t, lg[0])
                    except Exception:  # noqa: BLE001
                        pass
                # 2) apprentissage AUTOMATIQUE d'un fait (« chat -> mammifere »)
                appris = self._apprendre_fait(texte_web)

                if cible:
                    reponse = f"{cible}\n({texte_web}\nsource : {source})"
                else:
                    reponse = f"{texte_web}\n(source : {source})"
                self.learn(t, reponse)    # ce qu'elle trouve, elle l'apprend !
                self.markov_train(texte_web)
                self.last_web_query = t    # pour « dis-m'en plus »
                self.last_web_text = texte_web    # pour « resume ca »
                self.save()
                if appris:
                    reponse += (f"\n[j'ai aussi appris qu'un {appris[0]} est un "
                                f"{appris[1]} — je peux raisonner avec ca !]")
                return reponse, "web"

        # elle ne sait pas : on est HONNETE (plus de charabia invente au hasard)
        self.awaiting = t
        self.save()
        return ("Je ne sais pas repondre a ca, et je prefere te le dire "
                "plutot que d'inventer. Qu'est-ce que j'aurais du dire ? "
                "(ecris-le, je le retiendrai — ou tape « passe »)"), "ask"


BRAIN = Brain()

# ======================================================================
#  UI PYGAME
# ======================================================================
WIDTH, HEIGHT = 1000, 700
FPS = 60
COL_BG        = (24, 26, 34)
COL_SIDEBAR   = (19, 21, 28)
COL_ITEM      = (40, 44, 58)
COL_ITEM_ON   = (56, 62, 82)
COL_TRASH     = (205, 128, 128)
COL_DANGER    = (200, 90, 88)
COL_ASSISTANT = (40, 44, 58)
COL_USER      = (58, 66, 92)
COL_TEXT      = (234, 238, 246)
COL_MUTED     = (148, 156, 176)
COL_LEARN     = (150, 230, 170)
COL_INFO      = (150, 200, 255)
COL_LOGIC     = (255, 210, 120)
COL_WEB       = (140, 235, 235)
COL_INPUT_BG  = (46, 52, 68)
COL_INPUT_BRD = (82, 90, 112)
COL_ACCENT    = (110, 180, 255)
COL_SCROLL    = (82, 90, 112)
PAD = 16
SIDEBAR_W = 250
IMG_DISP = 280          # taille d'affichage des images generees (px)

GREETING = ("Bonjour ! Je m'appelle AMIE : j'Apprends, je Memorise, j'Imagine "
            "et j'Explique. Au debut je ne sais presque rien : quand je ne "
            "comprends pas, je te demande quoi repondre, et je le retiens.\n\n"
            "Tu peux aussi m'apprendre direct : « apprends: bonjour = salut ! »\n"
            "Dis « bien » ou « pas bien » pour noter mes reponses, et « cerveau » "
            "pour voir ce que je sais.")


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
        pygame.display.set_caption("AMIE — mon IA qui apprend")
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
        self._edit_rects = []          # boutons « Modifier » sur les messages de l'utilisateur
        self._img_cache = {}           # images generees deja chargees (path -> surface)
        self._gif_cache = {}           # frames de gif deja chargees (pour animer)
        self._gif_paused = {}          # gif en pause (cle = tuple des frames)
        self._gif_frozen = {}          # frame affichee au moment de la pause
        self._img_action_rects = []    # (rect, action, idx) : agrandir / refaire / pause
        self._zoom = None              # image affichee en grand (path) ou None
        self._think_label = "Je reflechis"
        self._new_btn = None
        self._save_btn = None
        self._send_btn = None
        self._pending_delete = None
        self._confirm_yes = None
        self._confirm_no = None
        pygame.key.set_repeat(300, 30)

    # ---------- conversations ----------
    def _new_chat(self):
        n = len(getattr(self, "chats", [])) + 1
        return {"name": f"Discussion {n}",
                "messages": [("assistant", GREETING, "info")]}

    def _load_conversations(self):
        try:
            with open(CONV_FILE, encoding="utf-8") as f:
                data = json.load(f)
            chats = []
            for ch in data.get("chats", []):
                msgs = [tuple(m) for m in ch.get("messages", [])]
                if not msgs:
                    msgs = [("assistant", GREETING, "info")]
                chats.append({"name": ch.get("name", "Discussion"), "messages": msgs})
            if chats:
                return chats
        except Exception:  # noqa: BLE001
            pass
        return [{"name": "Discussion 1",
                 "messages": [("assistant", GREETING, "info")]}]

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
        BRAIN.save()

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
        if not text or self.thinking:
            return
        chat = self.chats[self.active]
        chat["messages"].append(("user", text, "user"))
        self.input_text = ""
        self.scroll = 0
        self.thinking = True
        self._result = None
        video = _video_request(text) if gen_images is not None else None
        prompt = _image_request(text) if gen_images is not None else None
        if video:
            self._think_label = "Je cree la video (ca prend un peu de temps)"
            threading.Thread(target=self._gif_worker, args=(chat, video),
                             daemon=True).start()
        elif prompt:
            self._think_label = "Je dessine"
            threading.Thread(target=self._img_worker, args=(chat, prompt),
                             daemon=True).start()
        else:
            self._think_label = "Je reflechis"
            threading.Thread(target=self._worker, args=(chat, text),
                             daemon=True).start()

    def _gif_worker(self, chat, fr_prompt, n_frames=6):
        """Genere plusieurs images de la scene et les assemble en GIF anime."""
        en_full = self._build_image_prompt(fr_prompt)
        frames = []
        err = None
        for _ in range(n_frames):
            path, err = gen_images.download_image(en_full)
            if path:
                frames.append(path)
        if len(frames) < 2:
            message = ("assistant", "Je n'ai pas reussi a creer la video ("
                       + (err or "erreur") + "). Reessaie !", "info")
        else:
            gif = _assembler_gif(frames, gen_images.IMG_DIR)
            # message : [3] = liste des frames (pour animer), [4] = chemin .gif
            message = ("assistant", fr_prompt, "gif", frames, gif or "")
        with self._lock:
            self._result = (chat, message)

    def _worker(self, chat, text):
        # si l'utilisateur ecrit en anglais : on traduit -> FR, on raisonne,
        # puis on retraduit la reponse -> EN (l'IA « repond dans ta langue »)
        anglais = _langue_en(text)
        requete = text
        if anglais:
            fr = _traduire(text, "en", "fr")
            if fr:
                requete = fr
        msg, kind = BRAIN.respond(requete)
        if anglais and kind != "image":
            en = _traduire(msg, "fr", "en")
            if en:
                msg = en
        with self._lock:
            self._result = (chat, ("assistant", msg, kind))

    @staticmethod
    def _build_image_prompt(fr_prompt):
        """Construit le prompt anglais final : sujet traduit + style + qualite."""
        clean, style = _extract_style(fr_prompt)
        en = _traduire_en(clean)
        parts = [en]
        if style:
            parts.append(style)
        base = ", ".join(parts)
        if len(en.split()) <= 3:      # sujet court -> on etoffe pour la coherence
            base += (", single well-centered subject, detailed illustration, "
                     "sharp colors, high quality, simple background")
        return base

    def _img_worker(self, chat, fr_prompt):
        en_full = self._build_image_prompt(fr_prompt)
        self._img_download(chat, fr_prompt, en_full)

    def _img_rerun(self, chat, caption, en_full):
        """Refaire : on regenere avec le MEME prompt (nouvelle graine aleatoire)."""
        if en_full is None:
            en_full = self._build_image_prompt(caption)
        self._img_download(chat, caption, en_full)

    def start_rerun(self, idx):
        if self.thinking:
            return
        msgs = self.messages
        if not (0 <= idx < len(msgs)) or msgs[idx][2] != "image":
            return
        caption = msgs[idx][1]
        en_full = msgs[idx][4] if len(msgs[idx]) > 4 else None
        self.thinking = True
        self._result = None
        self._think_label = "Je redessine"
        self.scroll = 0
        chat = self.chats[self.active]
        threading.Thread(target=self._img_rerun, args=(chat, caption, en_full),
                         daemon=True).start()

    def _img_download(self, chat, caption, en_full):
        path, err = gen_images.download_image(en_full)
        if path:
            message = ("assistant", caption, "image", path, en_full)
        else:
            message = ("assistant", "Je n'ai pas reussi a creer l'image ("
                       + (err or "erreur") + "). Reessaie !", "info")
        with self._lock:
            self._result = (chat, message)

    def edit_message(self, idx):
        """Reprend la conversation a partir d'un de tes messages : on remet ton
        texte dans la barre, et on efface tout ce qui suivait."""
        if self.thinking:
            return
        msgs = self.messages
        if not (0 <= idx < len(msgs)) or msgs[idx][0] != "user":
            return
        self.input_text = msgs[idx][1]
        del self.chats[self.active]["messages"][idx:]
        BRAIN.awaiting = BRAIN.pending = BRAIN.options = None
        self.scroll = 0

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
                chat, message = res
                chat["messages"].append(tuple(message))
                self._result = None
                self.thinking = False
                self.scroll = 0

    def _get_image(self, path):
        """Charge (et met en cache) une image generee, mise a l'echelle."""
        if path in self._img_cache:
            return self._img_cache[path]
        surf = None
        try:
            img = pygame.image.load(path)
            iw, ih = img.get_size()
            sc = IMG_DISP / max(iw, ih)
            surf = pygame.transform.smoothscale(img, (int(iw * sc), int(ih * sc)))
        except Exception:  # noqa: BLE001
            surf = None
        self._img_cache[path] = surf
        return surf

    def draw_image_message(self, surface, text, y, img_path, idx=-1, top=0):
        """Bulle : legende + image + boutons Agrandir/Refaire (cote assistant)."""
        surf = self._get_image(img_path)
        cap_lines = wrap_text("Image : " + text, self.font_small, IMG_DISP)
        cap_h = self.font_small.get_linesize() * len(cap_lines)
        img_h = surf.get_height() if surf else 24
        img_w = surf.get_width() if surf else IMG_DISP
        bubble_w = max(img_w, IMG_DISP) + PAD * 2
        bubble_h = cap_h + img_h + PAD * 2 + 8 + 26      # +26 pour les boutons
        x = PAD
        pygame.draw.rect(surface, COL_ASSISTANT,
                         pygame.Rect(x, y, bubble_w, bubble_h), border_radius=14)
        surface.blit(self.font_small.render("L'IA", True, COL_MUTED), (x + 4, y - 18))
        ty = y + PAD
        for line in cap_lines:
            surface.blit(self.font_small.render(line, True, COL_WEB), (x + PAD, ty))
            ty += self.font_small.get_linesize()
        ty += 8
        if surf:
            surface.blit(surf, (x + PAD, ty))
            # zone cliquable pour agrandir (toute l'image)
            self._img_action_rects.append(
                (pygame.Rect(x + PAD, ty + top, img_w, img_h), "zoom", idx))
        else:
            surface.blit(self.font_small.render("[image indisponible]", True,
                                                COL_MUTED), (x + PAD, ty))
        # boutons sous l'image
        by = ty + img_h + 4
        for label, action, dx in (("Agrandir", "zoom", 0), ("Refaire", "refaire", 92)):
            bw = 84
            bx = x + PAD + dx
            pygame.draw.rect(surface, COL_ITEM,
                             pygame.Rect(bx, by, bw, 22), border_radius=7)
            img = self.font_small.render(label, True, COL_TEXT)
            surface.blit(img, (bx + (bw - img.get_width()) // 2, by + 3))
            self._img_action_rects.append(
                (pygame.Rect(bx, by + top, bw, 22), action, idx))
        return bubble_h + 34

    def _get_gif_frame(self, frames):
        """Renvoie la frame courante (animation) d'un gif, mise a l'echelle."""
        key = tuple(frames)
        if key not in self._gif_cache:
            surfs = []
            for p in frames:
                try:
                    img = pygame.image.load(p)
                    iw, ih = img.get_size()
                    sc = IMG_DISP / max(iw, ih)
                    surfs.append(pygame.transform.smoothscale(
                        img, (int(iw * sc), int(ih * sc))))
                except Exception:  # noqa: BLE001
                    pass
            self._gif_cache[key] = surfs
        surfs = self._gif_cache[key]
        if not surfs:
            return None
        if self._gif_paused.get(key):
            idx = self._gif_frozen.get(key, 0) % len(surfs)
        else:
            idx = (pygame.time.get_ticks() // 220) % len(surfs)
            self._gif_frozen[key] = idx      # on memorise pour une future pause
        return surfs[idx]

    def draw_gif_message(self, surface, text, y, frames, idx=-1, top=0):
        """Bulle avec une image qui S'ANIME (gif) + bouton Pause, cote assistant."""
        surf = self._get_gif_frame(frames)
        cap_lines = wrap_text("Video : " + text, self.font_small, IMG_DISP)
        cap_h = self.font_small.get_linesize() * len(cap_lines)
        img_h = surf.get_height() if surf else 24
        img_w = surf.get_width() if surf else IMG_DISP
        bubble_w = max(img_w, IMG_DISP) + PAD * 2
        bubble_h = cap_h + img_h + PAD * 2 + 8 + 26      # +26 pour le bouton
        x = PAD
        pygame.draw.rect(surface, COL_ASSISTANT,
                         pygame.Rect(x, y, bubble_w, bubble_h), border_radius=14)
        surface.blit(self.font_small.render("L'IA", True, COL_MUTED), (x + 4, y - 18))
        ty = y + PAD
        for line in cap_lines:
            surface.blit(self.font_small.render(line, True, COL_LOGIC), (x + PAD, ty))
            ty += self.font_small.get_linesize()
        ty += 8
        if surf:
            surface.blit(surf, (x + PAD, ty))
        else:
            surface.blit(self.font_small.render("[video indisponible]", True,
                                                COL_MUTED), (x + PAD, ty))
        # bouton Pause / Reprendre
        by = ty + img_h + 4
        paused = self._gif_paused.get(tuple(frames), False)
        label = "Reprendre" if paused else "Pause"
        bw = 96
        pygame.draw.rect(surface, COL_ITEM, pygame.Rect(x + PAD, by, bw, 22),
                         border_radius=7)
        lbl = self.font_small.render(label, True, COL_TEXT)
        surface.blit(lbl, (x + PAD + (bw - lbl.get_width()) // 2, by + 3))
        self._img_action_rects.append(
            (pygame.Rect(x + PAD, by + top, bw, 22), "pause", idx))
        return bubble_h + 34

    def draw_message(self, surface, role, text, kind, y, content_w, idx=-1, top=0,
                     img_path=None):
        if kind == "gif" and isinstance(img_path, list):
            return self.draw_gif_message(surface, text, y, img_path, idx, top)
        if kind == "image" and img_path:
            return self.draw_image_message(surface, text, y, img_path, idx, top)
        is_user = role == "user"
        bubble_col = COL_USER if is_user else COL_ASSISTANT
        txt_col = COL_TEXT
        if kind == "learn":
            txt_col = COL_LEARN
        elif kind == "logic":
            txt_col = COL_LOGIC
        elif kind == "web":
            txt_col = COL_WEB
        elif kind in ("info", "ask", "guess"):
            txt_col = COL_INFO
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
        label = "Toi" if is_user else "L'IA"
        surface.blit(self.font_small.render(label, True, COL_MUTED), (x + 4, y - 18))
        ty = y + PAD
        for line in lines:
            surface.blit(self.font.render(line, True, txt_col), (x + PAD, ty))
            ty += line_h

        # bouton « Modifier » sous les messages de l'utilisateur
        if is_user and idx >= 0:
            lbl = self.font_small.render("Modifier", True, COL_MUTED)
            bw2 = lbl.get_width() + 26
            bx = x + bubble_w - bw2
            by = y + bubble_h + 5
            pygame.draw.rect(surface, COL_ITEM,
                             pygame.Rect(bx, by, bw2, 20), border_radius=7)
            # petit crayon
            pcx, pcy = bx + 11, by + 10
            pygame.draw.line(surface, COL_MUTED, (pcx - 4, pcy + 4),
                             (pcx + 3, pcy - 3), 2)
            pygame.draw.line(surface, COL_ACCENT, (pcx + 3, pcy - 3),
                             (pcx + 5, pcy - 5), 2)
            surface.blit(lbl, (bx + 19, by + 3))
            self._edit_rects.append((pygame.Rect(bx, by + top, bw2, 20), idx))

        return bubble_h + 34

    def _measure(self, message, content_w):
        text, kind = message[1], message[2]
        if kind == "image":
            cap_lines = wrap_text("Image : " + text, self.font_small, IMG_DISP)
            cap_h = self.font_small.get_linesize() * len(cap_lines)
            return cap_h + IMG_DISP + PAD * 2 + 8 + 26 + 34
        if kind == "gif":
            cap_lines = wrap_text("Video : " + text, self.font_small, IMG_DISP)
            cap_h = self.font_small.get_linesize() * len(cap_lines)
            return cap_h + IMG_DISP + PAD * 2 + 8 + 26 + 34
        max_text_w = int(content_w * 0.80)
        lines = wrap_text(text, self.font, max_text_w)
        return self.font.get_linesize() * len(lines) + PAD * 2 + 34

    def draw(self):
        self.screen.fill(COL_BG)
        w, h = self.screen.get_size()
        sidebar_x = max(360, w - SIDEBAR_W)
        chat_w = sidebar_x
        content_w = chat_w - PAD * 2

        self.screen.blit(self.font_title.render("AMIE", True, COL_ACCENT),
                         (PAD, 12))
        mots = sum(1 for k in BRAIN.markov if not k.startswith("__"))
        sub = self.font_small.render(
            f"cerveau : {len(BRAIN.pairs)} reponses apprises, {mots} mots connus  "
            "•  tape « cerveau » pour voir",
            True, COL_MUTED)
        self.screen.blit(sub, (PAD, 40))
        pygame.draw.line(self.screen, COL_INPUT_BRD, (0, 62), (chat_w, 62), 1)

        top = 74
        bottom = h - (self.input_h + PAD * 2)
        view_h = bottom - top
        chat_surf = pygame.Surface((chat_w, max(view_h, 10)), pygame.SRCALPHA)

        total_h = PAD
        heights = []
        for message in self.messages:
            hgt = self._measure(message, content_w)
            heights.append(hgt)
            total_h += hgt
        if self.thinking:
            total_h += 36

        self.max_scroll = max(0, total_h - view_h)
        self.scroll = max(0, min(self.scroll, self.max_scroll))
        offset = total_h - view_h - self.scroll
        if total_h <= view_h:
            offset = 0

        self._edit_rects = []
        self._img_action_rects = []
        y = PAD - offset
        for idx, (message, hgt) in enumerate(zip(self.messages, heights)):
            role, text, kind = message[0], message[1], message[2]
            img_path = message[3] if len(message) > 3 else None
            if y + hgt > 0 and y < view_h:
                self.draw_message(chat_surf, role, text, kind, y, content_w,
                                  idx, top, img_path)
            y += hgt

        if self.thinking:
            dots = "." * (1 + (pygame.time.get_ticks() // 300) % 3)
            chat_surf.blit(self.font.render(self._think_label + dots, True,
                                            COL_MUTED), (PAD, y + 4))

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
            ph = self.font.render("Parle-lui, ou apprends: X = Y ...", True, COL_MUTED)
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
        if self._zoom is not None:
            self._draw_zoom(w, h)
        pygame.display.flip()

    def _draw_zoom(self, w, h):
        """Affiche l'image en grand par-dessus tout (clic ou Echap pour fermer)."""
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))
        key = self._zoom + "__big"
        if key not in self._img_cache:
            big = None
            try:
                img = pygame.image.load(self._zoom)
                iw, ih = img.get_size()
                sc = min((w - 80) / iw, (h - 100) / ih)
                big = pygame.transform.smoothscale(img, (int(iw * sc), int(ih * sc)))
            except Exception:  # noqa: BLE001
                big = None
            self._img_cache[key] = big
        big = self._img_cache[key]
        if big:
            self.screen.blit(big, ((w - big.get_width()) // 2,
                                   (h - big.get_height()) // 2 - 10))
        hint = self.font_small.render("Clique n'importe ou (ou Echap) pour fermer",
                                      True, COL_MUTED)
        self.screen.blit(hint, ((w - hint.get_width()) // 2, h - 34))

    def _draw_sidebar(self, x0, w, h):
        pygame.draw.rect(self.screen, COL_SIDEBAR, (x0, 0, w - x0, h))
        pygame.draw.line(self.screen, COL_INPUT_BRD, (x0, 0), (x0, h), 1)
        inner_w = (w - x0) - 24

        self.screen.blit(self.font_small.render("DISCUSSIONS", True, COL_MUTED),
                         (x0 + 14, 16))

        self._new_btn = pygame.Rect(x0 + 12, 38, inner_w, 34)
        pygame.draw.rect(self.screen, COL_ITEM, self._new_btn, border_radius=9)
        self.screen.blit(self.font_small.render("+  Nouvelle", True, COL_TEXT),
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
        if self._zoom is not None:          # image en grand : un clic/Echap ferme
            if event.type == pygame.MOUSEBUTTONDOWN or (
                    event.type == pygame.KEYDOWN
                    and event.key in (pygame.K_ESCAPE, pygame.K_RETURN)):
                self._zoom = None
            return True
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
                hit = False
                for er, i in self._edit_rects:
                    if er.collidepoint(pos):
                        self.edit_message(i)
                        hit = True
                        break
                if not hit:
                    for ar, action, i in self._img_action_rects:
                        if ar.collidepoint(pos):
                            if action == "zoom" and 0 <= i < len(self.messages) \
                                    and len(self.messages[i]) > 3:
                                self._zoom = self.messages[i][3]
                            elif action == "refaire":
                                self.start_rerun(i)
                            elif action == "pause" and 0 <= i < len(self.messages) \
                                    and isinstance(self.messages[i][3], list):
                                cle = tuple(self.messages[i][3])
                                self._gif_paused[cle] = not self._gif_paused.get(cle)
                            hit = True
                            break
                if not hit:
                    for tr, i in self._trash_rects:
                        if tr.collidepoint(pos):
                            self._pending_delete = i
                            hit = True
                            break
                if not hit:
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
