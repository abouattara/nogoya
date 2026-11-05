/**
 * Les conditions générales et la politique d'utilisation de BINOGOYA.
 *
 * Le texte vit ici, en données, et non dans le balisage de la page : il
 * se relit sans traverser du JSX, la page en dérive son sommaire, et une
 * modification se voit en diff comme une modification de texte.
 *
 * `TERMS_VERSION` doit rester égal à `apps/legal/terms.py` côté serveur.
 * C'est ce numéro que le formulaire d'inscription envoie, que le serveur
 * vérifie, et qu'il inscrit dans la trace d'acceptation. Faire avancer
 * l'un sans l'autre bloque les inscriptions avec un message qui demande
 * de recharger la page, donc les deux avancent dans le même commit.
 */

export const TERMS_VERSION = "2026-11-05";

export const TERMS_LABEL = "Version du 5 novembre 2026";

export type Block =
  | { kind: "p"; text: string }
  | { kind: "h3"; text: string }
  | { kind: "ul"; items: string[] }
  | { kind: "ol"; items: string[] };

export interface Section {
  id: string;
  title: string;
  blocks: Block[];
}

export const PREAMBLE: Block[] = [
  {
    kind: "p",
    text:
      "BINOGOYA met en relation des personnes qui possèdent un bien à louer et des personnes qui cherchent à en louer un. Le site ne loue rien lui-même. Il tient le rôle d'intermédiaire, et cet intermédiaire est tenu par une équipe qui regarde ce qui passe avant que cela ne devienne visible.",
  },
  {
    kind: "p",
    text: "Trois principes commandent tout ce qui suit.",
  },
  {
    kind: "ul",
    items: [
      "Aucune annonce n'apparaît sur le site sans avoir été lue par l'équipe.",
      "Personne n'obtient les coordonnées de quelqu'un d'autre tant que l'équipe ne les a pas transmises.",
      "Toute activité suspecte, arnaque ou contenu non sain, est sanctionnée.",
    ],
  },
  {
    kind: "p",
    text:
      "En créant un compte, vous déclarez avoir lu ce texte et l'accepter. Nous conservons la date de votre acceptation et le numéro de version du texte qui vous a été présenté, de sorte qu'il reste possible de dire, plus tard, ce qui avait été accepté et quand.",
  },
];

export const SECTIONS: Section[] = [
  {
    id: "prise-en-main",
    title: "1. Prise en main",
    blocks: [
      {
        kind: "p",
        text: "Le parcours tient en cinq temps, toujours dans le même ordre.",
      },
      {
        kind: "ol",
        items: [
          "Un fournisseur publie une annonce : description, photos, prix, localité, dates de disponibilité.",
          "L'annonce entre dans une file d'attente. Une personne de l'équipe la lit, puis la publie ou la refuse. Tant qu'elle n'est pas publiée, elle n'existe pour personne d'autre que son auteur.",
          "Un client trouve le bien et envoie une demande : les dates voulues, et un message. Une demande peut se faire sans compte, avec un numéro pour être rappelé.",
          "L'équipe vérifie la disponibilité auprès du fournisseur. C'est ce temps qui évite les allers-retours sur un bien déjà loué.",
          "Si le bien est libre, l'équipe met les deux parties en relation. Les coordonnées ne circulent qu'à ce moment, et seulement entre ces deux personnes.",
        ],
      },
      { kind: "h3", text: "Pourquoi ce détour" },
      {
        kind: "p",
        text:
          "Un numéro de téléphone affiché en clair sur une annonce attire le démarchage avant d'attirer des clients. Une annonce laissée en ligne alors que le bien est déjà pris fait perdre du temps à tout le monde et ruine la confiance. Passer par l'équipe coûte quelques heures ; cela évite ces deux situations, et cela donne un interlocuteur à qui s'adresser quand quelque chose ne va pas.",
      },
      { kind: "h3", text: "Ce que l'on attend de vous" },
      {
        kind: "ul",
        items: [
          "Décrire le bien tel qu'il est, avec des photos récentes et prises par vous.",
          "Annoncer le prix que vous pratiquez réellement, toutes charges comprises ou en disant clairement ce qui s'ajoute.",
          "Signaler sans attendre qu'un bien n'est plus disponible, depuis votre espace fournisseur.",
          "Répondre dans des délais raisonnables quand l'équipe vous écrit pour vérifier une disponibilité.",
        ],
      },
    ],
  },
  {
    id: "protection-des-donnees",
    title: "2. Protection des données",
    blocks: [
      { kind: "h3", text: "Ce que nous recueillons" },
      {
        kind: "ul",
        items: [
          "Votre nom et votre numéro de téléphone, qui servent à vous identifier et à vous joindre.",
          "Votre adresse électronique, si vous en donnez une. Elle reste facultative.",
          "Le contenu de vos annonces : texte, photos, prix, localité.",
          "Le contenu de vos échanges avec l'équipe : messages écrits, photos, vidéos et messages vocaux.",
          "Quelques mesures d'usage, comme le nombre de fois qu'une annonce a été consultée.",
        ],
      },
      { kind: "h3", text: "Ce que nous en faisons" },
      {
        kind: "ul",
        items: [
          "Faire fonctionner le service : afficher les annonces, acheminer les messages, tenir les demandes.",
          "Vérifier une disponibilité auprès d'un fournisseur, puis organiser la mise en relation.",
          "Modérer les contenus et instruire les signalements.",
          "Mesurer l'usage du site de façon agrégée, pour savoir ce qui sert et ce qui ne sert pas.",
        ],
      },
      { kind: "h3", text: "Ce que nous ne faisons pas" },
      {
        kind: "ul",
        items: [
          "Nous ne vendons aucune donnée, à personne, sous aucune forme.",
          "Nous n'affichons jamais votre numéro de téléphone sur une page publique, ni sur une annonce.",
          "Nous ne transmettons vos coordonnées à un autre membre qu'au moment de la mise en relation, et nous vous le disons.",
          "Nous n'utilisons pas vos conversations pour de la publicité.",
        ],
      },
      { kind: "h3", text: "Qui peut voir quoi" },
      {
        kind: "p",
        text:
          "Vos échanges sont accessibles à vous et à l'équipe de modération, personne d'autre. Un membre ne peut pas ouvrir la conversation d'un autre, ni écouter le message vocal d'un fil auquel il n'appartient pas, ni modifier l'annonce de quelqu'un d'autre. Cette séparation n'est pas une affaire d'affichage : le serveur revérifie l'appartenance à chaque requête, de sorte que changer un identifiant dans une adresse ne donne accès à rien.",
      },
      { kind: "h3", text: "Durée de conservation" },
      {
        kind: "p",
        text:
          "Vos données sont conservées tant que votre compte existe. À la fermeture du compte, les annonces sont retirées et les données personnelles supprimées, à l'exception de ce que nous devons garder pour une obligation légale ou pour un litige en cours. La trace de votre acceptation des conditions, qui ne contient que votre compte, une date et un numéro de version, est conservée pour la durée de prescription applicable.",
      },
      { kind: "h3", text: "Vos droits" },
      {
        kind: "p",
        text:
          "Vous pouvez demander à consulter les données que nous détenons sur vous, à les faire corriger, ou à les faire supprimer avec votre compte. La demande se fait depuis la messagerie du site, qui garantit que c'est bien vous qui la formulez. Nous répondons dans un délai raisonnable, et nous vous disons ce qui a été fait.",
      },
    ],
  },
  {
    id: "arnaque",
    title: "3. Arnaque et contenu non sain",
    blocks: [
      {
        kind: "p",
        text:
          "Un site de location vit de la confiance qu'on lui accorde. Une seule arnaque laissée passer coûte plus cher que cent annonces refusées à tort. Les règles qui suivent sont donc appliquées sans négociation.",
      },
      { kind: "h3", text: "Ce qui est interdit" },
      {
        kind: "ul",
        items: [
          "Publier un bien que vous ne possédez pas, ou dont vous n'avez pas le droit de disposer.",
          "Utiliser la photo d'un bien qui n'est pas le vôtre, ou une photo trouvée ailleurs.",
          "Annoncer un prix qui n'est pas celui que vous pratiquez, ou dissimuler des frais qui s'ajoutent.",
          "Réclamer un paiement, un acompte ou des frais de dossier avant que l'équipe n'ait vérifié la disponibilité et organisé la mise en relation.",
          "Proposer de poursuivre l'échange ailleurs pour éviter cette vérification.",
          "Se faire passer pour quelqu'un d'autre, ou pour BINOGOYA.",
          "Publier un contenu violent, sexuel, haineux, ou visant une personne en particulier.",
          "Harceler, insulter ou menacer, dans un message comme dans une annonce.",
          "Utiliser la messagerie pour du démarchage ou de la publicité.",
          "Ouvrir plusieurs comptes pour contourner une sanction.",
        ],
      },
      { kind: "h3", text: "Ce qui arrive ensuite" },
      {
        kind: "p",
        text:
          "Les sanctions sont graduées selon la gravité et la répétition. Une arnaque avérée ne passe pas par les premières marches : elle va directement à la fermeture du compte.",
      },
      {
        kind: "ol",
        items: [
          "L'annonce ou le message est retiré, et son auteur averti de ce qui a été retiré et pourquoi.",
          "Le compte est suspendu le temps de l'examen. Les demandes en cours sont gelées, et les clients concernés prévenus.",
          "Le compte est fermé définitivement. Le numéro de téléphone associé ne permet pas d'en ouvrir un nouveau.",
          "Lorsque les faits relèvent de la loi, ils sont transmis aux autorités compétentes avec les éléments en notre possession.",
        ],
      },
      { kind: "h3", text: "Signaler" },
      {
        kind: "p",
        text:
          "Chaque message peut être signalé depuis la conversation où il se trouve. Une annonce douteuse se signale en écrivant à l'équipe par la messagerie du site. Un signalement est lu par une personne, pas traité par un automate, et nous ne révélons jamais à la personne visée qui l'a signalée. Signaler de mauvaise foi, pour nuire à un concurrent par exemple, est une faute de même nature que celles listées plus haut.",
      },
    ],
  },
  {
    id: "responsabilite",
    title: "4. Responsabilité",
    blocks: [
      { kind: "h3", text: "Ce dont BINOGOYA répond" },
      {
        kind: "ul",
        items: [
          "La tenue du site et la sécurité des comptes.",
          "La lecture de chaque annonce avant sa publication.",
          "La vérification de la disponibilité auprès du fournisseur avant toute mise en relation.",
          "La confidentialité de vos coordonnées jusqu'à cette mise en relation.",
          "L'examen des signalements qui nous parviennent.",
        ],
      },
      { kind: "h3", text: "Ce dont BINOGOYA ne répond pas" },
      {
        kind: "p",
        text:
          "BINOGOYA n'est propriétaire d'aucun des biens proposés, n'est pas partie au contrat de location, et ne perçoit rien sur ce contrat. Le contrat se forme entre le fournisseur et le client, et c'est entre eux qu'il s'exécute.",
      },
      {
        kind: "p",
        text:
          "Une annonce lue par l'équipe n'est pas une annonce garantie. La modération écarte ce qui est manifestement faux, incomplet ou interdit. Elle ne se déplace pas chez le fournisseur pour inspecter le bien, et elle ne peut pas savoir ce qui se passera le jour de la remise.",
      },
      { kind: "h3", text: "Ce dont chacun répond" },
      {
        kind: "ul",
        items: [
          "Le fournisseur répond de l'existence du bien, de son état, de sa conformité à ce qui est annoncé, et de sa disponibilité aux dates convenues.",
          "Le client répond de l'usage qu'il fait du bien, de sa restitution dans l'état où il l'a reçu, et du respect de ce qui a été convenu.",
          "Chacun répond de l'exactitude des informations qu'il donne, et de la licéité de ce qu'il publie.",
        ],
      },
      { kind: "h3", text: "Ce que nous recommandons" },
      {
        kind: "ul",
        items: [
          "Constater l'état du bien ensemble, à la remise et au retour, photos à l'appui.",
          "Se mettre d'accord par écrit sur le prix total, la durée, la caution et ce qu'elle couvre.",
          "Garder les échanges dans la messagerie du site : en cas de litige, ce sont les seuls éléments que nous pouvons produire.",
        ],
      },
      { kind: "h3", text: "En cas de litige" },
      {
        kind: "p",
        text:
          "L'équipe peut être saisie et elle examine. Elle n'est pas un tribunal et ne tranche pas un différend contractuel. Ce qu'elle peut faire : retirer une annonce, suspendre ou fermer un compte, fournir à chaque partie les éléments la concernant, et transmettre aux autorités ce qui relève d'elles.",
      },
    ],
  },
  {
    id: "autres",
    title: "5. Autres",
    blocks: [
      { kind: "h3", text: "Accès au service" },
      {
        kind: "ul",
        items: [
          "L'inscription est réservée aux personnes de dix-huit ans révolus.",
          "Un compte par personne. Un compte fermé pour arnaque ne se rouvre pas sous un autre numéro.",
          "Vous êtes responsable de votre mot de passe et de ce qui se fait depuis votre compte.",
        ],
      },
      { kind: "h3", text: "Vos contenus" },
      {
        kind: "p",
        text:
          "Ce que vous publiez reste à vous. Vous nous autorisez simplement à l'afficher sur le site et dans les résultats de recherche tant que votre annonce est en ligne, et à en produire des versions redimensionnées pour qu'elles s'affichent vite sur un téléphone. Cette autorisation cesse quand l'annonce est retirée.",
      },
      { kind: "h3", text: "Modification des conditions" },
      {
        kind: "p",
        text:
          "Ce texte évoluera. Chaque version porte une date, visible en haut de cette page. Lorsque le texte change, la date change avec lui, et c'est la nouvelle version qui est présentée à l'inscription. Votre acceptation précédente reste enregistrée telle quelle, avec la version qu'elle visait : nous ne réécrivons pas ce que vous avez accepté.",
      },
      { kind: "h3", text: "Fermeture du compte" },
      {
        kind: "p",
        text:
          "Vous pouvez demander la fermeture de votre compte à tout moment depuis la messagerie du site. Nous pouvons de notre côté fermer un compte pour les motifs énoncés à la section 3, ou en cas d'inactivité prolongée après vous en avoir informé.",
      },
      { kind: "h3", text: "Droit applicable" },
      {
        kind: "p",
        text:
          "Ces conditions sont soumises au droit burkinabè. En cas de différend qui n'aurait pas trouvé de solution amiable, les tribunaux compétents de Ouagadougou sont saisis.",
      },
      { kind: "h3", text: "Nous écrire" },
      {
        kind: "p",
        text:
          "Pour une question sur ces conditions, un signalement, une demande d'accès ou de suppression de vos données, écrivez à l'équipe depuis la messagerie du site. C'est le canal qui nous permet de vérifier que la demande vient bien de vous.",
      },
    ],
  },
];
