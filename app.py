from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import case
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dein-geheimer-schluessel'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Stelle sicher, dass der Upload-Ordner existiert
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class MenuCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(50), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    is_drink_category = db.Column(db.Boolean, default=False)
    items = db.relationship('MenuItem', backref='category', lazy=True)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('menu_category.id'), nullable=False)
    vegetarian = db.Column(db.Boolean, default=False)
    vegan = db.Column(db.Boolean, default=False)
    spicy = db.Column(db.Boolean, default=False)
    image_path = db.Column(db.String(255))

class OpeningHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20), nullable=False)
    open_time_1 = db.Column(db.String(5))
    close_time_1 = db.Column(db.String(5))
    open_time_2 = db.Column(db.String(5))
    close_time_2 = db.Column(db.String(5))
    closed = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    # Create tables
    db.create_all()
    
    # Check if admin user exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password('admin')
        db.session.add(admin)
        
        # Add default categories
        categories = [
            MenuCategory(name='vorspeisen', display_name='Vorspeisen', order=1),
            MenuCategory(name='hauptgerichte', display_name='Hauptgerichte', order=2),
            MenuCategory(name='desserts', display_name='Desserts', order=3),
            MenuCategory(name='getraenke', display_name='Getränke', order=4, is_drink_category=True)
        ]
        db.session.add_all(categories)
        
        # Add default opening hours
        opening_hours = [
            OpeningHours(day='Montag', closed=True),
            OpeningHours(day='Dienstag', open_time_1='11:30', close_time_1='14:30'),
            OpeningHours(day='Mittwoch', open_time_1='11:30', close_time_1='14:30'),
            OpeningHours(day='Donnerstag', open_time_1='11:30', close_time_1='14:30'),
            OpeningHours(day='Freitag', open_time_1='11:30', close_time_1='14:30'),
            OpeningHours(day='Samstag', open_time_1='17:00', close_time_1='22:00'),
            OpeningHours(day='Sonntag', open_time_1='11:30', close_time_1='14:30')
        ]
        db.session.add_all(opening_hours)
        
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
            # Altes Bild löschen
            if menu_item.image_path:
                old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(menu_item.image_path))
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            
            # Neues Bild speichern
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
        
        # Bild löschen wenn vorhanden
        if menu_item.image_path:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(menu_item.image_path))
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(menu_item)
        db.session.commit()
        flash('Menüpunkt erfolgreich gelöscht')
    except Exception as e:
        flash(f'Fehler beim Löschen des Menüpunkts: {str(e)}')
    
    return redirect(url_for('admin_menu'))

@app.route('/admin/categories')
@login_required
def admin_categories():
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/categories/add', methods=['POST'])
@login_required
def admin_add_category():
    try:
        name = request.form.get('name').lower()
        display_name = request.form.get('display_name')
        order = int(request.form.get('order'))
        is_drink_category = bool(request.form.get('is_drink_category'))
        
        category = MenuCategory(
            name=name,
            display_name=display_name,
            order=order,
            is_drink_category=is_drink_category
        )
        
        db.session.add(category)
        db.session.commit()
        flash('Kategorie erfolgreich hinzugefügt', 'success')
    except Exception as e:
        flash(f'Fehler beim Hinzufügen der Kategorie: {str(e)}', 'error')
    
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/delete/<int:id>', methods=['POST'])
@login_required
def admin_delete_category(id):
    try:
        category = MenuCategory.query.get_or_404(id)
        db.session.delete(category)
        db.session.commit()
        flash('Kategorie erfolgreich gelöscht', 'success')
    except Exception as e:
        flash(f'Fehler beim Löschen der Kategorie: {str(e)}', 'error')
    
    return redirect(url_for('admin_categories'))

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
    return render_template('admin/hours.html', opening_hours=opening_hours)

@app.route('/admin/hours/save', methods=['POST'])
@login_required
def admin_save_hours():
    try:
        days = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
        
        for day in days:
            hours = OpeningHours.query.filter_by(day=day).first()
            if not hours:
                hours = OpeningHours(day=day)
                db.session.add(hours)
            
            closed = request.form.get(f'{day}_closed') == 'on'
            hours.closed = closed
            
            if not closed:
                hours.open_time_1 = request.form.get(f'{day}_open_1')
                hours.close_time_1 = request.form.get(f'{day}_close_1')
                hours.open_time_2 = request.form.get(f'{day}_open_2')
                hours.close_time_2 = request.form.get(f'{day}_close_2')
        
        db.session.commit()
        flash('Öffnungszeiten erfolgreich gespeichert', 'success')
    except Exception as e:
        flash(f'Fehler beim Speichern der Öffnungszeiten: {str(e)}', 'error')
    
    return redirect(url_for('admin_hours'))

@app.route('/menu')
def menu():
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    menu_items = MenuItem.query.all()
    return render_template('menu.html', categories=categories, menu_items=menu_items)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
else:
    with app.app_context():
        init_db()
