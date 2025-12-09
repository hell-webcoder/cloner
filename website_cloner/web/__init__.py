"""
Web module for the website cloner.

Provides a Flask-based web interface for controlling the website cloner.
"""

from .app import create_app

__all__ = ["create_app"]
