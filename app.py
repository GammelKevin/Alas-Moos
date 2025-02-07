from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
import os
from sqlalchemy import case

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
    
    # Admin User erstellen
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.password_hash = generate_password_hash('admin')
        db.session.add(admin)
    
    # Standard-Kategorien erstellen
    if not MenuCategory.query.first():
        categories = [
            {'name': 'vorspeisen', 'display_name': 'Vorspeisen', 'order': 1},
            {'name': 'hauptspeisen', 'display_name': 'Hauptspeisen', 'order': 2},
            {'name': 'desserts', 'display_name': 'Desserts', 'order': 3},
            {'name': 'getraenke', 'display_name': 'Getränke', 'order': 4, 'is_drink_category': True}
        ]
        
        for cat in categories:
            category = MenuCategory(
                name=cat['name'],
                display_name=cat['display_name'],
                order=cat['order'],
                is_drink_category=cat.get('is_drink_category', False)
            )
            db.session.add(category)
    
    # Standard-Öffnungszeiten erstellen
    if not OpeningHours.query.first():
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
def home():
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
    menu_categories = MenuCategory.query.order_by(MenuCategory.order).all()
    return render_template('index.html', opening_hours=opening_hours, categories=menu_categories)

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

@app.route('/admin/menu-items/add', methods=['GET', 'POST'])
@login_required
def add_menu_item():
    if request.method == 'POST':
        try:
            # Bildupload
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_path = f'uploads/{filename}'

            new_item = MenuItem(
                name=request.form.get('name'),
                description=request.form.get('description'),
                price=float(request.form.get('price')),
                category_id=int(request.form.get('category_id')),
                order=int(request.form.get('order', 0)),
                active=bool(request.form.get('active')),
                image_path=image_path,
                is_lunch_special=bool(request.form.get('is_lunch_special')),
                allergens=request.form.get('allergens'),
                portion_size=request.form.get('portion_size'),
                spiciness_level=int(request.form.get('spiciness_level', 0)),
                is_vegetarian=bool(request.form.get('is_vegetarian')),
                is_vegan=bool(request.form.get('is_vegan'))
            )
            
            db.session.add(new_item)
            db.session.commit()
            flash('Neues Gericht wurde erfolgreich hinzugefügt', 'success')
            return redirect(url_for('admin_menu_items'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Hinzufügen des Gerichts: {str(e)}', 'error')
            return redirect(url_for('add_menu_item'))
    
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    return render_template('admin/add_menu_item.html', categories=categories)

@app.route('/admin/menu-items/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    
    if request.method == 'POST':
        try:
            # Bildupload
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    # Lösche altes Bild, falls vorhanden
                    if item.image_path:
                        old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], item.image_path.split('/')[-1])
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    item.image_path = f'uploads/{filename}'

            item.name = request.form.get('name')
            item.description = request.form.get('description')
            item.price = float(request.form.get('price'))
            item.category_id = int(request.form.get('category_id'))
            item.order = int(request.form.get('order', 0))
            item.active = bool(request.form.get('active'))
            item.is_lunch_special = bool(request.form.get('is_lunch_special'))
            item.allergens = request.form.get('allergens')
            item.portion_size = request.form.get('portion_size')
            item.spiciness_level = int(request.form.get('spiciness_level', 0))
            item.is_vegetarian = bool(request.form.get('is_vegetarian'))
            item.is_vegan = bool(request.form.get('is_vegan'))
            
            db.session.commit()
            flash('Gericht wurde erfolgreich aktualisiert', 'success')
            return redirect(url_for('admin_menu_items'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Aktualisieren des Gerichts: {str(e)}', 'error')
            return redirect(url_for('edit_menu_item', item_id=item_id))
    
    return render_template('admin/edit_menu_item.html', item=item, categories=categories)

@app.route('/admin/menu-items/delete/<int:id>', methods=['POST'])
@login_required
def delete_menu_item(id):
    item = MenuItem.query.get_or_404(id)
    try:
        # Lösche das Bild, falls vorhanden
        if item.image_path:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], item.image_path.split('/')[-1])
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(item)
        db.session.commit()
        flash('Gericht wurde erfolgreich gelöscht', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen des Gerichts: {str(e)}', 'error')
    
    return redirect(url_for('admin_menu_items'))

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

@app.route('/admin/opening-hours', methods=['GET'])
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
        days = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
        
        for day in days:
            hours = OpeningHours.query.filter_by(day=day).first()
            if not hours:
                hours = OpeningHours(day=day)
                db.session.add(hours)
            
            day_key = day.lower()
            hours.closed = request.form.get(f'{day_key}_closed') is not None
            
            if not hours.closed:
                open_time = request.form.get(f'{day_key}_open')
                close_time = request.form.get(f'{day_key}_close')
                
                if not open_time or not close_time:
                    flash(f'Bitte geben Sie gültige Öffnungszeiten für {day} ein.', 'error')
                    return redirect(url_for('admin_opening_hours'))
                
                hours.open_time = open_time
                hours.close_time = close_time
            else:
                hours.open_time = None
                hours.close_time = None
        
        db.session.commit()
        flash('Öffnungszeiten wurden erfolgreich gespeichert.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Speichern der Öffnungszeiten: {str(e)}', 'error')
    
    return redirect(url_for('admin_opening_hours'))

with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
