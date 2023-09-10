from flask import Flask, request
from http import HTTPStatus
from google.oauth2 import id_token
from google.auth.transport import requests
from shops import tile_url_to_image_url, update_all
import logging

app = Flask(__name__)


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


@app.route('/scrape-tiles', methods=['POST'])
def task_handler():
    if is_authorized():
        update_all()
        return "Updated"
    else:
        return "", HTTPStatus.UNAUTHORIZED
        # payload = request.get_data(as_text=True) or '(empty payload)'


@app.route('/')
def hello():
    """Basic index to verify app is serving."""
    return 'Webscraper is serving'


@app.route('/tile_url_to_image_url', methods=['GET'])
def tile_url_handler():
    tile_url = request.args.get('tile_url')
    if tile_url:
        return tile_url_to_image_url(tile_url)
    else:
        return 'Invalid tile_url', HTTPStatus.BAD_REQUEST


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
