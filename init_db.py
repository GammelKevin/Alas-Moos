from app import app, db
from database import MenuItem, OpeningHours

def init_sample_data():
    with app.app_context():
        # Beispielgerichte hinzufügen
        items = [
            MenuItem(
                category='Vorspeisen',
                name='Tzatziki',
                description='Joghurt mit Gurken und Knoblauch',
                price=5.90
            ),
            MenuItem(
                category='Hauptgerichte',
                name='Gyros Teller',
                description='Gyros mit Pommes und Tzatziki',
                price=14.90
            ),
            MenuItem(
                category='Desserts',
                name='Baklava',
                description='Traditionelles Dessert',
                price=6.90
            )
        ]
        
        for item in items:
            db.session.add(item)
        
        # Öffnungszeiten hinzufügen
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in days:
            hours = OpeningHours(
                day=day,
                open_time='11:30',
                close_time='22:00',
                closed=(day == 'monday')  # Montag ist Ruhetag
            )
            db.session.add(hours)
        
        db.session.commit()

if __name__ == '__main__':
    init_sample_data()
    print("Beispieldaten wurden zur Datenbank hinzugefügt!")
