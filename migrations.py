from app import app, db, OpeningHours
from sqlalchemy import text

def migrate_db():
    with app.app_context():
        # Lösche alte Öffnungszeiten-Tabelle
        db.session.execute(text('DROP TABLE IF EXISTS opening_hours'))
        db.session.commit()
        
        # Erstelle neue Tabelle
        db.create_all()
        
        # Füge Standard-Öffnungszeiten hinzu
        default_hours = [
            {'day': 'Montag', 'closed': True},
            {'day': 'Dienstag', 'open_time': '11:30', 'close_time': '14:30'},
            {'day': 'Mittwoch', 'open_time': '11:30', 'close_time': '14:30'},
            {'day': 'Donnerstag', 'open_time': '11:30', 'close_time': '14:30'},
            {'day': 'Freitag', 'open_time': '11:30', 'close_time': '14:30'},
            {'day': 'Samstag', 'open_time': '17:00', 'close_time': '22:00'},
            {'day': 'Sonntag', 'open_time': '11:30', 'close_time': '14:30'}
        ]
        
        for hours in default_hours:
            opening_hours = OpeningHours(
                day=hours['day'],
                open_time=hours.get('open_time'),
                close_time=hours.get('close_time'),
                closed=hours.get('closed', False)
            )
            db.session.add(opening_hours)
        
        db.session.commit()

if __name__ == '__main__':
    migrate_db()
    print("Migration erfolgreich!")
