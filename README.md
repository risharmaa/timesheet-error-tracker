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
- TimesheetID (Number associated with a specific timesheet)
- ClientID (associated with the people table)
- CaregiverID (associated with the people table)
- Date
- Reason
- Timesheet sent (Y/N)
- Sent via E-Signature/Paper Timesheet
- Date Received

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

## HIPAA Considerations
- Admin passwords are hashed within the database (so they can't be viewed by anyone)
- Users get automatically logged out if they're inactive for 5 minutes
- Two options for storing the database:
  1. Everything is done locally (this means there can be multiple users/admin accounts, but it's all done on 1 laptop/computer, with code libraries installed that monitor/audits changes made)
     - Pros: No additional costs (don't have to pay any subscriptions)
     - Cons: Only one laptop/user can use it at a time
  2. Use a HIPAA-compliant database
     - Pros: Mutliple users can use it (if one laptop uses it, another laptop gets updated instantly)
     - Cons: Can be very expensive
