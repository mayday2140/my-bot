# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# --- 讀取設定檔 ---
def load_config():
    conf = {}
    if not os.path.exists("config.txt"):
        print("找不到 config.txt，請先產生。")
        input(); sys.exit()
    with open("config.txt", "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip().replace(",", "").replace(" ", "")
    return conf

CONFIG = load_config()

class StandXBot:
    def __init__(self):
        self.base_url = "https://perps.standx.com"
        self.ws_url = "wss://perps.standx.com/ws-stream/v1"
        self.mid_price = 0.0
        # 私鑰處理
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
        # 價格精確到 0.5
        px = str(round(price * 2) / 2)
        data = {"symbol": CONFIG["SYMBOL"], "side": side, "type": "LIMIT", "price": px, "qty": str(CONFIG["QTY"])}
        body = json.dumps(data)
        try:
            res = requests.post(self.base_url + path, data=body, headers={**self.headers, **self.sign(body)}, timeout=5)
            if res.status_code == 200:
                return "成功掛單 ✅"
            else:
                return f"失敗 ❌ (代碼: {res.status_code}, 內容: {res.text if res.text else '空回傳，請檢查保證金是否劃轉'})"
        except Exception as e:
            return f"連線異常: {e}"

    def run_trading(self):
        print(f">>> 機器人啟動中... 目標: {CONFIG['SYMBOL']} (QTY: {CONFIG['QTY']})")
        while True:
            if self.mid_price == 0:
                time.sleep(1); continue
            
            gap = self.mid_price * (int(CONFIG.get("TARGET_BPS", 8)) / 10000)
            bid, ask = self.mid_price - gap, self.mid_price + gap

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 市場價格: {self.mid_price}")
            print(f"嘗試掛單 [買]: {bid:.1f} -> {self.place_order('BUY', bid)}")
            print(f"嘗試掛單 [賣]: {ask:.1f} -> {self.place_order('SELL', ask)}")
            
            # 等待下次循環
            time.sleep(20)

if __name__ == "__main__":
    try:
        bot = StandXBot()
        bot.run_trading()
    except Exception as e:
        print(f"\n❌ 程式崩潰原因: {e}")
        input("\n按任意鍵結束視窗，修正後再試一次...")
