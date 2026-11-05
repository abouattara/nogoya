"""La version des conditions en vigueur.

Le texte lui-même vit dans le frontend, à l'écran que la personne lit
avant de cocher la case. Ce qui vit ici, c'est son numéro de version : le
serveur a besoin de savoir ce qui était affiché pour l'inscrire dans la
trace d'acceptation, et de refuser une acceptation portant sur un texte
qui n'est plus celui du site.

La version est une date, parce qu'une question de litige se pose toujours
sous la forme « qu'est-ce qui s'appliquait ce jour-là ». À chaque
modification du texte, cette constante avance et le frontend suit : les
comptes existants gardent la trace de ce qu'ils avaient accepté, et les
nouveaux acceptent le texte à jour.
"""

TERMS_VERSION = "2026-11-05"
