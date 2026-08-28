from flask import Flask, render_template, request, redirect, flash, session
import mysql.connector
from dotenv import load_dotenv
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta  # ⬅️ IMPORTANT: Added for date handling

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

@app.before_request
def require_login():
    allowed_routes = ['login', 'static', 'forgot_password', 'home', 'dev_login']
    if 'user_id' in session or request.endpoint in allowed_routes:
        return

    if DEV_MODE:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user WHERE role='admin' LIMIT 1")
        user = cursor.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[4]
            return
        else:
            return "DEV_MODE is on, but no admin user exists yet. Run 'python create_admin.py' first."

    return redirect('/login')

@app.route('/dev-login/<role>')
def dev_login(role):
    if not DEV_MODE:
        return redirect('/login')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user WHERE role=%s LIMIT 1", (role,))
    user = cursor.fetchone()
    conn.close()
    if not user:
        return f"No user with role '{role}' exists yet. Add one from /add-user first."
    session['user_id'] = user[0]
    session['username'] = user[1]
    session['role'] = user[4]
    return redirect('/dashboard' if role == 'admin' else '/user/dashboard')

# ==================== DATABASE CONNECTION ====================
def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("DB_PASSWORD"),
        database="inventory_db"
    )
    return connection

# ==================== AUTH ROUTES ====================
@app.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user WHERE email=%s", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[4]
            
            # 🚀 REDIRECT BASED ON ROLE
            if user[4] == 'admin':
                return redirect('/dashboard')
            else:
                return redirect('/user/dashboard')
        else:
            return render_template('login.html', error='Invalid email or password')

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

# ==================== USER ROUTES (NEW!) ====================

@app.route('/user/dashboard')
def user_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = session['user_id']
    
    # Get user's checked out items
    cursor.execute("""
        SELECT c.*, p.product_name, p.sku, p.unit_price
        FROM checkout c
        JOIN product p ON c.product_id = p.product_id
        WHERE c.user_id = %s AND c.status IN ('checked_out', 'overdue')
        ORDER BY c.due_date ASC
    """, (user_id,))
    my_items = cursor.fetchall()
    
    # Get checkout history (last 10)
    cursor.execute("""
        SELECT c.*, p.product_name
        FROM checkout c
        JOIN product p ON c.product_id = p.product_id
        WHERE c.user_id = %s
        ORDER BY c.created_at DESC LIMIT 10
    """, (user_id,))
    history = cursor.fetchall()
    
    # Get available products
    cursor.execute("""
        SELECT p.*, c.category_name
        FROM product p
        LEFT JOIN category c ON p.category_id = c.category_id
        WHERE p.available_quantity > 0
        ORDER BY p.product_name
    """)
    available_products = cursor.fetchall()
    
    conn.close()
    
    return render_template('user_dashboard.html', 
                         my_items=my_items,
                         history=history,
                         available_products=available_products,
                         today=date.today())

@app.route('/checkout/<int:product_id>', methods=['GET', 'POST'])
def checkout_product(product_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get product details
    cursor.execute("SELECT * FROM product WHERE product_id = %s", (product_id,))
    product = cursor.fetchone()
    
    if not product:
        flash('Product not found!', 'error')
        return redirect('/user/dashboard')
    
    # Check if product is available
    if product[9] <= 0:  # available_quantity column
        flash('This product is currently not available!', 'error')
        return redirect('/user/dashboard')
    
    if request.method == 'POST':
        purpose = request.form['purpose']
        due_date = request.form['due_date']
        user_id = session['user_id']
        
        # Check if user has overdue items
        cursor.execute("""
            SELECT COUNT(*) FROM checkout 
            WHERE user_id = %s AND status = 'overdue'
        """, (user_id,))
        overdue_count = cursor.fetchone()[0]
        
        if overdue_count > 0:
            flash('⚠️ You have overdue items! Please return them first.', 'error')
            conn.close()
            return redirect('/user/dashboard')
        
        # Create checkout record
        cursor.execute("""
            INSERT INTO checkout (user_id, product_id, checkout_date, due_date, purpose, status)
            VALUES (%s, %s, CURDATE(), %s, %s, 'checked_out')
        """, (user_id, product_id, due_date, purpose))
        
        # Update product stock
        cursor.execute("""
            UPDATE product 
            SET available_quantity = available_quantity - 1,
                quantity_in_stock = quantity_in_stock - 1
            WHERE product_id = %s
        """, (product_id,))
        
        # Create stock transaction
        cursor.execute("""
            INSERT INTO stock_transaction (product_id, user_id, transaction_type, quantity, reference)
            VALUES (%s, %s, 'OUT', 1, %s)
        """, (product_id, user_id, f'Checked out by {session["username"]}'))
        
        conn.commit()
        conn.close()
        flash('✅ Product checked out successfully!')
        return redirect('/user/dashboard')
    
    conn.close()
    return render_template('checkout_product.html', product=product, today=date.today())

@app.route('/return/<int:checkout_id>', methods=['GET', 'POST'])
def return_product(checkout_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get checkout details
    cursor.execute("""
        SELECT c.*, p.product_name, p.product_id 
        FROM checkout c
        JOIN product p ON c.product_id = p.product_id
        WHERE c.checkout_id = %s AND c.user_id = %s
    """, (checkout_id, session['user_id']))
    checkout = cursor.fetchone()
    
    if not checkout:
        flash('Invalid checkout record!', 'error')
        return redirect('/user/dashboard')
    
    if checkout[5] == 'returned':  # status column
        flash('This item has already been returned!', 'warning')
        return redirect('/user/dashboard')
    
    if request.method == 'POST':
        condition = request.form['condition']
        notes = request.form['notes']
        
        # Update checkout record
        cursor.execute("""
            UPDATE checkout 
            SET return_date = CURDATE(), 
                status = 'returned',
                condition_on_return = %s,
                notes = %s
            WHERE checkout_id = %s
        """, (condition, notes, checkout_id))
        
        # Update product stock
        cursor.execute("""
            UPDATE product 
            SET available_quantity = available_quantity + 1,
                quantity_in_stock = quantity_in_stock + 1
            WHERE product_id = %s
        """, (checkout[2],))  # product_id from checkout
        
        # Create stock transaction
        cursor.execute("""
            INSERT INTO stock_transaction (product_id, user_id, transaction_type, quantity, reference)
            VALUES (%s, %s, 'IN', 1, %s)
        """, (checkout[2], session['user_id'], f'Returned by {session["username"]}'))
        
        conn.commit()
        conn.close()
        flash('✅ Product returned successfully!')
        return redirect('/user/dashboard')
    
    conn.close()
    return render_template('return_product.html', checkout=checkout)

@app.route('/user/history')
def user_history():
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = session['user_id']
    
    cursor.execute("""
        SELECT c.*, p.product_name, p.unit_price
        FROM checkout c
        JOIN product p ON c.product_id = p.product_id
        WHERE c.user_id = %s
        ORDER BY c.created_at DESC
    """, (user_id,))
    history = cursor.fetchall()
    
    conn.close()
    return render_template('user_history.html', history=history)

# ==================== PRODUCT ROUTES ====================

@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        product_name = request.form['product_name']
        sku = request.form['sku']
        description = request.form['description']
        unit_price = request.form['unit_price']
        quantity_in_stock = request.form['quantity_in_stock']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO product (product_name, sku, description, unit_price, quantity_in_stock, available_quantity) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (product_name, sku, description, unit_price, quantity_in_stock, quantity_in_stock)
        )
        conn.commit()
        conn.close()
        flash('✅ Product added successfully!')
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
        description = request.form['description']
        unit_price = request.form['unit_price']
        quantity_in_stock = request.form['quantity_in_stock']

        cursor.execute(
            """UPDATE product 
               SET product_name=%s, sku=%s, description=%s, unit_price=%s, quantity_in_stock=%s,
                   available_quantity = %s
               WHERE product_id=%s""",
            (product_name, sku, description, unit_price, quantity_in_stock, quantity_in_stock, id)
        )
        conn.commit()
        conn.close()
        flash('✅ Product updated successfully!')
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

# ==================== CATEGORY ROUTES ====================

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
        flash('✅ Category added successfully!')
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
        flash('✅ Category updated successfully!')
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

# ==================== SUPPLIER ROUTES ====================

@app.route('/add-supplier', methods=['GET', 'POST'])
def add_supplier():
    if request.method == 'POST':
        supplier_name = request.form['supplier_name']
        contact_person = request.form['contact_person']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']
        payment_terms = request.form['payment_terms']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO supplier (supplier_name, contact_person, phone, email, address, payment_terms) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (supplier_name, contact_person, phone, email, address, payment_terms)
        )
        conn.commit()
        conn.close()
        flash('✅ Supplier added successfully!')
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
        payment_terms = request.form['payment_terms']

        cursor.execute(
            """UPDATE supplier 
               SET supplier_name=%s, contact_person=%s, phone=%s, email=%s, address=%s, payment_terms=%s 
               WHERE supplier_id=%s""",
            (supplier_name, contact_person, phone, email, address, payment_terms, id)
        )
        conn.commit()
        conn.close()
        flash('✅ Supplier updated successfully!')
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

# ==================== PURCHASE ORDER ROUTES ====================

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
        flash('✅ Purchase order created successfully!')
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

@app.route('/receive-purchase-order/<int:id>')
def receive_purchase_order(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE purchase_order SET status='received' WHERE purchase_order_id=%s", (id,))

    cursor.execute("SELECT product_id, quantity FROM purchase_order_item WHERE purchase_order_id=%s", (id,))
    items = cursor.fetchall()

    for product_id, quantity in items:
        cursor.execute(
            "UPDATE product SET quantity_in_stock = quantity_in_stock + %s, available_quantity = available_quantity + %s WHERE product_id = %s",
            (quantity, quantity, product_id)
        )
        cursor.execute(
            """INSERT INTO stock_transaction (product_id, transaction_type, quantity, reference) 
               VALUES (%s, 'IN', %s, %s)""",
            (product_id, quantity, f'Received from Purchase Order #{id}')
        )

    conn.commit()
    conn.close()
    flash('✅ Purchase order marked as received — stock updated automatically!')
    return redirect('/view-purchase-orders')

# ==================== USER MANAGEMENT ROUTES ====================

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
        flash('✅ User added successfully!')
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
        flash('✅ User updated successfully!')
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

# ==================== STOCK TRANSACTION ROUTES ====================

@app.route('/add-stock-transaction', methods=['GET', 'POST'])
def add_stock_transaction():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        product_id = request.form['product_id']
        transaction_type = request.form['transaction_type']
        quantity = int(request.form['quantity'])
        reference = request.form['reference']

        if transaction_type == 'OUT':
            cursor.execute("SELECT quantity_in_stock FROM product WHERE product_id = %s", (product_id,))
            current_stock = cursor.fetchone()[0]
            if quantity > current_stock:
                conn.close()
                flash(f'❌ Cannot remove {quantity} units — only {current_stock} in stock!', 'error')
                return redirect('/add-stock-transaction')

        cursor.execute(
            "INSERT INTO stock_transaction (product_id, transaction_type, quantity, reference) VALUES (%s, %s, %s, %s)",
            (product_id, transaction_type, quantity, reference)
        )

        if transaction_type == 'IN':
            cursor.execute(
                "UPDATE product SET quantity_in_stock = quantity_in_stock + %s, available_quantity = available_quantity + %s WHERE product_id = %s",
                (quantity, quantity, product_id)
            )
        else:
            cursor.execute(
                "UPDATE product SET quantity_in_stock = quantity_in_stock - %s, available_quantity = available_quantity - %s WHERE product_id = %s",
                (quantity, quantity, product_id)
            )

        conn.commit()
        conn.close()
        flash('✅ Stock transaction recorded successfully!')
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

# ==================== DASHBOARD ====================

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

    cursor.execute("""
        SELECT c.category_name, COUNT(p.product_id) 
        FROM category c 
        LEFT JOIN product p ON c.category_id = p.category_id 
        GROUP BY c.category_id, c.category_name
    """)
    category_data = cursor.fetchall()
    category_names = [row[0] for row in category_data]
    category_counts = [row[1] for row in category_data]

    cursor.execute("""
        SELECT product_name, quantity_in_stock, reorder_level 
        FROM product 
        WHERE quantity_in_stock <= reorder_level 
        ORDER BY quantity_in_stock ASC LIMIT 5
    """)
    low_stock_items = cursor.fetchall()

    cursor.execute("""
        SELECT p.product_name, st.transaction_type, st.quantity, st.transaction_date
        FROM stock_transaction st
        JOIN product p ON st.product_id = p.product_id
        ORDER BY st.transaction_date DESC LIMIT 5
    """)
    recent_activity = cursor.fetchall()

    conn.close()
    return render_template('dashboard.html', total_products=total_products,
                            low_stock_count=low_stock_count,
                            pending_orders=pending_orders,
                            total_suppliers=total_suppliers,
                            category_names=category_names,
                            category_counts=category_counts,
                            low_stock_items=low_stock_items,
                            recent_activity=recent_activity)

# ==================== REPORTS ====================

@app.route('/reports')
def reports():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT product_name, quantity_in_stock, reorder_level 
        FROM product 
        WHERE quantity_in_stock <= reorder_level
    """)
    low_stock_report = cursor.fetchall()

    cursor.execute("SELECT SUM(unit_price * quantity_in_stock), SUM(quantity_in_stock) FROM product")
    result = cursor.fetchone()
    total_value = result[0] or 0
    total_units = result[1] or 0

    conn.close()
    return render_template('reports.html', low_stock_report=low_stock_report,
                            total_value=total_value, total_units=total_units)

# ==================== SETTINGS ====================

@app.route('/settings')
def settings():
    return render_template('settings.html')

# ==================== RUN APP ====================

if __name__ == '__main__':
    app.run(debug=True)