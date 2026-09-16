import asyncio
from app.services.embedding import get_embedding_service
import httpx
import os
import json

async def main():
    service = get_embedding_service()
    emb = await service.embed_query("whats the document about ?")
    
    url = "https://iblmxloizfpxmucypquv.supabase.co/rest/v1/rpc/match_documents"
    key = os.popen("grep SUPABASE_SERVICE_ROLE_KEY backend/.env | cut -d '=' -f 2-").read().strip()
    print("Key exists:", bool(key))
    
    async with httpx.AsyncClient() as client:
        res = await client.post(
            url,
            json={
                "query_embedding": emb,
                "match_threshold": 0.0,
                "match_count": 5,
                "filter_user_id": "4ced005c-0b9a-4f9b-b4ec-c10fc7f6790c"
            },
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
        )
        print("Status:", res.status_code)
        data = res.json()
        print("MATCHES:", len(data))
        if len(data) > 0:
            print("TOP SCORE:", data[0].get("similarity"))
            print("WORST SCORE:", data[-1].get("similarity"))

asyncio.run(main())
