# Déploiement sur cPanel (AshuraHosting)

Panneau : https://c6.my-control-panel.com/

Ce document couvre un hébergement **mutualisé**. Pour un VPS ou une
plateforme conteneurisée, voir [DEPLOYMENT.md](DEPLOYMENT.md) : l'approche y
est différente (Docker, Redis managé, stockage objet).

---

## 0. La vérification qui décide de tout : la version de MariaDB

Votre hébergement fournit **Setup Python App**, **Setup Node.js App** et
**phpMyAdmin** — donc MySQL/MariaDB, pas PostgreSQL. Le portage est possible
(rien dans le code n'est propre à PostgreSQL), à une condition :

> **Django 6 exige MariaDB ≥ 10.6 ou MySQL ≥ 8.0.11.**
> En dessous, il refuse de démarrer — ce n'est pas contournable
> proprement.

Ouvrez phpMyAdmin : la version du serveur s'affiche sur la page d'accueil,
encadré « Serveur de base de données ». Beaucoup d'hébergements mutualisés
tournent encore en 10.3 ou 10.4.

| Version constatée | Marche à suivre |
|---|---|
| MariaDB ≥ 10.6 / MySQL ≥ 8.0.11 | Continuer avec ce document. |
| Plus ancienne | Demander la mise à niveau au support AshuraHosting — c'est courant et souvent immédiat. À défaut, rétrograder le projet en Django 5.2 LTS (MariaDB ≥ 10.5) : un changement réel, à tester. |

Notez aussi la **version de Python** proposée (3.10 minimum ; 3.12 ou 3.13
de préférence) et si vous avez un accès **Terminal** ou **SSH** — sinon les
commandes se lancent depuis les boutons de l'interface Python App.

## Ce qui change par rapport à l'architecture de référence

Un mutualisé ne fournit ni Redis, ni Docker, ni processus long. Le profil
`config/settings/cpanel.py` remplace chacun de ces éléments :

| Composant | Architecture de référence | Sur cPanel |
|---|---|---|
| Serveur | daphne (ASGI) | Passenger (WSGI), via `passenger_wsgi.py` |
| Cache | Redis | Table en base (`createcachetable`) |
| Tâches | Worker Celery | Exécutées dans la requête (~1 s pour une photo) |
| Médias | S3 / Cloudflare R2 | Disque du compte (persistant ici) |
| Base | PostgreSQL | MySQL / MariaDB |
| WebSockets | — | — (le chat fonctionne déjà par polling) |

**Le cache en base n'est pas un détail de confort.** La déduplication des
vues et les quotas de débit s'appuient dessus. Avec un cache en mémoire,
chaque worker Passenger aurait le sien et un quota de 20 connexions/minute
deviendrait 20 × le nombre de workers.

**Le fuseau horaire passe en UTC sur MySQL, et ce n'est pas arbitraire.**
Les graphiques du tableau de bord regroupent par jour (`TruncDate`). Dès que
le fuseau de Django diffère de celui de la connexion, Django écrit
`CONVERT_TZ(col, 'UTC', 'Africa/Ouagadougou')` — qui renvoie **NULL** tant
que les tables de fuseaux ne sont pas chargées dans MySQL
(`mysql_tzinfo_to_sql`), ce qu'un mutualisé ne permet jamais. Les statistiques
seraient vides, sans la moindre erreur dans les journaux. Le Burkina Faso
étant à UTC+0 toute l'année, sans heure d'été, basculer en UTC ne décale
aucune heure affichée et supprime l'appel. C'est automatique dès que l'URL
de base commence par `mysql://`.

---

## 1. Base de données

cPanel → *MySQL Databases* :

1. créer une base, par exemple `moncompte_nogoya` ;
2. créer un utilisateur avec un mot de passe long et généré ;
3. lui donner **tous les privilèges** sur cette base.

cPanel préfixe les noms par votre identifiant de compte : notez les noms
exacts affichés, ce sont eux qui vont dans l'URL.

```
DATABASE_URL=mysql://UTILISATEUR:MOTDEPASSE@127.0.0.1:3306/BASE
```

Si le mot de passe contient `@`, `:`, `/` ou `#`, encodez-le
(`monmotdepasse@1` → `monmotdepasse%401`), sinon l'URL est mal découpée.

Le profil `cpanel.py` détecte `mysql://` et applique automatiquement :
`utf8mb4`, le mode SQL strict (sans lui, MySQL tronque silencieusement une
valeur trop longue au lieu de refuser l'écriture) et le passage en UTC
expliqué plus haut.

### Pilote

`mysqlclient` est le pilote recommandé, mais il se compile. Si
`pip install` échoue faute d'en-têtes de développement :

```bash
pip install PyMySQL
```

Le projet bascule tout seul (`config/__init__.py` installe PyMySQL sous le
nom attendu par Django). Rien d'autre à changer.

## 2. Récupérer le code

Le plus simple, puisque le projet est sur GitHub : cPanel → **Git Version
Control** → *Create* → URL `https://github.com/abouattara/nogoya.git`,
chemin par exemple `/home/UTILISATEUR/nogoya`.

Les mises à jour suivantes se font par *Manage* → *Update from Remote*,
puis un redémarrage de l'application (§ 6).

Sans Git dans cPanel : déposer une archive du dépôt via le Gestionnaire de
fichiers et l'extraire au même endroit.

---

## 3. Créer l'application Python

cPanel → **Setup Python App** → *Create Application* :

| Champ | Valeur |
|---|---|
| Python version | la plus récente proposée (≥ 3.10) |
| Application root | `nogoya/backend` |
| Application URL | le sous-domaine de l'API, par exemple `api.mondomaine.com` |
| Application startup file | `passenger_wsgi.py` |
| Application Entry point | `application` |

> ⚠️ **cPanel écrit son propre `passenger_wsgi.py` en créant l'application**,
> et écrase celui du projet. Son gabarit contient
> `wsgi = imp.load_source('wsgi', 'passenger_wsgi.py')`, c'est-à-dire un
> fichier qui se charge lui-même : toutes les URL répondent alors 500, et le
> terminal montre un `RecursionError`. **Après avoir créé l'application,
> restaurez le fichier du projet** (voir § 4).

Toujours dans cet écran, ajoutez les **variables d'environnement** :

```
DJANGO_SETTINGS_MODULE=config.settings.cpanel
DJANGO_SECRET_KEY=<50 caractères aléatoires — voir ci-dessous>
DJANGO_ALLOWED_HOSTS=api.mondomaine.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://api.mondomaine.com,https://mondomaine.com
CORS_ALLOWED_ORIGINS=https://mondomaine.com
FRONTEND_URL=https://mondomaine.com
DATABASE_URL=mysql://UTILISATEUR:MOTDEPASSE@127.0.0.1:3306/BASE
CELERY_TASK_ALWAYS_EAGER=True
```

Générer la clé secrète (sur votre machine, jamais dans un fichier versionné) :

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

> Ces variables peuvent aussi vivre dans un fichier `.env` placé à côté de
> `manage.py` : le projet le lit automatiquement. Le fichier est ignoré par
> git, il ne partira donc jamais sur GitHub. L'interface cPanel reste plus
> sûre — rien n'est écrit sur le disque.

---

## 4. Installer et initialiser

Ouvrez le **Terminal** cPanel (ou SSH). La commande d'activation de
l'environnement virtuel est affichée en haut de l'écran *Setup Python App* :
copiez-la telle quelle, elle ressemble à

```bash
source /home/UTILISATEUR/virtualenv/nogoya/backend/3.12/bin/activate && cd /home/UTILISATEUR/nogoya/backend
```

Puis :

D'abord, **restaurez le point d'entrée écrasé par cPanel** :

```bash
cd ~/nogoya/backend
head -3 passenger_wsgi.py     # s'il contient imp.load_source, c'est le gabarit
```

S'il faut le remplacer : `git checkout passenger_wsgi.py`, ou re-déposez le
fichier depuis le dépôt. Sans ça, l'application boucle sur elle-même.

```bash
pip install -r requirements/cpanel.txt
# Si mysqlclient échoue à se compiler :
#   pip install PyMySQL
python manage.py migrate
python manage.py createcachetable          # la table de cache, indispensable
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py seed_demo                 # facultatif : données de démonstration
```

Sans Terminal, l'écran *Setup Python App* propose un champ « Execute python
script » et un bouton « Run pip install » qui font la même chose.

---

## 5. Servir les fichiers médias

Les photos d'annonces sont servies directement par le serveur web (les
médias du chat, eux, passent par l'API qui vérifie l'appartenance à la
conversation — voir SECURITY.md).

Dans le dossier racine du sous-domaine de l'API, créez un lien vers le
dossier des médias :

```bash
ln -s /home/UTILISATEUR/nogoya/backend/media /home/UTILISATEUR/api.mondomaine.com/media
```

Si les liens symboliques sont refusés par l'hébergeur, définissez plutôt
`MEDIA_ROOT` directement dans le dossier du sous-domaine :

```
MEDIA_ROOT=/home/UTILISATEUR/api.mondomaine.com/media
```

Vérification : une image d'annonce doit s'afficher à
`https://api.mondomaine.com/media/products/<fichier>.jpg`.

---

## 6. Redémarrer après chaque modification

Passenger garde l'application en mémoire. Après un `git pull`, une
migration ou un changement de variable :

- bouton **Restart** dans *Setup Python App*, ou
- `touch /home/UTILISATEUR/nogoya/backend/tmp/restart.txt`

---

## 7. Frontend Next.js

**Le frontend ne peut pas être déposé tel quel dans `public_html`.** Les
pages sont rendues côté serveur et les routes `/api/auth/*` s'exécutent sur
un serveur Node : il n'existe pas d'export statique de ce projet. Toute
procédure qui consiste à téléverser un dossier `out/` échouera.

### Option A — Vercel (recommandée)

Next.js y est natif, l'offre gratuite suffit largement à un MVP, et les
mises à jour se font au `git push`.

1. Importer `abouattara/nogoya` sur vercel.com ;
2. *Root Directory* : `frontend` ;
3. variables d'environnement :
   ```
   NEXT_PUBLIC_API_URL=https://api.mondomaine.com
   API_URL=https://api.mondomaine.com
   ```
4. faire pointer `mondomaine.com` sur Vercel (les DNS restent gérables
   depuis cPanel).

L'API reste sur AshuraHosting. C'est la répartition la plus simple à
exploiter, et la moins susceptible de casser.

### Option B — Tout sur cPanel (Setup Node.js App)

Disponible sur cet hébergement. Deux réserves : la mémoire d'un compte
mutualisé est juste pour un serveur Next.js, et Passenger arrête le
processus après une période d'inactivité — la visite suivante est alors
lente.

#### Répartition des noms de domaine

| Application | Type | Application URL |
|---|---|---|
| Frontend Next.js | Node.js App | `binogoya.com` |
| API Django | Python App | `api.binogoya.com` |

Les deux ne peuvent pas partager un nom d'hôte : c'est la première erreur à
éviter.

#### Champs de l'écran « Create Application »

| Champ | Valeur |
|---|---|
| Node.js version | **22.x** ou 20.x — Next 16 exige ≥ 20.9.0, et la 18 proposée par défaut ne suffit pas |
| Application mode | **Production** — et non Development : ce champ pilote `NODE_ENV`, et un build de production doit tourner avec `NODE_ENV=production` |
| Application root | `nogoya-node` |
| Application URL | `binogoya.com` |
| Application startup file | `server.js` |

> Changer la version de Node change le chemin de l'environnement virtuel
> (`.../nogoya-node/18/` → `.../22/`). La commande d'activation affichée en
> haut de l'écran change donc aussi : reprenez-la après chaque bascule.

Variables d'environnement (bouton *ADD VARIABLE*) :

```
NEXT_PUBLIC_API_URL=https://api.binogoya.com
API_URL=https://api.binogoya.com
```

> Ces deux variables sont lues **au moment du build**, pas seulement à
> l'exécution : elles déterminent l'hôte autorisé pour les images
> (`next.config.ts`). Un changement impose de reconstruire.

#### Construire et déposer

`next build` consomme beaucoup de mémoire et dépasse souvent ce qu'autorise
un compte mutualisé. **Construisez sur votre machine**, puis n'envoyez que
le résultat :

```bash
# dans frontend/
NEXT_PUBLIC_API_URL=https://api.binogoya.com API_URL=https://api.binogoya.com npm run build
npm run deploy:pack
```

`deploy:pack` assemble le dossier `deploy/` et règle trois pièges que
`next build` laisse derrière lui :

| Piège | Ce que fait le script |
|---|---|
| `.next/static` et `public` ne sont pas copiés par Next | il les ajoute — sans eux, le site s'affiche **sans aucun style** |
| Le binaire natif de `sharp` correspond à la machine du build | il retire les variantes d'autres plateformes. Un build Windows embarque `@img/sharp-win32-x64`, inutilisable sous Linux : `/_next/image` renverrait 500 et **plus aucune photo ne s'afficherait** |
| La `package.json` recopiée liste *toutes* les dépendances | il la remplace par le strict nécessaire. Sinon un `npm install` sur le serveur — ou le bouton « Run NPM Install » — téléchargerait Playwright, Vitest et le reste : plus de 500 Mo |

Le dossier obtenu pèse **29 Mo** (1 523 fichiers), contre 504 Mo pour un
`node_modules` complet.

Compressez `deploy/` en `.zip`, déposez-le dans `nogoya-node` via le
Gestionnaire de fichiers, extrayez-le. Puis, dans le Terminal, environnement
Node activé :

```bash
cd ~/nogoya-node
npm install        # récupère le binaire Linux de sharp, quelques Mo
```

Enfin **Restart** dans *Setup Node.js App*.

L'arborescence finale doit être :

```
nogoya-node/
├── server.js          ← fichier de démarrage
├── node_modules/
├── package.json
├── .next/
│   └── static/        ← indispensable, sinon aucun style ne se charge
└── public/
```

#### Si vous préférez construire sur le serveur

Possible, à trois conditions.

**1. Activez l'environnement *Node*, pas celui de Python.** Les deux
coexistent sur le compte et leurs invites se ressemblent. Si le prompt
affiche `((backend:3.11))`, vous êtes dans l'environnement Python : `node`
y reste en version système et `next` est introuvable.

```bash
source ~/nodevenv/nogoya-node/22/bin/activate && cd ~/nogoya-node
node -v        # doit afficher v22.x — sinon rien de ce qui suit ne marchera
```

**2. Utilisez `npm install`, surtout pas `npm ci`.** Le `package-lock.json`
du dépôt est produit sous Windows, et npm n'y inscrit pas certaines
dépendances que la résolution Linux exige (`@emnapi/runtime`,
`@emnapi/core`, tirées des variantes wasm de `sharp` et de Tailwind).
`npm ci` échoue alors sur :

```
npm error `npm ci` can only install packages when your package.json and
npm error package-lock.json are in sync.
npm error Missing: @emnapi/runtime@1.11.3 from lock file
```

Ce n'est pas réparable depuis Windows : npm refuse d'ajouter ces entrées,
même avec `--os=linux --cpu=x64`. `npm install` résout l'arbre à neuf et
fonctionne.

**3. Surveillez la mémoire et les inodes.** `npm install` dépose 504 Mo et
26 578 fichiers — les mutualisés limitent souvent le *nombre* de fichiers
autant que l'espace.

```bash
cd ~/nogoya/frontend
npm install
NEXT_PUBLIC_API_URL=https://api.binogoya.com API_URL=https://api.binogoya.com npm run build
npm run deploy:pack
cp -r deploy/. ~/nogoya-node/
rm -rf ~/nogoya/frontend/node_modules   # libère les inodes
```

Un arrêt brutal pendant `npm run build` (« Killed », ou plus aucun message)
signifie que la limite mémoire est atteinte : repassez à la construction
locale.

> Construire sur le serveur a un avantage : le binaire natif de `sharp` est
> alors celui de Linux, et le `npm install` de l'étape précédente devient
> inutile.

## 8. Entretien

Une tâche planifiée (cPanel → *Cron Jobs*), une fois par jour :

```
15 3 * * * source /home/UTILISATEUR/virtualenv/nogoya/backend/3.12/bin/activate && cd /home/UTILISATEUR/nogoya/backend && python manage.py prune_media --delete
```

Elle supprime les fichiers que plus aucune ligne de la base ne référence
(uploads interrompus, médias de messages supprimés). Lancez-la d'abord
**sans** `--delete` pour voir ce qu'elle retirerait.

Sauvegardes : cPanel → *Backup Wizard* pour la base, et une copie du dossier
`media/` — les images d'annonces ne sont nulle part ailleurs tant que
`USE_S3` est désactivé.

---

## 9. Vérifications après mise en ligne

Dans cet ordre, en s'arrêtant à la première qui échoue :

| Vérification | Attendu |
|---|---|
| `https://api.mondomaine.com/healthz/` | `{"status": "ok"}` |
| `https://api.mondomaine.com/readyz/` | `database` et `cache` à `ok` |
| `https://api.mondomaine.com/admin/` | page de connexion correctement mise en forme (sinon : `collectstatic`) |
| `https://mondomaine.com` | l'accueil affiche des annonces |
| Inscription puis connexion | redirige vers `/compte` |
| Une image d'annonce | s'affiche (sinon : § 5) |
| Envoi d'un message avec photo | la vignette apparaît dans la conversation |

Si `/readyz/` renvoie `cache: error`, c'est que `createcachetable` n'a pas
été exécuté.

---

## Limites connues de cet hébergement

À savoir avant de s'engager sur du volume :

- **Le traitement d'image se fait dans la requête.** L'envoi d'une photo
  prend environ une seconde de plus. Acceptable pour un MVP ; au-delà, il
  faut un worker, donc un VPS.
- **Pas de stockage objet ni de CDN.** Les images sont servies par le
  serveur du compte. C'est le premier poste qui saturera si le trafic
  monte ; `USE_S3=True` plus les clés R2 suffisent à basculer, sans
  changement de code.
- **Quota disque.** Les médias grossissent en continu ; la tâche du § 8 les
  contient, elle ne les remplace pas.

## Ce qui a été vérifié, et ce qui ne l'a pas été

Pour que vous sachiez où porter votre attention au premier déploiement.

**Vérifié sur cette machine :**

- le profil `cpanel.py` se charge et produit la bonne configuration
  (cache en base, Celery synchrone, UTC sur MySQL, `utf8mb4`, mode strict) ;
- le repli automatique vers PyMySQL fonctionne quand `mysqlclient` manque ;
- aucune dépendance à PostgreSQL dans le code (ni `django.contrib.postgres`,
  ni type propriétaire) ;
- le DDL généré pour MySQL est correct : colonnes `json` natives, contraintes
  uniques et index bien en dessous de la limite de 3072 octets d'InnoDB ;
- le lookup JSON `contains` utilisé par les filtres par caractéristique est
  supporté par MariaDB avec Django 6 ;
- le build Next produit bien `.next/standalone/server.js`, qui se replace
  dans son propre dossier au démarrage (`process.chdir`) et écoute sur
  `PORT` — ce que Passenger fournit ;
- l'hôte de l'API figure dans les motifs d'images autorisés du build (sans
  quoi chaque photo d'annonce revenait en 400).

**Non vérifié, faute de serveur adéquat ici :** l'exécution réelle des
migrations et de la suite de tests sur MariaDB ≥ 10.6. La seule instance
disponible localement était une MariaDB 10.4, sous le minimum de Django 6 —
elle a d'ailleurs échoué exactement là où ce minimum existe pour l'éviter
(`INSERT … RETURNING`, apparu en 10.5).

Concrètement : lancez `python manage.py migrate` en premier et lisez sa
sortie avant toute autre chose. C'est là que se manifesterait une surprise.
