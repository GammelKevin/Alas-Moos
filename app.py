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
    try:
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
    except Exception as e:
        print(f"Fehler auf der Homepage: {str(e)}")
        init_db()  # Initialisiere die Datenbank falls sie nicht existiert
        return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin'))
        else:
            flash('Ungültige Anmeldedaten')
    
    return render_template('login.html')

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

@app.route('/admin/menu/add', methods=['POST'])
@login_required
def admin_menu_add():
    try:
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        category_id = int(request.form.get('category'))
        vegetarian = bool(request.form.get('vegetarian'))
        vegan = bool(request.form.get('vegan'))
        spicy = bool(request.form.get('spicy'))
        
        image = request.files.get('image')
        image_path = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            image_path = os.path.join('uploads', filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        menu_item = MenuItem(
            name=name,
            description=description,
            price=price,
            category_id=category_id,
            vegetarian=vegetarian,
            vegan=vegan,
            spicy=spicy,
            image_path=image_path
        )
        
        db.session.add(menu_item)
        db.session.commit()
        
        flash('Menüpunkt erfolgreich hinzugefügt')
    except Exception as e:
        flash(f'Fehler beim Hinzufügen des Menüpunkts: {str(e)}')
    
    return redirect(url_for('admin_menu'))

@app.route('/admin/menu/edit/<int:id>', methods=['POST'])
@login_required
def admin_menu_edit(id):
    try:
        menu_item = MenuItem.query.get_or_404(id)
        menu_item.name = request.form.get('name')
        menu_item.description = request.form.get('description')
        menu_item.price = float(request.form.get('price'))
        menu_item.category_id = int(request.form.get('category'))
        menu_item.vegetarian = bool(request.form.get('vegetarian'))
        menu_item.vegan = bool(request.form.get('vegan'))
        menu_item.spicy = bool(request.form.get('spicy'))
        
        image = request.files.get('image')
        if image and image.filename:
            filename = secure_filename(image.filename)
            image_path = os.path.join('uploads', filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            menu_item.image_path = image_path
        
        db.session.commit()
        flash('Menüpunkt erfolgreich aktualisiert')
    except Exception as e:
        flash(f'Fehler beim Aktualisieren des Menüpunkts: {str(e)}')
    
    return redirect(url_for('admin_menu'))

@app.route('/admin/menu/delete/<int:id>')
@login_required
def admin_menu_delete(id):
    try:
        menu_item = MenuItem.query.get_or_404(id)
        if menu_item.image_path:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(menu_item.image_path)))
            except:
                pass
        db.session.delete(menu_item)
        db.session.commit()
        flash('Menüpunkt erfolgreich gelöscht')
    except Exception as e:
        flash(f'Fehler beim Löschen des Menüpunkts: {str(e)}')
    
    return redirect(url_for('admin_menu'))

@app.route('/admin/hours')
@login_required
def admin_hours():
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

@app.route('/admin/hours/update', methods=['POST'])
@login_required
def admin_hours_update():
    try:
        for day in ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']:
            hours = OpeningHours.query.filter_by(day=day).first()
            if not hours:
                hours = OpeningHours(day=day)
                db.session.add(hours)
            
            closed = request.form.get(f'{day}_closed') == 'on'
            hours.closed = closed
            
            if not closed:
                hours.open_time = request.form.get(f'{day}_open')
                hours.close_time = request.form.get(f'{day}_close')
        
        db.session.commit()
        flash('Öffnungszeiten erfolgreich aktualisiert')
    except Exception as e:
        flash(f'Fehler beim Aktualisieren der Öffnungszeiten: {str(e)}')
    
    return redirect(url_for('admin_hours'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
