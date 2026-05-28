import mysql
import mysql.connector 

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)

app = Flask(__name__)
app.secret_key = "admin"

import os
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash

mydb = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    database="project",
    buffered=True
)

app.debug = True

#automatically logs out after 5 minutes
app.permanent_session_lifetime = timedelta(minutes=5)

#checks if the user is active (if it's not then it automatically logs out after 5 minutes)
@app.before_request
def refresh_session():
    if 'user' in session:
        session.modified = True


@app.route('/')
def index():
    if 'user' not in session:
        return redirect("/login")
    else:
        return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        mydb.commit()
        cursor = mydb.cursor(dictionary=True)
        cursor.execute("SELECT people.*, password FROM admin INNER JOIN people ON userid = adminid WHERE adminid = %s", (username,))
        user = cursor.fetchone()

        if user and (
            user["password"] == password
            or check_password_hash(user["password"], password)
        ):
            session["user"] = {
                "fname": user["fname"],
                "lname": user["lname"]
            }
            flash("Logged in successfully.", "success")
            return redirect("/")
        else:
            flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
  session.clear()
  return redirect("/")

@app.route("/adduser", methods=["GET", "POST"])
def adduser():
    cursor = mydb.cursor(dictionary=True)
    if request.method == "POST":
        username = request.form.get("email")
        fname = request.form.get("fname")
        lname = request.form.get("lname")
        kind = request.form.get("type")
        cursor.execute("INSERT INTO people (userid, fname, lname, type) VALUES (%s, %s, %s, %s)", (username, fname, lname, kind))
        if kind == "Admin":
            hashed_password = generate_password_hash("pass", method='pbkdf2:sha256')
            cursor.execute("INSERT INTO admin (adminid, password) VALUES (%s, %s)", (username, hashed_password))
        return redirect("/")
    return render_template("adduser.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
