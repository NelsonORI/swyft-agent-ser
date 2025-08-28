from flask import Flask
from flask_migrate import Migrate
from extensions import db, cors
from config import Config

# Import routes
from routes.mpesa_routes import mpesa_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    Migrate(app, db)
    cors.init_app(app)

    # Register blueprints
    app.register_blueprint(mpesa_bp, url_prefix="/api/mpesa")

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
