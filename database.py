"""
Database connection and operations module
"""
import os
import psycopg2
from psycopg2 import pool, sql, extras
from psycopg2.extras import RealDictCursor
import logging
from contextlib import contextmanager
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    """Database connection manager with connection pooling"""
    
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._pool is None:
            self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize connection pool"""
        try:
            self._pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=Config.DATABASE_URL,
                sslmode='require'
            )
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        except Exception as e:
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                self._pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, cursor_factory=None):
        """Get a cursor from a connection"""
        with self.get_connection() as conn:
            if cursor_factory:
                cur = conn.cursor(cursor_factory=cursor_factory)
            else:
                cur = conn.cursor()
            try:
                yield cur
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database operation error: {e}")
                raise
            finally:
                cur.close()
    
    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        """Execute a query and return results"""
        with self.get_cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            if fetch_one:
                return cur.fetchone()
            elif fetch_all:
                return cur.fetchall()
            else:
                return cur.rowcount

# Create a singleton instance
db = Database()

def init_database():
    """Initialize database tables"""
    logger.info("Initializing database tables...")
    
    # SQL to create members table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS members (
        id SERIAL PRIMARY KEY,
        member_number VARCHAR(50) UNIQUE NOT NULL,
        full_name VARCHAR(200) NOT NULL,
        national_id VARCHAR(20) UNIQUE NOT NULL,
        telephone VARCHAR(20) NOT NULL,
        passport_photo VARCHAR(500),
        group_stage_name VARCHAR(200),
        chairman_name VARCHAR(200),
        chairman_phone VARCHAR(20),
        motorcycle_registration VARCHAR(50),
        next_of_kin_name VARCHAR(200),
        next_of_kin_phone VARCHAR(20),
        date_registered DATE DEFAULT CURRENT_DATE,
        qr_code_data TEXT,
        badge_image VARCHAR(500),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_member_number ON members(member_number);
    CREATE INDEX IF NOT EXISTS idx_national_id ON members(national_id);
    CREATE INDEX IF NOT EXISTS idx_telephone ON members(telephone);
    CREATE INDEX IF NOT EXISTS idx_full_name ON members(full_name);
    CREATE INDEX IF NOT EXISTS idx_group_stage ON members(group_stage_name);
    """
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_table_sql)
                conn.commit()
                logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise

def create_member(data):
    """Insert a new member into the database"""
    query = """
    INSERT INTO members (
        member_number, full_name, national_id, telephone,
        passport_photo, group_stage_name, chairman_name,
        chairman_phone, motorcycle_registration,
        next_of_kin_name, next_of_kin_phone,
        date_registered, qr_code_data, badge_image
    ) VALUES (
        %(member_number)s, %(full_name)s, %(national_id)s, %(telephone)s,
        %(passport_photo)s, %(group_stage_name)s, %(chairman_name)s,
        %(chairman_phone)s, %(motorcycle_registration)s,
        %(next_of_kin_name)s, %(next_of_kin_phone)s,
        %(date_registered)s, %(qr_code_data)s, %(badge_image)s
    ) RETURNING id;
    """
    with db.get_cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, data)
        return cur.fetchone()['id']

def get_member(member_id):
    """Get a member by ID"""
    query = "SELECT * FROM members WHERE id = %s"
    return db.execute_query(query, (member_id,), fetch_one=True)

def get_member_by_number(member_number):
    """Get a member by member number"""
    query = "SELECT * FROM members WHERE member_number = %s"
    return db.execute_query(query, (member_number,), fetch_one=True)

def get_member_by_national_id(national_id):
    """Get a member by national ID"""
    query = "SELECT * FROM members WHERE national_id = %s"
    return db.execute_query(query, (national_id,), fetch_one=True)

def get_member_by_telephone(telephone):
    """Get a member by telephone"""
    query = "SELECT * FROM members WHERE telephone = %s"
    return db.execute_query(query, (telephone,), fetch_one=True)

def get_all_members(limit=50, offset=0, search=None):
    """Get all members with pagination and search"""
    query = "SELECT * FROM members"
    params = []
    
    if search:
        query += " WHERE full_name ILIKE %s OR member_number ILIKE %s OR national_id ILIKE %s OR telephone ILIKE %s"
        search_pattern = f"%{search}%"
        params = [search_pattern, search_pattern, search_pattern, search_pattern]
    
    query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    return db.execute_query(query, tuple(params), fetch_all=True)

def get_members_count(search=None):
    """Get total number of members"""
    query = "SELECT COUNT(*) as count FROM members"
    params = []
    
    if search:
        query += " WHERE full_name ILIKE %s OR member_number ILIKE %s OR national_id ILIKE %s OR telephone ILIKE %s"
        search_pattern = f"%{search}%"
        params = [search_pattern, search_pattern, search_pattern, search_pattern]
    
    result = db.execute_query(query, tuple(params), fetch_one=True)
    return result['count'] if result else 0

def update_member(member_id, data):
    """Update a member's information"""
    set_clauses = []
    values = []
    
    for key, value in data.items():
        if value is not None:
            set_clauses.append(f"{key} = %s")
            values.append(value)
    
    values.append(member_id)
    query = f"""
    UPDATE members 
    SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
    WHERE id = %s
    RETURNING id
    """
    
    with db.get_cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, tuple(values))
        return cur.fetchone()

def delete_member(member_id):
    """Delete a member"""
    query = "DELETE FROM members WHERE id = %s RETURNING id"
    result = db.execute_query(query, (member_id,), fetch_one=True)
    return result is not None

def get_recent_members(limit=5):
    """Get recent members"""
    query = "SELECT * FROM members ORDER BY created_at DESC LIMIT %s"
    return db.execute_query(query, (limit,), fetch_all=True)

def search_members_by_qr(qr_data):
    """Search members by QR code data"""
    query = "SELECT * FROM members WHERE qr_code_data = %s"
    return db.execute_query(query, (qr_data,), fetch_one=True)

# Initialize database on module import
init_database()
