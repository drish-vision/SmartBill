from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysql_connector import MySQL
import bcrypt
import re
from functools import wraps
from flask import render_template, make_response
from weasyprint import HTML

app = Flask(__name__)
app.secret_key = "smartbill_secret"

# ---------- DATABASE CONFIG ----------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Drishya@2006'
app.config['MYSQL_DATABASE'] = 'invoice_system'
mysql = MySQL(app)

# ---------- DECORATORS ----------
def owner_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'owner_id' not in session:
            flash("Please login as owner to access this page.", "warning")
            return redirect(url_for('login_owner'))
        return f(*args, **kwargs)
    return decorated_function

def customer_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'customer_id' not in session:
            flash("Please login as customer to access this page.", "warning")
            return redirect(url_for('customer_login'))
        return f(*args, **kwargs)
    return decorated_function

# ---------- UTILITIES ----------
def validate_password_strength(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[\W_]', password):
        return False, "Password must contain at least one special character."
    return True, "Password is strong."

# ---------- ROUTES ----------


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/download_invoice/<int:invoice_id>')
@customer_login_required
def download_invoice(invoice_id):
    # Get invoice data from DB (example, adjust as needed)
    cursor = mysql.connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM invoices WHERE invoice_id = %s", (invoice_id,))
    invoice = cursor.fetchone()
    cursor.close()

    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for('customer_dashboard'))

    # Render HTML template for the invoice
    rendered_html = render_template('invoice_template.html', invoice=invoice)

    # Convert rendered HTML to PDF
    pdf = HTML(string=rendered_html).write_pdf()

    # Return PDF as a downloadable file
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{invoice_id}.pdf'
    return response

# --------- OWNER REGISTRATION & LOGIN ---------

@app.route('/register_owner', methods=['GET', 'POST'])
def register_owner():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        is_strong, message = validate_password_strength(password)
        if not is_strong:
            flash(message, 'danger')
            return render_template('register_owner.html')

        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO shop_owners (name, email, phone, password)
            VALUES (%s, %s, %s, %s)
        """, (name, email, phone, hashed_pw.decode('utf-8')))
        mysql.connection.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login_owner'))

    return render_template('register_owner.html')


@app.route('/shop_owner_login', methods=['GET', 'POST'])
def login_owner():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password'].encode('utf-8')

        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM shop_owners WHERE name = %s AND email = %s AND phone = %s",
                       (name, email, phone))
        owner = cursor.fetchone()

        if owner and bcrypt.checkpw(password, owner['password'].encode('utf-8')):
            session['owner_id'] = owner['owner_id']
            session['owner_name'] = owner['name']
            flash("Owner login successful!", "success")
            return redirect(url_for('owner_dashboard'))

        flash("Invalid credentials.", "danger")

    return render_template('owner_login.html')

@app.route('/owner_dashboard')
@owner_login_required
def owner_dashboard():
    cursor = mysql.connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customers WHERE owner_id = %s", (session['owner_id'],))
    customers = cursor.fetchall()

    labels = ["January", "February", "March", "April"]
    data = [100, 150, 120, 130]

    return render_template('owner_dashboard.html', customers=customers, labels=labels, data=data)

# --------- CUSTOMER REGISTRATION & LOGIN ---------

@app.route('/register_customer', methods=['GET', 'POST'])
def register_customer():
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')

        if not customer_id or not name or not email or not phone:
            flash('Please fill in all fields', 'danger')
            return render_template('register_customer.html')

        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO customers (customer_id, name, email, phone, owner_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (customer_id, name, email, phone, session.get('owner_id')))
        mysql.connection.commit()

        flash('Customer registered successfully!', 'success')
        return redirect(url_for('registered_customers'))

    return render_template('register_customer.html')

@app.route('/registered_customers')
@owner_login_required
def registered_customers():
    cursor = mysql.connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customers WHERE owner_id = %s", (session['owner_id'],))
    customers = cursor.fetchall()
    return render_template('registered_customers.html', customers=customers)

# --------- PRODUCT AND OFFER MANAGEMENT ---------

@app.route('/product_management')
@owner_login_required
def product_management():
    products = [
        {'id': 1, 'name': 'Product A', 'price': 100},
        {'id': 2, 'name': 'Product B', 'price': 150},
    ]
    return render_template('product_management.html', products=products)

@app.route('/offers_management')
@owner_login_required
def offers_management():
    offers = [
        {'id': 1, 'title': 'Discount 10%', 'valid_till': '2025-12-31'},
        {'id': 2, 'title': 'Buy 1 Get 1', 'valid_till': '2025-06-30'},
    ]
    return render_template('offers_management.html', offers=offers)

# --------- INVOICES ---------

@app.route('/invoices')
@owner_login_required
def invoices():
    invoices = [
        {'id': 1, 'customer_name': 'Alice', 'date': '2025-05-01', 'amount': '250.00'},
        {'id': 2, 'customer_name': 'Bob', 'date': '2025-05-05', 'amount': '150.00'},
    ]
    return render_template('invoices.html', invoices=invoices)

# --------- CUSTOMER PANEL --------
@app.route('/customer_login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        email = request.form.get('email')
        mobile = request.form.get('phone')  # use phone input for mobile value

        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customers WHERE email = %s AND mobile = %s", (email, mobile))
        customer = cursor.fetchone()

        if customer:
            session['customer_id'] = customer['customer_id']
            session['customer_name'] = customer['name']
            flash("Login successful!", "success")
            return redirect(url_for('customer_dashboard'))

        flash("Invalid credentials.", "danger")

    return render_template('customer_login.html')

@app.route('/customer_dashboard')
@customer_login_required
def customer_dashboard():
    customer_name = session.get('customer_name', 'Customer')
    return render_template('customer_dashboard.html', customer_name=customer_name)


@app.route('/purchase_history')
@customer_login_required
def purchase_history():
    purchases = [
        {'item': 'Product A', 'date': '2025-05-10', 'amount': '100.00'},
        {'item': 'Product B', 'date': '2025-05-12', 'amount': '150.00'},
    ]
    return render_template('purchase_history.html', purchases=purchases)


@app.route('/invoices_customer')
@customer_login_required
def invoices_customer():
    invoices = [
        {'id': 1, 'date': '2025-05-01', 'amount': '250.00'},
        {'id': 2, 'date': '2025-05-05', 'amount': '150.00'},
    ]
    return render_template('invoices_customer.html', invoices=invoices)


@app.route('/exchange_offers')
@customer_login_required
def exchange_offers():
    offers = [
        {'title': 'New Year Offer', 'discount': 15, 'valid_till': '2025-12-31'},
        {'title': 'Summer Sale', 'discount': 10, 'valid_till': '2025-06-30'},
    ]
    return render_template('exchange_offers.html', offers=offers)


@app.route('/available_offers')
@customer_login_required
def customer_offers():
    offers = [
        {'title': 'New Year Offer', 'discount': 15, 'valid_till': '2025-12-31'},
        {'title': 'Summer Sale', 'discount': 10, 'valid_till': '2025-06-30'},
    ]
    return render_template('customer_offers.html', offers=offers)


@app.route('/profile')
@customer_login_required
def profile_settings():
    customer = {
        'name': session.get('customer_name'),
        'email': 'customer@email.com'  # Placeholder, replace with actual DB data
    }
    return render_template('profile_settings.html', customer=customer)


@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", 'info')
    return redirect(url_for('home'))

# ---------- RUN APP ----------
if __name__ == '__main__':
    app.run(debug=True)
