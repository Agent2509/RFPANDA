from supabase import create_client
import os

url = "https://iblmxloizfpxmucypquv.supabase.co"
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

res = supabase.table("document_chunks").select("id, document_id, chunk_index, similarity:embedding").limit(5).execute()
print(res)
