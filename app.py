from flask import Flask, render_template, request, jsonify
from flask_mail import Mail, Message
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Mail-Konfiguration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

mail = Mail(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route('/reservierung', methods=['POST'])
def reservierung():
    data = request.get_json()
    
    # E-Mail zusammenstellen
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
