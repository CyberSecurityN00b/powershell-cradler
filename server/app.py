import os
from flask import Flask, Response, abort, send_file

app = Flask(__name__)
_endpoint_registry = None
_powershellcradle_termminal = None

def init_app(endpoint_registry,powershellcradle_terminal):
    global _endpoint_registry, _powershellcradle_termminal
    _endpoint_registry          = endpoint_registry
    _powershellcradle_termminal = powershellcradle_terminal

@app.route("/<uid>", methods=["GET"])
def serve_resource(uid: str):
    global _endpoint_registry, _powershellcradle_termminal
    if _endpoint_registry:
        payload_type, payload, content_type = _endpoint_registry.get(uid)
        if payload is not None:
            if payload_type == "file":
                if payload:
                    if payload.exists:
                        return send_file(payload.path, as_attachment=False)
                abort(404)
            else:
                return Response(payload, content_type=content_type)
        
    abort(404)

@app.route("/", methods=["GET"])
def index():
    return Response("", status=204)