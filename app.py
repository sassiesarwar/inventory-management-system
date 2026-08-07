from flask import Flask, render_template, request, redirect
import mysql.connector

app = Flask(__name__)

def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Sassycs09@gmail.com",
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

if __name__ == '__main__':
    app.run(debug=True)