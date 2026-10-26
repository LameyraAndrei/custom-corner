from flask import Blueprint, render_template
from .. import db

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    categories = db.query("SELECT * FROM categories ORDER BY id")
    featured = db.query(
        "SELECT p.*, c.name AS category_name, c.slug AS category_slug "
        "FROM products p JOIN categories c ON c.id = p.category_id "
        "WHERE p.is_featured = 1 AND p.is_active = 1 ORDER BY p.id LIMIT 4"
    )
    return render_template("home.html", categories=categories, featured=featured)


@bp.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html")


@bp.route("/about")
def about():
    return render_template("about.html")
