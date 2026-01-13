#!/usr/bin/env python3
"""
Database Migration System for Resume Screener Application

This module provides database migration functionality for schema changes,
version management, and rollback capabilities.

Usage:
    python migrations.py --run-migrations
    python migrations.py --rollback --version 1
    python migrations.py --status
    python migrations.py --create-migration "Add new column"
"""

import sys
import argparse
from datetime import datetime
from database import DatabaseManager
from sqlalchemy import text, MetaData, Table, Column, Integer, String, DateTime
from config import config

class MigrationManager:
    def __init__(self):
        self.db = DatabaseManager()
        self.engine = self.db.engine
        self.ensure_migration_table()
    
    def ensure_migration_table(self):
        """Create migration tracking table if it doesn't exist"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        version VARCHAR(50) NOT NULL UNIQUE,
                        name VARCHAR(255) NOT NULL,
                        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        rollback_sql TEXT,
                        INDEX idx_version (version)
                    )
                """))
                conn.commit()
        except Exception as e:
            print(f"Error creating migration table: {e}")
    
    def get_applied_migrations(self):
        """Get list of applied migrations"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version, name, applied_at FROM schema_migrations ORDER BY applied_at"))
                return result.fetchall()
        except Exception as e:
            print(f"Error getting applied migrations: {e}")
            return []
    
    def is_migration_applied(self, version):
        """Check if a migration version has been applied"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM schema_migrations WHERE version = :version"), 
                                    {"version": version})
                return result.scalar() > 0
        except Exception as e:
            print(f"Error checking migration status: {e}")
            return False
    
    def record_migration(self, version, name, rollback_sql=None):
        """Record a migration as applied"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO schema_migrations (version, name, rollback_sql) 
                    VALUES (:version, :name, :rollback_sql)
                """), {"version": version, "name": name, "rollback_sql": rollback_sql})
                conn.commit()
                print(f"✅ Migration {version} recorded successfully")
        except Exception as e:
            print(f"❌ Error recording migration: {e}")
    
    def rollback_migration(self, version):
        """Rollback a specific migration"""
        try:
            with self.engine.connect() as conn:
                # Get rollback SQL
                result = conn.execute(text("SELECT rollback_sql FROM schema_migrations WHERE version = :version"), 
                                    {"version": version})
                row = result.fetchone()
                
                if not row or not row[0]:
                    print(f"❌ No rollback SQL found for migration {version}")
                    return False
                
                # Execute rollback SQL
                rollback_sql = row[0]
                print(f"🔄 Rolling back migration {version}...")
                conn.execute(text(rollback_sql))
                
                # Remove migration record
                conn.execute(text("DELETE FROM schema_migrations WHERE version = :version"), 
                           {"version": version})
                conn.commit()
                print(f"✅ Migration {version} rolled back successfully")
                return True
                
        except Exception as e:
            print(f"❌ Error rolling back migration: {e}")
            return False

# Migration definitions
MIGRATIONS = [
    {
        "version": "001",
        "name": "Add vacancy and profile support to screening_results",
        "description": "Add vacancy_id, candidate_profile_id, and screening_type columns",
        "sql": """
            ALTER TABLE screening_results 
            ADD COLUMN vacancy_id INT NULL,
            ADD COLUMN candidate_profile_id INT NULL,
            ADD COLUMN screening_type VARCHAR(50) DEFAULT 'criteria_based'
        """,
        "rollback_sql": """
            ALTER TABLE screening_results 
            DROP COLUMN vacancy_id,
            DROP COLUMN candidate_profile_id,
            DROP COLUMN screening_type
        """,
        "check_function": lambda conn: check_columns_exist(conn, 'screening_results', 
                                                         ['vacancy_id', 'candidate_profile_id', 'screening_type'])
    },
    {
        "version": "002", 
        "name": "Create job_vacancies table",
        "description": "Create table for storing job vacancy JSON data",
        "sql": """
            CREATE TABLE IF NOT EXISTS job_vacancies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                vacancy_id INT NOT NULL,
                group_name VARCHAR(500),
                job_activities TEXT,
                creation_date DATETIME,
                update_date DATETIME,
                visibility VARCHAR(100),
                num_positions INT DEFAULT 1,
                skills JSON,
                additional_software JSON,
                languages JSON,
                benefits JSON,
                profile JSON,
                seniority JSON,
                currency JSON,
                created_by JSON,
                position_owner JSON,
                full_vacancy_json JSON NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "rollback_sql": "DROP TABLE IF EXISTS job_vacancies",
        "check_function": lambda conn: check_table_exists(conn, 'job_vacancies')
    },
    {
        "version": "003",
        "name": "Create candidate_profiles table", 
        "description": "Create table for storing candidate profile JSON data",
        "sql": """
            CREATE TABLE IF NOT EXISTS candidate_profiles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                profile_id INT NOT NULL,
                profile_description TEXT,
                working VARCHAR(10),
                regions JSON,
                salary_ranges JSON,
                experience_areas JSON,
                languages JSON,
                academic_levels JSON,
                hiring_types JSON,
                updated_at_info JSON,
                created_by INT,
                modified_by INT,
                full_profile_json JSON NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "rollback_sql": "DROP TABLE IF EXISTS candidate_profiles",
        "check_function": lambda conn: check_table_exists(conn, 'candidate_profiles')
    },
    {
        "version": "004",
        "name": "Fix criteria_id column constraint",
        "description": "Allow NULL values for criteria_id to support vacancy-based and profile-based screening",
        "sql": """
            ALTER TABLE screening_results 
            MODIFY COLUMN criteria_id INT NULL
        """,
        "rollback_sql": """
            ALTER TABLE screening_results 
            MODIFY COLUMN criteria_id INT NOT NULL
        """,
        "check_function": lambda conn: check_column_nullable(conn, 'screening_results', 'criteria_id')
    }
]

def check_table_exists(conn, table_name):
    """Check if a table exists"""
    try:
        result = conn.execute(text(f"SHOW TABLES LIKE '{table_name}'"))
        return result.fetchone() is not None
    except:
        return False

def check_columns_exist(conn, table_name, column_names):
    """Check if specific columns exist in a table"""
    try:
        result = conn.execute(text(f"DESCRIBE {table_name}"))
        existing_columns = [row[0] for row in result.fetchall()]
        return all(col in existing_columns for col in column_names)
    except:
        return False

def check_column_nullable(conn, table_name, column_name):
    """Check if a column allows NULL values"""
    try:
        result = conn.execute(text(f"DESCRIBE {table_name}"))
        for row in result.fetchall():
            if row[0] == column_name:
                return row[2] == 'YES'  # NULL column is at index 2
        return False
    except:
        return False

def run_migrations():
    """Run all pending migrations"""
    print("🚀 Starting database migrations...")
    migration_manager = MigrationManager()
    
    applied_count = 0
    for migration in MIGRATIONS:
        version = migration["version"]
        name = migration["name"]
        
        if migration_manager.is_migration_applied(version):
            print(f"⏭️  Migration {version} ({name}) already applied")
            continue
        
        print(f"🔄 Running migration {version}: {name}")
        
        try:
            with migration_manager.engine.connect() as conn:
                # Check if migration is needed
                if migration.get("check_function") and migration["check_function"](conn):
                    print(f"✅ Migration {version} already exists in database, marking as applied")
                    migration_manager.record_migration(version, name, migration.get("rollback_sql"))
                    continue
                
                # Run migration SQL
                conn.execute(text(migration["sql"]))
                conn.commit()
                
                # Record migration
                migration_manager.record_migration(version, name, migration.get("rollback_sql"))
                applied_count += 1
                print(f"✅ Migration {version} completed successfully")
                
        except Exception as e:
            print(f"❌ Migration {version} failed: {e}")
            return False
    
    if applied_count == 0:
        print("✅ All migrations are up to date")
    else:
        print(f"✅ Applied {applied_count} migrations successfully")
    
    return True

def show_migration_status():
    """Show current migration status"""
    print("📊 Migration Status:")
    print("=" * 50)
    
    migration_manager = MigrationManager()
    applied_migrations = migration_manager.get_applied_migrations()
    applied_versions = [m[0] for m in applied_migrations]
    
    for migration in MIGRATIONS:
        version = migration["version"]
        name = migration["name"]
        status = "✅ Applied" if version in applied_versions else "⏳ Pending"
        print(f"{version}: {name} - {status}")
    
    if applied_migrations:
        print("\n📅 Applied Migrations:")
        print("-" * 30)
        for version, name, applied_at in applied_migrations:
            print(f"{version}: {name} (Applied: {applied_at})")
    
    print("=" * 50)

def create_migration_template(name):
    """Create a new migration template"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    version = f"{len(MIGRATIONS) + 1:03d}_{timestamp}"
    
    template = f'''
# Migration {version}: {name}
# Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

MIGRATION = {{
    "version": "{version}",
    "name": "{name}",
    "description": "TODO: Add description",
    "sql": """
        -- TODO: Add your migration SQL here
        -- Example:
        -- ALTER TABLE table_name ADD COLUMN new_column VARCHAR(255);
    """,
    "rollback_sql": """
        -- TODO: Add rollback SQL here
        -- Example:
        -- ALTER TABLE table_name DROP COLUMN new_column;
    """,
    "check_function": lambda conn: True  # TODO: Add check logic
}}

# Add this migration to the MIGRATIONS list in migrations.py
'''
    
    filename = f"migration_{version}_{name.lower().replace(' ', '_')}.py"
    print(f"📝 Migration template created: {filename}")
    print(template)
    print(f"\n💡 Add the MIGRATION dictionary to the MIGRATIONS list in migrations.py")

def main():
    """Main function for command line usage"""
    parser = argparse.ArgumentParser(description='Database migration utilities')
    parser.add_argument('--run-migrations', action='store_true',
                       help='Run all pending migrations')
    parser.add_argument('--rollback', action='store_true',
                       help='Rollback a migration')
    parser.add_argument('--version', type=str,
                       help='Migration version to rollback')
    parser.add_argument('--status', action='store_true',
                       help='Show migration status')
    parser.add_argument('--create-migration', type=str,
                       help='Create a new migration template')
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    print(f"🕒 Migration utilities started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        if args.status:
            show_migration_status()
        
        elif args.run_migrations:
            success = run_migrations()
            if not success:
                sys.exit(1)
        
        elif args.rollback:
            if not args.version:
                print("❌ --version is required for rollback")
                sys.exit(1)
            
            migration_manager = MigrationManager()
            success = migration_manager.rollback_migration(args.version)
            if not success:
                sys.exit(1)
        
        elif args.create_migration:
            create_migration_template(args.create_migration)
        
        print("\n🎉 Migration utilities completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration utilities failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
