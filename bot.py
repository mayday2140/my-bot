# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# --- 1. 設定檔讀取 (精確保留你的命名) ---
CONFIG_FILE = "config.txt"

def load_config_txt():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("JWT_TOKEN=你的JWT\nPRIVATE_KEY_HEX=你的私鑰\nSYMBOL=BTC-USD\nBASE_URL=https://perps.standx.com\nORDER_QTY=0.1\nTARGET_BPS=8\nMIN_BPS=6\nMAX_BPS=10\nREFRESH_RATE=0.5\n")
        print("已產生 config.txt，請填寫後重開。")
        input(); sys.exit()

    conf = {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip().replace(",", "").replace('"', '')
    
    return {
        "JWT_TOKEN": conf.get("JWT_TOKEN", ""),
        "PRIVATE_KEY_HEX": conf.get("PRIVATE_KEY_HEX", ""),
        "SYMBOL": conf.get("SYMBOL", "BTC-USD"),
        "BASE_URL": conf.get("BASE_URL", "https://perps.standx.com"),
        "ORDER_QTY": conf.get("ORDER_QTY", "0.1"),
        "TARGET_BPS": int(conf.get("TARGET_BPS", 8)),
        "MIN_BPS": int(conf.get("MIN_BPS", 6)),
        "MAX_BPS": int(conf.get("MAX_BPS", 10)),
        "REFRESH_RATE": float(conf.get("REFRESH_RATE", 0.5))
    }

CONFIG = load_config_txt()

# --- 2. 交易核心 ---
class StandXBot:
    def __init__(self):
        self.base_url = CONFIG["BASE_URL"]
        self.ws_url = "wss://perps.standx.com/ws-stream/v1"
        self.mid_price = 0.0
        
        pk = CONFIG["PRIVATE_KEY_HEX"]
        if pk.startswith("0x"): pk = pk[2:]
        self.signer = SigningKey(pk, encoder=HexEncoder)
        self.headers = {"Authorization": f"Bearer {CONFIG['JWT_TOKEN']}", "Content-Type": "application/json"}
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
        px = str(round(price * 2) / 2) # BTC 步進 0.5
        data = {"symbol": CONFIG["SYMBOL"], "side": side, "type": "LIMIT", "price": px, "qty": str(CONFIG["ORDER_QTY"])}
        body = json.dumps(data)
        try:
            res = requests.post(self.base_url + path, data=body, headers={**self.headers, **self.sign(body)}, timeout=5)
            return "OK ✅" if res.status_code == 200 else f"Fail({res.status_code})"
        except: return "Error"

    def run(self):
        print(f">>> 啟動頻率: {CONFIG['REFRESH_RATE']}s")
        while True:
            if self.mid_price == 0:
                time.sleep(0.1); continue
            
            gap = self.mid_price * (CONFIG["TARGET_BPS"] / 10000)
            bid, ask = self.mid_price - gap, self.mid_price + gap

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Px: {self.mid_price} | Buy: {self.place_order('BUY', bid)} | Sell: {self.place_order('SELL', ask)}")
            time.sleep(CONFIG["REFRESH_RATE"])

if __name__ == "__main__":
    try:
        StandXBot().run()
    except Exception as e:
        print(f"錯誤: {e}"); input()
