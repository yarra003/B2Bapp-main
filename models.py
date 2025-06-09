from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'factory' or 'seller'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    factory = db.relationship('Factory', backref='factory_user', uselist=False, foreign_keys='Factory.user_id')
    orders = db.relationship('Order', backref='seller', foreign_keys='Order.seller_id')
    chats_started = db.relationship('Chat', backref='chat_user1', foreign_keys='Chat.user1_id')
    chats_received = db.relationship('Chat', backref='chat_user2', foreign_keys='Chat.user2_id')
    messages_sent = db.relationship('Message', backref='message_sender', foreign_keys='Message.sender_id')
    ratings = db.relationship('Rating', backref='user')
    comments = db.relationship('Comment', backref='user')
    wishlist = db.relationship('Wishlist', backref='user')
    cart = db.relationship('Cart', backref='user', uselist=False, cascade="all, delete-orphan")

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    factories = db.relationship('Factory', backref='category')

class Factory(db.Model):
    __tablename__ = 'factories'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    description = db.Column(db.Text)
    contact_info = db.Column(db.String(200))

    user = db.relationship('User', backref='factory_account', foreign_keys=[user_id])
    orders = db.relationship('Order', backref='factory', foreign_keys='Order.factory_id')
    products = db.relationship('Product', backref='factory', cascade="all, delete-orphan")

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    factory_id = db.Column(db.Integer, db.ForeignKey('factories.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    quantity = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ratings = db.relationship('Rating', backref='product')
    comments = db.relationship('Comment', backref='product')
    wishlist_items = db.relationship('Wishlist', backref='product')
    cart_items = db.relationship('CartItem', backref='product')

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    factory_id = db.Column(db.Integer, db.ForeignKey('factories.id'), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    shipping_address = db.Column(db.Text, nullable=False)
    payment_method = db.Column(db.String(50), nullable=True)

    items = db.relationship('OrderItem', backref='order', cascade="all, delete-orphan")
    receipt = db.relationship('Receipt', backref='order', uselist=False, cascade="all, delete-orphan")
    chat = db.relationship('Chat', back_populates='order', uselist=False, cascade="all, delete-orphan")

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

    product = db.relationship('Product')

class Receipt(db.Model):
    __tablename__ = 'receipts'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, unique=True)
    amount_paid = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Chat(db.Model):
    __tablename__ = 'chats'
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user1_typing = db.Column(db.Boolean, default=False)
    user2_typing = db.Column(db.Boolean, default=False)

    order = db.relationship('Order', back_populates='chat')
    messages = db.relationship('Message', backref='chat', cascade="all, delete-orphan")

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=True)
    attachment_url = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Rating(db.Model):
    __tablename__ = 'ratings'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1 to 5
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Wishlist(db.Model):
    __tablename__ = 'wishlists'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    added_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Cart(db.Model):
    __tablename__ = 'carts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship('CartItem', backref='cart', cascade="all, delete-orphan")

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('carts.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)