
PRAGMA foreign_keys=off;

BEGIN TRANSACTION;

ALTER TABLE user RENAME TO taciturn_user;

ALTER TABLE app_account RENAME TO _old_app_account;
ALTER TABLE blacklist RENAME TO _old_blacklist;
ALTER TABLE follower RENAME TO _old_follower;
ALTER TABLE following RENAME TO _old_following;
ALTER TABLE unfollowed RENAME TO _old_unfollowed;
ALTER TABLE whitelist RENAME TO _old_whitelist;


CREATE TABLE app_account (
	id INTEGER NOT NULL,
	application_id INTEGER,
	taciturn_user_id INTEGER,
	established DATETIME NOT NULL,
	name VARCHAR(500) NOT NULL,
	password VARCHAR(500) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(application_id) REFERENCES application (id),
	FOREIGN KEY(taciturn_user_id) REFERENCES taciturn_user (id)
);

CREATE TABLE blacklist (
	id INTEGER NOT NULL,
	application_id INTEGER,
	taciturn_user_id INTEGER,
	established DATETIME NOT NULL,
	name VARCHAR(100) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(application_id) REFERENCES application (id),
	FOREIGN KEY(taciturn_user_id) REFERENCES taciturn_user (id)
);

CREATE TABLE follower (
	id INTEGER NOT NULL,
	application_id INTEGER,
	taciturn_user_id INTEGER,
	established DATETIME NOT NULL,
	name VARCHAR(100) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(application_id) REFERENCES application (id),
	FOREIGN KEY(taciturn_user_id) REFERENCES taciturn_user (id)
);

CREATE TABLE following (
	id INTEGER NOT NULL,
	application_id INTEGER,
	taciturn_user_id INTEGER,
	established DATETIME NOT NULL,
	name VARCHAR(100) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(application_id) REFERENCES application (id),
	FOREIGN KEY(taciturn_user_id) REFERENCES taciturn_user (id)
);

CREATE TABLE unfollowed (
	id INTEGER NOT NULL,
	application_id INTEGER,
	taciturn_user_id INTEGER,
	established DATETIME NOT NULL,
	name VARCHAR(100) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(application_id) REFERENCES application (id),
	FOREIGN KEY(taciturn_user_id) REFERENCES taciturn_user (id)
);

CREATE TABLE whitelist (
	id INTEGER NOT NULL,
	application_id INTEGER,
	taciturn_user_id INTEGER,
	established DATETIME NOT NULL,
	name VARCHAR(100) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(application_id) REFERENCES application (id),
	FOREIGN KEY(taciturn_user_id) REFERENCES taciturn_user (id)
);

INSERT INTO app_account SELECT * FROM _old_app_account;
INSERT INTO blacklist SELECT * FROM _old_blacklist;
INSERT INTO follower SELECT * FROM _old_follower;
INSERT INTO following SELECT * FROM _old_following;
INSERT INTO unfollowed SELECT * FROM _old_unfollowed;
INSERT INTO whitelist SELECT * FROM _old_whitelist;

DROP TABLE _old_app_account;
DROP TABLE _old_blacklist;
DROP TABLE _old_follower;
DROP TABLE _old_following;
DROP TABLE _old_unfollowed;
DROP TABLE _old_whitelist;


COMMIT;

PRAGMA foreign_keys=on;
