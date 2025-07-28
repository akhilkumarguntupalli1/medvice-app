from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
import os
import sqlite3
import smtplib
from email.mime.text import MIMEText
from werkzeug.security import generate_password_hash, check_password_hash
import time
import datetime
import threading
import schedule
import requests
import json

import google.generativeai as genai

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

DATABASE = 'medvice.db'

# -------------------- Fast2SMS Credentials --------------------
FAST2SMS_API_KEY = 'OTcSNy0zpELkDshCnvuFeKWqj6xYlXA3i4wRUmfI1ZVd9HMraJDZnSmOv2NwK4B3tkphI8d9EWxQuTie'  # Replace with your Fast2SMS API key

# -------------------- Gemini API Key --------------------
genai.configure(api_key="AIzaSyBpG2732lNGnClRx0bJG4s2FUFlo6deKVo")

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def send_sms(to_number, message):
    try:
        # Remove any + prefix and country code if present
        if to_number.startswith('+'):
            to_number = to_number[1:]  # Remove the + sign
        if to_number.startswith('91') and len(to_number) > 10:
            to_number = to_number[2:]  # Remove country code

        print(f"📤 Sending SMS to: {to_number}")
        
        url = "https://www.fast2sms.com/dev/bulkV2"
        
        payload = {
            "route": "q",  # Use 'q' for quick SMS without DLT
            "message": message.strip(),
            "language": "english",
            "flash": 0,
            "numbers": to_number,
        }
        
        headers = {
            "authorization": FAST2SMS_API_KEY,
            "Content-Type": "application/json"
        }
        
        start = time.time()
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        duration = time.time() - start
        
        response_data = response.json()
        
        if response_data.get('return') == True:
            print(f"✅ SMS sent! Request ID: {response_data.get('request_id')} (Time taken: {duration:.2f} sec)")
            return True
        else:
            print(f"❌ Fast2SMS error: {response_data.get('message')}")
            return False
    except Exception as ex:
        print(f"❌ General error: {ex}")
        return False

def generate_email_html(user_name, symptoms, disease, description, medications, diets, workouts, precautions, ai_powered=False):
    ai_badge = '<span style="background-color: #6c5ce7; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-left: 10px;">AI Powered</span>' if ai_powered else ''
    
    return f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f9f9f9;
                padding: 20px;
            }}
            .container {{
                background-color: #fff;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                max-width: 600px;
                margin: auto;
            }}
            h2 {{
                color: #2c3e50;
            }}
            ul {{
                padding-left: 20px;
            }}
            li {{
                margin-bottom: 5px;
            }}
            .section {{
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Hello {user_name},</h2>
            <p>Based on your symptoms: <b>{symptoms}</b></p>

            <div class="section">
                <h3>Predicted Disease {ai_badge}</h3>
                <p><b>{disease}</b></p>
            </div>

            <div class="section">
                <h3>Description</h3>
                <p>{description}</p>
            </div>

            <div class="section">
                <h3>Medications</h3>
                <ul>{''.join(f"<li>{med}</li>" for med in medications)}</ul>
            </div>

            <div class="section">
                <h3>Diet Recommendations</h3>
                <ul>{''.join(f"<li>{diet}</li>" for diet in diets)}</ul>
            </div>

            <div class="section">
                <h3>Workout Suggestions</h3>
                <ul>{''.join(f"<li>{work}</li>" for work in workouts)}</ul>
            </div>

            <div class="section">
                <h3>Precautions</h3>
                <ul>{''.join(f"<li>{prec}</li>" for prec in precautions)}</ul>
            </div>

            <p>Stay healthy,<br><b>MedVice Team</b></p>
        </div>
    </body>
    </html>
    """

def send_email(to_email, subject, html_body):
    sender_email = 'medvice2025@gmail.com'
    sender_password = 'nshwcbdrxmnwjgui'

    msg = MIMEText(html_body, 'html')
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
        print("✅ HTML Email sent successfully.")
        return True
    except Exception as e:
        print("❌ Email sending failed:", e)
        return False

def send_morning_reminders():
    """Send morning reminder messages to all users"""
    try:
        conn = get_db_connection()
        users = conn.execute('SELECT * FROM users').fetchall()
        conn.close()
        
        for user in users:
            message = (
                f"Good morning {user['full_name']}! 🌞\n\n"
                f"Remember to check your MedVice dashboard for your health recommendations today.\n\n"
                f"Stay healthy!\n"
                f"- Team MedVice 💚"
            )
            
            # Send SMS
            send_sms(user['phone'], message)
            
            # Send email
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <div style="background-color: #fff; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); max-width: 600px; margin: auto;">
                    <h2 style="color: #2c3e50;">Good Morning, {user['full_name']}! 🌞</h2>
                    <p>We hope you're having a great start to your day.</p>
                    <p>Don't forget to check your <a href="http://localhost:5000/dashboard">MedVice dashboard</a> for your health recommendations and follow your personalized health plan.</p>
                    <p>Stay healthy!<br><b>MedVice Team 💚</b></p>
                </div>
            </body>
            </html>
            """
            
            send_email(user['email'], "🌞 MedVice Morning Health Reminder", html_body)
    except Exception as e:
        print(f"Error sending morning reminders: {e}")

def send_evening_reminders():
    """Send evening reminder messages to all users"""
    try:
        conn = get_db_connection()
        users = conn.execute('SELECT * FROM users').fetchall()
        conn.close()
        
        for user in users:
            message = (
                f"Good evening {user['full_name']}! 🌙\n\n"
                f"Have you followed your health recommendations today? Check your MedVice dashboard.\n\n"
                f"Rest well!\n"
                f"- Team MedVice 💚"
            )
            
            # Send SMS
            send_sms(user['phone'], message)
            
            # Send email
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <div style="background-color: #fff; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); max-width: 600px; margin: auto;">
                    <h2 style="color: #2c3e50;">Good Evening, {user['full_name']}! 🌙</h2>
                    <p>We hope you've had a productive day.</p>
                    <p>Have you followed your health recommendations today? Visit your <a href="http://localhost:5000/dashboard">MedVice dashboard</a> to review your personalized health plan.</p>
                    <p>Rest well and take care of yourself!<br><b>MedVice Team 💚</b></p>
                </div>
            </body>
            </html>
            """
            
            send_email(user['email'], "🌙 MedVice Evening Health Check-In", html_body)
    except Exception as e:
        print(f"Error sending evening reminders: {e}")

def run_scheduler():
    """Run the scheduler in a separate thread"""
    # Schedule morning reminders at 8:00 AM
    schedule.every().day.at("08:00").do(send_morning_reminders)
    
    # Schedule evening reminders at 8:00 PM
    schedule.every().day.at("20:00").do(send_evening_reminders)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def get_ai_prediction_with_gemini(symptoms_input):
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        chat = model.start_chat()
        response = chat.send_message(
            f"""
            I have these symptoms: {symptoms_input}. 
            Based on these symptoms, please provide a structured analysis:
            1. Most likely disease or condition
            2. A brief description of this condition (2-3 sentences)
            3. List of 3-5 recommended medications (generic names preferred)
            4. List of 3-5 diet recommendations
            5. List of 3-5 workout or physical activity suggestions
            6. List of 3-5 important precautions or warning signs
            
            Format your response so it's easy to parse into sections.
            """
        )
        
        ai_response = response.text.strip()
        
        # Parse the AI response into structured data
        result = parse_ai_response(ai_response)
        return result
    except Exception as e:
        print(f"AI prediction error: {e}")
        return {
            "disease": "Unknown",
            "description": f"AI prediction failed: {e}",
            "medications": ["Consult a doctor"],
            "diets": ["Consult a doctor"],
            "workouts": ["Consult a doctor"],
            "precautions": ["Seek immediate medical attention if symptoms worsen"]
        }

def parse_ai_response(ai_text):
    # Default values
    result = {
        "disease": "Unknown",
        "description": "No description available.",
        "medications": [],
        "diets": [],
        "workouts": [],
        "precautions": []
    }
    
    # Simple parsing - this can be improved with more sophisticated methods
    lines = ai_text.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for disease name (usually at the beginning)
        if result["disease"] == "Unknown" and not line.startswith(('1.', '2.', '3.', '4.', '5.', '6.')):
            if "disease" in line.lower() or "condition" in line.lower():
                parts = line.split(":", 1)
                if len(parts) > 1:
                    result["disease"] = parts[1].strip()
            
        # Check for section headers
        if "disease" in line.lower() or "condition" in line.lower() or line.startswith("1."):
            current_section = "disease"
            parts = line.split(":", 1)
            if len(parts) > 1:
                result["disease"] = parts[1].strip()
        elif "description" in line.lower() or line.startswith("2."):
            current_section = "description"
            parts = line.split(":", 1)
            if len(parts) > 1:
                result["description"] = parts[1].strip()
        elif "medication" in line.lower() or line.startswith("3."):
            current_section = "medications"
        elif "diet" in line.lower() or line.startswith("4."):
            current_section = "diets"
        elif "workout" in line.lower() or "physical" in line.lower() or line.startswith("5."):
            current_section = "workouts"
        elif "precaution" in line.lower() or "warning" in line.lower() or line.startswith("6."):
            current_section = "precautions"
        # Process list items
        elif line.startswith(('-', '•', '*')) and current_section:
            item = line.lstrip('-•* ').strip()
            if item and current_section != "disease" and current_section != "description":
                result[current_section].append(item)
                
    # If no medications were extracted, add a default
    for key in ["medications", "diets", "workouts", "precautions"]:
        if not result[key]:
            result[key] = ["Consult a healthcare professional for specific advice"]
            
    return result


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        conn.execute("INSERT INTO users (full_name, email, phone, username, password) VALUES (?, ?, ?, ?, ?)",
                     (full_name, email, phone, username, password))
        conn.commit()
        conn.close()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('symptoms'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/symptoms', methods=['GET', 'POST'])
def symptoms():
    if request.method == 'POST':
        symptoms_input = request.form['symptoms']
        session['symptoms_input'] = symptoms_input
        return redirect(url_for('results'))
    
    # Get all valid symptoms from the training dataset for autocomplete
    try:
        training_df = pd.read_csv('datasets/Training.csv')
        all_symptoms = [col.replace('_', ' ').title() for col in training_df.columns[:-1]]
    except:
        all_symptoms = []
        
    return render_template('symptoms.html', all_symptoms=all_symptoms)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    results = conn.execute('SELECT * FROM diagnosis_results WHERE user_id = ? ORDER BY timestamp DESC', 
                          (user_id,)).fetchall()
    conn.close()
    
    return render_template('dashboard.html', results=results)

@app.route('/save_results', methods=['POST'])
def save_results():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    prediction = request.form.get('prediction')
    description = request.form.get('description')
    medications = request.form.getlist('medications')
    precautions = request.form.getlist('precautions')
    diets = request.form.getlist('diets')
    workouts = request.form.getlist('workouts')
    symptoms_input = session.get('symptoms_input', 'Not specified')

    # Save to database
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO diagnosis_results (
            user_id, prediction, description, medications, precautions, diets, workouts, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        user_id, prediction, description,
        ', '.join(medications),
        ', '.join(precautions),
        ', '.join(diets),
        ', '.join(workouts)
    ))
    conn.commit()
    
    # Get user information for notifications
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    if user:
        # Send email notification
        email_html = generate_email_html(
            user_name=user['full_name'],
            symptoms=symptoms_input,
            disease=prediction,
            description=description,
            medications=medications,
            diets=diets,
            workouts=workouts,
            precautions=precautions,
            ai_powered=False
        )
        send_email(user['email'], f"❤️-MedVice Results Saved - {prediction}", email_html)
        
        # Send SMS notification about dashboard update - split into two messages for Fast2SMS length limitations
        sms_segment_1 = (
                f"MedVice Alert for {user['full_name']}:\n"
                f"Detected: {prediction.title()}\n"
                f"Take Your Medicine On Time!-Full report emailed to you.\n"
                f"Stay safe, stay healthy! — Team MedVice "
                )
                
        send_sms(user['phone'], sms_segment_1)

    flash('Diagnosis saved to your dashboard!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/map')
def map():
    return render_template('map.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        message = request.form['message']

        # Optional: Add basic server-side validation
        if not full_name or not email or not message:
            flash('Please fill out all fields.', 'error')
            return redirect(url_for('contact'))

        # Save to database
        conn = sqlite3.connect('medvice.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO contacts (full_name, email, message) VALUES (?, ?, ?)",
                       (full_name, email, message))
        conn.commit()
        conn.close()

        flash('Your message has been sent successfully!', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html')


@app.route('/results')
def results():
    symptoms_input = session.get('symptoms_input', '')
    if not symptoms_input:
        return redirect(url_for('symptoms'))

    symptoms = [s.strip().lower().replace(' ', '_') for s in symptoms_input.split(',') if s.strip()]
    
    try:
        training_df = pd.read_csv('datasets/Training.csv')
        training_df.fillna(0, inplace=True)
        all_symptoms = [col.lower() for col in training_df.columns[:-1]]
        matched_symptoms = [s for s in symptoms if s in all_symptoms]

        # If no matched symptoms, use AI
        if not matched_symptoms:
            ai_result = get_ai_prediction_with_gemini(symptoms_input)
            
            # No SMS or email notifications here - we'll send them only when saved
            return render_template(
                'results.html',
                prediction=ai_result["disease"],
                description=ai_result["description"],
                medications=ai_result["medications"],
                diets=ai_result["diets"],
                workouts=ai_result["workouts"],
                precautions=ai_result["precautions"],
                ai_powered=True
            )

        training_df = training_df.rename(columns=lambda x: x.strip().lower())
        training_df['match_count'] = training_df[matched_symptoms].sum(axis=1)
        best_match = training_df.sort_values(by='match_count', ascending=False).iloc[0]

        # If match count is 0, use AI
        if best_match['match_count'] == 0:
            ai_result = get_ai_prediction_with_gemini(symptoms_input)
            
            # No SMS or email notifications here - we'll send them only when saved
            return render_template(
                'results.html',
                prediction=ai_result["disease"],
                description=ai_result["description"],
                medications=ai_result["medications"],
                diets=ai_result["diets"],
                workouts=ai_result["workouts"],
                precautions=ai_result["precautions"],
                ai_powered=True
            )

        predicted_disease = best_match['prognosis'].strip().lower()

        # Load other datasets
        description_df = pd.read_csv('datasets/description.csv')
        medication_df = pd.read_csv('datasets/medications.csv')
        diet_df = pd.read_csv('datasets/diets.csv')
        workout_df = pd.read_csv('datasets/workout_df.csv')
        precautions_df = pd.read_csv('datasets/precautions_df.csv')

        def get_info(df):
            match = df[df['Disease'].str.strip().str.lower() == predicted_disease]
            if match.empty:
                return ["No data available"]
            values = match.drop(columns=['Disease']).values.flatten().tolist()
            return [str(v).strip() for v in values if str(v).strip() and not str(v).isdigit()]

        desc_row = description_df[description_df['Disease'].str.strip().str.lower() == predicted_disease]
        description = desc_row['Description'].values[0] if not desc_row.empty else "Description not available."

        medications = get_info(medication_df)
        diets = get_info(diet_df)
        workouts = get_info(workout_df)
        precautions = get_info(precautions_df)

        # No SMS or email notifications here - we'll send them only when saved
        return render_template(
            'results.html',
            prediction=predicted_disease.title(),
            description=description,
            medications=medications,
            diets=diets,
            workouts=workouts,
            precautions=precautions,
            ai_powered=False
        )
    
    except Exception as e:
        # Fallback to AI in case of any error
        print(f"Error processing symptoms: {e}")
        ai_result = get_ai_prediction_with_gemini(symptoms_input)
        
        return render_template(
            'results.html',
            prediction=ai_result["disease"],
            description=ai_result["description"],
            medications=ai_result["medications"],
            diets=ai_result["diets"],
            workouts=ai_result["workouts"],
            precautions=ai_result["precautions"],
            ai_powered=True
        )

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        conn = get_db_connection()
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            full_name TEXT NOT NULL,
                            email TEXT NOT NULL,
                            phone TEXT NOT NULL,
                            username TEXT NOT NULL UNIQUE,
                            password TEXT NOT NULL
                        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS diagnosis_results (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER,
                            prediction TEXT,
                            description TEXT,
                            medications TEXT,
                            precautions TEXT,
                            diets TEXT,
                            workouts TEXT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(user_id) REFERENCES users(id)
                        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS contacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        full_name TEXT NOT NULL,
                        email TEXT NOT NULL,
                        message TEXT NOT NULL
                       )''')

        conn.commit()
        conn.close()
    
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    app.run(debug=True)