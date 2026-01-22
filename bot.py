# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# --- 1. 設定檔讀取 (自動過濾錯誤字元) ---
CONFIG_FILE = "config.txt"

def load_config_txt():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("=== StandX Bot 設定檔 ===\n")
            f.write("JWT=貼上你的JWT\n")
            f.write("SECRET=貼上你的私鑰\n")
            f.write("SYMBOL=BTC-USD\n")
            f.write("QTY=0.01\n")
            f.write("TARGET_BPS=8\n")
        print(f"已產生 {CONFIG_FILE}，請填寫後重開。")
        input("按任意鍵退出..."); sys.exit()

    conf = {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip().replace(",", "").replace(" ", "").replace('"', '')
    
    def safe_float(key, default):
        try: return str(conf.get(key, default))
        except: return default

    def safe_int(key, default):
        try:
            num = "".join(filter(str.isdigit, str(conf.get(key, ""))))
            return int(num) if num else default
        except: return default

    return {
        "JWT": conf.get("JWT", ""),
        "SECRET": conf.get("SECRET", ""),
        "SYMBOL": conf.get("SYMBOL", "BTC-USD"),
        "QTY": safe_float("QTY", "0.01"),
        "TARGET_BPS": safe_int("TARGET_BPS", 8)
    }

CONFIG = load_config_txt()

# --- 2. 交易機器人核心 ---
class StandXBot:
    def __init__(self):
        self.base_url = "https://perps.standx.com"
        self.ws_url = "wss://perps.standx.com/ws-stream/v1"
        self.mid_price = 0.0
        # 處理私鑰與 Headers
        pk_str = CONFIG["SECRET"][2:] if CONFIG["SECRET"].startswith("0x") else CONFIG["SECRET"]
        self.signer = SigningKey(pk_str, encoder=HexEncoder)
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
        # 重要修正：價格必須是 0.5 的倍數，並轉換為字串
        tick_size = 0.5
        rounded_price = str(round(price / tick_size) * tick_size)
        
        data = {
            "symbol": CONFIG["SYMBOL"],
            "side": side,
            "type": "LIMIT",
            "price": rounded_price,
            "qty": CONFIG["QTY"]
        }
        body = json.dumps(data)
        try:
            res = requests.post(self.base_url + path, data=body, headers={**self.headers, **self.sign(body)}, timeout=5)
            # 如果回傳空值，顯示自定義錯誤
            if not res.text: return {"status": "Empty Response (Check JWT/Balance)"}
            return res.json()
        except Exception as e:
            return {"status": f"Error: {str(e)}"}

    def run_loop(self):
        print(f">>> 監控中，準備於網頁預掛單...")
        while True:
            if self.mid_price == 0:
                time.sleep(1); continue
            
            gap = self.mid_price * (CONFIG["TARGET_BPS"] / 10000)
            bid = self.mid_price - gap
            ask = self.mid_price + gap

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 市價: {self.mid_price}")
            
            # 發送掛單
            res_bid = self.place_order("BUY", bid)
            res_ask = self.place_order("SELL", ask)

            print(f"買單結果: {res_bid}")
            print(f"賣單結果: {res_ask}")
            
            # 若成功，網頁紅框處就會出現單子
            time.sleep(20) 

if __name__ == "__main__":
    try:
        bot = StandXBot()
        bot.run_loop()
    except Exception as e:
        print(f"致命錯誤: {e}")
        input("按任意鍵結束...")
