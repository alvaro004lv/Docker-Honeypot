from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import login_user, login_required, logout_user, current_user
import requests

def send_telegram_message(message):
    bot_token = 'YOUR_BOT_TOKEN' # change this with your bot token
    chat_id = 'YOUR_CHAT_ID' # change this with your telegram bot chat id
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message
    }
    requests.post(url, data=payload)


auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Loged in successfully!', category='success')
                login_user(user, remember=True)

                send_telegram_message(f"User {user.email} has logged in honeypot website.")

                return redirect(url_for('views.home'))
            else:
                flash('User or password are incorrect.', category='error')
        else:
            flash('Account doesn\'t exist, create one first.', category='error')

    return render_template("login.html", user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Account already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 4 characters.', category='error')
            pass
        elif len(first_name) < 2:
            flash('First name must be greater than 2 characters.', category='error')
            pass
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
            pass
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
            pass
        else:
            new_user = User(email=email, first_name=first_name, password=generate_password_hash(password1, method='pbkdf2:sha256', salt_length=16))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('Account created successfully!', category='success')
            return redirect(url_for('views.home'))

    return render_template("sign_up.html", user=current_user)
