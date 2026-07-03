"""
Database connection and operations module
"""
import os
import psycopg
from psycopg import sql
import logging
from contextlib import contextmanager
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    """Database connection manager"""
    
    _instance = None
    _conn = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        self._conn = None
    
    def get_connection(self):
        """Get a database connection"""
        if self._conn is None or self._conn.closed:
            try:
                self._conn = psycopg.connect(Config.DATABASE_URL)
                logger.info("Database connection established")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise
        return self._conn
    
    @contextmanager
    def get_cursor(self):
        """Get a cursor from a connection"""
        conn = self.get_connection()
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
        with self.get_cursor() as cur:
            cur.execute(query, params or ())
            if fetch_one:
                result = cur.fetchone()
                if result:
                    # Get column names
                    columns = [desc[0] for desc in cur.description]
                    return dict(zip(columns, result))
                return None
            elif fetch_all:
                results = cur.fetchall()
                if results:
                    columns = [desc[0] for desc in cur.description]
                    return [dict(zip(columns, row)) for row in results]
                return []
            else:
                return cur.rowcount

# Create a singleton instance
db = Database()

def init_database():
    """Initialize database tables with issuance tracking"""
    logger.info("Initializing database tables...")
    
    # SQL to create members table with issuance tracking
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
        badge_issued BOOLEAN DEFAULT FALSE,
        badge_issued_date TIMESTAMP,
        badge_issued_by VARCHAR(100),
        badge_print_count INTEGER DEFAULT 0,
        last_printed TIMESTAMP,
        card_type VARCHAR(50) DEFAULT 'standard',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_member_number ON members(member_number);
    CREATE INDEX IF NOT EXISTS idx_national_id ON members(national_id);
    CREATE INDEX IF NOT EXISTS idx_telephone ON members(telephone);
    CREATE INDEX IF NOT EXISTS idx_full_name ON members(full_name);
    CREATE INDEX IF NOT EXISTS idx_group_stage ON members(group_stage_name);
    CREATE INDEX IF NOT EXISTS idx_badge_issued ON members(badge_issued);
    
    -- Create issuance log table
    CREATE TABLE IF NOT EXISTS badge_issuance_log (
        id SERIAL PRIMARY KEY,
        member_id INTEGER REFERENCES members(id),
        issued_by VARCHAR(100),
        issued_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        print_format VARCHAR(20),
        print_quality VARCHAR(20),
        notes TEXT
    );
    """
    
    try:
        with db.get_cursor() as cur:
            cur.execute(create_table_sql)
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
        date_registered, qr_code_data, badge_image,
        badge_issued, badge_issued_date, badge_issued_by
    ) VALUES (
        %s, %s, %s, %s,
        %s, %s, %s,
        %s, %s,
        %s, %s,
        %s, %s, %s,
        %s, %s, %s
    ) RETURNING id;
    """
    with db.get_cursor() as cur:
        cur.execute(query, (
            data['member_number'],
            data['full_name'],
            data['national_id'],
            data['telephone'],
            data.get('passport_photo'),
            data.get('group_stage_name'),
            data.get('chairman_name'),
            data.get('chairman_phone'),
            data.get('motorcycle_registration'),
            data.get('next_of_kin_name'),
            data.get('next_of_kin_phone'),
            data.get('date_registered'),
            data.get('qr_code_data'),
            data.get('badge_image'),
            data.get('badge_issued', False),
            data.get('badge_issued_date'),
            data.get('badge_issued_by')
        ))
        return cur.fetchone()[0]

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
    
    with db.get_cursor() as cur:
        cur.execute(query, tuple(values))
        result = cur.fetchone()
        return result[0] if result else None

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

def log_badge_issuance(member_id, issued_by, print_format, print_quality, notes=None):
    """Log badge issuance"""
    query = """
    INSERT INTO badge_issuance_log (member_id, issued_by, print_format, print_quality, notes)
    VALUES (%s, %s, %s, %s, %s)
    """
    with db.get_cursor() as cur:
        cur.execute(query, (member_id, issued_by, print_format, print_quality, notes))
        return cur.rowcount > 0

def get_issuance_log(member_id, limit=10):
    """Get issuance log for a member"""
    query = """
    SELECT * FROM badge_issuance_log 
    WHERE member_id = %s 
    ORDER BY issued_date DESC 
    LIMIT %s
    """
    return db.execute_query(query, (member_id, limit), fetch_all=True)

def get_unissued_members(limit=None):
    """Get members who haven't been issued badges"""
    query = "SELECT * FROM members WHERE badge_issued = FALSE ORDER BY created_at ASC"
    if limit:
        query += f" LIMIT {limit}"
    return db.execute_query(query, fetch_all=True)

def get_issued_members(limit=None):
    """Get members who have been issued badges"""
    query = "SELECT * FROM members WHERE badge_issued = TRUE ORDER BY badge_issued_date DESC"
    if limit:
        query += f" LIMIT {limit}"
    return db.execute_query(query, fetch_all=True)

# Initialize database on module import
init_database()
