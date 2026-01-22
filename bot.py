# -*- coding: utf-8 -*-
import requests, time, json, uuid, base64, os, sys, threading, math
import websocket
from datetime import datetime
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# ... (中間邏輯不變) ...

if __name__ == "__main__":
    try:
        # 強制開啟 ANSI 支援
        if sys.platform == "win32":
            os.system('') 
            
        bot = StandXCMD()
        bot.main_loop()
    except Exception as e:
        print("\n" + "="*50)
        print(f"❌ 程式發生嚴重錯誤:")
        print(f"錯誤類型: {type(e).__name__}")
        print(f"錯誤詳細內容: {e}")
        print("="*50)
        input("\n按任意鍵結束並關閉視窗...") # 這一行能防止視窗直接跳掉
