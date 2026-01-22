# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# --- 讀取設定檔 ---
CONFIG_FILE = "config.txt"

def load_config_txt():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("=== StandX Bot 設定檔 ===\nJWT=貼上你的JWT\nSECRET=貼上你的私鑰\nSYMBOL=BTC-USD\nQTY=0.01\nTARGET_BPS=8\n")
        print(f"已產生 {CONFIG_FILE}，請填寫後重開。")
        input("按任意鍵退出..."); sys.exit()
    conf = {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip().replace(",", "").replace(" ", "")
    return conf

CONFIG = load_config_txt()

class StandXBot:
    def __init__(self):
        self.base_url = "https://perps.standx.com"
        self.ws_url = "wss://perps.standx.com/ws-stream/v1"
        self.mid_price = 0.0
        # 私鑰格式校正
        pk = CONFIG["SECRET"][2:] if CONFIG["SECRET"].startswith("0x") else CONFIG["SECRET"]
        self.signer = SigningKey(pk, encoder=HexEncoder)
        self.headers = {"Authorization": f"Bearer {CONFIG['JWT']}", "Content-Type": "application/json"}
        self.start_ws()

    def start_ws(self):
        def on_msg(ws, msg):
            d = json.loads(msg).get("data", {})
            if "mid_price" in d: self.mid_price = float(d["mid_price"])
        def run():
            ws = websocket.WebSocketApp(self.ws_url, 
                on_open=lambda ws: ws.send(json.dumps({"subscribe": {"channel": "price", "symbol": CONFIG["SYMBOL"]}})),
                on_message=on_msg)
            ws.run_forever()
        threading.Thread(target=run, daemon=True).start()

    def sign(self, body):
        rid, ts = str(uuid.uuid4()), str(int(time.time() * 1000))
        msg = f"v1,{rid},{ts},{body}"
        sig = base64.b64encode(self.signer.sign(msg.encode()).signature).decode()
        return {"x-request-sign-version": "v1", "x-request-id": rid, "x-request-timestamp": ts, "x-request-signature": sig}

    def place_order(self, side, price):
        path = "/api/v1/orders"
        # 價格精確到 0.5 (StandX BTC 規範)
        px = str(round(price * 2) / 2)
        data = {"symbol": CONFIG["SYMBOL"], "side": side, "type": "LIMIT", "price": px, "qty": str(CONFIG["QTY"])}
        body = json.dumps(data)
        try:
            res = requests.post(self.base_url + path, data=body, headers={**self.headers, **self.sign(body)}, timeout=5)
            if res.status_code == 401: return "JWT 過期或無效"
            if res.status_code == 400: return f"參數錯誤: {res.text}"
            return res.json() if res.text else "伺服器回傳空值 (請檢查餘額)"
        except Exception as e:
            return f"連線錯誤: {e}"

    def run_trading(self):
        print(">>> 機器人啟動，正在嘗試掛單...")
        while True:
            if self.mid_price == 0:
                time.sleep(1); continue
            
            gap = self.mid_price * (int(CONFIG.get("TARGET_BPS", 8)) / 10000)
            bid, ask = self.mid_price - gap, self.mid_price + gap

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 市價: {self.mid_price}")
            print(f"買單結果: {self.place_order('BUY', bid)}")
            print(f"賣單結果: {self.place_order('SELL', ask)}")
