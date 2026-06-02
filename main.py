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

        # check if the email already exists first
        cursor.execute("SELECT * FROM people WHERE userid = %s", (username,))
        check = cursor.fetchall()
        if check:
            flash("A user with the same email already exists.", "error")
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
        return redirect("/")
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

    for item in contacts:
        if item["type"] == "Client":
            cursor.execute("SELECT people.fname, people.lname, people.userid, clientid FROM clients INNER JOIN people ON caregiverid = userid WHERE clientid = %s", (item['userid'],))
            item["caregiver"] = cursor.fetchall()

    return render_template("contact_list.html", contacts = contacts)

@app.route("/deleteuser/<path:email>")
def delete_user(email):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    # first check if the person that is trying to be deleted is the user
    if email == session['user']['username']:
        flash("You cannot delete yourself.", "error")
        return redirect('/contactlist')
    # next check if the user being deleted has a timesheet that is still open:
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM timesheet WHERE (clientid = %s OR caregiverid = %s) AND received = FALSE", (email, email))
    open_check = cursor.fetchall()
    if open_check:
        # this means that there exists a timesheet error that is still open/not closed yet!
        flash("You can not delete a user with an open timesheet error.", "error")
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

@app.route("/addcaregiver/<usernum>", methods = ["GET"])
def assign_caregiver(usernum):
    # check if user is logged in:
    if 'user' not in session:
        return redirect("/login")

    cursor = mydb.cursor(dictionary=True)
    # generate a list of caregivers (that aren't already assigned to the client)
    cursor.execute("SELECT * FROM people WHERE usernum = %s", (usernum,))
    client = cursor.fetchone()
    email = client['userid']

    cursor.execute("SELECT DISTINCT people.fname, people.lname, people.userid FROM people WHERE people.userid IN (SELECT caregiverid FROM clients) AND people.userid NOT IN (SELECT caregiverid FROM clients WHERE clientid = %s)", (email,))
    c_list = cursor.fetchall()

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
            flash("You can not remove a client-caregiver relationship with an open timesheet error.", "error")
            return redirect(url_for("assign_caregiver", email=email))
        else:
            # delete any client-caregiver relationships
            cursor.execute("DELETE FROM clients WHERE clientid = %s AND caregiverid = %s", (email, remove_caregiver))
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
        client = request.form.get("client")
        caregiver = request.form.get("caregiver")
        reason = request.form.get("reason")
        date = request.form.get("date")
        cursor.execute("SELECT * FROM timesheet WHERE clientid = %s AND caregiverid = %s AND date = %s", (client, caregiver, date))
        check = cursor.fetchall()
        if check:
            flash("A timesheet error already exists for this client, caregiver and date.", "error")
            return redirect("/viewtimesheets")
        else:
            cursor.execute("INSERT INTO timesheet (clientid, caregiverid, date, reason) VALUES (%s, %s, %s, %s)", (client, caregiver, date, reason))
            mydb.commit()
            flash("You have successfully created a timesheet error!", "success")
            return redirect("/viewtimesheets")

    return render_template("create_timesheet.html", cl_list = cl_list, cr_list = cr_list)
    
@app.route("/viewtimesheets")
def view_timesheets():
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT timesheet.*, client.fname AS clfname, client.lname AS cllname, caregiver.fname AS crfname, caregiver.lname AS crlname FROM timesheet INNER JOIN people AS client ON timesheet.clientid = client.userid INNER JOIN people AS caregiver ON timesheet.caregiverid = caregiver.userid")
    info = cursor.fetchall()



    return render_template("view_timesheets.html", info = info)




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
