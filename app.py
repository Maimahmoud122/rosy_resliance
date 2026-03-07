from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db      = SQLAlchemy()
migrate = Migrate()
bcrypt  = Bcrypt()
jwt     = JWTManager()
mail    = Mail()
limiter = Limiter(
    key_func       = get_remote_address,
    default_limits = ["200 per day", "50 per hour"]
)


def create_app():
    app = Flask(__name__)

    from config.config import Config
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    CORS(app)
    mail.init_app(app)
    limiter.init_app(app)

    # Import all models
    from models import User, Doctor, Patient, Admin
    from models.email_verification import EmailVerification
    from models.password_reset_token import PasswordResetToken

    # Register blueprints
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.account import account_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(account_bp)
    from routes.assignment import assignment_bp
    app.register_blueprint(assignment_bp)

    # Global error handlers
    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({"success": False, "message": "Too many attempts. Please wait and try again."}), 429

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "message": "Route not found."}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"success": False, "message": "Internal server error."}), 500

    return app