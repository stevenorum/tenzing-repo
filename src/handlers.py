#!/usr/bin/env python3

import s3_core

from jinja2 import Environment, FileSystemLoader
import json
import logging
import os
import re

env = Environment(loader=FileSystemLoader(os.path.join(os.environ['LAMBDA_TASK_ROOT'], "templates")))

REPO_NAME = os.environ.get("REPO_NAME", "GenericTenzingRepo")

def make_response(body, code=200, headers={"Content-Type": "text/html"}, base64=False):
    return {
        "body": body,
        "statusCode": code,
        "headers": headers,
        "isBase64Encoded": base64
    }

def render_response(template_name, code=200, event=None, **kwargs):
    template = env.get_template(template_name)
    params = {"repo_name":REPO_NAME}
    if event:
        params["requested_url"] = event["requestedUrl"]
        params["base_url"] = event["baseUrl"]
        params["repo_url"] = params["base_url"] + "/repo"
        params["api_url"] = params["base_url"] + "/api"
    params.update(kwargs)
    return make_response(template.render(**params))

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
        self.template = template if (template and template in env.list_templates()) else "http_xxx.html"
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

    def render(self, event=None):
        if event and "event" not in self.params:
            self.params["event"] = event
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
    dictify = lambda p: {"name":p, "url_segment":normalize_package_name(p)}
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
    return render_response("index.html", event=event)

def load_repo_index(event=None):
    return render_response("repo_index.html", package_list=get_packages(), event=event)

def load_package_index(package_name, event=None):
    return render_response("package_index.html", package_name=package_name, file_list=get_files_in_package(package_name), event=event)

def api_docs(event=None):
    return render_response("api_docs.html", event=event)

def handle_api_call(args, event=None):
    raise HttpException.from_code(501)

def handle_request(event, context):
    event["requestedUrl"] = event["headers"]["Host"].rstrip("/") + "/" + event["requestContext"]["path"].lstrip("/")
    event["baseUrl"] = event["requestedUrl"].rstrip("/")[:-1*len(event["path"].strip("/"))].rstrip("/")
    if "debug" in json.dumps(event).lower():
        blob = json.dumps(event, indent=2, sort_keys=True)
        blob += "\n{}\n{}".format(dir(context), vars(context))
        return make_response("<pre>{}</pre>".format(blob))
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
        return e.render(event=event)
    except Exception as e:
        return http500(event=event, exception=e).render()
