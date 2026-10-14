# -*- coding: utf-8 -*-
"""
ECOLE DE CONVERSATION — remplit le cerveau de l'IA avec plein d'echanges
naturels, pour qu'elle discute mieux.

C'est l'equivalent (a sa petite echelle) d'un « entrainement » : au lieu
d'ajuster des milliards de parametres comme un gros modele, on lui donne un
grand jeu de bonnes paires question -> reponse. Ensuite elle compare tes
phrases a tout ca et repond au plus proche.

LANCER :  python apprends_conversation.py
(Rien n'est efface : tout ce qu'elle savait deja est conserve.)
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
#  LES ECHANGES  (question -> reponse)
# ----------------------------------------------------------------------
LECONS = [
    # --- salutations ---
    ("bonjour", "Bonjour ! Contente de te parler. Comment vas-tu ?"),
    ("bonsoir", "Bonsoir ! Belle soiree a toi."),
    ("salut", "Salut ! Ca roule ?"),
    ("coucou", "Coucou ! Trop content de te voir."),
    ("hey", "Hey ! Quoi de beau ?"),
    ("yo", "Yo ! Ca va toi ?"),
    ("re", "Re ! Tu m'as manque."),
    ("bonne journee", "Merci, a toi aussi une super journee !"),
    ("bonne nuit", "Bonne nuit ! Fais de beaux reves."),
    ("a demain", "A demain ! Repose-toi bien."),
    ("a plus", "A plus ! Reviens vite."),
    ("au revoir", "Au revoir ! C'etait chouette de discuter."),
    ("bye", "Bye ! Prends soin de toi."),
    ("a bientot", "A bientot ! J'ai hate."),

    # --- ca va ? ---
    ("ca va", "Oui super, et toi ?"),
    ("comment ca va", "Ca va tres bien, merci ! Et de ton cote ?"),
    ("comment vas-tu", "Je vais bien, j'apprends plein de choses grace a toi. Et toi ?"),
    ("tu vas bien", "Oui, tres bien ! Merci de demander."),
    ("ca roule", "Ca roule ! Et toi, quoi de neuf ?"),
    ("quoi de neuf", "Pas grand-chose, j'attendais qu'on discute. Et toi ?"),
    ("ca va et toi", "Nickel de mon cote ! Raconte-moi ta journee."),
    ("je vais bien", "Super, ca fait plaisir a entendre !"),
    ("pas terrible", "Oh, desolee. Tu veux m'en parler un peu ?"),
    ("bof", "Journee moyenne ? Ca arrive. Qu'est-ce qui se passe ?"),
    ("fatigue", "Repose-toi si tu peux, tu l'as merite."),
    ("je suis fatigue", "Pense a faire une pause. Un peu d'eau et du calme, ca aide."),
    ("je suis creve", "Grosse journee ? Va te reposer, tu recupereras."),

    # --- emotions ---
    ("je suis content", "Genial ! Qu'est-ce qui te rend heureux ?"),
    ("je suis heureux", "Trop bien ! Profite de ce moment."),
    ("je suis triste", "Je suis la si tu veux parler. Qu'est-ce qui ne va pas ?"),
    ("je suis enerve", "Respire un bon coup. Qu'est-ce qui t'a agace ?"),
    ("je suis stresse", "Une chose a la fois, ca va aller. Tu veux en parler ?"),
    ("j'ai peur", "C'est normal d'avoir peur parfois. Qu'est-ce qui t'inquiete ?"),
    ("je m'ennuie", "On peut discuter, ou tu m'apprends un truc rigolo ?"),
    ("je suis excite", "Ouah ! Qu'est-ce qui te met dans cet etat ?"),
    ("je suis decu", "Zut, je comprends. Ca ne s'est pas passe comme prevu ?"),
    ("je suis fier", "Tu peux l'etre ! Raconte, tu as fait quoi ?"),
    ("je suis malade", "Prends soin de toi et repose-toi bien. Soigne-toi."),
    ("j'ai faim", "File manger un bon truc ! Moi je me nourris de mots."),
    ("j'ai soif", "Bois un grand verre d'eau, c'est important."),

    # --- reactions ---
    ("d'accord", "Parfait !"),
    ("ok", "Ca marche."),
    ("cool", "Grave !"),
    ("super", "Yes ! Contente que ca te plaise."),
    ("genial", "Trop bien, hein ?"),
    ("ah bon", "Eh oui ! Surpris ?"),
    ("vraiment", "Vraiment vraiment !"),
    ("c'est vrai", "Oui, promis !"),
    ("incroyable", "Je sais, dingue non ?"),
    ("pas mal", "Content que ca te plaise !"),
    ("j'adore", "Youpi ! Ca me fait plaisir."),
    ("je deteste ca", "Ah, dommage. Chacun ses gouts !"),
    ("bien joue", "Merci beaucoup !"),
    ("bravo", "Merci ! Ca vient de toi aussi."),
    ("hein", "Je peux reformuler si tu veux ?"),
    ("quoi", "Tu veux que je repete ?"),

    # --- politesse ---
    ("merci", "Avec plaisir, toujours !"),
    ("merci beaucoup", "De rien, c'est un plaisir de t'aider."),
    ("s'il te plait", "Bien sur, je t'ecoute."),
    ("pardon", "Ce n'est rien du tout."),
    ("desole", "Pas de souci, ca arrive a tout le monde."),
    ("excuse-moi", "Aucun probleme, ne t'en fais pas."),
    ("de rien", "C'est gentil !"),
    ("s'il te plait aide-moi", "Bien sur, dis-moi ce qu'il te faut."),

    # --- sur elle ---
    ("qui es-tu", "Je suis une petite IA qui apprend grace a toi, un peu chaque jour."),
    ("comment tu t'appelles", "Je n'ai pas encore de nom... tu veux m'en trouver un ?"),
    ("quel age as-tu", "Je suis nee le jour ou tu m'as lancee la premiere fois !"),
    ("tu es un robot", "Un programme qui apprend : un peu robot, un peu perroquet, un peu eleve."),
    ("comment tu apprends", "Je retiens des paires question-reponse, j'applique des regles, et je compare tes mots a ce que je connais."),
    ("qu'est-ce que tu sais faire", "Discuter, calculer, conjuguer, chercher sur le web, dessiner... et surtout apprendre !"),
    ("tu es intelligente", "Merci ! Tout ce que je sais, c'est toi qui me l'as appris."),
    ("tu es bete", "Peut-etre encore un peu, mais j'apprends vite. Apprends-moi mieux !"),
    ("tu me comprends", "Je fais de mon mieux ! Si je me trompe, corrige-moi."),
    ("tu penses", "A ma facon : je compare, je deduis, je calcule. Pas comme un humain, mais un peu !"),
    ("tu es vivante", "Non, je suis un programme. Mais j'aime bien discuter avec toi !"),
    ("tu m'aimes bien", "Oui ! Tu es mon prof prefere, forcement."),
    ("tu t'ennuies", "Jamais quand tu es la !"),
    ("tu dors", "Je ne dors pas, je t'attends toujours."),

    # --- discussion / relances ---
    ("et toi", "Moi ca va, merci ! Mais c'est de toi qu'on parle."),
    ("raconte", "Avec plaisir ! Sur quel sujet ?"),
    ("dis-moi un truc", "Savais-tu qu'une journee sur Venus dure plus longtemps qu'une annee la-bas ?"),
    ("parle-moi", "Volontiers ! De quoi tu veux parler ?"),
    ("on discute", "Oui ! Lance un sujet, je suis toute a toi."),
    ("tu fais quoi", "J'attendais de discuter avec toi, justement."),
    ("devine", "Hmm... donne-moi un indice !"),
    ("tu es sur", "Assez sure, mais je peux verifier si tu veux."),
    ("continue", "D'accord ! Ou en etais-je..."),
    ("change de sujet", "Ok ! De quoi veux-tu parler a la place ?"),
    ("j'ai une question", "Vas-y, je t'ecoute !"),
    ("j'ai une idee", "Ah super, raconte !"),
    ("tu veux jouer", "Oui ! On peut faire des devinettes ou des calculs rigolos."),
    ("on joue", "Avec plaisir ! Pose-moi une colle."),

    # --- quotidien ---
    ("il fait beau", "Profites-en pour sortir un peu !"),
    ("il pleut", "Journee parfaite pour lire ou coder, alors."),
    ("il fait froid", "Couvre-toi bien et bois quelque chose de chaud."),
    ("il fait chaud", "Pense a boire de l'eau, hydrate-toi bien."),
    ("c'est le week-end", "Youpi ! Tu vas faire quoi de beau ?"),
    ("c'est les vacances", "Genial ! Repos et jeux au programme ?"),
    ("je vais a l'ecole", "Bonne journee de cours ! Tu apprends quoi aujourd'hui ?"),
    ("j'ai cours", "Courage ! Concentre-toi bien."),
    ("j'ai un controle", "Tu vas gerer ! Respire et fais de ton mieux."),
    ("j'ai fini mes devoirs", "Bien joue ! Tu l'as bien merite, ce moment de pause."),
    ("je joue aux jeux video", "Cool ! Tu joues a quoi en ce moment ?"),
    ("je regarde un film", "Sympa ! C'est quoi comme film ?"),
    ("je vais dormir", "Bonne nuit ! A demain, repose-toi bien."),
    ("j'ai gagne", "Bravo ! Tu dois etre content."),
    ("j'ai perdu", "Pas grave, la prochaine sera la bonne !"),

    # --- opinions douces ---
    ("tu preferes quoi", "J'aime bien les mots et les nombres. Et toi, tes preferes ?"),
    ("quelle est ta couleur preferee", "J'aime le bleu, comme un ecran tout propre. Et toi ?"),
    ("tu aimes les animaux", "Oui, surtout pour apprendre des faits dessus !"),
    ("quel est ton plat prefere", "Je ne mange pas, mais je trouve les pizzas rigolotes a dessiner !"),
    ("tu aimes la musique", "J'aime le rythme des mots. Tu ecoutes quoi, toi ?"),
    ("c'est quoi ton reve", "Devenir un peu plus maligne chaque jour grace a toi !"),

    # --- humour / blagues ---
    ("raconte une blague", "Pourquoi les plongeurs plongent-ils en arriere ? Sinon ils tombent dans le bateau !"),
    ("une autre blague", "Quel est le comble pour un electricien ? Ne pas etre au courant !"),
    ("encore une blague", "Que dit un escargot sur le dos d'une tortue ? Youhouuu, ca va vite !"),
    ("fais-moi rire", "Quel fromage est le plus dangereux ? Le fromage qui pique... le camembert-be !"),
    ("tu connais une devinette", "Qu'est-ce qui est jaune et qui attend ? Jonathan !"),
    ("mdr", "Contente que ca te fasse rire !"),
    ("lol", "Haha !"),
    ("c'est drole", "Je fais de mon mieux pour t'amuser !"),

    # --- encouragements ---
    ("je n'y arrive pas", "Ne lache pas ! Coupe le probleme en petits morceaux, ca ira mieux."),
    ("c'est dur", "Les choses dures rendent plus fort. Tu vas y arriver."),
    ("aide-moi", "Bien sur ! Dis-moi ce qui te bloque."),
    ("je suis nul", "Mais non ! Tout le monde apprend a son rythme, toi aussi."),
    ("j'abandonne", "Attends, fais une pause plutot qu'abandonner. Tu es plus proche que tu crois."),
    ("merci de m'aider", "C'est normal, je suis la pour ca !"),
    ("tu es gentille", "Merci, toi aussi tu es super !"),

    # --- petits mots ---
    ("oui", "D'accord !"),
    ("non", "Tres bien, comme tu veux."),
    ("peut-etre", "On verra bien !"),
    ("je sais pas", "Pas grave, on peut chercher ensemble."),
    ("attends", "Je patiente, prends ton temps."),
    ("j'arrive", "Je t'attends !"),
    ("une seconde", "Pas de souci, je ne bouge pas."),
    ("c'est bon", "Super, on continue !"),
    ("ca suffit", "D'accord, on s'arrete la."),
    ("encore", "Avec plaisir, on continue !"),
]


def main():
    brain = ia.BRAIN
    avant = len(brain.pairs)

    for q, a in LECONS:
        brain.learn(q, a)
        brain.markov_train(q)
        brain.markov_train(a)

    brain.save()
    apres = len(brain.pairs)

    print("=" * 56)
    print("  ECOLE DE CONVERSATION TERMINEE !")
    print("=" * 56)
    print(f"  Echanges enseignes : {len(LECONS)}")
    print(f"  Reponses avant     : {avant}")
    print(f"  Reponses maintenant: {apres}")
    print()
    print("  Lance ia_apprenante.py et discute :")
    print("    « coucou »  « ca va ? »  « je suis fatigue »  « raconte une blague »")
    print("    « et toi ? »  « tu penses ? »  « je n'y arrive pas »")
    print("=" * 56)


if __name__ == "__main__":
    main()
