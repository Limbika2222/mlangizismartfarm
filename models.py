from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class SoilTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    method = db.Column(db.String(50), nullable=False)
    ph = db.Column(db.Float, nullable=True)
    nitrogen = db.Column(db.Integer, nullable=True)
    phosphorus = db.Column(db.Integer, nullable=True)
    potassium = db.Column(db.Integer, nullable=True)
    visual_color = db.Column(db.String(50), nullable=True)
    drainage = db.Column(db.String(50), nullable=True)
    crop_growth = db.Column(db.String(50), nullable=True)
    recommendation = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('soil_tests', lazy=True))

class PlanningTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('planning_tasks', lazy=True))

    @property
    def status(self):
        """Returns status string: 'completed', 'overdue', or 'pending'."""
        if self.completed:
            return "completed"
        elif self.due_date < datetime.utcnow().date():
            return "overdue"
        else:
            return "pending"
