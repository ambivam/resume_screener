from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import config

Base = declarative_base()

class Resume(Base):
    __tablename__ = 'resumes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    original_text = Column(Text, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Integer)
    file_type = Column(String(50))

class ScreeningCriteria(Base):
    __tablename__ = 'screening_criteria'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    criteria_json = Column(JSON, nullable=False)
    created_date = Column(DateTime, default=datetime.utcnow)

class ScreeningResult(Base):
    __tablename__ = 'screening_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(Integer, nullable=False)
    criteria_id = Column(Integer, nullable=False)
    overall_score = Column(Float, nullable=False)
    category = Column(String(100), nullable=False)
    detailed_analysis = Column(JSON, nullable=False)
    screening_date = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    def __init__(self):
        try:
            self.engine = create_engine(config.database_url, echo=False)
            # Test the connection
            self.engine.connect()
            # Create tables automatically
            self.create_tables()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MySQL database: {str(e)}. Please ensure MySQL server is running and credentials are correct.")
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all tables in the database"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        """Get a database session"""
        return self.SessionLocal()
    
    def save_resume(self, filename, text, file_size, file_type):
        """Save resume to database"""
        session = self.get_session()
        try:
            resume = Resume(
                filename=filename,
                original_text=text,
                file_size=file_size,
                file_type=file_type
            )
            session.add(resume)
            session.commit()
            session.refresh(resume)
            return resume.id
        finally:
            session.close()
    
    def save_criteria(self, name, description, criteria_json):
        """Save screening criteria to database"""
        session = self.get_session()
        try:
            criteria = ScreeningCriteria(
                name=name,
                description=description,
                criteria_json=criteria_json
            )
            session.add(criteria)
            session.commit()
            session.refresh(criteria)
            return criteria.id
        finally:
            session.close()
    
    def save_screening_result(self, resume_id, criteria_id, overall_score, category, detailed_analysis):
        """Save screening result to database"""
        session = self.get_session()
        try:
            result = ScreeningResult(
                resume_id=resume_id,
                criteria_id=criteria_id,
                overall_score=overall_score,
                category=category,
                detailed_analysis=detailed_analysis
            )
            session.add(result)
            session.commit()
            session.refresh(result)
            return result.id
        finally:
            session.close()
    
    def get_all_resumes(self):
        """Get all resumes from database"""
        session = self.get_session()
        try:
            return session.query(Resume).all()
        finally:
            session.close()
    
    def get_screening_results(self, criteria_id=None):
        """Get screening results, optionally filtered by criteria"""
        session = self.get_session()
        try:
            query = session.query(ScreeningResult, Resume).join(Resume, ScreeningResult.resume_id == Resume.id)
            if criteria_id:
                query = query.filter(ScreeningResult.criteria_id == criteria_id)
            return query.all()
        finally:
            session.close()
    
    def get_all_screening_results(self, criteria_id=None):
        """Get ALL screening results including orphaned ones"""
        session = self.get_session()
        try:
            query = session.query(ScreeningResult)
            if criteria_id:
                query = query.filter(ScreeningResult.criteria_id == criteria_id)
            return query.all()
        finally:
            session.close()
    
    def delete_resume(self, resume_id):
        """Delete a resume and its associated screening results"""
        session = self.get_session()
        try:
            # First delete associated screening results
            session.query(ScreeningResult).filter(ScreeningResult.resume_id == resume_id).delete()
            
            # Then delete the resume
            resume = session.query(Resume).filter(Resume.id == resume_id).first()
            if resume:
                session.delete(resume)
                session.commit()
                return True, f"Resume '{resume.filename}' deleted successfully"
            else:
                return False, "Resume not found"
        except Exception as e:
            session.rollback()
            return False, f"Error deleting resume: {str(e)}"
        finally:
            session.close()
    
    def delete_multiple_resumes(self, resume_ids):
        """Delete multiple resumes and their associated screening results"""
        session = self.get_session()
        try:
            deleted_count = 0
            for resume_id in resume_ids:
                # Delete associated screening results
                session.query(ScreeningResult).filter(ScreeningResult.resume_id == resume_id).delete()
                
                # Delete the resume
                resume = session.query(Resume).filter(Resume.id == resume_id).first()
                if resume:
                    session.delete(resume)
                    deleted_count += 1
            
            session.commit()
            return True, f"Successfully deleted {deleted_count} resume(s)"
        except Exception as e:
            session.rollback()
            return False, f"Error deleting resumes: {str(e)}"
        finally:
            session.close()
    
    def cleanup_orphaned_results(self):
        """Clean up screening results for deleted resumes"""
        session = self.get_session()
        try:
            # Get all existing resume IDs
            existing_resume_ids = [resume.id for resume in session.query(Resume).all()]
            all_screening_results = session.query(ScreeningResult).all()
            
            # Find orphaned screening results
            orphaned_results = []
            for result in all_screening_results:
                if result.resume_id not in existing_resume_ids:
                    orphaned_results.append(result)
            
            orphaned_count = len(orphaned_results)
            
            if orphaned_count > 0:
                # Show details before deletion
                orphaned_resume_ids = [r.resume_id for r in orphaned_results]
                
                # Delete orphaned results one by one to ensure they're deleted
                deleted_count = 0
                for result in orphaned_results:
                    session.delete(result)
                    deleted_count += 1
                
                session.commit()
                return True, f"Cleaned up {deleted_count} orphaned screening results (resume IDs: {sorted(set(orphaned_resume_ids))})"
            else:
                # Double check - count all results vs existing resumes
                total_results = len(all_screening_results)
                total_resumes = len(existing_resume_ids)
                
                if total_results > total_resumes * 2:
                    # Something is wrong, force delete all results and let user re-screen
                    session.query(ScreeningResult).delete()
                    session.commit()
                    return True, f"Force cleaned all {total_results} screening results due to data inconsistency"
                else:
                    return True, f"No orphaned results found. Total results: {total_results}, Total resumes: {total_resumes}"
                
        except Exception as e:
            session.rollback()
            return False, f"Error cleaning up orphaned results: {str(e)}"
        finally:
            session.close()
    
    def test_connection(self):
        """Test database connection"""
        try:
            from sqlalchemy import text
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True, "Connection successful"
        except Exception as e:
            return False, str(e)

# Initialize database manager
try:
    db_manager = DatabaseManager()
except ConnectionError as e:
    print(f"Database connection failed: {e}")
    db_manager = None
