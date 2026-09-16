import requests
import os

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "https://jymrhyevcypjftrhlkty.supabase.co")
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." # wait, I don't need to hardcode it, I can read it from the backend .env or I'll just check frontend/.env.local
