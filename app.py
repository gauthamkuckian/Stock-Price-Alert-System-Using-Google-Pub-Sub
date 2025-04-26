import os
import sqlite3
import time
import smtplib
from threading import Thread
from datetime import datetime
from email.mime.text import MIMEText
from flask import Flask, render_template, jsonify, request
import yfinance as yf
import pytz
from dotenv import load_dotenv
from google.cloud import pubsub_v1

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
EMAIL_SENDER = os.getenv('USER_EMAIL')
EMAIL_PASSWORD = os.getenv('USER_PASSWORD')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID')
TOPIC_NAME = "stock-alerts"
SUBSCRIPTION_NAME = "stock-alerts-sub"

# Initialize Pub/Sub clients
publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()
topic_path = publisher.topic_path(GCP_PROJECT_ID, TOPIC_NAME)
subscription_path = subscriber.subscription_path(GCP_PROJECT_ID, SUBSCRIPTION_NAME)

# Database setup
def init_db():
    conn = sqlite3.connect('alerts.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS alerts
                 (email TEXT, threshold REAL, direction TEXT, timestamp DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (email TEXT PRIMARY KEY, first_seen DATETIME)''')
    conn.commit()
    conn.close()

init_db()

# Email function
def send_email(to_email, subject, body):
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_SENDER
        msg['To'] = to_email
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False

# Price publisher
def publish_price_updates():
    while True:
        try:
            apple = yf.Ticker("AAPL")
            current_price = apple.history(period='1d')['Close'].iloc[-1]
            data = str(current_price).encode("utf-8")
            future = publisher.publish(topic_path, data)
            future.result()
            print(f"Published price: {current_price}")
        except Exception as e:
            print(f"Error publishing price: {str(e)}")
        time.sleep(300)

# Message handler
def handle_price_message(message):
    try:
        current_price = float(message.data.decode("utf-8"))
        print(f"Processing price update: {current_price}")
        
        conn = sqlite3.connect('alerts.db')
        c = conn.cursor()
        c.execute("SELECT email, threshold, direction FROM alerts")
        alerts = c.fetchall()
        
        for email, threshold, direction in alerts:
            if (direction == 'above' and current_price > threshold) or \
               (direction == 'below' and current_price < threshold):
                subject = f"AAPL Price Alert: ${current_price:.2f} {'>' if direction == 'above' else '<'} ${threshold:.2f}"
                body = f"Apple stock price is now ${current_price:.2f} which is {direction} your alert threshold of ${threshold:.2f}"
                
                if send_email(email, subject, body):
                    c.execute("DELETE FROM alerts WHERE email=? AND threshold=? AND direction=?", 
                             (email, threshold, direction))
                    conn.commit()
        
        message.ack()
        conn.close()
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        message.nack()

# Subscriber setup
def setup_subscriber():
    try:
        # Create subscription if it doesn't exist
        try:
            subscriber.create_subscription(
                name=subscription_path,
                topic=topic_path
            )
            print(f"Created subscription: {SUBSCRIPTION_NAME}")
        except Exception as e:
            print(f"Subscription likely exists: {str(e)}")
            
        # Start listening
        streaming_pull_future = subscriber.subscribe(
            subscription_path,
            callback=handle_price_message
        )
        print(f"Listening for messages on {SUBSCRIPTION_NAME}...")
        
        with subscriber:
            try:
                streaming_pull_future.result()
            except Exception as e:
                streaming_pull_future.cancel()
                print(f"Subscriber stopped: {str(e)}")
                
    except Exception as e:
        print(f"Failed to set up subscriber: {str(e)}")

# Flask routes
@app.route('/')
def index():
    return render_template('chart.html')

@app.route('/<timeframe>')
def timeframe_route(timeframe):
    try:
        params = {
            'today': {'interval': '5m', 'period': '1d'},
            'day': {'interval': '1h', 'period': '5d'},
            'month': {'interval': '1d', 'period': '1mo'},
            'year': {'interval': '1wk', 'period': '1y'}
        }
        
        config = params.get(timeframe, {'interval': '1d', 'period': '1mo'})
        apple = yf.Ticker("AAPL")
        hist = apple.history(**config, prepost=True)
        
        if hist.empty:
            return jsonify({'error': 'No data available'}), 404
            
        hist.index = hist.index.tz_convert(pytz.timezone('America/New_York'))
        hist = hist[['Close']].reset_index()
        hist.columns = ['timestamp', 'price']
        
        if timeframe == 'today':
            today = datetime.now(pytz.timezone('America/New_York')).date()
            hist = hist[hist['timestamp'].dt.date == today]
        
        return jsonify(hist.to_dict(orient='records'))
        
    except Exception as e:
        print(f"Error in {timeframe} endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/set_alert', methods=['POST'])
def set_alert():
    try:
        data = request.json
        email = data.get('email')
        threshold = float(data.get('threshold'))
        direction = data.get('direction')
        
        if not email or not threshold or not direction:
            return jsonify({'error': 'Missing parameters'}), 400
        
        conn = sqlite3.connect('alerts.db')
        c = conn.cursor()
        
        c.execute("INSERT INTO alerts VALUES (?, ?, ?, datetime('now'))", 
                 (email, threshold, direction))
        c.execute("INSERT OR IGNORE INTO users (email, first_seen) VALUES (?, datetime('now'))", 
                 (email,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/users', methods=['GET'])
def list_users():
    try:
        conn = sqlite3.connect('alerts.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users")
        users = [{'email': row[0], 'first_seen': row[1]} for row in c.fetchall()]
        conn.close()
        return jsonify(users)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Validate configurations
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("Warning: Email credentials not properly configured")
    if not GCP_PROJECT_ID:
        print("Warning: GCP_PROJECT_ID not set")
    
    # Start background threads
    Thread(target=publish_price_updates, daemon=True).start()
    Thread(target=setup_subscriber, daemon=True).start()
    
    # Start Flask app
    app.run(debug=True,port=8080)