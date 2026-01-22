def load_config_txt():
    # ... 前面產出檔案的邏輯不變 ...
    conf = {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.split("=", 1)
                    # 自動清理掉所有空白、逗號、引號
                    val = v.strip().replace(",", "").replace(" ", "").replace('"', '')
                    conf[k.strip()] = val
        
        # 轉換數字的強大容錯
        def safe_int(key, default):
            raw = conf.get(key, str(default))
            num = "".join(filter(str.isdigit, raw)) # 只保留數字
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
        print(f"讀取錯誤: {e}"); input("按任意鍵退出..."); sys.exit()
