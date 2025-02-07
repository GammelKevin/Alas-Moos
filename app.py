from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from models import db, User, MenuCategory, MenuItem, OpeningHours
from sqlalchemy import case

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dein-geheimer-schluessel'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Stelle sicher, dass der Upload-Ordner existiert
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    with app.app_context():
        db.create_all()
        
        # Admin User erstellen
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
        
        # Standard-Kategorien erstellen
        if MenuCategory.query.count() == 0:
            categories = [
                {'name': 'vorspeisen', 'display_name': 'Vorspeisen', 'order': 1},
                {'name': 'hauptgerichte', 'display_name': 'Hauptgerichte', 'order': 2},
                {'name': 'desserts', 'display_name': 'Desserts', 'order': 3},
                {'name': 'getraenke', 'display_name': 'Getränke', 'order': 4}
            ]
            
            for cat in categories:
                category = MenuCategory(
                    name=cat['name'],
                    display_name=cat['display_name'],
                    order=cat['order']
                )
                db.session.add(category)
            db.session.commit()
        
        # Standard-Öffnungszeiten erstellen
        if OpeningHours.query.count() == 0:
            default_hours = [
                {'day': 'Montag', 'closed': True},
                {'day': 'Dienstag', 'open_time': '11:30', 'close_time': '14:30'},
                {'day': 'Mittwoch', 'open_time': '11:30', 'close_time': '14:30'},
                {'day': 'Donnerstag', 'open_time': '11:30', 'close_time': '14:30'},
                {'day': 'Freitag', 'open_time': '11:30', 'close_time': '14:30'},
                {'day': 'Samstag', 'open_time': '17:00', 'close_time': '22:00'},
                {'day': 'Sonntag', 'open_time': '11:30', 'close_time': '14:30'}
            ]
            
            for hours in default_hours:
                opening_hours = OpeningHours(
                    day=hours['day'],
                    open_time=hours.get('open_time'),
                    close_time=hours.get('close_time'),
                    closed=hours.get('closed', False)
                )
                db.session.add(opening_hours)
            db.session.commit()

@app.route('/')
def index():
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    menu_items = MenuItem.query.all()
    opening_hours = OpeningHours.query.order_by(
        case(
            (OpeningHours.day == 'Montag', 1),
            (OpeningHours.day == 'Dienstag', 2),
            (OpeningHours.day == 'Mittwoch', 3),
            (OpeningHours.day == 'Donnerstag', 4),
            (OpeningHours.day == 'Freitag', 5),
            (OpeningHours.day == 'Samstag', 6),
            (OpeningHours.day == 'Sonntag', 7)
        )
    ).all()
    return render_template('index.html', categories=categories, menu_items=menu_items, opening_hours=opening_hours)

@app.route('/admin')
@login_required
def admin():
    return render_template('admin/index.html')

@app.route('/admin/menu')
@login_required
def admin_menu():
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    menu_items = MenuItem.query.all()
    return render_template('admin/menu.html', categories=categories, menu_items=menu_items)

@app.route('/admin/menu/save', methods=['POST'])
@login_required
def save_menu_item():
    try:
        item_id = request.form.get('id')
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price', 0))
        category_id = int(request.form.get('category'))
        vegetarian = request.form.get('vegetarian') == 'true'
        vegan = request.form.get('vegan') == 'true'
        spicy = request.form.get('spicy') == 'true'
        
        if item_id:
            # Existierendes Item aktualisieren
            item = MenuItem.query.get(item_id)
            if item:
                item.name = name
                item.description = description
                item.price = price
                item.category_id = category_id
                item.vegetarian = vegetarian
                item.vegan = vegan
                item.spicy = spicy
        else:
            # Neues Item erstellen
            item = MenuItem(
                name=name,
                description=description,
                price=price,
                category_id=category_id,
                vegetarian=vegetarian,
                vegan=vegan,
                spicy=spicy
            )
            db.session.add(item)
        
        # Bild verarbeiten
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                item.image_path = filename
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Fehler beim Speichern: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/opening-hours')
@login_required
def admin_opening_hours():
    opening_hours = OpeningHours.query.order_by(
        case(
            (OpeningHours.day == 'Montag', 1),
            (OpeningHours.day == 'Dienstag', 2),
            (OpeningHours.day == 'Mittwoch', 3),
            (OpeningHours.day == 'Donnerstag', 4),
            (OpeningHours.day == 'Freitag', 5),
            (OpeningHours.day == 'Samstag', 6),
            (OpeningHours.day == 'Sonntag', 7)
        )
    ).all()
    return render_template('admin/opening_hours.html', opening_hours=opening_hours)

@app.route('/admin/opening-hours/save', methods=['POST'])
@login_required
def save_opening_hours():
    try:
        data = request.get_json()
        for item in data:
            day = item['day']
            opening_hours = OpeningHours.query.filter_by(day=day).first()
            
            if not opening_hours:
                opening_hours = OpeningHours(day=day)
                db.session.add(opening_hours)
            
            opening_hours.closed = item['closed']
            if not item['closed']:
                opening_hours.open_time = item['openTime']
                opening_hours.close_time = item['closeTime']
            else:
                opening_hours.open_time = None
                opening_hours.close_time = None
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Fehler beim Speichern der Öffnungszeiten: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin'))
        
        flash('Ungültige Anmeldedaten')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
