# The Project
This project details the process of viewing/adding Timesheets, using a locally stored database

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

### Progress made so far:
**05/28/2026**:
- Created/formatted the database
- Added a login page, logout page, and create new user page
  
**05/29/2026**:
- Worked on creating a contact list
  - For each person in the contact list, you can view their names and emails (and is already hyperlinked to automatically email when clicked)
  - You can also delete each person (if there are no issues such as open timesheets for that person)
  - If a person is a client, you can view a list of their caregivers/their emails. You can also assign and delete client-caregiver relationships
- Fixed some bugs within the code to make it more secure (like requiring all fields for adding users and checking for login at each page of the website)
- Updated the database to match the new description for timesheets (removed the Timesheet #)

**06/02 & 06/03**:
- Able to create, update status to 'sent', and close a timesheet error
- Can view all timesheet errors
- Updated the database/schema to change the primary keys/use user numbers in links to make it more secure
- Fixed bugs with changing caregiver assignments
- Created an update password option 
- When a user logs in, they automatically see which timesheet errors still need to be sent or are still waiting for a response
- Created an option to view timesheet errors via a calendar (still very basic, needs to be updated w/pop-ups)
- Added a confirmation page before users are deleted
- Updated the view timesheets page to split up information into tabs based on status
  - Can also search for timesheet errors based on client, caregiver + date

**06/04**:
- Made the calendar interactive -- when clicking on the specific event, they can see the reason/update it as sent right away
- Create a pop-up during the create timesheet error
  - it should pop up if a timesheet error w/the same caregiver, client & date exists
  - should let the user know that a pre-existing timesheet error exists & the reason why
  - allow the user to decide whether to go through or cancel creating a new error 
- Turn the contact list into tabs (one for all users, another for clients, another for caregivers, and admin)
- Add search features for create_timesheet dropdowns

### Upcoming Tasks:
- When creating a timesheet error, based on the client that the admin picks the drop-down list of caregivers that client has should be automatically generated (and vice versa)
- Make the website look nice/usable (last task)

## HIPAA Considerations
- Admin passwords are hashed within the database (so they can't be viewed by anyone)
- Users get automatically logged out if they're inactive for 5 minutes
- Two options for storing the database:
  1. Everything is done locally (this means there can be multiple users/admin accounts, but it's all done on 1 laptop/computer, with code libraries installed that monitor/audits changes made)
     - Pros: No additional costs (don't have to pay any subscriptions)
     - Cons: Only one laptop can use it. If another person would want to use it on their own device, the original laptop would have to push the database to a service (like GitHub), and the second person would have to pull the database. You would need to constantly do things like pushing/pulling whenever changes are made
  2. Use a HIPAA-compliant database
     - Pros: Mutliple users can use it (if one laptop uses it, another laptop gets updated instantly)
     - Cons: Can be very expensive
