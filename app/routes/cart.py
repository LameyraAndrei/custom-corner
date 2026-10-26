import json
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash

from .. import db
from ..helpers import login_required, current_user, calculate_customization_fee

bp = Blueprint("cart", __name__)


@bp.route("/cart")
@login_required
def view_cart():
    user = current_user()
    items = db.query(
        "SELECT ci.*, p.name AS product_name, p.slug AS product_slug, p.image AS product_image, "
        "p.stock AS product_stock FROM cart_items ci JOIN products p ON p.id = ci.product_id "
        "WHERE ci.user_id = ? ORDER BY ci.created_at DESC",
        (user["id"],),
    )
    subtotal = sum((i["unit_price"] + i["customization_fee"]) * i["quantity"] for i in items)
    return render_template("cart.html", items=items, subtotal=subtotal)


@bp.route("/api/cart/add", methods=["POST"])
@login_required
def add_to_cart():
    user = current_user()
    payload = request.get_json(force=True, silent=True) or {}

    product_id = payload.get("product_id")
    product = db.query("SELECT * FROM products WHERE id = ? AND is_active = 1", (product_id,), one=True)
    if not product:
        return jsonify({"ok": False, "error": "Product not available."}), 400

    quantity = max(1, int(payload.get("quantity", 1)))
    if product["stock"] < quantity:
        return jsonify({"ok": False, "error": f"Only {product['stock']} left in stock."}), 400

    design_id = payload.get("design_id")
    color = payload.get("color", "")
    size = payload.get("size", "")
    preview_image = payload.get("preview_image")

    customization_fee = 0.0
    if design_id:
        design = db.query("SELECT * FROM designs WHERE id = ? AND user_id = ?", (design_id, user["id"]), one=True)
        if design:
            customization_fee = calculate_customization_fee(design["design_data"])
            preview_image = preview_image or design["preview_image"]

    cart_id = db.execute(
        "INSERT INTO cart_items (user_id, product_id, design_id, color, size, quantity, unit_price, "
        "customization_fee, preview_image) VALUES (?,?,?,?,?,?,?,?,?)",
        (user["id"], product_id, design_id, color, size, quantity, product["base_price"],
         customization_fee, preview_image),
    )
    count_row = db.query("SELECT COALESCE(SUM(quantity),0) c FROM cart_items WHERE user_id=?", (user["id"],), one=True)
    return jsonify({"ok": True, "cart_item_id": cart_id, "cart_count": count_row["c"]})


@bp.route("/api/cart/<int:item_id>", methods=["PATCH"])
@login_required
def update_cart_item(item_id):
    user = current_user()
    item = db.query("SELECT * FROM cart_items WHERE id = ? AND user_id = ?", (item_id, user["id"]), one=True)
    if not item:
        return jsonify({"ok": False, "error": "Item not found."}), 404
    payload = request.get_json(force=True, silent=True) or {}
    quantity = payload.get("quantity")
    if quantity is not None:
        quantity = max(1, min(99, int(quantity)))
        db.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (quantity, item_id))
    item = db.query("SELECT * FROM cart_items WHERE id = ?", (item_id,), one=True)
    line_total = (item["unit_price"] + item["customization_fee"]) * item["quantity"]
    return jsonify({"ok": True, "quantity": item["quantity"], "line_total": line_total})


@bp.route("/api/cart/<int:item_id>", methods=["DELETE"])
@login_required
def remove_cart_item(item_id):
    user = current_user()
    item = db.query("SELECT * FROM cart_items WHERE id = ? AND user_id = ?", (item_id, user["id"]), one=True)
    if not item:
        return jsonify({"ok": False, "error": "Item not found."}), 404
    db.execute("DELETE FROM cart_items WHERE id = ?", (item_id,))
    return jsonify({"ok": True})
