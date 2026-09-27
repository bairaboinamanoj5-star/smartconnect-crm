from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(role):
    """Restrict a route to a specific role, e.g. @role_required('admin')"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role != role:
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator
