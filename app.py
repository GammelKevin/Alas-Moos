from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from database import db, MenuItem, OpeningHours, Admin

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-123')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail-Konfiguration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

db.init_app(app)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

def init_db():
    with app.app_context():
        db.create_all()
        # Create default admin if not exists
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(
                username='admin',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin)
            db.session.commit()

@app.route('/')
def home():
    menu_items = MenuItem.query.filter_by(active=True).all()
    opening_hours = OpeningHours.query.all()
    return render_template('index.html', menu_items=menu_items, opening_hours=opening_hours)

@app.route('/menu')
def menu():
    menu_items = MenuItem.query.filter_by(active=True).all()
    return render_template('menu.html', menu_items=menu_items)

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
    opening_hours = OpeningHours.query.all()
    return render_template('admin/dashboard.html', menu_items=menu_items, opening_hours=opening_hours)

@app.route('/admin/menu/add', methods=['POST'])
@login_required
def add_menu_item():
    data = request.form
    item = MenuItem(
        category=data['category'],
        name=data['name'],
        description=data['description'],
        price=float(data['price']),
        active=True
    )
    db.session.add(item)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/menu/edit/<int:id>', methods=['POST'])
@login_required
def edit_menu_item(id):
    item = MenuItem.query.get_or_404(id)
    data = request.form
    item.category = data['category']
    item.name = data['name']
    item.description = data['description']
    item.price = float(data['price'])
    item.active = 'active' in data
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/menu/delete/<int:id>')
@login_required
def delete_menu_item(id):
    item = MenuItem.query.get_or_404(id)
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
            recipients=[os.getenv('MAIL_DEFAULT_SENDER')],
            body=msg_body
        )
        mail.send(msg)
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"Fehler beim Senden der E-Mail: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
