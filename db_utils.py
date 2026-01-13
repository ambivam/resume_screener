#!/usr/bin/env python3
"""
Database Utilities for Resume Screener Application

This module provides utility functions for database management tasks including:
- Testing database connectivity
- Creating/updating database schema
- Database maintenance operations
- Schema validation

Usage:
    python db_utils.py --test-connection
    python db_utils.py --create-tables
    python db_utils.py --validate-schema
"""

import sys
import argparse
from datetime import datetime
from database import DatabaseManager
from config import config

def test_database_connection():
    """Test database connection and return status"""
    try:
        print("🔍 Testing database connection...")
        db = DatabaseManager()
        print("✅ Database connection successful!")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def create_update_tables():
    """Create or update database tables"""
    try:
        print("🔧 Creating/updating database tables...")
        db = DatabaseManager()
        db.create_tables()
        print("✅ Tables created/updated successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating/updating tables: {e}")
        return False

def validate_schema():
    """Validate database schema and check for required tables/columns"""
    try:
        print("🔍 Validating database schema...")
        db = DatabaseManager()
        
        # Test basic operations
        session = db.get_session()
        
        # Check if we can query each table
        from database import Resume, ScreeningCriteria, ScreeningResult, JobVacancy, CandidateProfile
        
        tables_to_check = [
            ('resumes', Resume),
            ('screening_criteria', ScreeningCriteria), 
            ('screening_results', ScreeningResult),
            ('job_vacancies', JobVacancy),
            ('candidate_profiles', CandidateProfile)
        ]
        
        for table_name, model in tables_to_check:
            try:
                count = session.query(model).count()
                print(f"  ✅ Table '{table_name}': {count} records")
            except Exception as e:
                print(f"  ❌ Table '{table_name}': Error - {e}")
        
        session.close()
        print("✅ Schema validation completed!")
        return True
        
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False

def get_database_stats():
    """Get database statistics"""
    try:
        print("📊 Gathering database statistics...")
        db = DatabaseManager()
        session = db.get_session()
        
        from database import Resume, ScreeningCriteria, ScreeningResult, JobVacancy, CandidateProfile
        
        stats = {
            'resumes': session.query(Resume).count(),
            'screening_criteria': session.query(ScreeningCriteria).count(),
            'screening_results': session.query(ScreeningResult).count(),
            'job_vacancies': session.query(JobVacancy).count(),
            'candidate_profiles': session.query(CandidateProfile).count()
        }
        
        print("\n📈 Database Statistics:")
        print("=" * 30)
        for table, count in stats.items():
            print(f"{table.replace('_', ' ').title()}: {count}")
        print("=" * 30)
        
        session.close()
        return stats
        
    except Exception as e:
        print(f"❌ Error gathering statistics: {e}")
        return None

def check_environment():
    """Check environment configuration"""
    print("🔧 Checking environment configuration...")
    
    try:
        config.validate_config()
        print("✅ Environment configuration is valid")
        return True
    except Exception as e:
        print(f"❌ Environment configuration error: {e}")
        print("💡 Please check your .env file and ensure all required variables are set")
        return False

def full_database_check():
    """Perform a comprehensive database check"""
    print("🚀 Starting comprehensive database check...")
    print("=" * 50)
    
    # Check environment
    env_ok = check_environment()
    if not env_ok:
        return False
    
    # Test connection
    conn_ok = test_database_connection()
    if not conn_ok:
        return False
    
    # Create/update tables
    tables_ok = create_update_tables()
    if not tables_ok:
        return False
    
    # Validate schema
    schema_ok = validate_schema()
    if not schema_ok:
        return False
    
    # Get statistics
    get_database_stats()
    
    print("=" * 50)
    print("✅ Comprehensive database check completed successfully!")
    return True

def main():
    """Main function for command line usage"""
    parser = argparse.ArgumentParser(description='Database utilities for Resume Screener')
    parser.add_argument('--test-connection', action='store_true', 
                       help='Test database connection')
    parser.add_argument('--create-tables', action='store_true',
                       help='Create or update database tables')
    parser.add_argument('--validate-schema', action='store_true',
                       help='Validate database schema')
    parser.add_argument('--stats', action='store_true',
                       help='Show database statistics')
    parser.add_argument('--check-env', action='store_true',
                       help='Check environment configuration')
    parser.add_argument('--full-check', action='store_true',
                       help='Perform comprehensive database check')
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        # No arguments provided, show help
        parser.print_help()
        return
    
    print(f"🕒 Database utilities started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = True
    
    if args.check_env:
        success &= check_environment()
        print()
    
    if args.test_connection:
        success &= test_database_connection()
        print()
    
    if args.create_tables:
        success &= create_update_tables()
        print()
    
    if args.validate_schema:
        success &= validate_schema()
        print()
    
    if args.stats:
        stats = get_database_stats()
        success &= stats is not None
        print()
    
    if args.full_check:
        success &= full_database_check()
        print()
    
    if success:
        print("🎉 All operations completed successfully!")
        sys.exit(0)
    else:
        print("❌ Some operations failed. Please check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
