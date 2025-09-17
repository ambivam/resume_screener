# AI-Enabled Resume Screener

A comprehensive AI-powered resume screening application built with Python, featuring GPT-4 integration, LangGraph workflows, MySQL database, and a modern Streamlit interface.

## 🚀 Features

- **AI-Powered Screening**: Uses GPT-4 for intelligent resume analysis and scoring
- **LangGraph Workflow**: Advanced workflow management for resume processing
- **Multi-Format Support**: Supports PDF, DOCX, and TXT resume formats
- **MySQL Database**: Persistent storage for resumes, criteria, and results
- **Interactive UI**: Modern Streamlit interface with real-time analytics
- **Batch Processing**: Screen multiple resumes simultaneously
- **Folder Upload**: Upload all resume files from a folder at once
- **Customizable Criteria**: Flexible screening criteria for different roles
- **Detailed Analytics**: Comprehensive visualizations and reporting
- **Export Functionality**: Export results to CSV and other formats

## 📋 Requirements

- Python 3.8+
- MySQL Server 5.7+
- OpenAI API Key (GPT-4 access)

## 🛠️ Installation

1. **Clone or download the project files**
   ```bash
   cd python_resume_screener
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   # source venv/bin/activate  # On macOS/Linux
   ```

3. **Install dependencies**
   
   **Option A: Install all at once (may fail on Python 3.13)**
   ```bash
   pip install -r requirements.txt
   ```
   
   **Option B: Install individually (recommended for Python 3.13)**
   ```bash
   # Core dependencies first
   pip install --upgrade pip setuptools wheel
   
   # Install packages one by one
   pip install streamlit
   pip install plotly
   pip install pandas numpy
   pip install python-dotenv
   pip install PyPDF2 python-docx
   pip install mysql-connector-python SQLAlchemy
   pip install openai langchain langchain-openai langgraph
   pip install streamlit-option-menu
   ```

4. **Set up MySQL database**
   - Install MySQL Server if not already installed
   - Create a new database for the application:
   ```sql
   CREATE DATABASE resume_screener;
   ```

5. **Configure environment variables**
   - Copy `.env.example` to `.env`
   - Fill in your configuration:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=your_mysql_username
   DB_PASSWORD=your_mysql_password
   DB_NAME=resume_screener
   ```

## 🚀 Usage

1. **Start the application**
   ```bash
   streamlit run streamlit_app.py
   ```

2. **Access the web interface**
   - Open your browser and go to `http://localhost:8501`

3. **Upload Resumes**
   - Navigate to "Upload Resumes"
   - Choose upload method:
     - **Individual Files**: Select one or more resume files (PDF, DOCX, TXT)
     - **Folder Upload**: Enter folder path to upload all resume files from a directory
   - Files will be automatically parsed and stored

4. **Set Screening Criteria**
   - Go to "Set Criteria"
   - Use quick templates or create custom criteria
   - Define job requirements, skills, experience, etc.

5. **Screen Resumes**
   - Navigate to "Screen Resumes"
   - Select resumes to analyze
   - Click "Start Screening" to begin AI analysis

6. **View Results**
   - Check "View Results" for detailed analysis
   - See scores, categories, and recommendations
   - Export results as needed

7. **Analytics**
   - Visit "Analytics" for visualizations
   - View score distributions and trends
   - Generate reports and insights

## 🏗️ Architecture

### Core Components

- **`streamlit_app.py`**: Main Streamlit application with UI components
- **`langgraph_workflow.py`**: LangGraph workflow for AI processing
- **`ai_prompts.py`**: GPT-4 prompt templates for different scenarios
- **`resume_parser.py`**: File parsing and text extraction
- **`database.py`**: MySQL database models and operations
- **`config.py`**: Configuration management

### Database Schema

- **`resumes`**: Stores uploaded resume files and extracted text
- **`screening_criteria`**: Stores different screening configurations
- **`screening_results`**: Stores AI analysis results and scores

### AI Workflow

1. **Input Validation**: Validates resume text and criteria
2. **Prompt Generation**: Creates role-specific prompts
3. **AI Analysis**: Processes with GPT-4
4. **Result Parsing**: Extracts structured data
5. **Storage**: Saves results to database

## 🎯 Screening Categories

The system categorizes candidates into:
- **EXCELLENT**: Top-tier candidates (80-100 score)
- **GOOD**: Strong candidates (60-79 score)
- **AVERAGE**: Adequate candidates (40-59 score)
- **BELOW_AVERAGE**: Weak candidates (20-39 score)
- **POOR**: Unsuitable candidates (0-19 score)

## 📊 Scoring Metrics

Each resume is evaluated on:
- **Overall Score** (0-100): Comprehensive assessment
- **Technical Skills**: Role-specific technical competencies
- **Experience**: Relevant work experience and progression
- **Education**: Educational background and qualifications
- **Cultural Fit**: Alignment with company values and culture

## 🔧 Customization

### Adding New Role Templates

Edit `streamlit_app.py` to add new quick templates:

```python
if st.button("🎨 UX Designer", use_container_width=True):
    st.session_state.current_criteria = {
        "job_title": "UX Designer",
        "required_skills": ["UI/UX Design", "Figma", "User Research"],
        "preferred_skills": ["Prototyping", "Adobe Creative Suite"],
        "experience_years": 2,
        "education_requirements": "Design-related degree preferred"
    }
```

### Custom Prompt Templates

Modify `ai_prompts.py` to add specialized prompts for specific industries or roles.

## 🛡️ Security Considerations

- Store API keys securely in environment variables
- Use strong MySQL credentials
- Implement proper access controls for production deployment
- Consider data privacy regulations (GDPR, CCPA) for resume data

## 🚨 Troubleshooting

### Common Issues

1. **Dependency Installation Errors**
   - **ModuleNotFoundError (e.g., 'plotly', 'pandas')**: Install missing packages individually
     ```bash
     pip install plotly
     pip install pandas numpy
     pip install streamlit-option-menu
     ```
   - **Pandas/NumPy compilation errors on Python 3.13**: Use pre-compiled wheels
     ```bash
     python -m pip install --upgrade pip setuptools wheel
     pip install --only-binary=all pandas numpy
     ```
   - **setuptools.build_meta error**: Upgrade setuptools first
     ```bash
     pip install --upgrade setuptools>=65.0.0
     ```
   - **Complete individual installation** (if requirements.txt fails):
     ```bash
     pip install --upgrade pip setuptools wheel
     pip install streamlit plotly pandas numpy python-dotenv
     pip install PyPDF2 python-docx mysql-connector-python SQLAlchemy
     pip install openai langchain langchain-openai langgraph
     pip install streamlit-option-menu
     ```

2. **Database Connection Error**
   - Verify MySQL is running
   - Check database credentials in `.env`
   - Ensure database exists
   - Test connection: `mysql -u username -p -h localhost`

3. **OpenAI API Error**
   - Verify API key is correct and has GPT-4 access
   - Check API quota and billing status
   - Test API key: `curl -H "Authorization: Bearer YOUR_API_KEY" https://api.openai.com/v1/models`

4. **File Upload Issues**
   - Check file format (PDF, DOCX, TXT only)
   - Verify file size is under 10MB
   - Ensure files are not corrupted
   - Check file permissions

5. **Import Errors**
   - Activate virtual environment: `venv\Scripts\activate`
   - Install all requirements with compatible versions
   - Check Python version compatibility (3.8+ recommended, 3.13 may need special handling)

6. **Streamlit Issues**
   - Clear Streamlit cache: `streamlit cache clear`
   - Check port availability (default 8501)
   - Run with specific port: `streamlit run streamlit_app.py --server.port 8502`

## 📈 Performance Optimization

- **Batch Processing**: Use for multiple resumes
- **Database Indexing**: Add indexes for frequently queried fields
- **Caching**: Implement Redis for session data
- **Async Processing**: Use Celery for background tasks

## 🔄 Future Enhancements

- [ ] Integration with ATS systems
- [ ] Email notifications for screening completion
- [ ] Advanced ML models for pre-screening
- [ ] Multi-language resume support
- [ ] Video resume analysis
- [ ] Integration with job boards
- [ ] Advanced reporting and dashboards
- [ ] Role-based access control
- [ ] API endpoints for external integrations

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
- Check the troubleshooting section
- Review the documentation
- Create an issue in the repository

## 🙏 Acknowledgments

- OpenAI for GPT-4 API
- LangChain and LangGraph teams
- Streamlit community
- MySQL development team
