# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# --- 1. 設定檔 ---
def load_config():
    p = "config.txt"
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8") as f:
            f.write("JWT_TOKEN=你的JWT\nPRIVATE_KEY_HEX=你的私鑰\nSYMBOL=BTC-USD\nBASE_URL=https://perps.standx.com\nORDER_QTY=0.05\nTARGET_BPS=8\nREFRESH_RATE=0.5\n")
        print("已產生 config.txt，請填寫後重開。")
        input(); sys.exit()
    conf = {}
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip().replace('"', '')
    return conf

C = load_config()

class StandXBot:
    def __init__(self):
        # 網址校準：StandX 網頁端下單通常會導向特定的 API Gateway
        self.base_url = C.get("BASE_URL", "https://perps.standx.com").rstrip('/')
        self.ws_url = "wss://perps.standx.com/ws-stream/v1"
        self.mid_price = 0.0
        
        pk = C.get("PRIVATE_KEY_HEX", "")
        if pk.startswith("0x"): pk = pk[2:]
        self.signer = SigningKey(pk, encoder=HexEncoder)
        self.headers = {
            "Authorization": f"Bearer {C.get('JWT_TOKEN', '')}",
            "Content-Type": "application/json"
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
                on_open=lambda ws: ws.send(json.dumps({"subscribe": {"channel": "price", "symbol": C.get("SYMBOL", "BTC-USD")}})),
                on_message=on_msg)
            ws.run_forever()
        threading.Thread(target=run, daemon=True).start()

    def sign(self, body):
        rid, ts = str(uuid.uuid4()), str(int(time.time() * 1000))
        msg = f"v1,{rid},{ts},{body}"
        sig = base64.b64encode(self.signer.sign(msg.encode()).signature).decode()
        return {"x-request-sign-version": "v1", "x-request-id": rid, "x-request-timestamp": ts, "x-request-signature": sig}

    def place_order(self, side, price):
        # 精確路徑探測：StandX 的 API 路由
        url = f"{self.base_url}/api/v1/orders"
        
        # 價格格式校準：BTC 必須為整數 (如 90098)
        data = {
            "symbol": C.get("SYMBOL", "BTC-USD"),
            "side": side,
            "type": "LIMIT",
            "price": str(round(price)),
            "qty": str(C.get("ORDER_QTY", "0.05"))
        }
        body = json.dumps(data, separators=(',', ':'))
        
        try:
            res = requests.post(url, data=body, headers={**self.headers, **self.sign(body)}, timeout=3)
            if res.status_code == 200: return "成功 ✅"
            return f"失敗({res.status_code})"
        except Exception:
            return "連線超時"

    def run(self):
        print(f"機器人已啟動 | 頻率: {C.get('REFRESH_RATE')}s")
        while True:
            if self.mid_price == 0:
                time.sleep(0.1); continue
            
            gap = self.mid_price * (int(C.get("TARGET_BPS", 8)) / 10000)
            bid, ask = self.mid_price - gap, self.mid_price + gap

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Px: {self.mid_price:,.2f} | 買單: {self.place_order('BUY', bid)} | 賣單: {self.place_order('SELL', ask)}")
            time.sleep(float(C.get("REFRESH_RATE", 0.5)))

if __name__ == "__main__":
    try: StandXBot().run()
    except Exception as e: print(f"致命錯誤: {e}"); input()
