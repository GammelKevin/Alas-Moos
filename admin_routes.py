from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from database import db, OpeningHours, MenuItem, MenuCategory

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
def index():
    return render_template('admin/index.html')

@admin_bp.route('/opening-hours', methods=['GET', 'POST'])
@login_required
def opening_hours():
    hours = OpeningHours.query.order_by(OpeningHours.id).all()
    return render_template('admin/opening_hours.html', opening_hours=hours)

@admin_bp.route('/update-opening-hours', methods=['POST'])
@login_required
def update_opening_hours():
    try:
        ids = request.form.getlist('ids[]')
        days = request.form.getlist('days[]')
        day_displays = request.form.getlist('day_displays[]')
        open_times = request.form.getlist('open_times[]')
        close_times = request.form.getlist('close_times[]')
        closed = request.form.getlist('closed[]')

        for i, id in enumerate(ids):
            hour = OpeningHours.query.get(id)
            if hour:
                hour.day = days[i]
                hour.day_display = day_displays[i]
                hour.open_time = open_times[i]
                hour.close_time = close_times[i]
                hour.closed = str(id) in closed

        db.session.commit()
        flash('Öffnungszeiten wurden erfolgreich aktualisiert!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Speichern der Öffnungszeiten: {str(e)}', 'error')

    return redirect(url_for('admin.opening_hours'))

@admin_bp.route('/menu')
@login_required
def menu():
    items = MenuItem.query.all()
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    return render_template('admin/menu.html', items=items, categories=categories)

@admin_bp.route('/menu/add', methods=['GET', 'POST'])
@login_required
def add_menu_item():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            price = float(request.form.get('price'))
            category_id = int(request.form.get('category_id'))
            is_drink = request.form.get('is_drink') == 'true'
            active = request.form.get('active') == 'true'
            unit = request.form.get('unit')

            item = MenuItem(
                name=name,
                description=description,
                price=price,
                category_id=category_id,
                is_drink=is_drink,
                active=active,
                unit=unit
            )
            db.session.add(item)
            db.session.commit()
            flash('Menü-Item erfolgreich hinzugefügt!', 'success')
            return redirect(url_for('admin.menu'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Hinzufügen des Menü-Items: {str(e)}', 'error')

    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    return render_template('admin/add_menu_item.html', categories=categories)

@admin_bp.route('/menu/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_menu_item(id):
    item = MenuItem.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            item.name = request.form.get('name')
            item.description = request.form.get('description')
            item.price = float(request.form.get('price'))
            item.category_id = int(request.form.get('category_id'))
            item.is_drink = request.form.get('is_drink') == 'true'
            item.active = request.form.get('active') == 'true'
            item.unit = request.form.get('unit')

            db.session.commit()
            flash('Menü-Item erfolgreich aktualisiert!', 'success')
            return redirect(url_for('admin.menu'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Aktualisieren des Menü-Items: {str(e)}', 'error')

    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    return render_template('admin/edit_menu_item.html', item=item, categories=categories)

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
        flash(f'Fehler beim Löschen des Menü-Items: {str(e)}', 'error')
    
    return redirect(url_for('admin.menu'))
