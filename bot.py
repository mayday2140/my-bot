# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# --- 1. 設定檔管理 (自動清理空格與逗號) ---
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

# --- 2. 核心交易機器人 ---
class StandXBot:
    def __init__(self):
        self.base_url = "https://perps.standx.com"
        self.ws_url = "wss://perps.standx.com/ws-stream/v1"
        self.mid_price = 0.0
        # 處理私鑰
        pk_str = CONFIG["SECRET"]
        if pk_str.startswith("0x"): pk_str = pk_str[2:]
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
        data = {"symbol": CONFIG["SYMBOL"], "side": side, "type": "LIMIT", "price": str(price), "qty": str(CONFIG["QTY"])}
        body = json.dumps(data)
        try:
            res = requests.post(self.base_url + path, data=body, headers={**self.headers, **self.sign(body)}, timeout=5)
            return res.json()
        except Exception as e:
            return {"error": str(e)}

    def start_trading_loop(self):
        print(">>> 交易系統啟動，等待價格數據...")
        while True:
            try:
                if self.mid_price == 0:
                    time.sleep(1); continue
                
                # 計算 BPS 價位
                gap = self.mid_price * (CONFIG["TARGET_BPS"] / 10000)
                buy_px = round(self.mid_price - gap, 2)
                sell_px = round(self.mid_price + gap, 2)

                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 市價: {self.mid_price}")
                print(f"嘗試下單 -> 買: {buy_px} | 賣: {sell_px}")

                # 執行下單
                r1 = self.place_order("BUY", buy_px)
                r2 = self.place_order("SELL", sell_px)

                print(f"結果 -> 買入: {r1.get('status', r1.get('error', 'Unknown'))} | 賣出: {r2.get('status', r2.get('error', 'Unknown'))}")
                
                # 每 15 秒運行一次
                time.sleep(15)
            except Exception as e:
                print(f"循環出錯: {e}")
                time.sleep(5)

if __name__ == "__main__":
    try:
        if sys.platform == "win32": os.system('')
        bot = StandXBot()
        bot.start_trading_loop()
    except Exception as e:
        print(f"\n❌ 啟動失敗: {e}")
        input("\n按任意鍵結束並檢查錯誤...")
