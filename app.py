import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash # 用來加密密碼
from flask_mail import Mail, Message 

app = Flask(__name__)
app.secret_key = "super_secret_key"
DB_NAME = "focus_space.db"

# --- 👇 新增 Email 設定開始 ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '你的信箱@gmail.com'  
app.config['MAIL_PASSWORD'] = '填自己的密碼'      
app.config['MAIL_DEFAULT_SENDER'] = 'FocusSpace 通知 <你的信箱@gmail.com>'

mail = Mail(app) 
# --- 🔺 新增 Email 設定結束 ---



# --- 資料庫連線 ---
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # 讓我們可以用欄位名稱 (例如 user['id']) 來取值
    return conn

# --- 初始化資料庫 ---
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Users 表格 (含住戶資訊 & 管理員標記)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        floor TEXT,
        building TEXT,
        unit TEXT,
        is_admin BOOLEAN DEFAULT 0
    )
    ''')

    # 2. Rooms 表格
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        capacity INTEGER NOT NULL
    )
    ''')

    # 3. Bookings 表格 (改為紀錄 user_id)
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

    # 4. 建立預設房間
    cursor.execute('SELECT count(*) FROM rooms')
    if cursor.fetchone()[0] == 0:
        rooms = [('會議室 (A)', 8), ('重訓室 (B)', 6), ('媽媽教室 (C)', 12)]
        cursor.executemany('INSERT INTO rooms (name, capacity) VALUES (?, ?)', rooms)
    
    # 5. 建立預設管理員 (帳號: admin, 密碼: admin123)
    cursor.execute('SELECT count(*) FROM users WHERE username = "admin"')
    if cursor.fetchone()[0] == 0:
        admin_pass = generate_password_hash("admin123")
        cursor.execute('''
            INSERT INTO users (username, password_hash, is_admin) 
            VALUES (?, ?, 1)
        ''', ("admin", admin_pass))
        print("已建立管理員帳號: admin / admin123")

    conn.commit()
    conn.close()

# --- 核心邏輯：檢查時間重疊 ---
def check_overlap(cursor, room_id, start_time, end_time):
    query = '''
    SELECT count(*) FROM bookings
    WHERE room_id = ? 
    AND (start_time < ? AND end_time > ?)
    '''
    cursor.execute(query, (room_id, end_time, start_time))
    return cursor.fetchone()[0] > 0

# --- Routes (路由) ---

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login')) # 沒登入就踢去登入頁

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM rooms')
    rooms = cursor.fetchall()

    # 顯示預約列表 (包含使用者資訊)
    cursor.execute('''
        SELECT rooms.name as room_name, users.username, users.floor, users.building, users.unit,
               bookings.start_time, bookings.end_time 
        FROM bookings 
        JOIN rooms ON bookings.room_id = rooms.id
        JOIN users ON bookings.user_id = users.id
        ORDER BY bookings.start_time
    ''')
    bookings = cursor.fetchall()
    
    conn.close()
    return render_template('index.html', rooms=rooms, bookings=bookings, user=session)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # 👇 1. 新增：接收 Email 資料
        email = request.form['email'] 
        floor = request.form['floor']
        building = request.form['building']
        unit = request.form['unit']
        
        hashed_pw = generate_password_hash(password)

        conn = get_db_connection()
        try:
            # 👇 2. 修改 SQL：加入 email 欄位與問號
            conn.execute('''
                INSERT INTO users (username, password_hash, email, floor, building, unit)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, hashed_pw, email, floor, building, unit)) # 參數也要記得加 email
            
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

@app.route('/book', methods=['POST'])
def book_room():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    room_id = request.form['room_id']
    
    # 接收日期與時間
    date_part = request.form['date']
    hour_part = request.form['hour']
    minute_part = request.form['minute']
    
    start_time = f"{date_part} {hour_part}:{minute_part}"
    end_time = request.form['end_time'].replace('T', ' ')

    conn = get_db_connection()
    cursor = conn.cursor()

    if end_time <= start_time:
        flash("結束時間必須晚於開始時間", "danger") # 順便把這裡的驚嘆號也拿掉，保持風格統一
    elif check_overlap(cursor, room_id, start_time, end_time):
        flash("預約失敗：該時段已被預約", "danger")
    else:
        cursor.execute('''
            INSERT INTO bookings (room_id, user_id, start_time, end_time)
            VALUES (?, ?, ?, ?)
        ''', (room_id, session['user_id'], start_time, end_time))
        conn.commit()

        # --- 👇 新增：寄信程式碼開始 ---
        try:
            # 1. 查房間名稱
            room_name = cursor.execute('SELECT name FROM rooms WHERE id = ?', (room_id,)).fetchone()[0]
            # 2. 查使用者 Email
            user_email = cursor.execute('SELECT email FROM users WHERE id = ?', (session['user_id'],)).fetchone()[0]
            
            if user_email:
                msg = Message("預約成功通知 - FocusSpace", recipients=[user_email])
                msg.body = f"""
                親愛的住戶您好：
                您已成功預約！
                ------------------------
                🏠 會議室：{room_name}
                📅 時間：{start_time} ~ {end_time}
                ------------------------
                """
                mail.send(msg)
                print(f"📧 信件已發送給 {user_email}")
        except Exception as e:
            print(f"❌ 寄信失敗: {e}")
        # --- 🔺 寄信程式碼結束 ---

        flash("預約成功", "success")

        # --------------------

    conn.close()
    return redirect(url_for('index'))

# --- 後台管理功能 ---
@app.route('/admin/users')
def admin_users():
    # 權限檢查：只有管理員能進來
    if not session.get('is_admin'):
        flash("權限不足！", "danger")
        return redirect(url_for('index'))

    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return render_template('admin_users.html', users=users)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.execute('DELETE FROM bookings WHERE user_id = ?', (user_id,)) # 連帶刪除該用戶的預約
    conn.commit()
    conn.close()
    flash("使用者及其預約已刪除", "success")
    return redirect(url_for('admin_users'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)