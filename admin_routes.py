from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from models import db, OpeningHours, MenuItem, MenuCategory

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
def index():
    return render_template('admin/index.html')

@admin_bp.route('/menu')
@login_required
def menu():
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    food_items = MenuItem.query.filter_by(is_drink=False).order_by(MenuItem.order).all()
    drink_items = MenuItem.query.filter_by(is_drink=True).order_by(MenuItem.order).all()
    return render_template('admin/menu.html', 
                         categories=categories,
                         food_items=food_items,
                         drink_items=drink_items)

@admin_bp.route('/menu/add', methods=['POST'])
@login_required
def add_menu_item():
    try:
        item = MenuItem(
            name=request.form['name'],
            description=request.form.get('description', ''),
            price=float(request.form['price']),
            category_id=int(request.form['category_id']),
            is_drink=bool(request.form.get('is_drink')),
            unit=request.form.get('unit', ''),
            active=True,
            order=request.form.get('order', 0)
        )
        db.session.add(item)
        db.session.commit()
        flash('Menü-Item erfolgreich hinzugefügt!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Hinzufügen: {str(e)}', 'error')
    return redirect(url_for('admin.menu'))

@admin_bp.route('/menu/edit/<int:id>', methods=['POST'])
@login_required
def edit_menu_item(id):
    try:
        item = MenuItem.query.get_or_404(id)
        item.name = request.form['name']
        item.description = request.form.get('description', '')
        item.price = float(request.form['price'])
        item.category_id = int(request.form['category_id'])
        item.is_drink = bool(request.form.get('is_drink'))
        item.unit = request.form.get('unit', '')
        item.active = bool(request.form.get('active', True))
        item.order = int(request.form.get('order', 0))
        db.session.commit()
        flash('Menü-Item erfolgreich aktualisiert!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Aktualisieren: {str(e)}', 'error')
    return redirect(url_for('admin.menu'))

@admin_bp.route('/menu/delete/<int:id>', methods=['POST'])
@login_required
def delete_menu_item(id):
    try:
        item = MenuItem.query.get_or_404(id)
        db.session.delete(item)
        db.session.commit()
        flash('Menü-Item erfolgreich gelöscht!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen: {str(e)}', 'error')
    return redirect(url_for('admin.menu'))

@admin_bp.route('/opening-hours')
@login_required
def opening_hours():
    hours = OpeningHours.query.order_by(OpeningHours.id).all()
    return render_template('admin/opening_hours.html', opening_hours=hours)

@admin_bp.route('/opening-hours/update', methods=['POST'])
@login_required
def update_opening_hours():
    try:
        for hour in OpeningHours.query.all():
            hour.closed = str(hour.id) in request.form.getlist('closed')
            if not hour.closed:
                hour.open_time = request.form.get(f'open_time_{hour.id}')
                hour.close_time = request.form.get(f'close_time_{hour.id}')
        db.session.commit()
        flash('Öffnungszeiten erfolgreich aktualisiert!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Speichern: {str(e)}', 'error')
    return redirect(url_for('admin.opening_hours'))
