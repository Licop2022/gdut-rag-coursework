"""Small-sample BF16 LoRA pilot; test articles never enter training/dev."""
import argparse
import json
from pathlib import Path
import time

from engine import ROOT, gpu_guard, read_jsonl, save_json
import torch
from peft import LoraConfig, TaskType, get_peft_model
from transformers import AutoTokenizer, Qwen3_5ForConditionalGeneration, Trainer, TrainingArguments, set_seed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "adapters/lora_pilot")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Use a fresh adapter output directory")
    gpu_guard()
    set_seed(42)
    train = read_jsonl(ROOT / "data/lora_train.jsonl")
    dev = read_jsonl(ROOT / "data/lora_dev.jsonl")
    split = json.loads((ROOT / "data/split_manifest.json").read_text(encoding="utf-8"))
    heldout = set(split["test_articles"])
    assert not any(heldout.intersection(row["article_ids"]) for row in train + dev)
    tokenizer = AutoTokenizer.from_pretrained(ROOT / "models/generator", local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    model = Qwen3_5ForConditionalGeneration.from_pretrained(ROOT / "models/generator", local_files_only=True,
                dtype=torch.bfloat16, device_map={"": "cuda:0"}, attn_implementation="sdpa")
    suffixes = {"q_proj", "k_proj", "v_proj", "o_proj", "in_proj_qkv", "in_proj_z", "out_proj", "gate_proj", "up_proj", "down_proj"}
    targets = [name for name, module in model.named_modules()
               if isinstance(module, torch.nn.Linear) and ".language_model.layers." in name and name.rsplit(".", 1)[-1] in suffixes]
    if not targets:
        raise RuntimeError("No text decoder LoRA targets found; inspect architecture before training")
    config = LoraConfig(task_type=TaskType.CAUSAL_LM, r=8, lora_alpha=16, lora_dropout=0.05,
                        target_modules=targets, bias="none")
    model = get_peft_model(model, config)
    model.config.use_cache = False
    model.enable_input_require_grads()
    model.print_trainable_parameters()

    def tokenize(row):
        prompt = tokenizer.apply_chat_template(row["messages"][:-1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
        # Use the same non-thinking assistant prefix in inference and training.
        prefix_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        answer_ids = tokenizer(row["messages"][-1]["content"], add_special_tokens=False)["input_ids"] + [tokenizer.eos_token_id]
        if len(prefix_ids) + len(answer_ids) > 1024:
            raise ValueError(f"Sample {row['id']} exceeds 1024 tokens; revise explicitly instead of silently truncating labels")
        return {"input_ids": prefix_ids + answer_ids, "attention_mask": [1] * (len(prefix_ids) + len(answer_ids)),
                "labels": [-100] * len(prefix_ids) + answer_ids}

    train_tokens, dev_tokens = list(map(tokenize, train)), list(map(tokenize, dev))

    def collate(rows):
        length = max(len(r["input_ids"]) for r in rows)
        return {key: torch.tensor([r[key] + [(-100 if key == "labels" else tokenizer.pad_token_id if key == "input_ids" else 0)] * (length - len(r[key])) for r in rows], dtype=torch.long)
                for key in ["input_ids", "attention_mask", "labels"]}

    training_args = TrainingArguments(output_dir=str(args.output), num_train_epochs=3,
        per_device_train_batch_size=1, per_device_eval_batch_size=1, gradient_accumulation_steps=4,
        learning_rate=5e-5, warmup_ratio=0.1, weight_decay=0.0, bf16=True,
        gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False},
        eval_strategy="epoch", save_strategy="no", logging_steps=1, report_to="none",
        optim="adamw_torch", seed=42, data_seed=42, dataloader_num_workers=0,
        remove_unused_columns=False)
    trainer = Trainer(model=model, args=training_args, train_dataset=train_tokens,
                      eval_dataset=dev_tokens, data_collator=collate)
    start = time.perf_counter()
    result = trainer.train()
    metrics = trainer.evaluate()
    model.save_pretrained(args.output, safe_serialization=True)
    tokenizer.save_pretrained(args.output)
    save_json(args.output / "training_manifest.json", {"complete": True, "method": "BF16 LoRA, frozen base and vision weights",
        "train_examples": len(train), "dev_examples": len(dev), "test_articles_excluded": sorted(heldout),
        "epochs": 3, "learning_rate": 5e-5, "rank": 8, "max_sequence_tokens": 1024,
        "target_modules": targets, "training_metrics": result.metrics, "dev_metrics": metrics,
        "trainer_history": trainer.state.log_history, "elapsed_s": time.perf_counter() - start,
        "selection": "预先固定3个epoch，使用最终adapter；未根据测试集调参或挑选checkpoint。",
        "limitation": "27个训练样本仅验证微调流程，不代表足够训练数据，也不保证质量提升。"})
    print("LORA_TRAINING_COMPLETED", flush=True)


if __name__ == "__main__":
    main()
