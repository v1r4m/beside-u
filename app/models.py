from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    character = db.relationship('Character', backref='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Character(db.Model):
    __tablename__ = 'characters'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    answers = db.relationship('Answer', backref='character', cascade='all, delete-orphan')


class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    day_number = db.Column(db.Integer, unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Answer(db.Model):
    __tablename__ = 'answers'

    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    question = db.relationship('Question')

    __table_args__ = (
        db.UniqueConstraint('character_id', 'question_id', name='unique_character_question'),
    )


def get_available_questions(character):
    """캐릭터 생성일 기준으로 사용 가능한 질문 반환"""
    if not character:
        return []

    days_since_creation = (date.today() - character.created_at.date()).days + 1
    return Question.query.filter(Question.day_number <= days_since_creation).order_by(Question.day_number).all()


def init_default_questions():
    """기본 질문 초기화"""
    default_questions = [
        (1, "가장 좋아하는 음식은?"),
        (2, "가장 행복했던 순간은 언제야?"),
        (3, "요즘 가장 관심있는 것은?"),
        (4, "스트레스 받을 때 어떻게 해?"),
        (5, "가장 좋아하는 계절은?"),
        (6, "어린 시절 꿈은 뭐였어?"),
        (7, "가장 소중한 사람은 누구야?"),
    ]

    for day_number, content in default_questions:
        existing = Question.query.filter_by(day_number=day_number).first()
        if not existing:
            question = Question(day_number=day_number, content=content)
            db.session.add(question)

    db.session.commit()
