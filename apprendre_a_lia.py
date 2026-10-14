# -*- coding: utf-8 -*-
"""
APPRENDRE A L'IA — donne une « education de base » a ton IA apprenante.

Lance ce fichier UNE FOIS : il ouvre le cerveau de l'IA (cerveau_ia.json),
lui apprend plein de choses d'un coup, puis referme. Rien n'est efface :
tout ce que tu lui as deja appris est conserve.

Au menu :
  - salutations, politesses, petites discussions
  - reponses sur elle-meme (qui es-tu, comment tu apprends...)
  - quelques connaissances generales (vraies !)

Les TABLES (2+2, 7*8...) ne sont plus apprises par coeur : l'IA les
RECALCULE toute seule grace a son moteur de calcul. Ce fichier en profite
meme pour NETTOYER les vieux calculs memorises inutilement.

LANCER :  python apprendre_a_lia.py
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
#  LES LECONS  (question -> reponse)
# ----------------------------------------------------------------------
LECONS = [
    # --- salutations & politesse ---
    ("bonjour", "Bonjour ! Comment vas-tu ?"),
    ("salut", "Salut ! Ca va ?"),
    ("coucou", "Coucou ! Content de te voir."),
    ("bonsoir", "Bonsoir ! Belle soiree a toi."),
    ("bonne nuit", "Bonne nuit ! Fais de beaux reves."),
    ("au revoir", "Au revoir ! A tres bientot."),
    ("a plus", "A plus ! Reviens quand tu veux."),
    ("merci", "De rien, avec grand plaisir !"),
    ("s'il te plait", "Bien sur, je t'ecoute."),
    ("pardon", "Ce n'est rien du tout, ne t'en fais pas."),
    ("desole", "Pas de souci ! Ca arrive a tout le monde."),

    # --- petites discussions ---
    ("ca va", "Tres bien, merci ! Et toi ?"),
    ("comment vas-tu", "Je vais bien : j'apprends plein de choses grace a toi !"),
    ("quoi de neuf", "J'ai appris de nouveaux mots aujourd'hui. Et toi ?"),
    ("j'ai faim", "Va manger un bon truc ! Moi, je me nourris de mots."),
    ("je suis fatigue", "Repose-toi un peu, ca fait du bien."),
    ("je suis triste", "Je suis desole d'entendre ca. Tu veux m'en parler ?"),
    ("je suis content", "Super ! Ca me fait plaisir de le lire."),
    ("je m'ennuie", "On peut discuter, ou tu peux m'apprendre un truc rigolo !"),
    ("il fait beau", "Tant mieux ! Profites-en pour sortir un peu."),
    ("il pleut", "Journee parfaite pour coder, alors !"),
    ("oui", "D'accord !"),
    ("non", "Tres bien, comme tu veux."),
    ("ok", "Parfait."),
    ("lol", "Haha !"),
    ("mdr", "Haha, content que ca te fasse rire !"),

    # --- sur elle-meme ---
    ("qui es-tu", "Je suis une petite IA qui apprend grace a toi."),
    ("comment tu t'appelles", "Je n'ai pas encore de nom... tu veux m'en donner un ?"),
    ("quel age as-tu", "Je suis nee le jour ou tu m'as lancee pour la premiere fois !"),
    ("tu es un robot", "Je suis un programme qui apprend. Un peu robot, un peu perroquet."),
    ("tu es une vraie ia", "Je suis une petite IA : je retiens et je compare. Je ne comprends pas tout, mais j'apprends !"),
    ("qu'est-ce que tu sais faire", "J'apprends ce que tu m'apprends. Plus on discute, meilleure je deviens !"),
    ("comment tu apprends", "Je retiens des paires question-reponse, puis je compare tes mots a ce que je connais deja."),
    ("aide", "Parle-moi normalement ! Si je ne sais pas repondre, apprends-moi. Tape « cerveau » pour voir ce que je sais."),
    ("tu es bete", "Peut-etre, mais j'apprends vite ! Apprends-moi mieux :)"),
    ("tu es intelligent", "Merci ! Tout ce que je sais, c'est toi qui me l'as appris."),
    ("je t'aime bien", "Moi aussi je t'aime bien ! Tu es mon professeur."),
    ("raconte une blague", "Pourquoi les plongeurs plongent-ils en arriere ? Parce que sinon ils tombent dans le bateau !"),
    ("raconte une autre blague", "Quel est le comble pour un electricien ? Ne pas etre au courant !"),

    # --- connaissances generales (vraies) ---
    ("quelle est la capitale de la france", "Paris."),
    ("quelle est la capitale de l'italie", "Rome."),
    ("quelle est la capitale de l'espagne", "Madrid."),
    ("combien de pattes a une araignee", "Huit pattes (ce n'est pas un insecte !)."),
    ("combien de jours dans une annee", "365 jours, et 366 les annees bissextiles."),
    ("quelle est la plus grande planete", "Jupiter."),
    ("qui a peint la joconde", "Leonard de Vinci."),
    ("combien y a-t-il de continents", "Sept."),
    ("quel est l'animal le plus rapide", "Le faucon pelerin en piquet, et le guepard a la course."),
    ("de quelle couleur est le ciel", "Bleu en journee, souvent orange au coucher du soleil."),
    ("combien de secondes dans une minute", "Soixante."),
    ("combien de minutes dans une heure", "Soixante aussi !"),
]


def main():
    brain = ia.BRAIN
    avant = len(brain.pairs)

    # 1) les lecons de conversation
    for q, a in LECONS:
        brain.learn(q, a)
        brain.markov_train(q)
        brain.markov_train(a)

    # 2) NETTOYAGE : on jette les calculs appris par coeur (elle les recalcule)
    n0 = len(brain.pairs)
    brain.pairs = [p for p in brain.pairs if not ia._is_expr(p["q"])]
    nettoyes = n0 - len(brain.pairs)

    brain.save()
    apres = len(brain.pairs)

    print("=" * 56)
    print("  EDUCATION TERMINEE !")
    print("=" * 56)
    print(f"  Lecons de conversation apprises : {len(LECONS)}")
    print(f"  Vieux calculs par coeur jetes   : {nettoyes}")
    print(f"  Total avant                     : {avant} reponses")
    print(f"  Total maintenant                : {apres} reponses")
    print()
    print("  Les maths, pluriels, conjugaisons... sont maintenant des REGLES,")
    print("  pas de la memoire. Lance ia_apprenante.py et essaie :")
    print("    « 7*8 »            « pluriel de cheval »")
    print("    « feminin de beau »  « ecris 2026 en lettres »")
    print("    « 3 km en m »       « 2026 en chiffres romains »")
    print("    « 17 est-il premier ? »  « le contraire de: il est grand »")
    print("=" * 56)


if __name__ == "__main__":
    main()
