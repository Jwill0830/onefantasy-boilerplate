"""
Route blueprints initialization.
"""
from .auth import auth_bp
from .leagues import leagues_bp
from .drafts import drafts_bp
from .teams import teams_bp
from .players import players_bp
from .waivers import waivers_bp
from .trades import trades_bp
from .matchups import matchups_bp
from .chat import chat_bp
from .admin import admin_bp

__all__ = [
    'auth_bp',
    'leagues_bp', 
    'drafts_bp',
    'teams_bp',
    'players_bp',
    'waivers_bp',
    'trades_bp',
    'matchups_bp',
    'chat_bp',
    'admin_bp'
]