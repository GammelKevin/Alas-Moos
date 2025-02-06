from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from database import db, MenuItem, MenuCategory, OpeningHours, Admin

load_dotenv()

app = Flask(__name__)

# Konfiguration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-123')

# Datenbank-Konfiguration
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail-Konfiguration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Extensions initialisieren
db.init_app(app)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# Datenbank beim Start initialisieren
with app.app_context():
    db.create_all()
    
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
        ('pan_dishes', 'Pfannengerichte & Ofengerichte', False),
        ('lamb', 'Spezialitäten vom Lamm', False),
        ('meat', 'Fleischgerichte', False),
        ('mixed_plates', 'Gemischte Fleischplatten vom Grill', False),
        ('desserts', 'Desserts', False),
        
        # Getränke
        ('aperitifs', 'Aperitifs', True),
        ('water_soft', 'Wasser & Softdrinks', True),
        ('juices', 'Säfte & Schorlen', True),
        ('beer', 'Bier', True),
        ('digestifs', 'Digestifs', True),
        ('longdrinks', 'Longdrinks', True),
        ('metaxa', 'Metaxa Brandy', True),
        ('wine_open', 'Offene Weine', True),
        ('wine_bottle', 'Weinliste', True),
        ('ouzo', 'Ouzo', True),
    ]
    
    for name, display_name, is_drink in categories:
        if not db.session.query(MenuCategory).filter_by(name=name).first():
            category = MenuCategory(
                name=name,
                display_name=display_name,
                is_drink_category=is_drink
            )
            db.session.add(category)
    
    # Admin-Account erstellen
    if not db.session.query(Admin).filter_by(username='admin').first():
        admin = Admin(
            username='admin',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin)
        
    # Beispiel-Öffnungszeiten
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for day in days:
        if not db.session.query(OpeningHours).filter_by(day=day).first():
            hours = OpeningHours(
                day=day,
                open_time='11:30',
                close_time='22:00',
                closed=(day == 'monday')
            )
            db.session.add(hours)
    
    db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Admin, int(user_id))

@app.route('/')
def home():
    menu_items = db.session.query(MenuItem).filter_by(active=True, is_drink=False).all()
    drink_items = db.session.query(MenuItem).filter_by(active=True, is_drink=True).all()
    categories = db.session.query(MenuCategory).filter_by(active=True).order_by(MenuCategory.order).all()
    opening_hours = db.session.query(OpeningHours).all()
    return render_template('index.html', 
                         menu_items=menu_items,
                         drink_items=drink_items,
                         categories=categories,
                         opening_hours=opening_hours)

@app.route('/menu')
def menu():
    return redirect(url_for('home') + '#menu')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = db.session.query(Admin).filter_by(username=username).first()
        
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
    menu_items = db.session.query(MenuItem).all()
    categories = db.session.query(MenuCategory).order_by(MenuCategory.order).all()
    opening_hours = db.session.query(OpeningHours).all()
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
    item = db.session.get(MenuItem, id)
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
    item = db.session.get(MenuItem, id)
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/hours/update', methods=['POST'])
@login_required
def update_hours():
    data = request.form
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
        hours = db.session.query(OpeningHours).filter_by(day=day).first()
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
            recipients=[os.getenv('MAIL_DEFAULT_SENDER')],
            body=msg_body
        )
        mail.send(msg)
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"Fehler beim Senden der E-Mail: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
