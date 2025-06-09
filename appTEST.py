

# from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session
# from models import Category, db, User, Factory
# from werkzeug.security import generate_password_hash, check_password_hash
# from datetime import datetime

# app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///b2b_platform.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.secret_key = 'your-secret-key'

# db.init_app(app)

# # Login page (GET)
# @app.route('/')
# def index():
#     return render_template('login.html')

# # Login form submission (POST)
# @app.route('/login', methods=['POST'])
# def login():
#     email = request.form['email']
#     password = request.form['password']

#     user = User.query.filter_by(email=email).first()

#     if user and check_password_hash(user.password, password):
#         session['user_id'] = user.id
#         flash('Login successful!', 'success')

#         # Redirect based on role
#         if user.role == 'seller':
#             return redirect(url_for('shop'))
#         elif user.role == 'factory':
#             return redirect(url_for('dashboard'))
#         else:
#             flash('Unknown user role.', 'error')
#             return redirect(url_for('index'))
#     else:
#         flash('Invalid email or password.', 'error')
#         return redirect(url_for('index'))

# # Registration (GET and POST)
# @app.route("/register", methods=["GET", "POST"])
# def register():
#     categories = Category.query.all()

#     if request.method == "POST":
#         role = request.form.get("role")
#         name = request.form.get("name")
#         email = request.form.get("email")
#         password = request.form.get("password")
#         repeat_password = request.form.get("repeat_password")

#         if password != repeat_password:
#             flash("Passwords do not match.", "error")
#             return redirect(url_for("register"))

#         if User.query.filter_by(email=email).first():
#             flash("Email already exists.", "error")
#             return redirect(url_for("register"))

#         hashed_password = generate_password_hash(password)
#         new_user = User(name=name, email=email, password=hashed_password, role=role)
#         db.session.add(new_user)
#         db.session.flush()  # Get new_user.id before commit

#         if role == "factory":
#             factory_name = request.form.get("factory_name")
#             location = request.form.get("location")
#             category_id = request.form.get("category_id")
#             contact_info = request.form.get("contact_info")
#             description = request.form.get("description")

#             new_factory = Factory(
#                 user_id=new_user.id,
#                 name=factory_name,
#                 location=location,
#                 category_id=category_id,
#                 contact_info=contact_info,
#                 description=description
#             )
#             db.session.add(new_factory)

#         db.session.commit()
#         flash("User registered successfully. Please log in.", "success")
#         return redirect(url_for("index"))

#     return render_template("register.html", categories=categories)

# # Dashboard
# @app.route('/dashboard')
# def dashboard():
#     if 'user_id' not in session:
#         flash('Please log in first.', 'error')
#         return redirect(url_for('index'))

#     user = User.query.get(session['user_id'])
#     return render_template('dashboard.html', user=user)

# # Shop
# @app.route('/shop')
# def shop():
#     if 'user_id' not in session:
#         flash('Please log in first.', 'error')
#         return redirect(url_for('index'))

#     user = User.query.get(session['user_id'])
#     if user.role != 'seller':
#         flash('Access denied: Only sellers can access the shop.', 'error')
#         return redirect(url_for('index'))

#     return render_template('shop.html', user=user)

# # Logout
# @app.route('/logout')
# def logout():
#     session.pop('user_id', None)
#     flash('You have been logged out.', 'success')
#     return redirect(url_for('index'))

# if __name__ == '__main__':
#     app.run(debug=True)
