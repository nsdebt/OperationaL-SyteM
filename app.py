import os
import json
import joblib
import smtplib
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from flask import Flask, jsonify, request, render_template
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from flask_wtf.csrf import CSRFProtect
# Import shared extensions and initialization function
from extensions import db, migrate, socketio, login_manager, init_extensions
from routes import main  # Import the fully defined blueprint from routes
from utils import predict_default_risk  # Import the shared function from utils to avoid circular import

# Initialize Flask app
app = Flask(__name__)
csrf = CSRFProtect(app)
DB_FOLDER = r'C:\Users\Administrator\Desktop\NS-Debt-Management'

# ---------------------------------------------------
# Configuration and Environment Variables
# ---------------------------------------------------
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')  # Environment variable for security
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads/'
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'memory://'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'info@nsdebt.co.za')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'Mapulashuma47@')
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'reactor.aserv.co.za')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))

app.config.from_object(Config)

# ---------------------------------------------------
# Initialize Extensions with the app
# ---------------------------------------------------
init_extensions(app)

# Ensure database tables are created
with app.app_context():
    db.create_all()

# Register the blueprint after initializing extensions
app.register_blueprint(main)

# ---------------------------------------------------
# Utility Functions (Application-specific)
# ---------------------------------------------------
def fetch_client_data(client_id):
    """Mock function to fetch client data."""
    return {
        "income": 5000,
        "payment_history": 3,
        "credit_score": 650,
        "spending_patterns": 2,
        "debt_balance": 20000
    }

def fetch_credit_report(client_id):
    """
    Simulate fetching a credit report via an API.
    In production, replace this with a real API call.
    """
    return {
        "client_id": client_id,
        "credit_score": 580,
        "report_date": datetime.now().strftime("%Y-%m-%d"),
        "discrepancies": ["Outdated address", "Duplicate account entry"]
    }

def generate_dispute_letter(client_id, discrepancies):
    """
    Generate a dispute letter based on detected discrepancies.
    """
    letter = f"""Dear Credit Bureau,

I am writing to dispute the following discrepancies on my credit report:
"""
    for item in discrepancies:
        letter += f"- {item}\n"
    letter += "\nI kindly request that you investigate and correct these issues immediately.\n\nSincerely,\nClient {client_id}"
    return letter

def send_email(client_email, subject, body):
    """
    Send an email using SMTP.
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = client_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.sendmail(msg['From'], client_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

# ----- Flask Route for Credit Repair -----
@app.route('/credit_repair', methods=['POST'])
def credit_repair():
    client_id = request.form.get('client_id')
    additional_details = request.form.get('additional_details')
    captcha = request.form.get('captcha')
    
    if captcha.lower() != "abc123":
        return jsonify({"success": False, "message": "Captcha verification failed."})
    
    credit_report = fetch_credit_report(client_id)
    discrepancies = credit_report.get("discrepancies", [])
    
    if discrepancies:
        dispute_letter = generate_dispute_letter(client_id, discrepancies)
        client_email = "client_email@example.com"  # Replace with actual lookup logic
        email_sent = send_email(client_email, "Your Credit Dispute Letter", dispute_letter)
        response_message = "Discrepancies found. A dispute letter has been sent." if email_sent else "Discrepancies found, but email sending failed."
    else:
        response_message = "No discrepancies found in your credit report."
    
    return jsonify({"success": True, "message": response_message, "credit_report": credit_report})

def update_case_priority(client_id, priority):
    """Update the case priority based on risk level."""
    print(f"Updated client {client_id} priority to {priority}")

def analyze_payment_trends(client_data):
    return "Stable" if client_data["payment_history"] > 2 else "Irregular"

def prioritize_debt_cases(client_id):
    client_data = fetch_client_data(client_id)
    risk = predict_default_risk([
        client_data["income"], client_data["payment_history"], client_data["credit_score"], client_data["spending_patterns"]
    ])
    priority = "High" if risk == "High Risk" else "Low"
    update_case_priority(client_id, priority)
    return {"client_id": client_id, "risk_level": risk, "priority": priority}

def train_default_prediction_model():
    try:
        data_path = 'consumer_behavior_data.csv'
        if not os.path.exists(data_path):
            print(f"Error: {data_path} not found.")
            return
        
        data = pd.read_csv(data_path)
        X = data[['income', 'payment_history', 'credit_score', 'spending_patterns']]
        y = data['default']
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
        
        model = LogisticRegression()
        model.fit(X_train, y_train)
        
        joblib.dump(model, 'debt_default_model.pkl')
        joblib.dump(scaler, 'scaler.pkl')
        
        print(f"Model Accuracy: {model.score(X_test, y_test) * 100:.2f}%")
    except Exception as e:
        print(f"Error during model training: {e}")

# ---------------------------------------------------
# Run the Flask App with SocketIO
# ---------------------------------------------------
if __name__ == '__main__':
    socketio.run(app, debug=True, port=5002)
