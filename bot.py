# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading, math
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# --- 1. 設定檔讀取邏輯 ---
CONFIG_FILE = "config.txt"

def load_config_txt():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("=== StandX Bot 設定檔 ===\n")
            f.write("JWT=請貼上你的JWT\n")
            f.write("SECRET=請貼上你的私鑰\n")
            f.write("SYMBOL=BTC-USD\n")
            f.write("QTY=1.01\n")
            f.write("TARGET_BPS=8\n")
            f.write("MIN_BPS=7\n")
            f.write("MAX_BPS=10\n")
        print(f"已產生 {CONFIG_FILE}，請填寫後重開。")
        input("按任意鍵退出..."); sys.exit()

    conf = {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.split("=", 1)
                    val = v.strip().replace(",", "").replace(" ", "").replace('"', '')
                    conf[k.strip()] = val
        
        def safe_int(key, default):
            raw = conf.get(key, str(default))
            num = "".join(filter(str.isdigit, raw))
            return int(num) if num else default

        return {
            "JWT": conf.get("JWT", ""),
            "SECRET": conf.get("SECRET", ""),
            "SYMBOL": conf.get("SYMBOL", "BTC-USD"),
            "QTY": conf.get("QTY", "1.01"),
            "TARGET_BPS": safe_int("TARGET_BPS", 8),
            "MIN_BPS": safe_int("MIN_BPS", 7),
            "MAX_BPS": safe_int("MAX_BPS", 10)
        }
    except Exception as e:
        print(f"讀取錯誤: {e}"); input("按鍵退出..."); sys.exit()

CONFIG = load_config_txt()

# --- 2. 交易核心邏輯 (StandXCMD) ---
class StandXCMD:
    def __init__(self):
        self.base_url = "https://perps.standx.com"
        self.ws_url = "wss://perps.standx.com/ws-stream/v1"
        self.mid_price = 0.0
        self.running = True
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

    def main_loop(self):
        while self.running:
            try:
                if self.mid_price == 0:
                    time.sleep(1); continue
                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"==========================================")
                print(f"   StandX 交易機器人 (運行中)")
                print(f"==========================================")
                print(f" 💰 當前價格: {self.mid_price:,.2f}")
                print(f" ⚙️  QTY: {CONFIG['QTY']} | BPS: {CONFIG['TARGET_BPS']}")
                print(f"------------------------------------------")
                time.sleep(1)
            except KeyboardInterrupt:
                self.running = False; break

# --- 3. 程式進入點 ---
if __name__ == "__main__":
    try:
        if sys.platform == "win32": os.system('') 
        print(">>> 正在初始化交易引擎...")
        bot = StandXCMD()
        bot.main_loop()
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        input("\n按任意鍵結束並關閉視窗...")
