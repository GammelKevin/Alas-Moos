from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class OpeningHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20), nullable=False)
    open_time = db.Column(db.String(5))
    close_time = db.Column(db.String(5))
    closed = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<OpeningHours {self.day}>'

class MenuCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)
    is_drink_category = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    image_path = db.Column(db.String(255))
    items = db.relationship('MenuItem', backref='category', lazy=True)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('menu_category.id'), nullable=False)
    order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    image_path = db.Column(db.String(255))
    is_lunch_special = db.Column(db.Boolean, default=False)
    allergens = db.Column(db.String(255))
    portion_size = db.Column(db.String(50))
    spiciness_level = db.Column(db.Integer, default=0)  # 0-3: nicht scharf bis sehr scharf
    is_vegetarian = db.Column(db.Boolean, default=False)
    is_vegan = db.Column(db.Boolean, default=False)
