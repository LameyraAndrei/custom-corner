import os
from flask import Flask, session, g

from .config import Config
from . import db as db_module


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db_module.init_app(app)

    # Ensure the sqlite file exists (auto-init on first run for convenience).
    if not os.path.exists(app.config["DATABASE_PATH"]):
        db_module.init_db(app)
        from .seed import run_seed
        run_seed(app)

    from .routes.main import bp as main_bp
    from .routes.auth import bp as auth_bp
    from .routes.shop import bp as shop_bp
    from .routes.customizer import bp as customizer_bp
    from .routes.cart import bp as cart_bp
    from .routes.orders import bp as orders_bp
    from .routes.account import bp as account_bp
    from .routes.admin import bp as admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(customizer_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)

    from .helpers import current_user, cart_count, cart_total

    @app.context_processor
    def inject_globals():
        user = current_user()
        return {
            "current_user": user,
            "cart_count": cart_count(user["id"]) if user else 0,
            "cart_total": cart_total(user["id"]) if user else 0,
        }

    @app.template_filter("peso")
    def peso_filter(value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return value
        return "₱{:,.2f}".format(value).replace(".00", "") if value == int(value) else "₱{:,.2f}".format(value)

    return app
