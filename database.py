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

class JobVacancy(Base):
    __tablename__ = 'job_vacancies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vacancy_id = Column(Integer, nullable=False)  # Original vacancy ID from JSON
    group_name = Column(String(500), nullable=True)
    job_activities = Column(Text, nullable=True)
    creation_date = Column(DateTime, nullable=True)
    update_date = Column(DateTime, nullable=True)
    visibility = Column(String(100), nullable=True)
    num_positions = Column(Integer, default=1)
    
    # JSON fields for complex data
    skills = Column(JSON, nullable=True)
    additional_software = Column(JSON, nullable=True)
    languages = Column(JSON, nullable=True)
    benefits = Column(JSON, nullable=True)
    profile = Column(JSON, nullable=True)
    seniority = Column(JSON, nullable=True)
    currency = Column(JSON, nullable=True)
    created_by = Column(JSON, nullable=True)
    position_owner = Column(JSON, nullable=True)
    
    # Full JSON for reference
    full_vacancy_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class CandidateProfile(Base):
    __tablename__ = 'candidate_profiles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, nullable=False)  # Original profile ID from JSON
    profile_description = Column(Text, nullable=True)
    working = Column(String(10), nullable=True)  # Store as string for flexibility
    
    # JSON fields for complex data
    regions = Column(JSON, nullable=True)
    salary_ranges = Column(JSON, nullable=True)
    experience_areas = Column(JSON, nullable=True)
    languages = Column(JSON, nullable=True)
    academic_levels = Column(JSON, nullable=True)
    hiring_types = Column(JSON, nullable=True)
    updated_at_info = Column(JSON, nullable=True)
    
    # Audit fields
    created_by = Column(Integer, nullable=True)
    modified_by = Column(Integer, nullable=True)
    
    # Full JSON for reference
    full_profile_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ScreeningResult(Base):
    __tablename__ = 'screening_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(Integer, nullable=False)
    criteria_id = Column(Integer, nullable=True)  # Made nullable for vacancy-based screening
    vacancy_id = Column(Integer, nullable=True)  # New field for job vacancy screening
    candidate_profile_id = Column(Integer, nullable=True)  # New field for candidate profile matching
    overall_score = Column(Float, nullable=False)
    category = Column(String(100), nullable=False)
    detailed_analysis = Column(JSON, nullable=False)
    screening_type = Column(String(50), default='criteria_based')  # criteria_based, vacancy_based, profile_based
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
    
    def save_job_vacancy(self, vacancy_json):
        """Save job vacancy to database"""
        session = self.get_session()
        try:
            from datetime import datetime as dt
            
            # Parse dates if they exist
            creation_date = None
            update_date = None
            
            if vacancy_json.get('creationDate'):
                try:
                    creation_date = dt.strptime(vacancy_json['creationDate'], '%Y-%m-%d %H:%M:%S')
                except:
                    pass
            
            if vacancy_json.get('updateDate'):
                try:
                    update_date = dt.strptime(vacancy_json['updateDate'], '%Y-%m-%d')
                except:
                    pass
            
            vacancy = JobVacancy(
                vacancy_id=vacancy_json.get('id'),
                group_name=vacancy_json.get('group'),
                job_activities=vacancy_json.get('jobActivities'),
                creation_date=creation_date,
                update_date=update_date,
                visibility=vacancy_json.get('visibility'),
                num_positions=vacancy_json.get('numOfPositions', 1),
                skills=vacancy_json.get('skills'),
                additional_software=vacancy_json.get('aditionalSoftware'),
                languages=vacancy_json.get('languages'),
                benefits=vacancy_json.get('benefits'),
                profile=vacancy_json.get('profile'),
                seniority=vacancy_json.get('seniority'),
                currency=vacancy_json.get('currency'),
                created_by=vacancy_json.get('createdBy'),
                position_owner=vacancy_json.get('positionOwner'),
                full_vacancy_json=vacancy_json
            )
            session.add(vacancy)
            session.commit()
            session.refresh(vacancy)
            return vacancy.id
        finally:
            session.close()
    
    def get_job_vacancy(self, vacancy_id):
        """Get job vacancy by ID"""
        session = self.get_session()
        try:
            return session.query(JobVacancy).filter(JobVacancy.id == vacancy_id).first()
        finally:
            session.close()
    
    def get_all_job_vacancies(self):
        """Get all job vacancies"""
        session = self.get_session()
        try:
            return session.query(JobVacancy).all()
        finally:
            session.close()
    
    def save_candidate_profile(self, profile_json):
        """Save candidate profile to database"""
        session = self.get_session()
        try:
            profile = CandidateProfile(
                profile_id=profile_json.get('id'),
                profile_description=profile_json.get('profileDescription'),
                working=str(profile_json.get('working', False)),
                regions=profile_json.get('regions'),
                salary_ranges=profile_json.get('salaryRanges'),
                experience_areas=profile_json.get('experienceAreas'),
                languages=profile_json.get('languages'),
                academic_levels=profile_json.get('academicLevels'),
                hiring_types=profile_json.get('hiringTypes'),
                updated_at_info=profile_json.get('updatedAt'),
                created_by=profile_json.get('createdBy'),
                modified_by=profile_json.get('modifiedBy'),
                full_profile_json=profile_json
            )
            session.add(profile)
            session.commit()
            session.refresh(profile)
            return profile.id
        finally:
            session.close()
    
    def get_candidate_profile(self, profile_id):
        """Get candidate profile by ID"""
        session = self.get_session()
        try:
            return session.query(CandidateProfile).filter(CandidateProfile.id == profile_id).first()
        finally:
            session.close()
    
    def get_all_candidate_profiles(self):
        """Get all candidate profiles"""
        session = self.get_session()
        try:
            return session.query(CandidateProfile).all()
        finally:
            session.close()

    def save_screening_result(self, resume_id, overall_score, category, detailed_analysis, criteria_id=None, vacancy_id=None, candidate_profile_id=None, screening_type='criteria_based'):
        """Save screening result to database"""
        session = self.get_session()
        try:
            result = ScreeningResult(
                resume_id=resume_id,
                criteria_id=criteria_id,
                vacancy_id=vacancy_id,
                candidate_profile_id=candidate_profile_id,
                overall_score=overall_score,
                category=category,
                detailed_analysis=detailed_analysis,
                screening_type=screening_type
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
