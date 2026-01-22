# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# --- 1. 設定檔管理 ---
CONFIG_FILE = "config.txt"

def load_config_txt():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("=== StandX Bot 設定檔 ===\n")
            f.write("JWT=請貼上你的JWT\n")
            f.write("SECRET=請貼上你的私鑰\n")
            f.write("SYMBOL=BTC-USD\n")
            f.write("QTY=0.01\n")
            f.write("TARGET_BPS=8\n")
            f.write("MIN_BPS=7\n")
            f.write("MAX_BPS=10\n")
        print(f"已產生 {CONFIG_FILE}，請填寫後重開。")
        input("按任意鍵退出..."); sys.exit()

    conf = {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip().replace(",", "").replace(" ", "")

    def safe_int(key, default):
        raw = conf.get(key, str(default))
        num = "".join(filter(str.isdigit, raw))
        return int(num) if num else default

    return {
        "JWT": conf.get("JWT", ""),
        "SECRET": conf.get("SECRET", ""),
        "SYMBOL": conf.get("SYMBOL", "BTC-USD"),
        "QTY": conf.get("QTY", "0.01"),
        "TARGET_BPS": safe_int("TARGET_BPS", 8)
    }

CONFIG = load_config_txt()

# --- 2. 交易核心邏輯 ---
class StandXBot:
    def __init__(self):
        self.base_url = "https://perps.standx.com"
        self.ws_url = "wss://perps.standx.com/ws-stream/v1"
        self.mid_price = 0.0
        pk = CONFIG["SECRET"][2:] if CONFIG["SECRET"].startswith("0x") else CONFIG["SECRET"]
        self.signer = SigningKey(pk, encoder=HexEncoder)
        self.headers = {"Authorization": f"Bearer {CONFIG['JWT']}", "Content-Type": "application/json"}
        self.start_ws()

    def start_ws(self):
        def on_msg(ws, msg):
            data = json.loads(msg).get("data", {})
            if "mid_price" in data: self.mid_price = float(data["mid_price"])
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
        order_data = {
            "symbol": CONFIG["SYMBOL"],
            "side": side,
            "type": "LIMIT",
            "price": str(price),
            "qty": CONFIG["QTY"]
        }
        body = json.dumps(order_data)
        try:
            res = requests.post(self.base_url + path, data=body, headers={**self.headers, **self.sign(body)}, timeout=3)
            return res.json()
        except Exception as e:
            return {"error": str(e)}

    def run_trading(self):
        print(f">>> 啟動自動掛單 (目標: {CONFIG['SYMBOL']})")
        while True:
            if self.mid_price == 0:
                time.sleep(1); continue
            
            # 計算買賣價格 (根據 BPS)
            spread = self.mid_price * (CONFIG["TARGET_BPS"] / 10000)
            bid_px = round(self.mid_price - spread, 2)
            ask_px = round(self.mid_price + spread, 2)

            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"--- StandX 交易中 --- {datetime.now().strftime('%H:%M:%S')}")
            print(f"當前市價: {self.mid_price:,.2f}")
            print(f"嘗試掛單: 買入 {bid_px} | 賣出 {ask_px}")
            
            # 送出訂單
            r_bid = self
