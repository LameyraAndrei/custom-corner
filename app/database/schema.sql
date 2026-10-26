-- Custom Corner database schema (SQLite)
-- Designed to be portable to MySQL/PostgreSQL with minimal changes.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS cart_items;
DROP TABLE IF EXISTS design_elements;
DROP TABLE IF EXISTS designs;
DROP TABLE IF EXISTS product_sizes;
DROP TABLE IF EXISTS product_colors;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS addresses;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    phone           TEXT,
    password_hash   TEXT NOT NULL,
    is_admin        INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE addresses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label           TEXT NOT NULL DEFAULT 'Home',
    full_name       TEXT NOT NULL,
    phone           TEXT,
    address_line    TEXT NOT NULL,
    city            TEXT NOT NULL,
    province        TEXT NOT NULL,
    postal_code     TEXT,
    is_default      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE categories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,
    icon            TEXT
);

CREATE TABLE products (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id         INTEGER NOT NULL REFERENCES categories(id),
    name                TEXT NOT NULL,
    slug                TEXT NOT NULL UNIQUE,
    description         TEXT,
    base_price          REAL NOT NULL,
    customization_fee   REAL NOT NULL DEFAULT 0,
    image               TEXT,
    material            TEXT,
    production_time     TEXT,
    mockup_shape        TEXT NOT NULL DEFAULT 'tshirt',
    has_back_side       INTEGER NOT NULL DEFAULT 0,
    stock               INTEGER NOT NULL DEFAULT 0,
    is_active           INTEGER NOT NULL DEFAULT 1,
    is_featured         INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE product_colors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    hex             TEXT NOT NULL
);

CREATE TABLE product_sizes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    name            TEXT NOT NULL
);

CREATE TABLE designs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id      INTEGER NOT NULL REFERENCES products(id),
    name            TEXT NOT NULL DEFAULT 'Untitled Design',
    color           TEXT,
    size            TEXT,
    design_data     TEXT NOT NULL,   -- JSON: full element scene graph (front/back)
    preview_image   TEXT,            -- data URL / static path of a flattened preview
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Kept for relational completeness / reporting; the authoritative design data
-- is the JSON blob in designs.design_data so a design can always be fully
-- reconstructed even if this normalized table is not queried directly.
CREATE TABLE design_elements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    design_id       INTEGER NOT NULL REFERENCES designs(id) ON DELETE CASCADE,
    element_type    TEXT NOT NULL,   -- 'text' | 'image'
    side            TEXT NOT NULL DEFAULT 'front'
);

CREATE TABLE cart_items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id          INTEGER NOT NULL REFERENCES products(id),
    design_id           INTEGER REFERENCES designs(id),
    color               TEXT,
    size                TEXT,
    quantity            INTEGER NOT NULL DEFAULT 1,
    unit_price          REAL NOT NULL,
    customization_fee   REAL NOT NULL DEFAULT 0,
    preview_image       TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    order_number    TEXT NOT NULL UNIQUE,
    status          TEXT NOT NULL DEFAULT 'Pending',
    subtotal        REAL NOT NULL,
    delivery_fee    REAL NOT NULL DEFAULT 0,
    total           REAL NOT NULL,
    full_name       TEXT NOT NULL,
    email           TEXT NOT NULL,
    phone           TEXT NOT NULL,
    address_line    TEXT NOT NULL,
    city            TEXT NOT NULL,
    province        TEXT NOT NULL,
    postal_code     TEXT,
    delivery_option TEXT NOT NULL DEFAULT 'Standard',
    payment_method  TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE order_items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id            INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id          INTEGER NOT NULL REFERENCES products(id),
    design_id           INTEGER REFERENCES designs(id),
    product_name        TEXT NOT NULL,
    color               TEXT,
    size                TEXT,
    quantity            INTEGER NOT NULL DEFAULT 1,
    unit_price          REAL NOT NULL,
    customization_fee   REAL NOT NULL DEFAULT 0,
    preview_image       TEXT,
    design_data         TEXT
);

CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_designs_user ON designs(user_id);
CREATE INDEX idx_cart_user ON cart_items(user_id);
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
