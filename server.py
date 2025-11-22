from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
from datetime import datetime
import uuid
from pathlib import Path

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = 'your-secret-key-change-this-in-production'
CORS(app)

# Data storage paths
DATA_DIR = Path(__file__).parent / 'data'
USERS_FILE = DATA_DIR / 'users.json'
MESSAGES_FILE = DATA_DIR / 'messages.json'

# Create data directory if it doesn't exist
DATA_DIR.mkdir(exist_ok=True)

# Initialize data files
if not USERS_FILE.exists():
    USERS_FILE.write_text('{}')

if not MESSAGES_FILE.exists():
    MESSAGES_FILE.write_text('[]')

def load_users():
    """Load users from JSON file"""
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    """Save users to JSON file"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_messages():
    """Load messages from JSON file"""
    try:
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_messages(messages):
    """Save messages to JSON file"""
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

# ============= AUTH ROUTES =============

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        email = data.get('email', '').strip()

        # Validation
        if not username or not password or not email:
            return jsonify({'error': 'Все поля обязательны'}), 400

        if len(username) < 3:
            return jsonify({'error': 'Имя пользователя должно быть не менее 3 символов'}), 400

        if len(password) < 6:
            return jsonify({'error': 'Пароль должен быть не менее 6 символов'}), 400

        users = load_users()

        # Check if user exists
        if username in users:
            return jsonify({'error': 'Пользователь с таким именем уже существует'}), 400

        # Create new user
        user_id = str(uuid.uuid4())
        users[username] = {
            'id': user_id,
            'email': email,
            'password': generate_password_hash(password),
            'created_at': datetime.now().isoformat(),
            'avatar': username[0].upper()
        }

        save_users(users)

        return jsonify({
            'message': 'Пользователь успешно зарегистрирован',
            'user': {
                'id': user_id,
                'username': username,
                'email': email,
                'avatar': username[0].upper()
            }
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if not username or not password:
            return jsonify({'error': 'Имя пользователя и пароль обязательны'}), 400

        users = load_users()

        if username not in users:
            return jsonify({'error': 'Неверное имя пользователя или пароль'}), 401

        user = users[username]

        if not check_password_hash(user['password'], password):
            return jsonify({'error': 'Неверное имя пользователя или пароль'}), 401

        session['user_id'] = user['id']
        session['username'] = username

        return jsonify({
            'message': 'Успешный вход',
            'user': {
                'id': user['id'],
                'username': username,
                'email': user['email'],
                'avatar': user['avatar']
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'message': 'Успешный выход'}), 200

@app.route('/api/auth/user', methods=['GET'])
def get_current_user():
    """Get current logged in user"""
    if 'username' not in session:
        return jsonify({'error': 'Не авторизованы'}), 401

    users = load_users()
    username = session['username']

    if username not in users:
        return jsonify({'error': 'Пользователь не найден'}), 404

    user = users[username]
    return jsonify({
        'id': user['id'],
        'username': username,
        'email': user['email'],
        'avatar': user['avatar']
    }), 200

# ============= GLOBAL CHAT ROUTES =============

@app.route('/api/chat/messages', methods=['GET'])
def get_messages():
    """Get all global chat messages"""
    try:
        limit = request.args.get('limit', 50, type=int)
        messages = load_messages()
        
        # Return last N messages
        return jsonify(messages[-limit:]), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/messages', methods=['POST'])
def send_message():
    """Send a message to global chat"""
    try:
        if 'username' not in session:
            return jsonify({'error': 'Не авторизованы'}), 401

        data = request.get_json()
        content = data.get('content', '').strip()

        if not content:
            return jsonify({'error': 'Сообщение не может быть пустым'}), 400

        users = load_users()
        username = session['username']
        user = users[username]

        message = {
            'id': str(uuid.uuid4()),
            'username': username,
            'avatar': user['avatar'],
            'content': content,
            'timestamp': datetime.now().isoformat()
        }

        messages = load_messages()
        messages.append(message)
        save_messages(messages)

        return jsonify(message), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/messages/<message_id>', methods=['DELETE'])
def delete_message(message_id):
    """Delete a message (only by author)"""
    try:
        if 'username' not in session:
            return jsonify({'error': 'Не авторизованы'}), 401

        messages = load_messages()
        message_index = None

        for i, msg in enumerate(messages):
            if msg['id'] == message_id:
                message_index = i
                break

        if message_index is None:
            return jsonify({'error': 'Сообщение не найдено'}), 404

        if messages[message_index]['username'] != session['username']:
            return jsonify({'error': 'Вы не можете удалить это сообщение'}), 403

        del messages[message_index]
        save_messages(messages)

        return jsonify({'message': 'Сообщение удалено'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============= HEALTH CHECK =============

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'users_count': len(load_users()),
        'messages_count': len(load_messages())
    }), 200

# ============= STATIC FILES =============

@app.route('/')
def index():
    """Serve index.html"""
    return send_from_directory('.', 'index.html')

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors - try to serve static files"""
    if request.path.startswith('/api'):
        return jsonify({'error': 'API endpoint not found'}), 404
    
    # Try to serve static files
    file_path = request.path.lstrip('/')
    if file_path and os.path.exists(file_path):
        return send_from_directory('.', file_path)
    
    # Fallback to index.html
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
