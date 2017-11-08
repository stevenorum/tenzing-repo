 #!/usr/bin/env python3

from junko.decorators import *

from junko.exceptions import HttpException, render_http_exceptions

from junko.dispatch import DispatchChain, Link
from junko.template_dispatchers import TemplateLink

from junko.formatting import format_content
from junko import kson as json
from junko import logster
from junko.random_utils import *
from junko.response_core import make_response

import api, s3_core

import base64
import boto3
import os
import re
import time
import traceback

logster.set_level(logster.DEBUG)

s3 = boto3.client("s3")

REPO_BUCKET = os.environ.get("REPO_BUCKET")
AUTH_ENABLED = os.environ.get("AUTH_ENABLED") == "TRUE"
DEBUG_ENABLED = os.environ.get("DEBUG_ENABLED") == "TRUE"

# LINK_MAX_AGE = 900 # seconds, so 15 minutes
# LINK_REFRESH_BUFFER = 60 # seconds, so 1 minute

PAGE_CHAIN = DispatchChain(debug_name="PAGE_CHAIN")

HANDLER_CHAIN = DispatchChain(
    PAGE_CHAIN,
    debug_name="HANDLER_CHAIN"
)

# TODO: fix this janky shit
def authorized(username, password):
    return username=="ThisIsAUsername" and password=="ThisIsAPassword"

def get_repo_name():
    return "Tenzing dev repo"

def get_debug_string(request):
    event = to_object(request)
    return json.dumps(event, indent=2, sort_keys=True)+"\n\nDispatch paths:\n"+json.dumps(HANDLER_CHAIN.debug_info(),indent=2,sort_keys=True) + "\n\n\nENVIRON:\n\n" + json.dumps(dict(os.environ), indent=2, sort_keys=True) + "\n\n\nTask root contents:\n\n" + "\n".join(os.listdir(os.environ['LAMBDA_TASK_ROOT'])) + "\n\nRepo bucket:\n\n" + REPO_BUCKET

def debug(request):
    return make_response(format_content(get_debug_string(request)))

# PRESIGNED_URL_CACHE = {}

# def get_file_link(s3_key):
#     obj = PRESIGNED_URL_CACHE.get(s3_key, {"expires":0})
#     now = int(time.time())
#     if obj["expires"] - now < LINK_REFRESH_BUFFER:
#         PRESIGNED_URL_CACHE[s3_key] = {
#             "expires": now + LINK_MAX_AGE,
#             "url": s3.generate_presigned_url(
#                 ClientMethod="get_object",
#                 Params={'Bucket':REPO_BUCKET,'Key':s3_key},
#                 ExpiresIn=LINK_MAX_AGE
#             )
#         }
#     return PRESIGNED_URL_CACHE[s3_key]["url"]

# def list_objects(**kwargs):
#     response = s3.list_objects_v2(Bucket=REPO_BUCKET, **kwargs)
#     contents = response.get("Contents", [])
#     prefixes = response.get("CommonPrefixes", [])
#     while response.get("IsTruncated", False):
#         response = s3.list_objects_v2(Bucket=REPO_BUCKET, ContinuationToken=response.get("NextContinuationToken", None), **kwargs)
#         contents += response.get("Contents", [])
#         prefixes += response.get("CommonPrefixes", [])
#         pass
#     return contents, [p["Prefix"] for p in prefixes]

# def list_files(**kwargs):
#     return list_objects(**kwargs)[0]

# def list_prefixes(**kwargs):
#     return list_objects(**kwargs)[1]

# def handle_api(request):
#     return make_response(body=format_content("Not yet implemented"))

# def create_package(request):
#     pass

# def update_package(request):
#     pass

# def get_upload_link(request):
#     pass

def get_packages_in_repo():
    prefixes = s3_core.list_prefixes(Delimiter="/")
    trimmed_prefixes = [p[:-1] for p in prefixes]
    return trimmed_prefixes

def get_files_in_package(packagename):
    prefix = add_trailing_slash(packagename)
    files = s3_core.list_files(Prefix=prefix)
    files = [f for f in files if not f.endswith('/tenzing-conf.json')]
    file_keys = [f["Key"] for f in files]
    file_urls = {f[len(prefix):]:s3_core.get_file_link(f) for f in file_keys}
    return file_urls

def normalize_package_name(packagename):
    return re.sub(r"[-_.]+", "-", packagename).lower()

def package_exists(packagename):
    if not packagename:
        return False
    return packagename in get_packages_in_repo()

def file_exists(packagename, filename):
    if not filename or not packagename:
        return False
    return filename in get_files_in_package(packagename)

def get_package_from_request(request):
    path = strip_trailing_slash(strip_leading_slash(request.get("path","")))
    parts = path.split("/")
    if parts[0] == "repo":
        del parts[0]
    packagename = parts[0]
    if not package_exists(packagename):
        raise HttpException.from_code(404)
    return packagename

def get_package_and_file_from_request(request):
    path = strip_trailing_slash(strip_leading_slash(request.get("path","")))
    parts = path.split("/")
    if parts[0] == "repo":
        del parts[0]
    packagename = parts[0]
    filename = parts[1]
    if not file_exists(packagename, filename):
        # This'll also catch the case where the package doesn't exist, for hopefully obvious reasons.
        raise HttpException.from_code(404)
    return packagename, filename

def repo_index_param_loader(request):
    return {"packages":[(p, normalize_package_name(p)) for p in get_packages_in_repo()], "repo_name":get_repo_name()}

def package_index_param_loader(request):
    packagename = get_package_from_request(request)
    files = get_files_in_package(packagename)
    file_list = [json.blob({"name":k,"url":files[k]}) for k in files]
    return {"files":file_list, "package_name":packagename}

def return_file(request):
    packagename, filename = get_package_and_file_from_request(request)
    return make_response(body=format_content("Not yet implemented, sorry."))

def check_auth(request):
    headers = request.get("headers", {})
    auth_header = headers.get("Authorization")
    logster.debug("Auth header: {}".format(auth_header))
    if not auth_header:
        raise HttpException.from_code(401)
    try:
        auth_type = auth_header.split(" ")[0]
        auth_blob = auth_header.split(" ")[1]
        logster.debug("Auth type / blob: {} / {}".format(auth_type, auth_blob))
        auth_string = base64.b64decode(auth_blob).decode("utf-8")
        logster.debug("Auth string: {}".format(auth_string))
        username = auth_string.split(":")[0]
        password = ":".join(auth_string.split(":")[1:])
        logster.debug("Username / Password: {} / {}".format(username, password))
        if authorized(username, password):
            logster.debug("Authorization succeeded.")
            return None
    except Exception as e:
        logster.warn(traceback.format_exc())
        pass
    raise HttpException.from_code(401)

if DEBUG_ENABLED:
    PAGE_CHAIN.add_link(
        Link(r"^.*debug$", debug, debug_name="Debug page")
    )
if AUTH_ENABLED:
    PAGE_CHAIN.add_link(
        Link(r"^.*$", check_auth, debug_name="Auth page")
    )

PAGE_CHAIN.add_links(
    TemplateLink(r"^/?$", template_name="index.html", param_loader=repo_index_param_loader, debug_name="tenzing landing page"),
    TemplateLink(r"^/repo/?$", template_name="repo_index.html", param_loader=repo_index_param_loader, debug_name="repo index"),
    TemplateLink(r"^/repo/[-_.0-9a-zA-Z]+/?$", template_name="package_index.html", param_loader=package_index_param_loader, debug_name="package index"),
    Link(r"^/repo/[-_.0-9a-zA-Z]+/.*$", return_file, debug_name="file page"),
    # Link(r"^/api/package/create.*$", create_package, debug_name="create package"),
    # Link(r"^/api/package/update.*$", update_package, debug_name="update package"),
    # Link(r"^/api/package/upload.*$", get_upload_link, debug_name="get update link"),
    # Link(r"^/api/.*$", handle_api, debug_name="api page"),
)

PAGE_CHAIN.add_links(*api.get_api_links())

@log_calls
@render_http_exceptions
@log_errors
def dispatcher(event, context):
    try:
        logster.info("HEADERS:\n{}".format(json.dumps(event.get("headers",{}))))
        request = to_object(event)
        request["lambda_context"] = context
        response = HANDLER_CHAIN.dispatch(request)
        if response:
            return response
        raise HttpException.from_code(404)
    except Exception as e:
        if DEBUG_ENABLED:
            return make_response(body=format_content(traceback.format_exc()))
        else:
            raise e
