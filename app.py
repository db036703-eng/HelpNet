from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "helpnet_secret_key"
socketio = SocketIO(app, cors_allowed_origins="*")
app.secret_key = "helpnet_secret_key"

app.config["UPLOAD_FOLDER"] = "static/uploads"

if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])


def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_name TEXT,
            item_type TEXT,
            quantity TEXT,
            location TEXT,
            description TEXT,
            urgency TEXT,
            pickup_date TEXT,
            photo TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ngo_name TEXT,
            item_type TEXT,
            quantity TEXT,
            location TEXT,
            urgency TEXT,
            description TEXT,
            status TEXT DEFAULT 'Open'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            content TEXT,
            timestamp TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            is_read INTEGER DEFAULT 0,
            timestamp TEXT,
            related_user_id INTEGER
        )
    """)

    # Attempt to alter donations table to add status column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE donations ADD COLUMN status TEXT DEFAULT 'Available'")
    except sqlite3.OperationalError:
        pass # Column might already exist

    conn.commit()
    conn.close()

init_db()



@app.route("/")
def home():
    return redirect(url_for("login"))



@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE name=?", (name,))
        if cursor.fetchone():
            return "Username already exists! Please choose another name."

        try:
            cursor.execute(
                "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                (name,email,password,role)
            )
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except:
            return "Email already exists!"

    return render_template("register.html")



@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["user_name"] = user[1]
            session["role"] = user[4]
            return redirect(url_for("dashboard"))
        else:
            return "Invalid credentials!"

    return render_template("login.html")



@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Get real stats
    cursor.execute("SELECT COUNT(*) FROM donations")
    total_donations = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM requests WHERE status='Fulfilled'")
    requests_fulfilled = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(quantity) FROM donations")
    quantity_sum = cursor.fetchone()[0]
    total_items = int(quantity_sum) if quantity_sum else 0

    # Get recent activities (last 3 items total)
    cursor.execute("""
        SELECT 'donation' as type, donor_name as user, item_type as item, id
        FROM donations
        ORDER BY id DESC LIMIT 3
    """)
    recent_donations = cursor.fetchall()
    
    cursor.execute("""
        SELECT 'request' as type, ngo_name as user, item_type as item, id
        FROM requests
        ORDER BY id DESC LIMIT 3
    """)
    recent_requests = cursor.fetchall()

    conn.close()

    # Combine and sort activities (mocking timeline by ID descending)
    activities = sorted(recent_donations + recent_requests, key=lambda x: x[3], reverse=True)[:3]

    return render_template("dashboard.html",
                           name=session["user_name"],
                           role=session["role"],
                           total_donations=total_donations,
                           requests_fulfilled=requests_fulfilled,
                           total_items=total_items,
                           activities=activities)



@app.route("/donate", methods=["GET","POST"])
def donate():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        item = request.form["item"]
        quantity = request.form["quantity"]
        location = request.form["location"]
        description = request.form["description"]
        urgency = request.form.get("urgency")
        pickup_date = request.form.get("pickup_date")

        photo_file = request.files.get("photo")
        filename = ""

        if photo_file and photo_file.filename != "":
            filename = secure_filename(photo_file.filename)
            photo_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO donations 
        (donor_name,item_type,quantity,location,description,urgency,pickup_date,photo)
        VALUES (?,?,?,?,?,?,?,?)
        """,(session["user_name"],item,quantity,location,description,urgency,pickup_date,filename))

        conn.commit()

        socketio.emit('new_activity', {
            'type': 'donation',
            'user': session["user_name"],
            'item': item,
            'timestamp': datetime.now().isoformat()
        })

        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("donate.html")



@app.route("/donation-history")
def donation_history():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM donations WHERE donor_name=?", (session["user_name"],))
    donations = cursor.fetchall()

    conn.close()

    return render_template("donation_history.html", donations=donations)



@app.route("/view-donations")
def view_donations():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM donations")
    donations = cursor.fetchall()

    conn.close()

    return render_template("view_donations.html", donations=donations)



@app.route("/create-request", methods=["GET","POST"])
def create_request():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "NGO":
        return "Access denied"

    if request.method == "POST":

        item = request.form["item"]
        quantity = request.form["quantity"]
        location = request.form["location"]
        urgency = request.form["urgency"]
        description = request.form["description"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO requests 
        (ngo_name,item_type,quantity,location,urgency,description)
        VALUES (?,?,?,?,?,?)
        """,(session["user_name"],item,quantity,location,urgency,description))

        conn.commit()

        socketio.emit('new_activity', {
            'type': 'request',
            'user': session["user_name"],
            'item': item,
            'timestamp': datetime.now().isoformat()
        })

        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("create_request.html")



@app.route("/view-requests")
def view_requests():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM requests WHERE status='Open'")
    requests_data = cursor.fetchall()

    conn.close()

    return render_template("view_requests.html", requests=requests_data)


@app.route("/claim-donation/<int:donation_id>", methods=["POST"])
def claim_donation(donation_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "NGO":
        return "Access denied. Only NGOs can claim donations."

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Get the donation to find out who the donor is
    cursor.execute("SELECT donor_name, item_type FROM donations WHERE id=?", (donation_id,))
    res = cursor.fetchone()

    # Update status to Claimed
    cursor.execute("UPDATE donations SET status='Claimed' WHERE id=?", (donation_id,))
    conn.commit()

    if res:
        donor_name = res[0]
        item_type = res[1]
        msg = f"{session['user_name']} claimed your donation: {item_type}"
        timestamp = datetime.now().isoformat()
        cursor.execute("INSERT INTO notifications (user_name, message, timestamp) VALUES (?, ?, ?)", (donor_name, msg, timestamp))
        conn.commit()
        # Emit notification to the donor's global room
        socketio.emit('new_notification', {'message': msg, 'timestamp': timestamp}, to=f"global_{donor_name}")

    conn.close()

    # Broadcast status change for inventory view
    socketio.emit('donation_status_update', {'donation_id': donation_id, 'status': 'Claimed'})

    return redirect(url_for("dashboard"))


@app.route("/fulfill-request/<int:request_id>", methods=["POST"])
def fulfill_request(request_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "Donor":
        return "Access denied. Only Donors can fulfill requests."

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE requests SET status='Fulfilled' WHERE id=?", (request_id,))
    
    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))

# ------------------------
# NOTIFICATIONS & CHAT SYSTEM API & SOCKETS
# ------------------------
@app.route("/api/notifications")
def get_notifications():
    if "user_id" not in session:
        return jsonify([])
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, message, timestamp, is_read, related_user_id 
        FROM notifications 
        WHERE user_id=? 
        ORDER BY id DESC LIMIT 20
    """, (session["user_id"],))
    results = cursor.fetchall()
    conn.close()
    
    return jsonify([{"id":r[0], "message":r[1], "timestamp":r[2], "is_read":r[3], "related_user":r[4]} for r in results])

@app.route("/api/notifications/read", methods=["POST"])
def mark_notifications_read():
    if "user_id" not in session:
        return jsonify({"status": "error"})
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (session["user_id"],))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "ok"})

@app.route("/chat/resolve/<username>")
def chat_resolve(username):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE name=?", (username,))
    target = cursor.fetchone()
    conn.close()
    if target:
        if "user_id" in session and target[0] == session["user_id"]:
            return redirect(url_for('chat'))
        return redirect(url_for('chat_user', user_id=target[0]))
    return redirect(url_for('chat'))

@app.route("/chat")
def chat():
    if "user_id" not in session:
        return redirect(url_for("login"))
        
    me_id = session["user_id"]
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Get all distinct users I have chatted with
    cursor.execute("""
        SELECT DISTINCT u.id, u.name, u.role
        FROM users u 
        JOIN messages m ON (u.id = m.receiver_id OR u.id = m.sender_id)
        WHERE (m.sender_id = ? OR m.receiver_id = ?) AND u.id != ?
    """, (me_id, me_id, me_id))
    conversations_raw = cursor.fetchall()
    # Ensure distinct
    conv_dict = {}
    for r in conversations_raw:
        conv_dict[r[0]] = {"id": r[0], "name": r[1], "role": r[2]}
    conversations = list(conv_dict.values())
    conn.close()
    
    return render_template("chat_full.html", name=session.get("user_name"), role=session.get("role"), me_id=me_id, conversations=conversations, active_user=None, chat_history=[])

@app.route("/chat/<int:user_id>")
def chat_user(user_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
        
    me_id = session["user_id"]
    if user_id == me_id:
        return redirect(url_for("chat"))
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Target User
    cursor.execute("SELECT id, name, role FROM users WHERE id=?", (user_id,))
    target = cursor.fetchone()
    if not target:
        return redirect(url_for("chat"))
    active_user = {"id": target[0], "name": target[1], "role": target[2]}

    # Get conversations list
    cursor.execute("""
        SELECT DISTINCT u.id, u.name, u.role
        FROM users u 
        JOIN messages m ON (u.id = m.receiver_id OR u.id = m.sender_id)
        WHERE (m.sender_id = ? OR m.receiver_id = ?) AND u.id != ?
    """, (me_id, me_id, me_id))
    conversations_raw = cursor.fetchall()
    conv_dict = {}
    for r in conversations_raw:
        conv_dict[r[0]] = {"id": r[0], "name": r[1], "role": r[2]}
    
    # Add active user directly just in case it's a new combo
    conv_dict[active_user["id"]] = active_user
    conversations_list = list(conv_dict.values())
    
    # Get active history
    cursor.execute("""
        SELECT m.sender_id, m.content, m.timestamp, u.name as sender_name
        FROM messages m
        JOIN users u ON u.id = m.sender_id
        WHERE (m.sender_id=? AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=?)
        ORDER BY m.timestamp ASC
    """, (me_id, user_id, user_id, me_id))
    
    history = []
    for r in cursor.fetchall():
        history.append({
            "sender_id": r[0],
            "content": r[1],
            "timestamp": r[2],
            "sender_name": r[3]
        })
        
    conn.close()
    
    return render_template("chat_full.html", name=session.get("user_name"), role=session.get("role"), me_id=me_id, conversations=conversations_list, active_user=active_user, chat_history=history)

@app.route("/api/chat-history/<other_user>")
def chat_history(other_user):
    if "user_name" not in session:
        return jsonify([])

    me = session["user_name"]
    if me == other_user:
        return jsonify([])
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sender_name, content, timestamp 
        FROM messages 
        WHERE (sender_name=? AND receiver_name=?) 
           OR (sender_name=? AND receiver_name=?)
        ORDER BY id ASC
    """, (me, other_user, other_user, me))
    
    msgs = cursor.fetchall()
    conn.close()

    result = [{"sender": m[0], "content": m[1], "timestamp": m[2]} for m in msgs]
    return jsonify(result)

@socketio.on('join_global')
def handle_join_global():
    if "user_id" in session:
        room = f"global_{session['user_id']}"
        join_room(room)

@socketio.on('join_chat')
def handle_join_chat(data):
    if "user_id" not in session:
        return
    me_id = session["user_id"]
    other_user_id = data.get("other_user")
    if str(other_user_id) == str(me_id):
        return
    if other_user_id:
        # Create a unique room deterministic to both users independent of who calls it
        room = f"chat_{min(int(me_id), int(other_user_id))}_{max(int(me_id), int(other_user_id))}"
        join_room(room)

@socketio.on('send_message')
def handle_send_message(data):
    if "user_id" not in session:
        return
    
    me_id = session["user_id"]
    me_name = session["user_name"]
    other_user_id = data.get("other_user")
    if str(other_user_id) == str(me_id):
        return
        
    content = data.get("content")
    if not other_user_id or not content:
        return

    timestamp = datetime.now().isoformat()
    # Log directly to DB
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (sender_id, receiver_id, content, timestamp)
        VALUES (?, ?, ?, ?)
    """, (me_id, other_user_id, content, timestamp))
    
    # Also notify the receiver directly
    msg = f"New message from {me_name}"
    cursor.execute("INSERT INTO notifications (user_id, message, timestamp, related_user_id) VALUES (?, ?, ?, ?)", (other_user_id, msg, timestamp, me_id))
    conn.commit()
    conn.close()

    # Emit new message explicitly to the scoped chat room
    chat_room = f"chat_{min(int(me_id), int(other_user_id))}_{max(int(me_id), int(other_user_id))}"
    emit('receive_message', {
        'sender_id': me_id,
        'sender_name': me_name,
        'content': content,
        'timestamp': timestamp,
        'related_user': me_id
    }, to=chat_room)
    
    # Emit notification pulse to receiver's wider global state
    emit('new_notification', {'message': msg, 'timestamp': timestamp, 'related_user': me_id}, to=f"global_{other_user_id}")

# ------------------------
# RUN SERVER
# ------------------------
if __name__ == "__main__":
    socketio.run(app, debug=True)