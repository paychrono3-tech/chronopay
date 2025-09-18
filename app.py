from flask import Flask, render_template, request, redirect, session, url_for
import json, os, qrcode
from flask import Flask, render_template, request, redirect, url_for, jsonify
from forex_python.converter import CurrencyRates
import cv2

app = Flask(__name__)
app.secret_key = "secret123"

USER_FILE = "users.json"
QR_FOLDER = "static/qrcodes"
os.makedirs(QR_FOLDER, exist_ok=True)

c = CurrencyRates()


# ----------------- Utility Functions -----------------
def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=2)


def generate_qr(username):
    """Generate QR code image for user"""
    img = qrcode.make(username)
    path = os.path.join(QR_FOLDER, f"{username}.png")
    img.save(path)


# ----------------- Routes -----------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        users = load_users()
        if username in users:
            return "User already exists. <a href='/signup'>Try again</a>"

        # New users start with balance 0
        users[username] = {"password": password, "balance": 0, "history": []}
        save_users(users)

        generate_qr(username)
        return redirect("/login")
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        users = load_users()
        if username in users and users[username]["password"] == password:
            session["username"] = username
            return redirect("/dashboard")
        return "Invalid credentials. <a href='/login'>Try again</a>"
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect("/login")

    users = load_users()
    username = session["username"]
    balance = users[username]["balance"]

    return render_template(
        "dashboard.html", username=username, balance=balance
    )


@app.route("/transfer", methods=["GET", "POST"])
def transfer():
    if "username" not in session:
        return redirect("/login")

    if request.method == "POST":
        sender = session["username"]
        receiver = request.form["receiver"]
        amount = float(request.form["amount"])
        from_currency = request.form["from_currency"].upper()
        to_currency = request.form["to_currency"].upper()

        users = load_users()
        if receiver not in users:
            return "Receiver not found. <a href='/transfer'>Try again</a>"

        if users[sender]["balance"] < amount:
            return "Insufficient balance. <a href='/transfer'>Try again</a>"

        # Currency conversion
        converted_amount = c.convert(from_currency, to_currency, amount)

        # Update balances
        users[sender]["balance"] -= amount
        users[receiver]["balance"] += converted_amount

        # History records
        users[sender]["history"].append(
            f"Sent {amount} {from_currency} to {receiver} ({converted_amount:.2f} {to_currency})"
        )
        users[receiver]["history"].append(
            f"Received {converted_amount:.2f} {to_currency} from {sender} ({amount} {from_currency})"
        )

        save_users(users)
        return redirect("/dashboard")

    return render_template("transfer.html")


@app.route("/scan_qr", methods=["POST"])
def scan_qr():
    if "username" not in session:
        return redirect("/login")

    file = request.files["qrfile"]
    filepath = os.path.join("static", "temp.png")
    file.save(filepath)

    # Decode QR using OpenCV
    img = cv2.imread(filepath)
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img)

    if not data:
        return "Invalid QR. <a href='/transfer'>Try again</a>"

    receiver = data.strip()
    return render_template("transfer.html", receiver=receiver)


@app.route("/history")
def history():
    if "username" not in session:
        return redirect("/login")

    users = load_users()
    username = session["username"]
    history = users[username]["history"]

    return render_template("history.html", history=history)


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect("/")



app = Flask(__name__)

# Scan QR / Payment Route
import json
from flask import Flask, render_template, request

app = Flask(__name__)

# Load users from JSON
def load_users():
    with open("users.json", "r") as f:
        return json.load(f)

# Save users back to JSON
def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

@app.route("/scan_qr", methods=["GET", "POST"])
def scan_qr():
    if request.method == "POST":
        sender = request.form.get("sender")
        receiver = request.form.get("receiver")
        amount = float(request.form.get("amount", 0))

        users = load_users()

        if sender not in users or receiver not in users:
            return "❌ Sender or receiver not found!", 400

        if users[sender]["balance"] < amount:
            return "❌ Insufficient balance!", 400

        # Update balances
        users[sender]["balance"] -= amount
        users[receiver]["balance"] += amount

        save_users(users)

        return f"✅ {sender} paid {amount} to {receiver} successfully!"

    return render_template("scan_qr.html")



# ----------------- Run App -----------------
if __name__ == "__main__":
    app.run(debug=True)
