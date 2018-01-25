 #!/usr/bin/env python3

# from junko.decorators import *

# from junko.exceptions import HttpException, render_http_exceptions

# from junko.dispatch import DispatchChain, Link
# from junko.template_dispatchers import TemplateLink

# from junko.formatting import format_content
# from junko import kson as json
# from junko import logster
# from junko.random_utils import *
# from junko.response_core import make_response

import s3_core

# import base64
# import boto3
import logging
import os
import re
# import time
# import traceback

env = Environment(loader=FileSystemLoader(os.path.join(os.environ['LAMBDA_TASK_ROOT'], "templates")))

# s3 = boto3.client("s3")

# REPO_BUCKET = os.environ.get("REPO_BUCKET")
REPO_NAME = os.environ.get("REPO_NAME", "generic tenzing repo")

# def get_packages_in_repo():
#     prefixes = s3_core.list_prefixes(Delimiter="/")
#     trimmed_prefixes = [p[:-1] for p in prefixes]
#     return trimmed_prefixes

# def get_files_in_package(packagename):
#     prefix = add_trailing_slash(packagename)
#     files = s3_core.list_files(Prefix=prefix)
#     files = [f for f in files if not f['Key'].endswith('.json')]
#     file_keys = [f["Key"] for f in files]
#     file_urls = {f[len(prefix):]:s3_core.get_download_link(f) for f in file_keys}
#     return file_urls

# def normalize_package_name(packagename):
#     return re.sub(r"[-_.]+", "-", packagename).lower()

# def package_exists(packagename):
#     if not packagename:
#         return False
#     return packagename in get_packages_in_repo()

# def file_exists(packagename, filename):
#     if not filename or not packagename:
#         return False
#     return filename in get_files_in_package(packagename)

# def get_package_from_request(request):
#     path = strip_trailing_slash(strip_leading_slash(request.get("path","")))
#     parts = path.split("/")
#     if parts[0] == "repo":
#         del parts[0]
#     packagename = parts[0]
#     if not package_exists(packagename):
#         raise HttpException.from_code(404)
#     return packagename

# def get_package_and_file_from_request(request):
#     path = strip_trailing_slash(strip_leading_slash(request.get("path","")))
#     parts = path.split("/")
#     if parts[0] == "repo":
#         del parts[0]
#     packagename = parts[0]
#     filename = parts[1]
#     if not file_exists(packagename, filename):
#         # This'll also catch the case where the package doesn't exist, for hopefully obvious reasons.
#         raise HttpException.from_code(404)
#     return packagename, filename

# def repo_index_param_loader(request):
#     repo_root = 'https://{host}{path}'.format(host=request['headers']['Host'], path=request['requestContext']['path'])
#     repo_root = strip_trailing_slash(repo_root)
#     return {"packages":[(p, normalize_package_name(p)) for p in get_packages_in_repo()], "repo_name":REPO_NAME, 'repo_root':repo_root}

# def package_index_param_loader(request):
#     package_root = 'https://{host}{path}'.format(host=request['headers']['Host'], path=request['requestContext']['path'])
#     package_root = strip_trailing_slash(package_root)
#     packagename = get_package_from_request(request)
#     files = get_files_in_package(packagename)
#     file_list = [json.blob({"name":k,"url":files[k]}) for k in files]
#     return {"files":file_list, "package_name":packagename, 'package_root':package_root}


###### Above here is old, throwaway stuff. ######


def make_response(body, code=200, headers={"Content-Type": "text/html"}, base64=False):
    return {
        "body": body,
        "statusCode": code,
        "headers": headers,
        "isBase64Encoded": base64
    }

def render_response(template_name, code=200, **kwargs):
    template = env.get_template(template_name)
    return make_response(template.render(**kwargs))

class HttpException(Exception):
    DEFAULT_MESSAGES = {
        400:"Your request is bad and you should feel bad.",
        401:"You are not authorized to access this page.",
        403:"You are not authorized to access this page.",
        404:"The page you requested does not exist.",
        451:"The man says you can't see that.  Sorry.",
        500:"An internal server error occurred.  Sorry about that.",
        501:"Not yet implemented.  Sorry about that.",
        503:"The service is temporarily down.  Please try again later."
    }

    DEFAULT_PHRASES = {
        400:"Bad Request",
        401:"Unauthorized",
        403:"Forbidden",
        404:"Not Found",
        451:"Unavailable For Legal Reasons",
        500:"Internal Server Error",
        501:"Not Implemented",
        503:"Service Unavailable"
    }

    def __init__(self, template=None, code=None, params={}):
        self.template = template if (template and template in env.list_templates() else "http_xxx.html")
        self.code = int(code)
        self.params = params
        if "message" not in params:
            # The exception templates expect this by default.
            params["message"] = self.DEFAULT_MESSAGES.get(self.code, "An error occurred.")
        if "code" not in params:
            params["code"] = self.code
        if "phrase" not in params:
            params["phrase"] = self.DEFAULT_PHRASES.get(self.code, "Unspecified Error")

    @classmethod
    def from_code(cls, code, **kwargs):
        return cls(template="http_{code}.html".format(code=code), code=code, params=kwargs)

    def render(self):
        return render_response(self.template, code=self.code, **self.params)

def http500(event=None, exception=None, message=None):
    # Has a helper function to log the event for debugging purposes.
    logargs = ["An unexpected error occurred."] if not event else ["An unexpected error occurred with input event {}".format(json.dumps(event))]
    logargs = (logargs + [exception]) if exception else logargs
    logging.error(*logargs)
    return HttpException.from_code(500, message=message)

def package_exists(packagename):
    if not packagename:
        return False
    return packagename in get_packages_in_repo()

def get_packages_in_repo():
    packages = s3_core.list_prefixes(Delimiter="/")
    packages = [p.strip("/") for p in packages]
    return packages

def normalize_package_name(packagename):
    return re.sub(r"[-_./]+", "-", packagename).lower()

def get_packages():
    dictify = lambda p: {"name":p, "prefix":normalize_package_name(p)}
    return [dictify(p) for p in get_packages_in_repo()]

def get_files_in_package(package_name):
    if not package_name or package_name.strip("/") not in get_packages_in_repo():
        raise HttpException.from_code(404, message="Package '{}' not found in repo.".format(package_name))
    prefix = package_name.strip("/") + "/"
    files = s3_core.list_files(Prefix=prefix)
    files = [f["Key"] for f in files]
    files = [f for f in files if not f.endswith(".json")]
    dictify = lambda f: {"name":f[len(prefix):],"url":s3_core.get_download_link(f)}
    return [dictify(f) for f in files]

def landing_page(event=None):
    return render_response("index.html")

def load_repo_index(event=None):
    return render_response("repo_index.html", repo_name=REPO_NAME, package_list=get_packages())

def load_package_index(package_name, event=None):
    return render_response("package_index.html", package_name=package_name, file_list=get_files_in_package(package_name))

def api_docs(event=None):
    return render_response("api_docs.html")

def handle_api_call(args, event=None):
    raise HttpException.from_code(501)

def handle_request(event, context):
    try:
        path = event["path"].strip("/").split("/")
        if path[0] == "":
            return landing_page(event=event)
        elif path[0] == "repo":
            if len(path) == 1:
                return load_repo_index(event=event)
            elif len(path) == 2:
                return load_package_index(path[1],event=event)
        elif path[0] == "api":
            if len(path) == 1:
                return api_docs(event=event)
            else:
                return handle_api_call(path[1:], event=event)
        raise HttpException.from_code(404)
    except HttpException as e:
        return e.render()
    except Exception as e:
        return http500(exception=e).render()
