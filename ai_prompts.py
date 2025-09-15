"""
AI Prompt templates for resume screening using GPT-4
"""

class ResumeScreeningPrompts:
    """Collection of prompt templates for different screening scenarios"""
    
    @staticmethod
    def get_base_screening_prompt():
        """Base prompt for resume screening"""
        return """
You are an expert HR professional and resume screener with years of experience in talent acquisition. 
Your task is to analyze resumes against specific criteria and provide detailed, objective assessments.

IMPORTANT GUIDELINES:
1. Be objective and fair in your assessment
2. Focus on relevant qualifications and experience
3. Consider both hard skills (technical) and soft skills (communication, leadership)
4. Provide specific examples from the resume to support your scoring
5. Be consistent in your evaluation criteria
6. Consider career progression and growth potential
7. Account for different career paths and backgrounds

OUTPUT FORMAT:
Your response must be a valid JSON object with the following structure:
{
    "overall_score": <float between 0-100>,
    "category": "<EXCELLENT|GOOD|AVERAGE|BELOW_AVERAGE|POOR>",
    "detailed_analysis": {
        "strengths": ["list of key strengths"],
        "weaknesses": ["list of areas for improvement"],
        "technical_skills_score": <float between 0-100>,
        "experience_score": <float between 0-100>,
        "education_score": <float between 0-100>,
        "cultural_fit_score": <float between 0-100>,
        "recommendations": "detailed recommendations for this candidate"
    },
    "criteria_match": {
        "required_skills": <float between 0-100>,
        "preferred_skills": <float between 0-100>,
        "experience_level": <float between 0-100>,
        "education_requirements": <float between 0-100>
    },
    "key_highlights": ["most important points about this candidate"],
    "red_flags": ["any concerns or potential issues"]
}
"""

    @staticmethod
    def get_technical_role_prompt(job_title: str, required_skills: list, preferred_skills: list, 
                                experience_years: int, education_requirements: str):
        """Prompt for technical role screening"""
        base_prompt = ResumeScreeningPrompts.get_base_screening_prompt()
        
        technical_prompt = f"""
{base_prompt}

SPECIFIC ROLE REQUIREMENTS:
Job Title: {job_title}
Required Technical Skills: {', '.join(required_skills)}
Preferred Skills: {', '.join(preferred_skills)}
Minimum Experience: {experience_years} years
Education Requirements: {education_requirements}

TECHNICAL EVALUATION FOCUS:
1. Programming languages and frameworks mentioned
2. Project complexity and scale
3. Problem-solving approach
4. System design experience
5. Code quality and best practices awareness
6. Continuous learning and technology adaptation
7. Open source contributions or personal projects

Pay special attention to:
- Depth vs breadth of technical knowledge
- Hands-on experience vs theoretical knowledge
- Leadership in technical projects
- Mentoring and knowledge sharing
- Innovation and creative problem solving
"""
        return technical_prompt

    @staticmethod
    def get_management_role_prompt(job_title: str, team_size: int, required_skills: list, 
                                 industry_experience: str, leadership_years: int):
        """Prompt for management role screening"""
        base_prompt = ResumeScreeningPrompts.get_base_screening_prompt()
        
        management_prompt = f"""
{base_prompt}

SPECIFIC ROLE REQUIREMENTS:
Job Title: {job_title}
Team Size to Manage: {team_size} people
Required Skills: {', '.join(required_skills)}
Industry Experience: {industry_experience}
Leadership Experience: {leadership_years} years minimum

MANAGEMENT EVALUATION FOCUS:
1. Team leadership and people management experience
2. Strategic thinking and planning abilities
3. Budget and resource management
4. Stakeholder communication and relationship building
5. Change management and organizational development
6. Performance management and talent development
7. Cross-functional collaboration

Pay special attention to:
- Scale of teams and projects managed
- Measurable business impact and results
- Conflict resolution and decision-making
- Coaching and mentoring experience
- Cultural and organizational fit
"""
        return management_prompt

    @staticmethod
    def get_sales_role_prompt(job_title: str, sales_targets: str, industry: str, 
                            required_skills: list, territory: str):
        """Prompt for sales role screening"""
        base_prompt = ResumeScreeningPrompts.get_base_screening_prompt()
        
        sales_prompt = f"""
{base_prompt}

SPECIFIC ROLE REQUIREMENTS:
Job Title: {job_title}
Sales Targets/Quotas: {sales_targets}
Industry: {industry}
Required Skills: {', '.join(required_skills)}
Territory/Market: {territory}

SALES EVALUATION FOCUS:
1. Sales performance and quota achievement
2. Customer relationship building and management
3. Negotiation and closing skills
4. Market knowledge and competitive analysis
5. Pipeline management and forecasting
6. Prospecting and lead generation abilities
7. Product knowledge and consultative selling

Pay special attention to:
- Quantifiable sales achievements (numbers, percentages)
- Customer retention and expansion
- New market penetration
- Sales methodology and process adherence
- CRM and sales tool proficiency
"""
        return sales_prompt

    @staticmethod
    def get_custom_criteria_prompt(criteria_dict: dict):
        """Generate prompt based on custom criteria"""
        base_prompt = ResumeScreeningPrompts.get_base_screening_prompt()
        
        custom_prompt = f"""
{base_prompt}

CUSTOM SCREENING CRITERIA:
"""
        
        for key, value in criteria_dict.items():
            if isinstance(value, list):
                custom_prompt += f"{key.replace('_', ' ').title()}: {', '.join(value)}\n"
            else:
                custom_prompt += f"{key.replace('_', ' ').title()}: {value}\n"
        
        custom_prompt += """

EVALUATION INSTRUCTIONS:
Evaluate the resume against the above custom criteria. Weight each criterion based on its importance to the role.
Provide detailed analysis of how well the candidate matches each specified requirement.
Consider both explicit mentions and implicit evidence of the required qualifications.
"""
        
        return custom_prompt

    @staticmethod
    def get_diversity_inclusive_prompt():
        """Additional prompt guidelines for diversity and inclusion"""
        return """
DIVERSITY AND INCLUSION GUIDELINES:
1. Focus on qualifications, skills, and experience rather than personal characteristics
2. Value diverse educational backgrounds and career paths
3. Consider non-traditional routes to expertise
4. Recognize transferable skills from different industries
5. Be mindful of unconscious bias in language and assumptions
6. Value different perspectives and experiences
7. Consider potential rather than just current qualifications
"""

    @staticmethod
    def get_resume_analysis_prompt(resume_text: str, criteria: dict):
        """Complete prompt for resume analysis"""
        # Determine the best prompt based on criteria
        job_title = criteria.get('job_title', 'General Position')
        
        if 'technical_skills' in criteria or 'programming_languages' in criteria:
            prompt = ResumeScreeningPrompts.get_technical_role_prompt(
                job_title=job_title,
                required_skills=criteria.get('required_skills', []),
                preferred_skills=criteria.get('preferred_skills', []),
                experience_years=criteria.get('experience_years', 0),
                education_requirements=criteria.get('education_requirements', 'Any')
            )
        elif 'team_size' in criteria or 'leadership_experience' in criteria:
            prompt = ResumeScreeningPrompts.get_management_role_prompt(
                job_title=job_title,
                team_size=criteria.get('team_size', 1),
                required_skills=criteria.get('required_skills', []),
                industry_experience=criteria.get('industry_experience', 'Any'),
                leadership_years=criteria.get('leadership_years', 0)
            )
        elif 'sales_targets' in criteria or 'quota' in criteria:
            prompt = ResumeScreeningPrompts.get_sales_role_prompt(
                job_title=job_title,
                sales_targets=criteria.get('sales_targets', 'TBD'),
                industry=criteria.get('industry', 'Any'),
                required_skills=criteria.get('required_skills', []),
                territory=criteria.get('territory', 'TBD')
            )
        else:
            prompt = ResumeScreeningPrompts.get_custom_criteria_prompt(criteria)
        
        # Add diversity guidelines
        prompt += "\n\n" + ResumeScreeningPrompts.get_diversity_inclusive_prompt()
        
        # Add the resume text
        prompt += f"""

RESUME TO ANALYZE:
{resume_text}

Now analyze this resume against the specified criteria and provide your assessment in the required JSON format.
"""
        
        return prompt
