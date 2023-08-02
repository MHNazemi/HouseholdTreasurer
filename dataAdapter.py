import redis

key_delimiter= "1eX3kja2h" # this keys shouldn't be changed. It's a prefix to all keys 

redis_server = redis.Redis("localhost",6379,0)

def get_keys():
    redis_server.keys(key_delimiter+"",)

def add_entity(key:str,value:str):
    redis_server.set(key_delimiter+key,value)

def get_all():
    return redis_server.mget(redis_server.keys(key_delimiter+"*"))
    