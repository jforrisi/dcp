"""Ticker module for Wall Street style data display."""
from flask import Blueprint
from .router import bp

ticker = Blueprint('ticker', __name__)
ticker.register_blueprint(bp, url_prefix='/api/ticker')

__all__ = ['ticker']
