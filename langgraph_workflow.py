import json
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from ai_prompts import ResumeScreeningPrompts
from config import config

class ResumeScreeningState(TypedDict):
    """State for the resume screening workflow"""
    resume_text: str
    criteria: Dict[str, Any]
    analysis_result: Dict[str, Any]
    messages: List[Dict[str, str]]
    error: str

class ResumeScreeningWorkflow:
    """LangGraph workflow for AI-powered resume screening"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            api_key=config.OPENAI_API_KEY
        )
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow"""
        workflow = StateGraph(ResumeScreeningState)
        
        # Add nodes
        workflow.add_node("validate_input", self._validate_input)
        workflow.add_node("generate_prompt", self._generate_prompt)
        workflow.add_node("analyze_resume", self._analyze_resume)
        workflow.add_node("parse_result", self._parse_result)
        workflow.add_node("handle_error", self._handle_error)
        
        # Add edges
        workflow.set_entry_point("validate_input")
        workflow.add_edge("validate_input", "generate_prompt")
        workflow.add_edge("generate_prompt", "analyze_resume")
        workflow.add_edge("analyze_resume", "parse_result")
        workflow.add_edge("parse_result", END)
        workflow.add_edge("handle_error", END)
        
        # Add conditional edges for error handling
        workflow.add_conditional_edges(
            "validate_input",
            self._check_validation,
            {
                "continue": "generate_prompt",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "analyze_resume",
            self._check_analysis,
            {
                "continue": "parse_result",
                "error": "handle_error"
            }
        )
        
        return workflow.compile()
    
    def _validate_input(self, state: ResumeScreeningState) -> ResumeScreeningState:
        """Validate input data"""
        try:
            resume_text = state.get("resume_text", "")
            if not resume_text or not resume_text.strip():
                state["error"] = "Resume text is empty or missing"
                return state
            
            if not state.get("criteria") or not isinstance(state["criteria"], dict):
                state["error"] = "Screening criteria is missing or invalid"
                return state
            
            # Check minimum criteria requirements
            required_fields = ["job_title"]
            missing_fields = [field for field in required_fields if field not in state["criteria"]]
            if missing_fields:
                state["error"] = f"Missing required criteria fields: {', '.join(missing_fields)}"
                return state
            
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append({"role": "system", "content": "Input validation successful"})
            return state
            
        except Exception as e:
            state["error"] = f"Validation error: {str(e)}"
            return state
    
    def _generate_prompt(self, state: ResumeScreeningState) -> ResumeScreeningState:
        """Generate the appropriate prompt for resume analysis"""
        try:
            prompt = ResumeScreeningPrompts.get_resume_analysis_prompt(
                state["resume_text"], 
                state["criteria"]
            )
            
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append({
                "role": "system", 
                "content": f"Generated prompt with {len(prompt)} characters"
            })
            state["generated_prompt"] = prompt
            return state
            
        except Exception as e:
            state["error"] = f"Prompt generation error: {str(e)}"
            return state
    
    def _analyze_resume(self, state: ResumeScreeningState) -> ResumeScreeningState:
        """Analyze resume using GPT-4"""
        try:
            prompt = state["generated_prompt"]
            
            # Create message for the LLM
            message = HumanMessage(content=prompt)
            
            # Get response from GPT-4
            response = self.llm.invoke([message])
            
            state["raw_analysis"] = response.content
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append({
                "role": "assistant", 
                "content": f"Analysis completed with {len(response.content)} characters"
            })
            
            return state
            
        except Exception as e:
            state["error"] = f"Analysis error: {str(e)}"
            return state
    
    def _parse_result(self, state: ResumeScreeningState) -> ResumeScreeningState:
        """Parse and validate the analysis result"""
        try:
            raw_analysis = state["raw_analysis"]
            
            # Try to extract JSON from the response
            json_start = raw_analysis.find('{')
            json_end = raw_analysis.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in the analysis response")
            
            json_str = raw_analysis[json_start:json_end]
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
            
            state["analysis_result"] = analysis_result
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append({
                "role": "system", 
                "content": f"Analysis parsed successfully. Score: {score}, Category: {analysis_result['category']}"
            })
            
            return state
            
        except json.JSONDecodeError as e:
            state["error"] = f"JSON parsing error: {str(e)}"
            return state
        except Exception as e:
            state["error"] = f"Result parsing error: {str(e)}"
            return state
    
    def _handle_error(self, state: ResumeScreeningState) -> ResumeScreeningState:
        """Handle errors in the workflow"""
        error_msg = state.get("error", "Unknown error occurred")
        if "messages" not in state:
            state["messages"] = []
        state["messages"].append({
            "role": "system", 
            "content": f"Error: {error_msg}"
        })
        
        # Create a default analysis result for errors
        state["analysis_result"] = {
            "overall_score": 0,
            "category": "ERROR",
            "detailed_analysis": {
                "strengths": [],
                "weaknesses": ["Analysis failed due to error"],
                "technical_skills_score": 0,
                "experience_score": 0,
                "education_score": 0,
                "cultural_fit_score": 0,
                "recommendations": f"Unable to analyze resume: {error_msg}"
            },
            "criteria_match": {
                "required_skills": 0,
                "preferred_skills": 0,
                "experience_level": 0,
                "education_requirements": 0
            },
            "key_highlights": [],
            "red_flags": [f"Analysis error: {error_msg}"]
        }
        
        return state
    
    def _check_validation(self, state: ResumeScreeningState) -> str:
        """Check if validation passed"""
        return "error" if state.get("error") else "continue"
    
    def _check_analysis(self, state: ResumeScreeningState) -> str:
        """Check if analysis was successful"""
        return "error" if state.get("error") else "continue"
    
    def screen_resume(self, resume_text: str, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Main method to screen a resume"""
        initial_state = {
            "resume_text": resume_text,
            "criteria": criteria,
            "analysis_result": {},
            "messages": [],
            "error": ""
        }
        
        # Run the workflow
        result = self.workflow.invoke(initial_state)
        
        return {
            "analysis_result": result["analysis_result"],
            "messages": result["messages"],
            "error": result.get("error", ""),
            "success": not bool(result.get("error"))
        }
    
    def batch_screen_resumes(self, resumes_data: List[Dict[str, Any]], criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Screen multiple resumes in batch"""
        results = []
        
        for i, resume_data in enumerate(resumes_data):
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

# Initialize the workflow
resume_workflow = ResumeScreeningWorkflow()
