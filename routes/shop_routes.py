import logging
import sys
from datetime import datetime
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from models import Chat, Receipt, User, Product, Category, Factory, db, Order, OrderItem
from routes.chat import get_or_create_chat

# Force logging to console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

shop_bp = Blueprint('shop', __name__)

# ---------------- Helpers ----------------
def seller_required():
    print("*** ENTERING seller_required ***")
    logger.debug("Entering seller_required")
    print(f"*** Session: {session} ***")
    logger.debug(f"Session: {session}")
    if 'user_id' not in session:
        print("*** No user_id in session ***")
        logger.debug("No user_id in session")
        flash('Please log in first.', 'error')
        return False, redirect(url_for('auth.index'))
    user = User.query.get(session['user_id'])
    if not user or user.role != 'seller':
        print(f"*** Invalid user or role: {user.id if user else None} ***")
        logger.debug(f"Invalid user or role: {user.id if user else None}")
        flash('Unauthorized access.', 'error')
        return False, redirect(url_for('auth.index'))
    print(f"*** seller_required passed for user {user.id}, {user.name} ***")
    logger.debug(f"seller_required passed for user {user.id}, {user.name}")
    return True, user

def ensure_cart():
    print("*** ENTERING ensure_cart ***")
    logger.debug("Entering ensure_cart")
    if 'cart' not in session or not isinstance(session['cart'], dict):
        session['cart'] = {}
    print(f"*** Cart ensured: {session['cart']} ***")
    logger.debug(f"Cart ensured: {session['cart']}")

# ---------------- Browse Products ----------------
@shop_bp.route('/shop')
def browse():
    print("*** ENTERING browse ***")
    logger.debug("Entering browse")

    ok, resp = seller_required()
    if not ok:
        print("*** seller_required failed in browse ***")
        logger.debug("seller_required failed in browse")
        return resp

    ensure_cart()
    user = resp
    print(f"*** User: {user.id}, {user.name} ***")
    logger.debug(f"User: {user.id}, {user.name}")

    selected_category = request.args.get('category', type=int)
    selected_factory = request.args.get('factory', type=int)
    print(f"*** Selected category: {selected_category}, factory: {selected_factory} ***")
    logger.debug(f"Selected category: {selected_category}, factory: {selected_factory}")

    categories = Category.query.all()
    factories = Factory.query.all()
    print(f"*** Loaded {len(categories)} categories, {len(factories)} factories ***")
    logger.debug(f"Loaded {len(categories)} categories, {len(factories)} factories")

    query = Product.query
    if selected_category:
        query = query.join(Factory).filter(Factory.category_id == selected_category)
    if selected_factory:
        query = query.filter(Product.factory_id == selected_factory)

    products = query.all()
    cart_quantity = sum(session['cart'].values()) if session['cart'] else 0
    print(f"*** Loaded {len(products)} products, cart_quantity: {cart_quantity} ***")
    logger.debug(f"Loaded {len(products)} products, cart_quantity: {cart_quantity}")

    return render_template(
        'shop/browse.html',
        user=user,
        categories=categories,
        factories=factories,
        products=products,
        selected_category=selected_category,
        selected_factory=selected_factory,
        now=datetime.utcnow,
        cart_quantity=cart_quantity
    )

# ---------------- View Cart ----------------
@shop_bp.route('/cart')
def cart():
    print("*** ENTERING cart ***")
    logger.debug("Entering cart")

    ok, resp = seller_required()
    if not ok:
        print("*** seller_required failed in cart ***")
        logger.debug("seller_required failed in cart")
        return resp

    ensure_cart()
    user = resp
    print(f"*** User: {user.id}, {user.name} ***")
    logger.debug(f"User: {user.id}, {user.name}")

    cart = session['cart']
    print(f"*** Cart: {cart} ***")
    logger.debug(f"Cart: {cart}")

    product_ids = list(cart.keys())
    products = Product.query.filter(Product.id.in_(product_ids)).all()
    product_map = {p.id: p for p in products}
    print(f"*** Loaded {len(products)} products for cart ***")
    logger.debug(f"Loaded {len(products)} products for cart")

    cart_items = []
    total_price = 0
    for pid_str, qty in cart.items():
        pid = int(pid_str)
        product = product_map.get(pid)
        if product:
            subtotal = product.price * qty
            total_price += subtotal
            cart_items.append({
                'product': product,
                'quantity': qty,
                'subtotal': subtotal
            })
    print(f"*** Cart items: {len(cart_items)}, Total price: {total_price} ***")
    logger.debug(f"Cart items: {len(cart_items)}, Total price: {total_price}")

    return render_template(
        'shop/cart.html',
        user=user,
        cart_items=cart_items,
        total_price=total_price,
        now=datetime.utcnow,
        cart_quantity=sum(cart.values()) if cart else 0
    )

# ---------------- Add to Cart ----------------
@shop_bp.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    print(f"*** ENTERING add_to_cart with product_id={product_id} ***")
    logger.debug(f"Entering add_to_cart with product_id={product_id}")

    ok, resp = seller_required()
    if not ok:
        print("*** seller_required failed in add_to_cart ***")
        logger.debug("seller_required failed in add_to_cart")
        return resp

    ensure_cart()
    product = Product.query.get_or_404(product_id)
    print(f"*** Product: {product.id}, {product.name}, quantity available: {product.quantity} ***")
    logger.debug(f"Product: {product.id}, {product.name}, quantity available: {product.quantity}")

    cart = session['cart']
    current_qty = cart.get(str(product_id), 0)
    print(f"*** Current quantity in cart for product {product_id}: {current_qty} ***")
    logger.debug(f"Current quantity in cart for product {product_id}: {current_qty}")

    if current_qty < product.quantity:
        cart[str(product_id)] = current_qty + 1
        session['cart'] = cart
        flash(f'Added {product.name} to cart.', 'success')
        print(f"*** Added {product.name} to cart, new cart: {cart} ***")
        logger.debug(f"Added {product.name} to cart, new cart: {cart}")
    else:
        flash(f'Only {product.quantity} units available for {product.name}.', 'error')
        print(f"*** Stock limit reached for {product.name} ***")
        logger.debug(f"Stock limit reached for {product.name}")

    return redirect(request.referrer or url_for('shop.browse'))

# ---------------- Update Cart Quantity (+ / -) ----------------
@shop_bp.route('/cart/update/<int:product_id>/<string:action>', methods=['POST'])
def update_cart_quantity(product_id, action):
    print(f"*** ENTERING update_cart_quantity with product_id={product_id}, action={action} ***")
    logger.debug(f"Entering update_cart_quantity with product_id={product_id}, action={action}")

    ok, resp = seller_required()
    if not ok:
        print("*** seller_required failed in update_cart_quantity ***")
        logger.debug("seller_required failed in update_cart_quantity")
        return resp

    ensure_cart()
    cart = session['cart']
    pid = str(product_id)
    print(f"*** Cart: {cart} ***")
    logger.debug(f"Cart: {cart}")

    product = Product.query.get_or_404(product_id)
    print(f"*** Product: {product.id}, {product.name}, quantity available: {product.quantity} ***")
    logger.debug(f"Product: {product.id}, {product.name}, quantity available: {product.quantity}")

    if pid not in cart:
        flash("Product not in cart.", "error")
        print(f"*** Product {product_id} not in cart ***")
        logger.debug(f"Product {product_id} not in cart")
        return redirect(url_for('shop.cart'))

    if action == 'increment':
        if cart[pid] < product.quantity:
            cart[pid] += 1
            print(f"*** Incremented quantity for product {product_id} to {cart[pid]} ***")
            logger.debug(f"Incremented quantity for product {product_id} to {cart[pid]}")
        else:
            flash("Cannot exceed available stock.", "warning")
            print(f"*** Cannot increment, stock limit reached for product {product_id} ***")
            logger.debug(f"Cannot increment, stock limit reached for product {product_id}")

    elif action == 'decrement':
        if cart[pid] > 1:
            cart[pid] -= 1
            print(f"*** Decremented quantity for product {product_id} to {cart[pid]} ***")
            logger.debug(f"Decremented quantity for product {product_id} to {cart[pid]}")
        elif cart[pid] == 1:
            del cart[pid]
            flash(f"{product.name} removed from cart.", "info")
            print(f"*** Removed product {product_id} from cart ***")
            logger.debug(f"Removed product {product_id} from cart")
        else:
            flash("Quantity can't be less than 0.", "warning")
            print(f"*** Cannot decrement, quantity already 0 for product {product_id} ***")
            logger.debug(f"Cannot decrement, quantity already 0 for product {product_id}")

    else:
        flash("Invalid action.", "error")
        print(f"*** Invalid action: {action} ***")
        logger.debug(f"Invalid action: {action}")

    session['cart'] = cart
    return redirect(url_for('shop.cart'))

# ---------------- Remove from Cart ----------------
@shop_bp.route('/cart/remove/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    print(f"*** ENTERING remove_from_cart with product_id={product_id} ***")
    logger.debug(f"Entering remove_from_cart with product_id={product_id}")

    ok, resp = seller_required()
    if not ok:
        print("*** seller_required failed in remove_from_cart ***")
        logger.debug("seller_required failed in remove_from_cart")
        return resp

    ensure_cart()
    cart = session['cart']
    if str(product_id) in cart:
        del cart[str(product_id)]
        session['cart'] = cart
        flash('Item removed from cart.', 'success')
        print(f"*** Removed product {product_id} from cart ***")
        logger.debug(f"Removed product {product_id} from cart")
    else:
        flash('Item not found in cart.', 'error')
        print(f"*** Product {product_id} not found in cart ***")
        logger.debug(f"Product {product_id} not found in cart")
    return redirect(url_for('shop.cart'))

# ---------------- View Orders ----------------
@shop_bp.route('/my-orders', endpoint='orders')
def orders():
    print("*** ENTERING orders ***")
    logger.debug("Entering orders")

    ok, resp = seller_required()
    if not ok:
        print("*** seller_required failed in orders ***")
        logger.debug("seller_required failed in orders")
        return resp

    user = resp
    print(f"*** User: {user.id}, {user.name} ***")
    logger.debug(f"User: {user.id}, {user.name}")

    orders = Order.query.filter_by(seller_id=user.id).order_by(Order.order_date.desc()).all()
    print(f"*** Loaded {len(orders)} orders for user {user.id} ***")
    logger.debug(f"Loaded {len(orders)} orders for user {user.id}")

    return render_template(
        'shop/customers_orders.html',
        user=user,
        orders=orders,
        now=datetime.utcnow
    )

# ---------------- Place Order ----------------
@shop_bp.route('/orders/place', methods=['POST'])
def place_order():
    print("*** START place_order ***")
    logger.debug("START place_order")
    print(f"*** Request form: {request.form} ***")
    logger.debug(f"Request form: {request.form}")
    print(f"*** Session: {session} ***")
    logger.debug(f"Session: {session}")

    ok, resp = seller_required()
    if not ok:
        print("*** seller_required failed, redirecting ***")
        logger.debug("seller_required failed, redirecting")
        return resp

    print("*** Passed seller_required ***")
    logger.debug("Passed seller_required")

    ensure_cart()
    user = resp
    print(f"*** User: {user.id}, {user.name} ***")
    logger.debug(f"User: {user.id}, {user.name}")

    cart = session['cart']
    print(f"*** Cart: {cart} ***")
    logger.debug(f"Cart: {cart}")
    if not cart:
        print("*** Cart is empty ***")
        logger.debug("Cart is empty")
        flash('Your cart is empty.', 'error')
        return redirect(url_for('shop.cart'))

    payment_method = request.form.get('payment_method')
    shipping_address = request.form.get('shipping_address')
    print(f"*** Payment method: {payment_method}, Shipping address: {shipping_address} ***")
    logger.debug(f"Payment method: {payment_method}, Shipping address: {shipping_address}")

    if not payment_method:
        print("*** No payment method provided ***")
        logger.debug("No payment method provided")
        flash('Please select a payment method.', 'error')
        return redirect(url_for('shop.cart'))

    product_ids = list(map(int, cart.keys()))
    products = Product.query.filter(Product.id.in_(product_ids)).all()
    product_map = {p.id: p for p in products}
    print(f"*** Products in cart: {len(products)} ***")
    logger.debug(f"Products in cart: {len(products)}")

    factory_ids = {product_map[pid].factory_id for pid in product_ids}
    print(f"*** Factory IDs: {factory_ids} ***")
    logger.debug(f"Factory IDs: {factory_ids}")
    if len(factory_ids) != 1:
        print("*** Multiple factories detected ***")
        logger.debug("Multiple factories detected")
        flash('Order contains products from multiple factories, which is not supported yet.', 'error')
        return redirect(url_for('shop.cart'))
    factory_id = factory_ids.pop()
    print(f"*** Factory ID: {factory_id} ***")
    logger.debug(f"Factory ID: {factory_id}")

    total_price = sum(product_map[int(pid)].price * qty for pid, qty in cart.items())
    print(f"*** Total price: {total_price} ***")
    logger.debug(f"Total price: {total_price}")

    try:
        # Create the Order
        new_order = Order(
            seller_id=user.id,
            factory_id=factory_id,
            total_price=total_price,
            payment_method=payment_method,
            shipping_address=shipping_address,
            status='Pending'
        )
        db.session.add(new_order)
        db.session.flush()
        print(f"*** Created order with ID: {new_order.id} ***")
        logger.debug(f"Created order with ID: {new_order.id}")

        # Add OrderItems
        for pid_str, qty in cart.items():
            pid = int(pid_str)
            product = product_map.get(pid)
            if product:
                item = OrderItem(
                    order_id=new_order.id,
                    product_id=product.id,
                    quantity=qty,
                    unit_price=product.price
                )
                db.session.add(item)
                print(f"*** Added OrderItem for product ID: {pid}, quantity: {qty} ***")
                logger.debug(f"Added OrderItem for product ID: {pid}, quantity: {qty}")

        # Create Receipt
        receipt = Receipt(
            order_id=new_order.id,
            amount_paid=total_price,
            payment_method=payment_method,
            payment_date=datetime.utcnow()
        )
        db.session.add(receipt)
        print(f"*** Created receipt for order ID: {new_order.id} ***")
        logger.debug(f"Created receipt for order ID: {new_order.id}")

        # Create chat
        factory = Factory.query.get(factory_id)
        print(f"*** Factory: {factory_id}, user_id: {factory.user_id if factory else None} ***")
        logger.debug(f"Factory: {factory_id}, user_id: {factory.user_id if factory else None}")
        if not factory or not factory.user:
            print(f"*** ERROR: Factory {factory_id} has no associated user ***")
            logger.error(f"Factory {factory_id} has no associated user")
            flash('Error: Factory has no associated user.', 'error')
            db.session.commit()
            session['cart'] = {}
            return redirect(url_for('shop.orders'))

        factory_user_id = factory.user.id
        print(f"*** Attempting to create chat between user {user.id} and factory user {factory_user_id} for order {new_order.id} ***")
        logger.debug(f"Attempting to create chat between user {user.id} and factory user {factory_user_id} for order {new_order.id}")

        chat = get_or_create_chat(user.id, factory_user_id, new_order.id)
        print(f"*** Chat created with ID: {chat.id} ***")
        logger.debug(f"Chat created with ID: {chat.id}")

        db.session.commit()
        print("*** Database committed successfully ***")
        logger.debug("Database committed successfully")

        session['cart'] = {}
        flash('Order placed successfully! Chat started with factory.', 'success')
        return redirect(url_for('chat.view_chat', chat_id=chat.id))

    except Exception as e:
        db.session.rollback()
        print(f"*** ERROR in place_order: {str(e)} ***")
        logger.error(f"Error in place_order: {str(e)}")
        flash(f"Error placing order: {str(e)}", 'error')
        return redirect(url_for('shop.cart'))