import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message 
from dotenv import load_dotenv
from datetime import datetime, timedelta # [新增] 處理時間邏輯

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev_key') 
DB_NAME = "focus_space.db"

# --- Email 設定 ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = f"FocusSpace 通知 <{os.getenv('MAIL_USERNAME')}>"

mail = Mail(app)

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # [修正] Users 表格補上 email 欄位
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        email TEXT, 
        floor TEXT,
        building TEXT,
        unit TEXT,
        is_admin BOOLEAN DEFAULT 0
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        capacity INTEGER NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        FOREIGN KEY (room_id) REFERENCES rooms (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    cursor.execute('SELECT count(*) FROM rooms')
    if cursor.fetchone()[0] == 0:
        rooms = [('會議室 (A)', 8), ('重訓室 (B)', 6), ('媽媽教室 (C)', 12)]
        cursor.executemany('INSERT INTO rooms (name, capacity) VALUES (?, ?)', rooms)
    
    conn.commit()
    conn.close()

def check_overlap(cursor, room_id, start_time, end_time):
    query = '''
    SELECT count(*) FROM bookings
    WHERE room_id = ? 
    AND (start_time < ? AND end_time > ?)
    '''
    cursor.execute(query, (room_id, end_time, start_time))
    return cursor.fetchone()[0] > 0

# --- Routes ---

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM rooms')
    rooms = cursor.fetchall()

    # [優化] 自動釋放時段：只顯示 end_time 大於現在時間的紀錄
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    cursor.execute('''
        SELECT rooms.name as room_name, users.username, users.floor, users.building, users.unit,
               bookings.start_time, bookings.end_time 
        FROM bookings 
        JOIN rooms ON bookings.room_id = rooms.id
        JOIN users ON bookings.user_id = users.id
        WHERE bookings.end_time > ?
        ORDER BY bookings.start_time
    ''', (now_str,))
    bookings = cursor.fetchall()
    
    conn.close()
    return render_template('index.html', rooms=rooms, bookings=bookings, user=session)

# [新增] API 路由：提供給 FullCalendar 顯示
@app.route('/api/bookings')
def get_bookings_api():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT rooms.name || ' - ' || users.username as title, 
               bookings.start_time as start, 
               bookings.end_time as end 
        FROM bookings
        JOIN rooms ON bookings.room_id = rooms.id
        JOIN users ON bookings.user_id = users.id
    ''')
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

# --- 補回登入、註冊與登出功能 ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email'] 
        floor = request.form['floor']
        building = request.form['building']
        unit = request.form['unit']
        
        hashed_pw = generate_password_hash(password)

        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO users (username, password_hash, email, floor, building, unit)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, hashed_pw, email, floor, building, unit))
            conn.commit()
            flash("註冊成功，請登入！", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("帳號已存在！", "danger")
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            return redirect(url_for('index'))
        else:
            flash("帳號或密碼錯誤", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/users')
def admin_users():
    if not session.get('is_admin'):
        flash("權限不足！", "danger")
        return redirect(url_for('index'))

    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return render_template('admin_users.html', users=users)


@app.route('/book', methods=['POST'])
def book_room():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    room_id = request.form['room_id']
    date_part = request.form['date']
    hour_part = request.form['hour']
    minute_part = request.form['minute']
    
    start_time_str = f"{date_part} {hour_part}:{minute_part}"
    end_time_str = request.form['end_time'].replace('T', ' ')

    # [新增] 時數限制邏輯
    try:
        fmt = '%Y-%m-%d %H:%M'
        start_dt = datetime.strptime(start_time_str, fmt)
        end_dt = datetime.strptime(end_time_str, fmt)
        duration = end_dt - start_dt
        now = datetime.now()

        if end_dt <= start_dt:
            flash("結束時間必須晚於開始時間", "danger")
            return redirect(url_for('index'))
        
        if start_dt < now:
            flash("不能預約過去的時間", "danger")
            return redirect(url_for('index'))

        if duration > timedelta(hours=4):
            flash("預約失敗：單次預約不得超過 4 小時", "danger")
            return redirect(url_for('index'))
            
    except ValueError:
        flash("時間格式錯誤", "danger")
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if check_overlap(cursor, room_id, start_time_str, end_time_str):
        flash("預約失敗：該時段已被預約", "danger")
    else:
        cursor.execute('''
            INSERT INTO bookings (room_id, user_id, start_time, end_time)
            VALUES (?, ?, ?, ?)
        ''', (room_id, session['user_id'], start_time_str, end_time_str))
        conn.commit()

        # 寄信邏輯 (維持不變)
        try:
            room_name = cursor.execute('SELECT name FROM rooms WHERE id = ?', (room_id,)).fetchone()[0]
            user_email = cursor.execute('SELECT email FROM users WHERE id = ?', (session['user_id'],)).fetchone()[0]
            if user_email:
                msg = Message("預約成功通知 - FocusSpace", recipients=[user_email])
                msg.body = f"親愛的住戶您好：\n您已成功預約 {room_name}！\n時間：{start_time_str} ~ {end_time_str}"
                mail.send(msg)
        except Exception as e:
            print(f"❌ 寄信失敗: {e}")

        flash("預約成功", "success")

    conn.close()
    return redirect(url_for('index'))

# ... 其他路由 (register, login, logout, admin_users) 保持原樣 ...