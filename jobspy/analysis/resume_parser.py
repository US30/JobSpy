# In jobspy/analysis/resume_parser.py

from pathlib import Path
import pypdf
import docx

def parse_resume(file_path: str) -> str:
    """
    Parses a resume file (.pdf or .docx) and returns its text content.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume file not found at: {file_path}")

    text = ""
    if path.suffix == ".pdf":
        try:
            reader = pypdf.PdfReader(path)
            for page in reader.pages:
                text += page.extract_text() or ""
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
            return ""
    elif path.suffix == ".docx":
        try:
            doc = docx.Document(path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            print(f"Error reading DOCX {file_path}: {e}")
            return ""
    else:
        raise ValueError("Unsupported file type. Please use .pdf or .docx.")
    
    return text.strip()