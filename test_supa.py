from supabase import create_client
import os
url = "https://iblmxloizfpxmucypquv.supabase.co"
key = "sb_publishable_OTtcrtmKqwVRFUQbbqu6bA_-K9xOj9G"
supabase = create_client(url, key)
res = supabase.auth.sign_in_anonymously()
print(res.session.access_token)
