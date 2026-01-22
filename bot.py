# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# ---------------------------------------------------------
# 記事本設定檔管理 (config.txt)
# ---------------------------------------------------------
CONFIG_FILE = "config.txt"

def load_config_txt():
    # 如果檔案不存在，產生一個空白範本並退出
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("=== StandX Bot 設定檔 (請在等號後方輸入資訊) ===\n")
            f.write("JWT=請在此貼上你的JWT\n")
            f.write("SECRET=請在此貼上你的私鑰\n")
            f.write("SYMBOL=BTC-USD\n")
            f.write("QTY=1.01\n")
            f.write("TARGET_BPS=8\n")
            f.write("MIN_BPS=7\n")
            f.write("MAX_BPS=10\n")
        print(f"首次執行：已為您產生 {CONFIG_FILE}")
        print("請先用記事本打開該檔案，填好資訊後儲存，再重新執行程式。")
        input("按任意鍵退出..."); sys.exit()

    # 讀取記事本內容
    config = {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
        
        # 轉換數值型態
        config['QTY'] = config.get('QTY', '1.01')
        config['TARGET_BPS'] = int(config.get('TARGET_BPS', 8))
        config['MIN_BPS'] = int(config.get('MIN_BPS', 7))
        config['MAX_BPS'] = int(config.get('MAX_BPS', 10))
        return config
    except Exception as e:
        print(f"讀取 config.txt 出錯: {e}")
        input("請檢查設定檔格式後按任意鍵退出..."); sys.exit()

# 初始化設定
CONFIG = load_config_txt()

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
        
        # 處理私鑰格式
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
                print(f"   StandX 交易機器人 (記事本控制版)")
                print(f"==========================================")
                print(f" 🕒 時間: {datetime.now().strftime('%H:%M:%S')}")
                print(f" 💰 當前價格: {self.mid_price:,.2f}")
                print(f" ⚙️  QTY: {CONFIG['QTY']} | BPS: {CONFIG['TARGET_BPS']}")
                print(f" 📑 設定檔: {CONFIG_FILE}")
                print(f"------------------------------------------")
                print(f" [提示] 按下 Ctrl+C 可安全停止")
                
                time.sleep(1)
            except KeyboardInterrupt:
                print("\n停止運行..."); break
            except Exception as e:
                print(f"執行錯誤: {e}"); time.sleep(2)

if __name__ == "__main__":
    try:
        bot = StandXCMD()
        bot.main_loop()
    except Exception as e:
        print(f"\n❌ 啟動失敗: {e}")
        input("\n按任意鍵結束...")
