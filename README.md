# The Project
This project details the process of viewing/adding Timesheet Errors, using a locally stored database for Home & Happiness Home Care LLC.
Within the project, there are specific elements.

An admin can perform the following tasks:
- Be able to log in and update their password
- Be able to add or view contacts (such as clients, caregivers, or other admin)
- Be able to add, view timesheet errors, and update their status. Admin can view timesheet errors with one of three ways:
     - On the homepage, admin can see a list of timesheet errors that need to be sent out or closed.
     - There is a specific "View Timesheet Errors" page where admin can view all timesheet errors that need to be sent, are waiting for a response, or closed.
     - There is a calendar page, where admin can see the day a timesheet error occurred, with events color-coded by their status.

[**Demo Video**](https://drive.google.com/file/d/1317FOkAJP8hUyfTENrVzBB4Z_Am-c5ID/view?usp=sharing)

## The Database
Within the database, there are a couple of tables:

*People*
- UserID -- email or phone number, unique identifier that determines who a person is
- First Name
- Last Name
- Type of user (caregiver/admin/client)
- Usernum (this makes sure that if we visit a link to perform something, emails/phone numbers aren't showing up)

*Client (Connected to the People Table)*
- ClientID (connects a client to the people table)
- CaregiverID (connects a caregiver to a client)
* **Each Client can have multiple Caregivers, and each Caregiver can have multiple clients*

*Admin (Connected to the People Table)*
- AdminID
- Password (allows them to login)

*Timesheet*
- TimesheetNum (this number automatically increases every time we add a new timesheet)
- ClientID (associated with the people table)
- CaregiverID (associated with the people table)
- Date
- Reason
- Timesheet sent (Y/N)
- Timesheet received (Y/N)
- Sent via E-Signature/Paper Timesheet
- Date Received
- **Since someone can have 2 shifts w/the same client on the same day, we'll just use the TimesheetNum to be the primary key*

## The Website
The website, which can only be accessed by admin, can perform these functions:
- Update their own info (name/password)
- Add users (admin, clients, or caregivers)
- Assign or change client/caregiver assignments
- Create/edit/close timesheets
- View timesheets

## HIPAA Considerations
- Admin passwords are hashed within the database (so they can't be viewed by anyone)
- Users get automatically logged out if they're inactive for 5 minutes
- Two options for storing the database:
  1. Local database (this means there can be multiple users/admin accounts, but it's all done on 1 laptop/computer, with code libraries installed that monitor/audits changes made)
     - Pros: No additional costs (don't have to pay any subscriptions for using a web-database)
     - Cons: Only one laptop can use it at a time. If another person would want to use it on their own device, the original laptop would have to push the database to a service (like GitHub), and the second person would have to pull the database. You would need to constantly do things like pushing/pulling whenever changes are made, and this can be hard for anyone who isn't used to coding
  2. Use a HIPAA-compliant database (examples include AWS RDS or Microsoft Azure)
     - Pros: Mutliple users can use it (if one laptop uses updates the database, another laptop gets the change instantly)
     - Cons: Can be very expensive
       - Some ideas about cost: The cheapest option would be an Amazon RDS MySQL (or AWS) or Microsoft Azure database, which gives you a free BAA, and you pay based on how much you use it. As an estimation, it would be $15-$20/month.
