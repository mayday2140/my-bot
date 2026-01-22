# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# --- 1. 設定檔管理 (完全保留你要求的變數名稱) ---
CONFIG_FILE = "config.txt"

def load_config_txt():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("=== StandX Bot 設定檔 ===\n")
            f.write("JWT_TOKEN=請貼上你的JWT\n")
            f.write("PRIVATE_KEY_HEX=請貼上你的私鑰\n")
            f.write("SYMBOL=BTC-USD\n")
            f.write("BASE_URL=https://perps.standx.com\n")
            f.write("ORDER_QTY=0.1\n")
            f.write("TARGET_BPS=8\n")
            f.write("MIN_BPS=6\n")
            f.write("MAX_BPS=10\n")
            f.write("REFRESH_RATE=0.5\n")
        print(f"已產生 {CONFIG_FILE}，請填寫後重開。")
        input("按任意鍵退出..."); sys.exit()

    conf = {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip().replace(",", "").replace(" ", "").replace('"', '')
    
    def safe_float(key, default):
        try: return float(conf.get(key, default))
        except: return float(default)

    def safe_int(key, default):
        try:
            num = "".join(filter(str.isdigit, str(conf.get(key, ""))))
            return int(num) if num else default
        except: return default

    return {
        "JWT_TOKEN": conf.get("JWT_TOKEN", ""),
        "PRIVATE_KEY_HEX": conf.get("PRIVATE_KEY_HEX", ""),
        "SYMBOL": conf.get("SYMBOL", "BTC-USD"),
        "BASE_URL": conf.get("BASE_URL", "https://perps.standx.com"),
        "ORDER_QTY": conf.get("ORDER_QTY", "0.1"),
        "TARGET_BPS": safe_int("TARGET_BPS", 8),
        "MIN_BPS": safe_int("MIN_BPS", 6),
        "MAX_BPS": safe_int("MAX_BPS", 10),
        "REFRESH_RATE": safe_float("REFRESH_RATE", 0.5)
    }

CONFIG = load_config_txt()

# --- 2. 交易核心 ---
class StandXBot:
    def __init__(self):
        self.base_url = CONFIG["BASE_URL"]
        self.ws_url = "wss://perps.standx.com/ws-stream/v1"
        self.mid_price = 0.0
        
        # 處理私鑰
        pk_str = CONFIG["PRIVATE_KEY_HEX"]
        if pk_str.startswith("0x"): pk_str = pk_str[2:]
        self.signer = SigningKey(pk_str, encoder=HexEncoder)
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
            if res.status_code == 200: return "成功 ✅"
            return f"失敗 (代碼:{res.status_code}, {res.text if res.text else '請檢查保證金'})"
        except Exception as e:
            return f"連線錯誤: {e}"

    def run_loop(self):
        print(f">>> 機器人啟動 | 交易對: {CONFIG['SYMBOL']} | 數量: {CONFIG['ORDER_QTY']}")
        print(f">>> 重新整理頻率: {CONFIG['REFRESH_RATE']} 秒")
        
        while True:
            if self.mid_price == 0:
                time.sleep(1); continue
            
            gap = self.mid_price * (CONFIG["TARGET_BPS"] / 10000)
            bid, ask = self.mid_price - gap, self.mid_price + gap

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 市價: {self.mid_price}")
            print(f" 📥 買單 ({bid:.1f}): {self.place_order('BUY', bid)}")
            print(f" 📤 賣單 ({ask:.1f}): {self.place_order('SELL', ask)}")
            
            # 使用你指定的 REFRESH_RATE
            time.sleep(CONFIG["REFRESH_RATE"])

if __name__ == "__main__":
    try:
        bot = StandXBot()
        bot.run_loop()
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        input("\n按任意鍵結束視窗...")
