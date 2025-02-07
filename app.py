from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.urls import url_parse

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dein-geheimer-schluessel'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
db = SQLAlchemy(app)

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

def init_admin_user():
    # Create admin user if it doesn't exist
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            password_hash=generate_password_hash('admin')  # Change this password in production!
        )
        db.session.add(admin_user)
        db.session.commit()

def init_db():
    with app.app_context():
        db.create_all()
        init_admin_user()
        
        # Initialize opening hours if not exists
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
        
        # Initialize menu categories if they don't exist
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
                    is_drink_category=is_drink,
                    active=True
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
    opening_hours = OpeningHours.query.order_by(OpeningHours.id).all()
    return render_template('admin/index.html', opening_hours=opening_hours)

@app.route('/admin/menu-categories')
@login_required
def admin_menu_categories():
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    return render_template('admin/menu_categories.html', categories=categories)

@app.route('/admin/menu-items')
@login_required
def admin_menu_items():
    items = MenuItem.query.order_by(MenuItem.category_id, MenuItem.order).all()
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    return render_template('admin/menu_items.html', items=items, categories=categories)

@app.route('/admin/menu-items/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    
    if request.method == 'POST':
        try:
            item.name = request.form.get('name')
            item.description = request.form.get('description')
            item.price = float(request.form.get('price'))
            item.category_id = int(request.form.get('category_id'))
            item.order = int(request.form.get('order'))
            item.active = bool(request.form.get('active'))
            
            db.session.commit()
            flash('Gericht wurde erfolgreich aktualisiert', 'success')
            return redirect(url_for('admin_menu_items'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Aktualisieren des Gerichts: {str(e)}', 'error')
    
    return render_template('admin/edit_menu_item.html', item=item, categories=categories)

@app.route('/admin/menu-items/add', methods=['GET', 'POST'])
@login_required
def add_menu_item():
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    
    if request.method == 'POST':
        try:
            new_item = MenuItem(
                name=request.form.get('name'),
                description=request.form.get('description'),
                price=float(request.form.get('price')),
                category_id=int(request.form.get('category_id')),
                order=int(request.form.get('order')),
                active=bool(request.form.get('active'))
            )
            
            db.session.add(new_item)
            db.session.commit()
            flash('Neues Gericht wurde erfolgreich hinzugefügt', 'success')
            return redirect(url_for('admin_menu_items'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Hinzufügen des Gerichts: {str(e)}', 'error')
    
    return render_template('admin/add_menu_item.html', categories=categories)

@app.route('/admin/menu-categories/add', methods=['POST'])
@login_required
def add_menu_category():
    name = request.form.get('name')
    display_name = request.form.get('display_name')
    order = request.form.get('order', type=int, default=0)
    is_drink_category = 'is_drink_category' in request.form
    
    category = MenuCategory(
        name=name,
        display_name=display_name,
        order=order,
        is_drink_category=is_drink_category,
        active=True
    )
    
    db.session.add(category)
    db.session.commit()
    
    flash('Kategorie wurde erfolgreich hinzugefügt', 'success')
    return redirect(url_for('admin_menu_categories'))

@app.route('/admin/menu-categories/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_menu_category(id):
    category = MenuCategory.query.get_or_404(id)
    
    if request.method == 'POST':
        category.name = request.form.get('name')
        category.display_name = request.form.get('display_name')
        category.order = request.form.get('order', type=int, default=0)
        category.is_drink_category = 'is_drink_category' in request.form
        category.active = 'active' in request.form
        
        db.session.commit()
        flash('Kategorie wurde erfolgreich aktualisiert', 'success')
        return redirect(url_for('admin_menu_categories'))
    
    return render_template('admin/edit_menu_category.html', category=category)

@app.route('/admin/menu-categories/delete/<int:id>', methods=['POST'])
@login_required
def delete_menu_category(id):
    category = MenuCategory.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    flash('Kategorie wurde erfolgreich gelöscht', 'success')
    return redirect(url_for('admin_menu_categories'))

@app.route('/admin/menu-items/delete/<int:id>', methods=['POST'])
@login_required
def delete_menu_item(id):
    item = MenuItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Gericht wurde erfolgreich gelöscht', 'success')
    return redirect(url_for('admin_menu_items'))

@app.route('/admin/opening-hours/save', methods=['POST'])
@login_required
def save_opening_hours():
    opening_hours = OpeningHours.query.all()
    
    for hour in opening_hours:
        hour.closed = f'closed_{hour.id}' in request.form
        if not hour.closed:
            hour.open_time_1 = request.form.get(f'open_time_1_{hour.id}')
            hour.close_time_1 = request.form.get(f'close_time_1_{hour.id}')
            hour.open_time_2 = request.form.get(f'open_time_2_{hour.id}')
            hour.close_time_2 = request.form.get(f'close_time_2_{hour.id}')
        else:
            hour.open_time_1 = None
            hour.close_time_1 = None
            hour.open_time_2 = None
            hour.close_time_2 = None
    
    db.session.commit()
    flash('Öffnungszeiten wurden erfolgreich gespeichert', 'success')
    return redirect(url_for('admin'))

with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True)
