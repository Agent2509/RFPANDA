import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
try:
    token = jwt.encode({"sub": "123"}, private_key, algorithm="RS256")
    jwt.decode(token, "secret", algorithms=["HS256"])
except Exception as e:
    print(repr(e))
