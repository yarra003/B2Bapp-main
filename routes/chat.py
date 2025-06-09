import logging
import sys
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, session
from models import Factory, Order, db, Chat, Message, User
from datetime import datetime

# Force logging to console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

# Custom authentication check
def user_required():
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return False, redirect(url_for('auth.index'))
    user = User.query.get(session['user_id'])
    if not user:
        flash('User not found.', 'error')
        session.pop('user_id', None)
        return False, redirect(url_for('auth.index'))
    return True, user

# ---------------- List All Chats ----------------
@chat_bp.route('/', endpoint='list_chats')
def chat_list():
    print("*** ENTERING chat_list ***")
    logger.debug("Entering chat_list")

    ok, resp = user_required()
    if not ok:
        print("*** user_required failed in chat_list ***")
        logger.debug("user_required failed in chat_list")
        return resp

    user = resp
    print(f"*** User in chat_list: {user.id}, {user.name}, role: {user.role} ***")
    logger.debug(f"User in chat_list: {user.id}, {user.name}, role: {user.role}")

    chats = Chat.query.filter(
        (Chat.user1_id == user.id) | (Chat.user2_id == user.id)
    ).order_by(Chat.started_at.desc()).all()
    print(f"*** Found {len(chats)} chats for user {user.id} ***")
    logger.debug(f"Found {len(chats)} chats for user {user.id}")

    template = 'chat/factory_chat_list.html' if user.role == 'factory' else 'chat/chat_list.html'
    return render_template(template, user=user, chats=chats)

# ---------------- View Chat ----------------
@chat_bp.route('/<int:chat_id>', endpoint='view_chat')
def view_chat(chat_id):
    print(f"*** ENTERING view_chat with chat_id={chat_id} ***")
    logger.debug(f"Entering view_chat with chat_id={chat_id}")

    ok, resp = user_required()
    if not ok:
        print("*** user_required failed in view_chat ***")
        logger.debug("user_required failed in view_chat")
        return resp

    user = resp
    chat = Chat.query.get_or_404(chat_id)
    print(f"*** Chat loaded: ID={chat.id}, user1_id={chat.user1_id}, user2_id={chat.user2_id}, order_id={chat.order_id} ***")
    logger.debug(f"Chat loaded: ID={chat.id}, user1_id={chat.user1_id}, user2_id={chat.user2_id}, order_id={chat.order_id}")

    if user.id not in (chat.user1_id, chat.user2_id):
        print("*** Unauthorized access to chat ***")
        logger.error("Unauthorized access to chat")
        abort(403)

    messages = Message.query.filter_by(chat_id=chat.id).order_by(Message.timestamp.asc()).all()
    print(f"*** Loaded {len(messages)} messages for chat {chat.id} ***")
    logger.debug(f"Loaded {len(messages)} messages for chat {chat.id}")

    template = 'chat/factory_chat_room.html' if user.role == 'factory' else 'chat/chat_room.html'
    return render_template(template, user=user, chat=chat, messages=messages)

# ---------------- Send Message ----------------
@chat_bp.route('/<int:chat_id>/send', methods=['POST'])
def send_message(chat_id):
    print(f"*** ENTERING send_message with chat_id={chat_id} ***")
    logger.debug(f"Entering send_message with chat_id={chat_id}")

    ok, resp = user_required()
    if not ok:
        print("*** user_required failed in send_message ***")
        logger.debug("user_required failed in send_message")
        return resp

    user = resp
    chat = Chat.query.get_or_404(chat_id)
    if user.id not in (chat.user1_id, chat.user2_id):
        print("*** Unauthorized access to send_message ***")
        logger.error("Unauthorized access to send_message")
        return jsonify({'error': 'Unauthorized'}), 403

    content = request.form.get('content', '').strip()
    print(f"*** Message content: {content} ***")
    logger.debug(f"Message content: {content}")

    if content:
        new_msg = Message(
            chat_id=chat_id,
            sender_id=user.id,
            content=content,
            timestamp=datetime.utcnow()
        )
        chat.last_updated = datetime.utcnow()
        db.session.add(new_msg)
        db.session.commit()
        print(f"*** Message sent for chat {chat_id} by user {user.id} ***")
        logger.debug(f"Message sent for chat {chat_id} by user {user.id}")
        return jsonify({'success': True})

    print("*** Empty message content ***")
    logger.debug("Empty message content")
    return jsonify({'error': 'Empty content'}), 400

# ---------------- API: Fetch Messages (for polling/AJAX) ----------------
@chat_bp.route('/<int:chat_id>/messages')
def fetch_messages(chat_id):
    print(f"*** ENTERING fetch_messages with chat_id={chat_id} ***")
    logger.debug(f"Entering fetch_messages with chat_id={chat_id}")

    ok, resp = user_required()
    if not ok:
        print("*** user_required failed in fetch_messages ***")
        logger.debug("user_required failed in fetch_messages")
        return resp

    user = resp
    chat = Chat.query.get_or_404(chat_id)
    if user.id not in (chat.user1_id, chat.user2_id):
        print("*** Unauthorized access to fetch_messages ***")
        logger.error("Unauthorized access to fetch_messages")
        return jsonify({'error': 'Unauthorized'}), 403

    messages = Message.query.filter_by(chat_id=chat.id).order_by(Message.timestamp.asc()).all()
    print(f"*** Fetched {len(messages)} messages for chat {chat_id} ***")
    logger.debug(f"Fetched {len(messages)} messages for chat {chat_id}")

    return jsonify([
        {
            'sender_id': msg.sender_id,
            'sender_name': msg.message_sender.name,
            'content': msg.content,
            'timestamp': msg.timestamp.strftime("%Y-%m-%d %H:%M")
        } for msg in messages
    ])

# ---------------- Start New Chat ----------------
def get_or_create_chat(user1_id, user2_id, order_id=None):
    print(f"*** get_or_create_chat called with user1_id={user1_id}, user2_id={user2_id}, order_id={order_id} ***")
    logger.debug(f"get_or_create_chat called with user1_id={user1_id}, user2_id={user2_id}, order_id={order_id}")

    if user1_id == user2_id:
        logger.error("Cannot create chat with the same user")
        print("*** ERROR: Cannot create chat with the same user ***")
        raise ValueError("Cannot create chat with the same user")

    user1 = User.query.get(user1_id)
    user2 = User.query.get(user2_id)
    if not user1 or not user2:
        logger.error(f"One or both users not found: user1_id={user1_id}, user2_id={user2_id}")
        print(f"*** ERROR: One or both users not found: user1_id={user1_id}, user2_id={user2_id} ***")
        raise ValueError("One or both users not found")

    if order_id:
        order = Order.query.get(order_id)
        if not order:
            logger.error(f"Order not found: order_id={order_id}")
            print(f"*** ERROR: Order not found: order_id={order_id} ***")
            raise ValueError("Order not found")

    uid1, uid2 = sorted([user1_id, user2_id])
    logger.debug(f"Querying for existing chat with user1_id={uid1}, user2_id={uid2}, order_id={order_id}")
    print(f"*** Querying for existing chat with user1_id={uid1}, user2_id={uid2}, order_id={order_id} ***")
    chat = Chat.query.filter_by(user1_id=uid1, user2_id=uid2)
    if order_id:
        chat = chat.filter_by(order_id=order_id)
    chat = chat.first()
    if chat:
        logger.debug(f"Existing chat found with ID: {chat.id}")
        print(f"*** Existing chat found with ID: {chat.id} ***")
        return chat

    new_chat = Chat(user1_id=uid1, user2_id=uid2, order_id=order_id)
    db.session.add(new_chat)
    db.session.flush()
    logger.debug(f"New chat created with ID: {new_chat.id}")
    print(f"*** New chat created with ID: {new_chat.id} ***")
    return new_chat

@chat_bp.route('/start/<int:other_user_id>/<int:order_id>')
def start_chat(other_user_id, order_id):
    print(f"*** ENTERING start_chat with other_user_id={other_user_id}, order_id={order_id} ***")
    logger.debug(f"Entering start_chat with other_user_id={other_user_id}, order_id={order_id}")

    ok, resp = user_required()
    if not ok:
        print("*** user_required failed in start_chat ***")
        logger.debug("user_required failed in start_chat")
        return resp

    user = resp
    print(f"*** User: {user.id}, {user.name}, role: {user.role} ***")
    logger.debug(f"User: {user.id}, {user.name}, role: {user.role}")

    if user.id == other_user_id:
        print("*** Cannot chat with yourself ***")
        logger.debug("Cannot chat with yourself")
        flash('Cannot chat with yourself.', 'error')
        return redirect(url_for('shop.orders'))

    order = Order.query.get_or_404(order_id)
    print(f"*** Order: {order.id}, factory_id: {order.factory_id} ***")
    logger.debug(f"Order: {order.id}, factory_id: {order.factory_id}")

    factory = Factory.query.get(order.factory_id)
    if not factory or not factory.user:
        print(f"*** ERROR: Factory {order.factory_id} has no associated user ***")
        logger.error(f"Factory {order.factory_id} has no associated user")
        flash('No factory user available for this order.', 'error')
        return redirect(url_for('shop.orders'))

    if factory.user.id != other_user_id:
        print(f"*** ERROR: Other user {other_user_id} does not match factory user {factory.user.id} ***")
        logger.error(f"Other user {other_user_id} does not match factory user {factory.user.id}")
        flash('Invalid factory user for this order.', 'error')
        return redirect(url_for('shop.orders'))

    try:
        chat = get_or_create_chat(user.id, other_user_id, order_id)
        print(f"*** Redirecting to chat ID: {chat.id} ***")
        logger.debug(f"Redirecting to chat ID: {chat.id}")
        return redirect(url_for('chat.view_chat', chat_id=chat.id))
    except Exception as e:
        print(f"*** ERROR creating chat: {str(e)} ***")
        logger.error(f"Error creating chat: {str(e)}")
        flash(f'Error starting chat: {str(e)}', 'error')
        return redirect(url_for('shop.orders'))