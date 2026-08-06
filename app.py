from flask import Flask
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

if __name__ == '__main__':
    app.run(debug=True)