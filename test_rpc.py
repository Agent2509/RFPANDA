from supabase import create_client
import os

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

print(supabase.rpc("increment_query_count", {"p_user_id": "00000000-0000-0000-0000-000000000000"}).execute())
