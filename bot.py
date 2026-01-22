# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# --- 1. 設定檔讀取 (保留您的所有變數名) ---
CONFIG_FILE = "config.txt"

def load_config_txt():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("JWT_TOKEN=你的JWT\nPRIVATE_KEY_HEX=你的私鑰\nSYMBOL=BTC-USD\nBASE_URL=https://perps.standx.com\nORDER_QTY=0.05\nTARGET_BPS=8\nMIN_BPS=6\nMAX_BPS=10\nREFRESH_RATE=0.5\n")
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
        "BASE_URL": conf.get("BASE_URL", "https://perps.standx.com").rstrip('/'),
        "ORDER_QTY": conf.get("ORDER_QTY", "0.05"), # 根據您的截圖，建議設為 0.05
        "TARGET_BPS": int(conf.get("TARGET_BPS", 8)),
        "REFRESH_RATE": float(conf.get("REFRESH_RATE", 0.5))
    }

CONFIG = load_config_txt()

class StandXBot:
    def __init__(self):
        # 修正後的 URL：StandX 必須在 API 路徑前加上完整的前綴
        self.api_base = f"{CONFIG['BASE_URL']}/api/v1"
        self.ws_url = "wss://perps.standx.com/ws-stream/v1"
        self.mid_price = 0.0
        
        pk = CONFIG["PRIVATE_KEY_HEX"]
        if pk.startswith("0x"): pk = pk[2:]
        self.signer = SigningKey(pk, encoder=HexEncoder)
        self.headers = {
            "Authorization": f"Bearer {CONFIG['JWT_TOKEN']}", 
            "Content-Type": "application/json",
            "Accept": "application/json"
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
        url = f"{self.api_base}/orders"
        
        # 根據您的截圖修正：價格必須整數或 0.5 步進
        px = str(round(price)) 
        data = {
            "symbol": CONFIG["SYMBOL"],
            "side": side,
            "type": "LIMIT",
            "price": px,
            "qty": str(CONFIG["ORDER_QTY"])
        }
        body = json.dumps(data, separators=(',', ':'))
        
        try:
            res = requests.post(url, data=body, headers={**self.headers, **self.sign(body)}, timeout=5)
            if res.status_code == 200:
                return "成功 ✅"
            else:
                # 抓取 API 返回的錯誤訊息，方便排錯
                err_msg = res.json().get('message', res.text) if res.text else f"Status:{res.status_code}"
                return f"失敗 ({err_msg})"
        except Exception as e:
            return f"連線錯誤"

    def run(self):
        print(f"StandX 監控中，準備於網頁預掛單...")
        while True:
            if self.mid_price == 0:
                time.sleep(0.1); continue
            
            gap = self.mid_price * (CONFIG["TARGET_BPS"] / 10000)
            bid, ask = self.mid_price - gap, self.mid_price + gap

            res_b = self.place_order('BUY', bid)
            res_s = self.place_order('SELL', ask)
            
            now = datetime.now().strftime('%H:%M:%S')
            print(f"[{now}] 市價: {self.mid_price:,.2f}")
            print(f"買單結果: {res_b} | 賣單結果: {res_s}")
            time.sleep(CONFIG["REFRESH_RATE"])

if __name__ == "__main__":
    try:
        StandXBot().run()
    except Exception as e:
        print(f"致命錯誤:
