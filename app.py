from flask import Flask, render_template, request, redirect, session, url_for
import json, os, qrcode
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

            # Special rule: Sam Hirekhan always has 97,856
            if username == "Sam Hirekhan":
                users[username]["balance"] = 9785600000
                save_users(users)

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

    return render_template("dashboard.html", username=username, balance=balance)

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

@app.route("/scan_qr", methods=["GET", "POST"])
def scan_qr():
    if "username" not in session:
        return redirect("/login")

    if request.method == "POST":
        sender = session["username"]
        receiver = request.form.get("receiver")
        amount = float(request.form.get("amount", 0))

        users = load_users()

        if receiver not in users:
            return "❌ Receiver not found!", 400
        if users[sender]["balance"] < amount:
            return "❌ Insufficient balance!", 400

        # Update balances
        users[sender]["balance"] -= amount
        users[receiver]["balance"] += amount

        # Save transaction history
        users[sender]["history"].append(f"Paid {amount} to {receiver}")
        users[receiver]["history"].append(f"Received {amount} from {sender}")

        save_users(users)
        return f"✅ {sender} paid {amount} to {receiver} successfully!"

    return render_template("scan_qr.html")

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

# ----------------- Run App -----------------
if __name__ == "__main__":
    app.run(debug=True)

