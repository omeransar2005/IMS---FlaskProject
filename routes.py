from flask import render_template, url_for, redirect, flash, request
from flask_login import login_user, login_required, logout_user, current_user
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

        existing_item = InventoryItem.query.filter_by(item_name=name).first()

        if existing_item:
            # Update existing item if it already exists
            existing_item.quantity += quantity
            existing_item.price = price
            existing_item.last_updated = datetime.utcnow()

            threshold = 10
            if existing_item.quantity >= threshold:
                existing_alerts = LowStock.query.filter_by(item_id=existing_item.id, resolved=False).all()
                for alert in existing_alerts:
                    alert.resolved = True
                    alert.resolved_by = current_user.id
                    alert.resolved_date = datetime.utcnow()
                flash('Item quantity updated and low stock alert resolved!')

            db.session.commit()
            return redirect(url_for('view_inventory'))

        # Add a new item
        item = InventoryItem(
            item_name=name,
            quantity=quantity,
            price=price,
            user_id=current_user.id
        )
        db.session.add(item)
        db.session.commit()

        threshold = 10
        if quantity < threshold:
            low_stock_alert = LowStock(
                item_id=item.id,
                threshold=threshold,
                user_id=current_user.id
            )
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
        try:
            item_id = int(request.form['item_id'])
            item = InventoryItem.query.get(item_id)

            if item:
                # Store old values for logging
                old_name = item.item_name
                old_quantity = item.quantity
                old_price = item.price

                # Update item details
                item.item_name = request.form['item_name']
                item.quantity = int(request.form['quantity'])
                item.price = float(request.form['price'])
                item.last_updated = datetime.utcnow()

                threshold = 10
                if item.quantity < threshold:
                    existing_alert = LowStock.query.filter_by(item_id=item_id, resolved=False).first()
                    if not existing_alert:
                        low_stock_alert = LowStock(
                            item_id=item_id,
                            threshold=threshold,
                            user_id=current_user.id
                        )
                        db.session.add(low_stock_alert)
                        flash(f'Item updated! Warning: Item is now below stock threshold.')
                else:
                    existing_alerts = LowStock.query.filter_by(item_id=item_id, resolved=False).all()
                    if existing_alerts:
                        for alert in existing_alerts:
                            alert.resolved = True
                            alert.resolved_by = current_user.id
                            alert.resolved_date = datetime.utcnow()
                        flash(
                            f'Item updated from "{old_name}" to "{item.item_name}"! Low stock alert has been resolved.')
                    else:
                        flash(f'Item updated from "{old_name}" to "{item.item_name}" successfully!')

                db.session.commit()
                print(
                    f"Item {item_id} updated: {old_name}->{item.item_name}, {old_quantity}->{item.quantity}, {old_price}->{item.price}")
            else:
                flash(f'Item with ID {item_id} not found.')
                print(f"Item with ID {item_id} not found in database")
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating item: {str(e)}')
            print(f"Error updating item: {str(e)}")

        return redirect(url_for('view_inventory'))
    else:
        item_id = request.args.get('id')
        item = None
        if item_id:
            item = InventoryItem.query.get(int(item_id))
        return render_template('update_item_record.html', item=item)


@app.route('/dashboard/delete_item', methods=['GET', 'POST'])
@login_required
def delete_item():
    if request.method == 'POST':
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
        item_id = request.args.get('id')
        if item_id:
            item = InventoryItem.query.get(int(item_id))
            if item:
                return render_template('delete_item.html', item=item, item_id=item_id)
        return render_template('delete_item.html')


@app.route('/dashboard/search', methods=['GET', 'POST'])
@login_required
def search():
    results = []
    search_query = ""

    if request.method == 'POST':
        search_query = request.form.get('search_query', '')
    else:
        search_query = request.args.get('search_query', '')

    if search_query:
        # Case-insensitive search
        results = InventoryItem.query.filter(
            InventoryItem.item_name.ilike(f'%{search_query}%')
        ).all()

    return render_template('search.html', results=results, search_query=search_query)


@app.route('/dashboard/sales_report', methods=['GET', 'POST'])
@login_required
def sales_report():
    sales = Sale.query.all()

    total_sales = sum(
        (sale.price_at_sale - (sale.price_at_sale * sale.discount_at_sale / 100)) * sale.quantity for sale in sales
    )

    items_with_sales = []
    for item in InventoryItem.query.all():
        item_sales = Sale.query.filter_by(item_id=item.id).all()
        if item_sales:
            total_quantity = sum(sale.quantity for sale in item_sales)
            total_revenue = sum(
                (sale.price_at_sale - (sale.price_at_sale * sale.discount_at_sale / 100)) * sale.quantity for sale in
                item_sales
            )
            items_with_sales.append({
                'item': item,
                'total_quantity': total_quantity,
                'total_revenue': total_revenue,
                'recorded_by': User.query.get(item_sales[0].user_id).username if item_sales[0].user_id else 'Unknown'
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
            item.quantity -= sold_qty
            item.last_updated = datetime.utcnow()

            new_sale = Sale(
                item_id=item_id,
                quantity=sold_qty,
                price_at_sale=item.price,
                discount_at_sale=item.discount,
                user_id=current_user.id
            )
            db.session.add(new_sale)

            threshold = 10
            if item.quantity < threshold:
                existing_alert = LowStock.query.filter_by(item_id=item_id, resolved=False).first()
                if not existing_alert:
                    low_stock_alert = LowStock(
                        item_id=item_id,
                        threshold=threshold,
                        user_id=current_user.id
                    )
                    db.session.add(low_stock_alert)
                flash('Sales recorded! Warning: Item is now below stock threshold.')
            else:
                flash('Sales recorded successfully!')

            db.session.commit()
        else:
            flash('Insufficient stock or item not found.')
        return redirect(url_for('view_inventory'))

    item_id = request.args.get('id')
    selected_item = None
    if item_id:
        selected_item = InventoryItem.query.get(int(item_id))

    inventory = InventoryItem.query.all()
    return render_template('add_sales.html', inventory=inventory, selected_item=selected_item)


@app.route('/dashboard/low_stock', methods=['GET'])
@login_required
def low_stock():
    active_alerts = LowStock.query.filter_by(resolved=False).all()
    resolved_alerts = LowStock.query.filter_by(resolved=True).order_by(LowStock.alert_date.desc()).all()

    threshold = 10
    low_inventory = InventoryItem.query.filter(InventoryItem.quantity < threshold).all()

    alerted_item_ids = {alert.item_id for alert in active_alerts}

    for item in low_inventory:
        if item.id not in alerted_item_ids:
            new_alert = LowStock(
                item_id=item.id,
                threshold=threshold,
                user_id=current_user.id
            )
            db.session.add(new_alert)
            alerted_item_ids.add(item.id)

    if len(low_inventory) > len(alerted_item_ids):
        db.session.commit()
        active_alerts = LowStock.query.filter_by(resolved=False).all()

    # Add user information to alerts
    for alert in active_alerts:
        alert.user_name = User.query.get(alert.user_id).username
        if alert.resolved_by:
            alert.resolved_by_name = User.query.get(alert.resolved_by).username
        else:
            alert.resolved_by_name = None

    for alert in resolved_alerts:
        alert.user_name = User.query.get(alert.user_id).username
        if alert.resolved_by:
            alert.resolved_by_name = User.query.get(alert.resolved_by).username
        else:
            alert.resolved_by_name = None

    return render_template('low_stock.html', active_alerts=active_alerts, resolved_alerts=resolved_alerts)


@app.route('/dashboard/apply_discount', methods=['GET', 'POST'])
@login_required
def apply_discount():
    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        discount = float(request.form['discount'])
        item = InventoryItem.query.get(item_id)
        if item:
            item.discount = discount
            item.last_updated = datetime.utcnow()
            db.session.commit()
            flash('Discount applied.')
        else:
            flash('Item not found.')
        return redirect(url_for('view_inventory'))

    item_id = request.args.get('id')
    selected_item = None
    if item_id:
        selected_item = InventoryItem.query.get(int(item_id))

    inventory = InventoryItem.query.all()
    return render_template('apply_discount.html', inventory=inventory, selected_item=selected_item)


@app.route('/dashboard/my_activity', methods=['GET'])
@login_required
def my_activity():
    # Get user's items
    user_items = InventoryItem.query.filter_by(user_id=current_user.id).all()

    # Get user's sales
    user_sales = Sale.query.filter_by(user_id=current_user.id).all()

    # Get low stock alerts created by user
    user_alerts = LowStock.query.filter_by(user_id=current_user.id).all()

    # Get alerts resolved by user
    resolved_alerts = LowStock.query.filter_by(resolved_by=current_user.id).all()

    return render_template(
        'my_activity.html',
        items=user_items,
        sales=user_sales,
        alerts=user_alerts,
        resolved_alerts=resolved_alerts
    )


@app.route('/dashboard/users', methods=['GET'])
@login_required
def users():
    all_users = User.query.all()

    # Prepare user statistics
    user_stats = []
    for user in all_users:
        items_count = InventoryItem.query.filter_by(user_id=user.id).count()
        sales_count = Sale.query.filter_by(user_id=user.id).count()
        alerts_count = LowStock.query.filter_by(user_id=user.id).count()

        # Calculate total sales value
        sales = Sale.query.filter_by(user_id=user.id).all()
        total_sales_value = sum(
            (sale.price_at_sale - (sale.price_at_sale * sale.discount_at_sale / 100)) * sale.quantity
            for sale in sales
        )

        user_stats.append({
            'user': user,
            'items_count': items_count,
            'sales_count': sales_count,
            'alerts_count': alerts_count,
            'total_sales_value': total_sales_value
        })

    return render_template('users.html', user_stats=user_stats)