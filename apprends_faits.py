# -*- coding: utf-8 -*-
"""
PACK DE FAITS — donne a l'IA une grande « ontologie » : des relations
« X est un Y » reliees en chaine.

Pourquoi c'est puissant : avec ~230 faits bien relies, elle repond a des
MILLIERS de questions qu'on ne lui a jamais posees, par DEDUCTION.
Exemple : elle apprend  aigle -> oiseau,  oiseau -> animal,  animal -> vivant.
Alors « un aigle est-il un etre vivant ? » -> OUI (aigle > oiseau > animal > vivant).

C'est ca, raisonner : combiner des faits simples pour repondre a du nouveau.

LANCER :  python apprends_faits.py
(Rien n'est efface : les faits deja connus sont conserves.)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import ia_apprenante as ia
except Exception as e:  # noqa: BLE001
    print("Impossible d'ouvrir ia_apprenante.py :", e)
    sys.exit(1)


# ----------------------------------------------------------------------
#  1) LES CATEGORIES : chaque membre « est un » <categorie>
# ----------------------------------------------------------------------
GROUPES = {
    # --- animaux ---
    "mammifere": ["chat", "chien", "cheval", "vache", "cochon", "mouton",
                  "chevre", "lion", "tigre", "ours", "loup", "renard",
                  "elephant", "souris", "rat", "lapin", "singe", "gorille",
                  "girafe", "zebre", "hippopotame", "rhinoceros", "dauphin",
                  "baleine", "phoque", "kangourou", "koala", "panda",
                  "ecureuil", "herisson", "chameau", "cerf", "sanglier",
                  "taupe", "chauve-souris", "humain", "homme"],
    "oiseau": ["aigle", "hibou", "chouette", "perroquet", "pingouin",
               "manchot", "canard", "poule", "coq", "oie", "cygne", "corbeau",
               "moineau", "pigeon", "mouette", "autruche", "flamant", "paon",
               "faucon", "vautour", "hirondelle", "merle"],
    "poisson": ["saumon", "thon", "sardine", "truite", "requin", "carpe",
                "anguille", "hippocampe", "raie", "morue"],
    "reptile": ["serpent", "lezard", "crocodile", "tortue", "cameleon",
                "iguane", "gecko", "alligator", "vipere", "cobra"],
    "amphibien": ["grenouille", "crapaud", "salamandre", "triton"],
    "insecte": ["fourmi", "abeille", "mouche", "moustique", "papillon",
                "coccinelle", "scarabee", "sauterelle", "criquet", "libellule",
                "guepe", "chenille", "puceron", "grillon"],
    "arachnide": ["araignee", "scorpion", "acarien", "tique"],
    "mollusque": ["escargot", "poulpe", "pieuvre", "moule", "huitre", "calmar",
                  "limace"],
    "crustace": ["crabe", "crevette", "homard", "langouste", "ecrevisse"],
    # --- vegetaux ---
    "arbre": ["chene", "sapin", "pin", "bouleau", "palmier", "pommier",
              "cerisier", "olivier", "saule", "erable", "peuplier", "hetre"],
    "fleur": ["rose", "tulipe", "marguerite", "tournesol", "lys", "violette",
              "coquelicot", "jonquille", "orchidee", "pivoine", "muguet"],
    "fruit": ["pomme", "poire", "banane", "orange", "fraise", "cerise",
              "raisin", "peche", "abricot", "kiwi", "ananas", "citron",
              "pasteque", "melon", "prune", "framboise", "mangue"],
    "legume": ["carotte", "tomate", "patate", "salade", "courgette", "poireau",
               "oignon", "haricot", "epinard", "chou", "radis", "navet",
               "aubergine", "concombre"],
    # --- objets ---
    "vehicule": ["voiture", "camion", "moto", "velo", "bus", "train", "avion",
                 "bateau", "tracteur", "helicoptere", "fusee", "trottinette",
                 "sous-marin", "montgolfiere"],
    "meuble": ["chaise", "table", "lit", "armoire", "canape", "bureau",
               "etagere", "commode", "tabouret"],
    "instrument": ["guitare", "piano", "violon", "flute", "batterie",
                   "trompette", "harpe", "saxophone", "accordeon"],
    "vetement": ["pantalon", "chemise", "robe", "manteau", "chaussure",
                 "chapeau", "pull", "jupe", "veste", "echarpe", "gant"],
    "outil": ["marteau", "tournevis", "scie", "pince", "perceuse", "cle",
              "rateau", "pelle"],
    # --- lieux ---
    "pays": ["france", "espagne", "italie", "allemagne", "portugal",
             "belgique", "suisse", "japon", "chine", "inde", "bresil",
             "canada", "mexique", "egypte", "maroc", "algerie", "senegal",
             "russie", "australie", "argentine", "grece", "norvege"],
    "ville": ["paris", "londres", "rome", "madrid", "berlin", "tokyo",
              "pekin", "moscou", "lisbonne", "bruxelles", "geneve"],
    "planete": ["terre", "mars", "venus", "jupiter", "saturne", "mercure",
                "neptune", "uranus"],
}


# ----------------------------------------------------------------------
#  2) LES LIENS ENTRE CATEGORIES (les chaines montent vers le haut)
# ----------------------------------------------------------------------
LIENS = [
    # tous les animaux -> animal -> vivant
    ("mammifere", "animal"), ("oiseau", "animal"), ("poisson", "animal"),
    ("reptile", "animal"), ("amphibien", "animal"), ("insecte", "animal"),
    ("arachnide", "animal"), ("mollusque", "animal"), ("crustace", "animal"),
    ("animal", "vivant"),
    # vegetaux -> vegetal -> vivant
    ("arbre", "vegetal"), ("fleur", "vegetal"), ("fruit", "vegetal"),
    ("legume", "vegetal"), ("vegetal", "vivant"),
    # fruits et legumes sont aussi des aliments
    ("fruit", "aliment"), ("legume", "aliment"),
    # humains
    ("humain", "mammifere"), ("homme", "mammifere"),
    # objets
    ("vehicule", "objet"), ("meuble", "objet"), ("instrument", "objet"),
    ("vetement", "objet"), ("outil", "objet"),
    ("instrument", "instrument de musique"),
    # lieux
    ("pays", "lieu"), ("ville", "lieu"),
    # espace
    ("planete", "astre"), ("etoile", "astre"), ("soleil", "etoile"),
    ("lune", "astre"), ("terre", "planete"),
]


def main():
    brain = ia.BRAIN
    strip = ia._strip_accents
    avant = sum(len(v) for v in brain.facts.values())

    def ajoute(sujet, cat):
        sujet, cat = strip(sujet.lower()), strip(cat.lower())
        brain.facts.setdefault(sujet, [])
        if cat not in brain.facts[sujet]:
            brain.facts[sujet].append(cat)

    n = 0
    for categorie, membres in GROUPES.items():
        for membre in membres:
            ajoute(membre, categorie)
            n += 1
    for sujet, cat in LIENS:
        ajoute(sujet, cat)
        n += 1

    brain.save()
    apres = sum(len(v) for v in brain.facts.values())

    print("=" * 58)
    print("  PACK DE FAITS CHARGE !")
    print("=" * 58)
    print(f"  Faits proposes     : {n}")
    print(f"  Faits connus avant : {avant}")
    print(f"  Faits connus apres : {apres}")
    print()
    print("  Lance ia_apprenante.py et teste sa DEDUCTION :")
    print("    « un aigle est-il un animal ? »   -> oui (aigle > oiseau > animal)")
    print("    « une rose est-elle vivante ? »   -> oui (rose > fleur > vegetal > vivant)")
    print("    « une voiture est-elle un objet ? »")
    print("    « paris est-il un lieu ? »   « mars est-elle une planete ? »")
    print("=" * 58)


if __name__ == "__main__":
    main()
