from flask import Flask
import os
from databaseMan import close_db, before_request

def create_app():
    app = Flask(__name__, static_url_path='/static')
    app.secret_key = os.environ['sessionKey']
    app.teardown_appcontext(close_db)
    app.before_request(before_request)
    return app