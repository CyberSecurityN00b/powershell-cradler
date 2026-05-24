import os
from flask import Flask, Response, abort, send_file

app = Flask(__name__)
_endpoint_registry = None

def init_app(endpoint_registry,):
    global _plugin_registry, _file_registry
    _endpoint_registry = endpoint_registry

@app.route("/<uid>", methods=["GET"])
def serve_resource(uid: str):
    if _endpoint_registry:
        payload_type, payload, content_type = _plugin_registry.get(uid)
        if payload is not None:
            if payload_type == "file":
                if payload:
                    if payload.exists:
                        return send_file(payload.path, as_attachment=False)
                abort(404)
            else:
                return Response(payload, content_type=content_type)
        
    abort(404)

@app.rout("/", methods=["GET"])
def index():
    return Response("", status=204)