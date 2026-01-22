# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# --- 1. 設定檔管理 ---
def load_config_txt():
    conf_path = "config.txt"
    if not os.path.exists(conf_path):
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write("JWT_TOKEN=你的JWT\nPRIVATE_KEY_HEX=你的私鑰\nSYMBOL=BTC-USD\nBASE_URL=https://perps.standx.com\nORDER_QTY=0.05\nTARGET_BPS=8\nREFRESH_RATE=0.5\n")
        print("已產生 config.txt，請填寫後重開。")
        input(); sys.exit()

    conf = {}
    with open(conf_path, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip().replace('"', '')
    return conf

C = load_config_txt()

class StandXBot:
    def __init__(self):
        # 修正：根據實測，下單路徑應為 /api/v1/private/order
        self.base_url = C.get("BASE_URL", "https://perps.standx.com").rstrip('/')
        self.ws_url = "wss://perps.standx.com/ws-stream/v1"
        self.mid_price = 0.0
        
        pk = C.get("PRIVATE_KEY_HEX", "")
        if pk.startswith("0x"): pk = pk[2:]
        self.signer = SigningKey(pk, encoder=HexEncoder)
        self.headers = {
            "Authorization": f"Bearer {C.get('JWT_TOKEN', '')}",
            "Content-Type": "application/json"
        }
        self.start_ws()

    def start_ws(self):
        def on_msg(ws, msg):
            try:
                d = json.loads(msg).get("data", {})
                if "mid_price" in d: self.mid_price = float(d["mid_price"])
            except: pass
        def run():
            ws = websocket.WebSocketApp(self.ws_url, 
                on_open=lambda ws: ws.send(json.dumps({"subscribe": {"channel": "price", "symbol": C.get("SYMBOL", "BTC-USD")}})),
                on_message=on_msg)
            ws.run_forever()
        threading.Thread(target=run, daemon=True).start()

    def sign(self, body):
        rid, ts = str(uuid.uuid4()), str(int(time.time() * 1000))
        # 簽名格式校準
        msg = f"v1,{rid},{ts},{body}"
        sig = base64.b64encode(self.signer.sign(msg.encode()).signature).decode()
        return {"x-request-sign-version": "v1", "x-request-id": rid, "x-request-timestamp": ts, "x-request-signature": sig}

    def place_order(self, side, price):
        # 嘗試 StandX 最常見的兩個下單端點
        endpoints = ["/api/v1/orders", "/api/v1/private/order"]
        
        # 價格格式校準：BTC 必須為整數或 .5 (例如 90098)
        px_str = str(int(round(price)))
        data = {
            "symbol": C.get("SYMBOL", "BTC-USD"),
            "side": side,
            "type": "LIMIT",
            "price": px_str,
            "qty": str(C.get("ORDER_QTY", "0.05"))
        }
        body = json.dumps(data, separators=(',', ':'))
        
        last_err = "404"
        for path in endpoints:
            try:
                url = self.base_url + path
                res = requests.post(url, data=body, headers={**self.headers, **self.sign(
