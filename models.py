from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

class MenuCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(50), nullable=False)
    is_drink_category = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    items = db.relationship('MenuItem', backref='category', lazy=True)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('menu_category.id'), nullable=False)
    is_drink = db.Column(db.Boolean, default=False)
    unit = db.Column(db.String(20))
    active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)

class OpeningHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20), nullable=False)
    day_display = db.Column(db.String(20), nullable=False)
    open_time = db.Column(db.String(5), nullable=False, default='11:30')
    close_time = db.Column(db.String(5), nullable=False, default='22:00')
    closed = db.Column(db.Boolean, default=False)
