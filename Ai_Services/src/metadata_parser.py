"""
Metadata extraction — NFKC + visual-order aware.
"""

import re
import unicodedata
import logging
from typing import List

from src.config import YEAR_MAP, SEMESTER_MAP, SEMESTER_ORDER_PATTERNS
from src.palestinian import UniversityRules
from src.models import (
    UniversityInfo, ApprovalInfo, ProgramInfo,
    DegreeType, CreditHoursBreakdown,
)

logger = logging.getLogger(__name__)


def _norm(text: str) -> str:
    return unicodedata.normalize('NFKC', text)


def _fix(text: str) -> str:
    """Reverse visual LTR Arabic to logical order."""
    if not text or len(text) < 2:
        return text
    r = text[::-1]
    for old, new in [(')', '('), (']', '['), ('}', '{')]:
        r = r.replace(old, '\x00').replace(new, old).replace('\x00', new)
    return r


def _m(keyword: str, text: str) -> bool:
    """Match keyword in text, trying both directions + NFKC."""
    nk = _norm(keyword)
    nt = _norm(text)
    return nk in nt or nk[::-1] in nt


def _first_match(pattern: str, text: str) -> int:
    # Try on normalized text
    nt = _norm(text)
    m = re.search(pattern, nt)
    if m:
        for g in m.groups():
            if g and g.isdigit():
                return int(g)
    # Try on reversed normalized text
    m = re.search(pattern, nt[::-1])
    if m:
        for g in m.groups():
            if g and g.isdigit():
                return int(g)
    return 0


def _first_match_text(pattern: str, text: str) -> str:
    nt = _norm(text)
    m = re.search(pattern, nt)
    if m:
        for g in m.groups():
            if g and g.strip():
                return g.strip()
    m = re.search(pattern, nt[::-1])
    if m:
        for g in m.groups():
            if g and g.strip():
                return _fix(g.strip())
    return ""


def parse_metadata(full_text: str, rules: UniversityRules) -> dict:
    return {
        "university": _extract_university(full_text, rules),
        "approval": _extract_approval(full_text, rules),
        "program": _extract_program(full_text, rules),
        "semester_contexts": _extract_semester_contexts(full_text),
    }


def _extract_university(text: str, rules: UniversityRules) -> UniversityInfo:
    info = UniversityInfo(detected_id=rules.id, institution_type=rules.institution_type)

    # Use the detected university's known names (already correct)
    info.name_ar = rules.name_ar
    info.name_en = rules.name_en
    info.college_ar = rules.name_ar if rules.institution_type == "college" else ""
    info.college_en = rules.name_en if rules.institution_type == "college" else ""

    # Try to find section from text
    nt = _norm(text)
    for pat in [r"القبول\s*و?التسجيل\s*قسم", r"الشؤون\s*الأكاديمية"]:
        m = re.search(pat, nt) or re.search(pat, nt[::-1])
        if m:
            info.section_ar = _fix(m.group(0))
            break

    return info


def _extract_approval(text: str, rules: UniversityRules) -> ApprovalInfo:
    info = ApprovalInfo()
    nt = _norm(text)

    m = re.search(rules.ucas_pattern, nt) or re.search(rules.ucas_pattern, nt[::-1])
    if m:
        info.ucas_code = (m.group(1) or m.group(2) or "")

    m = re.search(rules.version_pattern, nt) or re.search(rules.version_pattern, nt[::-1])
    if m:
        info.version = (m.group(1) or m.group(2) or "")

    for pat in [rules.date_pattern, r"(\d{1,2}/\d{1,2}/\d{4})"]:
        m = re.search(pat, nt) or re.search(pat, nt[::-1])
        if m:
            info.approval_date = next((g for g in m.groups() if g), "")
            if info.approval_date:
                break
    return info


def _extract_program(text: str, rules: UniversityRules) -> ProgramInfo:
    # Degree type
    degree_type, degree_label = DegreeType.BACHELOR, ""
    for dk, patterns in rules.degree_patterns.items():
        for p in patterns:
            if _m(p, text):
                degree_type = DegreeType(dk)
                degree_label = p
                break
        if degree_label:
            break

    # Credit breakdown
    breakdown = CreditHoursBreakdown(
        specialization=_first_match(rules.spec_hours_pattern, text),
        college=_first_match(rules.college_hours_pattern, text),
        university=_first_match(rules.univ_hours_pattern, text),
    )
    total_hours = _first_match(rules.total_hours_pattern, text)
    if not total_hours:
        m = re.search(r"(\d+)\s*ساعة\s*معتمدة", _norm(text))
        if m:
            total_hours = int(m.group(1))

    # Department
    department = ""
    for pat in [r"القسم\s*:?\s*(.+?)(?:\n|$)", r"قسم\s+([\u0600-\u06FF\s]+?)(?:\s*[-–:|]|\n|$)"]:
        raw = _first_match_text(pat, text)
        if raw:
            department = re.sub(r"^قسم\s*", "", raw).strip()
            for patterns in rules.degree_patterns.values():
                for p in patterns:
                    department = department.replace(p, "").strip()
            if len(department) >= 2:
                break

    # Specialization
    specialization = ""
    for pat in [r"الاختصاص\s*:?\s*(.+?)(?:\n|$)", r"التخصص\s*:?\s*(.+?)(?:\n|$)"]:
        raw = _first_match_text(pat, text)
        if raw:
            spec = raw
            for patterns in rules.degree_patterns.values():
                for p in patterns:
                    spec = spec.replace(p, "").strip()
            if department:
                spec = spec.replace(department, "").strip()
            spec = spec.strip("- –—: ,")
            if len(spec) >= 2:
                specialization = spec
                break

    return ProgramInfo(
        department_ar=department,
        specialization_ar=specialization,
        degree_type=degree_type,
        degree_label_ar=degree_label,
        total_credit_hours=total_hours,
        credit_hours_breakdown=breakdown,
    )


def _extract_semester_contexts(text: str) -> List[dict]:
    results = []
    nt = _norm(text)

    for pattern in SEMESTER_ORDER_PATTERNS:
        for m in re.finditer(pattern, nt):
            groups = m.groups()
            year_num, sem_num = None, None
            for g in groups:
                g = (g or "").strip()
                if g in YEAR_MAP:
                    year_num = YEAR_MAP[g]
                elif g in SEMESTER_MAP:
                    sem_num = SEMESTER_MAP[g]
                elif g.isdigit():
                    n = int(g)
                    if 1 <= n <= 5 and year_num is None:
                        year_num = n
                    elif 1 <= n <= 2 and sem_num is None:
                        sem_num = n
            if year_num or sem_num:
                # Fix the semester name to logical order
                name = _fix(m.group(0))
                results.append({
                    "year": year_num or 1,
                    "semester": sem_num or 1,
                    "position": m.start(),
                    "text": name,
                })

    seen, unique = set(), []
    for r in results:
        key = r["position"] // 10
        if key not in seen:
            seen.add(key)
            unique.append(r)
    unique.sort(key=lambda x: x["position"])
    return unique