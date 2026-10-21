"""Independent exploration only; never alter fixed-test ranks or metrics."""
import argparse
from pathlib import Path

from engine import ROOT, Retriever, gpu_guard, read_jsonl, save_json

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=ROOT / "runs/ranking_probes_extra")
parser.add_argument("--situational", action="store_true")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
gpu_guard()
retriever = Retriever()
rows, cases = [], []
for sample in read_jsonl(ROOT / "data/lora_train.jsonl") + read_jsonl(ROOT / "data/lora_dev.jsonl"):
    question = sample["messages"][1]["content"].split("问题：", 1)[1].split("\n", 1)[0]
    prefixes = ["", "根据研究生手册，", "关于研究生奖学金，", "请解释一下：", "我有个奖学金问题："]
    if args.situational:
        prefixes = [
            "我是二年级硕士，平时参与社会实践与志愿服务，也参加创新实践项目和学术活动。现在想确认：",
            "我正在整理学院研究生年度测评、科研成果积分和课程成绩材料。有个具体问题：",
            "我知道学业奖学金和单项奖学金有不同评定条件，也看到学院和学校要公示。请回答：",
            "我热心学生工作，担任过学生干部，积极参加文体比赛和公益活动，最近在了解奖学金规定。想问：",
            "同学提到了硕士生一等奖、二等奖、三等奖和科研创新能力，我不确定具体规定，请解释：",
            "我已经准备好了研究生奖励申报表和有关证明，正在核对注册、缴费以及申请条件。请问：",
            "我看到手册里既有停发奖学金，也有取消资格和追回奖金，不想把不同条款混淆。具体来说：",
            "我在学院研究生会做学生工作，想向大家解释学业奖学金、骨干奖学金及其他单项奖学金。问题是：",
        ]
    for prefix in prefixes:
        result = retriever.retrieve(prefix + question)
        result.update(probe_id=f"E{len(rows)+1:03d}", expected_articles=sample["article_ids"],
                      selection="由训练/开发条款的人工问题变体进行独立探索；不进入固定测试指标。")
        rows.append(result)
        first = result["reranked_candidates"][0]
        if first["vector_rank"] == 4 and first["article_id"] in sample["article_ids"]:
            cases.append(result)
            print("ACTUAL_RELEVANT_RANK4_TO_1",result["probe_id"],result["question"],first["id"],flush=True)
save_json(args.output / "all_probes.json", rows)
save_json(args.output / "verified_candidate_cases.json", cases)
print("Probes",len(rows),"rank4->1 relevant cases",len(cases),flush=True)
