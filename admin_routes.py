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
        # Bestimme die Kategorie und ob es ein Getränk ist
        category_id = int(request.form['category_id'])
        category = MenuCategory.query.get(category_id)
        if not category:
            raise ValueError('Ungültige Kategorie')
        
        # Hole den höchsten order-Wert für diese Kategorie
        max_order = db.session.query(db.func.max(MenuItem.order)).filter_by(
            category_id=category_id
        ).scalar() or 0
        
        # Erstelle das neue Item
        item = MenuItem(
            name=request.form['name'],
            description=request.form.get('description', ''),
            price=float(request.form['price']),
            category_id=category_id,
            is_drink=category.is_drink_category,
            unit=request.form.get('unit', ''),
            active=True,
            order=max_order + 1  # Setze den order-Wert auf den nächsten verfügbaren
        )
        db.session.add(item)
        db.session.commit()
        flash('Menü-Item erfolgreich hinzugefügt!', 'success')
    except ValueError as e:
        db.session.rollback()
        flash(f'Fehler beim Hinzufügen: {str(e)}', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Hinzufügen: Ein unerwarteter Fehler ist aufgetreten', 'error')
    return redirect(url_for('admin.menu'))

@admin_bp.route('/menu/edit/<int:id>', methods=['POST'])
@login_required
def edit_menu_item(id):
    try:
        item = MenuItem.query.get_or_404(id)
        
        # Bestimme die neue Kategorie und ob es ein Getränk ist
        category_id = int(request.form['category_id'])
        category = MenuCategory.query.get(category_id)
        if not category:
            raise ValueError('Ungültige Kategorie')
        
        # Update die Werte
        item.name = request.form['name']
        item.description = request.form.get('description', '')
        item.price = float(request.form['price'])
        item.category_id = category_id
        item.is_drink = category.is_drink_category
        item.unit = request.form.get('unit', '')
        item.active = True
        
        db.session.commit()
        flash('Menü-Item erfolgreich aktualisiert!', 'success')
    except ValueError as e:
        db.session.rollback()
        flash(f'Fehler beim Aktualisieren: {str(e)}', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Aktualisieren: Ein unerwarteter Fehler ist aufgetreten', 'error')
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
        flash('Fehler beim Löschen: Ein unerwarteter Fehler ist aufgetreten', 'error')
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
        closed_days = request.form.getlist('closed')
        
        for hour in OpeningHours.query.all():
            # Prüfe, ob der Tag geschlossen ist
            hour.closed = str(hour.id) in closed_days
            
            # Wenn der Tag nicht geschlossen ist, update die Zeiten
            if not hour.closed:
                open_time = request.form.get(f'open_time_{hour.id}')
                close_time = request.form.get(f'close_time_{hour.id}')
                
                if not open_time or not close_time:
                    raise ValueError(f'Bitte geben Sie gültige Öffnungszeiten für {hour.day_display} ein')
                
                hour.open_time = open_time
                hour.close_time = close_time
        
        db.session.commit()
        flash('Öffnungszeiten erfolgreich aktualisiert!', 'success')
    except ValueError as e:
        db.session.rollback()
        flash(f'Fehler beim Speichern: {str(e)}', 'error')
    except Exception as e:
        db.session.rollback()
        flash('Fehler beim Speichern: Ein unerwarteter Fehler ist aufgetreten', 'error')
    return redirect(url_for('admin.opening_hours'))
