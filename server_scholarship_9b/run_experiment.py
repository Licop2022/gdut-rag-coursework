import argparse
import json
from pathlib import Path
import platform
import re
import time

from engine import ROOT, SETTINGS, Generator, Retriever, gpu_guard, read_jsonl, save_json


def metrics(retrievals, route):
    keys = ("candidates" if route == "baseline" else "reranked_candidates")
    answerable = [r for r in retrievals if r["test"]["answerable"]]
    ranks = []
    for row in answerable:
        relevant = set(row["test"]["expected_articles"])
        ranks.append(next((i + 1 for i, c in enumerate(row[keys]) if c["article_id"] in relevant), 0))
    return {"article_hit_at_1": sum(r == 1 for r in ranks) / len(ranks),
            "article_hit_at_5": sum(r > 0 for r in ranks) / len(ranks),
            "article_mrr_at_5": sum(1 / r if r else 0 for r in ranks) / len(ranks), "answerable_questions": len(ranks)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["retrieve", "generate"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--adapter", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    gpu_guard()
    if args.stage == "retrieve":
        retriever = Retriever()
        rows = []
        for test in read_jsonl(ROOT / "data/eval.jsonl"):
            rows.append(dict(retriever.retrieve(test["question"]), test=test))
        save_json(args.output / "retrievals.json", rows)
        save_json(args.output / "retrieval_metrics.json", {route: metrics(rows, route) for route in ["baseline", "rerank"]})
        # These exploration queries are explicitly separate from the fixed test statistics.
        probes = [
            "我既有挂科又做了志愿服务，能申请学业奖学金吗？", "学校公示和学院公示不是一样长吗？",
            "研二一等奖能直接认定，那二等奖也能直接认定吗？", "研一和研二的奖学金名额比例一样吗？",
            "博士生一等奖和硕士生一等奖每年各多少元？", "学业奖学金和学生骨干奖学金是不是同一笔钱？",
            "我认为奖学金评定不公平，学院答复后仍不满意怎么办？", "学院初审结果公布后多久可以报给学校？",
            "如果没注册或者休学，会停发学业奖学金还是追回已发奖金？", "弄虚作假和缺勤分别会怎样影响奖学金？",
            "申请一等奖是只看课程分数还是还要求科研成果？", "一人兼任几个学生干部职务能领几份骨干奖学金？",
            "学校研究生会干部申请奖学金是交学院还是交校研究生会？", "哪种奖学金每人1000元，哪种每人200元？",
            "拿到国奖是不是就不能拿学业奖学金？", "申请前缴费和注册有什么规定？",
            "省赛前八和校赛前三都可以申请文体菁英吗？", "有专利但不是第一署名能直接认定一等奖吗？",
            "课程成绩积分和科研成果积分是否使用同一公式？", "评审结果有异议是在学校还是学院先申诉？",
            "不参加集体活动和未请假缺勤各达到多少会停发？", "硕博连读选修硕士课程时按哪种身份评奖？",
            "二年级一等奖直接认定的发明专利要求是申请还是授权？", "社会实践获得奖励和文体比赛获得奖励有什么条件区别？",
        ]
        exploration = [dict(retriever.retrieve(q), id=f"P{i:02d}") for i, q in enumerate(probes, 1)]
        save_json(args.output / "exploratory_ranking.json", exploration)
        found = [r for r in exploration if r["reranked_candidates"][0]["vector_rank"] == 4]
        save_json(args.output / "rank4_to_rank1_cases.json", found)
        print("Retrieval finished; actual rank4->rank1 cases:", len(found), flush=True)
    else:
        path = ROOT / "runs/retrieval/retrievals.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
        generator = Generator(args.adapter)
        for i, row in enumerate(rows, 1):
            for route in ["baseline", "rerank"]:
                row[route + "_generation"] = generator.generate(row["question"], row[route + "_context"])
                print(i, route, row[route + "_generation"]["answer"], flush=True)
            # Persist progress after every question, without claiming unfinished runs complete.
            save_json(args.output / "answers.partial.json", rows[:i])
        save_json(args.output / "answers.json", rows)
        case_path = ROOT / "runs/ranking_probes_situational/verified_candidate_cases.json"
        if case_path.exists():
            cases = json.loads(case_path.read_text(encoding="utf-8"))
            selected = next((c for c in cases if c["reranked_candidates"][0]["article_id"] == "A07"), cases[0] if cases else None)
            if selected:
                for route in ["baseline", "rerank"]:
                    selected[route + "_generation"] = generator.generate(selected["question"], selected[route + "_context"])
                selected["scope"] = "从240条独立情境化探索中选出的演示案例，不进入固定16题或泛化结论。"
                save_json(args.output / "exploratory_answers.json", selected)
        review = []
        for row in rows:
            for route in ["baseline", "rerank"]:
                answer = row[route + "_generation"]["answer"]
                compact = re.sub(r"\s+", "", answer)
                groups = row["test"]["keyword_groups"]
                review.append({"id": row["test"]["id"], "route": route, "answer": answer,
                    "keyword_group_coverage": sum(any(word in compact for word in group) for group in groups) / len(groups) if groups else None,
                    "citation_present": bool(re.search(r"\[A\d{2}-C\d{2}\]", answer)),
                    "manual_correctness": None, "manual_completeness": None, "manual_grounding": None,
                    "note": "关键词覆盖和引用格式仅为辅助检查，不等于答案正确率。"})
        save_json(args.output / "review_to_complete.json", review)
        print("Generation finished.", flush=True)
    import torch
    import transformers
    save_json(args.output / "run_manifest.json", {"complete": True, "settings": SETTINGS, "adapter": str(args.adapter) if args.adapter else None,
             "python": platform.python_version(), "torch": torch.__version__, "transformers": transformers.__version__,
             "source_manifest": json.loads((ROOT / "data/source_manifest.json").read_text(encoding="utf-8")), "finished_unix": time.time()})


if __name__ == "__main__":
    main()
