# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# --- 設定檔管理 ---
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
                    # 自動清理：去掉空格、逗號、引號
                    val = v.strip().replace(",", "").replace(" ", "").replace('"', '')
                    conf[k.strip()] = val
        
        # 強制清理數字字元，防止 '8,' 這種錯誤
        def safe_int(key, default):
            raw = conf.get(key, str(default))
            num = "".join(filter(str.isdigit, raw))
            return int(num) if num else default

        config_data = {
            "JWT": conf.get("JWT", ""),
            "SECRET": conf.get("SECRET", ""),
            "SYMBOL": conf.get("SYMBOL", "BTC-USD"),
            "QTY": conf.get("QTY", "1.01"),
            "TARGET_BPS": safe_int("TARGET_BPS", 8),
            "MIN_BPS": safe_int("MIN_BPS", 7),
            "MAX_BPS": safe_int("MAX_BPS", 10)
        }
        return config_data
    except Exception as e:
        print(f"讀取設定檔發生錯誤: {e}")
        input("按任意鍵退出..."); sys.exit()

CONFIG = load_config_txt()

# --- 核心邏輯 (StandXCMD) ---
# [此處請保留您原本的 StandXCMD 類別內容]
