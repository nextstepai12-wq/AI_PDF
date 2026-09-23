"""
Content-Based Course Detection — RTL + Presentation-Form + Visual-Order aware.
"""

import re
import unicodedata
import logging
from typing import Optional, List, Tuple

from src.palestinian import UniversityRules
from src.models import Course, CreditHours, CourseType

logger = logging.getLogger(__name__)

ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+")


def _norm(text: str) -> str:
    return unicodedata.normalize('NFKC', text)


def _contains(keyword: str, text: str) -> bool:
    nk = _norm(keyword)
    nt = _norm(text)
    return nk in nt or nk[::-1] in nt


def _fix_arabic_order(text: str) -> str:
    """Reverse visual LTR Arabic to logical reading order + fix brackets."""
    if not text or len(text) < 2:
        return text
    reversed_text = text[::-1]
    for old, new in [(')', '('), (']', '['), ('}', '{')]:
        reversed_text = reversed_text.replace(old, '\x00').replace(new, old).replace('\x00', new)
    return reversed_text


def parse_course_from_row(
    cells: List[str],
    rules: UniversityRules,
    year_number: int,
    semester_number: int,
) -> Optional[Course]:
    if not cells or all(not c.strip() for c in cells):
        return None

    row_text = " ".join(cells)

    skip = rules.skip_markers + [
        "الفصل الدراسي", "السنة الدراسية", "المستوى الدراسي",
        "المستوى", "الدراسية الخطة",
    ]
    for marker in skip:
        if _contains(marker, row_text):
            return None

    known_set = set(p.upper() for p in rules.prefixes)
    codes = _find_codes(cells, row_text, known_set)

    if not codes:
        return None

    main_prefix, main_num = codes[0]
    main_code = main_prefix + main_num

    name = _extract_name(cells, rules, main_code)
    if not name:
        return None
    name = _fix_arabic_order(_norm(name))

    # ── Credit hours: positional (3 cols before code) ──
    code_col = _find_code_column(cells, main_code)
    code_num_set = {n for _, n in codes}
    hours = _extract_hours_positional(cells, code_col, code_num_set)

    course_type = _extract_type(row_text, rules)
    prereqs = [p + n for p, n in codes[1:] if (p + n) != main_code]

    logger.debug(f"  {main_code} | {name} | {hours.total}/{hours.theory}/{hours.practical} | {course_type.value}")

    return Course(
        course_code=main_code,
        course_name_ar=name,
        credit_hours=hours,
        course_type=course_type,
        prerequisites=prereqs,
        semester_number=semester_number,
        year_number=year_number,
    )


# ═══════════════════════════════════════════════════════════════
#  Code Detection
# ═══════════════════════════════════════════════════════════════

def _find_code_column(cells: List[str], main_code: str) -> Optional[int]:
    """Find which column contains the main course code."""
    code_clean = main_code.replace(" ", "")
    for i, cell in enumerate(cells):
        if code_clean in cell.replace(" ", "").replace("-", "").replace("–", ""):
            return i
    return None


def _find_codes(cells: List[str], row_text: str, known_prefixes: set) -> List[Tuple[str, str]]:
    clean_matches = []
    mixed_matches = []

    for i, cell in enumerate(cells):
        stripped = cell.strip()
        clean = stripped.replace(" ", "").replace("-", "").replace("–", "")

        m = re.match(r"^([A-Za-z]{2,5})\s*(\d{3,5})$", stripped)
        if m:
            clean_matches.append((i, m.group(1).upper(), m.group(2)))
            continue
        m = re.match(r"^([A-Za-z]{2,5})(\d{3,5})$", clean)
        if m:
            clean_matches.append((i, m.group(1).upper(), m.group(2)))
            continue
        m = re.match(r"^(\d{3,5})\s*([A-Za-z]{2,5})$", stripped)
        if m:
            clean_matches.append((i, m.group(2).upper(), m.group(1)))
            continue
        m = re.match(r"^(\d{3,5})([A-Za-z]{2,5})$", clean)
        if m:
            clean_matches.append((i, m.group(2).upper(), m.group(1)))
            continue
        for m in re.finditer(r"([A-Za-z]{2,5})\s*[-–]?\s*(\d{3,5})", stripped):
            mixed_matches.append((i, m.group(1).upper(), m.group(2)))
        for m in re.finditer(r"(\d{3,5})\s*[-–]?\s*([A-Za-z]{2,5})", stripped):
            mixed_matches.append((i, m.group(2).upper(), m.group(1)))

    source = clean_matches or mixed_matches
    if not source:
        found = re.findall(r"\b([A-Za-z]{2,5})\s*[-–—]?\s*(\d{3,5})\b", row_text)
        if found:
            return [(p.upper(), n) for p, n in found]
        return _pair_adjacent(cells, known_prefixes)

    source.sort(key=lambda x: x[0], reverse=True)
    known = [(i, p, n) for i, p, n in source if p in known_prefixes]
    ordered = known if known else source

    seen, result = set(), []
    for _, p, n in ordered:
        code = p + n
        if code not in seen:
            seen.add(code)
            result.append((p, n))
    return result


def _pair_adjacent(cells: List[str], known_prefixes: set) -> List[Tuple[str, str]]:
    prefix_cells, number_cells = [], []
    for i, cell in enumerate(cells):
        clean = cell.strip().replace(" ", "")
        if re.match(r"^[A-Za-z]{2,5}$", clean):
            prefix_cells.append((i, clean.upper()))
        elif re.match(r"^[1-9]\d{3}$", clean):
            number_cells.append((i, clean))
    if not prefix_cells or not number_cells:
        return []
    pairs, used = [], set()
    for pi, prefix in prefix_cells:
        best_ni, best_dist = None, 999
        for ni, num in number_cells:
            if ni in used:
                continue
            dist = abs(pi - ni)
            if dist < best_dist:
                best_dist = dist
                best_ni = ni
        if best_ni is not None and best_dist <= 4:
            num = [n for i, n in number_cells if i == best_ni][0]
            pairs.append((prefix, num))
            used.add(best_ni)
    if not pairs:
        return []
    known = [(p, n) for p, n in pairs if p in known_prefixes]
    return known if known else pairs[:1]


# ═══════════════════════════════════════════════════════════════
#  Hours Extraction — positional when possible
# ═══════════════════════════════════════════════════════════════

def _safe_int(text: str) -> int:
    try:
        v = int(text.strip())
        return v if 0 <= v <= 9 else 0
    except (ValueError, AttributeError):
        return 0


def _extract_hours_positional(
    cells: List[str],
    code_col: Optional[int],
    code_nums: set,
) -> CreditHours:
    """
    Use column position: in UCAS-format tables, the 3 columns
    before the code column are: practical, theory, total.
    """
    # Positional extraction
    if code_col is not None and code_col >= 3:
        try:
            practical = _safe_int(cells[code_col - 3])
            theory = _safe_int(cells[code_col - 2])
            total = _safe_int(cells[code_col - 1])
            # Validate: all zeros likely means wrong columns
            if practical + theory + total > 0:
                return CreditHours(total=total, theory=theory, practical=practical)
        except IndexError:
            pass

    # Fallback: find small numbers in any cell
    return _extract_hours_fallback(cells, code_nums)


def _extract_hours_fallback(cells: List[str], code_nums: set) -> CreditHours:
    hour_candidates = []
    for cell in cells:
        clean = cell.strip()
        if re.match(r"^\d{1,2}$", clean):
            val = int(clean)
            if val not in code_nums and 0 <= val <= 6:
                hour_candidates.append(val)
    if not hour_candidates:
        return CreditHours(total=0, theory=0, practical=0)
    if len(hour_candidates) == 1:
        return CreditHours(total=hour_candidates[0], theory=hour_candidates[0], practical=0)
    if len(hour_candidates) == 2:
        a, b = sorted(hour_candidates)
        return CreditHours(total=max(a, b), theory=a, practical=max(0, b - a))
    if len(hour_candidates) >= 3:
        h = hour_candidates[-3:]
        if h[0] >= h[1] and h[0] >= h[2]:
            return CreditHours(total=h[0], theory=h[1], practical=h[2])
        if h[2] >= h[0] and h[2] >= h[1]:
            return CreditHours(total=h[2], theory=h[1], practical=h[0])
        return CreditHours(total=h[0], theory=h[1], practical=h[2])
    return CreditHours(total=0, theory=0, practical=0)


# ═══════════════════════════════════════════════════════════════
#  Name Extraction
# ═══════════════════════════════════════════════════════════════

def _extract_name(cells: List[str], rules: UniversityRules, main_code: str) -> str:
    type_keywords = set(rules.course_type_map.keys())
    candidates = []

    for cell in cells:
        cell_clean = cell.strip()
        if not cell_clean:
            continue
        c = cell_clean.replace(" ", "").replace("-", "")
        if re.match(r"^([A-Za-z]{2,5})(\d{3,5})$", c):
            continue
        if re.match(r"^(\d{3,5})([A-Za-z]{2,5})$", c):
            continue
        if re.match(r"^[A-Za-z]{2,5}$", cell_clean):
            continue
        if re.match(r"^\d+$", cell_clean):
            continue
        if _norm(cell_clean) in {_norm(k) for k in type_keywords}:
            continue
        if not ARABIC_RE.search(cell_clean):
            continue

        cleaned = cell_clean
        cleaned = re.sub(r"[A-Za-z]{2,5}\s*[-–]?\s*\d{3,5}", "", cleaned)
        cleaned = re.sub(r"\d{3,5}\s*[-–]?\s*[A-Za-z]{2,5}", "", cleaned)
        for kw in type_keywords:
            cleaned = _norm(cleaned).replace(_norm(kw), "")
        cleaned = re.sub(r"\b\d+\b", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        # Don't strip () — _fix_arabic_order needs them
        cleaned = cleaned.strip(" .,-–—:،,")

        if len(cleaned) >= 2:
            candidates.append(cleaned)

    if not candidates:
        return ""
    candidates.sort(key=len, reverse=True)
    if len(candidates[0]) > 60 and len(candidates) > 1:
        return candidates[1]
    return candidates[0]


# ═══════════════════════════════════════════════════════════════
#  Type Extraction
# ═══════════════════════════════════════════════════════════════

def _extract_type(row_text: str, rules: UniversityRules) -> CourseType:
    for ar_kw, en_val in rules.course_type_map.items():
        if _contains(ar_kw, row_text):
            try:
                return CourseType(en_val)
            except ValueError:
                continue
    return CourseType.SPECIALIZATION


# ═══════════════════════════════════════════════════════════════
#  Text Fallback
# ═══════════════════════════════════════════════════════════════

def parse_courses_from_text_lines(
    lines: List[str], rules: UniversityRules,
    year_number: int, semester_number: int,
) -> List[Course]:
    courses = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        cells = re.split(r"\s{2,}|\t+", line)
        if len(cells) < 2:
            cells = [line]
        course = parse_course_from_row(cells, rules, year_number, semester_number)
        if course:
            courses.append(course)
    return courses