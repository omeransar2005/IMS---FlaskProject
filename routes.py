from flask import render_template, url_for, redirect, flash, request
from flask_login import login_user, login_required, logout_user
from app import app, db, bcrypt
from models import User, InventoryItem, Sale, LowStock
from forms import RegisterForm, LoginForm
from datetime import datetime


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
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)



@app.route('/features')
def features():
    return render_template('features.html')


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

        # Check if new item is already below threshold
        threshold = 10  # Default threshold
        if quantity < threshold:
            low_stock_alert = LowStock(item_id=item.id, threshold=threshold)
            db.session.add(low_stock_alert)
            db.session.commit()
            flash('Item added successfully but it is below the stock threshold!')
        else:
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
            old_quantity = item.quantity
            item.item_name = request.form['item_name']
            item.quantity = int(request.form['quantity'])
            item.price = float(request.form['price'])

            # Check if item quantity is now below threshold
            threshold = 10  # Default threshold
            if item.quantity < threshold and old_quantity >= threshold:
                low_stock_alert = LowStock(item_id=item.id, threshold=threshold)
                db.session.add(low_stock_alert)
                flash('Item updated successfully! Note: Item is now below stock threshold.')
            # Check if item was previously below threshold but now is not
            elif item.quantity >= threshold and old_quantity < threshold:
                # Resolve any existing alerts
                low_stock_alerts = LowStock.query.filter_by(item_id=item.id, resolved=False).all()
                for alert in low_stock_alerts:
                    alert.resolved = True
                flash('Item updated successfully! Stock levels now adequate.')
            else:
                flash('Item updated successfully!')

            db.session.commit()
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
            # Delete related sales and low stock alerts
            Sale.query.filter_by(item_id=item_id).delete()
            LowStock.query.filter_by(item_id=item_id).delete()
            db.session.delete(item)
            db.session.commit()
            flash('Item and all related records deleted successfully!')
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
    sales = Sale.query.all()

    # Calculate total sales
    total_sales = sum(
        (sale.price_at_sale - (sale.price_at_sale * sale.discount_at_sale / 100)) * sale.quantity for sale in sales)

    # Group sales by item for reporting
    items_with_sales = []
    for item in InventoryItem.query.all():
        item_sales = Sale.query.filter_by(item_id=item.id).all()
        if item_sales:
            total_quantity = sum(sale.quantity for sale in item_sales)
            total_revenue = sum(
                (sale.price_at_sale - (sale.price_at_sale * sale.discount_at_sale / 100)) * sale.quantity for sale in
                item_sales)
            items_with_sales.append({
                'item': item,
                'total_quantity': total_quantity,
                'total_revenue': total_revenue
            })

    return render_template('sales_report.html', sales=sales, items_with_sales=items_with_sales, total_sales=total_sales)


@app.route('/dashboard/add_sales', methods=['GET', 'POST'])
@login_required
def add_sales():
    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        sold_qty = int(request.form['sold_quantity'])
        item = InventoryItem.query.get(item_id)

        if item and item.quantity >= sold_qty:
            # Update inventory quantity
            item.quantity -= sold_qty

            # Record the sale with current price and discount
            new_sale = Sale(
                item_id=item_id,
                quantity=sold_qty,
                price_at_sale=item.price,
                discount_at_sale=item.discount
            )
            db.session.add(new_sale)

            # Check if stock is now low after this sale
            threshold = 10  # Default threshold
            if item.quantity < threshold:
                # Check if there's already an unresolved alert
                existing_alert = LowStock.query.filter_by(item_id=item_id, resolved=False).first()
                if not existing_alert:
                    low_stock_alert = LowStock(item_id=item_id, threshold=threshold)
                    db.session.add(low_stock_alert)
                flash('Sales recorded! Warning: Item is now below stock threshold.')
            else:
                flash('Sales recorded successfully!')

            db.session.commit()
        else:
            flash('Insufficient stock or item not found.')
        return redirect(url_for('view_inventory'))

    inventory = InventoryItem.query.all()
    return render_template('add_sales.html', inventory=inventory)


@app.route('/dashboard/low_stock', methods=['GET'])
@login_required
def low_stock():
    # Get all current (unresolved) low stock alerts
    low_stock_alerts = LowStock.query.filter_by(resolved=False).all()

    # Get items that are currently below threshold but might not have alerts yet
    threshold = 10  # Default threshold
    low_inventory = InventoryItem.query.filter(InventoryItem.quantity < threshold).all()

    # Create a set of item IDs that already have alerts
    alerted_item_ids = {alert.item_id for alert in low_stock_alerts}

    # Create alerts for items that are below threshold but don't have alerts
    for item in low_inventory:
        if item.id not in alerted_item_ids:
            new_alert = LowStock(item_id=item.id, threshold=threshold)
            db.session.add(new_alert)
            alerted_item_ids.add(item.id)

    if alerted_item_ids:
        db.session.commit()
        # Refresh the alerts query to include newly created alerts
        low_stock_alerts = LowStock.query.filter_by(resolved=False).all()

    return render_template('low_stock.html', alerts=low_stock_alerts)


@app.route('/dashboard/resolve_low_stock', methods=['POST'])
@login_required
def resolve_low_stock():
    alert_id = int(request.form['alert_id'])
    alert = LowStock.query.get(alert_id)

    if alert:
        alert.resolved = True
        db.session.commit()
        flash('Low stock alert marked as resolved.')
    else:
        flash('Alert not found.')

    return redirect(url_for('low_stock'))


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

    inventory = InventoryItem.query.all()
    return render_template('apply_discount.html', inventory=inventory)


@app.route('/dashboard/view_sales_history', methods=['GET'])
@login_required
def view_sales_history():
    item_id = request.args.get('item_id')

    if item_id:
        # View sales history for a specific item
        item = InventoryItem.query.get(int(item_id))
        if item:
            sales = Sale.query.filter_by(item_id=int(item_id)).order_by(Sale.sale_date.desc()).all()
            return render_template('sales_history.html', item=item, sales=sales)
        else:
            flash('Item not found.')
            return redirect(url_for('view_inventory'))
    else:
        # View all sales history
        sales = Sale.query.order_by(Sale.sale_date.desc()).all()
        return render_template('sales_history.html', sales=sales)