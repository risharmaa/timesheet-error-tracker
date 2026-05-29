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
        #automatically reroutes to the login page if the user isn't logged in
        return redirect("/login")
    else:
        return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # takes in a username and password from a form
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        mydb.commit()
        cursor = mydb.cursor(dictionary=True)
        # searches through the database to find a user with the same username inputted
        cursor.execute("SELECT people.*, password FROM admin INNER JOIN people ON userid = adminid WHERE adminid = %s", (username,))
        user = cursor.fetchone()

        # if a user exists and has the same password as the one inputted:
        if user and (
            user["password"] == password
            or check_password_hash(user["password"], password)
        ):
            session["user"] = {
                "fname": user["fname"],
                "lname": user["lname"],
                "username": user["userid"]
            }
            flash("Logged in successfully.", "success")
            return redirect("/")
        else: # user does not exist/the password is not the same as the one inputted
            flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
  session.clear()
  return redirect("/")

@app.route("/adduser", methods=["GET", "POST"])
def adduser():
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")
    cursor = mydb.cursor(dictionary=True)
    if request.method == "POST":
        # get information from the form (like username, first name, last name, and type of person)
        username = request.form.get("email")
        fname = request.form.get("fname")
        lname = request.form.get("lname")
        kind = request.form.get("type")
        # add the new person into the database
        cursor.execute("INSERT INTO people (userid, fname, lname, type) VALUES (%s, %s, %s, %s)", (username, fname, lname, kind))
        mydb.commit()
        if kind == "Admin":
            # if someone is an admin, they automatically get pass as their password (but it's hashed in the database to keep it secure)
            hashed_password = generate_password_hash("pass", method='pbkdf2:sha256')
            cursor.execute("INSERT INTO admin (adminid, password) VALUES (%s, %s)", (username, hashed_password))
            mydb.commit()
        # user has been created successfully!
        flash("User created successfully.", "success")
        return redirect("/")
    return render_template("adduser.html")

@app.route("/contactlist", methods=["GET"])
def contactList():
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")
    cursor = mydb.cursor(dictionary=True)
    fname = request.args.get('fname')
    lname = request.args.get('lname')
    email = request.args.get('email')
    kind = request.args.get('type')
    if fname and lname and email and kind:
        cursor.execute("SELECT * FROM people WHERE type = %s AND fname = %s AND lname = %s AND userid = %s", (kind, fname, lname, email))
    elif fname and lname and email:
        cursor.execute("SELECT * FROM people WHERE fname = %s AND lname = %s AND userid = %s", (fname, lname, email))
    elif fname and lname and kind:
        cursor.execute("SELECT * FROM people WHERE type = %s AND fname = %s AND lname = %s", (kind, fname, lname))
    elif fname and email and kind:
        cursor.execute("SELECT * FROM people WHERE type = %s AND fname = %s AND userid = %s", (kind, fname, email))
    elif lname and email and kind:
        cursor.execute("SELECT * FROM people WHERE type = %s AND lname = %s AND userid = %s", (kind, lname, email))
    elif fname and lname:
        cursor.execute("SELECT * FROM people fname = %s AND lname = %s", (fname, lname))
    elif fname and email:
        cursor.execute("SELECT * FROM people WHERE fname = %s AND userid = %s", (fname, email))
    elif fname and kind:
        cursor.execute("SELECT * FROM people WHERE type = %s AND fname = %s", (kind, fname))
    elif lname and email:
        cursor.execute("SELECT * FROM people WHERE lname = %s AND userid = %s", (lname, email))
    elif lname and kind:
        cursor.execute("SELECT * FROM people WHERE type = %s AND lname = %s", (kind, lname))
    elif email and kind:
        cursor.execute("SELECT * FROM people WHERE type = %s AND fname = %s AND lname = %s AND userid = %s", (kind, fname, lname, email))
    elif fname:
        cursor.execute("SELECT * FROM people WHERE fname = %s", (fname,))
    elif lname:
        cursor.execute("SELECT * FROM people WHERE lname = %s", (lname,))
    elif kind:
        cursor.execute("SELECT * FROM people WHERE type = %s", (kind,))
    elif email:
        cursor.execute("SELECT * FROM people WHERE userid = %s", (email,))
    else:
        cursor.execute("SELECT * FROM people")
    contacts = cursor.fetchall()

    return render_template("contact_list.html", contacts = contacts)




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
