from supabase import create_client
url = "https://iblmxloizfpxmucypquv.supabase.co"
key = "$(grep SUPABASE_SERVICE_ROLE_KEY backend/.env | cut -d '=' -f 2-)"
supabase = create_client(url, key)
res = supabase.table("document_chunks").select("id").limit(1).execute()
print(res)
