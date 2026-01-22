# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading, math
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# ---------------------------------------------------------
# 設定檔管理功能
# ---------------------------------------------------------
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print("首次執行，請輸入您的 API 資訊 (資訊將存存在 config.json)：")
        jwt = input("請輸入 JWT Token: ").strip()
        secret = input("請輸入 Private Key (私鑰): ").strip()
        symbol = input("請輸入交易對 (預設 BTC-USD): ").strip() or "BTC-USD"
        
        config_data = {
            "JWT": jwt,
            "SECRET": secret,
            "SYMBOL": symbol,
            "QTY": "1.01",
            "TARGET_BPS": 8,
            "MIN_BPS": 7,
            "MAX_BPS": 10
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
        print("設定檔已儲存！")
        return config_data

# 初始化讀取
CONFIG = load_config()

# 修正 Windows CMD 編碼
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    os.system('color 0a')

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

    def call(self, method, path, data=None):
        try:
            url = self.base_url + path
            if method == "GET": return requests.get(url, headers=self.headers, timeout=2).json()
            body = json.dumps(data)
            return requests.post(url, data=body, headers={**self.headers, **self.sign(body)}, timeout=2).json()
        except: return {}

    def main_loop(self):
        os.system('cls')
        print(f">>> ProcyonsBot 啟動中 (目標: {CONFIG['SYMBOL']})...")
        while self.running:
            try:
                if self.mid_price == 0:
                    time.sleep(1); continue
                
                os.system('cls')
                print(f"==========================================")
                print(f"   StandX 交易機器人 (自定義設定版)")
                print(f"==========================================")
                print(f" 🕒 時間: {datetime.now().strftime('%H:%M:%S')}")
                print(f" 💰 當前中間價: {self.mid_price:,.2f}")
                print(f" ⚙️  設定: {CONFIG['TARGET_BPS']} bps | {CONFIG['QTY']} 數量")
                print(f"------------------------------------------")
                print(f" [提示] 按下 Ctrl+C 可安全停止")
                
                time.sleep(1)
            except KeyboardInterrupt:
                print("\n停止運行..."); break

if __name__ == "__main__":
    try:
        bot = StandXCMD()
        bot.main_loop()
    except Exception as e:
        print(f"發生錯誤: {e}")
        input("按任意鍵結束...")
