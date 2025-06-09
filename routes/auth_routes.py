from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Factory, Category

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        flash('Login successful!', 'success')
        if user.role == 'seller':
            return redirect(url_for('shop.browse'))
        elif user.role == 'factory':
            return redirect(url_for('dashboard.dashboard'))
        else:
            flash('Unknown user role.', 'error')
            return redirect(url_for('auth.index'))

    # 🛠️ Handle failed login
    flash('Invalid email or password.', 'error')
    return redirect(url_for('auth.index'))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    categories = Category.query.all()

    if request.method == "POST":
        role = request.form.get("role")
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        repeat_password = request.form.get("repeat_password")

        if password != repeat_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "error")
            return redirect(url_for("auth.register"))

        hashed_password = generate_password_hash(password)
        new_user = User(name=name, email=email, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.flush()

        if role == "factory":
            factory_name = request.form.get("factory_name")
            location = request.form.get("location")
            category_id = int(request.form.get("category_id"))
            contact_info = request.form.get("contact_info")
            description = request.form.get("description")

            new_factory = Factory(
                user_id=new_user.id,
                name=factory_name,
                location=location,
                category_id=category_id,
                contact_info=contact_info,
                description=description
            )
            db.session.add(new_factory)

        db.session.commit()
        flash("User registered successfully. Please log in.", "success")
        return redirect(url_for("auth.index"))

    return render_template("register.html", categories=categories)

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.index'))
