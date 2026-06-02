-- Active: 1779985622938@@127.0.0.1@3306@mysql

CREATE DATABASE IF NOT EXISTS project
    DEFAULT CHARACTER SET = 'utf8mb4';
USE project;
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS people;
CREATE TABLE people (
  userid    varchar(254) not null,
  fname     varchar(30),
  lname     varchar(30),
  type      varchar(10),
  usernum   INTEGER AUTO_INCREMENT,
  unique key (usernum),
  primary key (userid)
);

DROP TABLE IF EXISTS clients;
CREATE TABLE clients (
  clientid      varchar(254),
  caregiverid   varchar(254),
  primary key (clientid, caregiverid),
  foreign key (clientid) references people(userid),
  foreign key (caregiverid) references people(userid)
);

DROP TABLE IF EXISTS admin;
CREATE TABLE admin (
  adminid     varchar(254),
  password    varchar(255)
);

DROP TABLE IF EXISTS timesheet;
CREATE TABLE timesheet (
  clientid      varchar(254),
  caregiverid   varchar(254),
  date          DATE,
  reason        varchar(50),
  sent          BOOLEAN DEFAULT FALSE,
  received      BOOLEAN DEFAULT FALSE,
  type          varchar(50),
  day_r         DATE,
  num           INTEGER AUTO_INCREMENT,
  primary key (clientid, caregiverid, date),
  unique key (num),
  foreign key (clientid) references people(userid),
  foreign key (caregiverid) references people(userid)
);


-- adding a test admin (for logging in)
INSERT INTO people VALUES ('admin@gmail.com', 'Test', 'Admin', 'Admin', 1);
INSERT INTO admin VALUES ('admin@gmail.com', 'pass');

-- adding a test client and 2 caregivers
INSERT INTO people VALUES ('client@gmail.com', 'Test', 'Client', 'Client', 2);
INSERT INTO people VALUES ('caregiver1@gmail.com', 'Test1', 'Caregiver', 'Caregiver', 3);
INSERT INTO people VALUES ('caregiver2@gmail.com', 'Test2', 'Caregiver', 'Caregiver', 4);
INSERT INTO clients VALUES ('client@gmail.com', 'caregiver1@gmail.com');
INSERT INTO clients VALUES ('client@gmail.com', 'caregiver2@gmail.com');
--adding a timesheet error
INSERT INTO timesheet VALUES ('client@gmail.com', 'caregiver1@gmail.com', '2026-05-28', 'Out of window clock-out', FALSE, FALSE, NULL, NULL, 1);