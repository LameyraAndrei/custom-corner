from flask import Blueprint, render_template, request, redirect, url_for, flash

from .. import db
from ..helpers import login_required, current_user

bp = Blueprint("account", __name__, url_prefix="/account")


@bp.route("/")
@login_required
def dashboard():
    user = current_user()
    orders = db.query(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 3", (user["id"],)
    )
    designs = db.query(
        "SELECT d.*, p.name AS product_name, p.slug AS product_slug FROM designs d "
        "JOIN products p ON p.id = d.product_id WHERE d.user_id = ? ORDER BY d.updated_at DESC LIMIT 3",
        (user["id"],),
    )
    return render_template("account/dashboard.html", orders=orders, designs=designs)


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        if not name:
            flash("Name cannot be empty.", "error")
        else:
            db.execute("UPDATE users SET name = ?, phone = ? WHERE id = ?", (name, phone, user["id"]))
            flash("Profile updated.", "success")
        return redirect(url_for("account.profile"))
    return render_template("account/profile.html", user=user)


@bp.route("/orders")
@login_required
def orders():
    user = current_user()
    rows = db.query("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", (user["id"],))
    return render_template("account/orders.html", orders=rows)


@bp.route("/designs")
@login_required
def designs():
    user = current_user()
    rows = db.query(
        "SELECT d.*, p.name AS product_name, p.slug AS product_slug, p.base_price FROM designs d "
        "JOIN products p ON p.id = d.product_id WHERE d.user_id = ? ORDER BY d.updated_at DESC",
        (user["id"],),
    )
    return render_template("account/designs.html", designs=rows)


@bp.route("/addresses", methods=["GET", "POST"])
@login_required
def addresses():
    user = current_user()
    if request.method == "POST":
        label = request.form.get("label", "Home").strip() or "Home"
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        address_line = request.form.get("address_line", "").strip()
        city = request.form.get("city", "").strip()
        province = request.form.get("province", "").strip()
        postal_code = request.form.get("postal_code", "").strip()

        if not all([full_name, address_line, city, province]):
            flash("Please fill in all required address fields.", "error")
        else:
            make_default = request.form.get("is_default") == "on"
            if make_default:
                db.execute("UPDATE addresses SET is_default = 0 WHERE user_id = ?", (user["id"],))
            db.execute(
                "INSERT INTO addresses (user_id, label, full_name, phone, address_line, city, province, "
                "postal_code, is_default) VALUES (?,?,?,?,?,?,?,?,?)",
                (user["id"], label, full_name, phone, address_line, city, province, postal_code, int(make_default)),
            )
            flash("Address saved.", "success")
        return redirect(url_for("account.addresses"))

    rows = db.query("SELECT * FROM addresses WHERE user_id = ? ORDER BY is_default DESC, id DESC", (user["id"],))
    return render_template("account/addresses.html", addresses=rows)


@bp.route("/addresses/<int:address_id>/delete", methods=["POST"])
@login_required
def delete_address(address_id):
    user = current_user()
    addr = db.query("SELECT * FROM addresses WHERE id = ? AND user_id = ?", (address_id, user["id"]), one=True)
    if addr:
        db.execute("DELETE FROM addresses WHERE id = ?", (address_id,))
        flash("Address removed.", "success")
    return redirect(url_for("account.addresses"))


@bp.route("/designs/<int:design_id>/delete", methods=["POST"])
@login_required
def delete_design(design_id):
    user = current_user()
    design = db.query("SELECT * FROM designs WHERE id = ? AND user_id = ?", (design_id, user["id"]), one=True)
    if design:
        db.execute("DELETE FROM designs WHERE id = ?", (design_id,))
        flash("Design deleted.", "success")
    return redirect(url_for("account.designs"))


@bp.route("/designs/<int:design_id>/add-to-cart", methods=["POST"])
@login_required
def add_design_to_cart(design_id):
    from ..helpers import calculate_customization_fee
    user = current_user()
    design = db.query("SELECT * FROM designs WHERE id = ? AND user_id = ?", (design_id, user["id"]), one=True)
    if not design:
        flash("Design not found.", "error")
        return redirect(url_for("account.designs"))
    product = db.query("SELECT * FROM products WHERE id = ?", (design["product_id"],), one=True)
    fee = calculate_customization_fee(design["design_data"])
    db.execute(
        "INSERT INTO cart_items (user_id, product_id, design_id, color, size, quantity, unit_price, "
        "customization_fee, preview_image) VALUES (?,?,?,?,?,1,?,?,?)",
        (user["id"], product["id"], design_id, design["color"], design["size"], product["base_price"],
         fee, design["preview_image"]),
    )
    flash(f"{design['name']} added to your cart.", "success")
    return redirect(url_for("cart.view_cart"))
