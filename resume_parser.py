import PyPDF2
import docx
import io
import re
from typing import Optional, Dict, Any

class ResumeParser:
    """Class to handle parsing of different resume file formats"""
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.docx', '.txt']
    
    def extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF file"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            raise ValueError(f"Error reading PDF file: {str(e)}")
    
    def extract_text_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(io.BytesIO(file_content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise ValueError(f"Error reading DOCX file: {str(e)}")
    
    def extract_text_from_txt(self, file_content: bytes) -> str:
        """Extract text from TXT file"""
        try:
            return file_content.decode('utf-8').strip()
        except UnicodeDecodeError:
            try:
                return file_content.decode('latin-1').strip()
            except Exception as e:
                raise ValueError(f"Error reading TXT file: {str(e)}")
    
    def parse_resume(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Parse resume and extract text based on file type"""
        file_extension = filename.lower().split('.')[-1]
        
        if file_extension == 'pdf':
            text = self.extract_text_from_pdf(file_content)
        elif file_extension == 'docx':
            text = self.extract_text_from_docx(file_content)
        elif file_extension == 'txt':
            text = self.extract_text_from_txt(file_content)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
        
        # Basic text cleaning
        text = self.clean_text(text)
        
        # Extract basic information
        extracted_info = {
            'raw_text': text,
            'file_type': file_extension,
            'word_count': len(text.split()),
            'character_count': len(text)
        }
        
        return extracted_info
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might interfere with processing
        text = re.sub(r'[^\w\s@.-]', ' ', text)
        # Remove extra spaces
        text = ' '.join(text.split())
        return text.strip()
    
    def validate_file(self, filename: str, file_size: int, max_size_mb: int = 10) -> bool:
        """Validate file format and size"""
        file_extension = f".{filename.lower().split('.')[-1]}"
        
        if file_extension not in self.supported_formats:
            raise ValueError(f"Unsupported file format. Supported formats: {', '.join(self.supported_formats)}")
        
        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            raise ValueError(f"File size exceeds maximum limit of {max_size_mb}MB")
        
        return True

# Initialize parser
resume_parser = ResumeParser()
