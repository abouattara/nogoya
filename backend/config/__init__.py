# Ensure the Celery app is loaded when Django starts so shared_task uses it.
from .celery import app as celery_app

__all__ = ("celery_app",)


def _install_pymysql_if_needed():
    """Laisser PyMySQL tenir le rôle de mysqlclient si celui-ci manque.

    Django veut `mysqlclient`, qui se compile à l'installation. Sur un
    hébergement mutualisé sans en-têtes de développement, le `pip install`
    échoue ; PyMySQL est en Python pur et s'installe partout. Il faut alors
    lui faire annoncer une version que Django accepte : le contrôle porte
    sur `version_info`, et Django 6 exige au moins 2.2.1. À garder aligné
    lors d'une montée de version majeure de Django — le message d'erreur
    est trompeur, il compare `version_info` mais affiche `__version__`.

    Cela vit ici — et non dans `passenger_wsgi.py` — parce que `migrate` et
    `collectstatic` passent par `manage.py`, qui ne charge jamais le fichier
    de Passenger. Sur PostgreSQL, les deux imports échouent et la fonction
    ne fait rien.
    """
    try:
        import MySQLdb  # noqa: F401
    except ImportError:
        try:
            import pymysql
        except ImportError:
            return
        pymysql.version_info = (2, 2, 1, "final", 0)
        pymysql.install_as_MySQLdb()


_install_pymysql_if_needed()
