#!/usr/bin/env python3
"""
Study Plan PDF Parser — Palestinian Universities
"""
import argparse
import logging
import sys
from pathlib import Path
from src.course_parser import _fix_arabic_order  # أضف هذا السطر
from src.config import OUTPUT_DIR, LOG_LEVEL
from src.models import (
    StudyPlan, Year, Semester, SemesterCreditSummary,
    ParserResponse, PlanStatistics,
)
from src.extractor import extract_pdf
from src.metadata_parser import parse_metadata
from src.table_parser import parse_table_to_courses, build_semester
from src.course_parser import parse_courses_from_text_lines
from src.validator import validate_plan, compute_statistics
from src.palestinian import detect_university, get_merged_rules, REGISTRY, DEFAULT_RULES

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("parser")


def _parse(pdf_path, strict=False, university_id=None) -> ParserResponse:
    pdf_path = Path(pdf_path)
    errors, warnings = [], []

    # 1. Extract
    try:
        extracted = extract_pdf(pdf_path)
    except FileNotFoundError as e:
        return ParserResponse(success=False, errors=[str(e)], source_file=pdf_path.name)
    except Exception as e:
        return ParserResponse(success=False, errors=[f"Extraction failed: {e}"], source_file=pdf_path.name)

    if not extracted.full_text.strip():
        return ParserResponse(success=False, errors=["PDF is empty"], source_file=pdf_path.name)

    # 2. Detect university
    if university_id:
        rules = DEFAULT_RULES
        for r in REGISTRY:
            if r.id == university_id:
                rules = r
                break
        rules = get_merged_rules(rules)
    else:
        detected = detect_university(extracted.full_text)
        rules = get_merged_rules(detected)

    logger.info(f"🏆 Institution: {rules.name_ar} ({rules.id})")

    # 3. Metadata
    metadata = parse_metadata(extracted.full_text, rules)
    contexts = metadata["semester_contexts"]

    # 4. Parse courses
    all_sems = []

    if extracted.tables:
        all_sems = _parse_from_tables(extracted, rules, contexts)
    if not all_sems:
        logger.warning("Falling back to text parsing")
        all_sems = _parse_from_text(extracted.full_text, rules, contexts)

    if not all_sems:
        return ParserResponse(success=False, errors=["No courses extracted"], source_file=pdf_path.name)

    # 5. Build
    years = _build_years(all_sems)
    plan = StudyPlan(
        university=metadata["university"],
        approval=metadata["approval"],
        program=metadata["program"],
        years=years,
        statistics=PlanStatistics(),
    )
    plan.statistics = compute_statistics(plan)

    # 6. Validate
    ok, errs, warns = validate_plan(plan)
    errors.extend(errs)
    warnings.extend(warns)
    if strict and warnings:
        errors.extend([f"[STRICT] {w}" for w in warnings])
        warnings.clear()

    success = len(errors) == 0
    logger.info(f"✅ {plan.statistics.total_courses} courses | {plan.statistics.total_credit_hours} hrs | {len(errors)} err | {len(warnings)} warn")

    return ParserResponse(
        success=success,
        data=plan,
        errors=errors,
        warnings=warnings,
        source_file=pdf_path.name,
    )


def _parse_from_tables(extracted, rules, contexts):
    sems = []
    if contexts:
        positions = [c["position"] for c in contexts] + [len(extracted.full_text)]
        for i, ctx in enumerate(contexts):
            best = _find_table(extracted.tables, ctx["position"], extracted.full_text)
            if best:
                courses = parse_table_to_courses(best.rows, rules, ctx["year"], ctx["semester"])
                if courses:
                    s = build_semester(courses, ctx["year"], ctx["semester"], ctx["text"])
                    if s:
                        sems.append(s)
                        best._used = True
        # Unused
        unused = [t for t in extracted.tables if not getattr(t, "_used", False)]
        _parse_sequential(unused, rules, sems)
    else:
        _parse_sequential(extracted.tables, rules, sems)
    sems.sort(key=lambda s: (s.year_number, s.semester_number))
    return sems


def _parse_from_text(full_text, rules, contexts):
    sems = []
    if contexts:
        positions = [c["position"] for c in contexts] + [len(full_text)]
        for i, ctx in enumerate(contexts):
            block = full_text[ctx["position"]:positions[i + 1]]
            courses = parse_courses_from_text_lines(block.split("\n"), rules, ctx["year"], ctx["semester"])
            if courses:
                s = build_semester(courses, ctx["year"], ctx["semester"], ctx["text"])
                if s:
                    sems.append(s)
    else:
        courses = parse_courses_from_text_lines(full_text.split("\n"), rules, 1, 1)
        if courses:
            s = build_semester(courses, 1, 1)
            if s:
                sems.append(s)
    return sems


def _find_table(tables, pos, text):
    best, best_dist = None, float("inf")
    for t in tables:
        if getattr(t, "_used", False):
            continue
        idx = tables.index(t)
        tpos = idx * max(1, len(text) // max(1, len(tables)))
        d = tpos - pos
        if 0 <= d < best_dist:
            best_dist, best = d, t
    return best


def _parse_sequential(tables, rules, sems):
    if sems:
        last = max(sems, key=lambda s: (s.year_number, s.semester_number))
        y, s = last.year_number, last.semester_number + 1
        if s > 2:
            s, y = 1, y + 1
    else:
        y, s = 1, 1
    for t in tables:
        if getattr(t, "_used", False):
            continue
        courses = parse_table_to_courses(t.rows, rules, y, s)
        if courses:
            sem = build_semester(courses, y, s)
            if sem:
                sems.append(sem)
                s += 1
                if s > 2:
                    s, y = 1, y + 1


def _build_years(sems):
    ymap = {}
    for s in sems:
        ymap.setdefault(s.year_number, []).append(s)
    return [Year(year_number=yn, semesters=sorted(ymap[yn], key=lambda s: s.semester_number)) for yn in sorted(ymap)]

def main():
    p = argparse.ArgumentParser(
        description="🇵🇸 Palestinian Study Plan Parser",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py plan.pdf
  python main.py plan.pdf --dump-tables
  python main.py plan.pdf -o result.json
  python main.py plan.pdf --university ucas_gaza --strict --verbose
  python main.py --list-institutions
        """,
    )
    p.add_argument("input", nargs="?", help="PDF path")
    p.add_argument("-o", "--output", default=None)
    p.add_argument("--output-dir", default=None)
    p.add_argument("--university", default=None, help="Force institution ID")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--list-institutions", action="store_true")
    p.add_argument("--dump-tables", action="store_true", help="Print raw table cells and exit")
    p.add_argument("--dump-text", action="store_true", help="Print extracted text and exit")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--verbose", action="store_true")

    args = p.parse_args()

    if args.quiet:
        logging.getLogger().setLevel(logging.CRITICAL)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.list_institutions:
        from src.palestinian import list_institutions
        print("\n🇵🇸 Registered Palestinian Institutions:\n")
        print(f"  {'ID':<16} {'Type':<12} {'Arabic Name'}")
        print(f"  {'─'*16} {'─'*12} {'─'*50}")
        for inst in list_institutions():
            print(f"  {inst['id']:<16} {inst['type']:<12} {inst['name_ar']}")
        print(f"\n  Total: {len(list_institutions())} institutions")
        return

    if not args.input:
        p.print_help()
        sys.exit(1)

    inp = Path(args.input)

    # ── Debug: dump raw tables ────────────────────────
    if args.dump_tables:
        from src.extractor import extract_pdf
        data = extract_pdf(inp)
        print(f"\n📄 Pages: {data.page_count} | Tables: {len(data.tables)}\n")
        for ti, table in enumerate(data.tables):
            print(f"═══ TABLE {ti+1} (page {table.page_number}, strategy={table.strategy}) ═══")
            for ri, row in enumerate(table.rows):
                cells_str = " | ".join(f'[{c}]' for c in row)
                print(f"  R{ri:02d}: {cells_str}")
            print()
        return

    # ── Debug: dump extracted text ─────────────────────
    if args.dump_text:
        from src.extractor import extract_pdf
        data = extract_pdf(inp)
        print(data.full_text)
        return

    # ── Normal parsing ────────────────────────────────
    if args.output:
        out = Path(args.output)
    elif args.output_dir:
        d = Path(args.output_dir)
        d.mkdir(parents=True, exist_ok=True)
        out = d / f"{inp.stem}.json"
    else:
        out = OUTPUT_DIR / f"{inp.stem}.json"

    response = _parse(args.input, args.strict, args.university)
    out.parent.mkdir(parents=True, exist_ok=True)
    response.warnings = []  # Don't include warnings in output JSON
    with open(out, "w", encoding="utf-8") as f:
        f.write(response.to_json())

    if response.data:
        s = response.data.statistics
        print(f"✅ {response.data.university.name_ar or 'Unknown'} | "
              f"{response.data.program.degree_label_ar} | "
              f"{s.total_courses} courses | {s.total_credit_hours} hrs | "
              f"{s.years_count}Y {s.semesters_count}S")
        print(f"   → {out}")
    if response.warnings:
        print(f"⚠️  {len(response.warnings)} warning(s)")
        for w in response.warnings[:5]:
            print(f"   - {w}")
        if len(response.warnings) > 5:
            print(f"   ... and {len(response.warnings)-5} more")
    if response.errors:
        print(f"❌ {len(response.errors)} error(s)")
        for e in response.errors:
            print(f"   - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()