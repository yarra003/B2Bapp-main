from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, session
from models import Factory, Order, db, Chat, Message, User
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- List All Chats ----------------
@chat_bp.route('/', endpoint='list_chats')
def chat_list():
    ok, resp = user_required()
    if not ok:
        return resp

    user = resp
    chats = Chat.query.filter(
        (Chat.user1_id == user.id) | (Chat.user2_id == user.id)
    ).order_by(Chat.last_updated.desc()).all()
    logger.debug(f"User {user.id} fetched {len(chats)} chats")
    template = 'chat/factory_chat_list.html' if user.role == 'factory' else 'chat/chat_list.html'
    return render_template(template, user=user, chats=chats)

# ---------------- View Chat ----------------
@chat_bp.route('/<int:chat_id>', endpoint='view_chat')
def view_chat(chat_id):
    ok, resp = user_required()
    if not ok:
        return resp

    user = resp
    chat = Chat.query.get_or_404(chat_id)
    if user.id not in (chat.user1_id, chat.user2_id):
        logger.error(f"User {user.id} unauthorized for chat {chat_id}")
        abort(403)

    messages = Message.query.filter_by(chat_id=chat.id).order_by(Message.timestamp.asc()).all()
    logger.debug(f"Chat {chat_id}: user1_id={chat.user1_id}, user2_id={chat.user2_id}, messages={len(messages)}")
    if not chat.chat_user1 or not chat.chat_user2:
        logger.error(f"Chat {chat_id} missing user1 or user2: user1={chat.chat_user1}, user2={chat.chat_user2}")
        flash('Invalid chat participants.', 'error')
        return redirect(url_for('chat.list_chats'))

    template = 'chat/factory_chat_room.html' if user.role == 'factory' else 'chat/chat_room.html'
    return render_template(template, user=user, chat=chat, messages=messages)

# ---------------- Send Message ----------------
@chat_bp.route('/<int:chat_id>/send', methods=['POST'])
def send_message(chat_id):
    ok, resp = user_required()
    if not ok:
        return resp

    user = resp
    chat = Chat.query.get_or_404(chat_id)
    if user.id not in (chat.user1_id, chat.user2_id):
        logger.error(f"User {user.id} unauthorized to send message in chat {chat_id}")
        return jsonify({'error': 'Unauthorized'}), 403

    content = request.form.get('content', '').strip()
    file = request.files.get('file')
    attachment_url = None

    if file and file.filename:
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', UPLOAD_FOLDER)
            os.makedirs(upload_dir, exist_ok=True)
            file.save(os.path.join(upload_dir, filename))
            attachment_url = f'uploads/{filename}'
            logger.debug(f"Uploaded file: {filename} for chat {chat_id}")
        else:
            logger.warning(f"Invalid file type: {file.filename} for chat {chat_id}")
            return jsonify({'error': 'Invalid file type'}), 400

    if not content and not attachment_url:
        logger.warning(f"Empty message attempted in chat {chat_id}")
        return jsonify({'error': 'Empty message or no attachment'}), 400

    new_msg = Message(
        chat_id=chat_id,
        sender_id=user.id,
        content=content or None,
        attachment_url=attachment_url,
        timestamp=datetime.utcnow(),
        is_read=False
    )
    chat.last_updated = datetime.utcnow()
    db.session.add(new_msg)
    db.session.commit()
    logger.debug(f"Message sent in chat {chat_id} by user {user.id}")
    return jsonify({'success': True})

# ---------------- API: Fetch Messages ----------------
@chat_bp.route('/<int:chat_id>/messages')
def fetch_messages(chat_id):
    ok, resp = user_required()
    if not ok:
        return resp

    user = resp
    chat = Chat.query.get_or_404(chat_id)
    if user.id not in (chat.user1_id, chat.user2_id):
        logger.error(f"User {user.id} unauthorized to fetch messages for chat {chat_id}")
        return jsonify({'error': 'Unauthorized'}), 403

    messages = Message.query.filter_by(chat_id=chat.id).order_by(Message.timestamp.asc()).all()
    logger.debug(f"Fetched {len(messages)} messages for chat {chat_id}")
    return jsonify([
        {
            'id': msg.id,
            'sender_id': msg.sender_id,
            'sender_name': User.query.get(msg.sender_id).name if User.query.get(msg.sender_id) else 'Unknown',
            'content': msg.content,
            'attachment_url': msg.attachment_url,
            'is_read': msg.is_read,
            'timestamp': msg.timestamp.strftime("%Y-%m-%d %H:%M")
        } for msg in messages
    ])

# ---------------- API: Update Typing Status ----------------
@chat_bp.route('/<int:chat_id>/typing', methods=['POST'])
def update_typing(chat_id):
    ok, resp = user_required()
    if not ok:
        return resp

    user = resp
    chat = Chat.query.get_or_404(chat_id)
    if user.id not in (chat.user1_id, chat.user2_id):
        logger.error(f"User {user.id} unauthorized to update typing in chat {chat_id}")
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    typing = data.get('typing', False)

    if user.id == chat.user1_id:
        chat.user1_typing = typing
    else:
        chat.user2_typing = typing
    db.session.commit()
    logger.debug(f"Typing status updated for user {user.id} in chat {chat_id}: {typing}")
    return jsonify({'success': True})

# ---------------- API: Get Typing Status ----------------
@chat_bp.route('/<int:chat_id>/typing_status')
def get_typing_status(chat_id):
    ok, resp = user_required()
    if not ok:
        return resp

    user = resp
    chat = Chat.query.get_or_404(chat_id)
    if user.id not in (chat.user1_id, chat.user2_id):
        logger.error(f"User {user.id} unauthorized to get typing status for chat {chat_id}")
        return jsonify({'error': 'Unauthorized'}), 403

    partner = chat.chat_user1 if user.id == chat.user2_id else chat.chat_user2
    is_typing = chat.user2_typing if user.id == chat.user1_id else chat.user1_typing
    logger.debug(f"Typing status for chat {chat_id}: partner={partner.name if partner else 'None'}, is_typing={is_typing}")
    return jsonify({
        'is_typing': is_typing,
        'partner_name': partner.name if partner else 'Unknown'
    })

# ---------------- API: Mark Messages as Read ----------------
@chat_bp.route('/<int:chat_id>/read', methods=['POST'])
def mark_read(chat_id):
    ok, resp = user_required()
    if not ok:
        return resp

    user = resp
    chat = Chat.query.get_or_404(chat_id)
    if user.id not in (chat.user1_id, chat.user2_id):
        logger.error(f"User {user.id} unauthorized to mark messages read in chat {chat_id}")
        return jsonify({'error': 'Unauthorized'}), 403

    messages = Message.query.filter_by(chat_id=chat_id, is_read=False).filter(Message.sender_id != user.id).all()
    for msg in messages:
        msg.is_read = True
    db.session.commit()
    logger.debug(f"Marked {len(messages)} messages as read in chat {chat_id} by user {user.id}")
    return jsonify({'success': True})

# ---------------- Start New Chat ----------------
def get_or_create_chat(user1_id, user2_id, order_id=None):
    if user1_id == user2_id:
        raise ValueError("Cannot create chat with the same user")

    user1 = User.query.get(user1_id)
    user2 = User.query.get(user2_id)
    if not user1 or not user2:
        logger.error(f"Users not found: user1_id={user1_id}, user2_id={user2_id}")
        raise ValueError("One or both users not found")

    if order_id:
        order = Order.query.get(order_id)
        if not order:
            logger.error(f"Order not found: order_id={order_id}")
            raise ValueError("Order not found")

    uid1, uid2 = sorted([user1_id, user2_id])
    chat = Chat.query.filter_by(user1_id=uid1, user2_id=uid2)
    if order_id:
        chat = chat.filter_by(order_id=order_id)
    chat = chat.first()
    if chat:
        logger.debug(f"Found existing chat: chat_id={chat.id}")
        return chat

    new_chat = Chat(user1_id=uid1, user2_id=uid2, order_id=order_id)
    db.session.add(new_chat)
    db.session.flush()
    logger.debug(f"Created new chat: chat_id={new_chat.id}")
    return new_chat

@chat_bp.route('/start/<int:other_user_id>/<int:order_id>')
def start_chat(other_user_id, order_id):
    ok, resp = user_required()
    if not ok:
        return resp

    user = resp
    if user.id == other_user_id:
        logger.warning(f"User {user.id} attempted to chat with self")
        flash('Cannot chat with yourself.', 'error')
        return redirect(url_for('shop.orders'))

    order = Order.query.get_or_404(order_id)
    factory = Factory.query.get(order.factory_id)
    if not factory or not factory.user:
        logger.error(f"No factory user for order {order_id}")
        flash('No factory user available for this order.', 'error')
        return redirect(url_for('shop.orders'))

    if factory.user.id != other_user_id:
        logger.error(f"Invalid factory user {other_user_id} for order {order_id}")
        flash('Invalid factory user for this order.', 'error')
        return redirect(url_for('shop.orders'))

    try:
        chat = get_or_create_chat(user.id, other_user_id, order_id)
        db.session.commit()
        logger.debug(f"Started chat {chat.id} for user {user.id} and other_user {other_user_id}")
        return redirect(url_for('chat.view_chat', chat_id=chat.id))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error starting chat: {str(e)}")
        flash(f'Error starting chat: {str(e)}', 'error')
        return redirect(url_for('shop.orders'))