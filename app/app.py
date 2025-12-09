import os
import uuid
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from models import db, User, Character, Question, Answer, get_available_questions, init_default_questions
from gpt_service import generate_character_answer

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///dev.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = '/app/uploads'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '로그인이 필요합니다.'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file):
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)
        return filename
    return None


@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.character:
            return redirect(url_for('dashboard'))
        return redirect(url_for('create_character'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not email or not password:
            flash('이메일과 비밀번호를 입력해주세요.', 'error')
            return render_template('register.html')

        if password != confirm:
            flash('비밀번호가 일치하지 않습니다.', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('비밀번호는 6자 이상이어야 합니다.', 'error')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('이미 사용중인 이메일입니다.', 'error')
            return render_template('register.html')

        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash('회원가입이 완료되었습니다!', 'success')
        return redirect(url_for('create_character'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))

        flash('이메일 또는 비밀번호가 올바르지 않습니다.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('로그아웃되었습니다.', 'success')
    return redirect(url_for('login'))


@app.route('/character/create', methods=['GET', 'POST'])
@login_required
def create_character():
    if current_user.character:
        flash('이미 캐릭터가 있습니다.', 'info')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        image = request.files.get('image')

        if not name or not description:
            flash('이름과 설명을 입력해주세요.', 'error')
            return render_template('create_character.html')

        image_path = None
        if image and image.filename:
            image_path = save_image(image)

        character = Character(
            user_id=current_user.id,
            name=name,
            description=description,
            image_path=image_path
        )
        db.session.add(character)
        db.session.commit()

        flash(f'{name} 캐릭터가 생성되었습니다!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('create_character.html')


@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.character:
        return redirect(url_for('create_character'))

    character = current_user.character
    questions = get_available_questions(character)

    answered_ids = {a.question_id for a in character.answers}

    question_cards = []
    for q in questions:
        answer = Answer.query.filter_by(character_id=character.id, question_id=q.id).first()
        question_cards.append({
            'question': q,
            'answer': answer,
            'is_answered': q.id in answered_ids
        })

    return render_template('dashboard.html', character=character, question_cards=question_cards)


@app.route('/question/<int:question_id>/answer', methods=['POST'])
@login_required
def answer_question(question_id):
    if not current_user.character:
        return redirect(url_for('create_character'))

    character = current_user.character
    question = Question.query.get_or_404(question_id)

    available = get_available_questions(character)
    if question not in available:
        flash('아직 이 질문에 답변할 수 없습니다.', 'error')
        return redirect(url_for('dashboard'))

    existing = Answer.query.filter_by(character_id=character.id, question_id=question.id).first()
    if existing:
        flash('이미 답변한 질문입니다.', 'info')
        return redirect(url_for('dashboard'))

    answer_content = generate_character_answer(
        character_name=character.name,
        character_description=character.description,
        question=question.content
    )

    answer = Answer(
        character_id=character.id,
        question_id=question.id,
        content=answer_content
    )
    db.session.add(answer)
    db.session.commit()

    flash('답변이 생성되었습니다!', 'success')
    return redirect(url_for('dashboard'))


with app.app_context():
    db.create_all()
    init_default_questions()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
