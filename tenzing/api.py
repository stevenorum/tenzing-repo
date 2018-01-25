 #!/usr/bin/env python3

# from junko.decorators import api_call
# from junko.dispatch import Link
# from junko.exceptions import HttpError, HttpUnauthorized, HttpNotFound, HttpInvalid
# from junko.response_core import make_response

# import s3_core

# import hashlib
# import json
# import logging
# import traceback

# def config_key(package):
#     return package + "/tenzing-config.json"

# def get_config(package):
#     return json.loads(s3_core.reads(config_key(package)))

# def authorize(package, password):
#     if not package:
#         raise HttpInvalid('No package provided.')
#     try:
#         config = get_config(package)
#     except:
#         raise HttpNotFound('Package not found.')
#     expected_passhash = config.get('passhash')
#     if not password and not expected_passhash:
#         return
#     elif not password:
#         raise HttpUnauthorized('Not authorized.')
#     passhash = hash_password(package, password)
#     if passhash == expected_passhash:
#         return
#     raise HttpUnauthorized('Not authorized.')

# def hash_password(package, password):
#     if not password:
#         return None
#     # This isn't a great way to do this, but it's fine for a prototype.
#     return hashlib.sha256((package + password).encode('utf-8')).hexdigest()

# def generate_config_contents(package, password=None):
#     return {
#         'package':package,
#         'passhash':hash_password(package, password)
#     }

# @api_call
# def handle_api(**params):
#     return make_response(body=format_content("Not yet implemented"))

# @api_call
# def create_package(**params):
#     package = params['package']
#     password = params.get('password')
#     config = generate_config_contents(package, password)
#     try:
#         get_config(package)
#         raise HttpInvalid('Package already exists.')
#     except HttpError as e:
#         raise e
#     except:
#         logging.error(traceback.format_exc())
#         pass
#     s3_core.write(config_key(package), config)
#     return make_response("{}", headers={"Content-Type": "text/json"})

# @api_call
# def update_package(**params):
#     package = params['package']
#     password = params.get('password')
#     authorize(package, password)
#     if params.get('update_password'):
#         new_config = generate_config_contents(package, params.get('new_password'))
#         s3_core.write(config_key(package), new_config)
#     return make_response("{}", headers={"Content-Type": "text/json"})

# @api_call
# def get_upload_links(**params):
#     package = params['package']
#     password = params.get('password')
#     authorize(package, password)
#     fnames = params['filenames']
#     fnames = [f.split('/')[-1] for f in fnames]
#     url_map = {}
#     for fname in fnames:
#         s3_key = package + '/' + fname.split('/')[-1]
#         link = s3_core.get_upload_link(s3_key)
#         url_map[fname] = link
#     response = {'links':url_map}
#     return make_response(body = json.dumps(response), headers={"Content-Type": "text/json"})

# def get_api_links():
#     return [
#         Link(r"^/api/package/create.*$", create_package, debug_name="create package"),
#         Link(r"^/api/package/update.*$", update_package, debug_name="update package"),
#         Link(r"^/api/package/upload.*$", get_upload_links, debug_name="get update link"),
#         Link(r"^/api/.*$", handle_api, debug_name="api page"),
#     ]



pass
