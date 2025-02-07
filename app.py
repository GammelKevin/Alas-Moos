from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
import os
from sqlalchemy import case
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dein-geheimer-schluessel'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Stelle sicher, dass der Upload-Ordner existiert
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Login Manager Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Bitte melden Sie sich an, um auf diese Seite zuzugreifen.'
login_manager.login_message_category = 'error'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

class OpeningHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20), nullable=False)
    open_time = db.Column(db.String(5))
    close_time = db.Column(db.String(5))
    closed = db.Column(db.Boolean, default=False)

class MenuCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    display_name = db.Column(db.String(50), nullable=False)
    order = db.Column(db.Integer)
    is_drink_category = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    items = db.relationship('MenuItem', backref='category', lazy=True)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('menu_category.id'), nullable=False)
    order = db.Column(db.Integer)
    active = db.Column(db.Boolean, default=True)
    image_path = db.Column(db.String(100))
    is_lunch_special = db.Column(db.Boolean, default=False)
    allergens = db.Column(db.String(100))
    portion_size = db.Column(db.String(20))
    spiciness_level = db.Column(db.Integer, default=0)
    is_vegetarian = db.Column(db.Boolean, default=False)
    is_vegan = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    db.create_all()
    
    # Erstelle Admin-Benutzer falls nicht vorhanden
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password('admin')
        db.session.add(admin)
    
    # Erstelle Standardkategorien falls keine vorhanden
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
    
    # Erstelle Standardöffnungszeiten falls keine vorhanden
    if OpeningHours.query.count() == 0:
        default_hours = [
            OpeningHours(day='Montag', closed=True),
            OpeningHours(day='Dienstag', open_time='11:30', close_time='14:30'),
            OpeningHours(day='Mittwoch', open_time='11:30', close_time='14:30'),
            OpeningHours(day='Donnerstag', open_time='11:30', close_time='14:30'),
            OpeningHours(day='Freitag', open_time='11:30', close_time='14:30'),
            OpeningHours(day='Samstag', open_time='17:00', close_time='22:00'),
            OpeningHours(day='Sonntag', open_time='11:30', close_time='14:30')
        ]
        
        for hours in default_hours:
            db.session.add(hours)
    
    db.session.commit()

@app.route('/')
def home():
    try:
        # Hole und sortiere die Öffnungszeiten
        day_order = {
            'Montag': 1, 'Dienstag': 2, 'Mittwoch': 3,
            'Donnerstag': 4, 'Freitag': 5, 'Samstag': 6, 'Sonntag': 7
        }
        
        # Erstelle Standardzeiten falls keine existieren
        if OpeningHours.query.count() == 0:
            default_hours = [
                OpeningHours(day='Montag', closed=True),
                OpeningHours(day='Dienstag', open_time='11:30', close_time='14:30'),
                OpeningHours(day='Mittwoch', open_time='11:30', close_time='14:30'),
                OpeningHours(day='Donnerstag', open_time='11:30', close_time='14:30'),
                OpeningHours(day='Freitag', open_time='11:30', close_time='14:30'),
                OpeningHours(day='Samstag', open_time='17:00', close_time='22:00'),
                OpeningHours(day='Sonntag', open_time='11:30', close_time='14:30')
            ]
            for hours in default_hours:
                db.session.add(hours)
            db.session.commit()
        
        opening_hours = OpeningHours.query.all()
        opening_hours = sorted(opening_hours, key=lambda x: day_order.get(x.day, 8))
        
        # Hole die Menükategorien
        menu_categories = MenuCategory.query.order_by(MenuCategory.order).all()
        
        return render_template('index.html', 
                             opening_hours=opening_hours,
                             categories=menu_categories)
                             
    except Exception as e:
        app.logger.error(f"Fehler auf der Homepage: {str(e)}")
        flash('Ein Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.', 'error')
        return render_template('index.html', 
                             opening_hours=[],
                             categories=[])

@app.route('/menu')
def menu():
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    return render_template('menu.html', categories=categories)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('admin')
            return redirect(next_page)
        flash('Ungültige Anmeldedaten', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin():
    return render_template('admin/dashboard.html')

@app.route('/admin/menu-items')
@login_required
def admin_menu_items():
    items = MenuItem.query.order_by(MenuItem.category_id, MenuItem.order).all()
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    return render_template('admin/menu_items.html', items=items, categories=categories)

@app.route('/admin/menu/save', methods=['POST'])
@login_required
def save_menu_item():
    try:
        category_id = request.form.get('category')
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        
        # Hole die Boolean-Werte
        vegetarian = request.form.get('vegetarian') == 'on'
        vegan = request.form.get('vegan') == 'on'
        spicy = request.form.get('spicy') == 'on'
        
        if not all([category_id, name, price]):
            flash('Bitte füllen Sie alle Pflichtfelder aus.', 'error')
            return redirect(url_for('admin_menu'))
        
        # Erstelle oder aktualisiere das Menüitem
        item_id = request.form.get('item_id')
        if item_id:
            item = MenuItem.query.get(item_id)
            if not item:
                flash('Menüitem nicht gefunden.', 'error')
                return redirect(url_for('admin_menu'))
        else:
            item = MenuItem()
            db.session.add(item)
        
        # Aktualisiere die Werte
        item.category_id = category_id
        item.name = name
        item.description = description
        item.price = float(price.replace(',', '.'))
        item.vegetarian = vegetarian
        item.vegan = vegan
        item.spicy = spicy
        
        # Verarbeite das Bild, falls eines hochgeladen wurde
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                # Generiere einen sicheren Dateinamen
                filename = secure_filename(file.filename)
                # Füge einen Zeitstempel hinzu, um eindeutige Namen zu gewährleisten
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{int(time.time())}{ext}"
                # Speichere das Bild
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                item.image_path = f"uploads/{filename}"
        
        db.session.commit()
        flash('Menüitem wurde erfolgreich gespeichert.', 'success')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Fehler beim Speichern des Menüitems: {str(e)}")
        flash('Ein Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.', 'error')
    
    return redirect(url_for('admin_menu'))

@app.route('/admin/opening-hours', methods=['GET'])
@login_required
def admin_opening_hours():
    try:
        # Hole alle Öffnungszeiten
        opening_hours = OpeningHours.query.all()
        
        # Wenn keine Öffnungszeiten existieren, erstelle Standardzeiten
        if not opening_hours:
            default_hours = [
                OpeningHours(day='Montag', closed=True),
                OpeningHours(day='Dienstag', open_time='11:30', close_time='14:30'),
                OpeningHours(day='Mittwoch', open_time='11:30', close_time='14:30'),
                OpeningHours(day='Donnerstag', open_time='11:30', close_time='14:30'),
                OpeningHours(day='Freitag', open_time='11:30', close_time='14:30'),
                OpeningHours(day='Samstag', open_time='17:00', close_time='22:00'),
                OpeningHours(day='Sonntag', open_time='11:30', close_time='14:30')
            ]
            
            for hours in default_hours:
                db.session.add(hours)
            db.session.commit()
            
            # Hole die neu erstellten Öffnungszeiten
            opening_hours = OpeningHours.query.all()
        
        # Sortiere die Öffnungszeiten nach Wochentag
        day_order = {
            'Montag': 1, 'Dienstag': 2, 'Mittwoch': 3,
            'Donnerstag': 4, 'Freitag': 5, 'Samstag': 6, 'Sonntag': 7
        }
        opening_hours = sorted(opening_hours, key=lambda x: day_order.get(x.day, 8))
        
        return render_template('admin/opening_hours.html', opening_hours=opening_hours)
        
    except Exception as e:
        app.logger.error(f"Fehler in admin_opening_hours: {str(e)}")
        app.logger.exception("Detaillierter Fehler:")
        flash('Ein Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.', 'error')
        return redirect(url_for('admin'))

@app.route('/admin/opening-hours/save', methods=['POST'])
@login_required
def admin_opening_hours_save():
    try:
        days = ['montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag', 'samstag', 'sonntag']
        
        for day in days:
            hours = OpeningHours.query.filter_by(day=day.capitalize()).first()
            if not hours:
                hours = OpeningHours(day=day.capitalize())
                db.session.add(hours)
            
            closed = request.form.get(f'{day}_closed') == 'on'
            hours.closed = closed
            
            if not closed:
                hours.open_time = request.form.get(f'{day}_open')
                hours.close_time = request.form.get(f'{day}_close')
            else:
                hours.open_time = None
                hours.close_time = None
        
        db.session.commit()
        flash('Öffnungszeiten wurden erfolgreich gespeichert.', 'success')
        
    except Exception as e:
        app.logger.error(f"Fehler beim Speichern der Öffnungszeiten: {str(e)}")
        db.session.rollback()
        flash('Ein Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.', 'error')
    
    return redirect(url_for('admin_opening_hours'))

@app.route('/admin/menu-categories', methods=['GET'])
@login_required
def admin_menu_categories():
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    return render_template('admin/menu_categories.html', categories=categories)

@app.route('/admin/menu-categories/add', methods=['POST'])
@login_required
def add_menu_category():
    try:
        new_category = MenuCategory(
            name=request.form.get('name'),
            display_name=request.form.get('display_name'),
            order=int(request.form.get('order', 0))
        )
        db.session.add(new_category)
        db.session.commit()
        flash('Neue Kategorie wurde erfolgreich hinzugefügt', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Hinzufügen der Kategorie: {str(e)}', 'error')
    
    return redirect(url_for('admin_menu_categories'))

@app.route('/admin/menu-categories/edit/<int:id>', methods=['POST'])
@login_required
def edit_menu_category(id):
    category = MenuCategory.query.get_or_404(id)
    try:
        category.name = request.form.get('name')
        category.display_name = request.form.get('display_name')
        category.order = int(request.form.get('order', 0))
        db.session.commit()
        flash('Kategorie wurde erfolgreich aktualisiert', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Aktualisieren der Kategorie: {str(e)}', 'error')
    
    return redirect(url_for('admin_menu_categories'))

@app.route('/admin/menu-categories/delete/<int:id>', methods=['POST'])
@login_required
def delete_menu_category(id):
    category = MenuCategory.query.get_or_404(id)
    try:
        if MenuItem.query.filter_by(category_id=id).first():
            flash('Diese Kategorie enthält noch Gerichte und kann nicht gelöscht werden', 'error')
        else:
            db.session.delete(category)
            db.session.commit()
            flash('Kategorie wurde erfolgreich gelöscht', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen der Kategorie: {str(e)}', 'error')
    
    return redirect(url_for('admin_menu_categories'))

with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
