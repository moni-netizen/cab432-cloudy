import json, os, time
import boto3
from pymemcache.client.base import Client
from pymemcache.exceptions import MemcacheError

from fastapi import FastAPI, HTTPException, Response
from donut_service import (
    get_games_by_user, 
    get_recent_games_by_user,
    get_game_updates
    )

app = FastAPI()

mc = Client(
    (os.environ.get('CACHE_HOST', 'localhost'), int(os.environ.get("CACHE_PORT", "11211"))),
    connect_timeout = 1, timeout = 1, no_delay = True,
)

def cached(namespace: str, ident: str, ttl: int, builder):
    key = f"{namespace}:{ident}"                   # e.g. "donut_recent:7656...", "modified2w:7656..."
    try:
        hit = mc.get(key)
        if hit:
            return json.loads(hit), "hit"
    except (OSError, MemcacheError):
        pass
    data = builder(ident)
    try:
       mc.set(key, json.domps(data), expire = ttl)
    except (OSError, MemcacheError):
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
