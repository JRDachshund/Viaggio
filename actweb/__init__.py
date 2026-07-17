from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'marvintheparanoidandroid'

    from .alt import alt

    app.register_blueprint(alt, url_prefix="/")

    return app
