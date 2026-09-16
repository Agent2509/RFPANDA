import asyncio
from app.services.embedding import get_embedding_service
import httpx
import os

async def main():
    service = get_embedding_service()
    emb = await service.embed_query("whats the document about ?")
    
    url = "https://iblmxloizfpxmucypquv.supabase.co/rest/v1/rpc/match_documents"
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
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
                "Authorization": f"Bearer {key}"
            }
        )
        data = res.json()
        print("MATCHES:", len(data))
        if data:
            print("TOP SCORE:", data[0].get("similarity"))

asyncio.run(main())
