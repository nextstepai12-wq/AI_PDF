"""
Adaptive Table Parser — presentation-form aware.
"""

import re
import unicodedata
import logging
from typing import List, Optional
import unicodedata
from src.palestinian import UniversityRules
from src.course_parser import _fix_arabic_order, parse_course_from_row
from src.models import Course, Semester, SemesterCreditSummary

logger = logging.getLogger(__name__)


def _norm(text: str) -> str:
    return unicodedata.normalize('NFKC', text)


def _contains(keyword: str, text: str) -> bool:
    nk = _norm(keyword)
    nt = _norm(text)
    return nk in nt or nk[::-1] in nt


def _is_header(row: List[str], rules: UniversityRules) -> bool:
    text = " ".join(row)
    count = 0
    for keywords in rules.header_keywords.values():
        for kw in keywords:
            if _contains(kw, text):
                count += 1
                break
    if re.search(r"س\.ع|ساعة|ساعات", _norm(text)):
        count += 1
    return count >= 2


def parse_table_to_courses(
    rows: List[str],
    rules: UniversityRules,
    year_number: int,
    semester_number: int,
) -> List[Course]:
    courses = []
    for row in rows:
        if not row or all(not c.strip() for c in row):
            continue
        if _is_header(row, rules):
            continue
        course = parse_course_from_row(row, rules, year_number, semester_number)
        if course:
            courses.append(course)
    return courses


def build_semester(
    courses: List[Course],
    year_number: int,
    semester_number: int,
    name_ar: str = "",
) -> Optional[Semester]:
    if not courses:
        return None

    seen, unique = set(), []
    for c in courses:
        if c.course_code not in seen:
            seen.add(c.course_code)
            unique.append(c)

    return Semester(
        semester_number=semester_number,
        name_ar=_fix_arabic_order(unicodedata.normalize('NFKC', name_ar)) if name_ar else "",
        year_number=year_number,
        summary=SemesterCreditSummary(
            total_credit_hours=sum(c.credit_hours.total for c in unique),
            total_theory_hours=sum(c.credit_hours.theory for c in unique),
            total_practical_hours=sum(c.credit_hours.practical for c in unique),
            course_count=len(unique),
        ),
        courses=unique,
    )