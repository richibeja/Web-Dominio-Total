
import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPS_GROUP_ID = os.getenv("TELEGRAM_OPERACIONES_ID")

def check_activity():
    print(f"Checking Telegram updates for Bot Token: {TOKEN[:10]}...")
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    try:
        r = requests.get(url, params={"limit": 20, "allowed_updates": ["message"]}, timeout=10)
        if r.status_code != 200:
            print(f"Error: {r.status_code} - {r.text}")
            return
            
        updates = r.json().get("result", [])
        if not updates:
            print("No recent updates found.")
            return

        print(f"Found {len(updates)} recent updates.\n")
        for upd in updates:
            msg = upd.get("message") or upd.get("channel_post")
            if not msg: continue
            
            chat = msg.get("chat", {})
            user = msg.get("from", {})
            text = msg.get("text", "[No text]")
            date = datetime.fromtimestamp(msg.get("date")).strftime('%Y-%m-%d %H:%M:%S')
            
            chat_title = chat.get("title") or chat.get("username") or chat.get("id")
            user_name = user.get("first_name") or user.get("username") or "System"
            
            print(f"[{date}] {chat_title} | {user_name}: {text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    check_activity()
