import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
import json
import os
from datetime import datetime
from typing import Dict, List, Any

# Import our custom modules
from config import config
from database import db_manager
from resume_parser import resume_parser
from langgraph_workflow import resume_workflow

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
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 0.75rem;
        border-radius: 0.25rem;
        border: 1px solid #c3e6cb;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 0.75rem;
        border-radius: 0.25rem;
        border: 1px solid #f5c6cb;
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
        st.session_state.uploaded_resumes = []
    if 'screening_results' not in st.session_state:
        st.session_state.screening_results = []
    if 'current_criteria' not in st.session_state:
        st.session_state.current_criteria = {}

def validate_environment():
    """Validate environment configuration"""
    try:
        config.validate_config()
        return True, ""
    except ValueError as e:
        return False, str(e)

def create_sidebar():
    """Create application sidebar"""
    with st.sidebar:
        st.image("https://via.placeholder.com/200x100/1f77b4/ffffff?text=AI+Resume+Screener", width=200)
        
        # Environment status
        env_valid, env_error = validate_environment()
        if env_valid:
            st.success("✅ Environment configured")
        else:
            st.error(f"❌ Configuration error: {env_error}")
            st.info("Please check your .env file and ensure all required variables are set.")
        
        # Navigation menu
        selected = option_menu(
            menu_title="Navigation",
            options=["Upload Resumes", "Set Criteria", "Screen Resumes", "View Results", "Analytics"],
            icons=["upload", "gear", "search", "table", "bar-chart"],
            menu_icon="list",
            default_index=0,
        )
        
        # Statistics
        st.markdown("### 📊 Statistics")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Uploaded", len(st.session_state.uploaded_resumes))
        with col2:
            st.metric("Screened", len(st.session_state.screening_results))
        
        return selected

def upload_resumes_page():
    """Resume upload page"""
    st.markdown('<h1 class="main-header">📄 Upload Resumes</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>Supported formats:</strong> PDF, DOCX, TXT<br>
        <strong>Maximum file size:</strong> 10MB per file<br>
        <strong>Batch upload:</strong> Upload multiple files at once
    </div>
    """, unsafe_allow_html=True)
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose resume files",
        type=['pdf', 'docx', 'txt'],
        accept_multiple_files=True,
        help="Upload one or more resume files for screening"
    )
    
    if uploaded_files:
        st.subheader("📋 Processing Files")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        processed_resumes = []
        
        for i, uploaded_file in enumerate(uploaded_files):
            try:
                # Update progress
                progress = (i + 1) / len(uploaded_files)
                progress_bar.progress(progress)
                status_text.text(f"Processing {uploaded_file.name}...")
                
                # Validate file
                file_content = uploaded_file.read()
                resume_parser.validate_file(uploaded_file.name, len(file_content), config.MAX_FILE_SIZE_MB)
                
                # Parse resume
                parsed_resume = resume_parser.parse_resume(file_content, uploaded_file.name)
                
                # Save to database
                resume_id = db_manager.save_resume(
                    filename=uploaded_file.name,
                    text=parsed_resume['raw_text'],
                    file_size=len(file_content),
                    file_type=parsed_resume['file_type']
                )
                
                processed_resumes.append({
                    'id': resume_id,
                    'filename': uploaded_file.name,
                    'text': parsed_resume['raw_text'],
                    'word_count': parsed_resume['word_count'],
                    'file_type': parsed_resume['file_type'],
                    'upload_date': datetime.now()
                })
                
            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")
        
        # Update session state
        st.session_state.uploaded_resumes.extend(processed_resumes)
        
        progress_bar.progress(1.0)
        status_text.text("✅ All files processed successfully!")
        
        # Display results
        if processed_resumes:
            st.success(f"Successfully processed {len(processed_resumes)} resume(s)")
            
            # Show summary table
            df = pd.DataFrame(processed_resumes)
            st.dataframe(
                df[['filename', 'word_count', 'file_type', 'upload_date']],
                use_container_width=True
            )
    
    # Show existing uploads
    if st.session_state.uploaded_resumes:
        st.subheader("📚 Previously Uploaded Resumes")
        df = pd.DataFrame(st.session_state.uploaded_resumes)
        st.dataframe(
            df[['filename', 'word_count', 'file_type', 'upload_date']],
            use_container_width=True
        )

def set_criteria_page():
    """Screening criteria configuration page"""
    st.markdown('<h1 class="main-header">⚙️ Set Screening Criteria</h1>', unsafe_allow_html=True)
    
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
                    result = resume_workflow.screen_resume(resume["text"], st.session_state.current_criteria)
                    
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

def analytics_page():
    """Analytics and visualization page"""
    st.markdown('<h1 class="main-header">📊 Analytics</h1>', unsafe_allow_html=True)
    
    if not st.session_state.screening_results:
        st.info("No data available for analytics. Please screen some resumes first.")
        return
    
    # Prepare data
    results_data = []
    for result in st.session_state.screening_results:
        analysis = result["analysis_result"]
        results_data.append({
            "filename": result["filename"],
            "overall_score": analysis["overall_score"],
            "category": analysis["category"]
        })
    
    df = pd.DataFrame(results_data)
    
    # Score distribution
    st.subheader("📈 Score Distribution")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Histogram of overall scores
        fig_hist = px.histogram(
            df, 
            x="overall_score", 
            nbins=20,
            title="Overall Score Distribution",
            labels={"overall_score": "Overall Score", "count": "Number of Candidates"}
        )
        fig_hist.update_layout(showlegend=False)
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        # Category distribution
        category_counts = df['category'].value_counts()
        fig_pie = px.pie(
            values=category_counts.values,
            names=category_counts.index,
            title="Category Distribution"
        )
        st.plotly_chart(fig_pie, use_container_width=True)

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
    elif selected_page == "Analytics":
        analytics_page()

if __name__ == "__main__":
    main()
