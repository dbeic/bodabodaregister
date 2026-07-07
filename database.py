"""
Database connection and operations module with authentication support
"""
import os
import psycopg
import logging
import time
from contextlib import contextmanager
from config import Config
from flask_bcrypt import Bcrypt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Bcrypt for password hashing
bcrypt = Bcrypt()

class Database:
    """Database connection manager with connection retry logic"""
    
    _instance = None
    _conn = None
    _max_retries = 3
    _retry_delay = 1
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        self._conn = None
    
    def get_connection(self):
        """Get a database connection with retry logic"""
        if self._conn is None or self._conn.closed:
            for attempt in range(self._max_retries):
                try:
                    # Ensure SSL mode is set for Neon.tech
                    conn_string = Config.DATABASE_URL
                    if 'sslmode' not in conn_string:
                        conn_string += '?sslmode=require' if '?' not in conn_string else '&sslmode=require'
                    
                    self._conn = psycopg.connect(conn_string)
                    logger.info("Database connection established")
                    return self._conn
                except Exception as e:
                    logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                    if attempt < self._max_retries - 1:
                        time.sleep(self._retry_delay)
                    else:
                        logger.error(f"Failed to connect to database: {e}")
                        raise
        return self._conn
    
    def close_connection(self):
        """Close database connection"""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None
            logger.info("Database connection closed")
    
    @contextmanager
    def get_cursor(self):
        """Get a cursor from a connection with connection check"""
        conn = None
        try:
            # Get connection with retry
            conn = self.get_connection()
            
            # Check if connection is still alive
            if conn.closed:
                self._conn = None
                conn = self.get_connection()
            
            cur = conn.cursor()
            yield cur
            conn.commit()
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            logger.error(f"Database operation error: {e}")
            raise
        finally:
            if cur:
                try:
                    cur.close()
                except:
                    pass
    
    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        """Execute a query and return results with retry logic"""
        for attempt in range(self._max_retries):
            try:
                with self.get_cursor() as cur:
                    cur.execute(query, params or ())
                    if fetch_one:
                        result = cur.fetchone()
                        if result:
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
            except (psycopg.OperationalError, psycopg.InterfaceError) as e:
                logger.warning(f"Query attempt {attempt + 1} failed: {e}")
                # Close connection to force reconnection
                self.close_connection()
                if attempt < self._max_retries - 1:
                    time.sleep(self._retry_delay)
                    continue
                raise
            except Exception as e:
                logger.error(f"Query execution error: {e}")
                raise

db = Database()

def init_database():
    """Initialize database tables with issuance tracking and authentication"""
    logger.info("Initializing database tables...")
    
    create_table_sql = """
    -- Members table
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
    
    -- Badge issuance log table
    CREATE TABLE IF NOT EXISTS badge_issuance_log (
        id SERIAL PRIMARY KEY,
        member_id INTEGER REFERENCES members(id) ON DELETE CASCADE,
        issued_by VARCHAR(100),
        issued_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        print_format VARCHAR(20),
        print_quality VARCHAR(20),
        notes TEXT
    );
    
    -- Admins table
    CREATE TABLE IF NOT EXISTS admins (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(200) NOT NULL,
        email VARCHAR(100),
        full_name VARCHAR(200),
        role VARCHAR(50) DEFAULT 'admin',
        is_active BOOLEAN DEFAULT TRUE,
        last_login TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Admin login history
    CREATE TABLE IF NOT EXISTS admin_login_history (
        id SERIAL PRIMARY KEY,
        admin_id INTEGER REFERENCES admins(id) ON DELETE CASCADE,
        ip_address VARCHAR(50),
        user_agent TEXT,
        login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        success BOOLEAN DEFAULT TRUE
    );
    
    -- Password reset tokens
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id SERIAL PRIMARY KEY,
        admin_id INTEGER REFERENCES admins(id) ON DELETE CASCADE,
        token VARCHAR(100) UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        used BOOLEAN DEFAULT FALSE
    );
    
    CREATE INDEX IF NOT EXISTS idx_admins_username ON admins(username);
    CREATE INDEX IF NOT EXISTS idx_admins_email ON admins(email);
    CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token);
    """
    
    try:
        with db.get_cursor() as cur:
            cur.execute(create_table_sql)
            logger.info("Database tables created successfully")
            
            # Create default admin user with proper password hash
            # Password: Admin@2024
            password_hash = bcrypt.generate_password_hash('Admin@2024').decode('utf-8')
            
            cur.execute("""
                INSERT INTO admins (username, password_hash, full_name, role, is_active)
                SELECT %s, %s, %s, %s, %s
                WHERE NOT EXISTS (SELECT 1 FROM admins WHERE username = %s)
            """, ('admin', password_hash, 'System Administrator', 'super_admin', True, 'admin'))
            
            logger.info("Default admin user created (username: admin, password: Admin@2024)")
            
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise

# ============================================================
# MEMBER FUNCTIONS
# ============================================================

def create_member(data):
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
    query = "SELECT * FROM members WHERE id = %s"
    return db.execute_query(query, (member_id,), fetch_one=True)

def get_member_by_number(member_number):
    query = "SELECT * FROM members WHERE member_number = %s"
    return db.execute_query(query, (member_number,), fetch_one=True)

def get_member_by_national_id(national_id):
    query = "SELECT * FROM members WHERE national_id = %s"
    return db.execute_query(query, (national_id,), fetch_one=True)

def get_member_by_telephone(telephone):
    query = "SELECT * FROM members WHERE telephone = %s"
    return db.execute_query(query, (telephone,), fetch_one=True)

def get_all_members(limit=50, offset=0, search=None):
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
    query = "SELECT COUNT(*) as count FROM members"
    params = []
    
    if search:
        query += " WHERE full_name ILIKE %s OR member_number ILIKE %s OR national_id ILIKE %s OR telephone ILIKE %s"
        search_pattern = f"%{search}%"
        params = [search_pattern, search_pattern, search_pattern, search_pattern]
    
    result = db.execute_query(query, tuple(params), fetch_one=True)
    return result['count'] if result else 0

def update_member(member_id, data):
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
    query = "DELETE FROM members WHERE id = %s RETURNING id"
    result = db.execute_query(query, (member_id,), fetch_one=True)
    return result is not None

def get_recent_members(limit=5):
    query = "SELECT * FROM members ORDER BY created_at DESC LIMIT %s"
    return db.execute_query(query, (limit,), fetch_all=True)

def search_members_by_qr(qr_data):
    query = "SELECT * FROM members WHERE qr_code_data = %s"
    return db.execute_query(query, (qr_data,), fetch_one=True)

def log_badge_issuance(member_id, issued_by, print_format, print_quality, notes=None):
    query = """
    INSERT INTO badge_issuance_log (member_id, issued_by, print_format, print_quality, notes)
    VALUES (%s, %s, %s, %s, %s)
    """
    with db.get_cursor() as cur:
        cur.execute(query, (member_id, issued_by, print_format, print_quality, notes))
        return cur.rowcount > 0

def get_issuance_log(member_id, limit=10):
    query = """
    SELECT * FROM badge_issuance_log 
    WHERE member_id = %s 
    ORDER BY issued_date DESC 
    LIMIT %s
    """
    return db.execute_query(query, (member_id, limit), fetch_all=True)

def get_unissued_members(limit=None):
    query = "SELECT * FROM members WHERE badge_issued = FALSE ORDER BY created_at ASC"
    if limit:
        query += f" LIMIT {limit}"
    return db.execute_query(query, fetch_all=True)

def get_issued_members(limit=None):
    query = "SELECT * FROM members WHERE badge_issued = TRUE ORDER BY badge_issued_date DESC"
    if limit:
        query += f" LIMIT {limit}"
    return db.execute_query(query, fetch_all=True)

# ============================================================
# AUTHENTICATION FUNCTIONS
# ============================================================

def create_admin(username, password_hash, full_name=None, email=None, role='admin'):
    query = """
    INSERT INTO admins (username, password_hash, full_name, email, role)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id;
    """
    with db.get_cursor() as cur:
        cur.execute(query, (username, password_hash, full_name, email, role))
        return cur.fetchone()[0]

def get_admin_by_username(username):
    query = "SELECT * FROM admins WHERE username = %s"
    return db.execute_query(query, (username,), fetch_one=True)

def get_admin_by_id(admin_id):
    query = "SELECT * FROM admins WHERE id = %s"
    return db.execute_query(query, (admin_id,), fetch_one=True)

def get_admin_by_email(email):
    query = "SELECT * FROM admins WHERE email = %s"
    return db.execute_query(query, (email,), fetch_one=True)

def get_all_admins():
    query = "SELECT id, username, email, full_name, role, is_active, last_login, created_at FROM admins ORDER BY created_at DESC"
    return db.execute_query(query, fetch_all=True)

def update_admin(admin_id, data):
    set_clauses = []
    values = []
    
    allowed_fields = ['full_name', 'email', 'role', 'is_active']
    for key, value in data.items():
        if key in allowed_fields and value is not None:
            set_clauses.append(f"{key} = %s")
            values.append(value)
    
    if not set_clauses:
        return None
    
    values.append(admin_id)
    query = f"""
    UPDATE admins 
    SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
    WHERE id = %s
    RETURNING id
    """
    
    with db.get_cursor() as cur:
        cur.execute(query, tuple(values))
        result = cur.fetchone()
        return result[0] if result else None

def update_admin_password(admin_id, password_hash):
    query = "UPDATE admins SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s RETURNING id"
    with db.get_cursor() as cur:
        cur.execute(query, (password_hash, admin_id))
        result = cur.fetchone()
        return result[0] if result else None

def log_admin_login(admin_id, ip_address=None, user_agent=None, success=True):
    query = """
    INSERT INTO admin_login_history (admin_id, ip_address, user_agent, success)
    VALUES (%s, %s, %s, %s)
    """
    with db.get_cursor() as cur:
        cur.execute(query, (admin_id, ip_address, user_agent, success))
        return cur.rowcount > 0

def update_last_login(admin_id):
    query = "UPDATE admins SET last_login = CURRENT_TIMESTAMP WHERE id = %s"
    with db.get_cursor() as cur:
        cur.execute(query, (admin_id,))
        return cur.rowcount > 0

def delete_admin(admin_id):
    query = "DELETE FROM admins WHERE id = %s RETURNING id"
    result = db.execute_query(query, (admin_id,), fetch_one=True)
    return result is not None

def admin_exists(username=None, email=None):
    if username:
        query = "SELECT id FROM admins WHERE username = %s"
        result = db.execute_query(query, (username,), fetch_one=True)
        return result is not None
    elif email:
        query = "SELECT id FROM admins WHERE email = %s"
        result = db.execute_query(query, (email,), fetch_one=True)
        return result is not None
    return False

def get_admin_count():
    query = "SELECT COUNT(*) as count FROM admins"
    result = db.execute_query(query, fetch_one=True)
    return result['count'] if result else 0

# Initialize database on module import
try:
    init_database()
except Exception as e:
    logger.error(f"Database initialization failed: {e}")
    # Continue anyway - tables might already exist
