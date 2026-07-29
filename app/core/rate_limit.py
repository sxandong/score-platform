"""速率限制模块"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def init_limiter(app):
    app.state.limiter = limiter