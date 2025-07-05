from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ================================
# User Model
# ================================
class User(db.Model):
    """Stores user authentication and profile data."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # Relationships
    soil_tests = db.relationship('SoilTest', backref='user', lazy=True)
    planning_tasks = db.relationship('PlanningTask', backref='user', lazy=True)
    disease_detections = db.relationship('MaizeDiseaseDetection', backref='user', lazy=True)
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    reactions = db.relationship('Reaction', backref='user', lazy=True)

# ================================
# Soil Test Model
# ================================
class SoilTest(db.Model):
    """Stores soil test results for users."""
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

# ================================
# Planning Task Model
# ================================
class PlanningTask(db.Model):
    """Stores planning tasks for farm management."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, default=False)

    @property
    def status(self):
        """Returns status string: 'completed', 'overdue', or 'pending'."""
        if self.completed:
            return "completed"
        elif self.due_date < datetime.utcnow().date():
            return "overdue"
        else:
            return "pending"

# ================================
# Maize Disease Detection Model
# ================================
class MaizeDiseaseDetection(db.Model):
    """Stores disease detection results for maize images."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_path = db.Column(db.String(300), nullable=False)
    predicted_class = db.Column(db.String(100), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    treatment = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ================================
# Community Models
# ================================
class Post(db.Model):
    """Community posts by users."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(300), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    comments = db.relationship('Comment', backref='post', lazy=True)
    reactions = db.relationship('Reaction', backref='post', lazy=True)

class Comment(db.Model):
    """Comments on posts."""
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    reactions = db.relationship('Reaction', backref='comment', lazy=True)

class Reaction(db.Model):
    """Reactions to posts or comments."""
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)  # e.g. 👍, ❤️, 😂
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
