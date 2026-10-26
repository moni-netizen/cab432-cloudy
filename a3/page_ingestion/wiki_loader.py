import json, time, urllib.parse, urllib.request
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

## make an API request to get all the pages from the stardew valley website
API = "https://stardewvalley.fandom.com/api.php"
UA = {"User-Agent": "cab432-student-project (n12023868@qut.edu.au)"}

def fetch_all_pages(max_requests: int = 20):
    params = {
        "action": "query",
        "generator": "allpages",
        "gapnamespace": 0,
        "gapfilterredir": "nonredirects",     # skip redirect stubs
        "gaplimit": "max",
        "prop": "info",
        "inprop": "url",
        "format": "json",
        "formatversion": 2,                   # pages come back as a list, not a dict
    }
    pages, cont = {}, {}

    for _ in range(max_requests):             # hard cap so a bug can't loop forever
        url = API + "?" + urllib.parse.urlencode({**params, **cont})
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)

        for p in data.get("query", {}).get("pages", []):
            pages[p["pageid"]] = {"id": p["pageid"], "title": p["title"], "url": p["fullurl"]}

        if "continue" not in data:            # no continue tag: that was the last batch
            break
        cont = data["continue"]               # pass the WHOLE dict back, not just one field
        time.sleep(1)                         # be polite between requests
    return list(pages.values())


items = fetch_all_pages()

# connect to dynamodb table
table_name = "n12023868-wiki-pages"
aws_region = "ap-southeast-2"

dynamodb = boto3.resource(
    "dynamodb",
    region_name = aws_region
)
table = dynamodb.Table(table_name)

def store_to_dynamodb(item_list: list) -> tuple[int, dict]:
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in item_list:
            item.update({"createdAt": current_time, "updatedAt": current_time, "status": "pending"})
            table.put_item(Item = item)
        
        return 200, {"message": "success"}

    except ClientError as e:
        return 500, {"message": "failed", "error": e}


status_code, message = store_to_dynamodb(items)

print(message)

# thank u for ur service :3 now gtfo
