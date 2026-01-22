# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

CONFIG_FILE = "config.txt"

def load_config_txt():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("=== StandX Bot 設定檔 ===\n")
            f.write("JWT=貼上你的JWT\n")
            f.write("SECRET=貼上你的私鑰\n")
            f.write("SYMBOL=BTC-USD\n")
            f.write("QTY=1.01\n")
            f.write("TARGET_BPS=8\n")
            f.write("MIN_BPS=7\n")
            f.write("MAX_BPS=10\n")
        print(f"首次執行：已產生 {CONFIG_FILE}，請填寫後重開。")
        input("按任意鍵退出..."); sys.exit()

    conf = {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.split("=", 1)
                    # 自動去掉空格、逗號、換行符號
                    conf[k.strip()] = v.strip().replace(",", "").replace(" ", "")
        
        # 強大容錯：過濾非數字字元
        def clean_to_int(raw, default):
            try:
                num_part = "".join(filter(str.isdigit, str(raw)))
                return int(num_part) if num_part else default
            except: return default

        conf['TARGET_BPS'] = clean_to_int(conf.get('TARGET_BPS'), 8)
        conf['MIN_BPS'] = clean_to_int(conf.get('MIN_BPS'), 7)
        conf['MAX_BPS'] = clean_to_int(conf.get('MAX_BPS'), 10)
        return conf
    except Exception as e:
        print(f"讀取設定檔失敗: {e}"); input("按鍵退出..."); sys.exit()

CONFIG = load_config_txt()

# ... [此處接續您原本的 StandXCMD 類別代碼] ...
