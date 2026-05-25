import os
import logging

from flask import Flask, Response, abort, send_file, request
from core.models import CradleType

logging.getLogger('werkzeug').disabled=True
app = Flask(__name__)
_endpoint_registry = None
_powershellcradle_terminal = None

def _notification(notify_type: str, notify_text: str):
    _powershellcradle_terminal._notification(notify_type,notify_text)

def init_app(endpoint_registry,powershellcradle_terminal):
    global _endpoint_registry, _powershellcradle_terminal
    _endpoint_registry          = endpoint_registry
    _powershellcradle_terminal = powershellcradle_terminal


@app.route("/<uid>", methods=["GET"])
def serve_resource(uid: str):
    global _endpoint_registry, _powershellcradle_terminal
    if _endpoint_registry:
        cradle_type, payload, content_type = _endpoint_registry.generate_payload(uid)
        if payload is not None:
            if cradle_type == CradleType.File:
                if os.path.exists(payload):
                    _notification("<b><skyblue>[INFO]</skyblue></b>",f"{request.remote_addr} got '{payload}' via {uid}")
                    return send_file(payload, as_attachment=False)
                abort(404)
            elif cradle_type == CradleType.Plugin:
                return Response(payload, content_type=content_type)
            
    ## Commenting out below due to possible noise and "denial of service" if someone points a scanner at the port
    #_notification("<b><ansired>[WARN]</ansired></b>",f"{request.remote_addr} requested invalid uid {uid}, possible probing")
    abort(404)

@app.route("/<uid>", methods=["POST"])
def receive_notification(uid: str):
    global _endpoint_registry, _powershellcradle_terminal
    if _endpoint_registry:
        cradle_type, cradle_context, notification = _endpoint_registry.handle_notification(uid,request.remote_addr,request.get_json(force=True))
        if notification is not None:
            if cradle_type == CradleType.Notification:
                 _notification("<b><yellow>[NOTICE]</yellow></b>",notification)
    abort(404)

@app.route("/", methods=["GET"])
def index():
    return Response("", status=204)