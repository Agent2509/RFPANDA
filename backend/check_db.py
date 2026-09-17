import requests

SUPABASE_URL = "https://iblmxloizfpxmucypquv.supabase.co"
SUPABASE_KEY = "sb_secret_zSYRfcAOjwdwnVwu9VoRgw_rbafuTBh"

url = f"{SUPABASE_URL}/rest/v1/documents?select=status,error_message"
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

resp = requests.get(url, headers=headers)
print(resp.status_code, resp.text)
