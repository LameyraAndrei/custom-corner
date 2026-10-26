from flask import Blueprint, render_template, request
from .. import db

bp = Blueprint("shop", __name__)


@bp.route("/shop")
def catalog():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    sort = request.args.get("sort", "featured")

    sql = (
        "SELECT p.*, c.name AS category_name, c.slug AS category_slug "
        "FROM products p JOIN categories c ON c.id = p.category_id WHERE p.is_active = 1"
    )
    args = []
    if q:
        sql += " AND (p.name LIKE ? OR p.description LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    if category:
        sql += " AND c.slug = ?"
        args.append(category)
    if min_price is not None:
        sql += " AND p.base_price >= ?"
        args.append(min_price)
    if max_price is not None:
        sql += " AND p.base_price <= ?"
        args.append(max_price)

    sort_map = {
        "price_low": " ORDER BY p.base_price ASC",
        "price_high": " ORDER BY p.base_price DESC",
        "name": " ORDER BY p.name ASC",
        "newest": " ORDER BY p.created_at DESC",
        "featured": " ORDER BY p.is_featured DESC, p.id ASC",
    }
    sql += sort_map.get(sort, sort_map["featured"])

    products = db.query(sql, args)
    categories = db.query("SELECT * FROM categories ORDER BY name")

    return render_template(
        "shop.html", products=products, categories=categories, q=q,
        active_category=category, sort=sort, min_price=min_price, max_price=max_price,
    )


@bp.route("/product/<slug>")
def product_detail(slug):
    product = db.query(
        "SELECT p.*, c.name AS category_name, c.slug AS category_slug "
        "FROM products p JOIN categories c ON c.id = p.category_id WHERE p.slug = ?",
        (slug,), one=True,
    )
    if product is None:
        return render_template("404.html"), 404

    colors = db.query("SELECT * FROM product_colors WHERE product_id = ?", (product["id"],))
    sizes = db.query("SELECT * FROM product_sizes WHERE product_id = ?", (product["id"],))
    related = db.query(
        "SELECT * FROM products WHERE category_id = ? AND id != ? AND is_active = 1 LIMIT 4",
        (product["category_id"], product["id"]),
    )
    return render_template("product_detail.html", product=product, colors=colors, sizes=sizes, related=related)
