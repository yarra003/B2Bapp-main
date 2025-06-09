from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import User, Product, Category, Factory, Order, OrderItem, Receipt, Chat, Rating, Comment, Wishlist, Cart, CartItem, db
from datetime import datetime
import logging

from routes.chat import get_or_create_chat

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

shop_bp = Blueprint('shop', __name__)

# ---------------- Helpers ----------------
def seller_required():
    logger.debug("Entering seller_required")
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        logger.debug("No user_id in session")
        return False, redirect(url_for('auth.index'))
    user = User.query.get(session['user_id'])
    if not user or user.role != 'seller':
        flash('Unauthorized access.', 'error')
        logger.debug(f"Invalid user or role: {user.id if user else None}")
        return False, redirect(url_for('auth.index'))
    logger.debug(f"seller_required passed for user {user.id}, {user.name}")
    return True, user

# ---------------- Browse Products ----------------
@shop_bp.route('/shop')
def browse():
    ok, user = seller_required()
    if not ok:
        return user

    selected_category = request.args.get('category', type=int)
    selected_factory = request.args.get('factory', type=int)

    categories = Category.query.all()
    factories = []
    query = Product.query
    if selected_category:
        factories = Factory.query.filter_by(category_id=selected_category).all()
        query = query.join(Factory).filter(Factory.category_id == selected_category)
    if selected_factory:
        factories = Factory.query.filter_by(id=selected_factory).all()
        query = query.filter(Product.factory_id == selected_factory)

    products = query.all()
    cart = Cart.query.filter_by(user_id=user.id).first()
    cart_quantity = sum(item.quantity for item in cart.items) if cart and hasattr(cart, 'items') and cart.items is not None else 0
    now = datetime.utcnow
    logger.debug(f"Rendering browse with now: {now}, cart_quantity: {cart_quantity}")
    return render_template(
        'shop/browse.html',
        user=user,
        categories=categories,
        factories=factories,
        products=products,
        selected_category=selected_category,
        selected_factory=selected_factory,
        now=now,
        cart_quantity=cart_quantity
    )

# ---------------- View Cart ----------------
@shop_bp.route('/cart')
def cart():
    ok, user = seller_required()
    if not ok:
        return user

    cart = Cart.query.filter_by(user_id=user.id).first()
    cart_items = []
    total_price = 0
    if cart and hasattr(cart, 'items') and cart.items is not None:
        for item in cart.items:
            subtotal = item.quantity * item.product.price
            total_price += subtotal
            cart_items.append({
                'product': item.product,
                'quantity': item.quantity,
                'subtotal': subtotal
            })

    cart_quantity = sum(item.quantity for item in cart.items) if cart and hasattr(cart, 'items') and cart.items is not None else 0
    now = datetime.utcnow
    logger.debug(f"Rendering cart with now: {now}, cart_quantity: {cart_quantity}")
    return render_template(
        'shop/cart.html',
        user=user,
        cart_items=cart_items,
        total_price=total_price,
        now=now,
        cart_quantity=cart_quantity
    )

# ---------------- Add to Cart ----------------
@shop_bp.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    ok, user = seller_required()
    if not ok:
        return user

    product = Product.query.get_or_404(product_id)
    quantity = request.form.get('quantity', 1, type=int)
    if quantity < 1:
        flash('Invalid quantity.', 'error')
        return redirect(request.referrer or url_for('shop.browse'))

    cart = Cart.query.filter_by(user_id=user.id).first()
    if not cart:
        cart = Cart(user_id=user.id)
        db.session.add(cart)
        db.session.flush()

    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    current_qty = cart_item.quantity if cart_item else 0
    if current_qty + quantity <= product.quantity:
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity)
            db.session.add(cart_item)
        db.session.commit()
        flash(f'Added {product.name} to cart.', 'success')
    else:
        flash(f'Only {product.quantity} units available for {product.name}.', 'error')
    return redirect(request.referrer or url_for('shop.browse'))

# ---------------- Update Cart Quantity ----------------
@shop_bp.route('/cart/update/<int:product_id>/<string:action>', methods=['POST'])
def update_cart_quantity(product_id, action):
    ok, user = seller_required()
    if not ok:
        return user

    product = Product.query.get_or_404(product_id)
    cart = Cart.query.filter_by(user_id=user.id).first()
    if not cart:
        flash('Cart is empty.', 'error')
        return redirect(url_for('shop.cart'))

    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    if not cart_item:
        flash('Product not in cart.', 'error')
        return redirect(url_for('shop.cart'))

    if action == 'increment':
        if cart_item.quantity < product.quantity:
            cart_item.quantity += 1
            db.session.commit()
        else:
            flash('Cannot exceed available stock.', 'warning')
    elif action == 'decrement':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            db.session.commit()
        else:
            db.session.delete(cart_item)
            db.session.commit()
            flash(f'{product.name} removed from cart.', 'info')
    else:
        flash('Invalid action.', 'error')

    return redirect(url_for('shop.cart'))

# ---------------- Remove from Cart ----------------
@shop_bp.route('/cart/remove/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    ok, user = seller_required()
    if not ok:
        return user

    cart = Cart.query.filter_by(user_id=user.id).first()
    if not cart:
        flash('Cart is empty.', 'error')
        return redirect(url_for('shop.cart'))

    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart.', 'success')
    else:
        flash('Item not found in cart.', 'error')
    return redirect(url_for('shop.cart'))

# ---------------- View Orders ----------------
@shop_bp.route('/my-orders', endpoint='orders')
def orders():
    ok, user = seller_required()
    if not ok:
        return user

    orders = Order.query.filter_by(seller_id=user.id).order_by(Order.order_date.desc()).all()
    now = datetime.utcnow
    logger.debug(f"Rendering orders with now: {now}")
    return render_template(
        'shop/customers_orders.html',
        user=user,
        orders=orders,
        now=now,
        cart_quantity=0
    )

# ---------------- Place Order ----------------
@shop_bp.route('/orders/place', methods=['POST'])
def place_order():
    ok, user = seller_required()
    if not ok:
        return user

    cart = Cart.query.filter_by(user_id=user.id).first()
    if not cart or not (hasattr(cart, 'items') and cart.items is not None):
        flash('Your cart is empty.', 'error')
        return redirect(url_for('shop.cart'))

    payment_method = request.form.get('payment_method')
    shipping_address = request.form.get('shipping_address')
    if not payment_method or not shipping_address:
        flash('Please provide payment method and shipping address.', 'error')
        return redirect(url_for('shop.cart'))

    product_ids = [item.product_id for item in cart.items]
    products = Product.query.filter(Product.id.in_(product_ids)).all()
    product_map = {p.id: p for p in products}
    factory_ids = {product_map[pid].factory_id for pid in product_ids}
    if len(factory_ids) != 1:
        flash('Order contains products from multiple factories, which is not supported yet.', 'error')
        return redirect(url_for('shop.cart'))
    factory_id = factory_ids.pop()
    total_price = sum(item.quantity * product_map[item.product_id].price for item in cart.items)

    try:
        order_date = datetime.utcnow()
        logger.debug(f"Creating order with order_date: {order_date}, cart_items: {[{'id': item.product_id, 'qty': item.quantity} for item in cart.items]}")
        new_order = Order(
            seller_id=user.id,
            factory_id=factory_id,
            total_price=total_price,
            payment_method=payment_method,
            shipping_address=shipping_address,
            status='Pending',
            order_date=order_date
        )
        db.session.add(new_order)
        db.session.flush()

        for item in cart.items:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=product_map[item.product_id].price
            )
            db.session.add(order_item)
            logger.debug(f"Added OrderItem: product_id={item.product_id}, quantity={item.quantity}")

        receipt = Receipt(
            order_id=new_order.id,
            amount_paid=total_price,
            payment_method=payment_method,
            payment_date=datetime.utcnow()
        )
        db.session.add(receipt)
        logger.debug(f"Created receipt for order_id={new_order.id}")

        factory = Factory.query.get(factory_id)
        if not factory or not factory.user:
            flash('Error: Factory has no associated user.', 'error')
            for item in cart.items:
                db.session.delete(item)
            db.session.commit()
            return redirect(url_for('shop.orders'))

        factory_user_id = factory.user.id
        chat = get_or_create_chat(user.id, factory_user_id, new_order.id)
        logger.debug(f"Created chat with id={chat.id}")

        # Clear cart
        for item in cart.items:
            db.session.delete(item)
        db.session.commit()
        logger.debug("Cart cleared and order committed")

        flash('Order placed successfully! Chat started with factory.', 'success')
        return redirect(url_for('chat.view_chat', chat_id=chat.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error placing order: {str(e)}', 'error')
        logger.error(f"Order placement failed: {str(e)}")
        return redirect(url_for('shop.cart'))

# ---------------- Product Details ----------------
@shop_bp.route('/product/<int:product_id>', endpoint='product_details')
def product_details(product_id):
    product = Product.query.get_or_404(product_id)
    factory = product.factory
    avg_rating = db.session.query(db.func.avg(Rating.rating)).filter_by(product_id=product_id).scalar() or 0
    ratings_count = Rating.query.filter_by(product_id=product_id).count()
    comments = Comment.query.filter_by(product_id=product_id).order_by(Comment.created_at.desc()).all()
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    user_rating = Rating.query.filter_by(product_id=product_id, user_id=user.id).first() if user else None
    is_wishlisted = Wishlist.query.filter_by(product_id=product_id, user_id=user.id).first() if user else False
    cart = Cart.query.filter_by(user_id=user.id).first() if user else None
    cart_quantity = sum(item.quantity for item in cart.items) if cart and hasattr(cart, 'items') and cart.items is not None else 0

    # Map user_id to rating for each comment
    comment_ratings = {}
    if comments:
        ratings = Rating.query.filter(
            Rating.user_id.in_([c.user_id for c in comments]),
            Rating.product_id == product_id
        ).all()
        comment_ratings = {r.user_id: r.rating for r in ratings}

    now = datetime.utcnow
    logger.debug(f"Rendering product_details with now: {now}, cart_quantity: {cart_quantity}")
    return render_template(
        'shop/product_details.html',
        product=product,
        factory=factory,
        avg_rating=avg_rating,
        ratings_count=ratings_count,
        comments=comments,
        comment_ratings=comment_ratings,
        user=user,
        user_rating=user_rating,
        is_wishlisted=is_wishlisted,
        cart_quantity=cart_quantity,
        now=now
    )

# ---------------- Add to Wishlist ----------------
@shop_bp.route('/wishlist/add/<int:product_id>', methods=['POST'])
def add_to_wishlist(product_id):
    ok, user = seller_required()
    if not ok:
        return user
    product = Product.query.get_or_404(product_id)
    if Wishlist.query.filter_by(user_id=user.id, product_id=product_id).first():
        flash('Product already in wishlist.', 'info')
    else:
        wishlist = Wishlist(user_id=user.id, product_id=product_id, added_at=datetime.utcnow())
        db.session.add(wishlist)
        db.session.commit()
        flash('Product added to wishlist!', 'success')
    return redirect(request.referrer or url_for('shop.product_details', product_id=product_id))

# ---------------- Remove from Wishlist ----------------
@shop_bp.route('/wishlist/remove/<int:product_id>', methods=['POST'])
def remove_from_wishlist(product_id):
    ok, user = seller_required()
    if not ok:
        return user
    wishlist_item = Wishlist.query.filter_by(user_id=user.id, product_id=product_id).first()
    if wishlist_item:
        db.session.delete(wishlist_item)
        db.session.commit()
        flash('Product removed from wishlist.', 'success')
    else:
        flash('Product not found in wishlist.', 'error')
    return redirect(request.referrer or url_for('shop.wishlist'))

# ---------------- View Wishlist ----------------
@shop_bp.route('/wishlist', endpoint='wishlist')
def wishlist():
    ok, user = seller_required()
    if not ok:
        return user

    wishlist_items = Wishlist.query.filter_by(user_id=user.id).all()
    product_ids = [item.product_id for item in wishlist_items]
    products = Product.query.filter(Product.id.in_(product_ids)).all()
    product_map = {p.id: p for p in products}
    cart = Cart.query.filter_by(user_id=user.id).first()
    cart_quantity = sum(item.quantity for item in cart.items) if cart and hasattr(cart, 'items') and cart.items is not None else 0

    now = datetime.utcnow
    logger.debug(f"Rendering wishlist with now: {now}, cart_quantity: {cart_quantity}")
    return render_template(
        'shop/wishlist.html',
        user=user,
        wishlist_items=wishlist_items,
        product_map=product_map,
        cart_quantity=cart_quantity,
        now=now
    )

# ---------------- Submit Review (Rating + Optional Comment) ----------------
@shop_bp.route('/product/<int:product_id>/review', methods=['POST'])
def submit_review(product_id):
    ok, user = seller_required()
    if not ok:
        return user
    product = Product.query.get_or_404(product_id)

    rating_value = request.form.get('rating', type=int)
    content = request.form.get('content', '').strip()

    if not rating_value or rating_value < 1 or rating_value > 5:
        return jsonify({'error': 'Invalid or missing rating.'}), 400

    existing_rating = Rating.query.filter_by(user_id=user.id, product_id=product_id).first()
    if existing_rating:
        return jsonify({'error': 'You have already rated this product.'}), 400

    try:
        new_rating = Rating(
            user_id=user.id,
            product_id=product_id,
            rating=rating_value,
            created_at=datetime.utcnow()
        )
        db.session.add(new_rating)

        comment_data = None
        if content:
            new_comment = Comment(
                user_id=user.id,
                product_id=product_id,
                content=content,
                created_at=datetime.utcnow()
            )
            db.session.add(new_comment)
            db.session.flush()
            comment_data = {
                'id': new_comment.id,
                'content': new_comment.content,
                'user_name': user.name,
                'created_at': new_comment.created_at.strftime('%Y-%m-%d %H:%M')
            }

        db.session.commit()
        avg_rating = db.session.query(db.func.avg(Rating.rating)).filter_by(product_id=product_id).scalar() or 0
        return jsonify({
            'success': True,
            'avg_rating': avg_rating,
            'comment': comment_data
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error submitting review: {str(e)}'}), 500