from flask import Flask, render_template, request, redirect
import mysql.connector

from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("DB_PASSWORD"),
        database="inventory_db"
    )
    return connection

@app.route('/')
def home():
    return 'Inventory Management System is running!'

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

        return redirect('/view-products')

    return render_template('add_product.html')
@app.route('/view-products')
def view_products():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM product")
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
    return redirect('/view-suppliers')

if __name__ == '__main__':
    app.run(debug=True)