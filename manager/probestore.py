#
# Message session handling
#

import threading
import logging
import sqlite3
import time

import config
from probe import Probe
from timespec import Timespec

class ProbeStore:
    """ Probe storage """

    lock_db = None
    lock_buf = None
    logger = None
    config = None
    db_conn = None
    db_curs = None
    buf = []

    def __init__(self):
        """Constructor """

        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config.Config()
        self.lock_db = threading.Lock()
        self.lock_buf = threading.Lock()

        self.logger.debug("Created instance")

        # open database connection
        try:
            self.db_conn = sqlite3.connect(self.config.get_param("/config/dbpath"))
            self.db_conn.row_factory = sqlite3.Row
            self.db_curs = self.db_conn.cursor()
            self.db_curs.execute("CREATE TABLE IF NOT EXISTS probes (" + 
                "session_id INTEGER," +
                "seq INTEGER," + 
                "t1_sec INTEGER," + 
                "t1_nsec INTEGER," + 
                "t2_sec INTEGER," + 
                "t2_nsec INTEGER," + 
                "t3_sec INTEGER," + 
                "t3_nsec INTEGER," + 
                "t4_sec INTEGER," + 
                "t4_nsec INTEGER," + 
                "state TEXT" + 
                ");")
            self.db_curs.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON probes(session_id)")
            self.db_conn.commit()
            
        except Exception, e:
            self.logger.critical("Unable to open database: %s" % e)
            raise ProbeStoreError("Unable to open database: %s" % e)

    def insert(self, probe):
        """ Insert probe """

        self.lock_buf.acquire()

        # insert stuff
        self.logger.debug("Received probe; id: %d seq: %d rtt: %s" % (probe.msess_id, probe.seq, probe.rtt()))
        self.buf.append(probe)

        self.lock_buf.release()

    def flush(self):
        """ Flush received probes to database """    

        self.logger.debug("Flushing probes to database")

        # create copy of buffer to reduce time it is locked
        self.lock_buf.acquire()
        tmpbuf = self.buf[:]
        self.buf = list()
        self.lock_buf.release()

        # write copied probes to database
        self.lock_db.acquire()
        
        sql = str("INSERT INTO probes " +
            "(session_id, seq, state, t1_sec, t1_nsec, " +
            "t2_sec, t2_nsec, t3_sec, t3_nsec, " +
            "t4_sec, t4_nsec) VALUES " +
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
        for p in tmpbuf:
            try:
                self.db_curs.execute(sql, 
                    (p.msess_id, p.seq, p.state,
                    p.t1.sec, p.t1.nsec, p.t2.sec, p.t2.nsec,
                    p.t2.sec, p.t3.nsec, p.t4.sec, p.t4.nsec),
                )
            except Exception, e:
                self.logger.error("Unable to flush probe to database: %s" % e)
        try:
            self.db_conn.commit()
        except Exception, e:
            self.logger.error("Unable to commit flushed probes to database: %s" % e)
        self.lock_db.release()

    def delete(self, age):
        """ Deletes saved data of age 'age' and older. """
    
        self.logger.info("Deleting old data from database.")

        now = int(time.time())

        self.lock_db.acquire()
        sql = "DELETE FROM probes WHERE t1_sec < ?"
        try:
            self.db_curs.execute(sql, now - age)
            self.db_conn.commit()
        except Exception, e:
            self.logger.error("Unable to delete old data: %s" % e)
        self.lock_db.release()

class ProbeStoreError(Exception):
    pass