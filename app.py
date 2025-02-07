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
        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()

        # Admin-Benutzer erstellen
        admin = Admin(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)

        # Kategorien erstellen
        categories = [
            ('starters', 'Vorspeisen', False),
            ('soups', 'Suppen', False),
            ('salads', 'Salate', False),
            ('lunch', 'Mittagsangebot', False),
            ('fish', 'Fischgerichte', False),
            ('vegetarian', 'Vegetarische Gerichte', False),
            ('steaks', 'Steak vom Grill', False),
            ('desserts', 'Desserts', False),
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

        # Öffnungszeiten initialisieren
        days = [
            ('Montag', True),  # Montag geschlossen
            ('Dienstag', False, '11:30', '14:00', '17:00', '22:00'),
            ('Mittwoch', False, '11:30', '14:00', '17:00', '22:00'),
            ('Donnerstag', False, '11:30', '14:00', '17:00', '22:00'),
            ('Freitag', False, '11:30', '14:00', '17:00', '22:00'),
            ('Samstag', False, '11:30', '14:00', '17:00', '22:00'),
            ('Sonntag', False, '11:30', '14:00', '17:00', '22:00')
        ]
        
        for day_data in days:
            if len(day_data) == 2:  # Geschlossener Tag
                day, closed = day_data
                db.session.add(OpeningHours(
                    day=day,
                    closed=closed
                ))
            else:  # Tag mit Öffnungszeiten
                day, closed, open1, close1, open2, close2 = day_data
                db.session.add(OpeningHours(
                    day=day,
                    closed=closed,
                    open_time_1=open1,
                    close_time_1=close1,
                    open_time_2=open2,
                    close_time_2=close2
                ))

        db.session.commit()

@app.route('/')
def home():
    food_items = MenuItem.query.filter_by(active=True, is_drink=False).order_by(MenuItem.order).all()
    drink_items = MenuItem.query.filter_by(active=True, is_drink=True).order_by(MenuItem.order).all()
    categories = MenuCategory.query.filter_by(active=True).order_by(MenuCategory.order).all()
    opening_hours = OpeningHours.query.all()
    formatted_hours = []
    
    for hour in opening_hours:
        if hour.closed:
            formatted_hours.append(f"{hour.day}: Geschlossen")
        else:
            times = []
            if hour.open_time_1 and hour.close_time_1:
                times.append(f"{hour.open_time_1}-{hour.close_time_1}")
            if hour.open_time_2 and hour.close_time_2:
                times.append(f"{hour.open_time_2}-{hour.close_time_2}")
            
            if times:
                formatted_hours.append(f"{hour.day}: {' & '.join(times)}")
            else:
                formatted_hours.append(f"{hour.day}: Keine Zeiten angegeben")

    return render_template('index.html',
                         food_items=food_items,
                         drink_items=drink_items,
                         categories=categories,
                         opening_hours=formatted_hours)

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

@app.route('/admin')
@login_required
def admin():
    opening_hours = OpeningHours.query.all()
    return render_template('admin/index.html', opening_hours=opening_hours)

@app.route('/admin/opening-hours', methods=['POST'])
@login_required
def save_opening_hours():
    days = ['montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag', 'samstag', 'sonntag']
    
    for day in days:
        hours = OpeningHours.query.filter_by(day=day.capitalize()).first()
        if not hours:
            hours = OpeningHours(day=day.capitalize())
            db.session.add(hours)
        
        hours.closed = request.form.get(f'{day}_closed') is not None
        if not hours.closed:
            hours.open_time_1 = request.form.get(f'{day}_open_1')
            hours.close_time_1 = request.form.get(f'{day}_close_1')
            hours.open_time_2 = request.form.get(f'{day}_open_2')
            hours.close_time_2 = request.form.get(f'{day}_close_2')
        else:
            hours.open_time_1 = None
            hours.close_time_1 = None
            hours.open_time_2 = None
            hours.close_time_2 = None
    
    db.session.commit()
    flash('Öffnungszeiten wurden aktualisiert')
    return redirect(url_for('admin'))

# Initialisiere die Datenbank beim Start
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True)
