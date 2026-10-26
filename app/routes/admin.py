from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

from .. import db
from ..helpers import admin_required, STATUS_STEPS

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@admin_required
def dashboard():
    total_orders = db.query("SELECT COUNT(*) c FROM orders", one=True)["c"]
    revenue = db.query("SELECT COALESCE(SUM(total),0) r FROM orders WHERE status != 'Cancelled'", one=True)["r"]
    pending_orders = db.query("SELECT COUNT(*) c FROM orders WHERE status IN ('Pending','Design Review')", one=True)["c"]
    products_sold = db.query(
        "SELECT COALESCE(SUM(oi.quantity),0) c FROM order_items oi JOIN orders o ON o.id = oi.order_id "
        "WHERE o.status != 'Cancelled'", one=True
    )["c"]
    recent_orders = db.query(
        "SELECT o.*, u.name AS customer_name FROM orders o JOIN users u ON u.id = o.user_id "
        "ORDER BY o.created_at DESC LIMIT 8"
    )
    low_stock = db.query("SELECT * FROM products WHERE stock <= 20 AND is_active = 1 ORDER BY stock ASC LIMIT 5")
    return render_template(
        "admin/dashboard.html", total_orders=total_orders, revenue=revenue,
        pending_orders=pending_orders, products_sold=products_sold,
        recent_orders=recent_orders, low_stock=low_stock,
    )


@bp.route("/orders")
@admin_required
def orders():
    status_filter = request.args.get("status", "")
    sql = ("SELECT o.*, u.name AS customer_name FROM orders o JOIN users u ON u.id = o.user_id")
    args = []
    if status_filter:
        sql += " WHERE o.status = ?"
        args.append(status_filter)
    sql += " ORDER BY o.created_at DESC"
    rows = db.query(sql, args)
    return render_template("admin/orders.html", orders=rows, statuses=STATUS_STEPS + ["Cancelled"], active_status=status_filter)


@bp.route("/orders/<int:order_id>")
@admin_required
def order_detail(order_id):
    order = db.query("SELECT o.*, u.name AS customer_name, u.email AS customer_email FROM orders o "
                      "JOIN users u ON u.id = o.user_id WHERE o.id = ?", (order_id,), one=True)
    if not order:
        return render_template("404.html"), 404
    items = db.query("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    return render_template("admin/order_detail.html", order=order, items=items, statuses=STATUS_STEPS + ["Cancelled"])


@bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    new_status = request.form.get("status")
    if new_status:
        db.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        flash(f"Order status updated to {new_status}.", "success")
    return redirect(url_for("admin.order_detail", order_id=order_id))


@bp.route("/products")
@admin_required
def products():
    rows = db.query(
        "SELECT p.*, c.name AS category_name FROM products p JOIN categories c ON c.id = p.category_id "
        "ORDER BY p.id DESC"
    )
    return render_template("admin/products.html", products=rows)


@bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    product = db.query("SELECT * FROM products WHERE id = ?", (product_id,), one=True)
    if not product:
        return render_template("404.html"), 404
    categories = db.query("SELECT * FROM categories ORDER BY name")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        base_price = request.form.get("base_price", type=float)
        stock = request.form.get("stock", type=int)
        category_id = request.form.get("category_id", type=int)
        is_active = 1 if request.form.get("is_active") == "on" else 0

        if not name or base_price is None or stock is None:
            flash("Name, price and stock are required.", "error")
        else:
            db.execute(
                "UPDATE products SET name=?, description=?, base_price=?, stock=?, category_id=?, is_active=? "
                "WHERE id=?",
                (name, description, base_price, stock, category_id, is_active, product_id),
            )
            flash("Product updated.", "success")
            return redirect(url_for("admin.products"))

    return render_template("admin/product_form.html", product=product, categories=categories, mode="edit")


@bp.route("/products/new", methods=["GET", "POST"])
@admin_required
def new_product():
    categories = db.query("SELECT * FROM categories ORDER BY name")
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip().lower().replace(" ", "-")
        description = request.form.get("description", "").strip()
        base_price = request.form.get("base_price", type=float)
        stock = request.form.get("stock", type=int)
        category_id = request.form.get("category_id", type=int)
        mockup_shape = request.form.get("mockup_shape", "tshirt")

        if not name or not slug or base_price is None or stock is None or not category_id:
            flash("Please fill in all required fields.", "error")
        elif db.query("SELECT id FROM products WHERE slug = ?", (slug,), one=True):
            flash("A product with that slug already exists.", "error")
        else:
            pid = db.execute(
                "INSERT INTO products (category_id, name, slug, description, base_price, customization_fee, "
                "image, material, production_time, mockup_shape, stock, is_active, is_featured) "
                "VALUES (?,?,?,?,?,50,'placeholder.jpg','','2-3 business days',?,?,1,0)",
                (category_id, name, slug, description, base_price, mockup_shape, stock),
            )
            flash("Product created.", "success")
            return redirect(url_for("admin.edit_product", product_id=pid))

    return render_template("admin/product_form.html", product=None, categories=categories, mode="new")


@bp.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def delete_product(product_id):
    db.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
    flash("Product disabled.", "success")
    return redirect(url_for("admin.products"))


@bp.route("/designs")
@admin_required
def designs():
    rows = db.query(
        "SELECT d.*, u.name AS customer_name, p.name AS product_name FROM designs d "
        "JOIN users u ON u.id = d.user_id JOIN products p ON p.id = d.product_id "
        "ORDER BY d.updated_at DESC"
    )
    return render_template("admin/designs.html", designs=rows)


@bp.route("/customers")
@admin_required
def customers():
    rows = db.query(
        "SELECT u.*, "
        "(SELECT COUNT(*) FROM orders o WHERE o.user_id = u.id) AS order_count, "
        "(SELECT COALESCE(SUM(total),0) FROM orders o WHERE o.user_id = u.id AND o.status != 'Cancelled') AS lifetime_value "
        "FROM users u WHERE u.is_admin = 0 ORDER BY u.created_at DESC"
    )
    return render_template("admin/customers.html", customers=rows)


@bp.route("/inventory")
@admin_required
def inventory():
    rows = db.query(
        "SELECT p.*, c.name AS category_name FROM products p JOIN categories c ON c.id = p.category_id "
        "ORDER BY p.stock ASC"
    )
    return render_template("admin/inventory.html", products=rows)


@bp.route("/inventory/<int:product_id>/stock", methods=["POST"])
@admin_required
def update_stock(product_id):
    stock = request.form.get("stock", type=int)
    if stock is not None and stock >= 0:
        db.execute("UPDATE products SET stock = ? WHERE id = ?", (stock, product_id))
        flash("Stock updated.", "success")
    return redirect(url_for("admin.inventory"))


@bp.route("/reports")
@admin_required
def reports():
    by_category = db.query(
        "SELECT c.name AS category, COUNT(oi.id) AS items_sold, COALESCE(SUM(oi.quantity * (oi.unit_price + "
        "oi.customization_fee)),0) AS revenue FROM order_items oi JOIN products p ON p.id = oi.product_id "
        "JOIN categories c ON c.id = p.category_id JOIN orders o ON o.id = oi.order_id "
        "WHERE o.status != 'Cancelled' GROUP BY c.name ORDER BY revenue DESC"
    )
    by_status = db.query("SELECT status, COUNT(*) AS c FROM orders GROUP BY status")
    monthly = db.query(
        "SELECT strftime('%Y-%m', created_at) AS month, COALESCE(SUM(total),0) AS revenue, COUNT(*) AS orders "
        "FROM orders WHERE status != 'Cancelled' GROUP BY month ORDER BY month DESC LIMIT 6"
    )
    return render_template("admin/reports.html", by_category=by_category, by_status=by_status, monthly=monthly)


@bp.route("/settings")
@admin_required
def settings():
    return render_template("admin/settings.html")
