import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


PROBLEM_WORDS = re.compile(
    r"不足|缺陷|问题|老化|破坏|不完善|偏低|失效|渗漏|裂缝|沉降|冲刷|变形|损坏|隐患|不稳定|病害|失稳|异常|缺失|开裂|腐蚀|锈蚀|断裂"
)
COMPONENT_WORDS = re.compile(
    r"坝|闸|洞|渠|道|管|墙|坡|基|肩|体|堤|桥|门|机|设施|系统|结构|建筑物|公路|隧洞|输水|溢洪|泄洪|涵管|排水|护坡|护岸|防汛"
)
HEIGHT_TERMS = {"低坝", "中坝", "高坝", "特高坝"}
DAM_TYPES = {"土石坝", "重力坝", "拱坝"}
DAM_PARTS = {"坝体", "坝坡", "坝基", "坝肩", "坝顶"}


@dataclass
class Triple:
    line_no: int
    h: str
    r: str
    t: str

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.h, self.r, self.t)


def load_triples(path: Path) -> list[Triple]:
    triples: list[Triple] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            h = str(obj["h"]).strip()
            r = str(obj["r"]).strip()
            t = str(obj["t"]).strip()
            if h and r and t:
                triples.append(Triple(i, h, r, t))
    return triples


def normalize_height_direction(triples: list[Triple]) -> tuple[list[Triple], list[dict]]:
    out: list[Triple] = []
    actions: list[dict] = []
    for tr in triples:
        if tr.r == "典型坝高" and tr.h in HEIGHT_TERMS and tr.t not in HEIGHT_TERMS:
            swapped = Triple(tr.line_no, tr.t, tr.r, tr.h)
            out.append(swapped)
            actions.append(
                {
                    "action": "swap_typical_height_direction",
                    "line_no": tr.line_no,
                    "before": {"h": tr.h, "r": tr.r, "t": tr.t},
                    "after": {"h": swapped.h, "r": swapped.r, "t": swapped.t},
                }
            )
        else:
            out.append(tr)
    return out, actions


def build_entity_context(triples: list[Triple]) -> dict:
    ctx = {
        "tail_of_defect": defaultdict(int),
        "head_of_common_defect": defaultdict(int),
        "head_of_meta": defaultdict(int),
    }
    for tr in triples:
        if tr.r in {"常见缺陷", "典型缺陷"}:
            ctx["tail_of_defect"][tr.t] += 1
            ctx["head_of_common_defect"][tr.h] += 1
        if tr.r in {"所属环境", "所属地质", "典型坝高"}:
            ctx["head_of_meta"][tr.h] += 1
    return ctx


def score_direction(src: str, dst: str, ctx: dict) -> int:
    score = 0
    if PROBLEM_WORDS.search(src):
        score += 2
    if COMPONENT_WORDS.search(dst):
        score += 2
    score += min(3, ctx["tail_of_defect"][src])
    score += min(3, ctx["head_of_common_defect"][dst])
    score += 1 if ctx["head_of_meta"][dst] > 0 else 0
    return score


def resolve_bidirectional_occurs(triples: list[Triple]) -> tuple[list[Triple], list[dict], list[dict]]:
    pair_to_occurs_rows: dict[tuple[str, str], list[int]] = defaultdict(list)
    for idx, tr in enumerate(triples):
        if tr.r == "发生于":
            pair_to_occurs_rows[(tr.h, tr.t)].append(idx)

    ctx = build_entity_context(triples)
    actions: list[dict] = []
    unresolved: list[dict] = []
    remove_indices: set[int] = set()
    visited: set[tuple[str, str]] = set()

    for (a, b), rows_ab in pair_to_occurs_rows.items():
        if (a, b) in visited or (b, a) in visited:
            continue
        rows_ba = pair_to_occurs_rows.get((b, a), [])
        if not rows_ba:
            continue
        visited.add((a, b))
        visited.add((b, a))

        score_ab = score_direction(a, b, ctx)
        score_ba = score_direction(b, a, ctx)

        # 结构层级特判：坝体部位 与 坝型，保留“部位 -> 坝型”
        if a in DAM_TYPES and b in DAM_PARTS:
            for ridx in rows_ab:
                remove_indices.add(ridx)
            actions.append(
                {
                    "action": "remove_bidirectional_occurs_by_dam_hierarchy",
                    "keep": {"h": b, "r": "发生于", "t": a},
                    "remove": {"h": a, "r": "发生于", "t": b},
                    "remove_line_no": [triples[r].line_no for r in rows_ab],
                    "reason": "dam_part_to_dam_type_preferred",
                }
            )
            continue
        if b in DAM_TYPES and a in DAM_PARTS:
            for ridx in rows_ba:
                remove_indices.add(ridx)
            actions.append(
                {
                    "action": "remove_bidirectional_occurs_by_dam_hierarchy",
                    "keep": {"h": a, "r": "发生于", "t": b},
                    "remove": {"h": b, "r": "发生于", "t": a},
                    "remove_line_no": [triples[r].line_no for r in rows_ba],
                    "reason": "dam_part_to_dam_type_preferred",
                }
            )
            continue

        # 只有分差足够大才自动删除，避免误杀
        if score_ab - score_ba >= 2:
            for ridx in rows_ba:
                remove_indices.add(ridx)
            actions.append(
                {
                    "action": "remove_bidirectional_occurs_reverse",
                    "keep": {"h": a, "r": "发生于", "t": b},
                    "remove": {"h": b, "r": "发生于", "t": a},
                    "remove_line_no": [triples[r].line_no for r in rows_ba],
                    "score_keep": score_ab,
                    "score_remove": score_ba,
                }
            )
        elif score_ba - score_ab >= 2:
            for ridx in rows_ab:
                remove_indices.add(ridx)
            actions.append(
                {
                    "action": "remove_bidirectional_occurs_reverse",
                    "keep": {"h": b, "r": "发生于", "t": a},
                    "remove": {"h": a, "r": "发生于", "t": b},
                    "remove_line_no": [triples[r].line_no for r in rows_ab],
                    "score_keep": score_ba,
                    "score_remove": score_ab,
                }
            )
        else:
            unresolved.append(
                {
                    "category": "unresolved_bidirectional_occurs",
                    "a_to_b": {"h": a, "r": "发生于", "t": b, "line_no": [triples[r].line_no for r in rows_ab]},
                    "b_to_a": {"h": b, "r": "发生于", "t": a, "line_no": [triples[r].line_no for r in rows_ba]},
                    "score_a_to_b": score_ab,
                    "score_b_to_a": score_ba,
                }
            )

    kept = [tr for idx, tr in enumerate(triples) if idx not in remove_indices]
    return kept, actions, unresolved


def dedup_triples(triples: list[Triple]) -> tuple[list[Triple], list[int]]:
    seen: set[tuple[str, str, str]] = set()
    out: list[Triple] = []
    dropped_line_no: list[int] = []
    for tr in triples:
        if tr.key in seen:
            dropped_line_no.append(tr.line_no)
            continue
        seen.add(tr.key)
        out.append(tr)
    return out, dropped_line_no


def write_jsonl(path: Path, triples: list[Triple]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for tr in triples:
            f.write(json.dumps({"h": tr.h, "r": tr.r, "t": tr.t}, ensure_ascii=False) + "\n")


def write_dicts_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for item in rows:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Second-stage conservative repair for KG triples.")
    parser.add_argument("--input", default="kg_triples_cleaned.jsonl", help="Input cleaned triples file")
    parser.add_argument("--output", default="kg_triples_repaired.jsonl", help="Output repaired triples file")
    parser.add_argument(
        "--actions-output",
        default="kg_triples_repair_actions.jsonl",
        help="Output applied repair actions file",
    )
    parser.add_argument(
        "--unresolved-output",
        default="kg_triples_repair_unresolved.jsonl",
        help="Output unresolved review items file",
    )
    parser.add_argument("--stats-output", default="kg_triples_repair_stats.json", help="Output stats JSON file")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    actions_path = Path(args.actions_output)
    unresolved_path = Path(args.unresolved_output)
    stats_path = Path(args.stats_output)

    triples = load_triples(input_path)
    input_count = len(triples)

    triples, actions_height = normalize_height_direction(triples)
    triples, actions_occurs, unresolved_occurs = resolve_bidirectional_occurs(triples)
    triples, dedup_dropped = dedup_triples(triples)

    actions = actions_height + actions_occurs

    write_jsonl(output_path, triples)
    write_dicts_jsonl(actions_path, actions)
    write_dicts_jsonl(unresolved_path, unresolved_occurs)

    stats = {
        "input": str(input_path),
        "output": str(output_path),
        "input_count": input_count,
        "output_count": len(triples),
        "changed_count": input_count - len(triples),
        "applied_actions_count": len(actions),
        "height_direction_swaps": len(actions_height),
        "bidirectional_occurs_resolved": len(actions_occurs),
        "unresolved_bidirectional_occurs": len(unresolved_occurs),
        "dedup_dropped_after_repair": len(dedup_dropped),
    }
    with stats_path.open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
