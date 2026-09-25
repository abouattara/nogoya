"""Point d'entrée Passenger (cPanel « Setup Python App »).

cPanel cherche ce fichier à la racine du dossier de l'application et y
attend une variable `application`. Il n'est utilisé que là : ailleurs, le
projet démarre par `config/wsgi.py` ou `config/asgi.py`.

Le dossier courant est ajouté au `sys.path` parce que Passenger démarre le
processus depuis un répertoire qui n'est pas forcément celui-ci — sans ça,
`import config` échoue avec un ModuleNotFoundError peu parlant.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Surchargeable depuis l'interface cPanel si besoin (variables d'environnement
# de l'application), mais c'est la bonne valeur par défaut sur un mutualisé.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.cpanel")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
