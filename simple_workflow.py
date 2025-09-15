import json
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from ai_prompts import ResumeScreeningPrompts
from config import config

class SimpleResumeScreener:
    """Simple resume screening without LangGraph complexity"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            api_key=config.OPENAI_API_KEY
        )
    
    def screen_resume(self, resume_text: str, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Screen a resume using GPT-4"""
        try:
            # Validate input
            if not resume_text or not resume_text.strip():
                return {
                    "success": False,
                    "error": "Resume text is empty or missing",
                    "analysis_result": {}
                }
            
            if not criteria or not isinstance(criteria, dict):
                return {
                    "success": False,
                    "error": "Screening criteria is missing or invalid",
                    "analysis_result": {}
                }
            
            if "job_title" not in criteria:
                return {
                    "success": False,
                    "error": "Job title is required in criteria",
                    "analysis_result": {}
                }
            
            # Generate prompt
            prompt = ResumeScreeningPrompts.get_resume_analysis_prompt(resume_text, criteria)
            
            # Call GPT-4
            message = HumanMessage(content=prompt)
            response = self.llm.invoke([message])
            
            # Parse response
            analysis_result = self._parse_response(response.content)
            
            return {
                "success": True,
                "error": "",
                "analysis_result": analysis_result,
                "messages": [
                    {"role": "system", "content": "Analysis completed successfully"}
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "analysis_result": {
                    "overall_score": 0,
                    "category": "ERROR",
                    "detailed_analysis": {
                        "strengths": [],
                        "weaknesses": ["Analysis failed due to error"],
                        "technical_skills_score": 0,
                        "experience_score": 0,
                        "education_score": 0,
                        "cultural_fit_score": 0,
                        "recommendations": f"Unable to analyze resume: {str(e)}"
                    },
                    "criteria_match": {
                        "required_skills": 0,
                        "preferred_skills": 0,
                        "experience_level": 0,
                        "education_requirements": 0
                    },
                    "key_highlights": [],
                    "red_flags": [f"Analysis error: {str(e)}"]
                }
            }
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse GPT-4 response to extract JSON"""
        try:
            # Find JSON in response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in the analysis response")
            
            json_str = response_text[json_start:json_end]
            analysis_result = json.loads(json_str)
            
            # Validate required fields
            required_fields = ["overall_score", "category", "detailed_analysis"]
            for field in required_fields:
                if field not in analysis_result:
                    raise ValueError(f"Missing required field in analysis: {field}")
            
            # Ensure score is within valid range
            score = analysis_result["overall_score"]
            if not isinstance(score, (int, float)) or score < 0 or score > 100:
                raise ValueError("Overall score must be a number between 0 and 100")
            
            # Validate category
            valid_categories = ["EXCELLENT", "GOOD", "AVERAGE", "BELOW_AVERAGE", "POOR"]
            if analysis_result["category"] not in valid_categories:
                raise ValueError(f"Invalid category. Must be one of: {', '.join(valid_categories)}")
            
            return analysis_result
            
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON parsing error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Response parsing error: {str(e)}")
    
    def batch_screen_resumes(self, resumes_data: list, criteria: Dict[str, Any]) -> list:
        """Screen multiple resumes"""
        results = []
        
        for resume_data in resumes_data:
            try:
                result = self.screen_resume(resume_data["text"], criteria)
                result["resume_id"] = resume_data.get("id")
                result["filename"] = resume_data.get("filename")
                results.append(result)
            except Exception as e:
                results.append({
                    "resume_id": resume_data.get("id"),
                    "filename": resume_data.get("filename"),
                    "error": str(e),
                    "success": False,
                    "analysis_result": {}
                })
        
        return results

# Initialize the simple screener
resume_screener = SimpleResumeScreener()
