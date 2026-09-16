import jwt
try:
    token = jwt.encode({"sub": "123"}, "secret", algorithm="HS256")
    jwt.decode(token, "", algorithms=["HS256"])
except Exception as e:
    print(repr(e))
