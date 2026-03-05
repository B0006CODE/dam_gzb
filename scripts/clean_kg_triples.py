import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


CAUSE_RELS = {"典型病因", "主要病因"}
ACTION_RELS = {"处置措施"}
OCCUR_RELS = {"发生于"}

# Heuristic patterns only for review candidates; they are not used to mutate triples.
PROBLEM_WORDS = re.compile(
    r"不足|缺陷|问题|老化|破坏|不完善|偏低|失效|渗漏|裂缝|沉降|冲刷|变形|损坏|隐患|不稳定|病害|失稳"
)
ACTION_WORDS = re.compile(
    r"加固|修复|重建|改造|更换|建设|完善|培训|修建|扩建|新建|治理|补强|疏浚|清淤|监测|处理|设置|提升|优化|维护|加高|衬砌|灌浆"
)


@dataclass
class TripleRow:
    line_no: int
    h: str
    r: str
    t: str

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.h, self.r, self.t)


def _load_rows(path: Path) -> tuple[list[TripleRow], dict]:
    stats = {
        "total_lines": 0,
        "bad_json_lines": [],
        "missing_keys_lines": [],
        "empty_field_lines": [],
    }
    rows: list[TripleRow] = []
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            stats["total_lines"] = idx
            s = line.strip()
            if not s:
                stats["empty_field_lines"].append(idx)
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                stats["bad_json_lines"].append(idx)
                continue
            if not all(k in obj for k in ("h", "r", "t")):
                stats["missing_keys_lines"].append(idx)
                continue
            h = str(obj.get("h", "")).strip()
            r = str(obj.get("r", "")).strip()
            t = str(obj.get("t", "")).strip()
            if not h or not r or not t:
                stats["empty_field_lines"].append(idx)
                continue
            rows.append(TripleRow(line_no=idx, h=h, r=r, t=t))
    return rows, stats


def _dedup_and_filter(rows: list[TripleRow]) -> tuple[list[TripleRow], dict]:
    deduped: list[TripleRow] = []
    seen: set[tuple[str, str, str]] = set()

    removed_self_loop: list[int] = []
    removed_duplicates: list[int] = []

    for row in rows:
        if row.h == row.t:
            removed_self_loop.append(row.line_no)
            continue
        if row.key in seen:
            removed_duplicates.append(row.line_no)
            continue
        seen.add(row.key)
        deduped.append(row)

    return deduped, {
        "removed_self_loop_lines": removed_self_loop,
        "removed_duplicate_lines": removed_duplicates,
    }


def _build_review_candidates(rows: list[TripleRow]) -> list[dict]:
    by_pair_and_rel: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    by_pair_relset: dict[tuple[str, str], set[str]] = defaultdict(set)

    for row in rows:
        by_pair_and_rel[(row.h, row.r, row.t)].append(row.line_no)
        by_pair_relset[(row.h, row.t)].add(row.r)

    candidates: list[dict] = []

    # 1) bidirectional occurs_in candidates
    occurs_pairs = {(row.h, row.t) for row in rows if row.r in OCCUR_RELS}
    seen_pair: set[tuple[str, str]] = set()
    for h, t in occurs_pairs:
        if (t, h) in occurs_pairs:
            canon = tuple(sorted([h, t]))
            if canon in seen_pair:
                continue
            seen_pair.add(canon)
            lines_ab = by_pair_and_rel.get((h, "发生于", t), [])
            lines_ba = by_pair_and_rel.get((t, "发生于", h), [])
            candidates.append(
                {
                    "category": "occurs_in_bidirectional",
                    "entity_a": h,
                    "entity_b": t,
                    "line_numbers_a_to_b": lines_ab,
                    "line_numbers_b_to_a": lines_ba,
                }
            )

    # 2) same pair with multiple relations
    for (h, t), rels in by_pair_relset.items():
        if len(rels) < 2:
            continue
        rels_sorted = sorted(rels)
        conflict = (
            ("处置措施" in rels and ("典型病因" in rels or "主要病因" in rels))
            or ("发生于" in rels and ("处置措施" in rels or "典型病因" in rels or "主要病因" in rels))
        )
        if not conflict:
            continue
        candidates.append(
            {
                "category": "pair_multi_relation_conflict",
                "h": h,
                "t": t,
                "relations": rels_sorted,
                "line_numbers": {
                    rel: by_pair_and_rel.get((h, rel, t), [])
                    for rel in rels_sorted
                },
            }
        )

    # 3) lexical suspicious relation-tail mismatch
    for row in rows:
        reason = None
        if row.r in ACTION_RELS and PROBLEM_WORDS.search(row.t):
            reason = "action_rel_but_tail_looks_problem"
        elif row.r in CAUSE_RELS and ACTION_WORDS.search(row.t):
            reason = "cause_rel_but_tail_looks_action"
        if reason:
            candidates.append(
                {
                    "category": "lexical_relation_tail_mismatch",
                    "line_no": row.line_no,
                    "h": row.h,
                    "r": row.r,
                    "t": row.t,
                    "reason": reason,
                }
            )

    return candidates


def _write_jsonl(path: Path, rows: list[TripleRow]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps({"h": row.h, "r": row.r, "t": row.t}, ensure_ascii=False) + "\n")


def _write_review_jsonl(path: Path, candidates: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for item in candidates:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean KG triples with conservative, high-confidence rules.")
    parser.add_argument("--input", default="kg_triples_temp.jsonl", help="Input triples jsonl file path")
    parser.add_argument("--output", default="kg_triples_cleaned.jsonl", help="Output cleaned triples jsonl path")
    parser.add_argument(
        "--review-output",
        default="kg_triples_review_candidates.jsonl",
        help="Output review candidates jsonl path",
    )
    parser.add_argument(
        "--stats-output",
        default="kg_triples_cleaning_stats.json",
        help="Output stats json path",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    review_path = Path(args.review_output)
    stats_path = Path(args.stats_output)

    rows, parse_stats = _load_rows(input_path)
    cleaned_rows, clean_stats = _dedup_and_filter(rows)
    review_candidates = _build_review_candidates(cleaned_rows)

    _write_jsonl(output_path, cleaned_rows)
    _write_review_jsonl(review_path, review_candidates)

    relation_counts = Counter(row.r for row in cleaned_rows)
    candidate_category_counts = Counter(item["category"] for item in review_candidates)
    stats = {
        "input": str(input_path),
        "output": str(output_path),
        "review_output": str(review_path),
        "parse": {
            "total_lines": parse_stats["total_lines"],
            "valid_rows": len(rows),
            "bad_json_count": len(parse_stats["bad_json_lines"]),
            "missing_keys_count": len(parse_stats["missing_keys_lines"]),
            "empty_field_count": len(parse_stats["empty_field_lines"]),
        },
        "cleaning": {
            "kept_rows": len(cleaned_rows),
            "removed_self_loop_count": len(clean_stats["removed_self_loop_lines"]),
            "removed_duplicate_count": len(clean_stats["removed_duplicate_lines"]),
            "removed_total": len(clean_stats["removed_self_loop_lines"]) + len(clean_stats["removed_duplicate_lines"]),
        },
        "cleaned_relation_counts": dict(relation_counts),
        "review_candidates": {
            "total_count": len(review_candidates),
            "category_counts": dict(candidate_category_counts),
        },
        "removed_self_loop_lines": clean_stats["removed_self_loop_lines"],
        "removed_duplicate_lines_sample": clean_stats["removed_duplicate_lines"][:100],
    }

    with stats_path.open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
