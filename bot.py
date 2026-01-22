import os

# ==========================================
# ⚙️ 機器人設定區 (從 GitHub Secrets 讀取)
# ==========================================
JWT_TOKEN = os.getenv("JWT_TOKEN")
PRIVATE_KEY_HEX = os.getenv("PRIVATE_KEY_HEX")

# 如果環境變數不存在，報錯退出
if not JWT_TOKEN or not PRIVATE_KEY_HEX:
    logger.error("錯誤: 找不到環境變數 JWT_TOKEN 或 PRIVATE_KEY_HEX")
    sys.exit(1)
