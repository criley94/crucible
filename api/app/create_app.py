"""Flask application factory."""

from flask import Flask, jsonify
from flask_cors import CORS

from app.routes.health import health_bp
from app.routes.orgs import orgs_bp
from app.routes.teams import teams_bp
from app.routes.agents import agents_bp
from app.routes.projects import projects_bp
from app.routes.experience import experience_bp


def create_app(config_object=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    if config_object:
        app.config.from_object(config_object)

    CORS(app)

    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(orgs_bp)
    app.register_blueprint(teams_bp)
    app.register_blueprint(agents_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(experience_bp)

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({
            "error": {
                "code": "METHOD_NOT_ALLOWED",
                "message": "The method is not allowed for the requested URL.",
                "details": {"allowed": e.valid_methods} if e.valid_methods else {},
            }
        }), 405

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": "The requested URL was not found.",
                "details": {},
            }
        }), 404

    return app
