# The Project
This project details the process of viewing/adding Timesheets, using a locally stored database

## The Database
Within the database, there are a couple of tables:

*People*
- UserID -- email(?), unique identifier that determines who a person is
- First Name
- Last Name
- Type of user (caregiver/admin/client)

*Client (Connected to the People Table)*
- ClientID (connects a client to the people table)
- CaregiverID (connects a caregiver to a client)
* **Each Client can have multiple Caregivers, and each Caregiver can have multiple clients*

*Admin (Connected to the People Table)*
- AdminID
- Password (allows them to login)

*Timesheet*
- ClientID (associated with the people table)
- CaregiverID (associated with the people table)
- Date
- Reason
- Timesheet sent (Y/N)
- Sent via E-Signature/Paper Timesheet
- Date Received
- *To determine a specific timesheet, we'll use a combination of Client IDs, CaregiverIDs, and the Date*

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

### Upcoming Tasks:
- create a timesheet error
- view all timesheet errors
- update information for all users (emails, names, etc.)
- be able to have the admin update their own password
### Additional features(?)
- create 2FA for changing your own password (to ensure security)
- Add search features for dropdowns (like assigning caregivers to a client)
- Turn the contact list into tabs (one for all users, another for clients, another for caregivers, and admin)

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
