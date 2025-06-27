from flask import Flask, render_template, request, redirect, url_for, session, Response, jsonify
from models import db, User, SoilTest, PlanningTask
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta, datetime, date
from io import StringIO
import csv
import google.generativeai as genai

app = Flask(__name__)

# === Configuration ===
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = timedelta(days=30)

# === Initialize DB ===
db.init_app(app)

# === Configure Gemini ===
genai.configure(api_key="AIzaSyAMVb_p6I8nUx8VgwRPrXMl86F8RTt36xE")

# === Routes ===

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/home')
def home():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('index.html', username=session.get('username'), year=datetime.now().year)

@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    user_id = session['user_id']
    tests = SoilTest.query.filter_by(user_id=user_id).order_by(SoilTest.timestamp.asc()).all()

    ph_data = [{'date': test.timestamp.strftime('%b %d'), 'value': test.ph}
               for test in tests if test.method == 'scientific' and test.ph is not None]

    scientific_tests = [t for t in tests if t.method == 'scientific']
    n_values = [t.nitrogen for t in scientific_tests if t.nitrogen is not None]
    p_values = [t.phosphorus for t in scientific_tests if t.phosphorus is not None]
    k_values = [t.potassium for t in scientific_tests if t.potassium is not None]

    npk_data = {
        'n': round(sum(n_values) / len(n_values), 2) if n_values else 0,
        'p': round(sum(p_values) / len(p_values), 2) if p_values else 0,
        'k': round(sum(k_values) / len(k_values), 2) if k_values else 0
    }

    method_data = {
        'scientific': len([t for t in tests if t.method == 'scientific']),
        'visual': len([t for t in tests if t.method == 'visual'])
    }

    return render_template('dashboard.html',
                           soil_checks=tests,
                           ph_data=ph_data,
                           npk_data=npk_data,
                           method_data=method_data,
                           username=session.get('username'),
                           year=datetime.now().year)

@app.route('/export-csv')
def export_csv():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    user_id = session['user_id']
    tests = SoilTest.query.filter_by(user_id=user_id).order_by(SoilTest.timestamp.asc()).all()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Date', 'Method', 'pH', 'N', 'P', 'K', 'Color', 'Drainage', 'Growth', 'Recommendation'])

    for t in tests:
        writer.writerow([
            t.timestamp.strftime('%Y-%m-%d %H:%M'),
            t.method,
            t.ph or '',
            t.nitrogen or '',
            t.phosphorus or '',
            t.potassium or '',
            t.visual_color or '',
            t.drainage or '',
            t.crop_growth or '',
            t.recommendation or ''
        ])

    response = Response(si.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=soil_data.csv'
    return response

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
                                    nitrogen=n, phosphorus=p, potassium=k, visual_color=None,
                                    drainage=None, crop_growth=None, recommendation=recommendation)
                    db.session.add(test)
                    db.session.commit()

            elif method == 'visual':
                soil_color = request.form.get('soil_color')
                drainage = request.form.get('drainage')
                crop_growth = request.form.get('crop_growth')

                estimated_ph = ""
                estimated_npk = []

                if soil_color == 'red_brown':
                    estimated_ph = "likely acidic (low pH)"
                elif soil_color == 'black':
                    estimated_ph = "likely neutral or rich in organic matter"

                if crop_growth == 'yellow_leaves':
                    estimated_npk.append("Nitrogen may be low.")
                elif crop_growth == 'purple_leaves':
                    estimated_npk.append("Phosphorus may be low.")
                elif crop_growth == 'burned_edges':
                    estimated_npk.append("Potassium may be low.")
                elif crop_growth == 'healthy':
                    estimated_npk.append("Nutrient levels appear adequate.")

                if drainage == 'poor':
                    estimated_npk.append("Poor drainage may cause nutrient lock-up or root rot.")

                recommendation = f"Soil is {estimated_ph}. " + " ".join(estimated_npk)

                if session.get('user_id'):
                    test = SoilTest(user_id=session['user_id'], method='visual', ph=None,
                                    nitrogen=None, phosphorus=None, potassium=None,
                                    visual_color=soil_color, drainage=drainage,
                                    crop_growth=crop_growth, recommendation=recommendation)
                    db.session.add(test)
                    db.session.commit()
        except:
            recommendation = "Invalid input. Please enter valid values."

    return render_template('soil_check.html', recommendation=recommendation, method=method)

# === Planning Feature ===

@app.route('/planning', methods=['GET', 'POST'])
def planning():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        due_date = request.form.get('due_date')
        if title and due_date:
            task = PlanningTask(
                user_id=session['user_id'],
                title=title,
                due_date=datetime.strptime(due_date, '%Y-%m-%d'),
                completed=False
            )
            db.session.add(task)
            db.session.commit()
        return redirect(url_for('planning'))

    tasks = PlanningTask.query.filter_by(user_id=session['user_id']).order_by(PlanningTask.due_date).all()
    return render_template('planning.html', tasks=tasks, username=session.get('username'),
                           current_date=date.today(), today=date.today())  # ✅ Fix here

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

@app.route('/budget')
def budget():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('budget.html')

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

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

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
        email = request.form['email']
        password = request.form['password']
        remember = request.form.get('remember') == 'on'

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session.permanent = remember
            return redirect(url_for('home'))
        else:
            error = 'Invalid email or password.'

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        return render_template('forgot_password.html', message="If this email exists, reset instructions will be sent.")
    return render_template('forgot_password.html')

@app.route('/users')
def show_users():
    users = User.query.all()
    return "<br>".join([f"{u.id}: {u.username}, {u.email}" for u in users])

# === Run the App ===
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
