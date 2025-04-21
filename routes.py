from flask import render_template, url_for, redirect, flash, request
from flask_login import login_user, login_required, logout_user
from app import app, db, bcrypt
from models import User, InventoryItem
from forms import RegisterForm, LoginForm

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/dashboard/view_inventory', methods=['GET'])
@login_required
def view_inventory():
    inventory = InventoryItem.query.all()
    return render_template('view_inventory.html', inventory=inventory)


@app.route('/dashboard/add_item', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        name = request.form['item_name']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])

        item = InventoryItem(item_name=name, quantity=quantity, price=price)
        db.session.add(item)
        db.session.commit()
        flash('Item added successfully!')
        return redirect(url_for('view_inventory'))
    return render_template('add_item.html')


@app.route('/dashboard/update_item', methods=['GET', 'POST'])
@login_required
def update_item_record():
    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        item = InventoryItem.query.get(item_id)
        if item:
            item.item_name = request.form['item_name']
            item.quantity = int(request.form['quantity'])
            item.price = float(request.form['price'])
            db.session.commit()
            flash('Item updated successfully!')
        else:
            flash('Item not found.')
        return redirect(url_for('view_inventory'))
    return render_template('update_item_record.html')


@app.route('/dashboard/delete_item', methods=['GET', 'POST'])
@login_required
def delete_item():
    if request.method == 'POST':
        # Handle form submission for delete action
        item_id = int(request.form['item_id'])
        item = InventoryItem.query.get(item_id)
        if item:
            db.session.delete(item)
            db.session.commit()
            flash('Item deleted successfully!')
        else:
            flash('Item not found.')
        return redirect(url_for('view_inventory'))
    else:
        # Handle GET request - show delete confirmation page
        item_id = request.args.get('id')  # Get ID from URL parameter
        if item_id:
            return render_template('delete_item.html', item_id=item_id)
        return render_template('delete_item.html')


@app.route('/dashboard/search', methods=['GET', 'POST'])
@login_required
def search():
    results = []
    if request.method == 'POST':
        query = request.form['search_query']
        results = InventoryItem.query.filter(InventoryItem.item_name.contains(query)).all()
    return render_template('search.html', results=results)


@app.route('/dashboard/sales_report', methods=['GET', 'POST'])
@login_required
def sales_report():
    inventory = InventoryItem.query.all()
    total_sales = sum(item.sales * (item.price - (item.price * item.discount / 100)) for item in inventory)
    return render_template('sales_report.html', inventory=inventory, total_sales=total_sales)


@app.route('/dashboard/add_sales', methods=['GET', 'POST'])
@login_required
def add_sales():
    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        sold_qty = int(request.form['sold_quantity'])
        item = InventoryItem.query.get(item_id)
        if item and item.quantity >= sold_qty:
            item.quantity -= sold_qty
            item.sales += sold_qty
            db.session.commit()
            flash('Sales updated!')
        else:
            flash('Insufficient stock or item not found.')
        return redirect(url_for('view_inventory'))
    return render_template('add_sales.html')


@app.route('/dashboard/low_stock', methods=['GET', 'POST'])
@login_required
def low_stock():
    threshold = 10
    low_stock_items = InventoryItem.query.filter(InventoryItem.quantity < threshold).all()
    return render_template('low_stock.html', items=low_stock_items)


@app.route('/dashboard/apply_discount', methods=['GET', 'POST'])
@login_required
def apply_discount():
    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        discount = float(request.form['discount'])
        item = InventoryItem.query.get(item_id)
        if item:
            item.discount = discount
            db.session.commit()
            flash('Discount applied.')
        else:
            flash('Item not found.')
        return redirect(url_for('view_inventory'))
    return render_template('apply_discount.html')