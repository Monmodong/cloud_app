#!/usr/bin/env python3
"""
Web Dashboard for SCADA Live — deploy on Render.com free tier.
Subscribes to HiveMQ Cloud via MQTT and serves a live web page.
"""
import json
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── MQTT Config (same as scada_reader.py) ──────────────────────────────────
MQTT_BROKER = "5bcedcadf484478a9275d125b589d2d0.s1.eu.hivemq.cloud"
MQTT_PORT   = 8883
MQTT_USER   = "scada"
MQTT_PASS   = "Scada@123"
MQTT_TOPIC  = "scada/readings"

latest: dict = {}

# ── MQTT Listener ──────────────────────────────────────────────────────────
def _on_message(client, userdata, msg):
    global latest
    try:
        latest = json.loads(msg.payload.decode())
    except Exception:
        pass

def _mqtt_start():
    c = mqtt.Client(client_id="cloud_dashboard")
    c.tls_set()
    c.username_pw_set(MQTT_USER, MQTT_PASS)
    c.on_message = _on_message
    c.connect(MQTT_BROKER, MQTT_PORT)
    c.subscribe(MQTT_TOPIC)
    c.loop_forever()

# ── HTML Dashboard ─────────────────────────────────────────────────────────
def _get_html():
    path = os.path.join(_SCRIPT_DIR, "sld_dashboard.html")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return "<h1>sld_dashboard.html not found</h1>"

# ── HTTP Server ────────────────────────────────────────────────────────────
class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(latest).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(_get_html().encode())
    def log_message(self, *a): pass

def main():
    port = int(os.environ.get("PORT", 8080))
    t = threading.Thread(target=_mqtt_start, daemon=True)
    t.start()
    s = HTTPServer(("0.0.0.0", port), _Handler)
    print("Dashboard ready on port", port)
    s.serve_forever()

if __name__ == "__main__":
    main()
