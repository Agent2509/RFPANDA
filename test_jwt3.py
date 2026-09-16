import jwt
try:
    jwt.decode("some_random_string", "secret", algorithms=["HS256"])
except Exception as e:
    print(repr(e))
