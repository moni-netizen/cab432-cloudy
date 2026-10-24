from __future__ import annotations
import json, os, urllib.parse, urllib.request, time
import boto3

from donut_model import(
    get_pie_history,
    get_pie_ltw
)

secrets = boto3.client("secretsmanager")

ssm_client = boto3.client('ssm')
aws_region = ssm_client.get_parameter(
    Name = '/n12023868/a3/general/aws-region',
    WithDecryption=False,
)["Parameter"]["Value"]

secret_name = "n12023868-a3-secrets"

def get_secret() -> dict:
    session = boto3.session.Session()
    client = session.client(
        service_name = "secretsmanager",
        region_name = aws_region
    )

    try:
        response = client.get_secret_value(
            SecretId = secret_name
        )
    except ClientError as e:
        raise e
    
    return json.loads(response["SecretString"])

secrets = get_secret()
steam_api_token = secrets["STEAM_API_TOKEN"]

## perhaps edit this site to cache this too? many users will get
## the same most recently modified games, so we want to limit these
## calls. probably even more so with our data!
def get_game_updates(time_since: int) -> list[str]:
    time_since = int(time.time()) - (7 * 86400) # one week
    apps, last_appid = [], 0
    for _ in range(5):
        query = urllib.parse.urlencode({
            "key": steam_api_token,
            "if_modified_since": time_since,
            "have_description_language": "english",
            "max_results": 100,
        })
        url = f"https://api.steampowered.com/IStoreService/GetAppList/v1/?{query}"
        with urllib.request.urlopen(url, timeout=10) as r:
            body = json.load(r).get("response", {})
        apps.extend(body.get("apps", []))
        if not body.get("have more results"):
            break
        last_appid = body["last_appid"]
    
    apps.sort(key = lambda a: a.get("last_modified", 0), reverse = True)
    return [
        {
            "appid":a["appid"],
            "name": a["name"],
            "last_modified": a["last_modified"],
            "image": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{a['appid']}/header.jpg",
        }
        # just get 20 games thanks
        for a in apps[:20]
    ]


def get_games_by_user(steam_id: str):
    # this is the historical games for the RHS plot
    # update on a two-week schedule (maybe reenact as demonstration in ex. though)
    query = urllib.parse.urlencode({
        "key": steam_api_token,
        "steamid": steam_id,
        "include_appinfo": 1,
        "include_played_free_games": 1,
        "format": "json"
    })
    url = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/?{query}"
    with urllib.request.urlopen(url, timeout=10) as r:
        body = json.load(r)["response"]["games"]
        result = get_pie_history(body)
    return result

def get_recent_games_by_user(steam_id: str):
    # this finds and populates data for the last 2 weeks games
    # cache this daily
    query = urllib.parse.urlencode({
        "key": steam_api_token,
        "steamid": steam_id,
        "count": 6,
        "format": "json"
    })
    url = f"https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/?{query}"
    with urllib.request.urlopen(url, timeout=10) as r:
        body = json.load(r)["response"]["games"]
        result = get_pie_ltw(body)
    return result
