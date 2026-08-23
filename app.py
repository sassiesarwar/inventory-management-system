from flask import Flask, render_template, request, redirect, flash, session
import mysql.connector

from dotenv import load_dotenv
import os

from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

@app.before_request
def require_login():
    allowed_routes = ['login', 'static']
    if 'user_id' not in session and request.endpoint not in allowed_routes:
        return redirect('/login')

def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("DB_PASSWORD"),
        database="inventory_db"
    )
    return connection

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user WHERE username=%s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[4]
            return redirect('/')
        else:
            return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/test-db')
def test_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        conn.close()
        return f"Database connected successfully! Tables: {tables}"
    except Exception as e:
        return f"Database connection failed: {str(e)}"

@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        product_name = request.form['product_name']
        sku = request.form['sku']
        unit_price = request.form['unit_price']
        quantity_in_stock = request.form['quantity_in_stock']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO product (product_name, sku, unit_price, quantity_in_stock) VALUES (%s, %s, %s, %s)",
            (product_name, sku, unit_price, quantity_in_stock)
        )
        conn.commit()
        conn.close()
        flash('Product added successfully!')
        return redirect('/view-products')

    return render_template('add_product.html')


@app.route('/view-products')
def view_products():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, c.category_name 
        FROM product p 
        LEFT JOIN category c ON p.category_id = c.category_id
    """)
    products = cursor.fetchall()
    conn.close()
    return render_template('view_products.html', products=products)

@app.route('/edit-product/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        product_name = request.form['product_name']
        sku = request.form['sku']
        unit_price = request.form['unit_price']
        quantity_in_stock = request.form['quantity_in_stock']

        cursor.execute(
            "UPDATE product SET product_name=%s, sku=%s, unit_price=%s, quantity_in_stock=%s WHERE product_id=%s",
            (product_name, sku, unit_price, quantity_in_stock, id)
        )
        conn.commit()
        conn.close()
        flash('Product updated successfully!')
        return redirect('/view-products')

    cursor.execute("SELECT * FROM product WHERE product_id=%s", (id,))
    product = cursor.fetchone()
    conn.close()
    return render_template('edit_product.html', product=product)


@app.route('/delete-product/<int:id>')
def delete_product(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM product WHERE product_id=%s", (id,))
    conn.commit()
    conn.close()
    flash('Product deleted successfully!')
    return redirect('/view-products')


@app.route('/add-category', methods=['GET', 'POST'])
def add_category():
    if request.method == 'POST':
        category_name = request.form['category_name']
        description = request.form['description']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO category (category_name, description) VALUES (%s, %s)",
            (category_name, description)
        )
        conn.commit()
        conn.close()
        flash('Category added successfully!')
        return redirect('/view-categories')

    return render_template('add_category.html')


@app.route('/view-categories')
def view_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM category")
    categories = cursor.fetchall()
    conn.close()
    return render_template('view_categories.html', categories=categories)


@app.route('/edit-category/<int:id>', methods=['GET', 'POST'])
def edit_category(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        category_name = request.form['category_name']
        description = request.form['description']

        cursor.execute(
            "UPDATE category SET category_name=%s, description=%s WHERE category_id=%s",
            (category_name, description, id)
        )
        conn.commit()
        conn.close()
        flash('Category updated successfully!')
        return redirect('/view-categories')

    cursor.execute("SELECT * FROM category WHERE category_id=%s", (id,))
    category = cursor.fetchone()
    conn.close()
    return render_template('edit_category.html', category=category)


@app.route('/delete-category/<int:id>')
def delete_category(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM category WHERE category_id=%s", (id,))
    conn.commit()
    conn.close()
    flash('Category deleted successfully!')
    return redirect('/view-categories')


@app.route('/add-supplier', methods=['GET', 'POST'])
def add_supplier():
    if request.method == 'POST':
        supplier_name = request.form['supplier_name']
        contact_person = request.form['contact_person']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO supplier (supplier_name, contact_person, phone, email, address) VALUES (%s, %s, %s, %s, %s)",
            (supplier_name, contact_person, phone, email, address)
        )
        conn.commit()
        conn.close()
        flash('Supplier added successfully!')
        return redirect('/view-suppliers')

    return render_template('add_supplier.html')


@app.route('/view-suppliers')
def view_suppliers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM supplier")
    suppliers = cursor.fetchall()
    conn.close()
    return render_template('view_suppliers.html', suppliers=suppliers)


@app.route('/edit-supplier/<int:id>', methods=['GET', 'POST'])
def edit_supplier(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        supplier_name = request.form['supplier_name']
        contact_person = request.form['contact_person']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']

        cursor.execute(
            "UPDATE supplier SET supplier_name=%s, contact_person=%s, phone=%s, email=%s, address=%s WHERE supplier_id=%s",
            (supplier_name, contact_person, phone, email, address, id)
        )
        conn.commit()
        conn.close()
        flash('Supplier updated successfully!')
        return redirect('/view-suppliers')

    cursor.execute("SELECT * FROM supplier WHERE supplier_id=%s", (id,))
    supplier = cursor.fetchone()
    conn.close()
    return render_template('edit_supplier.html', supplier=supplier)


@app.route('/delete-supplier/<int:id>')
def delete_supplier(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM supplier WHERE supplier_id=%s", (id,))
    conn.commit()
    conn.close()
    flash('Supplier deleted successfully!')
    return redirect('/view-suppliers')


@app.route('/add-purchase-order', methods=['GET', 'POST'])
def add_purchase_order():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        supplier_id = request.form['supplier_id']
        product_id = request.form['product_id']
        quantity = request.form['quantity']
        unit_cost = request.form['unit_cost']
        total = float(quantity) * float(unit_cost)

        cursor.execute(
            "INSERT INTO purchase_order (supplier_id, order_date, status, total_amount) VALUES (%s, CURDATE(), 'pending', %s)",
            (supplier_id, total)
        )
        conn.commit()
        po_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO purchase_order_item (purchase_order_id, product_id, quantity, unit_cost) VALUES (%s, %s, %s, %s)",
            (po_id, product_id, quantity, unit_cost)
        )
        conn.commit()
        conn.close()
        flash('Purchase order created successfully!')
        return redirect('/view-purchase-orders')

    cursor.execute("SELECT * FROM supplier")
    suppliers = cursor.fetchall()
    cursor.execute("SELECT * FROM product")
    products = cursor.fetchall()
    conn.close()
    return render_template('add_purchase_order.html', suppliers=suppliers, products=products)


@app.route('/view-purchase-orders')
def view_purchase_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT po.purchase_order_id, s.supplier_name, p.product_name, 
               poi.quantity, po.status, po.order_date
        FROM purchase_order po
        JOIN supplier s ON po.supplier_id = s.supplier_id
        JOIN purchase_order_item poi ON po.purchase_order_id = poi.purchase_order_id
        JOIN product p ON poi.product_id = p.product_id
    """)
    orders = cursor.fetchall()
    conn.close()
    return render_template('view_purchase_orders.html', orders=orders)


@app.route('/add-user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        role = request.form['role']
        email = request.form['email']

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (username, password_hash, full_name, role, email) VALUES (%s, %s, %s, %s, %s)",
            (username, hashed_password, full_name, role, email)
        )
        conn.commit()
        conn.close()
        flash('User added successfully!')
        return redirect('/view-users')

    return render_template('add_user.html')


@app.route('/view-users')
def view_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user")
    users = cursor.fetchall()
    conn.close()
    return render_template('view_users.html', users=users)


@app.route('/edit-user/<int:id>', methods=['GET', 'POST'])
def edit_user(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        username = request.form['username']
        full_name = request.form['full_name']
        role = request.form['role']
        email = request.form['email']

        cursor.execute(
            "UPDATE user SET username=%s, full_name=%s, role=%s, email=%s WHERE user_id=%s",
            (username, full_name, role, email, id)
        )
        conn.commit()
        conn.close()
        flash('User updated successfully!')
        return redirect('/view-users')

    cursor.execute("SELECT * FROM user WHERE user_id=%s", (id,))
    user = cursor.fetchone()
    conn.close()
    return render_template('edit_user.html', user=user)


@app.route('/delete-user/<int:id>')
def delete_user(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user WHERE user_id=%s", (id,))
    conn.commit()
    conn.close()
    flash('User deleted successfully!')
    return redirect('/view-users')


@app.route('/add-stock-transaction', methods=['GET', 'POST'])
def add_stock_transaction():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        product_id = request.form['product_id']
        transaction_type = request.form['transaction_type']
        quantity = int(request.form['quantity'])
        reference = request.form['reference']

        cursor.execute(
            "INSERT INTO stock_transaction (product_id, transaction_type, quantity, reference) VALUES (%s, %s, %s, %s)",
            (product_id, transaction_type, quantity, reference)
        )

        if transaction_type == 'IN':
            cursor.execute(
                "UPDATE product SET quantity_in_stock = quantity_in_stock + %s WHERE product_id = %s",
                (quantity, product_id)
            )
        else:
            cursor.execute(
                "UPDATE product SET quantity_in_stock = quantity_in_stock - %s WHERE product_id = %s",
                (quantity, product_id)
            )

        conn.commit()
        conn.close()
        flash('Stock transaction recorded successfully!')
        return redirect('/view-stock-transactions')

    cursor.execute("SELECT * FROM product")
    products = cursor.fetchall()
    conn.close()
    return render_template('add_stock_transaction.html', products=products)


@app.route('/view-stock-transactions')
def view_stock_transactions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT st.transaction_id, p.product_name, st.transaction_type, 
               st.quantity, st.transaction_date, st.reference
        FROM stock_transaction st
        JOIN product p ON st.product_id = p.product_id
        ORDER BY st.transaction_date DESC
    """)
    transactions = cursor.fetchall()
    conn.close()
    return render_template('view_stock_transactions.html', transactions=transactions)


@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM product")
    total_products = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM product WHERE quantity_in_stock <= reorder_level")
    low_stock_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM purchase_order WHERE status='pending'")
    pending_orders = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM supplier")
    total_suppliers = cursor.fetchone()[0]

    conn.close()
    return render_template('dashboard.html', total_products=total_products,
                            low_stock_count=low_stock_count,
                            pending_orders=pending_orders,
                            total_suppliers=total_suppliers)


if __name__ == '__main__':
    app.run(debug=True)