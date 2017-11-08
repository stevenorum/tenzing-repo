#!/usr/bin/env python3

import boto3
import json
import os
import time

REPO_BUCKET = os.environ.get("REPO_BUCKET")

PRESIGNED_URL_CACHE = {}
LINK_MAX_AGE = 900 # seconds, so 15 minutes
LINK_REFRESH_BUFFER = 60 # seconds, so 1 minute

s3 = boto3.client('s3')

def readb(s3_key):
    return s3.get_object(Bucket=REPO_BUCKET, Key=s3_key)['Body'].read()

def reads(s3_key):
    return readb(s3_key).decode('utf-8')

def write(s3_key, body):
    body = json.dumps(body) if isinstance(body, (list, dict)) else body
    body = body if isinstance(body, (bytes, bytearray)) else body.encode('utf-8')
    s3.put_object(Bucket=REPO_BUCKET, Key=s3_key, Body=body)

def reads(s3_key):
    return readb(s3_key).decode('utf-8')

def get_file_link(s3_key):
    obj = PRESIGNED_URL_CACHE.get(s3_key, {"expires":0})
    now = int(time.time())
    if obj["expires"] - now < LINK_REFRESH_BUFFER:
        PRESIGNED_URL_CACHE[s3_key] = {
            "expires": now + LINK_MAX_AGE,
            "url": s3.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket':REPO_BUCKET,'Key':s3_key},
                ExpiresIn=LINK_MAX_AGE
            )
        }
    return PRESIGNED_URL_CACHE[s3_key]["url"]

def get_upload_link(s3_key):
    return s3.generate_presigned_url(
        ClientMethod='put_object',
        Params={'Bucket':REPO_BUCKET,'Key':s3_key},
        ExpiresIn=LINK_MAX_AGE
    )

def list_objects(**kwargs):
    response = s3.list_objects_v2(Bucket=REPO_BUCKET, **kwargs)
    contents = response.get("Contents", [])
    prefixes = response.get("CommonPrefixes", [])
    while response.get("IsTruncated", False):
        response = s3.list_objects_v2(Bucket=REPO_BUCKET, ContinuationToken=response.get("NextContinuationToken", None), **kwargs)
        contents += response.get("Contents", [])
        prefixes += response.get("CommonPrefixes", [])
        pass
    return contents, [p["Prefix"] for p in prefixes]

def list_files(**kwargs):
    return list_objects(**kwargs)[0]

def list_prefixes(**kwargs):
    return list_objects(**kwargs)[1]
