import sqlite3
import datetime

class TBindedDB:
    def __init__(self, context, db_name):
        self.context = context
        self.db_name = db_name

    def connection(self):
        return sqlite3.connect(self.db_name)

class TInterfaceDB:
    @staticmethod
    def get_config(db, uid):
        c = db.cursor()
        args = (
            uid, 
        )
        c.execute(
                """
                SELECT ask_task_interval, sleep_time, alarm_rate, sleep_interval, time_zone
                FROM settings WHERE (uid = ?);
                """, args
        )
        return c.fetchone()

    @staticmethod
    def update_config(
        db,
        uid,
        ask_task_interval = None,
        sleep_interval = None,
        sleep_time = None,
        alarm_rate = None,
        time_zone = None
    ):
        c = db.cursor()
        if ask_task_interval is not None:
            args = (
                ask_task_interval,
                uid
            )
            c.execute(
                    """
                        UPDATE Settings SET ask_task_interval = ? WHERE uid = ?;
                    """, args
            )
        if sleep_interval is not None:
            args = (
                sleep_interval,
                uid
            )
            c.execute(
                    """
                        UPDATE Settings SET sleep_interval = ? WHERE uid = ?;
                    """, args
            )
        if sleep_time is not None:
            args = (
                sleep_time,
                uid
            )
            c.execute(
                    """
                        UPDATE Settings SET sleep_time = ? WHERE uid = ?;
                    """, args
            )
        if alarm_rate is not None:
            args = (
                alarm_rate,
                uid
            )
            c.execute(
                    """
                        UPDATE Settings SET alarm_rate = ? WHERE uid = ?;
                    """, args
            )
        if time_zone is not None:
            args = (
                time_zone,
                uid
            )
            c.execute(
                    """
                        UPDATE Settings SET time_zone = ? WHERE uid = ?;
                    """, args
            )

        db.commit()

    @staticmethod
    def time_cast(db, uid, t):
        if isinstance(t, str):
            return t
        (*_, time_zone) = TInterfaceDB.get_config(db, uid)
        new_t = t + datetime.timedelta(seconds = time_zone * 60)
        return new_t
    
    @staticmethod
    def time_to_utc(db, uid, t):
        if isinstance(t, str):
            return t
        
        (*_, time_zone) = TInterfaceDB.get_config(db, uid)
        new_t = t + datetime.timedelta(seconds = -time_zone * 60)
        return new_t
    

    @staticmethod
    def insert_awake(db, uid, begin):
        c = db.cursor()
        cast_begin = TInterfaceDB.time_cast(db, uid, begin)
        args = (
            uid,
            cast_begin,
            0
        ) 
        c.execute(
                """
                    INSERT INTO sleep_manager(uid, "begin", sleep) VALUES (?, ?, ?);
                """, args
        );
        db.commit()
    
    @staticmethod
    def insert_sleep(db, uid, begin):
        c = db.cursor()
        cast_begin = TInterfaceDB.time_cast(db, uid, begin)
        args = (
            uid,
            cast_begin,
            1
        )
        c.execute(
                """
                    INSERT INTO sleep_manager(uid, "begin", sleep) VALUES (?, ?, ?);
                """, args
        );
        db.commit()
    
    @staticmethod
    def get_sleep_by_end(db, uid, end):
        return TInterfaceDB.get_segment_by_end(db, uid = uid, end = end, sleep = 1)
    
    @staticmethod
    def get_awake_by_end(db, uid, end):
        return TInterfaceDB.get_segment_by_end(db, uid = uid, end = end, sleep = 0)

    @staticmethod
    def get_sleep_by_begin(db, uid, begin):
        return TInterfaceDB.get_segment_by_begin(db, uid = uid, begin = begin, sleep = 1)
    
    @staticmethod
    def get_awake_by_begin(db, uid, begin):
        return TInterfaceDB.get_segment_by_begin(db, uid = uid, begin = begin, sleep = 0)
    
    @staticmethod
    def get_segment_by_end(db, uid, end, sleep):
        c = db.cursor()
        cast_end = TInterfaceDB.time_cast(db, uid, end)
        args = (
            uid,
            cast_end,
            sleep
        )
        c.execute(
                """
                    SELECT "begin", "end", id FROM sleep_manager 
                    WHERE uid = ? AND "end" = ? AND sleep = ?;
                """, args
        )

        res = c.fetchone()
        return res
    
    @staticmethod
    def get_segment_by_begin(db, uid, begin, sleep):
        c = db.cursor()
        cast_begin = TInterfaceDB.time_cast(db, uid, begin)
        args = (
            uid,
            cast_begin,
            sleep
        )
        c.execute(
                """
                    SELECT "begin", "end", id FROM sleep_manager 
                    WHERE uid = ? AND "begin" = ? AND sleep = ?;
                """, args
        )

        res = c.fetchone()
        return res
    
    @staticmethod
    def get_latest_sleep(db, uid):
        return get_latest_segment(db, uid, 1)

    @staticmethod
    def get_latest_awake(db, uid):
        return get_latest_segment(db, uid, 0)
    
    @staticmethod
    def get_latest_segment(db, uid, sleep):
        c = db.cursor()
        args = (
            uid,
            sleep
        )
        c.execute(
                """
                    SELECT MAX("begin"), "end", id FROM sleep_manager
                    WHERE uid = ? AND sleep = ?;
                """, args
        )
        res = c.fetchone()
        return res
   
    @staticmethod
    def get_segment_by_id(db, uid, sleep_id, sleep):
        c = db.cursor()
        args = (
            uid,
            sleep_id,
            sleep
        )
        c.execute(
                """
                    SELECT "begin", "end", id FROM sleep_manager
                    WHERE uid = ? AND id = ? AND sleep = ?;
                """, args
        )
        res = c.fetchone()
        return res


    @staticmethod
    def get_sleep_by_id(db, uid, sleep_id):
        return TInterfaceDB.get_segment_by_id(db, uid, sleep_id, 1)
    
    @staticmethod
    def get_awake_by_id(db, uid, sleep_id):
        return TInterfaceDB.get_segment_by_id(db, uid, sleep_id, 0)
    
    @staticmethod
    def update_segment_by_begin(db, uid, begin, end, key_begin, sleep):
        c = db.cursor()
        cast_begin = TInterfaceDB.time_cast(db, uid, begin)
        cast_end   = TInterfaceDB.time_cast(db, uid, end)
        cast_key   = TInterfaceDB.time_cast(db, uid, key_begin)
        
        args = (
            cast_begin,
            cast_end,
            uid,
            cast_key,
            sleep
        )
        c = db.cursor()
        c.execute(
                """
                UPDATE sleep_manager SET "begin" = ?, "end" = ? 
                WHERE uid = ? AND "begin" = ? AND sleep = ?
                """, args
        )
        db.commit()

    @staticmethod
    def update_sleep_by_begin(db, uid, begin, end, key_begin):
        TInterfaceDB.update_segment_by_begin(db, uid, begin, end, key_begin, 1)
    
    @staticmethod
    def update_awake_by_begin(db, uid, begin, end, key_begin):
        TInterfaceDB.update_segment_by_begin(db, uid, begin, end, key_begin, 0)

    @staticmethod
    def insert_ask_task(db, uid, ask_time, value):
        c = db.cursor()
        cast_ask_time = TInterfaceDB.time_cast(db, uid, ask_time)  
        args = (
            uid,
            cast_ask_time,
            value
        )
        c.execute("INSERT INTO ask_task(uid, ask_time, value) VALUES (?, ?, ?);", args);
        db.commit()
    
    @staticmethod
    def update_ask_task_by_time(db, uid, ask_time, value, key_time):
        c = db.cursor()
        cast_ask_time = TInterfaceDB.time_cast(db, uid, ask_time)  
        cast_key_time = TInterfaceDB.time_cast(db, uid, key_time)  
        args = (
            value,
            cast_ask_time, 
            cast_key_time,
            uid
        )
        c.execute(
                """
                UPDATE ask_task SET value = ?, ask_time = ?
                WHERE ask_time = ? AND uid = ?;
                """, args
        )
        db.commit()

    @staticmethod
    def get_all_ask_tasks(db, uid):
        c = db.cursor()
        args = (
            uid,
        )
        c.execute(
                """
                SELECT ask_time, value FROM ask_task WHERE uid = ?;
                """, args

        )
        return c.fetchall()

    @staticmethod
    def insert_statistics(db, sleep_id, total, useful, domestic):
        c = db.cursor()
        args = (
            sleep_id,
            total,
            useful,
            domestic
        )
        c.execute(
                """
                INSERT INTO statistics(sleep_id, total, useful, domestic) VALUES (?, ?, ?, ?);
                """, args
        )
        db.commit()

    @staticmethod
    def update_statistics_by_sleep(db, sleep_id, total, useful, domestic):
        c = db.cursor()
        args = (
            total,
            useful,
            domestic,
            sleep_id
        )
        c.execute(
                """
                UPDATE statistics SET total = ?, useful = ?, domestic = ? WHERE sleep_id = ?;
                """, args
        )
        db.commit()

    @staticmethod
    def calc_statistics(db, uid, begin, end):
        c = db.cursor()
        cast_begin = TInterfaceDB.time_cast(db, uid, begin)  
        cast_end   = TInterfaceDB.time_cast(db, uid, end)  
        args = (
            uid,
            cast_begin,
            cast_end
        )
        c.execute(
                """
                SELECT COUNT(value) FROM ask_task WHERE uid = ? AND ask_time BETWEEN ? AND ?;
                """, args
        )
        
        total = c.fetchone()[0]
        
        c.execute(
                """
                SELECT COUNT(value) FROM ask_task 
                WHERE uid = ? AND ask_time BETWEEN ? AND ? AND value = 2;
                """, args
        )
        
        useful = c.fetchone()[0]
        
        c.execute(
                """
                SELECT COUNT(value) FROM ask_task 
                WHERE uid = ? AND ask_time BETWEEN ? AND ? AND value = 1;
                """, args
        )
        
        domestic = c.fetchone()[0]
        useless = total - useful - domestic
        
        return (total, useful, domestic, useless)
    
    @staticmethod
    def get_all_statistics(db, uid):
        c = db.cursor()
        args = (
            uid,
        )
        c.execute(
                """
                SELECT total, useful, domestic, sleep_id, "begin", "end" FROM 
                (SELECT * FROM statistics S INNER JOIN sleep_manager M ON S.sleep_id = M.id)
                WHERE uid = ?
                """, args
        )
        res = c.fetchall()
        return res

    @staticmethod
    def get_user_state(db, uid):
        c = db.cursor()
        args = (
            uid,
        )
        c.execute(
                """
                SELECT uid, state, sleep_id FROM state WHERE uid = ?;
                """, args
        )
        res = c.fetchone()
        return res

    @staticmethod
    def update_user_state(db, uid, state, sleep_id):
        c = db.cursor()
        args = (
            state,
            sleep_id,
            uid
        )
        c.execute(
                """
                UPDATE state SET state = ?, sleep_id = ? WHERE uid = ?
                """, args
        )
        db.commit()
