from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, MenuItem, MenuCategory, OpeningHours, Admin
from admin_routes import admin_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dein-geheimer-schluessel'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Datenbank-Konfiguration
# DATABASE_URL = os.getenv('DATABASE_URL')
# if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
#     DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
# app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///restaurant.db'

# Mail-Konfiguration
# app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
# app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
# app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
# app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
# app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
# app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Initialisiere die Datenbank
db.init_app(app)

# Initialisiere Login-Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# Registriere die Admin-Routes
app.register_blueprint(admin_bp)

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# Funktion zum Initialisieren der Datenbank
def init_db():
    with app.app_context():
        db.create_all()
    
    # Prüfe, ob bereits Kategorien existieren
    if MenuCategory.query.count() == 0:
        # Standard-Kategorien erstellen
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
        # Standard-Öffnungszeiten erstellen
        opening_hours = [
            ('Monday', 'Montag', '11:30', '22:00', False),
            ('Tuesday', 'Dienstag', '11:30', '22:00', False),
            ('Wednesday', 'Mittwoch', '11:30', '22:00', False),
            ('Thursday', 'Donnerstag', '11:30', '22:00', False),
            ('Friday', 'Freitag', '11:30', '23:00', False),
            ('Saturday', 'Samstag', '11:30', '23:00', False),
            ('Sunday', 'Sonntag', '11:30', '22:00', False)
        ]
        
        for day_en, day_de, open_time, close_time, closed in opening_hours:
            hours = OpeningHours(
                day=day_en,
                day_display=day_de,
                open_time=open_time,
                close_time=close_time,
                closed=closed
            )
            db.session.add(hours)
        
        db.session.commit()

    # Prüfe, ob bereits ein Admin-Account existiert
    if Admin.query.count() == 0:
        # Standard Admin-Account erstellen
        admin = Admin(
            username='admin',
            password_hash=generate_password_hash('admin123', method='pbkdf2')
        )
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def home():
    menu_items = MenuItem.query.filter_by(active=True, is_drink=False).all()
    drink_items = MenuItem.query.filter_by(active=True, is_drink=True).all()
    categories = MenuCategory.query.filter_by(active=True).order_by(MenuCategory.order).all()
    opening_hours = OpeningHours.query.order_by(OpeningHours.id).all()

    # Wenn keine Öffnungszeiten existieren, initialisiere die Datenbank neu
    if not opening_hours:
        init_db()
        opening_hours = OpeningHours.query.order_by(OpeningHours.id).all()

    return render_template('index.html', 
                         menu_items=menu_items,
                         drink_items=drink_items,
                         categories=categories,
                         opening_hours=opening_hours)

@app.route('/menu')
def menu():
    menu_items = MenuItem.query.filter_by(active=True, is_drink=False).all()
    drink_items = MenuItem.query.filter_by(active=True, is_drink=True).all()
    categories = MenuCategory.query.filter_by(active=True).order_by(MenuCategory.order).all()
    return render_template('menu.html', 
                         menu_items=menu_items,
                         drink_items=drink_items,
                         categories=categories)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Admin.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Ungültige Anmeldedaten')
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin_dashboard():
    menu_items = MenuItem.query.all()
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    opening_hours = OpeningHours.query.all()
    return render_template('admin/dashboard.html', 
                         menu_items=menu_items,
                         categories=categories,
                         opening_hours=opening_hours)

@app.route('/admin/menu/add', methods=['POST'])
@login_required
def add_menu_item():
    data = request.form
    item = MenuItem(
        category=data['category'],
        name=data['name'],
        description=data.get('description'),
        price=float(data['price']),
        unit=data.get('unit'),
        is_drink=data.get('is_drink') == 'true',
        active=True
    )
    db.session.add(item)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/menu/edit/<int:id>', methods=['POST'])
@login_required
def edit_menu_item(id):
    item = MenuItem.query.get(id)
    if not item:
        return redirect(url_for('admin_dashboard'))
    
    data = request.form
    item.category = data['category']
    item.name = data['name']
    item.description = data.get('description')
    item.price = float(data['price'])
    item.unit = data.get('unit')
    item.is_drink = data.get('is_drink') == 'true'
    item.active = 'active' in data
    
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/menu/delete/<int:id>')
@login_required
def delete_menu_item(id):
    item = MenuItem.query.get(id)
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/hours/update', methods=['POST'])
@login_required
def update_hours():
    data = request.form
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
        hours = OpeningHours.query.filter_by(day=day).first()
        if not hours:
            hours = OpeningHours(day=day)
            db.session.add(hours)
        
        hours.open_time = data.get(f'{day}_open', '00:00')
        hours.close_time = data.get(f'{day}_close', '00:00')
        hours.closed = f'{day}_closed' in data
    
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/reservierung', methods=['POST'])
def reservierung():
    data = request.get_json()
    
    msg_body = f"""
    Neue Reservierungsanfrage:
    
    Name: {data.get('name')}
    Telefon: {data.get('telefon')}
    Datum: {data.get('datum')}
    Zeit: {data.get('zeit')}
    Anzahl Personen: {data.get('personen')}
    Nachricht: {data.get('nachricht', 'Keine')}
    """
    
    try:
        msg = Message(
            'Neue Reservierungsanfrage',
            recipients=['your-email@example.com'],  # Bitte ersetzen Sie durch Ihre E-Mail-Adresse
            body=msg_body
        )
        mail = Mail(app)
        mail.send(msg)
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"Fehler beim Senden der E-Mail: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Initialisiere die Datenbank beim Start
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True)
