import logging
from urllib.request import urlopen
from http import HTTPStatus
from fingerprint.Fingerprint import Fingerprint
from flask_cors import CORS, cross_origin
from flask import Flask, render_template, request, Response, jsonify
from google.oauth2 import id_token
from google.auth.transport import requests

# L̶o̶c̶a̶l̶ Bad practice
# https://stackoverflow.com/a/51146920/8106847
# import sys
# sys.path.append("..")

# from kafelki.fingerprint.Fingerprint import Fingerprint
# set FLASK_ENV=development

app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}})
fingerprint = Fingerprint()


@app.route('/', methods=['GET'])
def main_page():
    return render_template('main_page.html')


@app.route('/api/tiles', methods=['GET'])
@cross_origin(origin='localhost')
def get_tiles():
    tile_url = request.args.get('tile_url')
    if not tile_url:
        return '1', HTTPStatus.BAD_REQUEST

    webscraper_response = urlopen(
        'https://webscraper-app-engine-dot-kafelki-297818.ew.r.appspot.com/tile_url_to_image_url?tile_url=' + tile_url
    )

    if webscraper_response.status != 200:
        return '', HTTPStatus.INTERNAL_SERVER_ERROR

    image_url = webscraper_response.read()

    if not image_url:
        return '', HTTPStatus.BAD_REQUEST

    try:
        tile_objects = fingerprint.get_similar_tiles(img_path=image_url.decode())[:10]
    except Exception as e:
        print("ERR", e, flush=True)
        return "Error while processing the image", HTTPStatus.INTERNAL_SERVER_ERROR

    response = jsonify(tile_objects)

    return response


@app.route('/update', methods=['GET'])
def update():
    if is_authorized():
        fingerprint.update_fingerprints()
        fingerprint.update_attributes()
        fingerprint.update_datastore()
        fingerprint.generate_csv()
        return 'Updated'
    else:
        return '', HTTPStatus.UNAUTHORIZED


# https://github.com/GoogleCloudPlatform/python-docs-samples/blob/master/appengine/standard/migration/incoming/main.py
def is_authorized():
    auth_header = request.headers.get('Authorization', None)
    if auth_header is None:
        return None

    # The auth_header must be in the form Authorization: Bearer token.
    bearer, token = auth_header.split()
    if bearer.lower() != 'bearer':
        return None

    try:
        info = id_token.verify_oauth2_token(token, requests.Request())
        service_account_email = info['email']
        incoming_app_id, domain = service_account_email.split('@')
        if domain != 'kafelki-297818.iam.gserviceaccount.com':
            return None
        else:
            return True
    except Exception as e:
        logging.warning('Bad Auth token ' + str(e))


if __name__ == '__main__':
    app.run('127.0.0.1', 8080)
