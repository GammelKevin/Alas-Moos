from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, MenuItem, MenuCategory, OpeningHours, Admin
from admin_routes import admin_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dein-geheimer-schluessel'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialisiere die Datenbank
db.init_app(app)

# Initialisiere Login-Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Registriere die Admin-Routes
app.register_blueprint(admin_bp)

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

def init_db():
    with app.app_context():
        db.create_all()
        
        # Prüfe, ob bereits ein Admin existiert
        if Admin.query.count() == 0:
            admin = Admin(
                username='admin',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin)
            db.session.commit()
        
        # Prüfe, ob bereits Kategorien existieren
        if MenuCategory.query.count() == 0:
            categories = [
                # Speisen
                ('starters', 'Vorspeisen', False),
                ('soups', 'Suppen', False),
                ('salads', 'Salate', False),
                ('lunch', 'Mittagsangebot', False),
                ('fish', 'Fischgerichte', False),
                ('vegetarian', 'Vegetarische Gerichte', False),
                ('steaks', 'Steak vom Grill', False),
                ('desserts', 'Desserts', False),
                # Getränke
                ('softdrinks', 'Alkoholfreie Getränke', True),
                ('beer', 'Biere', True),
                ('wine', 'Weine', True),
                ('spirits', 'Spirituosen', True)
            ]
            
            for order, (name, display_name, is_drink) in enumerate(categories):
                category = MenuCategory(
                    name=name,
                    display_name=display_name,
                    is_drink_category=is_drink,
                    order=order,
                    active=True
                )
                db.session.add(category)
            db.session.commit()
        
        # Prüfe, ob bereits Öffnungszeiten existieren
        if OpeningHours.query.count() == 0:
            days = [
                ('Monday', 'Montag'),
                ('Tuesday', 'Dienstag'),
                ('Wednesday', 'Mittwoch'),
                ('Thursday', 'Donnerstag'),
                ('Friday', 'Freitag'),
                ('Saturday', 'Samstag'),
                ('Sunday', 'Sonntag')
            ]
            
            for day_en, day_de in days:
                hours = OpeningHours(
                    day=day_en,
                    day_display=day_de,
                    open_time='11:30',
                    close_time='22:00',
                    closed=False
                )
                db.session.add(hours)
            db.session.commit()

@app.route('/')
def home():
    food_items = MenuItem.query.filter_by(active=True, is_drink=False).order_by(MenuItem.order).all()
    drink_items = MenuItem.query.filter_by(active=True, is_drink=True).order_by(MenuItem.order).all()
    categories = MenuCategory.query.filter_by(active=True).order_by(MenuCategory.order).all()
    opening_hours = OpeningHours.query.order_by(OpeningHours.id).all()
    return render_template('index.html',
                         food_items=food_items,
                         drink_items=drink_items,
                         categories=categories,
                         opening_hours=opening_hours)

@app.route('/menu')
def menu():
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    food_items = MenuItem.query.filter_by(is_drink=False, active=True).order_by(MenuItem.order).all()
    drink_items = MenuItem.query.filter_by(is_drink=True, active=True).order_by(MenuItem.order).all()
    return render_template('menu.html', 
                         categories=categories,
                         food_items=food_items,
                         drink_items=drink_items)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Admin.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin.index'))
        else:
            flash('Ungültige Anmeldedaten')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Initialisiere die Datenbank beim Start
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True)
