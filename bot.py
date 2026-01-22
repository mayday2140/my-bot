# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# --- 讀取設定 ---
CONFIG_FILE = "config.txt"

def load_config_txt():
    # (此處保持之前的讀取邏輯不變...)
    # ... 
    return { "JWT": "...", "SECRET": "...", "SYMBOL": "BTC-USD", "QTY": "0.01", "TARGET_BPS": 8 }

CONFIG = load_config_txt()

class StandXBot:
    def __init__(self):
        self.base_url = "https://perps.standx.com"
        self.ws_url = "wss://perps.standx.com/ws-stream/v1"
        self.mid_price = 0.0
        pk_str = CONFIG["SECRET"][2:] if CONFIG["SECRET"].startswith("0x") else CONFIG["SECRET"]
        self.signer = SigningKey(pk_str, encoder=HexEncoder)
        self.headers = {"Authorization": f"Bearer {CONFIG['JWT']}", "Content-Type": "application/json"}
        self.start_ws()

    def start_ws(self):
        # (WebSocket 邏輯保持不變...)
        pass

    def sign(self, body):
        rid, ts = str(uuid.uuid4()), str(int(time.time() * 1000))
        msg = f"v1,{rid},{ts},{body}"
        sig = base64.b64encode(self.signer.sign(msg.encode()).signature).decode()
        return {"x-request-sign-version": "v1", "x-request-id": rid, "x-request-timestamp": ts, "x-request-signature": sig}

    # 新增：取消該交易對的所有掛單
    def cancel_all_orders(self):
        path = f"/api/v1/orders/all?symbol={CONFIG['SYMBOL']}"
        try:
            res = requests.delete(self.base_url + path, headers={**self.headers, **self.sign("")}, timeout=5)
            return res.status_code
        except: return None

    def place_order(self, side, price):
        path = "/api/v1/orders"
        tick = 0.5
        px = str(round(price / tick) * tick)
        data = {"symbol": CONFIG["SYMBOL"], "side": side, "type": "LIMIT", "price": px, "qty": CONFIG["QTY"]}
        body = json.dumps(data)
        try:
            res = requests.post(self.base_url + path, data=body, headers={**self.headers, **self.sign(body)}, timeout=5)
            return res.json() if res.text else {"status": "Fail (Check Balance/JWT)"}
        except Exception as e:
            return {"status": f"Error: {e}"}

    def run_loop(self):
        print(">>> 機器人已上線，正在嘗試在紅框處掛單...")
        while True:
            if self.mid_price == 0:
                time.sleep(1); continue
            
            # 1. 先清空舊單，確保網頁乾淨
            self.cancel_all_orders()
            
            gap = self.mid_price * (CONFIG["TARGET_BPS"] / 10000)
            bid, ask = self.mid_price - gap, self.mid_price + gap

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 市價: {self.mid_price}")
            
            # 2. 下新單
            r_b = self.place_order("BUY", bid)
            r_s = self.place_order("SELL", ask)

            print(f"買單: {r_b}")
            print(f"賣單: {r_s}")
            
            time.sleep(15) 

# (啟動代碼...)
