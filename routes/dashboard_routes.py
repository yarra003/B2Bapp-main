from datetime import datetime, timedelta
import os
from flask import Blueprint, current_app, jsonify, render_template, redirect, request, url_for, session, flash
from sqlalchemy import func
from models import Order, OrderItem, Product, User, db
from werkzeug.utils import secure_filename

dashboard_bp = Blueprint('dashboard', __name__)
UPLOAD_FOLDER = 'static/uploads'
@dashboard_bp.route('/dashboard', endpoint='dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('auth.index'))

    user = User.query.get(session['user_id'])

    if not user or not user.factory:
        flash('No factory linked to this user.', 'error')
        return redirect(url_for('auth.index'))

    factory = user.factory

    total_products = len(factory.products)
    total_orders = len(factory.orders)
    total_revenue = sum(order.total_price for order in factory.orders)

    # Show latest 5 orders, sorted by order_date descending
    recent_orders = (
        Order.query.filter_by(factory_id=factory.id)
        .order_by(Order.order_date.desc())
        .limit(5)
        .all()
    )

    # Low stock products under quantity 10
    low_stock_products = [p for p in factory.products if p.quantity < 10]

    return render_template(
        'dashboard.html',
        user=user,
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        recent_orders=recent_orders,
        low_stock_products=low_stock_products
    )

# ------------------------
# PRODUCT MANAGEMENT VIEW
# ------------------------
@dashboard_bp.route('/products', methods=['GET', 'POST'], endpoint='products')
def products():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('auth.index'))

    user = User.query.get(session['user_id'])
    if not user or not user.factory:
        flash('No factory linked to this user.', 'error')
        return redirect(url_for('auth.index'))

    factory = user.factory

    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price', type=float)
        quantity = request.form.get('quantity', type=int)
        description = request.form.get('description')
        image = request.files.get('image')

        if not name or price is None or quantity is None:
            flash('Please fill out all required fields (name, price, quantity).', 'error')
            return render_template('products.html', user=user, products=factory.products)

        image_url = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            upload_dir = os.path.join(current_app.root_path, UPLOAD_FOLDER)
            os.makedirs(upload_dir, exist_ok=True)
            image.save(os.path.join(upload_dir, filename))
            image_url = f'uploads/{filename}'

        new_product = Product(
            factory_id=factory.id,
            name=name,
            price=price,
            quantity=quantity,
            description=description,
            image_url=image_url
        )
        db.session.add(new_product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('dashboard.products'))

    return render_template('products.html', user=user, products=factory.products)

# ------------------------
# DELETE PRODUCTS ROUTE
# ------------------------
@dashboard_bp.route('/products/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully.', 'success')
    return redirect(url_for('dashboard.products'))

# ------------------------
# EDIT PRODUCTS ROUTE
# ------------------------
@dashboard_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'user_id' not in session:
        flash('You must be logged in to edit products.', 'error')
        return redirect(url_for('auth.index'))

    user = User.query.get(session['user_id'])
    if not user or not user.factory:
        flash('No factory linked to this user.', 'error')
        return redirect(url_for('auth.index'))

    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price', type=float)
        quantity = request.form.get('quantity', type=int)
        description = request.form.get('description')
        image = request.files.get('image')

        if not name or price is None or quantity is None:
            flash('Please fill out all required fields (name, price, quantity).', 'error')
            return render_template('edit_product.html', product=product, user=user)

        product.name = name
        product.price = price
        product.quantity = quantity
        product.description = description

        if image and image.filename:
            filename = secure_filename(image.filename)
            upload_dir = os.path.join(current_app.root_path, UPLOAD_FOLDER)
            os.makedirs(upload_dir, exist_ok=True)
            image.save(os.path.join(upload_dir, filename))
            product.image_url = f'uploads/{filename}'

        db.session.commit()
        flash('Product updated successfully.', 'success')
        return redirect(url_for('dashboard.products'))

    return render_template('edit_product.html', product=product, user=user)

@dashboard_bp.route('/dashboard/update_order_status', methods=['POST'])
def update_order_status():
    data = request.get_json()
    order_id = data.get('order_id')
    new_status = data.get('status')

    if not order_id or not new_status:
        return jsonify({'error': 'Missing order_id or status'}), 400

    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404

    allowed_statuses = ['Pending', 'Processing', 'Shipped', 'Delivered']
    if new_status not in allowed_statuses:
        return jsonify({'error': 'Invalid status value'}), 400

    order.status = new_status
    db.session.commit()

    return jsonify({'message': 'Order status updated successfully'})


# ------------------------
# ORDERS VIEW
# ------------------------
from sqlalchemy.orm import joinedload

@dashboard_bp.route('/orders', endpoint='orders')
def orders():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('auth.index'))

    user = User.query.get(session['user_id'])
    if not user or not user.factory:
        flash('No factory linked to this user.', 'error')
        return redirect(url_for('auth.index'))

    factory = user.factory

    factory_orders = (
        Order.query
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),  # load products per item
            joinedload(Order.seller)  # load the seller too
        )
        .filter_by(factory_id=factory.id)
        .order_by(Order.order_date.desc())
        .all()
    )

    return render_template('orders.html', user=user, orders=factory_orders)

# ------------------------
# ANALYTICS VIEW
# ------------------------
@dashboard_bp.route('/analytics', endpoint='analytics')
def analytics():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('auth.index'))

    user = User.query.get(session['user_id'])
    return render_template('analytics.html', user=user)

# ------------------------
# ANALYTICS DATA ENDPOINT
# ------------------------
@dashboard_bp.route('/analytics/data/<period>', methods=['GET'])
def get_analytics_data(period):
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in first.'}), 401

    user = User.query.get(session['user_id'])
    if not user or not user.factory:
        return jsonify({'error': 'No factory linked to this user.'}), 404

    factory = user.factory
    now = datetime.utcnow()

    # Helper function to get the start date based on period
    def get_start_date(period):
        if period == 'week':
            return now - timedelta(weeks=1)
        elif period == 'month':
            return now - timedelta(days=30)
        return datetime(2000, 1, 1)  # For 'all' time, no filter

    start_date = get_start_date(period)

    # Query orders within the selected time period for this factory
    orders_query = Order.query.filter(
        Order.factory_id == factory.id,
        Order.order_date >= start_date
    )

    # Total revenue
    total_revenue = db.session.query(func.sum(Order.total_price)).filter(
        Order.factory_id == factory.id,
        Order.order_date >= start_date
    ).scalar() or 0

    # Fulfilled orders = orders with status 'Delivered'
    fulfilled_orders = orders_query.filter(Order.status == 'Delivered').count()

    # Top 3 best-selling products
    top_products_query = db.session.query(
        Product, func.sum(OrderItem.quantity).label('total_sales')
    ).join(OrderItem, OrderItem.product_id == Product.id) \
     .join(Order, Order.id == OrderItem.order_id) \
     .filter(
         Order.factory_id == factory.id,
         Order.order_date >= start_date
     ) \
     .group_by(Product.id) \
     .order_by(func.sum(OrderItem.quantity).desc()) \
     .limit(3)

    top_products = [{'name': product.name} for product, _ in top_products_query]
    if not top_products:
        top_products = [{'name': 'You don’t have enough data yet.'}]

    # Sales over time (by day)
    sales_query = db.session.query(
        func.date(Order.order_date).label('date'),
        func.sum(Order.total_price).label('total_sales')
    ).filter(
        Order.factory_id == factory.id,
        Order.order_date >= start_date
    ).group_by(func.date(Order.order_date)) \
     .order_by(func.date(Order.order_date))

    sales_over_time = [{'date': str(date), 'sales': sales} for date, sales in sales_query]
    if not sales_over_time:
        sales_over_time = [{'date': 'No data', 'sales': 0}]

    # Low stock products (quantity < 10)
    low_stock_products = Product.query.filter(
        Product.factory_id == factory.id,
        Product.quantity < 10
    ).all()

    low_stock = [{'name': product.name, 'quantity': product.quantity} for product in low_stock_products]

    return jsonify({
        'total_revenue': total_revenue,
        'fulfilled_orders': fulfilled_orders,
        'top_products': top_products,
        'sales_over_time': sales_over_time,
        'low_stock': low_stock
    })
