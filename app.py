import os
import json
import time
import logging
from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = '1hexsGYT0aEDXVrtOJoZg5ZRF7X-LUM6F0zTImw3a4aI'

# In-memory cache
_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 60  # seconds

def get_credentials():
    creds_raw = os.environ.get('GOOGLE_CREDENTIALS', '')
    creds_dict = json.loads(creds_raw)
    return service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

def get_sheets_data():
    now = time.time()
    if _cache["data"] and (now - _cache["timestamp"]) < CACHE_TTL:
        return _cache["data"]

    sheets = build('sheets', 'v4', credentials=get_credentials())
    result = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range='Sheet1!A:B'
    ).execute()

    rows = result.get('values', [])
    info = {}
    for row in rows[1:]:
        if len(row) >= 2:
            info[row[0].strip().lower()] = row[1].strip()

    _cache["data"] = info
    _cache["timestamp"] = now
    return info

@app.route('/')
def home():
    return jsonify({"status": "ok"})

@app.route('/lookup_info', methods=['POST'])
def lookup_info():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        data = payload.get('args', payload)
        key = str(data.get('key', '')).strip().lower()

        info = get_sheets_data()

        if key in info:
            return jsonify({"success": True, "value": info[key]})
        else:
            return jsonify({"success": True, "value": info})

    except Exception as e:
        app.logger.error(f"ERROR: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
