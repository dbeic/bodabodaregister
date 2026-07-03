# SYSTEM ADMINISTRATOR GUIDE
## Busia County Bodaboda SACCO Badge Management System

**Version:** 1.0
**Effective Date:** July 2026

---

## 1. INTRODUCTION

This guide is for System Administrators responsible for managing the Busia County Bodaboda SACCO Badge Management System.

---

## 2. ADMINISTRATOR RESPONSIBILITIES

### 2.1 Primary Responsibilities
- User account management
- System configuration
- Member data management
- Badge generation and issuance
- System security maintenance
- Backup and recovery

### 2.2 Administrative Contact
- **Chairman:** Bonface Nyongesa Okumu - Tel: 0758488841
- **Secretary General:** Peter Juma Olero - Tel: 0722178959

---

## 3. SYSTEM ACCESS

### 3.1 Admin Login
- URL: (provided by IT team)
- Default username: `admin`
- Default password: `Admin@2024`
- **IMPORTANT:** Change password immediately!

### 3.2 Creating New Admin Users

1. Login as admin
2. Go to Admin Panel
3. Click "Add Admin"
4. Fill in details:
   - Username
   - Email
   - Role
   - Temporary password
5. Click "Create"
6. Provide credentials to new admin

### 3.3 Admin Roles

| Role | Permissions |
|------|-------------|
| Super Admin | Full access, manage admins |
| Admin | Register members, generate badges |
| Manager | View and export data only |
| Verifier | QR verification only |

---

## 4. SYSTEM CONFIGURATION

### 4.1 Environment Variables

Create or update `.env` file:
```

DATABASE_URL=postgresql://username:password@host:port/database
SECRET_KEY=your-secret-key-here
DEBUG=False
GROUP_NAME=Busia Bodaboda SACCO
APP_NAME=Bodaboda Badge System

```

### 4.2 Badge Configuration

In `config.py`:
- BADGE_WIDTH = 1050
- BADGE_HEIGHT = 675
- BADGE_DPI = 300
- BLEED_SIZE = 36

### 4.3 Customizing Badge Colors

Edit `utils/badge_generator.py`:
```python
RED_BG = (180, 20, 20)        # Background color
GOLD_ACCENT = (212, 175, 55)  # Accent color
WHITE_TEXT = (255, 255, 255)  # Text color
```

---

5. MEMBER MANAGEMENT

5.1 Bulk Registration

1. Prepare CSV file with member data
2. Go to "Import Members"
3. Upload CSV file
4. Review and confirm
5. Generate badges in batch

5.2 Updating Member Data

1. Search for member
2. Click "Edit"
3. Update fields
4. Save changes
5. Badge auto-regenerates

5.3 Database Backups

Backup Command:

```bash
pg_dump -d $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

Restore Command:

```bash
psql -d $DATABASE_URL < backup_20260701.sql
```

---

6. BADGE GENERATION

6.1 Manual Badge Generation

1. Go to member details
2. Click "Regenerate"
3. Badge creates automatically
4. Preview and download

6.2 Batch Generation

1. Go to "Batch Issue"
2. Select format (PNG/PDF/Both)
3. Select quality (Draft/Standard/High)
4. Toggle bleed area
5. Click "Generate"
6. Download ZIP file

6.3 Print Settings

· High Quality: 300 DPI, best for printing
· Standard: 150 DPI, suitable for most use
· Draft: 72 DPI, quick previews

---

7. QR CODE MANAGEMENT

7.1 QR Code Generation

· QR codes are generated automatically
· Contains member verification data
· Stored in static/qr/ directory
· Named: qr_{member_number}.png

7.2 QR Code Verification

· Use verify page: /verify-qr
· Enter QR code data manually
· Or scan QR code
· Member details displayed

---

8. SECURITY

8.1 Password Policy

· Minimum 8 characters
· Mix of letters, numbers, symbols
· Change every 90 days
· No common passwords

8.2 Session Management

· Session timeout: 30 minutes
· Auto-logout on inactivity
· Clear cookies on logout

8.3 Security Checklist

· Change default admin password
· Enable HTTPS
· Regular database backups
· Monitor access logs
· Update software regularly

---

9. MAINTENANCE

9.1 Regular Tasks

· Daily: Check system logs
· Weekly: Backup database
· Monthly: Review user accounts
· Quarterly: Update passwords

9.2 Log Files

· Access logs: logs/access.log
· Error logs: logs/error.log
· Database logs: PostgreSQL logs

9.3 Monitoring Script

```bash
#!/bin/bash
# System health check

echo "Checking database connection..."
python -c "from database import db; db.get_connection()" || echo "Database error!"

echo "Checking disk space..."
df -h

echo "Checking memory..."
free -h
```

---

10. TROUBLESHOOTING

10.1 Common Issues

Issue Solution
Database connection failed Check DATABASE_URL in .env
Badge not generating Check Pillow installation
Slow performance Clear cache, restart server
Login failure Check user credentials
Page not found Check routes in app.py

10.2 Restarting System

Termux/Development:

```bash
# Stop app (Ctrl+C)
python app.py
```

Production (Gunicorn):

```bash
sudo systemctl restart app
```

10.3 Emergency Contacts

· Technical: James Boyid Ochuna - 0701207062
· Administrative: Peter Juma Olero - 0722178959
· Oversight: Bonface Nyongesa Okumu - 0758488841

---

11. SYSTEM UPDATES

11.1 Update Procedure

1. Backup database
2. Backup current files
3. Pull latest code: git pull
4. Install new dependencies
5. Run database migrations
6. Restart system
7. Verify functionality

11.2 Version Control

```bash
git status
git add .
git commit -m "Update description"
git push origin main
```

---

12. COMPLIANCE

12.1 Data Protection

· Comply with Data Protection Act, 2019
· Member data must be secure
· Access logs must be maintained
· Data retention policies followed

12.2 Audit Trail

· All actions are logged
· Logs include:
  · Who performed action
  · When it was performed
  · What was changed

---

13. SUPPORT

13.1 Support Channels

· Technical: James Boyid Ochuna - 0701207062
· Administrative: Peter Juma Olero - 0722178959
· Oversight: Bonface Nyongesa Okumu - 0758488841

13.2 Escalation Procedure

1. Contact system administrator
2. If unresolved, contact developer
3. If critical, contact Chairman

---

14. APPENDIX

14.1 Useful Commands

```bash
# Start app
python app.py

# Run migrations
python -c "from database import init_database; init_database()"

# Backup database
pg_dump -d $DATABASE_URL > backup.sql

# Check logs
tail -f logs/app.log
```

14.2 Directory Structure

```
bodabodaregister/
├── app.py
├── config.py
├── database.py
├── requirements.txt
├── static/
│   ├── badges/
│   ├── qr/
│   └── uploads/
├── templates/
├── utils/
└── venv/
```

---

END OF ADMINISTRATOR GUIDE
