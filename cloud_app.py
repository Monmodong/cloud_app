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
DASHBOARD_HTML = """<!DOCTYPE html>
<html><head><title>SCADA Live Dashboard</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0f172a;color:#e2e8f0;font-family:'Segoe UI',sans-serif;padding:20px}
h1{font-size:22px;margin-bottom:16px;color:#38bdf8}
h1 span{font-size:13px;color:#94a3b8;font-weight:400}
#status{padding:6px 14px;border-radius:6px;display:inline-block;font-size:13px;margin-bottom:20px}
.connected{background:#065f46;color:#6ee7b7}
.disconnected{background:#7f1d1d;color:#fca5a5}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
.card{background:#1e293b;border-radius:10px;padding:14px;border-left:4px solid #334155}
.card h3{font-size:14px;color:#94a3b8;margin-bottom:8px}
.card .val{font-size:20px;font-weight:700}
.card .sub{font-size:12px;color:#64748b;margin-top:4px}
.ok{color:#4ade80} .warn{color:#fbbf24} .bad{color:#f87171} .dim{color:#64748b}
.tripped{border-left-color:#ef4444!important;background:#1f1315}
.hv-row{display:flex;gap:20px;margin-bottom:20px;flex-wrap:wrap}
.hv-box{background:#1e293b;border-radius:10px;padding:12px 18px;border-left:4px solid #38bdf8}
.hv-box .lbl{font-size:12px;color:#94a3b8}
.hv-box .val{font-size:18px;font-weight:700}
</style></head><body>
<h1>SCADA Live <span id="ts">waiting...</span></h1>
<div id="status" class="disconnected">Connecting to server...</div>
<div id="hv" class="hv-row"></div>
<div id="feeders" class="grid"><p style="color:#64748b">Awaiting data...</p></div>
<script>
let lastData = null;
async function poll(){
    try{
        const r=await fetch("/data");
        if(!r.ok)throw Error(r.status);
        const d=await r.json();
        if(JSON.stringify(d)===JSON.stringify(lastData))return;
        lastData=d;
        const data=d.data||{};
        document.getElementById("ts").textContent=new Date().toLocaleTimeString();
        document.getElementById("status").className="connected";
        document.getElementById("status").textContent="Live";
        let hvHtml="";
        for(const[sid,v]of Object.entries(data.hv69kv||{})){
            const c=v?.kv69?"ok":"dim";
            hvHtml+='<div class="hv-box"><div class="lbl">'+sid.toUpperCase()+'</div><div class="val '+c+'">'+(v?.kv69||0).toFixed(1)+' kV</div><div class="lbl">'+(v?.hz||0).toFixed(2)+' Hz</div></div>';
        }
        document.getElementById("hv").innerHTML=hvHtml;
        let html="";
        for(const[fid,r]of Object.entries(data.readings||{})){
            const trp=r.tripped?"tripped":"";
            const vc=r.has_voltage?(!r.has_current?"warn":"ok"):"dim";
            html+='<div class="card '+trp+'"><h3>'+fid.toUpperCase()+'</h3>';
            html+='<div class="val '+vc+'">'+(r.kv||0).toFixed(2)+' kV</div>';
            html+='<div class="sub">'+(r.kw||0).toFixed(1)+' kW '+(r.a||0).toFixed(1)+' A PF '+(r.pf||0).toFixed(3)+'</div></div>';
        }
        document.getElementById("feeders").innerHTML=html||'<p style="color:#64748b">No feeder data</p>';
    }catch(e){
        document.getElementById("status").className="disconnected";
        document.getElementById("status").textContent="Offline";
    }
}
setInterval(poll,2000);poll();
</script></body></html>"""

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
            self.wfile.write(DASHBOARD_HTML.encode())
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
