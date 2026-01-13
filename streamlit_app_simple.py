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
    
    # Note: Auto-refresh removed to prevent infinite loops
    # Users can manually refresh using the Clear Cache button

def refresh_session_data():
    """Refresh session state data from database"""
    st.session_state.uploaded_resumes = load_resumes_from_database()
    st.session_state.screening_results = load_screening_results_from_database()

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
            ["Upload Resumes", "Job Vacancies", "Candidate Profiles", "Set Criteria", "Screen Resumes", "View Results"]
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
                            # Refresh session state from database to ensure consistency
                            refresh_session_data()
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
    
    st.markdown("""
    <div class="info-box">
        <strong>Screening Options:</strong> Choose between traditional criteria-based screening or job vacancy-based screening.<br>
        <strong>Job Vacancy Screening:</strong> Uses comprehensive job vacancy JSON for more accurate matching<br>
        <strong>Traditional Screening:</strong> Uses custom criteria you define manually
    </div>
    """, unsafe_allow_html=True)
    
    # Add refresh button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh from Database"):
            st.session_state.uploaded_resumes = load_resumes_from_database()
            if 'job_vacancies' not in st.session_state:
                st.session_state.job_vacancies = load_job_vacancies_from_database()
            st.rerun()
    
    # Check prerequisites
    if not st.session_state.uploaded_resumes:
        st.warning("⚠️ Please upload resumes first!")
        return
    
    # Environment check
    env_valid, env_error = validate_environment()
    if not env_valid:
        st.error(f"❌ Environment configuration error: {env_error}")
        return
    
    # Initialize job vacancies if not present
    if 'job_vacancies' not in st.session_state:
        st.session_state.job_vacancies = load_job_vacancies_from_database()
    
    # Screening method selection
    st.subheader("🎯 Choose Screening Method")
    screening_method = st.radio(
        "Select screening approach:",
        ["💼 Job Vacancy Based", "👤 Candidate Profile Based", "📋 Traditional Criteria"],
        horizontal=False,
        help="Job Vacancy Based: Screen against job requirements | Candidate Profile Based: Check resume-profile consistency | Traditional: Use custom criteria"
    )
    
    selected_vacancy = None
    selected_profile = None
    use_criteria = False
    
    if screening_method == "💼 Job Vacancy Based":
        if not st.session_state.job_vacancies:
            st.warning("⚠️ No job vacancies found! Please add job vacancies first using the 'Job Vacancies' page.")
            return
        
        st.subheader("💼 Select Job Vacancy")
        vacancy_options = {
            f"ID {v['id']}: {v['group_name']} ({v.get('seniority', {}).get('valueItem', 'N/A')})": v 
            for v in st.session_state.job_vacancies
        }
        
        selected_vacancy_key = st.selectbox(
            "Choose job vacancy for screening:",
            options=list(vacancy_options.keys()),
            help="Select the job vacancy to screen resumes against"
        )
        
        if selected_vacancy_key:
            selected_vacancy = vacancy_options[selected_vacancy_key]
            
            # Display selected vacancy details
            with st.expander("💼 Selected Job Vacancy Details", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Position:** {selected_vacancy['group_name']}")
                    st.write(f"**Vacancy ID:** {selected_vacancy['vacancy_id']}")
                    st.write(f"**Positions Available:** {selected_vacancy['num_positions']}")
                    if selected_vacancy.get('seniority'):
                        st.write(f"**Seniority:** {selected_vacancy['seniority'].get('valueItem', 'N/A')}")
                
                with col2:
                    if selected_vacancy.get('skills'):
                        required_skills = [s['name'] for s in selected_vacancy['skills'] if s.get('isRequired')]
                        st.write(f"**Required Skills:** {len(required_skills)}")
                        preferred_skills = [s['name'] for s in selected_vacancy['skills'] if not s.get('isRequired')]
                        st.write(f"**Preferred Skills:** {len(preferred_skills)}")
                    
                    if selected_vacancy.get('languages'):
                        st.write(f"**Language Requirements:** {len(selected_vacancy['languages'])}")
                
                if selected_vacancy.get('job_activities'):
                    st.markdown("**Job Activities:**")
                    st.text_area("", value=selected_vacancy['job_activities'], height=100, disabled=True)
    
    elif screening_method == "👤 Candidate Profile Based":
        # Initialize candidate profiles if not present
        if 'candidate_profiles' not in st.session_state:
            st.session_state.candidate_profiles = load_candidate_profiles_from_database()
        
        if not st.session_state.candidate_profiles:
            st.warning("⚠️ No candidate profiles found! Please add candidate profiles first using the 'Candidate Profiles' page.")
            return
        
        st.subheader("👤 Select Candidate Profile")
        profile_options = {
            f"ID {p['id']}: {p['profile_description'][:50] + '...' if p.get('profile_description') and len(p['profile_description']) > 50 else (p.get('profile_description') or 'No description')}": p 
            for p in st.session_state.candidate_profiles
        }
        
        selected_profile_key = st.selectbox(
            "Choose candidate profile for consistency analysis:",
            options=list(profile_options.keys()),
            help="Select the candidate profile to check resume consistency against"
        )
        
        if selected_profile_key:
            selected_profile = profile_options[selected_profile_key]
            
            # Display selected profile details
            with st.expander("👤 Selected Candidate Profile Details", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Profile ID:** {selected_profile['profile_id']}")
                    st.write(f"**Currently Working:** {selected_profile.get('working', 'N/A')}")
                    
                    if selected_profile.get('regions'):
                        st.write("**Location Preferences:**")
                        for region in selected_profile['regions'][:2]:  # Show first 2
                            state = region.get('state', 'Unknown')
                            cities = region.get('city', [])
                            if cities:
                                st.write(f"• {state}: {', '.join(cities[:2])}")
                            else:
                                st.write(f"• {state}")
                
                with col2:
                    if selected_profile.get('experience_areas'):
                        st.write("**Experience Areas:**")
                        for area in selected_profile['experience_areas'][:3]:  # Show first 3
                            st.write(f"• {area.get('valueItem', 'N/A')}")
                    
                    if selected_profile.get('languages'):
                        st.write(f"**Languages:** {len(selected_profile['languages'])}")
                    
                    if selected_profile.get('salary_ranges'):
                        st.write(f"**Salary Expectations:** {len(selected_profile['salary_ranges'])}")
                
                if selected_profile.get('profile_description'):
                    st.markdown("**Profile Description:**")
                    st.text_area("", value=selected_profile['profile_description'], height=100, disabled=True)
    
    else:  # Traditional Criteria
        if not st.session_state.current_criteria:
            st.warning("⚠️ Please set screening criteria first using the 'Set Criteria' page!")
            return
        
        use_criteria = True
        
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
        
        # Show screening method summary
        if screening_method == "💼 Job Vacancy Based" and selected_vacancy:
            st.success(f"🎯 Ready to screen against: **{selected_vacancy['group_name']}**")
        elif screening_method == "👤 Candidate Profile Based" and selected_profile:
            st.success(f"🎯 Ready to analyze resume-profile consistency for: **{selected_profile['profile_description'][:50]}...**")
        elif use_criteria:
            st.success(f"🎯 Ready to screen with traditional criteria")
        
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
                    if screening_method == "💼 Job Vacancy Based" and selected_vacancy:
                        # Use vacancy-based screening
                        result = resume_screener.screen_resume_with_vacancy(
                            resume["text"], 
                            selected_vacancy['full_vacancy_json']
                        )
                        
                        if result["success"]:
                            result["resume_id"] = resume["id"]
                            result["filename"] = resume["filename"]
                            result["screening_method"] = "vacancy_based"
                            result["vacancy_id"] = selected_vacancy['id']
                            screening_results.append(result)
                            
                            # Save to database with vacancy reference
                            db_manager.save_screening_result(
                                resume_id=resume["id"],
                                overall_score=result["analysis_result"]["overall_score"],
                                category=result["analysis_result"]["category"],
                                detailed_analysis=result["analysis_result"],
                                vacancy_id=selected_vacancy['id'],
                                screening_type='vacancy_based'
                            )
                        else:
                            st.error(f"Error screening {resume['filename']}: {result.get('error', 'Unknown error')}")
                    
                    elif screening_method == "👤 Candidate Profile Based" and selected_profile:
                        # Use candidate profile-based screening
                        result = resume_screener.screen_resume_with_profile(
                            resume["text"], 
                            selected_profile['full_profile_json']
                        )
                        
                        if result["success"]:
                            result["resume_id"] = resume["id"]
                            result["filename"] = resume["filename"]
                            result["screening_method"] = "profile_based"
                            result["candidate_profile_id"] = selected_profile['id']
                            screening_results.append(result)
                            
                            # Save to database with profile reference
                            db_manager.save_screening_result(
                                resume_id=resume["id"],
                                overall_score=result["analysis_result"]["overall_score"],
                                category=result["analysis_result"]["category"],
                                detailed_analysis=result["analysis_result"],
                                candidate_profile_id=selected_profile['id'],
                                screening_type='profile_based'
                            )
                        else:
                            st.error(f"Error screening {resume['filename']}: {result.get('error', 'Unknown error')}")
                    
                    else:
                        # Use traditional criteria-based screening
                        result = resume_screener.screen_resume(resume["text"], st.session_state.current_criteria)
                        
                        if result["success"]:
                            result["resume_id"] = resume["id"]
                            result["filename"] = resume["filename"]
                            result["screening_method"] = "criteria_based"
                            screening_results.append(result)
                            
                            # Save to database with criteria reference
                            criteria_id = db_manager.save_criteria(
                                name=f"Screening - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                                description="Auto-generated screening criteria",
                                criteria_json=st.session_state.current_criteria
                            )
                            
                            db_manager.save_screening_result(
                                resume_id=resume["id"],
                                overall_score=result["analysis_result"]["overall_score"],
                                category=result["analysis_result"]["category"],
                                detailed_analysis=result["analysis_result"],
                                criteria_id=criteria_id,
                                screening_type='criteria_based'
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
    
    # Check for stale session data and show warning
    if (len(st.session_state.screening_results) > len(st.session_state.uploaded_resumes) * 2):
        st.warning("⚠️ Detected stale session data. Click 'Clear Cache' to fix this issue.")
    
    # Add refresh button to sync with database
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    with col2:
        if st.button("🔄 Refresh Data", help="Refresh results from database"):
            refresh_session_data()
            st.rerun()
    with col3:
        if st.button("🗑️ Clear Cache", help="Clear all cached data and reload"):
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            # Force cleanup of orphaned results before reloading
            if db_manager:
                db_manager.cleanup_orphaned_results()
            st.rerun()
    with col4:
        if st.button("🧹 Cleanup DB", help="Remove orphaned screening results"):
            if db_manager:
                with st.spinner("Cleaning up database..."):
                    success, message = db_manager.cleanup_orphaned_results()
                if success:
                    st.success(f"✅ {message}")
                    # Don't auto-refresh immediately, let user see the message
                    if st.button("🔄 Refresh After Cleanup"):
                        refresh_session_data()
                        st.rerun()
                else:
                    st.error(f"❌ {message}")
    with col5:
        if st.button("💥 Nuclear Reset", help="Delete ALL screening results and start fresh", type="secondary"):
            if st.button("⚠️ Confirm Nuclear Reset", help="This will delete ALL screening results!"):
                if db_manager:
                    try:
                        from database import ScreeningResult
                        session = db_manager.get_session()
                        deleted_count = session.query(ScreeningResult).delete()
                        session.commit()
                        session.close()
                        
                        # Clear session state
                        for key in list(st.session_state.keys()):
                            del st.session_state[key]
                        
                        st.success(f"✅ Nuclear reset complete! Deleted {deleted_count} screening results.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Nuclear reset failed: {str(e)}")
    
    if not st.session_state.screening_results:
        st.info("No screening results available. Please screen some resumes first.")
        return
    
    # Results overview
    st.subheader("📈 Results Overview")
    
    # Prepare data - only include results for resumes that still exist
    existing_resume_ids = {resume['id'] for resume in st.session_state.uploaded_resumes}
    results_data = []
    
    # Debug information
    with st.expander("🔧 Debug Information", expanded=False):
        st.write(f"**Total resumes in database:** {len(st.session_state.uploaded_resumes)}")
        st.write(f"**Total screening results in session:** {len(st.session_state.screening_results)}")
        st.write(f"**Existing resume IDs:** {sorted(existing_resume_ids)}")
        
        # Check for orphaned results in database directly
        if db_manager:
            try:
                all_results = db_manager.get_all_screening_results()
                all_resume_ids = [r.id for r in db_manager.get_all_resumes()]
                orphaned_in_db = [r for r in all_results if r.resume_id not in all_resume_ids]
                
                st.write(f"**Total screening results in database:** {len(all_results)}")
                st.write(f"**Orphaned results in database:** {len(orphaned_in_db)}")
                
                if orphaned_in_db:
                    st.write("**Orphaned resume IDs in database:**")
                    orphaned_ids = [r.resume_id for r in orphaned_in_db]
                    st.write(f"{sorted(set(orphaned_ids))}")
            except Exception as e:
                st.write(f"**Error checking database:** {str(e)}")
        
        # Show which results will be filtered out in UI
        filtered_results = []
        for result in st.session_state.screening_results:
            if result.get("resume_id") not in existing_resume_ids:
                filtered_results.append(f"{result['filename']} (ID: {result.get('resume_id')})")
        
        if filtered_results:
            st.write(f"**Results being filtered out in UI:** {len(filtered_results)}")
            for filtered in filtered_results:
                st.write(f"• {filtered}")
        else:
            st.write("**No results being filtered out in UI**")
    
    for result in st.session_state.screening_results:
        # Skip results for deleted resumes
        if result.get("resume_id") not in existing_resume_ids:
            continue
            
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
        # Find the corresponding result (only from valid results)
        valid_results = [
            result for result in st.session_state.screening_results 
            if result.get("resume_id") in existing_resume_ids
        ]
        selected_result = next(
            (result for result in valid_results 
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

def job_vacancies_page():
    """Job vacancy management page"""
    st.markdown('<h1 class="main-header">💼 Job Vacancies</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>Job Vacancy Management:</strong> Import job vacancies from JSON format to use for resume screening.<br>
        <strong>Supported format:</strong> Complete job vacancy JSON with skills, requirements, and benefits<br>
        <strong>Features:</strong> Store, view, and use job vacancies for targeted resume screening
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state for job vacancies
    if 'job_vacancies' not in st.session_state:
        st.session_state.job_vacancies = load_job_vacancies_from_database()
    
    # Tabs for different vacancy operations
    tab1, tab2, tab3 = st.tabs(["📥 Import Vacancy", "📋 View Vacancies", "🔧 Manage Vacancies"])
    
    with tab1:
        st.subheader("📥 Import Job Vacancy JSON")
        
        # JSON input methods
        input_method = st.radio(
            "Choose input method:",
            ["📝 Paste JSON", "📁 Upload JSON File"],
            horizontal=True
        )
        
        vacancy_json = None
        
        if input_method == "📝 Paste JSON":
            json_text = st.text_area(
                "Paste job vacancy JSON:",
                height=300,
                placeholder="""Paste your job vacancy JSON here...
Example:
{
    "id": 3255,
    "group": "Software Engineer Position",
    "jobActivities": "Develop and maintain software applications...",
    "skills": [...],
    "languages": [...],
    ...
}"""
            )
            
            if json_text.strip():
                try:
                    vacancy_json = json.loads(json_text)
                    st.success("✅ Valid JSON format detected")
                    
                    # Preview key information
                    st.markdown("**Preview:**")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**ID:** {vacancy_json.get('id', 'N/A')}")
                        st.write(f"**Position:** {vacancy_json.get('group', 'N/A')}")
                        st.write(f"**Positions Available:** {vacancy_json.get('numOfPositions', 1)}")
                    with col2:
                        st.write(f"**Seniority:** {vacancy_json.get('seniority', {}).get('valueItem', 'N/A')}")
                        st.write(f"**Visibility:** {vacancy_json.get('visibility', 'N/A')}")
                        skills_count = len(vacancy_json.get('skills', []))
                        st.write(f"**Skills Required:** {skills_count}")
                        
                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON format: {str(e)}")
        
        else:  # Upload JSON file
            uploaded_file = st.file_uploader(
                "Upload job vacancy JSON file:",
                type=['json'],
                help="Upload a JSON file containing job vacancy data"
            )
            
            if uploaded_file is not None:
                try:
                    json_content = uploaded_file.read().decode('utf-8')
                    vacancy_json = json.loads(json_content)
                    st.success("✅ JSON file loaded successfully")
                    
                    # Preview key information
                    st.markdown("**Preview:**")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**ID:** {vacancy_json.get('id', 'N/A')}")
                        st.write(f"**Position:** {vacancy_json.get('group', 'N/A')}")
                        st.write(f"**Positions Available:** {vacancy_json.get('numOfPositions', 1)}")
                    with col2:
                        st.write(f"**Seniority:** {vacancy_json.get('seniority', {}).get('valueItem', 'N/A')}")
                        st.write(f"**Visibility:** {vacancy_json.get('visibility', 'N/A')}")
                        skills_count = len(vacancy_json.get('skills', []))
                        st.write(f"**Skills Required:** {skills_count}")
                        
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    st.error(f"❌ Error reading JSON file: {str(e)}")
        
        # Save vacancy button
        if vacancy_json and st.button("💾 Save Job Vacancy", type="primary"):
            if db_manager:
                try:
                    vacancy_id = db_manager.save_job_vacancy(vacancy_json)
                    st.success(f"✅ Job vacancy saved successfully! (Database ID: {vacancy_id})")
                    
                    # Refresh session state
                    st.session_state.job_vacancies = load_job_vacancies_from_database()
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error saving job vacancy: {str(e)}")
            else:
                st.error("❌ Database connection not available")
    
    with tab2:
        st.subheader("📋 Current Job Vacancies")
        
        if not st.session_state.job_vacancies:
            st.info("No job vacancies found. Import a vacancy using the 'Import Vacancy' tab.")
        else:
            # Display vacancies in a table format
            vacancy_data = []
            for vacancy in st.session_state.job_vacancies:
                vacancy_data.append({
                    "Database ID": vacancy['id'],
                    "Vacancy ID": vacancy['vacancy_id'],
                    "Position": vacancy['group_name'] or "N/A",
                    "Seniority": vacancy.get('seniority', {}).get('valueItem', 'N/A') if vacancy.get('seniority') else 'N/A',
                    "Skills Count": len(vacancy.get('skills', [])) if vacancy.get('skills') else 0,
                    "Languages": len(vacancy.get('languages', [])) if vacancy.get('languages') else 0,
                    "Created": vacancy['created_at'].strftime('%Y-%m-%d %H:%M') if vacancy.get('created_at') else 'N/A'
                })
            
            df = pd.DataFrame(vacancy_data)
            st.dataframe(df, use_container_width=True)
            
            # Detailed view
            st.subheader("🔍 Detailed Vacancy View")
            selected_vacancy_id = st.selectbox(
                "Select vacancy for detailed view:",
                options=[v['id'] for v in st.session_state.job_vacancies],
                format_func=lambda x: f"ID {x}: {next(v['group_name'] for v in st.session_state.job_vacancies if v['id'] == x)}"
            )
            
            if selected_vacancy_id:
                selected_vacancy = next(v for v in st.session_state.job_vacancies if v['id'] == selected_vacancy_id)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Basic Information:**")
                    st.write(f"**Database ID:** {selected_vacancy['id']}")
                    st.write(f"**Original Vacancy ID:** {selected_vacancy['vacancy_id']}")
                    st.write(f"**Position:** {selected_vacancy['group_name']}")
                    st.write(f"**Number of Positions:** {selected_vacancy['num_positions']}")
                    st.write(f"**Visibility:** {selected_vacancy['visibility']}")
                    
                    if selected_vacancy.get('seniority'):
                        st.write(f"**Seniority:** {selected_vacancy['seniority'].get('valueItem', 'N/A')}")
                    
                    if selected_vacancy.get('created_by'):
                        creator = selected_vacancy['created_by']
                        st.write(f"**Created by:** {creator.get('firstName', '')} {creator.get('lastName', '')}")
                
                with col2:
                    st.markdown("**Requirements:**")
                    if selected_vacancy.get('skills'):
                        required_skills = [s['name'] for s in selected_vacancy['skills'] if s.get('isRequired')]
                        preferred_skills = [s['name'] for s in selected_vacancy['skills'] if not s.get('isRequired')]
                        
                        if required_skills:
                            st.write("**Required Skills:**")
                            for skill in required_skills:
                                st.write(f"• {skill}")
                        
                        if preferred_skills:
                            st.write("**Preferred Skills:**")
                            for skill in preferred_skills:
                                st.write(f"• {skill}")
                    
                    if selected_vacancy.get('languages'):
                        st.write("**Language Requirements:**")
                        for lang in selected_vacancy['languages']:
                            lang_info = lang.get('languageId', {})
                            level_info = lang.get('langLevelId', {})
                            st.write(f"• {lang_info.get('name', 'Unknown')} - {level_info.get('name', 'Unknown level')}")
                
                # Job activities
                if selected_vacancy.get('job_activities'):
                    st.markdown("**Job Activities:**")
                    st.text_area("", value=selected_vacancy['job_activities'], height=150, disabled=True)
    
    with tab3:
        st.subheader("🔧 Manage Job Vacancies")
        
        if not st.session_state.job_vacancies:
            st.info("No job vacancies to manage.")
        else:
            # Delete vacancy option
            st.markdown("**Delete Job Vacancy:**")
            vacancy_to_delete = st.selectbox(
                "Select vacancy to delete:",
                options=[0] + [v['id'] for v in st.session_state.job_vacancies],
                format_func=lambda x: "Select a vacancy..." if x == 0 else f"ID {x}: {next(v['group_name'] for v in st.session_state.job_vacancies if v['id'] == x)}"
            )
            
            if vacancy_to_delete != 0:
                if st.button("🗑️ Delete Selected Vacancy", type="secondary"):
                    if db_manager:
                        try:
                            # Note: You would need to implement delete_job_vacancy in DatabaseManager
                            st.warning("Delete functionality not yet implemented in database manager.")
                        except Exception as e:
                            st.error(f"❌ Error deleting vacancy: {str(e)}")
                    else:
                        st.error("❌ Database connection not available")
            
            # Refresh data button
            if st.button("🔄 Refresh Vacancy Data"):
                st.session_state.job_vacancies = load_job_vacancies_from_database()
                st.success("✅ Vacancy data refreshed")
                st.rerun()

def candidate_profiles_page():
    """Candidate profile management page"""
    st.markdown('<h1 class="main-header">👤 Candidate Profiles</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>Candidate Profile Management:</strong> Import candidate profiles/preferences from JSON format for bidirectional matching.<br>
        <strong>Supported format:</strong> Complete candidate profile JSON with preferences, skills, and requirements<br>
        <strong>Features:</strong> Store, view, and use candidate profiles for resume-profile consistency analysis
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state for candidate profiles
    if 'candidate_profiles' not in st.session_state:
        st.session_state.candidate_profiles = load_candidate_profiles_from_database()
    
    # Tabs for different profile operations
    tab1, tab2, tab3 = st.tabs(["📥 Import Profile", "📋 View Profiles", "🔧 Manage Profiles"])
    
    with tab1:
        st.subheader("📥 Import Candidate Profile JSON")
        
        # JSON input methods
        input_method = st.radio(
            "Choose input method:",
            ["📝 Paste JSON", "📁 Upload JSON File"],
            horizontal=True
        )
        
        profile_json = None
        
        if input_method == "📝 Paste JSON":
            json_text = st.text_area(
                "Paste candidate profile JSON:",
                height=300,
                placeholder="""Paste your candidate profile JSON here...
Example:
{
    "id": 1,
    "profileDescription": "Experienced Java backend developer...",
    "regions": [...],
    "salaryRanges": [...],
    "experienceAreas": [...],
    "languages": [...],
    ...
}"""
            )
            
            if json_text.strip():
                try:
                    profile_json = json.loads(json_text)
                    st.success("✅ Valid JSON format detected")
                    
                    # Preview key information
                    st.markdown("**Preview:**")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**ID:** {profile_json.get('id', 'N/A')}")
                        st.write(f"**Description:** {profile_json.get('profileDescription', 'N/A')[:100]}...")
                        st.write(f"**Currently Working:** {profile_json.get('working', 'N/A')}")
                    with col2:
                        regions_count = len(profile_json.get('regions', []))
                        st.write(f"**Location Preferences:** {regions_count}")
                        languages_count = len(profile_json.get('languages', []))
                        st.write(f"**Languages:** {languages_count}")
                        experience_areas_count = len(profile_json.get('experienceAreas', []))
                        st.write(f"**Experience Areas:** {experience_areas_count}")
                        
                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON format: {str(e)}")
        
        else:  # Upload JSON file
            uploaded_file = st.file_uploader(
                "Upload candidate profile JSON file:",
                type=['json'],
                help="Upload a JSON file containing candidate profile data"
            )
            
            if uploaded_file is not None:
                try:
                    json_content = uploaded_file.read().decode('utf-8')
                    profile_json = json.loads(json_content)
                    st.success("✅ JSON file loaded successfully")
                    
                    # Preview key information
                    st.markdown("**Preview:**")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**ID:** {profile_json.get('id', 'N/A')}")
                        st.write(f"**Description:** {profile_json.get('profileDescription', 'N/A')[:100]}...")
                        st.write(f"**Currently Working:** {profile_json.get('working', 'N/A')}")
                    with col2:
                        regions_count = len(profile_json.get('regions', []))
                        st.write(f"**Location Preferences:** {regions_count}")
                        languages_count = len(profile_json.get('languages', []))
                        st.write(f"**Languages:** {languages_count}")
                        experience_areas_count = len(profile_json.get('experienceAreas', []))
                        st.write(f"**Experience Areas:** {experience_areas_count}")
                        
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    st.error(f"❌ Error reading JSON file: {str(e)}")
        
        # Save profile button
        if profile_json and st.button("💾 Save Candidate Profile", type="primary"):
            if db_manager:
                try:
                    profile_id = db_manager.save_candidate_profile(profile_json)
                    st.success(f"✅ Candidate profile saved successfully! (Database ID: {profile_id})")
                    
                    # Refresh session state
                    st.session_state.candidate_profiles = load_candidate_profiles_from_database()
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error saving candidate profile: {str(e)}")
            else:
                st.error("❌ Database connection not available")
    
    with tab2:
        st.subheader("📋 Current Candidate Profiles")
        
        if not st.session_state.candidate_profiles:
            st.info("No candidate profiles found. Import a profile using the 'Import Profile' tab.")
        else:
            # Display profiles in a table format
            profile_data = []
            for profile in st.session_state.candidate_profiles:
                profile_data.append({
                    "Database ID": profile['id'],
                    "Profile ID": profile['profile_id'],
                    "Description": (profile['profile_description'] or "N/A")[:50] + "..." if profile.get('profile_description') and len(profile['profile_description']) > 50 else (profile.get('profile_description') or "N/A"),
                    "Working": profile.get('working', 'N/A'),
                    "Regions": len(profile.get('regions', [])) if profile.get('regions') else 0,
                    "Languages": len(profile.get('languages', [])) if profile.get('languages') else 0,
                    "Created": profile['created_at'].strftime('%Y-%m-%d %H:%M') if profile.get('created_at') else 'N/A'
                })
            
            df = pd.DataFrame(profile_data)
            st.dataframe(df, use_container_width=True)
            
            # Detailed view
            st.subheader("🔍 Detailed Profile View")
            selected_profile_id = st.selectbox(
                "Select profile for detailed view:",
                options=[p['id'] for p in st.session_state.candidate_profiles],
                format_func=lambda x: f"ID {x}: {next(p['profile_description'][:50] + '...' if p.get('profile_description') and len(p['profile_description']) > 50 else (p.get('profile_description') or 'No description') for p in st.session_state.candidate_profiles if p['id'] == x)}"
            )
            
            if selected_profile_id:
                selected_profile = next(p for p in st.session_state.candidate_profiles if p['id'] == selected_profile_id)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Basic Information:**")
                    st.write(f"**Database ID:** {selected_profile['id']}")
                    st.write(f"**Original Profile ID:** {selected_profile['profile_id']}")
                    st.write(f"**Currently Working:** {selected_profile.get('working', 'N/A')}")
                    
                    if selected_profile.get('regions'):
                        st.write("**Location Preferences:**")
                        for region in selected_profile['regions']:
                            state = region.get('state', 'Unknown')
                            cities = region.get('city', [])
                            if cities:
                                st.write(f"• {state}: {', '.join(cities)}")
                            else:
                                st.write(f"• {state}")
                
                with col2:
                    st.markdown("**Preferences:**")
                    if selected_profile.get('salary_ranges'):
                        st.write("**Salary Expectations:**")
                        for salary in selected_profile['salary_ranges']:
                            st.write(f"• {salary.get('valueItem', 'N/A')}")
                    
                    if selected_profile.get('experience_areas'):
                        st.write("**Experience Areas:**")
                        for area in selected_profile['experience_areas']:
                            st.write(f"• {area.get('valueItem', 'N/A')}")
                    
                    if selected_profile.get('hiring_types'):
                        st.write("**Employment Preferences:**")
                        for hiring_type in selected_profile['hiring_types']:
                            st.write(f"• {hiring_type.get('valueItem', 'N/A')}")
                
                # Profile description
                if selected_profile.get('profile_description'):
                    st.markdown("**Profile Description:**")
                    st.text_area("", value=selected_profile['profile_description'], height=150, disabled=True)
                
                # Languages
                if selected_profile.get('languages'):
                    st.markdown("**Language Skills:**")
                    for lang in selected_profile['languages']:
                        lang_info = lang.get('language', {})
                        level_info = lang.get('level', {})
                        st.write(f"• {lang_info.get('name', 'Unknown')} - {level_info.get('name', 'Unknown level')}")
    
    with tab3:
        st.subheader("🔧 Manage Candidate Profiles")
        
        if not st.session_state.candidate_profiles:
            st.info("No candidate profiles to manage.")
        else:
            # Delete profile option
            st.markdown("**Delete Candidate Profile:**")
            profile_to_delete = st.selectbox(
                "Select profile to delete:",
                options=[0] + [p['id'] for p in st.session_state.candidate_profiles],
                format_func=lambda x: "Select a profile..." if x == 0 else f"ID {x}: {next(p['profile_description'][:50] + '...' if p.get('profile_description') and len(p['profile_description']) > 50 else (p.get('profile_description') or 'No description') for p in st.session_state.candidate_profiles if p['id'] == x)}"
            )
            
            if profile_to_delete != 0:
                if st.button("🗑️ Delete Selected Profile", type="secondary"):
                    st.warning("Delete functionality not yet implemented in database manager.")
            
            # Refresh data button
            if st.button("🔄 Refresh Profile Data"):
                st.session_state.candidate_profiles = load_candidate_profiles_from_database()
                st.success("✅ Profile data refreshed")
                st.rerun()

def load_candidate_profiles_from_database():
    """Load all candidate profiles from database"""
    try:
        if db_manager is None:
            return []
        
        profiles = db_manager.get_all_candidate_profiles()
        profile_list = []
        
        for profile in profiles:
            profile_list.append({
                'id': profile.id,
                'profile_id': profile.profile_id,
                'profile_description': profile.profile_description,
                'working': profile.working,
                'regions': profile.regions,
                'salary_ranges': profile.salary_ranges,
                'experience_areas': profile.experience_areas,
                'languages': profile.languages,
                'academic_levels': profile.academic_levels,
                'hiring_types': profile.hiring_types,
                'updated_at_info': profile.updated_at_info,
                'created_by': profile.created_by,
                'modified_by': profile.modified_by,
                'full_profile_json': profile.full_profile_json,
                'created_at': profile.created_at
            })
        
        return profile_list
    except Exception as e:
        st.error(f"Error loading candidate profiles from database: {str(e)}")
        return []

def load_job_vacancies_from_database():
    """Load all job vacancies from database"""
    try:
        if db_manager is None:
            return []
        
        vacancies = db_manager.get_all_job_vacancies()
        vacancy_list = []
        
        for vacancy in vacancies:
            vacancy_list.append({
                'id': vacancy.id,
                'vacancy_id': vacancy.vacancy_id,
                'group_name': vacancy.group_name,
                'job_activities': vacancy.job_activities,
                'creation_date': vacancy.creation_date,
                'update_date': vacancy.update_date,
                'visibility': vacancy.visibility,
                'num_positions': vacancy.num_positions,
                'skills': vacancy.skills,
                'additional_software': vacancy.additional_software,
                'languages': vacancy.languages,
                'benefits': vacancy.benefits,
                'profile': vacancy.profile,
                'seniority': vacancy.seniority,
                'currency': vacancy.currency,
                'created_by': vacancy.created_by,
                'position_owner': vacancy.position_owner,
                'full_vacancy_json': vacancy.full_vacancy_json,
                'created_at': vacancy.created_at
            })
        
        return vacancy_list
    except Exception as e:
        st.error(f"Error loading job vacancies from database: {str(e)}")
        return []

def main():
    """Main application function"""
    initialize_session_state()
    
    # Create sidebar and get selected page
    selected_page = create_sidebar()
    
    # Route to appropriate page
    if selected_page == "Upload Resumes":
        upload_resumes_page()
    elif selected_page == "Job Vacancies":
        job_vacancies_page()
    elif selected_page == "Candidate Profiles":
        candidate_profiles_page()
    elif selected_page == "Set Criteria":
        set_criteria_page()
    elif selected_page == "Screen Resumes":
        screen_resumes_page()
    elif selected_page == "View Results":
        view_results_page()

if __name__ == "__main__":
    main()
