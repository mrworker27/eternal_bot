CREATE TABLE users (
    uid INT PRIMARY KEY, 
    username TEXT,
    first_name TEXT,
    last_name TEXT
);

CREATE TABLE settings (
    uid INT PRIMARY KEY,
    ask_task_interval INT DEFAULT (15 * 60),
    sleep_interval INT DEFAULT (15 * 60), 
    sleep_time INT DEFAULT (9 * 60 * 60),
    alarm_rate INT DEFAULT (30 * 60),
    time_zone INT DEFAULT (3 * 60)
);

CREATE TABLE state (
    uid INTEGER PRIMARY KEY,
    state TEXT DEFAULT "stop",
    sleep_id INT
);

CREATE TABLE ask_task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid INT,
    ask_time DATETIME,
    value INT DEFAULT 0 CHECK(value BETWEEN 0 AND 2),
    UNIQUE(uid, ask_time)
);

CREATE TABLE sleep_manager (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid INT,
    "begin" DATETIME,
    "end" DATETIME,
    sleep INT CHECK(sleep BETWEEN 0 AND 2),
    UNIQUE(uid, "begin", "end")
);

CREATE TABLE statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sleep_id INT,
    total INT,
    useful INT,
    domestic INT
);
