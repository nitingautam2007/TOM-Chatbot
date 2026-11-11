"""WSGI entrypoint for production servers.

Run from the backend directory with:

    gunicorn --config gunicorn.conf.py wsgi:app
"""

from api_server import app

application = app

__all__ = ["app", "application"]
