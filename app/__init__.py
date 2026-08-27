from flask import Flask, render_template

from .config import CONFIG_BY_NAME


def create_app(config_name: str = "production") -> Flask:
    app = Flask(__name__)
    app.config.from_object(CONFIG_BY_NAME.get(config_name, CONFIG_BY_NAME["production"]))

    from .blueprints.main.routes import main_bp

    app.register_blueprint(main_bp)

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html"), 404

    return app
