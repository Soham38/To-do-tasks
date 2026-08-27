from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime, timezone
import os
database_url = os.environ.get('DATABASE_URL', 'sqlite:///tasks.db')

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url

class Base(DeclarativeBase):
    pass
db = SQLAlchemy(model_class=Base)
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


# ----------------- MODELS ----------------- #
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    lists = relationship("SharedList", back_populates="owner", cascade="all, delete-orphan")


class SharedList(db.Model):
    __tablename__ = 'shared_lists'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(100), default="Untitled List")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=True)
    owner = relationship("User", back_populates="lists")

    tasks = relationship("TaskItem", back_populates="shared_list", cascade="all, delete-orphan",
                         order_by="TaskItem.position")


class TaskItem(db.Model):
    __tablename__ = 'tasks'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    description: Mapped[str] = mapped_column(String(250), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[str] = mapped_column(String(20), default="Normal")
    due_date: Mapped[str] = mapped_column(String(20), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    list_id: Mapped[str] = mapped_column(String(36), ForeignKey('shared_lists.id'), nullable=False)
    shared_list = relationship("SharedList", back_populates="tasks")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


with app.app_context():
    db.create_all()


# ----------------- AUTH & PAGE ROUTES ----------------- #

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please log in.', 'error')
            return redirect(url_for('login'))
        new_user = User(email=email, password_hash=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('dashboard'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    # Redirect with a query param so the client knows to clear storage
    return redirect(url_for('home') + '?logout=true')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user_lists=current_user.lists)


@app.route('/list/<list_id>')
def view_list(list_id):
    shared_list = db.session.get(SharedList, list_id)
    if not shared_list:
        return render_template('404.html'), 404

    # If the list is owned by an account, block non-owners
    if shared_list.user_id is not None:
        if not current_user.is_authenticated or current_user.id != shared_list.user_id:
            flash("This list is private. Please sign in to access it.", "error")
            return redirect(url_for('login'))

    return render_template('list.html', list_id=list_id)

# ----------------- REST API ENDPOINTS ----------------- #
@app.route('/api/lists', methods=['POST'])
def create_list():
    user_id = current_user.id if current_user.is_authenticated else None
    data = request.get_json(silent=True) or {}
    title = data.get('title', 'Untitled List')
    if isinstance(title, str):
        title = title.strip() or "Untitled List"
    else:
        title = "Untitled List"

    new_list = SharedList(title=title, user_id=user_id)
    db.session.add(new_list)
    db.session.commit()
    return jsonify({'list_id': new_list.id, 'title': new_list.title}), 201


@app.route('/api/lists/<list_id>', methods=['GET'])
def get_list(list_id):
    shared_list = db.session.get(SharedList, list_id)
    if not shared_list:
        return jsonify({'error': 'List not found'}), 404

    # Authorization Check
    if shared_list.user_id is not None:
        if not current_user.is_authenticated or current_user.id != shared_list.user_id:
            return jsonify({'error': 'Unauthorized: This is a private list.'}), 403

    tasks = [
        {
            'id': t.id,
            'description': t.description,
            'is_completed': t.is_completed,
            'priority': t.priority,
            'due_date': t.due_date,
            'position': t.position
        }
        for t in shared_list.tasks
    ]
    return jsonify({'list_id': shared_list.id, 'title': shared_list.title, 'tasks': tasks}), 200

@app.route('/api/lists/<list_id>', methods=['PATCH'])
def update_list_title(list_id):
    shared_list = db.session.get(SharedList, list_id)
    if not shared_list:
        return jsonify({'error': 'List not found'}), 404
    data = request.get_json() or {}
    if 'title' in data:
        shared_list.title = data['title'].strip() or "Untitled List"
        db.session.commit()
    return jsonify({'title': shared_list.title}), 200


@app.route('/api/lists/<list_id>', methods=['DELETE'])
def delete_list(list_id):
    shared_list = db.session.get(SharedList, list_id)
    if not shared_list:
        return jsonify({'error': 'List not found'}), 404
    db.session.delete(shared_list)
    db.session.commit()
    return '', 204


@app.route('/api/lists/<list_id>/tasks', methods=['POST'])
def add_task(list_id):
    shared_list = db.session.get(SharedList, list_id)
    if not shared_list:
        return jsonify({'error': 'List not found'}), 404
    data = request.get_json() or {}

    if 'description' not in data or not data['description'].strip():
        return jsonify({'error': 'Description is required'}), 400

    new_task = TaskItem(
        description=data['description'].strip(),
        priority=data.get('priority', 'Normal'),
        due_date=data.get('due_date') or None,
        position=len(shared_list.tasks),
        list_id=list_id
    )
    db.session.add(new_task)
    db.session.commit()
    return jsonify({
        'id': new_task.id,
        'description': new_task.description,
        'is_completed': new_task.is_completed,
        'priority': new_task.priority,
        'due_date': new_task.due_date,
        'position': new_task.position
    }), 201


@app.route('/api/tasks/<task_id>', methods=['PATCH'])
def update_task(task_id):
    task = db.session.get(TaskItem, task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    data = request.get_json() or {}

    if 'is_completed' in data:
        task.is_completed = data['is_completed']
    if 'description' in data:
        task.description = data['description']

    db.session.commit()
    return jsonify({'id': task.id, 'is_completed': task.is_completed}), 200


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = db.session.get(TaskItem, task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    db.session.delete(task)
    db.session.commit()
    return '', 204


@app.route('/api/lists/<list_id>/completed', methods=['DELETE'])
def clear_completed(list_id):
    shared_list = db.session.get(SharedList, list_id)
    if not shared_list:
        return jsonify({'error': 'List not found'}), 404
    tasks_to_delete = [t for t in shared_list.tasks if t.is_completed]
    for task in tasks_to_delete:
        db.session.delete(task)
    db.session.commit()
    return '', 204


@app.route('/api/lists/<list_id>/reorder', methods=['POST'])
def reorder_tasks(list_id):
    data = request.get_json() or {}
    order_ids = data.get('order', [])
    for idx, t_id in enumerate(order_ids):
        t = db.session.get(TaskItem, t_id)
        if t and t.list_id == list_id:
            t.position = idx
    db.session.commit()
    return '', 204


if __name__ == '__main__':
    app.run(debug=True)