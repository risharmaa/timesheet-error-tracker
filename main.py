import mysql
import mysql.connector 
import json
import random
import string
import os

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


from datetime import datetime, timedelta, date
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mail import Mail, Message


mydb = mysql.connector.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "project"),
    buffered=True
)

app.debug = True

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")

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

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = FALSE")
    sent = cursor.fetchall()
    cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = FALSE")
    waiting = cursor.fetchall()

    count = {}

    # get a total number of outstanding timesheets
    cursor.execute("SELECT COUNT(*) AS outstanding FROM timesheet WHERE (sent = FALSE OR received = FALSE)")
    a = cursor.fetchone()
    count['outstanding'] = a['outstanding']
    cursor.execute("SELECT COUNT(*) AS send FROM timesheet WHERE sent = FALSE AND received = FALSE")
    a = cursor.fetchone()
    count['send'] = a['send']
    cursor.execute("SELECT COUNT(*) AS wait FROM timesheet WHERE sent = TRUE AND received = FALSE")
    a = cursor.fetchone()
    count['wait'] = a['wait']

    return render_template("home.html", sent = sent, waiting = waiting, count = count)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # takes in a username and password from a form
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        cursor = mydb.cursor(dictionary=True)
        # searches through the database to find a user with the same username inputted
        cursor.execute("SELECT people.*, password FROM admin INNER JOIN people ON userid = adminid WHERE adminid = %s", (username,))
        user = cursor.fetchone()

        # if a user exists and has the same password as the one inputted:
        if user and (
            user["password"] == password
            or check_password_hash(user["password"], password)
        ):
            session["test"] = {
                "fname": user["fname"],
                "lname": user["lname"],
                "username": user["userid"]
            }
            flash("A verification code has been sent to your email.", "success")
            code = ''.join(random.choices(string.digits, k=6))
            session['2fa_code'] = code
            session['username'] = user["userid"]

            mail = Mail(app)

            msg = Message(
                subject="Your verification code",
                sender= app.config['MAIL_USERNAME'],
                recipients=[session['test']['username']]
            )
            msg.body = f"Your verification code is: {code}"   
            mail.send(msg)

            return redirect("/verify")
        else: # user does not exist/the password is not the same as the one inputted
            flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if code == session['2fa_code']:
            flash("Logged in successfully.", "success")
            session["user"] = {
                "fname": session["test"]["fname"],
                "lname": session["test"]["lname"],
                "username": session["test"]["lname"]
            }
            session.pop('2fa_code', None)
            session.pop('test', None)
            return redirect("/")
        else:
            session.clear()
            flash("2FA codes did not match.", "danger")
            return redirect("/")

    return render_template("2fa.html")

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

        # check if the email already exists first
        cursor.execute("SELECT * FROM people WHERE userid = %s", (username,))
        check = cursor.fetchall()
        if check:
            flash("A user with the same email or phone number already exists.", "danger")
            return redirect("/adduser")

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
        return redirect("/contactlist")
    return render_template("adduser.html")

@app.route("/contactlist", methods=["GET"])
def contactList():
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    # use this to search/filter for specific people!
    cursor = mydb.cursor(dictionary=True)
    fname = request.args.get('fname')
    lname = request.args.get('lname')
    email = request.args.get('email')

    if fname and lname and email:
        cursor.execute("SELECT * FROM people WHERE fname = %s AND lname = %s AND userid = %s", (fname, lname, email))
        contacts = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE fname = %s AND lname = %s AND userid = %s AND type = 'Admin'", (fname, lname, email))
        admin = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE fname = %s AND lname = %s AND userid = %s AND type = 'Client'", (fname, lname, email))
        client = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE fname = %s AND lname = %s AND userid = %s AND type = 'Caregiver'", (fname, lname, email))
        caregiver = cursor.fetchall()
    elif fname and lname:
        cursor.execute("SELECT * FROM people WHERE fname = %s AND lname = %s", (fname, lname))
        contacts = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE fname = %s AND lname = %s AND type = 'Admin'", (fname, lname))
        admin = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE fname = %s AND lname = %s AND type = 'Client'", (fname, lname))
        client = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE fname = %s AND lname = %s AND type = 'Caregiver'", (fname, lname))
        caregiver = cursor.fetchall()
    elif fname and email:
        cursor.execute("SELECT * FROM people WHERE fname = %s AND userid = %s", (fname, email))
        contacts = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE fname = %s AND userid = %s AND type = 'Admin'", (fname, email))
        admin = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE fname = %s AND userid = %s AND type = 'Client'", (fname, email))
        client = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE fname = %s AND userid = %s AND type = 'Caregiver'", (fname, email))
        caregiver = cursor.fetchall()
    elif lname and email:
        cursor.execute("SELECT * FROM people WHERE lname = %s AND userid = %s", (lname, email))
        contacts = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE lname = %s AND userid = %s AND type = 'Admin'", (lname, email))
        admin = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE lname = %s AND userid = %s AND type = 'Client'", (lname, email))
        client = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE lname = %s AND userid = %s AND type = 'Caregiver'", (lname, email))
        caregiver = cursor.fetchall()
    elif fname:
        cursor.execute("SELECT * FROM people WHERE fname = %s", (fname,))
        contacts = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE fname = %s AND type = 'Admin'", (fname,))
        admin = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE fname = %s AND type = 'Client'", (fname,))
        client = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE fname = %s AND type = 'Caregiver'", (fname,))
        caregiver = cursor.fetchall()
    elif lname:
        cursor.execute("SELECT * FROM people WHERE lname = %s", (lname,))
        contacts = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE lname = %s AND type = 'Admin'", (lname,))
        admin = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE lname = %s AND type = 'Client'", (lname,))
        client = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE lname = %s AND type = 'Caregiver'", (lname,))
        caregiver = cursor.fetchall()
    elif email:
        cursor.execute("SELECT * FROM people WHERE userid = %s", (email,))
        contacts = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE userid = %s AND type = 'Admin'", (email,))
        admin = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE userid = %s AND type = 'Client'", (email,))
        client = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE userid = %s AND type = 'Caregiver'", (email,))
        caregiver = cursor.fetchall()
    else:
        cursor.execute("SELECT * FROM people")
        contacts = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE type = 'Admin'")
        admin = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE type = 'Client'")
        client = cursor.fetchall()

        cursor.execute("SELECT * FROM people WHERE type = 'Caregiver'")
        caregiver = cursor.fetchall()

    for item in contacts:
        if item["type"] == "Client":
            cursor.execute("SELECT people.fname, people.lname, people.userid, clientid FROM clients INNER JOIN people ON caregiverid = userid WHERE clientid = %s", (item['userid'],))
            item["caregiver"] = cursor.fetchall()
            cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = FALSE AND received = FALSE AND clientid = %s ORDER BY date DESC", (item['userid'],))
            item["sent"] = cursor.fetchall()
            cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = FALSE AND clientid = %s ORDER BY date DESC", (item['userid'],))
            item["waiting"] = cursor.fetchall()
            cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = TRUE AND clientid = %s AND (date BETWEEN %s AND %s) ORDER BY date DESC", (item['userid'], date.today() - timedelta(days=30), date.today()))
            item["closed"] = cursor.fetchall()
        if item["type"] == "Caregiver":
            cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = FALSE AND received = FALSE AND caregiverid = %s ORDER BY date DESC", (item['userid'],))
            item["sent"] = cursor.fetchall()
            cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = FALSE AND caregiverid = %s ORDER BY date DESC", (item['userid'],))
            item["waiting"] = cursor.fetchall()
            cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = TRUE AND caregiverid = %s AND (date BETWEEN %s AND %s) ORDER BY date DESC", (item['userid'], date.today() - timedelta(days=30), date.today()))
            item["closed"] = cursor.fetchall()
    
    for item in client:
        cursor.execute("SELECT people.fname, people.lname, people.userid, clientid FROM clients INNER JOIN people ON caregiverid = userid WHERE clientid = %s", (item['userid'],))
        item["caregiver"] = cursor.fetchall()
        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = FALSE AND received = FALSE AND clientid = %s ORDER BY date DESC", (item['userid'],))
        item["sent"] = cursor.fetchall()
        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = FALSE AND clientid = %s ORDER BY date DESC", (item['userid'],))
        item["waiting"] = cursor.fetchall()
        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = TRUE AND clientid = %s AND (date BETWEEN %s AND %s) ORDER BY date DESC", (item['userid'], date.today() - timedelta(days=30), date.today()))
        item["closed"] = cursor.fetchall()

    for item in caregiver:
        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = FALSE AND received = FALSE AND caregiverid = %s ORDER BY date DESC", (item['userid'],))
        item["sent"] = cursor.fetchall()
        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = FALSE AND caregiverid = %s ORDER BY date DESC", (item['userid'],))
        item["waiting"] = cursor.fetchall()
        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = TRUE AND caregiverid = %s AND (day_r BETWEEN %s AND %s) ORDER BY date DESC", (item['userid'], date.today() - timedelta(days=30), date.today()))            
        item["closed"] = cursor.fetchall()

    return render_template("contact_list.html", contacts = contacts, admin = admin, client = client, caregiver = caregiver)

@app.route("/deleteuser/<int:usernum>")
def delete_user(usernum):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    # get userid of the person we're trying to delete
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT userid FROM people WHERE usernum = %s", (usernum,))
    email = cursor.fetchone()
    email = email['userid']

    # first check if the person that is trying to be deleted is the user
    if email == session['user']['username']:
        flash("You cannot delete yourself.", "danger")
        return redirect('/contactlist')
    # next check if the user being deleted has a timesheet that is still open:
    cursor.execute("SELECT * FROM timesheet WHERE (clientid = %s OR caregiverid = %s) AND received = FALSE", (email, email))
    open_check = cursor.fetchall()
    if open_check:
        # this means that there exists a timesheet error that is still open/not closed yet!
        flash("You can not delete a user with an open timesheet error.", "danger")
        return redirect('/contactlist')
    
    #figure out the type of user that we're trying to delete
    cursor.execute("SELECT type, fname, lname FROM people WHERE userid = %s", (email,))
    kind = cursor.fetchone()
    name = kind['fname'] + " " + kind['lname']
    kind = kind['type']
    if kind == "Admin":
        cursor.execute("DELETE FROM admin WHERE adminid = %s", (email,))
    if kind == "Client":
        cursor.execute("DELETE FROM timesheet WHERE clientid = %s", (email,))
        cursor.execute("DELETE FROM clients WHERE clientid = %s", (email,))
    if kind == "Caregiver":
        cursor.execute("DELETE FROM timesheet WHERE caregiverid = %s", (email,))
        cursor.execute("DELETE FROM clients WHERE caregiverid = %s", (email,))
    cursor.execute("DELETE FROM people WHERE userid = %s", (email,))
    mydb.commit()

    deletion = "You have successfully deleted " + name + "!"
    flash(deletion, "success")
    return redirect("/contactlist")

@app.route("/addcaregiver/<int:usernum>", methods = ["GET"])
def assign_caregiver(usernum):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    cursor = mydb.cursor(dictionary=True)
    # generate a list of caregivers (that aren't already assigned to the client)
    cursor.execute("SELECT * FROM people WHERE usernum = %s", (usernum,))
    client = cursor.fetchone()
    email = client['userid']

    cursor.execute("SELECT * FROM people WHERE type = 'Caregiver'")
    caregivers = cursor.fetchall()
    c_list = []
    # add caregivers to the need-to-add list
    for c in caregivers:
        cursor.execute("SELECT * FROM clients WHERE clientid = %s AND caregiverid = %s", (email, c['userid']))
        check = cursor.fetchone()
        if not check:
            c_list.append(c) 

    add_caregiver = request.args.get('add_caregiver')
    if add_caregiver is not None:
        cursor.execute("INSERT INTO clients (clientid, caregiverid) VALUES (%s, %s)", (email, add_caregiver))
        mydb.commit()
        added = "You have successfully added a caregiver to " + client['fname'] + " " + client['lname'] + "!"
        flash(added, "success")
        return redirect("/contactlist")
    

    cursor.execute("SELECT people.fname, people.lname, people.userid, clientid FROM clients INNER JOIN people ON caregiverid = userid WHERE clientid = %s", (email,))
    r_list = cursor.fetchall()
    remove_caregiver = request.args.get('remove_caregiver')
    if remove_caregiver is not None:
        # check if there's any open timesheets
        cursor.execute("SELECT * FROM timesheet WHERE clientid = %s AND caregiverid = %s AND received = FALSE", (email, remove_caregiver))
        timesheet_check = cursor.fetchall()
        if timesheet_check:
            flash("You can not remove a client-caregiver relationship with an open timesheet error.", "danger")
            return redirect(url_for("assign_caregiver", usernum=client['usernum']))
        else:
            # delete any client-caregiver relationships
            cursor.execute("DELETE FROM clients WHERE clientid = %s AND caregiverid = %s", (email, remove_caregiver))
            mydb.commit()
            removed = "You have successfully removed a caregiver from " + client['fname'] + " " + client['lname'] + "!"
            flash(removed, "success")
        return redirect("/contactlist")

    return render_template("assign_caregiver.html", c_list = c_list, client = client, r_list = r_list)

@app.route("/createtimesheet", methods = ["GET", "POST"])
def create_timesheet():
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    cursor = mydb.cursor(dictionary=True)

    cursor.execute("SELECT * FROM people WHERE type = 'Client'")
    cl_list = cursor.fetchall()

    cursor.execute("SELECT * FROM people WHERE type = 'Caregiver'")
    cr_list = cursor.fetchall()


    if request.method == "POST":
        # get information from the form
        client = request.form.get("client_id")
        caregiver = request.form.get("caregiver_id")
        reason = request.form.get("reason")
        date = request.form.get("date")

        # check to make sure that the caregiver or client is in the system
        cursor.execute("SELECT * FROM people WHERE type = 'Client' AND userid = %s", (client,))
        client_check = cursor.fetchall()
        if not client_check:
            flash("This client does not exist in our system.", "danger")
            return redirect("/createtimesheet")
        cursor.execute("SELECT * FROM people WHERE type = 'Caregiver' AND userid = %s", (caregiver,))
        caregiver_check = cursor.fetchall()
        if not caregiver_check:
            flash("This caregiver does not exist in our system.", "danger")
            return redirect("/createtimesheet")


        cursor.execute("SELECT * FROM timesheet WHERE clientid = %s AND caregiverid = %s AND date = %s", (client, caregiver, date))
        check = cursor.fetchone()
        if check:
            # redirect to make sure that the user doesn't add duplicate time sheets
            session["timesheet"] = {
                "client": client,
                "caregiver": caregiver,
                "reason": reason,
                "date": date
            }
            reason = check['reason']
            cursor.execute("SELECT fname, lname FROM people WHERE userid = %s", (session['timesheet']['client'],))
            client_name = cursor.fetchone()
            cursor.execute("SELECT fname, lname FROM people WHERE userid = %s", (session['timesheet']['caregiver'],))
            caregiver_name = cursor.fetchone()
            return render_template("confirm_timesheet.html", client_name = client_name, caregiver_name = caregiver_name, reason = reason)
        else:
            cursor.execute("INSERT INTO timesheet (clientid, caregiverid, date, reason) VALUES (%s, %s, %s, %s)", (client, caregiver, date, reason))
            mydb.commit()
            flash("You have successfully created a timesheet error!", "success")
            return redirect("/viewtimesheets")

    return render_template("create_timesheet.html", cl_list = cl_list, cr_list = cr_list)

@app.route("/getcaregivers/<path:userid>")
def get_caregivers(userid):
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT people.fname, people.lname, people.userid, clientid FROM clients INNER JOIN people ON caregiverid = userid WHERE clientid = %s", (userid,))
    caregivers = cursor.fetchall()
    print("caregivers found:", caregivers)
    return jsonify(caregivers)
    
@app.route("/viewtimesheets", methods = ["GET", "POST"])
def view_timesheets():
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    cursor = mydb.cursor(dictionary=True)

    #generate list of clients + caregivers
    cursor.execute("SELECT * FROM people WHERE type = 'Client'")
    clients = cursor.fetchall()

    cursor.execute("SELECT * FROM people WHERE type = 'Caregiver'")
    caregivers = cursor.fetchall()

    #search/filter for timesheet errors! 
    client = request.args.get('client')
    caregiver = request.args.get('caregiver')
    search_date = request.args.get('date')

    #get today's date to limit all closed timesheets to be within the year
    today = date.today()
    first = today - timedelta(days=365)
    last = today

    if client and caregiver and search_date:
        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = FALSE AND received = FALSE AND clientid = %s AND caregiverid = %s AND date = %s ORDER BY date DESC", (client, caregiver, search_date))
        sent = cursor.fetchall()

        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = FALSE AND clientid = %s AND caregiverid = %s AND date = %s ORDER BY date DESC", (client, caregiver, search_date))
        waiting = cursor.fetchall()

        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE and received = TRUE AND clientid = %s AND caregiverid = %s AND date = %s AND (date BETWEEN %s AND %s) ORDER BY date DESC", (client, caregiver, search_date, first, last))
        closed = cursor.fetchall()
    elif client and caregiver:
        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = FALSE AND received = FALSE AND clientid = %s AND caregiverid = %s ORDER BY date DESC", (client, caregiver))
        sent = cursor.fetchall()

        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = FALSE AND clientid = %s AND caregiverid = %s ORDER BY date DESC", (client, caregiver))
        waiting = cursor.fetchall()

        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE and received = TRUE AND clientid = %s AND caregiverid = %s AND (date BETWEEN %s AND %s) ORDER BY date DESC", (client, caregiver))
        closed = cursor.fetchall()
    elif client and search_date:
        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = FALSE AND received = FALSE AND clientid = %s AND date = %s ORDER BY date DESC", (client, search_date))
        sent = cursor.fetchall()

        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = FALSE AND clientid = %s AND date = %s ORDER BY date DESC", (client, search_date))
        waiting = cursor.fetchall()

        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE and received = TRUE AND clientid = %s AND date = %s AND (date BETWEEN %s AND %s) ORDER BY date DESC", (client, search_date, first, last))
        closed = cursor.fetchall()
    elif caregiver and search_date:
        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = FALSE AND received = FALSE AND caregiverid = %s AND date = %s ORDER BY date DESC", (caregiver, search_date))
        sent = cursor.fetchall()

        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = FALSE AND caregiverid = %s AND date = %s ORDER BY date DESC", (caregiver, search_date))
        waiting = cursor.fetchall()

        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE and received = TRUE AND caregiverid = %s AND date = %s AND (date BETWEEN %s AND %s) ORDER BY date DESC", (caregiver, search_date, first, last))
        closed = cursor.fetchall()
    elif client:
        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = FALSE AND received = FALSE AND clientid = %s ORDER BY date DESC", (client,))
        sent = cursor.fetchall()

        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = FALSE AND clientid = %s ORDER BY date DESC", (client,))
        waiting = cursor.fetchall()

        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE and received = TRUE AND clientid = %s AND (date BETWEEN %s AND %s) ORDER BY date DESC", (client, first, last))
        closed = cursor.fetchall()
    elif caregiver:
        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = FALSE AND received = FALSE AND caregiverid = %s ORDER BY date DESC", (caregiver,))
        sent = cursor.fetchall()

        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = FALSE AND caregiverid = %s ORDER BY date DESC", (caregiver,))
        waiting = cursor.fetchall()

        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE and received = TRUE AND caregiverid = %s AND (date BETWEEN %s AND %s) ORDER BY date DESC", (caregiver, first, last))
        closed = cursor.fetchall()
    elif search_date:
        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = FALSE AND received = FALSE AND date = %s ORDER BY date DESC", (search_date,))
        sent = cursor.fetchall()

        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = FALSE AND date = %s ORDER BY date DESC", (search_date,))
        waiting = cursor.fetchall()

        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE and received = TRUE AND date = %s AND (date BETWEEN %s AND %s) ORDER BY date DESC", (search_date, first, last))
        closed = cursor.fetchall()
    else:
        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = FALSE ORDER BY date DESC")
        sent = cursor.fetchall()

        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE AND received = FALSE ORDER BY date DESC")
        waiting = cursor.fetchall()

        cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE sent = TRUE and received = TRUE AND (date BETWEEN %s AND %s) ORDER BY date DESC", (first, last))
        closed = cursor.fetchall()
    
    if request.method == "POST":
        deletions = request.form.getlist('selected')
        number = len(deletions)
        if number == 0:
            delete = "You have not deleted any timesheet errors."
            flash(delete, "success")
            return redirect("/viewtimesheets")
        elif number == 1:
            delete = "You have deleted " + str(number) + " timesheet error."
            cursor.execute("DELETE from timesheet WHERE num = %s", (deletions[0],))
        else:
            # convert deletions into a tuple for executemany
            formatted_data = [(item,) for item in deletions]
            delete = "You have deleted " + str(number) + " timesheet errors."
            cursor.executemany("DELETE from timesheet WHERE num = %s", (formatted_data))
        mydb.commit()
        flash(delete, "success")
        return redirect("/viewtimesheets")

    return render_template("view_timesheets.html", sent = sent, waiting = waiting, closed = closed, clients = clients, caregivers = caregivers)

@app.route("/senttimesheet/<num>")
def sent_timesheet(num):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")
    
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("UPDATE timesheet SET sent = TRUE WHERE num = %s", (num,))
    mydb.commit()

    flash("Timesheet updated to sent.", "success")
    return redirect("/viewtimesheets")

# use this when updating on home (it redirects back to home)
@app.route("/home/senttimesheet/<num>")
def home_sent_timesheet(num):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")
    
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("UPDATE timesheet SET sent = TRUE WHERE num = %s", (num,))
    mydb.commit()

    flash("Timesheet updated to sent.", "success")
    return redirect("/")

# use this when updating on the calendar (it redirects back to calendar)
@app.route("/calendar/senttimesheet/<num>")
def calendar_sent_timesheet(num):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")
    
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("UPDATE timesheet SET sent = TRUE WHERE num = %s", (num,))
    mydb.commit()

    flash("Timesheet updated to sent.", "success")
    return redirect("/calendar")

@app.route("/closetimesheet/<num>", methods = ["GET", "POST"])
def close_timesheet(num):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    cursor = mydb.cursor(dictionary=True)

    cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE num = %s", (num,))
    info = cursor.fetchone()

    if request.method == "POST":
        # get information from the form
        day_r = request.form.get("day_r")
        kind = request.form.get("kind")

        cursor.execute("UPDATE timesheet SET received = TRUE, type = %s, day_r = %s WHERE num = %s", (kind, day_r, num))
        mydb.commit()
        flash("Timesheet closed.", "success")
        return redirect("/viewtimesheets")
    
    return render_template("close_timesheet.html", info = info)

# use this when closing from the home page (redirects back to home)
@app.route("/home/closetimesheet/<num>", methods = ["GET", "POST"])
def home_close_timesheet(num):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    cursor = mydb.cursor(dictionary=True)

    cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE num = %s", (num,))
    info = cursor.fetchone()

    if request.method == "POST":
        # get information from the form
        day_r = request.form.get("day_r")
        kind = request.form.get("kind")

        cursor.execute("UPDATE timesheet SET received = TRUE, type = %s, day_r = %s WHERE num = %s", (kind, day_r, num))
        mydb.commit()
        flash("Timesheet closed.", "success")
        return redirect("/")
    
    return render_template("home_close_timesheet.html", info = info)

# use this when closing from the calendar (redirects back to calendar)
@app.route("/calendar/closetimesheet/<num>", methods = ["GET", "POST"])
def calendar_close_timesheet(num):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    cursor = mydb.cursor(dictionary=True)

    cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE num = %s", (num,))
    info = cursor.fetchone()

    if request.method == "POST":
        # get information from the form
        day_r = request.form.get("day_r")
        kind = request.form.get("kind")

        cursor.execute("UPDATE timesheet SET received = TRUE, type = %s, day_r = %s WHERE num = %s", (kind, day_r, num))
        mydb.commit()
        flash("Timesheet closed.", "success")
        return redirect("/calendar")
    
    return render_template("calendar_close_timesheet.html", info = info)

@app.route("/updatepassword", methods = ["GET", "POST"])
def update_password():
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    if request.method == "POST":
        # takes in a username and password from a form
        new = request.form.get("new", "")
        second = request.form.get("second", "")

        cursor = mydb.cursor(dictionary=True)
        # searches through the database to find a user with the same username inputted
        cursor.execute("SELECT people.*, password FROM admin INNER JOIN people ON userid = adminid WHERE adminid = %s", (session['user']['username'],))
        user = cursor.fetchone()

        if new == second:
            if new != user['password']:
                # hash password before updating the database
                pword = generate_password_hash(new, method='pbkdf2:sha256')
                cursor.execute("UPDATE admin SET password = %s WHERE adminid = %s", (pword, session['user']['username']))
                mydb.commit()
                flash("Password updated.", "success")
                return redirect('/')
            elif new == user['password']:
                flash("You already have this password.", "danger")
                return redirect('/updatepassword')
        else:
            flash("Passwords do not match.", "danger")
            return redirect('/updatepassword')

    return render_template("update_password.html")

@app.route("/calendar")
def calendar():
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid")
    timesheets = cursor.fetchall()
    for t in timesheets:
        # if you still haven't sent the timesheet:
        if t['sent'] == 0 and t['received'] == 0:
            t['color'] = '#FF0000' #red
        # if you sent the timesheet but are waiting for a response:
        elif t['sent'] == 1 and t['received'] == 0:
            t['color'] = '#FDBE02' #mango-yellow
        # if the timesheet is closed
        else:
            t['color'] = '#008000' #green


    return render_template("calendar.html", timesheets = timesheets)

@app.route("/confirmtimesheet", methods = ["GET"])
def confirm():
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("INSERT INTO timesheet (clientid, caregiverid, date, reason) VALUES (%s, %s, %s, %s)", (session['timesheet']['client'], session['timesheet']['caregiver'], session['timesheet']['date'], session['timesheet']['reason']))
    mydb.commit()
    flash("You have successfully created a timesheet error!", "success")
    session.pop('timesheet', None)
    return redirect("/viewtimesheets")

@app.route("/canceltimesheet")
def cancel():
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    session.pop('timesheet', None)
    flash("Timesheet error creation canceled.", "danger")
    return redirect("/viewtimesheets")

@app.route("/home/deletetimesheet/<num>")
def home_delete_timesheet(num):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("DELETE from timesheet WHERE num = %s", (num,))
    mydb.commit()
    return redirect("/")

@app.route("/calendar/deletetimesheet/<num>")
def calendar_delete_timesheet(num):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("DELETE from timesheet WHERE num = %s", (num,))
    mydb.commit()
    return redirect("/calendar")

@app.route("/deletetimesheet/<num>")
def delete_timesheet(num):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    cursor = mydb.cursor(dictionary=True)
    cursor.execute("DELETE from timesheet WHERE num = %s", (num,))
    mydb.commit()
    return redirect("/viewtimesheets")

@app.route("/weeklydashboard")
def weekly_dashboard():
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")
    
    # this should give a recap of the past week: what errors have been created/closed
    cursor = mydb.cursor(dictionary=True)

    # get today's date:
    today = date.today()
    first = today - timedelta(days=7)
    first_formatted = first.strftime("%A, %B %d, %Y")
    last = today
    last_formatted = last.strftime("%A, %B %d, %Y")

    count={}

    # get a list of all timesheet errors that have been created within the week
    cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE (sent = FALSE or received = FALSE) AND (date between %s AND %s)", (first, last))
    created = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) AS count FROM timesheet WHERE (sent = FALSE or received = FALSE) AND (date between %s AND %s)", (first, last))
    t_o_count = cursor.fetchone()
    count['week_open'] = t_o_count['count']

    # get a list of all timesheet errors that have been closed this week
    cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE received = TRUE AND (day_r between %s AND %s)", (first, last))
    closed = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) AS count FROM timesheet WHERE sent = TRUE AND received = TRUE AND (day_r between %s AND %s)", (first, last))
    t_c_count = cursor.fetchone()
    count['week_closed'] = t_c_count['count']

    # get a total number of outstanding timesheets
    cursor.execute("SELECT COUNT(*) AS outstanding FROM timesheet WHERE (sent = FALSE OR received = FALSE)")
    a = cursor.fetchone()
    count['outstanding'] = a['outstanding']
    cursor.execute("SELECT COUNT(*) AS send FROM timesheet WHERE sent = FALSE AND received = FALSE")
    a = cursor.fetchone()
    count['send'] = a['send']
    cursor.execute("SELECT COUNT(*) AS wait FROM timesheet WHERE sent = TRUE AND received = FALSE")
    a = cursor.fetchone()
    count['wait'] = a['wait']

    # get the total count of reasons for all timesheet errors made this week (for a pie chart)
    cursor.execute("SELECT reason, COUNT(*) AS reason_count FROM timesheet WHERE date between %s AND %s GROUP BY reason ORDER BY reason_count DESC", (first, last))
    reason = cursor.fetchall()
    reason_labels = [r["reason"] for r in reason]
    reason_values = [r["reason_count"] for r in reason]

    # get total count of caregiver/client combos
    cursor.execute("SELECT clientid, caregiverid, COUNT(*) AS combo_count, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE date BETWEEN %s AND %s GROUP BY caregiverid, clientid ORDER BY combo_count DESC", (first, last))
    combo = cursor.fetchall()

    return render_template("weekly_dashboard.html", first = first_formatted, last = last_formatted, created = created, closed = closed, reason = reason, combo = combo, reason_labels = reason_labels, reason_values = reason_values, count = count)

@app.route("/biweeklydashboard")
def biweekly_dashboard():
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")
    
    # same as weekly dashboard
    cursor = mydb.cursor(dictionary=True)

    # get today's date:
    today = date.today()
    first = today - timedelta(days=14)
    first_formatted = first.strftime("%A, %B %d, %Y")
    last = today
    last_formatted = last.strftime("%A, %B %d, %Y")

    count={}

    # get a list of all timesheet errors that have been created within the week
    cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE (sent = FALSE or received = FALSE) AND (date between %s AND %s)", (first, last))
    created = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) AS count FROM timesheet WHERE (sent = FALSE or received = FALSE) AND (date between %s AND %s)", (first, last))
    t_o_count = cursor.fetchone()
    count['week_open'] = t_o_count['count']

    # get a list of all timesheet errors that have been closed this week
    cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE received = TRUE AND (day_r between %s AND %s)", (first, last))
    closed = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) AS count FROM timesheet WHERE sent = TRUE AND received = TRUE AND (day_r between %s AND %s)", (first, last))
    t_c_count = cursor.fetchone()
    count['week_closed'] = t_c_count['count']

    # get a total number of outstanding timesheets
    cursor.execute("SELECT COUNT(*) AS outstanding FROM timesheet WHERE (sent = FALSE OR received = FALSE)")
    a = cursor.fetchone()
    count['outstanding'] = a['outstanding']
    cursor.execute("SELECT COUNT(*) AS send FROM timesheet WHERE sent = FALSE AND received = FALSE")
    a = cursor.fetchone()
    count['send'] = a['send']
    cursor.execute("SELECT COUNT(*) AS wait FROM timesheet WHERE sent = TRUE AND received = FALSE")
    a = cursor.fetchone()
    count['wait'] = a['wait']

    # get the total count of reasons for all timesheet errors made this week (for a pie chart)
    cursor.execute("SELECT reason, COUNT(*) AS reason_count FROM timesheet WHERE date between %s AND %s GROUP BY reason ORDER BY reason_count DESC", (first, last))
    reason = cursor.fetchall()
    reason_labels = [r["reason"] for r in reason]
    reason_values = [r["reason_count"] for r in reason]

    # get total count of caregiver/client combos
    cursor.execute("SELECT clientid, caregiverid, COUNT(*) AS combo_count, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid WHERE date BETWEEN %s AND %s GROUP BY caregiverid, clientid ORDER BY combo_count DESC", (first, last))
    combo = cursor.fetchall()

    return render_template("biweekly_dashboard.html", first = first_formatted, last = last_formatted, created = created, closed = closed, reason = reason, combo = combo, reason_labels = reason_labels, reason_values = reason_values, count = count)

@app.route("/edituser/<int:usernum>", methods = ["GET", "POST"])
def edit_user(usernum):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    # get userid of the person we're trying to edit info for
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM people WHERE usernum = %s", (usernum,))
    person = cursor.fetchone()

    if request.method == "POST":
        # takes in a username and password from a form
        fname = request.form.get("fname")
        lname = request.form.get("lname")

        if fname and lname:
            cursor.execute("UPDATE people SET fname = %s, lname = %s WHERE usernum = %s", (fname, lname, usernum))
            mydb.commit()
            flash("Updated user information successfully.", "success")
            return redirect("/contactlist")
        if fname:
            cursor.execute("UPDATE people SET fname = %s WHERE usernum = %s", (fname, usernum))
            mydb.commit()
            flash("Updated user information successfully.", "success")
            return redirect("/contactlist")
        if lname:
            cursor.execute("UPDATE people SET lname = %s WHERE usernum = %s", (lname, usernum))
            mydb.commit()
            flash("Updated user information successfully.", "success")
            return redirect("/contactlist")

    return render_template("update_user.html", person = person)

@app.route("/undo/<int:num>")
def undo_status(num):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    # get status of timesheet error
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM timesheet WHERE num = %s", (num,))
    status = cursor.fetchone()
    
    # if waiting:
    if status['sent'] and not status['received']:
        cursor.execute("UPDATE timesheet SET sent = 0 WHERE num = %s", (num,))
        flash("Your timesheet error status has been updated to 'Not Sent'.", "success")
    elif status['sent'] and status['received']:
        cursor.execute("UPDATE timesheet SET sent = 1, received = 0, type = NULL, day_r = NULL WHERE num = %s", (num,))
        flash("Your timesheet error status has been updated to 'Waiting'.", "success")
    mydb.commit()

    return redirect("/viewtimesheets")

@app.route("/home/undo/<int:num>")
def home_undo_status(num):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    # get status of timesheet error
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM timesheet WHERE num = %s", (num,))
    status = cursor.fetchone()
    
    # if waiting:
    if status['sent'] and not status['received']:
        cursor.execute("UPDATE timesheet SET sent = 0 WHERE num = %s", (num,))
        flash("Your timesheet error status has been updated to 'Not Sent'.", "success")
    elif status['sent'] and status['received']:
        cursor.execute("UPDATE timesheet SET sent = 1, received = 0, type = NULL, day_r = NULL WHERE num = %s", (num,))
        flash("Your timesheet error status has been updated to 'Waiting'.", "success")
    mydb.commit()

    return redirect("/")

@app.route("/calendar/undo/<int:num>")
def calendar_undo_status(num):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    # get status of timesheet error
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM timesheet WHERE num = %s", (num,))
    status = cursor.fetchone()
    
    # if waiting:
    if status['sent'] and not status['received']:
        cursor.execute("UPDATE timesheet SET sent = 0 WHERE num = %s", (num,))
        flash("Your timesheet error status has been updated to 'Not Sent'.", "success")
    elif status['sent'] and status['received']:
        cursor.execute("UPDATE timesheet SET sent = 1, received = 0, type = NULL, day_r = NULL WHERE num = %s", (num,))
        flash("Your timesheet error status has been updated to 'Waiting'.", "success")
    mydb.commit()

    return redirect("/calendar")



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
