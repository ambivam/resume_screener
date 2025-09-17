#!/usr/bin/env python3
"""
Standalone script to clean up orphaned screening results
Run this if the Streamlit cleanup button doesn't work
"""

from database import db_manager

def main():
    print("🧹 Cleaning up orphaned screening results...")
    
    if db_manager is None:
        print("❌ Database connection failed")
        return
    
    try:
        success, message = db_manager.cleanup_orphaned_results()
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
