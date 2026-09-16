from supabase import create_client
url = "https://iblmxloizfpxmucypquv.supabase.co"
key = "sb_publishable_OTtcrtmKqwVRFUQbbqu6bA_-K9xOj9G"
supabase = create_client(url, key)
res = supabase.auth.sign_up({"email": "mohdfaizanali604@gmail.com", "password": "securepassword123"})
print(res)
