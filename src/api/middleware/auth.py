from flask import request, jsonify
import functools

def local_only(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if request.remote_addr not in ['127.0.0.1', '::1']:
            return jsonify({"code": 403, "msg": "Forbidden: Private API only accessible from localhost"}), 403
        return func(*args, **kwargs)
    return wrapper