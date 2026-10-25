import json, os, time
import boto3, redis
from fastapi import FastAPI, HTTPException, Response
from donut_service import (
    get_games_by_user, 
    get_recent_games_by_user,
    get_game_updates
    )

app = FastAPI()
rds = redis.Redis(
    host = os.environ.get("REDIS_HOST"), port = 6379, #beware tihs port. is it supported?
    ssl=os.environ.get("REDIS_TLS") == "1",
    socket_timeout=1, socket_connect_timeout=1, decode_responses=True,
)
TTL = {"all": 7 * 86400, "recent": 86400}

# in the case we need to get our data again...
BUILDERS = {"all": get_games_by_user,
 "recent": get_recent_games_by_user,
 "modified1wk": get_game_updates}

def cached(namespace: str, ident: str, ttl: int, builder):
    key = f"{namespace}:{ident}"                   # e.g. "donut_recent:7656...", "modified2w:7656..."
    try:
        hit = rds.get(key)
        if hit:
            return json.loads(hit), "hit"
    except redis.RedisError:
        pass
    data = builder(ident)
    try:
        rds.setex(key, ttl, json.dumps(data))
    except redis.RedisError:
        pass
    return data, "miss"

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/a3/games/{steam_id}")
def games(steam_id: str, response: Response):
    if not (steam_id.isdigit() and len(steam_id) == 17):
        raise HTTPException(400, "invalid id")
    t0 = time.perf_counter()
    all_games, s1 = cached("donut_all", steam_id, 7 * 86400, get_games_by_user)
    recent, s2 = cached("donut_recent", steam_id, 86400, get_recent_games_by_user)
    response.headers["X-Cache"] = f"all={s1},recent={s2}"
    return {"all_games": all_games, "recent_games": recent,
            "cache": {"all": s1, "recent": s2},
            "ms": round((time.perf_counter() - t0) * 1000, 1)}

@app.get("/a3/games")
def get_new_games(response: Response):
    games, s3 = cached("modifiedWeekly", "global", 3600 * 6, get_game_updates) # 6 hours
    response.headers["X-Cache"] = s3
    return {"games": games, "cache": s3}
