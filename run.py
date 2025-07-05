from flask import Flask, render_template, request, redirect, url_for, session, Response, jsonify
from models import db, User, SoilTest, PlanningTask, MaizeDiseaseDetection, Post, Comment, Reaction
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import timedelta, datetime, date
import requests
import google.generativeai as genai
import os
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np

# === App Setup ===
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = timedelta(days=30)

# === DB & Migrations ===
db.init_app(app)
migrate = Migrate(app, db)

# === Configure Gemini ===
genai.configure(api_key="YOUR_GEMINI_API_KEY")

# === Weather API Key ===
WEATHER_API_KEY = "YOUR_WEATHER_API_KEY"

# === Load Maize Disease Model ===
model = load_model('maize_disease_model.h5')
class_names = ['Blight', 'Common_Rust', 'Gray_Leaf_Spot', 'Healthy']

# === Disease Information ===
disease_info = {
    'Blight': {'description': 'Blight is a fungal disease causing leaf spots, wilting, and tissue death.', 'treatment': 'Use fungicides like mancozeb. Practice crop rotation and remove infected debris.'},
    'Common_Rust': {'description': 'Common rust causes small reddish-brown pustules on maize leaves.', 'treatment': 'Plant resistant varieties. Use fungicides like propiconazole if severe.'},
    'Gray_Leaf_Spot': {'description': 'Gray leaf spot causes rectangular gray lesions, reducing photosynthesis.', 'treatment': 'Rotate crops, use resistant varieties, and apply strobilurin fungicides if needed.'},
    'Healthy': {'description': 'No disease detected. Your maize is healthy.', 'treatment': 'Continue good agronomic practices to maintain plant health.'}
}

# =========================
# Routes
# =========================

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('index.html', username=session.get('username'), year=datetime.now().year, show_hero=True)

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

# === Community ===
@app.route('/community', methods=['GET', 'POST'])
def community():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        content = request.form.get('content')
        image_file = request.files.get('image')
        image_path = None

        if image_file and image_file.filename != '':
            upload_folder = os.path.join('static', 'community_uploads')
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, image_file.filename)
            image_file.save(filepath)
            image_path = '/' + filepath

        if content or image_path:
            post = Post(user_id=session['user_id'], content=content, image_path=image_path)
            db.session.add(post)
            db.session.commit()
        return redirect(url_for('community'))

    posts = Post.query.order_by(Post.timestamp.desc()).all()
    comments = Comment.query.all()
    reactions = Reaction.query.all()

    return render_template('community.html', posts=posts, comments=comments, reactions=reactions, username=session.get('username'))

@app.route('/comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    content = request.form.get('comment')
    if content:
        comment = Comment(post_id=post_id, user_id=session['user_id'], content=content)
        db.session.add(comment)
        db.session.commit()
    return redirect(url_for('community'))

# === React to Comment ===
@app.route('/react/comment/<int:comment_id>/<emoji>')
def react_comment(comment_id, emoji):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    existing_reaction = Reaction.query.filter_by(comment_id=comment_id, user_id=session['user_id']).first()
    if not existing_reaction:
        reaction = Reaction(comment_id=comment_id, user_id=session['user_id'], emoji=emoji)
        db.session.add(reaction)
        db.session.commit()
    return redirect(url_for('community'))

# === React to Post ===
@app.route('/react/post/<int:post_id>/<emoji>')
def react_post(post_id, emoji):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    existing_reaction = Reaction.query.filter_by(post_id=post_id, user_id=session['user_id']).first()
    if not existing_reaction:
        reaction = Reaction(post_id=post_id, user_id=session['user_id'], emoji=emoji)
        db.session.add(reaction)
        db.session.commit()
    return redirect(url_for('community'))

# === Maize Disease Detection ===
@app.route('/disease', methods=['GET', 'POST'])
def disease_detection():
    result, disease_details, image_url = None, None, None

    if request.method == 'POST':
        file = request.files.get('image')
        if file and session.get('user_id'):
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, file.filename)
            file.save(filepath)

            img = image.load_img(filepath, target_size=(150, 150))
            img_array = image.img_to_array(img) / 255.0
            img_array = np.expand_dims(img_array, axis=0)

            pred = model.predict(img_array)
            predicted_class = class_names[np.argmax(pred)]
            confidence = round(100 * np.max(pred), 2)

            result = f"{predicted_class} ({confidence}% confidence)"
            disease_details = disease_info.get(predicted_class, {})
            image_url = '/' + filepath

            detection = MaizeDiseaseDetection(user_id=session['user_id'], image_path=filepath,
                                              predicted_class=predicted_class, confidence=confidence,
                                              description=disease_details.get('description'),
                                              treatment=disease_details.get('treatment'))
            db.session.add(detection)
            db.session.commit()

    return render_template('disease.html', result=result, disease_details=disease_details, image_url=image_url)

# === Dashboard ===
@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    user_id = session['user_id']
    tests = SoilTest.query.filter_by(user_id=user_id).order_by(SoilTest.timestamp.asc()).all()
    detections = MaizeDiseaseDetection.query.filter_by(user_id=user_id).order_by(MaizeDiseaseDetection.timestamp.desc()).all()

    ph_data = [{'date': t.timestamp.strftime('%b %d'), 'value': t.ph} for t in tests if t.method == 'scientific' and t.ph is not None]
    scientific_tests = [t for t in tests if t.method == 'scientific']
    npk_data = {
        'n': round(sum([t.nitrogen for t in scientific_tests if t.nitrogen]), 2) if scientific_tests else 0,
        'p': round(sum([t.phosphorus for t in scientific_tests if t.phosphorus]), 2) if scientific_tests else 0,
        'k': round(sum([t.potassium for t in scientific_tests if t.potassium]), 2) if scientific_tests else 0
    }
    method_data = {'scientific': len(scientific_tests), 'visual': len([t for t in tests if t.method == 'visual'])}

    return render_template('dashboard.html', soil_checks=tests, ph_data=ph_data, npk_data=npk_data,
                           method_data=method_data, detections=detections, username=session.get('username'),
                           year=datetime.now().year)

# === Soil Check ===
@app.route('/soil-check', methods=['GET', 'POST'])
def soil_check():
    method = request.args.get('method', 'scientific')
    recommendation = None

    if request.method == 'POST':
        try:
            if method == 'scientific':
                ph = float(request.form['ph'])
                n = int(request.form['nitrogen'])
                p = int(request.form['phosphorus'])
                k = int(request.form['potassium'])

                if ph < 5.5:
                    recommendation = "Soil is too acidic. Add lime."
                elif n < 50:
                    recommendation = "Nitrogen is low. Add urea or compost."
                elif p < 30:
                    recommendation = "Phosphorus is low. Add DAP or manure."
                elif k < 50:
                    recommendation = "Potassium is low. Add muriate of potash."
                else:
                    recommendation = "Soil is healthy and balanced!"

                if session.get('user_id'):
                    test = SoilTest(user_id=session['user_id'], method='scientific', ph=ph,
                                    nitrogen=n, phosphorus=p, potassium=k, recommendation=recommendation)
                    db.session.add(test)
                    db.session.commit()
        except:
            recommendation = "Invalid input. Please enter valid values."

    return render_template('soil_check.html', recommendation=recommendation, method=method)

# === Planning ===
@app.route('/planning', methods=['GET', 'POST'])
def planning():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        due_date = request.form.get('due_date')
        if title and due_date:
            task = PlanningTask(user_id=session['user_id'], title=title,
                                due_date=datetime.strptime(due_date, '%Y-%m-%d'), completed=False)
            db.session.add(task)
            db.session.commit()
        return redirect(url_for('planning'))

    tasks = PlanningTask.query.filter_by(user_id=session['user_id']).order_by(PlanningTask.due_date).all()
    return render_template('planning.html', tasks=tasks, username=session.get('username'),
                           current_date=date.today(), today=date.today())

@app.route('/planning/done/<int:task_id>')
def mark_task_done(task_id):
    task = PlanningTask.query.get_or_404(task_id)
    if task.user_id != session.get('user_id'):
        return "Unauthorized", 403
    task.completed = True
    db.session.commit()
    return redirect(url_for('planning'))

@app.route('/planning/delete/<int:task_id>')
def delete_task(task_id):
    task = PlanningTask.query.get_or_404(task_id)
    if task.user_id != session.get('user_id'):
        return "Unauthorized", 403
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('planning'))

# === Weather ===
@app.route('/weather')
def weather():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    city = request.args.get('city', 'Lilongwe')
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    data = response.json()

    suggestions = []
    if "list" in data:
        for forecast in data["list"]:
            dt_txt = forecast["dt_txt"]
            weather_main = forecast["weather"][0]["main"]
            temp = forecast["main"]["temp"]

            if "rain" in weather_main.lower():
                plan = "Avoid pesticide spraying"
            elif temp > 30:
                plan = "Irrigate crops early morning or evening"
            elif temp < 20:
                plan = "Monitor crops for cold stress"
            else:
                plan = "Good day for general farm work"

            suggestions.append({"date": dt_txt, "weather": weather_main, "temp": temp, "plan": plan})

    return render_template('weather.html', suggestions=suggestions, city=city, username=session.get('username'))

# === Chat ===
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if request.method == 'POST':
        user_input = request.json.get('message')
        try:
            model = genai.GenerativeModel(model_name='gemini-1.5-flash')
            response = model.generate_content(user_input)
            return jsonify({'reply': response.text})
        except Exception as e:
            return jsonify({'reply': f"Error: {str(e)}"})
    return render_template('chat.html')

# === Auth ===
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    message = ''
    if request.method == 'POST':
        username, email, password = request.form.get('username'), request.form.get('email'), request.form.get('password')
        if not username or not email or not password:
            message = 'All fields are required.'
        elif User.query.filter_by(email=email).first():
            message = 'Email already exists.'
        else:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
    return render_template('signup.html', message=message)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        remember = request.form.get('remember') == 'on'

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'], session['username'], session.permanent = user.id, user.username, remember
            return redirect(url_for('home'))
        else:
            error = 'Invalid email or password.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# === Run ===
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # For initial dev only. Use flask db migrate/upgrade for production.
    app.run(debug=True)
