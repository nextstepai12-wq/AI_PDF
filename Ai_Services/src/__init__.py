from src.models import StudyPlan, ParserResponse
from src.palestinian import list_institutions

__version__ = "2.0.0"

def parse_study_plan(pdf_path, strict=False, university_id=None):
    from main import _parse
    return _parse(pdf_path, strict, university_id)

__all__ = ["parse_study_plan", "StudyPlan", "ParserResponse", "list_institutions"]