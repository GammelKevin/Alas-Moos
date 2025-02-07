from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dein-geheimer-schluessel'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

class OpeningHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20), nullable=False)
    open_time_1 = db.Column(db.String(5))
    close_time_1 = db.Column(db.String(5))
    open_time_2 = db.Column(db.String(5))
    close_time_2 = db.Column(db.String(5))
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
    is_drink = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    db.create_all()
    
    # Erstelle einen Admin-Benutzer, wenn noch keiner existiert
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin_user)
    
    # Initialisiere Öffnungszeiten, wenn sie noch nicht existieren
    days = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
    for day in days:
        if not OpeningHours.query.filter_by(day=day).first():
            hours = OpeningHours(
                day=day,
                open_time_1='11:30',
                close_time_1='14:00',
                open_time_2='17:00',
                close_time_2='22:00',
                closed=True if day == 'Montag' else False
            )
            db.session.add(hours)

    # Initialisiere Menü-Kategorien, wenn sie noch nicht existieren
    if not MenuCategory.query.first():
        categories = [
            ('vorspeisen', 'Vorspeisen', 1, False),
            ('hauptspeisen', 'Hauptspeisen', 2, False),
            ('desserts', 'Desserts', 3, False),
            ('getraenke', 'Getränke', 4, True)
        ]
        for name, display_name, order, is_drink in categories:
            category = MenuCategory(
                name=name,
                display_name=display_name,
                order=order,
                is_drink_category=is_drink
            )
            db.session.add(category)
    
    db.session.commit()

@app.route('/')
def home():
    opening_hours = OpeningHours.query.order_by(
        db.case(
            {
                'Montag': 1,
                'Dienstag': 2,
                'Mittwoch': 3,
                'Donnerstag': 4,
                'Freitag': 5,
                'Samstag': 6,
                'Sonntag': 7
            },
            value=OpeningHours.day
        )
    ).all()
    return render_template('index.html', opening_hours=opening_hours)

@app.route('/menu')
def menu():
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    return render_template('menu.html', categories=categories)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('admin'))
        flash('Ungültige Anmeldedaten')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin():
    opening_hours = {}
    for hour in OpeningHours.query.all():
        opening_hours[hour.day.lower()] = {
            'open_1': hour.open_time_1,
            'close_1': hour.close_time_1,
            'open_2': hour.open_time_2,
            'close_2': hour.close_time_2,
            'closed': hour.closed
        }
    return render_template('admin/index.html', opening_hours=opening_hours)

@app.route('/admin/opening-hours', methods=['POST'])
@login_required
def save_opening_hours():
    days = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
    
    for day in days:
        hours = OpeningHours.query.filter_by(day=day).first()
        if not hours:
            hours = OpeningHours(day=day)
            db.session.add(hours)
        
        day_lower = day.lower()
        hours.closed = request.form.get(f'{day_lower}_closed') is not None
        
        if not hours.closed:
            hours.open_time_1 = request.form.get(f'{day_lower}_open_1')
            hours.close_time_1 = request.form.get(f'{day_lower}_close_1')
            hours.open_time_2 = request.form.get(f'{day_lower}_open_2')
            hours.close_time_2 = request.form.get(f'{day_lower}_close_2')
        else:
            hours.open_time_1 = None
            hours.close_time_1 = None
            hours.open_time_2 = None
            hours.close_time_2 = None
    
    db.session.commit()
    flash('Öffnungszeiten wurden aktualisiert')
    return redirect(url_for('admin'))

@app.route('/admin/menu-categories')
@login_required
def admin_menu_categories():
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    return render_template('admin/menu_categories.html', categories=categories)

@app.route('/admin/menu-categories/add', methods=['POST'])
@login_required
def add_menu_category():
    name = request.form.get('name')
    display_name = request.form.get('display_name')
    order = request.form.get('order', type=int)
    is_drink = request.form.get('is_drink_category') == 'on'
    
    category = MenuCategory(
        name=name,
        display_name=display_name,
        order=order,
        is_drink_category=is_drink
    )
    db.session.add(category)
    db.session.commit()
    
    flash('Kategorie wurde hinzugefügt')
    return redirect(url_for('admin_menu_categories'))

@app.route('/admin/menu-categories/edit/<int:id>', methods=['POST'])
@login_required
def edit_menu_category(id):
    category = MenuCategory.query.get_or_404(id)
    category.name = request.form.get('name')
    category.display_name = request.form.get('display_name')
    category.order = request.form.get('order', type=int)
    category.is_drink_category = request.form.get('is_drink_category') == 'on'
    category.active = request.form.get('active') == 'on'
    
    db.session.commit()
    flash('Kategorie wurde aktualisiert')
    return redirect(url_for('admin_menu_categories'))

@app.route('/admin/menu-categories/delete/<int:id>', methods=['POST'])
@login_required
def delete_menu_category(id):
    category = MenuCategory.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    flash('Kategorie wurde gelöscht')
    return redirect(url_for('admin_menu_categories'))

@app.route('/admin/menu-items')
@login_required
def admin_menu_items():
    items = MenuItem.query.join(MenuCategory).order_by(MenuCategory.order, MenuItem.order).all()
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    return render_template('admin/menu_items.html', items=items, categories=categories)

@app.route('/admin/menu-items/add', methods=['POST'])
@login_required
def add_menu_item():
    name = request.form.get('name')
    description = request.form.get('description')
    price = request.form.get('price', type=float)
    category_id = request.form.get('category_id', type=int)
    order = request.form.get('order', type=int)
    is_drink = request.form.get('is_drink') == 'on'
    
    item = MenuItem(
        name=name,
        description=description,
        price=price,
        category_id=category_id,
        order=order,
        is_drink=is_drink
    )
    db.session.add(item)
    db.session.commit()
    
    flash('Gericht wurde hinzugefügt')
    return redirect(url_for('admin_menu_items'))

@app.route('/admin/menu-items/edit/<int:id>', methods=['POST'])
@login_required
def edit_menu_item(id):
    item = MenuItem.query.get_or_404(id)
    item.name = request.form.get('name')
    item.description = request.form.get('description')
    item.price = request.form.get('price', type=float)
    item.category_id = request.form.get('category_id', type=int)
    item.order = request.form.get('order', type=int)
    item.is_drink = request.form.get('is_drink') == 'on'
    item.active = request.form.get('active') == 'on'
    
    db.session.commit()
    flash('Gericht wurde aktualisiert')
    return redirect(url_for('admin_menu_items'))

@app.route('/admin/menu-items/delete/<int:id>', methods=['POST'])
@login_required
def delete_menu_item(id):
    item = MenuItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Gericht wurde gelöscht')
    return redirect(url_for('admin_menu_items'))

with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True)
