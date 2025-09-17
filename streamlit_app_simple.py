import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from typing import Dict, List, Any
import glob
from pathlib import Path

# Import our custom modules
from config import config
from database import db_manager
from resume_parser import resume_parser
from simple_workflow import resume_screener

# Page configuration
st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .info-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'uploaded_resumes' not in st.session_state:
        st.session_state.uploaded_resumes = load_resumes_from_database()
    if 'screening_results' not in st.session_state:
        st.session_state.screening_results = load_screening_results_from_database()
    if 'current_criteria' not in st.session_state:
        st.session_state.current_criteria = {}

def load_resumes_from_database():
    """Load all resumes from database"""
    try:
        if db_manager is None:
            return []
        
        resumes = db_manager.get_all_resumes()
        resume_list = []
        
        for resume in resumes:
            resume_list.append({
                'id': resume.id,
                'filename': resume.filename,
                'text': resume.original_text,
                'word_count': len(resume.original_text.split()) if resume.original_text else 0,
                'file_type': resume.file_type,
                'upload_date': resume.upload_date
            })
        
        return resume_list
    except Exception as e:
        st.error(f"Error loading resumes from database: {str(e)}")
        return []

def load_screening_results_from_database():
    """Load screening results from database"""
    try:
        if db_manager is None:
            return []
        
        results = db_manager.get_screening_results()
        result_list = []
        
        for result, resume in results:
            # Parse JSON if stored as string
            detailed_analysis = result.detailed_analysis
            if isinstance(detailed_analysis, str):
                import json
                detailed_analysis = json.loads(detailed_analysis)
            
            result_list.append({
                'resume_id': result.resume_id,
                'filename': resume.filename,
                'analysis_result': {
                    'overall_score': result.overall_score,
                    'category': result.category,
                    'detailed_analysis': detailed_analysis
                }
            })
        
        return result_list
    except Exception as e:
        st.error(f"Error loading screening results from database: {str(e)}")
        return []

def load_criteria_from_database():
    """Load all screening criteria from database"""
    try:
        if db_manager is None:
            return []
        
        session = db_manager.get_session()
        try:
            from database import ScreeningCriteria
            criteria_list = session.query(ScreeningCriteria).order_by(ScreeningCriteria.created_date.desc()).all()
            
            result = []
            for criteria in criteria_list:
                # Parse JSON if stored as string
                criteria_json = criteria.criteria_json
                if isinstance(criteria_json, str):
                    import json
                    criteria_json = json.loads(criteria_json)
                
                result.append({
                    'id': criteria.id,
                    'name': criteria.name,
                    'description': criteria.description,
                    'criteria': criteria_json,
                    'created_date': criteria.created_date
                })
            
            return result
        finally:
            session.close()
            
    except Exception as e:
        st.error(f"Error loading criteria from database: {str(e)}")
        return []

def validate_environment():
    """Validate environment configuration"""
    try:
        config.validate_config()
        
        # Test database connection
        if db_manager is None:
            return False, "Database connection failed. Please ensure MySQL server is running."
        
        success, message = db_manager.test_connection()
        if not success:
            return False, f"Database connection test failed: {message}"
        
        return True, ""
    except ValueError as e:
        return False, str(e)

def create_sidebar():
    """Create application sidebar"""
    with st.sidebar:
        st.markdown("# 📄 AI Resume Screener")
        
        # Environment status
        env_valid, env_error = validate_environment()
        if env_valid:
            st.success("✅ Environment configured")
        else:
            st.error(f"❌ Configuration error: {env_error}")
            st.info("Please check your .env file and ensure all required variables are set.")
        
        # Navigation menu
        selected = st.selectbox(
            "Navigation",
            ["Upload Resumes", "Set Criteria", "Screen Resumes", "View Results"]
        )
        
        # Statistics
        st.markdown("### 📊 Statistics")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Uploaded", len(st.session_state.uploaded_resumes))
        with col2:
            st.metric("Screened", len(st.session_state.screening_results))
        
        return selected

def process_folder_files(folder_path: str) -> List[Dict]:
    """Process all resume files from a selected folder"""
    supported_extensions = ['.pdf', '.docx', '.txt']
    processed_files = []
    
    try:
        folder_path = Path(folder_path)
        if not folder_path.exists():
            return []
        
        # Find all supported files in the folder
        for ext in supported_extensions:
            pattern = f"*{ext}"
            files = list(folder_path.glob(pattern))
            for file_path in files:
                try:
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    # Validate file size
                    if len(file_content) > config.MAX_FILE_SIZE_MB * 1024 * 1024:
                        continue
                    
                    processed_files.append({
                        'name': file_path.name,
                        'content': file_content,
                        'path': str(file_path)
                    })
                except Exception as e:
                    st.warning(f"Could not read {file_path.name}: {str(e)}")
                    continue
    
    except Exception as e:
        st.error(f"Error accessing folder: {str(e)}")
    
    return processed_files

def upload_resumes_page():
    """Resume upload page"""
    st.markdown('<h1 class="main-header">📄 Upload Resumes</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>Supported formats:</strong> PDF, DOCX, TXT<br>
        <strong>Maximum file size:</strong> 10MB per file<br>
        <strong>Upload options:</strong> Individual files or entire folder
    </div>
    """, unsafe_allow_html=True)
    
    # Upload method selection
    upload_method = st.radio(
        "Choose upload method:",
        ["📁 Upload Individual Files", "📂 Upload from Folder"],
        horizontal=True
    )
    
    # Initialize session state for folder files
    if 'scanned_folder_files' not in st.session_state:
        st.session_state.scanned_folder_files = []
    
    uploaded_files = None
    folder_files = None
    
    if upload_method == "📁 Upload Individual Files":
        # Clear folder files when switching to individual upload
        st.session_state.scanned_folder_files = []
        
        # File uploader
        uploaded_files = st.file_uploader(
            "Choose resume files",
            type=['pdf', 'docx', 'txt'],
            accept_multiple_files=True,
            help="Upload one or more resume files for screening"
        )
    else:
        # Folder selection
        st.markdown("### 📂 Select Folder")
        folder_path = st.text_input(
            "Enter folder path containing resume files:",
            placeholder="C:\\path\\to\\resume\\folder",
            help="Enter the full path to the folder containing resume files (PDF, DOCX, TXT)"
        )
        
        if folder_path:
            if st.button("🔍 Scan Folder", type="primary"):
                folder_files = process_folder_files(folder_path)
                st.session_state.scanned_folder_files = folder_files
                if folder_files:
                    st.success(f"Found {len(folder_files)} resume files in the folder")
                    # Display found files
                    file_names = [f['name'] for f in folder_files]
                    st.write("**Files found:**")
                    for name in file_names:
                        st.write(f"• {name}")
                else:
                    st.warning("No supported resume files found in the specified folder")
        
        # Use scanned files from session state
        if st.session_state.scanned_folder_files:
            folder_files = st.session_state.scanned_folder_files
            st.success(f"Ready to process {len(folder_files)} resume files")
            file_names = [f['name'] for f in folder_files]
            st.write("**Files ready for processing:**")
            for name in file_names:
                st.write(f"• {name}")
    
    # Process files based on upload method
    files_to_process = []
    
    if uploaded_files:
        # Convert uploaded files to common format
        for uploaded_file in uploaded_files:
            files_to_process.append({
                'name': uploaded_file.name,
                'content': uploaded_file.read(),
                'source': 'upload'
            })
    elif folder_files:
        # Use folder files
        for folder_file in folder_files:
            files_to_process.append({
                'name': folder_file['name'],
                'content': folder_file['content'],
                'source': 'folder'
            })
    
    # Process files if any are available
    if files_to_process:
        if st.button("🚀 Process Files", type="primary", use_container_width=True):
            st.subheader("📋 Processing Files")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            processed_resumes = []
            
            for i, file_data in enumerate(files_to_process):
                try:
                    # Update progress
                    progress = (i + 1) / len(files_to_process)
                    progress_bar.progress(progress)
                    status_text.text(f"Processing {file_data['name']}...")
                    
                    # Validate file
                    resume_parser.validate_file(file_data['name'], len(file_data['content']), config.MAX_FILE_SIZE_MB)
                    
                    # Parse resume
                    parsed_resume = resume_parser.parse_resume(file_data['content'], file_data['name'])
                    
                    # Save to database
                    resume_id = db_manager.save_resume(
                        filename=file_data['name'],
                        text=parsed_resume['raw_text'],
                        file_size=len(file_data['content']),
                        file_type=parsed_resume['file_type']
                    )
                    
                    processed_resumes.append({
                        'id': resume_id,
                        'filename': file_data['name'],
                        'text': parsed_resume['raw_text'],
                        'word_count': parsed_resume['word_count'],
                        'file_type': parsed_resume['file_type'],
                        'upload_date': datetime.now(),
                        'source': file_data['source']
                    })
                    
                except Exception as e:
                    st.error(f"Error processing {file_data['name']}: {str(e)}")
            
            # Update session state
            st.session_state.uploaded_resumes.extend(processed_resumes)
            
            progress_bar.progress(1.0)
            status_text.text("✅ All files processed successfully!")
            
            # Clear scanned folder files after processing
            if upload_method == "📂 Upload from Folder":
                st.session_state.scanned_folder_files = []
            
            # Display results
            if processed_resumes:
                st.success(f"✅ Successfully processed {len(processed_resumes)} resume(s)!")
                st.balloons()  # Add celebratory animation
                
                # Show summary table
                df = pd.DataFrame(processed_resumes)
                st.subheader("📊 Processing Summary")
                st.dataframe(
                    df[['filename', 'word_count', 'file_type', 'upload_date', 'source']],
                    use_container_width=True
                )
                
                # Show additional confirmation
                st.info(f"All {len(processed_resumes)} resume(s) have been saved to the database and are ready for screening.")
            else:
                st.warning("No files were successfully processed. Please check the files and try again.")
    
    # Show existing uploads with delete functionality
    if st.session_state.uploaded_resumes:
        st.subheader("📚 Previously Uploaded Resumes")
        
        # Add delete controls
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write("**Manage your uploaded resumes:**")
        with col2:
            if st.button("🔄 Refresh List", help="Reload resumes from database"):
                st.session_state.uploaded_resumes = load_resumes_from_database()
                st.rerun()
        with col3:
            show_delete_options = st.checkbox("🗑️ Delete Mode", help="Enable delete options")
        
        df = pd.DataFrame(st.session_state.uploaded_resumes)
        
        if show_delete_options:
            st.warning("⚠️ Delete Mode Active - Select resumes to delete")
            
            # Multi-select for deletion
            resume_options = {}
            for resume in st.session_state.uploaded_resumes:
                key = f"{resume['filename']} (ID: {resume['id']}) - {resume['upload_date'].strftime('%Y-%m-%d %H:%M')}"
                resume_options[key] = resume
            
            selected_for_deletion = st.multiselect(
                "Select resumes to delete:",
                options=list(resume_options.keys()),
                help="Choose one or more resumes to delete permanently"
            )
            
            if selected_for_deletion:
                st.error(f"⚠️ You are about to delete {len(selected_for_deletion)} resume(s). This action cannot be undone!")
                
                # Show selected files
                st.write("**Files to be deleted:**")
                for key in selected_for_deletion:
                    resume = resume_options[key]
                    st.write(f"• {resume['filename']} (uploaded: {resume['upload_date'].strftime('%Y-%m-%d %H:%M')})")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Confirm Delete", type="primary", use_container_width=True):
                        # Get resume IDs to delete
                        resume_ids_to_delete = [resume_options[key]['id'] for key in selected_for_deletion]
                        
                        # Delete from database
                        success, message = db_manager.delete_multiple_resumes(resume_ids_to_delete)
                        
                        if success:
                            # Update session state
                            st.session_state.uploaded_resumes = [
                                resume for resume in st.session_state.uploaded_resumes 
                                if resume['id'] not in resume_ids_to_delete
                            ]
                            # Also update screening results
                            st.session_state.screening_results = [
                                result for result in st.session_state.screening_results 
                                if result['resume_id'] not in resume_ids_to_delete
                            ]
                            st.success(f"✅ {message}")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                
                with col2:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.rerun()
        
        # Display resumes table
        display_columns = ['filename', 'word_count', 'file_type', 'upload_date']
        if 'source' in df.columns:
            display_columns.append('source')
        
        st.dataframe(
            df[display_columns],
            use_container_width=True
        )
        
        # Quick delete individual resumes
        if not show_delete_options:
            st.markdown("💡 **Tip:** Enable 'Delete Mode' above to remove unwanted resumes")

def set_criteria_page():
    """Criteria setting page"""
    st.markdown('<h1 class="main-header">📋 Set Screening Criteria</h1>', unsafe_allow_html=True)
    
    # Load saved criteria section
    st.subheader("📚 Previously Saved Criteria")
    saved_criteria = load_criteria_from_database()
    
    if saved_criteria:
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_criteria = st.selectbox(
                "Load Previously Saved Criteria:",
                options=[None] + saved_criteria,
                format_func=lambda x: "Select saved criteria..." if x is None else f"{x['name']} ({x['created_date'].strftime('%Y-%m-%d')})",
                help="Choose from previously saved screening criteria"
            )
        
        with col2:
            if st.button("🔄 Refresh Criteria"):
                st.rerun()
        
        if selected_criteria:
            if st.button(f"📥 Load '{selected_criteria['name']}'"):
                st.session_state.current_criteria = selected_criteria['criteria']
                st.success(f"✅ Loaded criteria: {selected_criteria['name']}")
                st.rerun()
    else:
        st.info("No saved criteria found. Create new criteria below.")
    
    st.divider()
    
    # Role selection
    role_type = st.selectbox(
        "Select Role Type:",
        ["Technical", "Management", "Sales", "Custom"],
        help="Choose a role type to get pre-defined criteria templates"
    )

    # Criteria templates
    st.subheader("📋 Quick Templates")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🖥️ Software Engineer", use_container_width=True):
            st.session_state.current_criteria = {
                "job_title": "Software Engineer",
                "required_skills": ["Python", "JavaScript", "SQL"],
                "preferred_skills": ["React", "Node.js", "AWS"],
                "experience_years": 3,
                "education_requirements": "Bachelor's in Computer Science or related field"
            }
    
    with col2:
        if st.button("👔 Project Manager", use_container_width=True):
            st.session_state.current_criteria = {
                "job_title": "Project Manager",
                "required_skills": ["Project Management", "Agile", "Scrum"],
                "team_size": 5,
                "leadership_years": 2,
                "industry_experience": "Technology"
            }
    
    with col3:
        if st.button("💼 Sales Representative", use_container_width=True):
            st.session_state.current_criteria = {
                "job_title": "Sales Representative",
                "required_skills": ["Sales", "CRM", "Negotiation"],
                "sales_targets": "100K+ annual quota",
                "industry": "SaaS",
                "territory": "North America"
            }
    
    st.divider()
    
    # Custom criteria form
    st.subheader("🎯 Custom Criteria")
    
    with st.form("criteria_form"):
        # Basic information
        col1, col2 = st.columns(2)
        
        with col1:
            job_title = st.text_input("Job Title *", value=st.session_state.current_criteria.get("job_title", ""))
            experience_years = st.number_input("Minimum Experience (years)", min_value=0, max_value=50, 
                                             value=st.session_state.current_criteria.get("experience_years", 0))
        
        with col2:
            industry = st.text_input("Industry", value=st.session_state.current_criteria.get("industry", ""))
            education_requirements = st.text_input("Education Requirements", 
                                                  value=st.session_state.current_criteria.get("education_requirements", ""))
        
        # Skills
        st.subheader("Skills Requirements")
        col1, col2 = st.columns(2)
        
        with col1:
            required_skills = st.text_area("Required Skills (one per line)", 
                                         value="\n".join(st.session_state.current_criteria.get("required_skills", [])))
        
        with col2:
            preferred_skills = st.text_area("Preferred Skills (one per line)", 
                                          value="\n".join(st.session_state.current_criteria.get("preferred_skills", [])))
        
        # Submit button
        submitted = st.form_submit_button("💾 Save Criteria", use_container_width=True)
        
        if submitted:
            if not job_title:
                st.error("Job title is required!")
            else:
                # Build criteria dictionary
                criteria = {
                    "job_title": job_title,
                    "experience_years": experience_years,
                    "industry": industry,
                    "education_requirements": education_requirements,
                    "required_skills": [skill.strip() for skill in required_skills.split('\n') if skill.strip()],
                    "preferred_skills": [skill.strip() for skill in preferred_skills.split('\n') if skill.strip()],
                }
                
                # Save to session state and database
                st.session_state.current_criteria = criteria
                
                # Save criteria to database
                criteria_id = db_manager.save_criteria(
                    name=f"{job_title} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    description=f"Screening criteria for {job_title} position",
                    criteria_json=criteria
                )
                
                st.success("✅ Criteria saved successfully!")
    
    # Display current criteria
    if st.session_state.current_criteria:
        st.subheader("📋 Current Criteria")
        st.json(st.session_state.current_criteria)

def screen_resumes_page():
    """Resume screening page"""
    st.markdown('<h1 class="main-header">🔍 Screen Resumes</h1>', unsafe_allow_html=True)
    
    # Add refresh button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh from Database"):
            st.session_state.uploaded_resumes = load_resumes_from_database()
            st.rerun()
    
    # Check prerequisites
    if not st.session_state.uploaded_resumes:
        st.warning("⚠️ Please upload resumes first!")
        return
    
    if not st.session_state.current_criteria:
        st.warning("⚠️ Please set screening criteria first!")
        return
    
    # Environment check
    env_valid, env_error = validate_environment()
    if not env_valid:
        st.error(f"❌ Environment configuration error: {env_error}")
        return
    
    # Display current criteria
    with st.expander("📋 Current Screening Criteria", expanded=False):
        st.json(st.session_state.current_criteria)
    
    # Resume selection
    st.subheader("📄 Select Resumes to Screen")
    
    resume_options = {f"{resume['filename']} (ID: {resume['id']})": resume 
                     for resume in st.session_state.uploaded_resumes}
    
    selected_resume_keys = st.multiselect(
        "Choose resumes to screen:",
        options=list(resume_options.keys()),
        default=list(resume_options.keys())
    )
    
    selected_resumes = [resume_options[key] for key in selected_resume_keys]
    
    if selected_resumes:
        st.info(f"Selected {len(selected_resumes)} resume(s) for screening")
        
        # Start screening
        if st.button("🚀 Start Screening", type="primary", use_container_width=True):
            
            # Initialize database tables
            try:
                db_manager.create_tables()
            except Exception as e:
                st.error(f"Database initialization error: {str(e)}")
                return
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            screening_results = []
            
            # Individual processing
            for i, resume in enumerate(selected_resumes):
                progress = (i + 1) / len(selected_resumes)
                progress_bar.progress(progress)
                status_text.text(f"🔄 Screening {resume['filename']}...")
                
                try:
                    result = resume_screener.screen_resume(resume["text"], st.session_state.current_criteria)
                    
                    if result["success"]:
                        result["resume_id"] = resume["id"]
                        result["filename"] = resume["filename"]
                        screening_results.append(result)
                        
                        # Save to database
                        criteria_id = db_manager.save_criteria(
                            name=f"Screening - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                            description="Auto-generated screening criteria",
                            criteria_json=st.session_state.current_criteria
                        )
                        
                        db_manager.save_screening_result(
                            resume_id=resume["id"],
                            criteria_id=criteria_id,
                            overall_score=result["analysis_result"]["overall_score"],
                            category=result["analysis_result"]["category"],
                            detailed_analysis=result["analysis_result"]
                        )
                    else:
                        st.error(f"Error screening {resume['filename']}: {result.get('error', 'Unknown error')}")
                
                except Exception as e:
                    st.error(f"Error processing {resume['filename']}: {str(e)}")
            
            progress_bar.progress(1.0)
            status_text.text("✅ Screening completed!")
            
            # Update session state
            st.session_state.screening_results.extend(screening_results)
            
            # Display results summary
            if screening_results:
                st.success(f"✅ Successfully screened {len(screening_results)} resume(s)")
                
                # Quick summary
                scores = [result["analysis_result"]["overall_score"] for result in screening_results]
                categories = [result["analysis_result"]["category"] for result in screening_results]
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Average Score", f"{sum(scores)/len(scores):.1f}")
                with col2:
                    st.metric("Highest Score", f"{max(scores):.1f}")
                with col3:
                    st.metric("Excellent", categories.count("EXCELLENT"))
                with col4:
                    st.metric("Good", categories.count("GOOD"))

def view_results_page():
    """Results viewing page"""
    st.markdown('<h1 class="main-header">📊 View Results</h1>', unsafe_allow_html=True)
    
    if not st.session_state.screening_results:
        st.info("No screening results available. Please screen some resumes first.")
        return
    
    # Results overview
    st.subheader("📈 Results Overview")
    
    # Prepare data
    results_data = []
    for result in st.session_state.screening_results:
        analysis = result["analysis_result"]
        results_data.append({
            "Filename": result["filename"],
            "Overall Score": analysis["overall_score"],
            "Category": analysis["category"],
            "Technical Skills": analysis["detailed_analysis"].get("technical_skills_score", 0),
            "Experience": analysis["detailed_analysis"].get("experience_score", 0),
            "Education": analysis["detailed_analysis"].get("education_score", 0),
            "Cultural Fit": analysis["detailed_analysis"].get("cultural_fit_score", 0)
        })
    
    df = pd.DataFrame(results_data)
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Screened", len(df))
    with col2:
        st.metric("Average Score", f"{df['Overall Score'].mean():.1f}")
    with col3:
        st.metric("Top Score", f"{df['Overall Score'].max():.1f}")
    with col4:
        excellent_count = len(df[df['Category'] == 'EXCELLENT'])
        st.metric("Excellent Candidates", excellent_count)
    
    # Results table
    st.subheader("📋 Detailed Results")
    
    # Display results
    st.dataframe(
        df.style.format({
            'Overall Score': '{:.1f}',
            'Technical Skills': '{:.1f}',
            'Experience': '{:.1f}',
            'Education': '{:.1f}',
            'Cultural Fit': '{:.1f}'
        }),
        use_container_width=True
    )
    
    # Detailed analysis for selected resume
    st.subheader("🔍 Detailed Analysis")
    
    selected_filename = st.selectbox(
        "Select resume for detailed analysis:",
        options=df['Filename'].tolist()
    )
    
    if selected_filename:
        # Find the corresponding result
        selected_result = next(
            (result for result in st.session_state.screening_results 
             if result["filename"] == selected_filename), 
            None
        )
        
        if selected_result:
            analysis = selected_result["analysis_result"]
            detailed = analysis["detailed_analysis"]
            
            # Score breakdown
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Strengths:**")
                for strength in detailed.get("strengths", []):
                    st.write(f"• {strength}")
                
                st.markdown("**Key Highlights:**")
                for highlight in analysis.get("key_highlights", []):
                    st.write(f"• {highlight}")
            
            with col2:
                st.markdown("**Areas for Improvement:**")
                for weakness in detailed.get("weaknesses", []):
                    st.write(f"• {weakness}")
                
                if analysis.get("red_flags"):
                    st.markdown("**Red Flags:**")
                    for flag in analysis["red_flags"]:
                        st.write(f"⚠️ {flag}")
            
            # Recommendations
            st.markdown("**Recommendations:**")
            st.write(detailed.get("recommendations", "No specific recommendations provided."))

def main():
    """Main application function"""
    initialize_session_state()
    
    # Create sidebar and get selected page
    selected_page = create_sidebar()
    
    # Route to appropriate page
    if selected_page == "Upload Resumes":
        upload_resumes_page()
    elif selected_page == "Set Criteria":
        set_criteria_page()
    elif selected_page == "Screen Resumes":
        screen_resumes_page()
    elif selected_page == "View Results":
        view_results_page()

if __name__ == "__main__":
    main()
