import sys
import json
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from fanvue_utils import FanvueUtils

utils = FanvueUtils()
response = utils.api_request("GET", "/chats")
if response:
    chats = response.json().get('data', [])
    if chats:
        print(json.dumps(chats[0], indent=2))
    else:
        print("No chats")
