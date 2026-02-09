"""Token store para auth admin (evita cookies bloqueadas por Tracking Prevention)."""
_admin_tokens = set()


def add_token(token):
    _admin_tokens.add(token)


def remove_token(token):
    _admin_tokens.discard(token)


def has_token(token):
    return token in _admin_tokens
