# app.py - ИСПРАВЛЕННАЯ И УЛУЧШЕННАЯ ВЕРСИЯ
import os
import random
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
import json

# Инициализация приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-2024-change-in-production'
'''app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fitness.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False'''


# Конфигурация БД для деплоя
if os.environ.get('DATABASE_URL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace('postgres://', 'postgresql://', 1)
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fitness.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация расширений
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему'

# Вспомогательные функции
def safe_float(value, default=0.0):
    """Безопасное преобразование в float"""
    if value is None:
        return default
    try:
        result = float(value)
        return result if not (result != result) else default  # Проверка на NaN
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """Безопасное преобразование в int"""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

# Модели базы данных
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    weight = db.Column(db.Float, default=70.0)  # НОВОЕ: вес пользователя
    
    # Связи
    workout_sessions = db.relationship('WorkoutSession', backref='user', lazy=True, cascade='all, delete-orphan')
    goals = db.relationship('FitnessGoal', backref='user', lazy=True, cascade='all, delete-orphan')
    workout_templates = db.relationship('WorkoutTemplate', backref='user', lazy=True, cascade='all, delete-orphan')
    calorie_trackings = db.relationship('CalorieTracking', backref='user', lazy=True, cascade='all, delete-orphan')
    progression_plans = db.relationship('ProgressionPlan', backref='user', lazy=True, cascade='all, delete-orphan')
    workout_streaks = db.relationship('WorkoutStreak', backref='user', lazy=True, cascade='all, delete-orphan')
    volume_loads = db.relationship('VolumeLoadTracking', backref='user', lazy=True, cascade='all, delete-orphan')
    double_progressions = db.relationship('DoubleProgression', backref='user', lazy=True, cascade='all, delete-orphan')
    custom_exercises = db.relationship('CustomExercise', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class WorkoutSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    name = db.Column(db.String(100))
    duration_minutes = db.Column(db.Float, default=60.0)
    total_calories = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    exercises = db.relationship('WorkoutExercise', backref='session', lazy=True, cascade='all, delete-orphan')
    calorie_trackings = db.relationship('CalorieTracking', backref='workout_session', lazy=True, cascade='all, delete-orphan')
    
    def calculate_calories(self, user_weight=70.0, workout_type="strength"):
        """Улучшенный расчет калорий"""
        total_volume = 0
        for exercise in self.exercises:
            sets_data = exercise.get_sets_data()
            for set_data in sets_data:
                weight = safe_float(set_data.get('weight'), 0)
                reps = safe_int(set_data.get('reps'), 0)
                if weight > 0 and reps > 0:
                    total_volume += weight * reps
        
        duration = safe_float(self.duration_minutes, 60.0)
        if duration <= 0:
            duration = 60.0
        
        if workout_type == "strength" or total_volume > 0:
            calculator = StrengthTrainingCalculator(duration, user_weight, total_volume)
        else:
            calculator = CardioTrainingCalculator(duration, user_weight)
        
        return calculator.get_spent_calories()
    
    def calculate_volume_load(self):
        """Расчет объемной нагрузки"""
        volume_data = {}
        for exercise in self.exercises:
            sets_data = exercise.get_sets_data()
            if sets_data:
                weights = []
                reps_list = []
                volume_load = 0.0
                
                for s in sets_data:
                    weight = safe_float(s.get('weight'), 0)
                    reps = safe_int(s.get('reps'), 0)
                    
                    if weight > 0 and reps > 0:
                        weights.append(weight)
                        reps_list.append(reps)
                        volume_load += weight * reps
                
                if weights and reps_list:
                    volume_data[exercise.exercise_type] = {
                        'volume_load': volume_load,
                        'sets_count': len(weights),
                        'reps_count': sum(reps_list),
                        'max_weight': max(weights)
                    }
        return volume_data

class WorkoutExercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('workout_session.id'), nullable=False)
    exercise_type = db.Column(db.String(100), nullable=False)
    sets_data = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, default=0)
    
    def get_sets_data(self):
        try:
            return json.loads(self.sets_data) if self.sets_data else []
        except json.JSONDecodeError:
            return []
    
    def set_sets_data(self, data):
        self.sets_data = json.dumps(data, ensure_ascii=False)

class FitnessGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise_type = db.Column(db.String(100), nullable=False)
    target_weight = db.Column(db.Float, nullable=False)
    target_reps = db.Column(db.Integer, nullable=False, default=8)
    target_sets = db.Column(db.Integer, nullable=False, default=3)
    current_weight = db.Column(db.Float, default=0.0, nullable=False)
    current_reps = db.Column(db.Integer, default=0, nullable=False)
    current_sets = db.Column(db.Integer, default=0, nullable=False)
    target_date = db.Column(db.Date, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def progress_percentage(self):
        target_w = safe_float(self.target_weight, 0.0)
        current_w = safe_float(self.current_weight, 0.0)
        if target_w <= 0:
            return 0
        progress = (current_w / target_w) * 100
        return min(progress, 100)
    
    @property
    def days_remaining(self):
        if self.target_date is None:
            return 0
        remaining = (self.target_date - date.today()).days
        return max(0, remaining)  # ИСПРАВЛЕНО: не возвращаем отрицательные значения
    
    def update_progress(self):
        latest_exercise = WorkoutExercise.query.join(WorkoutSession).filter(
            WorkoutSession.user_id == self.user_id,
            WorkoutExercise.exercise_type == self.exercise_type
        ).order_by(WorkoutSession.date.desc()).first()
        
        if latest_exercise:
            sets_data = latest_exercise.get_sets_data()
            if sets_data:
                valid_weights = []
                valid_reps = []
                
                for s in sets_data:
                    weight = safe_float(s.get('weight'), 0)
                    reps = safe_int(s.get('reps'), 0)
                    if weight > 0 and reps > 0:
                        valid_weights.append(weight)
                        valid_reps.append(reps)
                
                if valid_weights and valid_reps:
                    self.current_weight = max(valid_weights)
                    self.current_reps = max(valid_reps)
                    self.current_sets = len(valid_weights)
        
        current_w = safe_float(self.current_weight, 0.0)
        current_r = safe_int(self.current_reps, 0)
        current_s = safe_int(self.current_sets, 0)
        target_w = safe_float(self.target_weight, 0.0)
        target_r = safe_int(self.target_reps, 0)
        target_s = safe_int(self.target_sets, 0)
        
        self.is_completed = (current_w >= target_w and current_r >= target_r and current_s >= target_s)

class WorkoutTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    exercises_data = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_exercises_data(self):
        try:
            return json.loads(self.exercises_data) if self.exercises_data else []
        except json.JSONDecodeError:
            return []
    
    def set_exercises_data(self, data):
        self.exercises_data = json.dumps(data, ensure_ascii=False)

class CalorieTracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    workout_session_id = db.Column(db.Integer, db.ForeignKey('workout_session.id'), nullable=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    calories_burned = db.Column(db.Float, nullable=False, default=0.0)
    workout_duration = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProgressionPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise_type = db.Column(db.String(100), nullable=False)
    current_weight = db.Column(db.Float, nullable=False, default=0.0)
    target_weight = db.Column(db.Float, nullable=False, default=0.0)
    progression_type = db.Column(db.String(20), default='linear')
    weight_increment = db.Column(db.Float, default=2.5, nullable=False)
    reps_increment = db.Column(db.Integer, default=1, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_next_weight(self, current_reps, target_reps=8):
        current_r = safe_int(current_reps, 0)
        target_r = safe_int(target_reps, 8)
        current_w = safe_float(self.current_weight, 0.0)
        increment = safe_float(self.weight_increment, 2.5)
        
        if current_r >= target_r:
            return current_w + increment
        return current_w

class WorkoutStreak(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    streak_type = db.Column(db.String(50), default='workout')
    current_streak = db.Column(db.Integer, default=0)
    longest_streak = db.Column(db.Integer, default=0)
    last_activity_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def update_streak(self):
        today = date.today()
        
        if self.last_activity_date is None:
            self.current_streak = 1
            self.last_activity_date = today
        elif self.last_activity_date == today:
            return
        elif self.last_activity_date == today - timedelta(days=1):
            self.current_streak += 1
            self.last_activity_date = today
        else:
            self.current_streak = 1
            self.last_activity_date = today
        
        # Исправление: проверяем, что longest_streak не None перед сравнением
        if self.longest_streak is None:
            self.longest_streak = 0
        
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak

class VolumeLoadTracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise_type = db.Column(db.String(100), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('workout_session.id'), nullable=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    volume_load = db.Column(db.Float, nullable=False)
    sets_count = db.Column(db.Integer, default=0)
    reps_count = db.Column(db.Integer, default=0)
    max_weight = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    workout_session = db.relationship('WorkoutSession', backref='volume_loads')

class CustomExercise(db.Model):
    """Модель пользовательских упражнений"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    muscle_group = db.Column(db.String(50), nullable=False)  # Грудь, Руки, Плечи, Ноги, Спина, Кардио
    met_value = db.Column(db.Float, default=5.0, nullable=False)  # MET коэффициент для расчета калорий
    description = db.Column(db.Text)  # Описание упражнения
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DoubleProgression(db.Model):
    """Модель двойной прогрессии"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise_type = db.Column(db.String(100), nullable=False)
    current_weight = db.Column(db.Float, nullable=False, default=0.0)
    min_reps = db.Column(db.Integer, default=8, nullable=False)
    max_reps = db.Column(db.Integer, default=12, nullable=False)
    current_reps = db.Column(db.Integer, default=8, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_increase_date = db.Column(db.Date)  # НОВОЕ: когда последний раз увеличивали
    increase_count = db.Column(db.Integer, default=0)  # НОВОЕ: счетчик увеличений
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_training_instructions(self):
        """Возвращает инструкции для текущей тренировки"""
        return {
            'exercise': self.exercise_type,
            'weight': self.current_weight,
            'target_reps': self.current_reps,
            'min_reps': self.min_reps,
            'max_reps': self.max_reps,
            'status': self.get_status(),
            'next_action': self.get_next_action(),
            'progress_percentage': self.get_progress_percentage()
        }
    
    def get_status(self):
        """Статус прогрессии"""
        if self.current_reps >= self.max_reps:
            return "ready_for_weight_increase"
        elif self.current_reps > self.min_reps:
            return "progressing"
        else:
            return "maintaining"
    
    def get_next_action(self):
        """Что делать дальше"""
        status = self.get_status()
        if status == "ready_for_weight_increase":
            return f"Увеличить вес до {self.current_weight + 2.5}кг и сбросить до {self.min_reps} повт."
        elif status == "progressing":
            return f"Продолжайте с текущим весом, старайтесь сделать {self.current_reps + 1} повт."
        else:
            return f"Сфокусируйтесь на технике, цель - {self.min_reps + 1} повт."
    
    def get_progress_percentage(self):
        """Процент прогресса в текущем диапазоне"""
        total_range = self.max_reps - self.min_reps
        current_progress = self.current_reps - self.min_reps
        return min(100, max(0, (current_progress / total_range) * 100)) if total_range > 0 else 0
    
    def check_progression(self, performed_reps):
        """Проверяет и обновляет прогрессию"""
        performed = safe_int(performed_reps, 0)
        max_r = safe_int(self.max_reps, 12)
        min_r = safe_int(self.min_reps, 8)
        current_r = safe_int(self.current_reps, min_r)
        current_w = safe_float(self.current_weight, 0.0)
        
        if performed >= max_r:
            # Увеличиваем вес и сбрасываем повторения
            self.current_weight = current_w + 2.5
            self.current_reps = min_r
            self.last_increase_date = date.today()
            self.increase_count += 1
            self.updated_at = datetime.utcnow()
            return True, "weight_increased"
        elif performed >= current_r:
            # Увеличиваем повторения
            self.current_reps = min(performed, max_r)
            self.updated_at = datetime.utcnow()
            return True, "reps_increased"
        return False, "no_progression"

# Классы для расчета калорий
class TrainingCalculator:
    M_IN_KM = 1000
    
    def __init__(self, duration_minutes, weight_kg, workout_type="strength"):
        self.duration = safe_float(duration_minutes, 60.0) / 60.0
        self.weight = safe_float(weight_kg, 70.0)
        self.workout_type = workout_type
    
    def get_spent_calories(self):
        base_met = 6.0
        base_calories = self.weight * base_met * self.duration
        return max(0, base_calories)

class StrengthTrainingCalculator(TrainingCalculator):
    def __init__(self, duration_minutes, weight_kg, total_volume=0):
        super().__init__(duration_minutes, weight_kg, "strength")
        self.total_volume = safe_float(total_volume, 0)
    
    def get_spent_calories(self):
        base_met = 6.0
        base_calories = self.weight * base_met * self.duration
        volume_calories = self.total_volume * 0.05
        return max(0, base_calories + volume_calories)

class CardioTrainingCalculator(TrainingCalculator):
    def __init__(self, duration_minutes, weight_kg, distance_km=0, speed_kmh=0):
        super().__init__(duration_minutes, weight_kg, "cardio")
        self.distance = safe_float(distance_km, 0)
        self.speed = safe_float(speed_kmh, 0)
    
    def get_spent_calories(self):
        if self.speed > 0:
            time_minutes = self.duration * 60
            calories = (18 * self.speed - 20) * self.weight / self.M_IN_KM * time_minutes
            return max(0, calories)
        else:
            base_met = 8.0
            return max(0, self.weight * base_met * self.duration)

# Login Manager
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Контекстные процессоры
@app.context_processor
def inject_today():
    return {'today': date.today()}

@app.context_processor
def inject_user_data():
    if current_user.is_authenticated:
        return {'current_user_data': current_user}
    return {'current_user_data': None}

# Вспомогательные функции
def get_progress_data(user_id):
    """Получение данных для графика прогресса"""
    progress_data = {}
    
    user_sessions = WorkoutSession.query.filter_by(user_id=user_id).order_by(WorkoutSession.date).all()
    for session in user_sessions:
        for exercise in session.exercises:
            if exercise.exercise_type not in progress_data:
                progress_data[exercise.exercise_type] = {
                    'dates': [], 
                    'weights': [],
                    'sets_data': []
                }
            
            sets_data = exercise.get_sets_data()
            if sets_data:
                valid_weights = []
                for set_data in sets_data:
                    w = safe_float(set_data.get('weight'), 0)
                    if w > 0:
                        valid_weights.append(w)
                
                if valid_weights:
                    max_weight = max(valid_weights)
                    progress_data[exercise.exercise_type]['dates'].append(session.date.isoformat())
                    progress_data[exercise.exercise_type]['weights'].append(max_weight)
                    # Сохраняем данные по подходам для расчета метрик
                    progress_data[exercise.exercise_type]['sets_data'].append(sets_data)
    
    return progress_data

def validate_exercise_data(form_data):
    """Валидация данных упражнений с подробным отчетом"""
    errors = []
    valid_exercises_count = 0
    
    # Получаем все индексы упражнений
    exercise_indices = set()
    for key in form_data.keys():
        if key.startswith('exercise_type_'):
            try:
                index = int(key.split('_')[2])
                exercise_indices.add(index)
            except:
                pass
    
    print(f"DEBUG: Найдено упражнений: {len(exercise_indices)}, индексы: {sorted(exercise_indices)}")
    
    for exercise_count in sorted(exercise_indices):
        exercise_type = form_data.get(f'exercise_type_{exercise_count}', '').strip()
        
        print(f"DEBUG: Упражнение {exercise_count}: '{exercise_type}'")
        
        if not exercise_type:
            print(f"DEBUG: Упражнение {exercise_count} пропущено (пустое)")
            continue
        
        valid_exercises_count += 1
        has_valid_sets = False
        
        # Получаем все индексы подходов для этого упражнения
        set_indices = set()
        for key in form_data.keys():
            if key.startswith(f'weight_{exercise_count}_'):
                try:
                    set_idx = int(key.split('_')[2])
                    set_indices.add(set_idx)
                except:
                    pass
        
        print(f"DEBUG: Упражнение {exercise_count} ({exercise_type}): найдено подходов: {len(set_indices)}, индексы: {sorted(set_indices)}")
        
        for set_count in sorted(set_indices):
            weight_key = f'weight_{exercise_count}_{set_count}'
            reps_key = f'reps_{exercise_count}_{set_count}'
            
            weight = form_data.get(weight_key, '').strip()
            reps = form_data.get(reps_key, '').strip()
            
            print(f"DEBUG: Подход {set_count}: вес={weight}, повторения={reps}")
            
            if weight and reps:
                try:
                    weight_val = float(weight)
                    reps_val = int(reps)
                    if weight_val > 0 and reps_val > 0:
                        has_valid_sets = True
                        print(f"DEBUG: Подход {set_count} валиден: {weight_val}кг x {reps_val}повт")
                    else:
                        error_msg = f'Вес и повторения должны быть больше 0 в подходе {set_count + 1} упражнения "{exercise_type}"'
                        errors.append(error_msg)
                        print(f"DEBUG: {error_msg}")
                except ValueError as e:
                    error_msg = f'Некорректные данные в подходе {set_count + 1} упражнения "{exercise_type}": {str(e)}'
                    errors.append(error_msg)
                    print(f"DEBUG: {error_msg}")
            else:
                print(f"DEBUG: Подход {set_count} пропущен (пустой)")
        
        if not has_valid_sets:
            error_msg = f'Упражнение "{exercise_type}" не имеет валидных подходов. Проверьте, что вес и повторения заполнены.'
            errors.append(error_msg)
            print(f"DEBUG: {error_msg}")
    
    if valid_exercises_count == 0:
        errors.append('Не добавлено ни одного упражнения с заполненным названием')
        print("DEBUG: Нет валидных упражнений")
    
    print(f"DEBUG: Итого валидных упражнений: {valid_exercises_count}, ошибок: {len(errors)}")
    return errors

# МАРШРУТЫ

# Аутентификация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        weight = request.form.get('weight', '70')  # НОВОЕ: получаем вес
        
        if not username or not email or not password:
            flash('Все поля обязательны для заполнения', 'error')
            return render_template('register.html')
        
        if len(username) < 3 or len(username) > 50:
            flash('Имя пользователя должно быть от 3 до 50 символов', 'error')
            return render_template('register.html')
        
        if '@' not in email or '.' not in email:
            flash('Введите корректный email', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Пароль должен быть не короче 6 символов', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже существует', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email уже зарегистрирован', 'error')
            return render_template('register.html')
        
        user = User(username=username, email=email, weight=safe_float(weight, 70.0))
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Регистрация успешна! Добро пожаловать!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при регистрации: {str(e)}', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверные учетные данные', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

# Основные маршруты
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

'''@app.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    recent_sessions = WorkoutSession.query.filter_by(
        user_id=current_user.id
    ).order_by(WorkoutSession.date.desc()).limit(5).all()
    
    active_goals = FitnessGoal.query.filter_by(
        user_id=current_user.id,
        is_completed=False
    ).order_by(FitnessGoal.target_date.asc()).all()
    
    for goal in active_goals:
        goal.update_progress()
    
    week_workouts_count = WorkoutSession.query.filter(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.date >= week_ago
    ).count()
    
    total_workouts = WorkoutSession.query.filter_by(user_id=current_user.id).count()
    
    progress_data = get_progress_data(current_user.id)
    
    week_calories = db.session.query(db.func.sum(CalorieTracking.calories_burned)).filter(
        CalorieTracking.user_id == current_user.id,
        CalorieTracking.date >= week_ago
    ).scalar() or 0
    
    total_calories = db.session.query(db.func.sum(CalorieTracking.calories_burned)).filter(
        CalorieTracking.user_id == current_user.id
    ).scalar() or 0
    
    active_progressions = ProgressionPlan.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    
    workout_streak = WorkoutStreak.query.filter_by(
        user_id=current_user.id,
        streak_type='workout'
    ).first()
    
    streak_days = workout_streak.current_streak if workout_streak else 0
    longest_streak = workout_streak.longest_streak if workout_streak else 0
    
    active_double_progressions = DoubleProgression.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    
    return render_template('dashboard.html',
                         recent_sessions=recent_sessions,
                         active_goals=active_goals,
                         week_workouts_count=week_workouts_count,
                         total_workouts=total_workouts,
                         progress_data=json.dumps(progress_data),
                         week_calories=round(week_calories, 1),
                         total_calories=round(total_calories, 1),
                         active_progressions=active_progressions,
                         streak_days=streak_days,
                         longest_streak=longest_streak,
                         active_double_progressions=active_double_progressions)'''


@app.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    recent_sessions = WorkoutSession.query.filter_by(
        user_id=current_user.id
    ).order_by(WorkoutSession.date.desc()).limit(5).all()
    
    active_goals = FitnessGoal.query.filter_by(
        user_id=current_user.id,
        is_completed=False
    ).order_by(FitnessGoal.target_date.asc()).all()
    
    for goal in active_goals:
        goal.update_progress()
    
    week_workouts_count = WorkoutSession.query.filter(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.date >= week_ago
    ).count()
    
    progress_data = get_progress_data(current_user.id)
    
    week_calories = db.session.query(db.func.sum(CalorieTracking.calories_burned)).filter(
        CalorieTracking.user_id == current_user.id,
        CalorieTracking.date >= week_ago
    ).scalar() or 0
    
    # Расчет средней продолжительности тренировки за неделю
    week_sessions = WorkoutSession.query.filter(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.date >= week_ago
    ).all()
    
    total_duration = sum(session.duration_minutes or 0 for session in week_sessions)
    avg_duration = total_duration / len(week_sessions) if week_sessions else 0
    
    # Подсчет тренировок по группам мышц за неделю
    muscle_group_exercises = {
        'Грудь': ['Жим лежа', 'Сведение рук в кроссовере на грудь'],
        'Руки': ['Разгибания на трицепс с канатной рукоятью в кроссовере', 'Сгибания на бицепс в рычажном тренажере'],
        'Плечи': ['Махи на плечи со свободным весом', 'Отведение плеча в блочном тренажере "reverse fly"'],
        'Ягодицы': ['Ягодичный мост в рычажном тренажере', 'Разгибание бедра стоя в кроссовере / рычажном тренажере', 'Отведение бедра сидя в сдвоенном блочном тренажере (большая ягодичная)', 'Отведение с наклоном вперед бедра сидя в сдвоенном блочном тренажере (малая и средняя ягодичные)'],
        'Ноги': ['Болгарские выпады со свободным весом / в смите', 'Приседание в Смите'],
        'Спина': ['Вертикальная тяга сидя', 'Горизонтальная тяга троссовая в блочном тренажере', 'Экстензия на наклонной скамье']
    }
    
    muscle_group_data = {}
    for muscle_group, exercises in muscle_group_exercises.items():
        count = WorkoutSession.query.join(WorkoutExercise).filter(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.date >= week_ago,
            WorkoutExercise.exercise_type.in_(exercises)
        ).distinct(WorkoutSession.id).count()
        muscle_group_data[muscle_group] = count
    
    active_progressions = ProgressionPlan.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    
    workout_streak = WorkoutStreak.query.filter_by(
        user_id=current_user.id,
        streak_type='workout'
    ).first()
    
    streak_days = workout_streak.current_streak if workout_streak else 0
    longest_streak = workout_streak.longest_streak if workout_streak else 0
    
    active_double_progressions = DoubleProgression.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    
    return render_template('dashboard.html',
                         recent_sessions=recent_sessions,
                         active_goals=active_goals,
                         week_workouts_count=week_workouts_count,
                         progress_data=json.dumps(progress_data),
                         week_calories=round(week_calories, 1),
                         active_progressions=active_progressions,
                         streak_days=streak_days,
                         longest_streak=longest_streak,
                         active_double_progressions=active_double_progressions,
                         avg_duration=avg_duration,
                         muscle_group_data=muscle_group_data)



# Добавление тренировки (с полным логированием)
@app.route('/add-workout-session', methods=['GET', 'POST'])
@login_required
def add_workout_session():
    # Получаем пользовательские упражнения
    custom_exercises = CustomExercise.query.filter_by(user_id=current_user.id).order_by(CustomExercise.muscle_group, CustomExercise.name).all()
    
    if request.method == 'POST':
        print("=" * 60)
        print("НАЧАЛО ОБРАБОТКИ ФОРМЫ ADD-WORKOUT-SESSION")
        print("=" * 60)
        
        try:
            # Валидация
            print("ШАГ 1: Валидация данных...")
            errors = validate_exercise_data(request.form)
            print(f"ШАГ 1: Результат валидации - ошибок: {len(errors)}")
            
            if errors:
                print("ШАГ 1: ЕСТЬ ОШИБКИ! Возвращаем форму")
                for error in errors:
                    flash(error, 'error')
                return render_template('add_workout_session.html')
            
            print("ШАГ 1: ✓ Валидация пройдена")
            
            # Создание сессии
            print("ШАГ 2: Создание WorkoutSession...")
            workout_date = request.form.get('date', date.today().isoformat())
            workout_name = request.form.get('workout_name', '').strip()
            
            if not workout_name:
                workout_name = f"Тренировка {datetime.strptime(workout_date, '%Y-%m-%d').strftime('%d.%m.%Y')}"
            
            print(f"ШАГ 2: Дата={workout_date}, Название={workout_name}")
            
            session = WorkoutSession(
                user_id=current_user.id,
                date=datetime.strptime(workout_date, '%Y-%m-%d').date(),
                name=workout_name
            )
            db.session.add(session)
            db.session.flush()
            print(f"ШАГ 2: ✓ Session создан с ID={session.id}")
            
            # Duration
            print("ШАГ 3: Установка продолжительности...")
            duration = request.form.get('duration_minutes', '60')
            session.duration_minutes = safe_float(duration, 60.0)
            print(f"ШАГ 3: ✓ Duration={session.duration_minutes}")
            
            # Обработка упражнений
            print("ШАГ 4: Обработка упражнений...")
            exercise_indices = set()
            for key in request.form.keys():
                if key.startswith('exercise_type_'):
                    try:
                        parts = key.split('_')
                        if len(parts) >= 3:
                            index = int(parts[2])
                            exercise_indices.add(index)
                    except (ValueError, IndexError):
                        continue
            
            print(f"ШАГ 4: Найдено индексов упражнений: {sorted(exercise_indices)}")
            
            exercises_added = 0
            exercise_order = 0
            
            for exercise_count in sorted(exercise_indices):
                exercise_type = request.form.get(f'exercise_type_{exercise_count}', '').strip()
                
                if not exercise_type:
                    print(f"ШАГ 4.{exercise_count}: Пропущено (пустое)")
                    continue
                
                print(f"ШАГ 4.{exercise_count}: Обработка '{exercise_type}'")
                
                sets_data = []
                set_indices = set()
                
                for key in request.form.keys():
                    if key.startswith(f'weight_{exercise_count}_'):
                        try:
                            parts = key.split('_')
                            if len(parts) >= 3:
                                set_idx = int(parts[2])
                                set_indices.add(set_idx)
                        except (ValueError, IndexError):
                            continue
                
                print(f"ШАГ 4.{exercise_count}: Найдено подходов: {sorted(set_indices)}")
                
                for set_count in sorted(set_indices):
                    weight = request.form.get(f'weight_{exercise_count}_{set_count}', '').strip()
                    reps = request.form.get(f'reps_{exercise_count}_{set_count}', '').strip()
                    
                    if weight and reps:
                        try:
                            w = float(weight)
                            r = int(reps)
                            if w > 0 and r > 0:
                                sets_data.append({
                                    'set_number': len(sets_data) + 1,
                                    'weight': w,
                                    'reps': r
                                })
                                print(f"ШАГ 4.{exercise_count}.{set_count}: ✓ {w}кг x {r}повт")
                        except ValueError as e:
                            print(f"ШАГ 4.{exercise_count}.{set_count}: Ошибка конвертации: {e}")
                            continue
                
                if sets_data:
                    exercise = WorkoutExercise(
                        session_id=session.id,
                        exercise_type=exercise_type,
                        order=exercise_order
                    )
                    exercise.set_sets_data(sets_data)
                    db.session.add(exercise)
                    exercises_added += 1
                    exercise_order += 1
                    print(f"ШАГ 4.{exercise_count}: ✓ Упражнение добавлено ({len(sets_data)} подходов)")
                else:
                    print(f"ШАГ 4.{exercise_count}: ✗ Нет валидных подходов")
            
            print(f"ШАГ 4: ✓ Итого упражнений добавлено: {exercises_added}")
            
            if exercises_added == 0:
                db.session.rollback()
                print("ШАГ 4: ✗ НЕТ УПРАЖНЕНИЙ! Откат")
                flash('Не добавлено ни одного упражнения с подходами', 'error')
                return render_template('add_workout_session.html')
            
            # Расчет калорий
            print("ШАГ 5: Расчет калорий...")
            user_weight = safe_float(current_user.weight, 70.0)
            print(f"ШАГ 5: Вес пользователя: {user_weight}кг")
            
            try:
                session.total_calories = session.calculate_calories(user_weight, "strength")
                print(f"ШАГ 5: ✓ Калории рассчитаны: {session.total_calories}")
            except Exception as e:
                print(f"ШАГ 5: ✗ Ошибка расчета калорий: {e}")
                session.total_calories = 200.0
            
            # Запись калорий
            print("ШАГ 6: Создание CalorieTracking...")
            calorie_tracking = CalorieTracking(
                user_id=current_user.id,
                workout_session_id=session.id,
                date=session.date,
                calories_burned=session.total_calories,
                workout_duration=session.duration_minutes
            )
            db.session.add(calorie_tracking)
            print("ШАГ 6: ✓ CalorieTracking добавлен")
            
            # Volume Load
            print("ШАГ 7: Расчет Volume Load...")
            try:
                volume_data = session.calculate_volume_load()
                for exercise_type, data in volume_data.items():
                    if data and data.get('volume_load'):
                        volume_load = VolumeLoadTracking(
                            user_id=current_user.id,
                            exercise_type=exercise_type,
                            session_id=session.id,
                            date=session.date,
                            volume_load=safe_float(data.get('volume_load'), 0),
                            sets_count=safe_int(data.get('sets_count'), 0),
                            reps_count=safe_int(data.get('reps_count'), 0),
                            max_weight=safe_float(data.get('max_weight'), 0)
                        )
                        db.session.add(volume_load)
                        print(f"ШАГ 7: ✓ Volume Load для '{exercise_type}' добавлен")
            except Exception as e:
                print(f"ШАГ 7: ⚠ Ошибка Volume Load: {e}")
            
            # Streak
            print("ШАГ 8: Обновление Streak...")
            streak = WorkoutStreak.query.filter_by(
                user_id=current_user.id,
                streak_type='workout'
            ).first()
            
            if not streak:
                streak = WorkoutStreak(user_id=current_user.id, streak_type='workout')
                db.session.add(streak)
                print("ШАГ 8: Создан новый Streak")
            
            streak.update_streak()
            print(f"ШАГ 8: ✓ Streak обновлен: {streak.current_streak} дней")
            
            # Обновление целей
            print("ШАГ 9: Обновление прогресса целей...")
            goals_updated = 0
            for goal in FitnessGoal.query.filter_by(user_id=current_user.id).all():
                try:
                    goal.update_progress()
                    goals_updated += 1
                except Exception as e:
                    print(f"ШАГ 9: ⚠ Ошибка обновления цели {goal.id}: {e}")
            print(f"ШАГ 9: ✓ Обновлено целей: {goals_updated}")
            
            # COMMIT
            print("ШАГ 10: COMMIT...")
            db.session.commit()
            print("ШАГ 10: ✓✓✓ COMMIT УСПЕШЕН ✓✓✓")
            
            # Flash message
            if streak.current_streak > 1:
                if streak.current_streak % 7 == 0:
                    flash(f'🔥 Невероятно! Цепочка из {streak.current_streak} дней! Вы настоящий чемпион!', 'success')
                elif streak.current_streak % 5 == 0:
                    flash(f'💪 Отлично! Уже {streak.current_streak} дней подряд! Продолжайте в том же духе!', 'success')
                else:
                    flash(f'Тренировка успешно добавлена! Цепочка: {streak.current_streak} дней 🔥', 'success')
            else:
                flash('Тренировка успешно добавлена!', 'success')
            
            print("ШАГ 11: РЕДИРЕКТ на dashboard")
            print("=" * 60)
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            print("=" * 60)
            print(f"✗✗✗ КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
            print("=" * 60)
            import traceback
            traceback.print_exc()
            flash(f'Ошибка при добавлении тренировки: {str(e)}', 'error')
    
    print("Возврат формы (конец функции или GET запрос)")
    return render_template('add_workout_session.html', custom_exercises=custom_exercises)

@app.route('/add-goal', methods=['GET', 'POST'])
@login_required
def add_goal():
    if request.method == 'POST':
        try:
            exercise_type = request.form['exercise_type']
            target_weight = float(request.form['target_weight'])
            target_reps = int(request.form.get('target_reps', 8))
            target_sets = int(request.form.get('target_sets', 3))
            target_date_str = request.form.get('target_date', '').strip()
            
            if not target_date_str:
                flash('Целевая дата обязательна для заполнения', 'error')
                return render_template('add_goal.html')
            
            try:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                flash('Некорректный формат даты', 'error')
                return render_template('add_goal.html')
            
            if target_date <= date.today():
                flash('Целевая дата должна быть в будущем', 'error')
                return render_template('add_goal.html')
            
            goal = FitnessGoal(
                user_id=current_user.id,
                exercise_type=exercise_type,
                target_weight=target_weight,
                target_reps=target_reps,
                target_sets=target_sets,
                target_date=target_date
            )
            
            db.session.add(goal)
            db.session.commit()
            flash('Цель успешно добавлена!', 'success')
            return redirect(url_for('dashboard'))
            
        except ValueError:
            flash('Некорректные данные в форме', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении цели: {str(e)}', 'error')
    
    return render_template('add_goal.html')

@app.route('/generate-workout', methods=['GET', 'POST'])
@login_required
def generate_workout():
    if request.method == 'POST':
        try:
            muscle_groups = request.form.getlist('muscle_groups')
            duration_str = request.form.get('duration_minutes', '60')
            duration_minutes = safe_int(duration_str, 60)
            intensity = request.form.get('intensity', 'medium')
            
            exercise_database = {
                'chest': ['Жим лежа', 'Сведение рук в кроссовере на грудь'],
                'triceps': ['Разгибания на трицепс с канатной рукоятью в кроссовере'],
                'biceps': ['Сгибания на бицепс в рычажном тренажере'],
                'legs': ['Ягодичный мост в рычажном тренажере', 'Разгибание бедра стоя в кроссовере / рычажном тренажере', 'Болгарские выпады со свободным весом / в смите', 'Отведение бедра сидя в сдвоенном блочном тренажере (большая ягодичная)', 'Отведение с наклоном вперед бедра сидя в сдвоенном блочном тренажере (малая и средняя ягодичные)', 'Приседание в Смите'],
                'shoulders': ['Махи на плечи со свободным весом', 'Отведение плеча в блочном тренажере "reverse fly"'],
                'back': ['Вертикальная тяга сидя', 'Горизонтальная тяга троссовая в блочном тренажере', 'Экстензия на наклонной скамье'],
                'forearms': []
            }
            
            selected_exercises = []
            for group in muscle_groups:
                if group in exercise_database:
                    selected_exercises.extend(exercise_database[group])
            
            if not selected_exercises:
                selected_exercises = ['Жим лежа', 'Сгибания на бицепс в рычажном тренажере', 'Горизонтальная тяга троссовая в блочном тренажере']
            
            exercises_per_workout = min(len(selected_exercises), max(3, duration_minutes // 15))
            selected_exercises = random.sample(selected_exercises, min(exercises_per_workout, len(selected_exercises)))
            
            intensity_settings = {
                'low': {'sets': 2, 'reps_range': (8, 12), 'weight_percent': 0.6},
                'medium': {'sets': 3, 'reps_range': (8, 12), 'weight_percent': 0.7},
                'high': {'sets': 4, 'reps_range': (6, 10), 'weight_percent': 0.8}
            }
            
            settings = intensity_settings.get(intensity, intensity_settings['medium'])
            
            workout_name = f"Сгенерированная тренировка - {date.today().strftime('%d.%m.%Y')}"
            exercises_data = []
            
            for exercise in selected_exercises:
                sets_data = []
                for set_num in range(settings['sets']):
                    reps = random.randint(settings['reps_range'][0], settings['reps_range'][1])
                    weight = 20.0 * settings['weight_percent']
                    sets_data.append({
                        'set_number': set_num + 1,
                        'weight': round(weight, 1),
                        'reps': reps
                    })
                
                exercises_data.append({
                    'exercise_type': exercise,
                    'sets_data': sets_data
                })
            
            session = WorkoutSession(
                user_id=current_user.id,
                date=date.today(),
                name=workout_name,
                duration_minutes=float(duration_minutes)
            )
            db.session.add(session)
            db.session.flush()
            
            for idx, ex_data in enumerate(exercises_data):
                exercise = WorkoutExercise(
                    session_id=session.id,
                    exercise_type=ex_data['exercise_type'],
                    order=idx
                )
                exercise.set_sets_data(ex_data['sets_data'])
                db.session.add(exercise)
            
            user_weight = safe_float(current_user.weight, 70.0)
            session.total_calories = session.calculate_calories(user_weight, "strength")
            
            calorie_tracking = CalorieTracking(
                user_id=current_user.id,
                workout_session_id=session.id,
                date=session.date,
                calories_burned=session.total_calories,
                workout_duration=session.duration_minutes
            )
            db.session.add(calorie_tracking)
            
            streak = WorkoutStreak.query.filter_by(
                user_id=current_user.id,
                streak_type='workout'
            ).first()
            
            if not streak:
                streak = WorkoutStreak(user_id=current_user.id, streak_type='workout')
                db.session.add(streak)
            
            streak.update_streak()
            
            db.session.commit()
            flash(f'Тренировка сгенерирована и добавлена! Цепочка: {streak.current_streak} дней 🔥', 'success')
            return redirect(url_for('dashboard'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при генерации тренировки: {str(e)}', 'error')
    
    muscle_groups_list = [
        ('chest', 'Грудь'),
        ('triceps', 'Трицепс'),
        ('biceps', 'Бицепс'),
        ('legs', 'Ноги'),
        ('shoulders', 'Плечи'),
        ('back', 'Спина'),
        ('forearms', 'Предплечья')
    ]
    
    return render_template('generate_workout.html', muscle_groups=muscle_groups_list)

# Остальные маршруты (шаблоны, цели, экспорт и т.д.)
@app.route('/workout-templates')
@login_required
def workout_templates():
    templates = WorkoutTemplate.query.filter_by(user_id=current_user.id).order_by(WorkoutTemplate.created_at.desc()).all()
    return render_template('workout_templates.html', templates=templates)

@app.route('/delete-workout-session/<int:session_id>')
@login_required
def delete_workout_session(session_id):
    session = WorkoutSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        flash('У вас нет доступа к этой тренировке', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        db.session.delete(session)
        db.session.commit()
        flash('Тренировка успешно удалена!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении тренировки: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/delete-goal/<int:goal_id>')
@login_required
def delete_goal(goal_id):
    goal = FitnessGoal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        flash('У вас нет доступа к этой цели', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        db.session.delete(goal)
        db.session.commit()
        flash('Цель успешно удалена!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении цели: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/progression-plans')
@login_required
def progression_plans():
    plans = ProgressionPlan.query.filter_by(user_id=current_user.id).order_by(ProgressionPlan.exercise_type).all()
    plans_with_meta = []
    
    for p in plans:
        target_w = safe_float(p.target_weight, 0.0)
        current_w = safe_float(p.current_weight, 0.0)
        remaining = max(0.0, target_w - current_w)
        inc = safe_float(p.weight_increment, 2.5)
        
        if inc > 0:
            eta_weeks = int(remaining // inc) + (1 if remaining % inc > 1e-9 else 0)
        else:
            eta_weeks = 0
        
        eta_weeks = max(0, eta_weeks)
        estimated_date = date.today() + timedelta(weeks=eta_weeks) if eta_weeks > 0 else date.today()
        
        plans_with_meta.append({
            'id': p.id,
            'exercise_type': p.exercise_type,
            'current_weight': current_w,
            'target_weight': target_w,
            'weight_increment': inc,
            'reps_increment': safe_int(p.reps_increment, 1),
            'is_active': p.is_active,
            'eta_weeks': eta_weeks,
            'estimated_date': estimated_date.strftime('%Y-%m-%d'),
            'remaining_weight': remaining
        })
    
    progression_charts = {}
    user_sessions = WorkoutSession.query.filter_by(user_id=current_user.id).order_by(WorkoutSession.date).all()
    for session in user_sessions:
        for exercise in session.exercises:
            ex_type = exercise.exercise_type
            sets_data = exercise.get_sets_data()
            if not sets_data:
                continue
            
            weights = [safe_float(s.get('weight'), 0) for s in sets_data if safe_float(s.get('weight'), 0) > 0]
            if not weights:
                continue
            
            max_w = max(weights)
            if ex_type not in progression_charts:
                progression_charts[ex_type] = {'dates': [], 'weights': [], 'plan_id': None}
            progression_charts[ex_type]['dates'].append(session.date.isoformat())
            progression_charts[ex_type]['weights'].append(max_w)
    
    for plan_meta in plans_with_meta:
        ex_type = plan_meta['exercise_type']
        if ex_type in progression_charts:
            progression_charts[ex_type]['plan_id'] = plan_meta['id']
    
    progression_charts_json = {}
    for plan_meta in plans_with_meta:
        ex_type = plan_meta['exercise_type']
        if ex_type in progression_charts:
            progression_charts_json[ex_type] = {
                'dates': progression_charts[ex_type]['dates'],
                'weights': progression_charts[ex_type]['weights'],
                'plan_id': plan_meta['id']
            }
        else:
            progression_charts_json[ex_type] = {
                'dates': [],
                'weights': [],
                'plan_id': plan_meta['id']
            }
    
    return render_template('progression_plans.html', 
                           plans=plans_with_meta,
                           progression_charts_json=json.dumps(progression_charts_json))


@app.route('/double-progression-list')
@login_required
def double_progression_list():
    plans = DoubleProgression.query.filter_by(user_id=current_user.id).order_by(DoubleProgression.exercise_type).all()
    return render_template('double_progression.html', plans=plans)

@app.route('/add-double-progression', methods=['GET', 'POST'])
@login_required
def add_double_progression():
    """Добавить план двойной прогрессии"""
    if request.method == 'POST':
        try:
            exercise_type = request.form['exercise_type']
            current_weight = float(request.form['current_weight'])
            min_reps = int(request.form.get('min_reps', 8))
            max_reps = int(request.form.get('max_reps', 12))
            current_reps = int(request.form.get('current_reps', min_reps))
            
            # Проверяем, есть ли уже план
            existing = DoubleProgression.query.filter_by(
                user_id=current_user.id,
                exercise_type=exercise_type,
                is_active=True
            ).first()
            
            if existing:
                existing.current_weight = current_weight
                existing.min_reps = min_reps
                existing.max_reps = max_reps
                existing.current_reps = current_reps
                existing.updated_at = datetime.utcnow()
            else:
                plan = DoubleProgression(
                    user_id=current_user.id,
                    exercise_type=exercise_type,
                    current_weight=current_weight,
                    min_reps=min_reps,
                    max_reps=max_reps,
                    current_reps=current_reps
                )
                db.session.add(plan)
            
            db.session.commit()
            flash('План двойной прогрессии успешно сохранен!', 'success')
            return redirect(url_for('double_progression_list'))
            
        except ValueError:
            flash('Некорректные данные в форме', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении плана: {str(e)}', 'error')
    
    return render_template('add_double_progression.html')

@app.route('/delete-double-progression/<int:plan_id>')
@login_required
def delete_double_progression(plan_id):
    """Удалить план двойной прогрессии"""
    plan = DoubleProgression.query.get_or_404(plan_id)
    if plan.user_id != current_user.id:
        flash('У вас нет доступа к этому плану', 'error')
        return redirect(url_for('double_progression_list'))
    
    try:
        db.session.delete(plan)
        db.session.commit()
        flash('План двойной прогрессии успешно удален!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении плана: {str(e)}', 'error')
    
    return redirect(url_for('double_progression_list'))

# ===== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЬСКИМИ УПРАЖНЕНИЯМИ =====

@app.route('/custom-exercises')
@login_required
def custom_exercises():
    """Страница управления пользовательскими упражнениями"""
    exercises = CustomExercise.query.filter_by(user_id=current_user.id).order_by(CustomExercise.muscle_group, CustomExercise.name).all()
    
    # Группируем по группам мышц
    exercises_by_group = {}
    for exercise in exercises:
        if exercise.muscle_group not in exercises_by_group:
            exercises_by_group[exercise.muscle_group] = []
        exercises_by_group[exercise.muscle_group].append(exercise)
    
    return render_template('custom_exercises.html', exercises_by_group=exercises_by_group, exercises=exercises)

@app.route('/add-custom-exercise', methods=['GET', 'POST'])
@login_required
def add_custom_exercise():
    """Добавить пользовательское упражнение"""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            muscle_group = request.form.get('muscle_group', '').strip()
            met_value = safe_float(request.form.get('met_value', '5.0'), 5.0)
            description = request.form.get('description', '').strip()
            
            if not name or not muscle_group:
                flash('Название и группа мышц обязательны для заполнения', 'error')
                return render_template('add_custom_exercise.html')
            
            # Проверяем, нет ли уже такого упражнения у пользователя
            existing = CustomExercise.query.filter_by(
                user_id=current_user.id,
                name=name
            ).first()
            
            if existing:
                flash('Упражнение с таким названием уже существует', 'error')
                return render_template('add_custom_exercise.html')
            
            exercise = CustomExercise(
                user_id=current_user.id,
                name=name,
                muscle_group=muscle_group,
                met_value=met_value,
                description=description
            )
            
            db.session.add(exercise)
            db.session.commit()
            flash('Упражнение успешно добавлено!', 'success')
            return redirect(url_for('custom_exercises'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении упражнения: {str(e)}', 'error')
    
    return render_template('add_custom_exercise.html')

@app.route('/delete-custom-exercise/<int:exercise_id>')
@login_required
def delete_custom_exercise(exercise_id):
    """Удалить пользовательское упражнение"""
    exercise = CustomExercise.query.get_or_404(exercise_id)
    if exercise.user_id != current_user.id:
        flash('У вас нет доступа к этому упражнению', 'error')
        return redirect(url_for('custom_exercises'))
    
    try:
        db.session.delete(exercise)
        db.session.commit()
        flash('Упражнение успешно удалено!', 'success')
    except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при удалении упражнения: {str(e)}', 'error')
    
    return redirect(url_for('custom_exercises'))

# ===== ГЛОССАРИЙ =====

@app.route('/glossary')
@login_required
def glossary():
    """Страница глоссария упражнений"""
    # Стандартные упражнения с описаниями
    exercises_glossary = {
        'Грудь': [
            {
                'name': 'Жим лежа',
                'description': 'Базовое упражнение для развития грудных мышц, передних дельт и трицепсов. Выполняется лежа на скамье со штангой или гантелями.',
                'technique': 'Лягте на скамью, возьмите штангу хватом шире плеч. Опустите штангу к груди, затем выжмите вверх. Держите корпус напряженным.',
                'muscles': 'Большая грудная, передние дельты, трицепсы',
                'recommendations': 'Начинайте с легкого веса для отработки техники. Используйте страховку при работе с большими весами.',
                'sources': ['https://www.bodybuilding.com/exercises/barbell-bench-press', 'https://www.muscleandfitness.com/exercises/chest-exercises/bench-press']
            },
            {
                'name': 'Сведение рук в кроссовере на грудь',
                'description': 'Изолирующее упражнение для проработки грудных мышц, особенно внутренней части.',
                'technique': 'Встаньте между блоками, возьмите рукояти. Сведите руки перед собой, слегка согнув локти. Верните в исходное положение.',
                'muscles': 'Большая грудная (внутренняя часть)',
                'recommendations': 'Контролируйте движение, не используйте инерцию. Работайте в полной амплитуде.',
                'sources': ['https://www.bodybuilding.com/exercises/cable-crossover']
            }
        ],
        'Руки': [
            {
                'name': 'Разгибания на трицепс с канатной рукоятью в кроссовере',
                'description': 'Изолирующее упражнение для развития трицепсов.',
                'technique': 'Встаньте перед блоком, возьмите канатную рукоять. Разогните руки вниз, разводя концы каната в стороны.',
                'muscles': 'Трицепсы',
                'recommendations': 'Держите локти прижатыми к корпусу. Не раскачивайтесь.',
                'sources': ['https://www.bodybuilding.com/exercises/tricep-rope-pushdown']
            },
            {
                'name': 'Сгибания на бицепс в рычажном тренажере',
                'description': 'Изолирующее упражнение для развития бицепсов.',
                'technique': 'Сядьте в тренажер, возьмите рукояти. Сгибайте руки, поднимая вес. Контролируйте движение в обе стороны.',
                'muscles': 'Бицепсы',
                'recommendations': 'Не используйте читинг. Работайте в полной амплитуде.',
                'sources': ['https://www.bodybuilding.com/exercises/bicep-curl-machine']
            }
        ],
        'Плечи': [
            {
                'name': 'Махи на плечи со свободным весом',
                'description': 'Упражнение для развития средних пучков дельтовидных мышц.',
                'technique': 'Встаньте прямо, возьмите гантели. Поднимайте руки в стороны до уровня плеч. Опустите под контролем.',
                'muscles': 'Средние дельты',
                'recommendations': 'Не поднимайте выше уровня плеч. Контролируйте движение.',
                'sources': ['https://www.bodybuilding.com/exercises/dumbbell-lateral-raise']
            }
        ],
        'Ноги': [
            {
                'name': 'Приседание в Смите',
                'description': 'Базовое упражнение для развития мышц ног и ягодиц. Безопаснее обычных приседаний благодаря фиксированной траектории.',
                'technique': 'Встаньте под гриф, расположите его на трапециях. Приседайте до параллели бедер с полом, затем встаньте.',
                'muscles': 'Квадрицепсы, ягодичные, бицепсы бедер',
                'recommendations': 'Следите за техникой. Колени не должны выходить за носки. Держите спину прямой.',
                'sources': ['https://www.bodybuilding.com/exercises/smith-machine-squat']
            }
        ],
        'Спина': [
            {
                'name': 'Вертикальная тяга сидя',
                'description': 'Упражнение для развития широчайших мышц спины и бицепсов.',
                'technique': 'Сядьте, возьмите рукоять широким хватом. Тяните к груди, сводя лопатки. Верните в исходное положение.',
                'muscles': 'Широчайшие, ромбовидные, бицепсы',
                'recommendations': 'Не отклоняйтесь сильно назад. Работайте мышцами спины, а не рук.',
                'sources': ['https://www.bodybuilding.com/exercises/wide-grip-lat-pulldown']
            }
        ]
    }
    
    return render_template('glossary.html', exercises_glossary=exercises_glossary)

@app.route('/add-progression-plan', methods=['GET', 'POST'])
@login_required
def add_progression_plan():
    if request.method == 'POST':
        try:
            exercise_type = request.form['exercise_type']
            current_weight = float(request.form['current_weight'])
            target_weight = float(request.form['target_weight'])
            weight_increment = float(request.form.get('weight_increment', 2.5))
            reps_increment = int(request.form.get('reps_increment', 1))
            
            # Проверяем, есть ли уже план для этого упражнения
            existing = ProgressionPlan.query.filter_by(
                user_id=current_user.id,
                exercise_type=exercise_type,
                is_active=True
            ).first()
            
            if existing:
                existing.current_weight = current_weight
                existing.target_weight = target_weight
                existing.weight_increment = weight_increment
                existing.reps_increment = reps_increment
                existing.updated_at = datetime.utcnow()
            else:
                plan = ProgressionPlan(
                    user_id=current_user.id,
                    exercise_type=exercise_type,
                    current_weight=current_weight,
                    target_weight=target_weight,
                    weight_increment=weight_increment,
                    reps_increment=reps_increment
                )
                db.session.add(plan)
            
            db.session.commit()
            flash('План прогрессии успешно сохранен!', 'success')
            return redirect(url_for('progression_plans'))
            
        except ValueError:
            flash('Некорректные данные в форме', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении плана: {str(e)}', 'error')
    
    return render_template('add_progression_plan.html')

@app.route('/delete-progression-plan/<int:plan_id>')
@login_required
def delete_progression_plan(plan_id):
    plan = ProgressionPlan.query.get_or_404(plan_id)
    if plan.user_id != current_user.id:
        flash('У вас нет доступа к этому плану', 'error')
        return redirect(url_for('progression_plans'))
    
    try:
        db.session.delete(plan)
        db.session.commit()
        flash('План прогрессии успешно удален!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении плана: {str(e)}', 'error')
    
    return redirect(url_for('progression_plans'))

@app.route('/add-workout-template', methods=['GET', 'POST'])
@login_required
def add_workout_template():
    if request.method == 'POST':
        try:
            template_name = request.form.get('template_name', '').strip()
            if not template_name:
                flash('Название шаблона обязательно', 'error')
                return render_template('add_workout_template.html')
            
            # Собираем упражнения из формы (аналогично добавлению тренировки)
            exercises_data = []
            exercise_indices = set()
            
            for key in request.form.keys():
                if key.startswith('exercise_type_'):
                    try:
                        parts = key.split('_')
                        if len(parts) >= 3:
                            index = int(parts[2])
                            exercise_indices.add(index)
                    except (ValueError, IndexError):
                        continue
            
            for exercise_count in sorted(exercise_indices):
                exercise_type = request.form.get(f'exercise_type_{exercise_count}', '').strip()
                if not exercise_type:
                    continue
                
                sets_data = []
                set_indices = set()
                
                for key in request.form.keys():
                    if key.startswith(f'weight_{exercise_count}_'):
                        try:
                            parts = key.split('_')
                            if len(parts) >= 3:
                                set_idx = int(parts[2])
                                set_indices.add(set_idx)
                        except (ValueError, IndexError):
                            continue
                
                for set_count in sorted(set_indices):
                    weight = request.form.get(f'weight_{exercise_count}_{set_count}', '').strip()
                    reps = request.form.get(f'reps_{exercise_count}_{set_count}', '').strip()
                    
                    if weight and reps:
                        try:
                            sets_data.append({
                                'set_number': len(sets_data) + 1,
                                'weight': float(weight),
                                'reps': int(reps)
                            })
                        except ValueError:
                            continue
                
                if sets_data:
                    exercises_data.append({
                        'exercise_type': exercise_type,
                        'sets_data': sets_data
                    })
            
            if not exercises_data:
                flash('Добавьте хотя бы одно упражнение с подходами', 'error')
                return render_template('add_workout_template.html')
            
            template = WorkoutTemplate(
                user_id=current_user.id,
                name=template_name
            )
            template.set_exercises_data(exercises_data)
            
            db.session.add(template)
            db.session.commit()
            flash('Шаблон успешно создан!', 'success')
            return redirect(url_for('workout_templates'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании шаблона: {str(e)}', 'error')
    
    return render_template('add_workout_template.html')

@app.route('/use-workout-template/<int:template_id>')
@login_required
def use_workout_template(template_id):
    template = WorkoutTemplate.query.get_or_404(template_id)
    if template.user_id != current_user.id:
        flash('У вас нет доступа к этому шаблону', 'error')
        return redirect(url_for('workout_templates'))
    
    try:
        # Создаем тренировку из шаблона
        session = WorkoutSession(
            user_id=current_user.id,
            date=date.today(),
            name=f"{template.name} - {date.today().strftime('%d.%m.%Y')}",
            duration_minutes=60.0
        )
        db.session.add(session)
        db.session.flush()
        
        exercises_data = template.get_exercises_data()
        exercises_added = 0
        
        for idx, ex_data in enumerate(exercises_data):
            if not ex_data.get('exercise_type') or not ex_data.get('sets_data'):
                continue
            
            # Валидируем данные подходов
            validated_sets_data = []
            for set_data in ex_data['sets_data']:
                weight = safe_float(set_data.get('weight'), 0)
                reps = safe_int(set_data.get('reps'), 0)
                if weight > 0 and reps > 0:
                    validated_sets_data.append({
                        'set_number': set_data.get('set_number', len(validated_sets_data) + 1),
                        'weight': weight,
                        'reps': reps
                    })
            
            if validated_sets_data:
                exercise = WorkoutExercise(
                    session_id=session.id,
                    exercise_type=ex_data['exercise_type'],
                    order=idx
                )
                exercise.set_sets_data(validated_sets_data)
                db.session.add(exercise)
                exercises_added += 1
        
        if exercises_added == 0:
            db.session.rollback()
            flash('Не удалось создать тренировку из шаблона. Шаблон не содержит валидных упражнений.', 'error')
            return redirect(url_for('workout_templates'))
        
        # Рассчитываем калории
        user_weight = safe_float(current_user.weight, 70.0)
        session.total_calories = session.calculate_calories(user_weight, "strength")
        
        # Создаем запись о калориях
        calorie_tracking = CalorieTracking(
            user_id=current_user.id,
            workout_session_id=session.id,
            date=session.date,
            calories_burned=session.total_calories,
            workout_duration=session.duration_minutes
        )
        db.session.add(calorie_tracking)
        
        # Обновляем streaks
        streak = WorkoutStreak.query.filter_by(
            user_id=current_user.id,
            streak_type='workout'
        ).first()
        
        if not streak:
            streak = WorkoutStreak(user_id=current_user.id, streak_type='workout')
            db.session.add(streak)
        
        streak.update_streak()
        
        # Обновляем прогресс целей
        for goal in FitnessGoal.query.filter_by(user_id=current_user.id).all():
            goal.update_progress()
        
        db.session.commit()
        flash(f'Тренировка создана из шаблона! Цепочка: {streak.current_streak} дней 🔥', 'success')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при использовании шаблона: {str(e)}', 'error')
        return redirect(url_for('workout_templates'))

@app.route('/delete-workout-template/<int:template_id>')
@login_required
def delete_workout_template(template_id):
    template = WorkoutTemplate.query.get_or_404(template_id)
    if template.user_id != current_user.id:
        flash('У вас нет доступа к этому шаблону', 'error')
        return redirect(url_for('workout_templates'))
    
    try:
        db.session.delete(template)
        db.session.commit()
        flash('Шаблон успешно удален!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении шаблона: {str(e)}', 'error')
    
    return redirect(url_for('workout_templates'))

@app.route('/volume-load-stats')
@login_required
def volume_load_stats():
    thirty_days_ago = date.today() - timedelta(days=30)
    volume_loads = VolumeLoadTracking.query.filter(
        VolumeLoadTracking.user_id == current_user.id,
        VolumeLoadTracking.date >= thirty_days_ago
    ).order_by(VolumeLoadTracking.date.desc()).all()
    
    exercise_stats = {}
    for vol in volume_loads:
        if vol.exercise_type not in exercise_stats:
            exercise_stats[vol.exercise_type] = {
                'total_volume': 0,
                'sessions': 0,
                'max_volume': 0,
                'dates': [],
                'volumes': []
            }
        
        exercise_stats[vol.exercise_type]['total_volume'] += vol.volume_load
        exercise_stats[vol.exercise_type]['sessions'] += 1
        exercise_stats[vol.exercise_type]['max_volume'] = max(
            exercise_stats[vol.exercise_type]['max_volume'],
            vol.volume_load
        )
        exercise_stats[vol.exercise_type]['dates'].append(vol.date.isoformat())
        exercise_stats[vol.exercise_type]['volumes'].append(float(vol.volume_load))
    
    exercise_stats_json = {}
    for exercise_type, stats in exercise_stats.items():
        exercise_stats_json[exercise_type] = {
            'total_volume': float(stats['total_volume']),
            'sessions': stats['sessions'],
            'max_volume': float(stats['max_volume']),
            'dates': stats['dates'],
            'volumes': stats['volumes']
        }
    
    return render_template('volume_load.html', 
                         exercise_stats=exercise_stats, 
                         exercise_stats_json=json.dumps(exercise_stats_json))

@app.route('/export-data')
@login_required
def export_data():
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Тип', 'Дата', 'Упражнение', 'Вес (кг)', 'Повторения', 'Подход', 'Калории', 'Продолжительность (мин)'])
    
    sessions = WorkoutSession.query.filter_by(user_id=current_user.id).order_by(WorkoutSession.date.desc()).all()
    for session in sessions:
        for exercise in session.exercises:
            sets_data = exercise.get_sets_data()
            for set_data in sets_data:
                writer.writerow([
                    'Тренировка',
                    session.date.strftime('%Y-%m-%d'),
                    exercise.exercise_type,
                    set_data.get('weight', ''),
                    set_data.get('reps', ''),
                    set_data.get('set_number', ''),
                    session.total_calories if session.total_calories else '',
                    session.duration_minutes if session.duration_minutes else ''
                ])
    
    output.seek(0)
    response = Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=fitness_data_{current_user.username}_{date.today().strftime("%Y%m%d")}.csv'}
    )
    return response


@app.route('/analytics')
@login_required
def analytics():
    """Объединенная страница аналитики и советов"""
    # Получаем данные для статистики по периодам
    today = date.today()
    periods = {
        'week': today - timedelta(days=7),
        'month': today - timedelta(days=30),
        '3months': today - timedelta(days=90)
    }
    
    period_stats = {}
    for period_name, start_date in periods.items():
        sessions = WorkoutSession.query.filter(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.date >= start_date,
            WorkoutSession.date <= today
        ).all()
        
        exercise_stats = {}
        total_volume = 0
        total_calories = 0
        
        for session in sessions:
            total_calories += session.total_calories or 0
            volume_data = session.calculate_volume_load()
            
            for exercise_type, data in volume_data.items():
                if exercise_type not in exercise_stats:
                    exercise_stats[exercise_type] = {
                        'count': 0,
                        'total_volume': 0,
                        'max_weight': 0
                    }
                
                exercise_stats[exercise_type]['count'] += 1
                exercise_stats[exercise_type]['total_volume'] += data.get('volume_load', 0)
                exercise_stats[exercise_type]['max_weight'] = max(
                    exercise_stats[exercise_type]['max_weight'],
                    data.get('max_weight', 0)
                )
                total_volume += data.get('volume_load', 0)
        
        period_stats[period_name] = {
            'total_workouts': len(sessions),
            'total_calories': total_calories,
            'total_volume': total_volume,
            'exercise_stats': exercise_stats
        }
    
    # Получаем данные для графиков прогресса
    progress_data = get_progress_data(current_user.id)
    
    # Активные цели для расчетов
    active_goals = FitnessGoal.query.filter_by(
        user_id=current_user.id,
        is_completed=False
    ).all()
    
    # Double progression планы для расчетов
    double_progressions = DoubleProgression.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    
    return render_template('analytics.html',
                         period_stats=period_stats,
                         progress_data=json.dumps(progress_data),
                         active_goals=active_goals,
                         double_progressions=double_progressions)


@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/api/calculate-progression', methods=['POST'])
@login_required
def calculate_progression():
    """Расчет времени достижения цели"""
    data = request.get_json()
    
    exercise_type = data.get('exercise_type')
    current_weight = float(data.get('current_weight', 0))
    target_weight = float(data.get('target_weight', 0))
    frequency = int(data.get('frequency', 2))
    
    # Находим историю прогресса по этому упражнению
    exercises = WorkoutExercise.query.join(WorkoutSession).filter(
        WorkoutSession.user_id == current_user.id,
        WorkoutExercise.exercise_type == exercise_type
    ).order_by(WorkoutSession.date.asc()).all()
    
    # Анализируем скорость прогресса
    weight_increases = []
    dates = []
    
    for exercise in exercises:
        session = exercise.session
        sets_data = exercise.get_sets_data()
        if sets_data:
            max_weight = max([s.get('weight', 0) for s in sets_data])
            weight_increases.append(max_weight)
            dates.append(session.date)
    
    # Рассчитываем среднюю скорость прогресса
    avg_increase_per_week = 2.5  # кг в неделю по умолчанию
    
    if len(weight_increases) > 1:
        total_increase = weight_increases[-1] - weight_increases[0]
        if total_increase > 0 and len(dates) > 1:
            weeks = (dates[-1] - dates[0]).days / 7
            if weeks > 0:
                avg_increase_per_week = total_increase / weeks
    
    # Расчет времени до цели
    weight_diff = target_weight - current_weight
    if weight_diff <= 0:
        estimated_weeks = 0
    else:
        estimated_weeks = weight_diff / (avg_increase_per_week * (frequency / 2))
    
    estimated_weeks = max(1, estimated_weeks)
    estimated_months = estimated_weeks / 4.33
    
    # Генерация данных для графика прогрессии
    progression_data = []
    current = current_weight
    week_count = 0
    
    while current < target_weight and week_count < 52:  # макс 1 год
        progression_data.append({
            'week': week_count + 1,
            'weight': round(current, 1)
        })
        current += avg_increase_per_week * (frequency / 2)
        week_count += 1
    
    # Добавляем целевую точку
    progression_data.append({
        'week': week_count + 1,
        'weight': target_weight
    })
    
    return jsonify({
        'estimated_weeks': round(estimated_weeks, 1),
        'estimated_months': round(estimated_months, 1),
        'avg_increase_per_week': round(avg_increase_per_week, 2),
        'progression_data': progression_data,
        'exercise': exercise_type
    })

@app.route('/api/calculate-calories', methods=['POST'])
@login_required
def calculate_calories():
    """Расчет расхода калорий для упражнения"""
    data = request.get_json()
    
    exercise_type = data.get('exercise_type')
    duration = int(data.get('duration', 60))
    user_weight = float(data.get('user_weight', 70))
    
    # MET значения для разных типов упражнений
    met_values = {
        'Жим лежа': 6.0,
        'Сведение рук в кроссовере на грудь': 5.0,
        'Разгибания на трицепс с канатной рукоятью в кроссовере': 4.0,
        'Сгибания на бицепс в рычажном тренажере': 4.0,
        'Махи на плечи со свободным весом': 4.5,
        'Отведение плеча в блочном тренажере "reverse fly"': 4.0,
        'Ягодичный мост в рычажном тренажере': 5.5,
        'Разгибание бедра стоя в кроссовере / рычажном тренажере': 5.0,
        'Болгарские выпады со свободным весом / в смите': 6.0,
        'Отведение бедра сидя в сдвоенном блочном тренажере (большая ягодичная)': 4.5,
        'Отведение с наклоном вперед бедра сидя в сдвоенном блочном тренажере (малая и средняя ягодичные)': 4.5,
        'Приседание в Смите': 6.5,
        'Вертикальная тяга сидя': 6.0,
        'Горизонтальная тяга троссовая в блочном тренажере': 6.0,
        'Экстензия на наклонной скамье': 5.5,
        'Ходьба на дорожке с наклоном 13-14': 8.0
    }
    
    met = met_values.get(exercise_type, 5.0)
    calories_burned = met * user_weight * (duration / 60)
    
    # Эквиваленты для сравнения
    equivalents = {
        'low': '15 минут ходьбы',
        'medium': '30 минут уборки',
        'high': '45 минут плавания'
    }
    
    equivalent_key = 'low'
    if calories_burned > 200:
        equivalent_key = 'high'
    elif calories_burned > 100:
        equivalent_key = 'medium'
    
    return jsonify({
        'calories_burned': round(calories_burned, 1),
        'met_value': met,
        'equivalent': equivalents[equivalent_key]
    })

@app.route('/api/workout-stats/<period>')
@login_required
def workout_stats_period(period):
    """Статистика тренировок за период"""
    end_date = date.today()
    
    if period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == '3months':
        start_date = end_date - timedelta(days=90)
    else:
        start_date = end_date - timedelta(days=7)
    
    sessions = WorkoutSession.query.filter(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.date >= start_date,
        WorkoutSession.date <= end_date
    ).all()
    
    exercise_stats = {}
    total_volume = 0
    total_calories = 0
    
    for session in sessions:
        total_calories += session.total_calories or 0
        volume_data = session.calculate_volume_load()
        
        for exercise_type, data in volume_data.items():
            if exercise_type not in exercise_stats:
                exercise_stats[exercise_type] = {
                    'count': 0,
                    'total_volume': 0,
                    'max_weight': 0
                }
            
            exercise_stats[exercise_type]['count'] += 1
            exercise_stats[exercise_type]['total_volume'] += data.get('volume_load', 0)
            exercise_stats[exercise_type]['max_weight'] = max(
                exercise_stats[exercise_type]['max_weight'],
                data.get('max_weight', 0)
            )
            total_volume += data.get('volume_load', 0)
    
    return jsonify({
        'period': period,
        'total_workouts': len(sessions),
        'total_calories': round(total_calories, 1),
        'total_volume': round(total_volume, 1),
        'exercise_stats': exercise_stats
    })


@app.route('/double-progression-dashboard')
@login_required
def double_progression_dashboard():
    """Дашборд двойной прогрессии"""
    plans = DoubleProgression.query.filter_by(
        user_id=current_user.id, 
        is_active=True
    ).order_by(DoubleProgression.exercise_type).all()
    
    # Получаем инструкции для каждой тренировки
    training_instructions = [plan.get_training_instructions() for plan in plans]
    
    # Получаем историю прогресса для графиков
    progression_history = {}
    for plan in plans:
        # Находим все тренировки с этим упражнением
        exercises = WorkoutExercise.query.join(WorkoutSession).filter(
            WorkoutSession.user_id == current_user.id,
            WorkoutExercise.exercise_type == plan.exercise_type
        ).order_by(WorkoutSession.date.asc()).all()
        
        dates = []
        weights = []
        reps_list = []
        
        for exercise in exercises:
            session = exercise.session
            sets_data = exercise.get_sets_data()
            if sets_data:
                # Берем средние значения по подходам
                avg_weight = sum(s.get('weight', 0) for s in sets_data) / len(sets_data)
                avg_reps = sum(s.get('reps', 0) for s in sets_data) / len(sets_data)
                
                dates.append(session.date.isoformat())
                weights.append(avg_weight)
                reps_list.append(avg_reps)
        
        progression_history[plan.id] = {
            'dates': dates,
            'weights': weights,
            'reps': reps_list
        }
    
    return render_template('double_progression_dashboard.html',
                         plans=plans,
                         training_instructions=training_instructions,
                         progression_history=json.dumps(progression_history))



@app.route('/api/weight-prediction/<exercise_type>')
@login_required
def get_weight_prediction(exercise_type):
    """Улучшенное предсказание веса для упражнения на основе истории"""
    try:
        # Ищем последние тренировки с этим упражнением
        recent_exercises = WorkoutExercise.query.join(WorkoutSession).filter(
            WorkoutSession.user_id == current_user.id,
            WorkoutExercise.exercise_type == exercise_type
        ).order_by(WorkoutSession.date.desc()).limit(5).all()
        
        if not recent_exercises:
            return jsonify({
                'suggestion': None,
                'message': 'Вы ранее не выполняли это упражнение. Начните с комфортного для вас веса.'
            })
        
        # Анализируем последнюю тренировку
        latest_exercise = recent_exercises[0]
        latest_sets = latest_exercise.get_sets_data()
        
        if not latest_sets:
            return jsonify({
                'suggestion': None,
                'message': 'В прошлый раз не было записано подходов для этого упражнения.'
            })
        
        # Собираем статистику по последней тренировке
        weights = []
        reps_list = []
        
        for set_data in latest_sets:
            weight = safe_float(set_data.get('weight'), 0)
            reps = safe_int(set_data.get('reps'), 0)
            if weight > 0 and reps > 0:
                weights.append(weight)
                reps_list.append(reps)
        
        if not weights:
            return jsonify({
                'suggestion': None,
                'message': 'Не найдено данных о весе в предыдущих подходах.'
            })
        
        max_weight = max(weights)
        min_reps = min(reps_list)
        max_reps = max(reps_list)
        avg_reps = sum(reps_list) / len(reps_list)
        
        # Улучшенная логика предсказания
        suggested_weight = max_weight
        suggestion_reason = "Повторите последний результат"
        
        # Если все повторения были больше 10 - предлагаем увеличить вес
        if min_reps >= 10:
            suggested_weight = max_weight + 2.5
            suggestion_reason = f"Отличный результат! Увеличьте вес до {suggested_weight}кг"
        # Если средние повторения 8-10 - предлагаем небольшое увеличение
        elif avg_reps >= 8:
            suggested_weight = max_weight + 1.25
            suggestion_reason = f"Хороший прогресс! Попробуйте {suggested_weight}кг"
        # Если повторения были меньше 6 - предлагаем уменьшить вес
        elif max_reps < 6:
            suggested_weight = max(20.0, max_weight - 2.5)
            suggestion_reason = f"Снизьте вес до {suggested_weight}кг для лучшей техники"
        # Если были пропуски в повторениях - оставляем тот же вес
        elif max_reps - min_reps > 4:
            suggestion_reason = f"Оставайтесь на {suggested_weight}кг, сфокусируйтесь на стабильности"
        
        # Анализ тренда по предыдущим тренировкам
        if len(recent_exercises) > 1:
            improvement_count = 0
            total_improvement = 0
            
            for i in range(1, min(4, len(recent_exercises))):
                prev_sets = recent_exercises[i].get_sets_data()
                if prev_sets:
                    prev_weights = [safe_float(s.get('weight'), 0) for s in prev_sets if safe_float(s.get('weight'), 0) > 0]
                    if prev_weights:
                        prev_max = max(prev_weights)
                        if max_weight > prev_max:
                            improvement_count += 1
                            total_improvement += (max_weight - prev_max)
            
            if improvement_count >= 2:
                suggestion_reason += " (стабильный прогресс!)"
            elif improvement_count == 0 and len(recent_exercises) >= 3:
                suggestion_reason += " (плато -可以考虑 изменить стратегию)"
        
        return jsonify({
            'suggestion': {
                'weight': round(suggested_weight, 1),
                'reps': 8,  # Стандартное значение для начала
                'reason': suggestion_reason
            },
            'last_session': {
                'date': latest_exercise.session.date.strftime('%d.%m.%Y'),
                'max_weight': max_weight,
                'reps_range': f"{min_reps}-{max_reps}",
                'sets_count': len(weights)
            }
        })
        
    except Exception as e:
        return jsonify({
            'suggestion': None,
            'message': f'Ошибка при расчете рекомендации: {str(e)}'
        })


@app.route('/api/double-progression-stats')
@login_required
def double_progression_stats():
    """API для получения статистики двойной прогрессии"""
    plans = DoubleProgression.query.filter_by(
        user_id=current_user.id, 
        is_active=True
    ).all()
    
    stats = []
    for plan in plans:
        stats.append({
            'id': plan.id,
            'exercise': plan.exercise_type,
            'instructions': plan.get_training_instructions(),
            'history': get_exercise_history(plan.exercise_type, current_user.id)
        })
    
    return jsonify(stats)

def get_exercise_history(exercise_type, user_id):
    """Получает историю упражнения"""
    exercises = WorkoutExercise.query.join(WorkoutSession).filter(
        WorkoutSession.user_id == user_id,
        WorkoutExercise.exercise_type == exercise_type
    ).order_by(WorkoutSession.date.asc()).all()
    
    history = []
    for exercise in exercises:
        session = exercise.session
        sets_data = exercise.get_sets_data()
        if sets_data:
            history.append({
                'date': session.date.isoformat(),
                'sets': len(sets_data),
                'avg_weight': sum(s.get('weight', 0) for s in sets_data) / len(sets_data),
                'avg_reps': sum(s.get('reps', 0) for s in sets_data) / len(sets_data)
            })
    
    return history

@app.route('/api/progress-data')
@login_required
def api_progress_data():
    return jsonify(get_progress_data(current_user.id))

@app.route('/update-progress/<int:goal_id>')
@login_required
def update_progress(goal_id):
    goal = FitnessGoal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        flash('У вас нет доступа к этой цели', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        goal.update_progress()
        db.session.commit()
        flash('Прогресс обновлен!', 'success')
    except Exception as e:
        flash(f'Ошибка при обновлении прогресса: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))


@app.route('/api/user-workouts')
@login_required
def get_user_workouts():
    """API для получения списка тренировок пользователя"""
    workouts = WorkoutSession.query.filter_by(
        user_id=current_user.id
    ).order_by(WorkoutSession.date.desc()).limit(20).all()
    
    workouts_data = []
    for workout in workouts:
        workouts_data.append({
            'id': workout.id,
            'date': workout.date.isoformat(),
            'name': workout.name,
            'duration_minutes': workout.duration_minutes,
            'total_calories': workout.total_calories
        })
    
    return jsonify(workouts_data)

@app.route('/api/workout-volume/<int:workout_id>')
@login_required
def get_workout_volume(workout_id):
    """API для получения объема тренировки"""
    workout = WorkoutSession.query.filter_by(
        id=workout_id,
        user_id=current_user.id
    ).first_or_404()
    
    volume_data = workout.calculate_volume_load()
    total_volume = sum(data.get('volume_load', 0) for data in volume_data.values())
    
    return jsonify({
        'total_volume': total_volume,
        'exercises': volume_data
    })


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# КРИТИЧЕСКИ ВАЖНО: Миграция базы данных
def migrate_database():
    """Добавляет новый столбец weight если его нет"""
    import sqlite3
    try:
        # Проверяем существование файла БД
        if not os.path.exists('fitness.db'):
            print("База данных не найдена, будет создана при запуске приложения")
            return
        
        conn = sqlite3.connect('fitness.db')
        cursor = conn.cursor()
        
        # Проверяем существование таблицы user
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        if not cursor.fetchone():
            print("Таблица user не найдена, будет создана при запуске приложения")
            conn.close()
            return
        
        # Проверяем существование столбца
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'weight' not in columns:
            print("Добавляем столбец 'weight' в таблицу user...")
            cursor.execute("ALTER TABLE user ADD COLUMN weight REAL DEFAULT 70.0")
            conn.commit()
            print("Столбец успешно добавлен!")
        else:
            print("Столбец 'weight' уже существует")
        
        conn.close()
    except Exception as e:
        print(f"Ошибка при миграции: {e}")

if __name__ == '__main__':
    with app.app_context():
        try:
            # Создаем таблицы если их нет
            db.create_all()
            print("База данных инициализирована")
            
            # Применяем миграцию для добавления weight
            migrate_database()
            
        except Exception as e:
            print(f"Ошибка при создании базы данных: {e}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)