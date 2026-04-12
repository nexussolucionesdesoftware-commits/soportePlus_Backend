from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from config import config_by_name

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
jwt = JWTManager()
ma = Marshmallow()


def create_app(config_name="default"):
    """Application factory pattern."""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    jwt.init_app(app)
    ma.init_app(app)

    # Register blueprints
    with app.app_context():
        from app.routes.auth import auth_bp
        from app.routes.main import main_bp
        from app.routes.tickets import bp as tickets_bp
        from app.users.router import users_bp  # ← un solo origen
        from app.rolls import rolls_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        app.register_blueprint(users_bp, url_prefix="/api/users")
        app.register_blueprint(rolls_bp, url_prefix="/api/rolls")
        app.register_blueprint(tickets_bp, url_prefix="/api/tickets")

        from app.utils.error_handlers import register_error_handlers
        register_error_handlers(app)

    return app