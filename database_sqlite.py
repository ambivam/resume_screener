from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import sqlite3
import json

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
    criteria_json = Column(Text, nullable=False)  # SQLite doesn't have JSON type
    created_date = Column(DateTime, default=datetime.utcnow)

class ScreeningResult(Base):
    __tablename__ = 'screening_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(Integer, nullable=False)
    criteria_id = Column(Integer, nullable=False)
    overall_score = Column(Float, nullable=False)
    category = Column(String(100), nullable=False)
    detailed_analysis = Column(Text, nullable=False)  # SQLite doesn't have JSON type
    screening_date = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    def __init__(self, use_sqlite=True):
        if use_sqlite:
            self.engine = create_engine('sqlite:///resume_screener.db')
        else:
            from config import config
            self.engine = create_engine(config.database_url)
        
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
                criteria_json=json.dumps(criteria_json)  # Convert to JSON string
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
                detailed_analysis=json.dumps(detailed_analysis)  # Convert to JSON string
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

# Initialize database manager with SQLite as fallback
db_manager = DatabaseManager(use_sqlite=True)
