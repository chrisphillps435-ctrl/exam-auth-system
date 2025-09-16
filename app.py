from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import face_recognition
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'faces'

# Audit logging helper
def log_action(user_id, action, details=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO audit_log (user_id, action, details) VALUES (%s, %s, %s)', (user_id, action, details))
    conn.commit()
    cursor.close()
    conn.close()

# Admin dashboard route
@app.route('/admin')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        flash('Admin access required.')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    # Student count
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='student'")
    student_count = cursor.fetchone()[0]
    # Questions
    cursor.execute("SELECT * FROM exam_questions ORDER BY created_at DESC")
    questions = cursor.fetchall()
    # Students who submitted (finalized)
    cursor.execute("SELECT COUNT(DISTINCT student_id) FROM answers WHERE finalized=1")
    submitted_count = cursor.fetchone()[0]
    # Answer count per question
    cursor.execute("SELECT question_id, COUNT(*) FROM answers WHERE finalized=1 GROUP BY question_id")
    answer_counts = {row[0]: row[1] for row in cursor.fetchall()}
    # Fetch audit logs (latest 50)
    cursor.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 50")
    audit_logs = [
        {'timestamp': row[4], 'user_id': row[1], 'action': row[2], 'details': row[3]}
        for row in cursor.fetchall()
    ]
    cursor.close()
    conn.close()
    return render_template('admin_dashboard.html', student_count=student_count, questions=questions, submitted_count=submitted_count, answer_counts=answer_counts, audit_logs=audit_logs)

# Edit exam question
@app.route('/edit_question/<int:question_id>', methods=['GET', 'POST'])
def edit_question(question_id):
    if 'role' not in session or session['role'] != 'admin':
        flash('Admin access required.')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        new_text = request.form['question_text']
        cursor.execute('UPDATE exam_questions SET question_text=%s WHERE id=%s', (new_text, question_id))
        # Log admin action
        admin_id = session.get('user_id')
        log_action(admin_id, 'edit_question', f'Edited question {question_id}')
        conn.commit()
        cursor.close()
        conn.close()
        flash('Question updated!')
        return redirect(url_for('admin_dashboard'))
    cursor.execute('SELECT * FROM exam_questions WHERE id=%s', (question_id,))
    question = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('edit_question.html', question=question)

# Delete exam question
@app.route('/delete_question/<int:question_id>', methods=['POST'])
def delete_question(question_id):
    if 'role' not in session or session['role'] != 'admin':
        flash('Admin access required.')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM exam_questions WHERE id=%s', (question_id,))
    # Log admin action
    admin_id = session.get('user_id')
    log_action(admin_id, 'delete_question', f'Deleted question {question_id}')
    conn.commit()
    cursor.close()
    conn.close()
    flash('Question deleted!')
    return redirect(url_for('admin_dashboard'))

# Helper: Check if face image matches stored image (stub for now)
def verify_face(uploaded_path, stored_path):
    try:
        uploaded_image = face_recognition.load_image_file(uploaded_path)
        stored_image = face_recognition.load_image_file(stored_path)
        uploaded_encodings = face_recognition.face_encodings(uploaded_image)
        stored_encodings = face_recognition.face_encodings(stored_image)
        if not uploaded_encodings or not stored_encodings:
            return False
        result = face_recognition.compare_faces([stored_encodings[0]], uploaded_encodings[0])
        return result[0]
    except Exception as e:
        print(f"Face recognition error: {e}")
        return False

# Database config
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'exam_auth',
    'port': 3307
}

def get_db_connection():
    conn = mysql.connector.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        port=DB_CONFIG['port']
    )
    return conn

@app.route('/')
def home():
    return redirect(url_for('login'))


# Login route with role selection
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role']
        username = request.form['username']

        if role == 'admin':
            password = request.form['password']
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM users WHERE username=%s AND role=%s', (username, 'admin'))
            user = cursor.fetchone()
            if user and user['password'] == password:
                session['user_id'] = user['id']
                session['role'] = 'admin'
                cursor.close()
                conn.close()
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid admin credentials.')
                cursor.close()
                conn.close()
                return redirect(url_for('login'))
        elif role == 'student':
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM users WHERE username=%s AND role=%s', (username, 'student'))
            user = cursor.fetchone()
            if user:
                session['user_id'] = user['id']
                session['role'] = 'student'
                cursor.close()
                conn.close()
                return redirect(url_for('dashboard'))
            else:
                flash('Student not found or not registered.')
                cursor.close()
                conn.close()
                return redirect(url_for('login'))
    return render_template('login.html')


# Registration route with role selection

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Only allow access if logged in as admin
    if 'role' not in session or session['role'] != 'admin':
        flash('Only admins can register new users.')
        return redirect(url_for('login'))
    if request.method == 'POST':
        role = request.form['role']
        username = request.form['username']
        file = request.files['face_image']
        conn = get_db_connection()
        cursor = conn.cursor()
        if role == 'admin':
            password = request.form['password']
            cursor.execute('INSERT INTO users (username, password, face_image, role) VALUES (%s, %s, %s, %s)', (username, password, None, 'admin'))
        elif role == 'student':
            if file:
                filename = secure_filename(file.filename)
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(save_path)
                cursor.execute('INSERT INTO users (username, password, face_image, role) VALUES (%s, %s, %s, %s)', (username, '', save_path, 'student'))
        conn.commit()
        cursor.close()
        conn.close()
        flash('User registered successfully!')
        return redirect(url_for('register'))
    return render_template('register.html')



# Student dashboard: show exam questions and answers
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if 'role' in session and session['role'] == 'student':
        student_id = session['user_id']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Get all questions
        cursor.execute('SELECT * FROM exam_questions ORDER BY created_at DESC')
        questions = cursor.fetchall()
        # Get all answers for this student
        cursor.execute('SELECT * FROM answers WHERE student_id=%s', (student_id,))
        answers = cursor.fetchall()
        answer_map = {a['question_id']: a for a in answers}
        # Check if finalized
        finalized = any(a['finalized'] for a in answers)
        cursor.close()
        conn.close()
        return render_template('student_dashboard.html', questions=questions, answers=answer_map, finalized=finalized)
    else:
        return redirect(url_for('admin_dashboard'))

# Save or update answer for a question
@app.route('/answer/<int:question_id>', methods=['POST'])
def answer_question(question_id):
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    answer_text = request.form['answer_text']
    student_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO answers (student_id, question_id, answer_text)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE answer_text=%s, submitted_at=NOW()
    """, (student_id, question_id, answer_text, answer_text))
    conn.commit()
    flash('Answer submitted!')
    return redirect(url_for('dashboard'))  # <-- FIXED

@app.route('/finalize_answers', methods=['POST'])
def finalize_answers():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    student_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE answers SET finalized=1 WHERE student_id=%s', (student_id,))
    conn.commit()
    flash('Answers finalized!')
    return redirect(url_for('dashboard'))  # <-- FIXED

@app.route('/add_question', methods=['POST'])
def add_question():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    question_text = request.form['question_text']
    conn = get_db_connection()
    cursor = conn.cursor()
    # Check current number of questions
    cursor.execute('SELECT COUNT(*) FROM exam_questions')
    count = cursor.fetchone()[0]
    if count >= 5:
        flash('You can only add up to 5 questions.')
    else:
        cursor.execute('INSERT INTO exam_questions (question_text, created_by) VALUES (%s, %s)', (question_text, session['user_id']))
        conn.commit()
        flash('Question added!')
    cursor.close()
    conn.close()
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
