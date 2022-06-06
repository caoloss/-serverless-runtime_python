import json
import sys
import time


def hello(event, context):

    if event.get("exception"):
        raise Exception

    if event.get("exit"):
        sys.exit(1)

    if event.get("delay"):
        time.sleep(100)

    body = {
        "message": "Go Serverless v3.0! Your function executed successfully!",
        "input": event,
    }

    return {"statusCode": 200, "body": json.dumps(body)}
