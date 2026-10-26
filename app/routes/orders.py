import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from .. import db
from ..helpers import login_required, current_user, generate_order_number, STATUS_STEPS, TRACKER_STEPS, status_index

bp = Blueprint("orders", __name__)


@bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    user = current_user()
    items = db.query(
        "SELECT ci.*, p.name AS product_name, p.image AS product_image, p.stock AS product_stock "
        "FROM cart_items ci JOIN products p ON p.id = ci.product_id WHERE ci.user_id = ?",
        (user["id"],),
    )
    if not items:
        flash("Your cart is empty. Add something before checking out.", "error")
        return redirect(url_for("shop.catalog"))

    subtotal = sum((i["unit_price"] + i["customization_fee"]) * i["quantity"] for i in items)
    addresses = db.query("SELECT * FROM addresses WHERE user_id = ? ORDER BY is_default DESC", (user["id"],))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        address_line = request.form.get("address_line", "").strip()
        city = request.form.get("city", "").strip()
        province = request.form.get("province", "").strip()
        postal_code = request.form.get("postal_code", "").strip()
        delivery_option = request.form.get("delivery_option", "Standard")
        payment_method = request.form.get("payment_method", "Cash on Delivery")

        errors = []
        for field, label in [(full_name, "Full name"), (email, "Email"), (phone, "Phone number"),
                              (address_line, "Address"), (city, "City"), (province, "Province")]:
            if not field:
                errors.append(f"{label} is required.")
        if delivery_option not in current_app.config["DELIVERY_FEES"]:
            errors.append("Please choose a valid delivery option.")
        if payment_method not in ("GCash", "Maya", "Cash on Delivery", "Online Payment"):
            errors.append("Please choose a valid payment method.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "checkout.html", items=items, subtotal=subtotal, addresses=addresses, form=request.form
            )

        delivery_fee = current_app.config["DELIVERY_FEES"][delivery_option]
        if subtotal >= current_app.config["FREE_SHIPPING_THRESHOLD"]:
            delivery_fee = 0.0
        total = subtotal + delivery_fee

        order_id = db.execute(
            "INSERT INTO orders (user_id, order_number, status, subtotal, delivery_fee, total, full_name, "
            "email, phone, address_line, city, province, postal_code, delivery_option, payment_method) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (user["id"], generate_order_number(), "Pending", subtotal, delivery_fee, total, full_name, email,
             phone, address_line, city, province, postal_code, delivery_option, payment_method),
        )

        for item in items:
            design_data = None
            if item["design_id"]:
                d = db.query("SELECT design_data FROM designs WHERE id = ?", (item["design_id"],), one=True)
                design_data = d["design_data"] if d else None
            db.execute(
                "INSERT INTO order_items (order_id, product_id, design_id, product_name, color, size, "
                "quantity, unit_price, customization_fee, preview_image, design_data) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (order_id, item["product_id"], item["design_id"], item["product_name"], item["color"],
                 item["size"], item["quantity"], item["unit_price"], item["customization_fee"],
                 item["preview_image"], design_data),
            )
            db.execute("UPDATE products SET stock = MAX(0, stock - ?) WHERE id = ?", (item["quantity"], item["product_id"]))

        db.execute("DELETE FROM cart_items WHERE user_id = ?", (user["id"],))

        flash("Payment simulated for this school project -- no real transaction was processed.", "info")
        return redirect(url_for("orders.confirmation", order_id=order_id))

    default_addr = addresses[0] if addresses else None
    return render_template(
        "checkout.html", items=items, subtotal=subtotal, addresses=addresses,
        form={"full_name": user["name"], "email": user["email"], "phone": user["phone"] or "",
              "address_line": default_addr["address_line"] if default_addr else "",
              "city": default_addr["city"] if default_addr else "",
              "province": default_addr["province"] if default_addr else "",
              "postal_code": default_addr["postal_code"] if default_addr else ""},
    )


@bp.route("/order-confirmation/<int:order_id>")
@login_required
def confirmation(order_id):
    user = current_user()
    order = db.query("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, user["id"]), one=True)
    if not order:
        return render_template("404.html"), 404
    items = db.query("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    return render_template("order_confirmation.html", order=order, items=items)


@bp.route("/order/<int:order_id>/track")
@login_required
def track(order_id):
    user = current_user()
    order = db.query("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, user["id"]), one=True)
    if not order:
        return render_template("404.html"), 404
    items = db.query("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    is_cancelled = order["status"] == "Cancelled"
    current_step = status_index(order["status"])
    return render_template(
        "order_tracking.html", order=order, items=items, steps=TRACKER_STEPS,
        current_step=current_step, is_cancelled=is_cancelled,
    )
