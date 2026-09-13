#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import run_eval as base


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DATASET = ROOT / "data/raw/v0.1/validation.jsonl"
DEFAULT_POLICY = ROOT / "research/evaluation/generation-policy-v0.1.json"
DEFAULT_RUN_DIR = (
    ROOT / "research/runs/EXP-001-qwen3-1.7b-baseline"
)

BATCH_SIZE = 2


def derive_batch_seed(
    run_seed: int,
    record_ids: list[str],
) -> int:
    payload = (
        str(run_seed)
        + ":"
        + ":".join(record_ids)
    ).encode("utf-8")

    digest = hashlib.sha256(payload).digest()

    return (
        int.from_bytes(digest[:4], "big")
        & 0x7FFFFFFF
    )


def token_sha256(tokens: list[int]) -> str:
    payload = json.dumps(
        tokens,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def atomic_json(
    path: Path,
    obj: Any,
) -> None:
    tmp = path.with_suffix(
        path.suffix + ".tmp"
    )

    tmp.write_text(
        json.dumps(
            obj,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(tmp, path)


def effective_continuation(
    tokens: list[int],
    eos_ids: set[int],
    max_new_tokens: int,
) -> tuple[list[int], str, bool]:
    for index, token in enumerate(tokens):
        if token in eos_ids:
            return (
                tokens[: index + 1],
                "eos",
                False,
            )

    if len(tokens) >= max_new_tokens:
        return tokens, "length", True

    return tokens, "other", False


def validate_batch_file(
    path: Path,
    expected_index: int,
    expected_ids: list[str],
    expected_seed: int,
) -> dict[str, Any]:
    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if data["batch_index"] != expected_index:
        raise RuntimeError(
            f"{path}: batch index mismatch"
        )

    if data["record_ids"] != expected_ids:
        raise RuntimeError(
            f"{path}: record IDs mismatch"
        )

    if data["batch_seed"] != expected_seed:
        raise RuntimeError(
            f"{path}: batch seed mismatch"
        )

    if len(data["results"]) != len(expected_ids):
        raise RuntimeError(
            f"{path}: incomplete batch"
        )

    actual_ids = [
        row["record_id"]
        for row in data["results"]
    ]

    if actual_ids != expected_ids:
        raise RuntimeError(
            f"{path}: result ordering mismatch"
        )

    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "EXP-001 deterministic batch-2 "
            "validation generation harness"
        )
    )

    parser.add_argument(
        "--model-path",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=17,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--tag",
        required=True,
    )
    parser.add_argument(
        "--resume",
        action="store_true",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
    )

    args = parser.parse_args()

    if args.resume and args.overwrite:
        raise RuntimeError(
            "--resume and --overwrite cannot be combined"
        )

    if base.git_dirty() and not args.allow_dirty:
        raise RuntimeError(
            "Working tree is dirty. Commit changes "
            "before producing research artifacts."
        )

    rows, dataset_sha = (
        base.verify_validation_dataset(
            DEFAULT_DATASET
        )
    )

    policy = base.read_json(
        DEFAULT_POLICY
    )

    manifest = base.read_json(
        DEFAULT_RUN_DIR / "run-manifest.json"
    )

    if args.seed not in policy["seeds"]:
        raise RuntimeError(
            f"Seed {args.seed} is not preregistered"
        )

    if args.limit is not None:
        if args.limit <= 0:
            raise RuntimeError(
                "--limit must be positive"
            )

        rows = rows[: args.limit]

    tag = base.sanitize_tag(args.tag)

    model_path = (
        args.model_path
        .expanduser()
        .resolve()
    )

    if not model_path.is_dir():
        raise RuntimeError(
            f"Model path not found: {model_path}"
        )

    model_repo = (
        manifest["model"]["provider_or_repo"]
    )
    model_revision = (
        manifest["model"]["revision"]
    )

    chat_policy = policy["chat_template"]
    sampling = policy["sampling"]
    limits = policy["generation_limits"]

    max_new_tokens = int(
        limits["max_new_tokens"]
    )

    enable_thinking = bool(
        chat_policy["enable_thinking"]
    )

    (
        torch,
        transformers,
        AutoModelForCausalLM,
        AutoTokenizer,
        set_seed,
    ) = base.load_ml()

    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        local_files_only=True,
        trust_remote_code=False,
    )

    tokenizer.padding_side = "left"

    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = (
            tokenizer.eos_token_id
        )

    print("Loading model...")

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        local_files_only=True,
        torch_dtype="auto",
        device_map="auto",
        trust_remote_code=False,
    )

    model.eval()

    device = (
        model
        .get_input_embeddings()
        .weight
        .device
    )

    eos = model.generation_config.eos_token_id

    if eos is None:
        eos_ids: set[int] = set()
    elif isinstance(eos, int):
        eos_ids = {int(eos)}
    else:
        eos_ids = {
            int(value)
            for value in eos
        }

    if tokenizer.eos_token_id is not None:
        eos_ids.add(
            int(tokenizer.eos_token_id)
        )

    artifacts = (
        DEFAULT_RUN_DIR / "artifacts"
    )
    artifacts.mkdir(
        parents=True,
        exist_ok=True,
    )

    stem = (
        f"validation-batch2-seed-"
        f"{args.seed}-{tag}"
    )

    working_dir = artifacts / stem
    batch_dir = working_dir / "batches"

    merged_path = (
        artifacts / f"{stem}.jsonl"
    )
    metadata_path = (
        artifacts
        / f"{stem}.generation.json"
    )

    if args.overwrite:
        shutil.rmtree(
            working_dir,
            ignore_errors=True,
        )

        merged_path.unlink(
            missing_ok=True
        )
        metadata_path.unlink(
            missing_ok=True
        )

    if (
        working_dir.exists()
        and not args.resume
        and not args.overwrite
    ):
        raise RuntimeError(
            f"Run already exists: {working_dir}"
        )

    batch_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    batches = [
        rows[i : i + BATCH_SIZE]
        for i in range(
            0,
            len(rows),
            BATCH_SIZE,
        )
    ]

    git_sha = base.git_commit()

    print("=" * 76)
    print("EXP-001 — deterministic batch-2 validation generation")
    print("=" * 76)
    print(f"Model:          {model_repo}")
    print(f"Revision:       {model_revision}")
    print("Load source:    verified-local-snapshot")
    print(f"Records:        {len(rows)}")
    print(f"Batches:        {len(batches)}")
    print(f"Run seed:       {args.seed}")
    print(f"Thinking:       {enable_thinking}")
    print(f"Max new tokens: {max_new_tokens}")
    print(f"Device:         {device}")
    print(f"Dtype:          {model.dtype}")
    print("=" * 76)

    for batch_index, batch in enumerate(
        batches
    ):
        record_ids = [
            row["id"]
            for row in batch
        ]

        batch_seed = derive_batch_seed(
            args.seed,
            record_ids,
        )

        batch_path = (
            batch_dir
            / f"batch-{batch_index:03d}.json"
        )

        if args.resume and batch_path.exists():
            validate_batch_file(
                batch_path,
                batch_index,
                record_ids,
                batch_seed,
            )

            print(
                f"[batch {batch_index:03d}] "
                f"RESUME SKIP "
                f"{', '.join(record_ids)}"
            )
            continue

        prompt_texts = []

        for row in batch:
            prompt_messages = (
                row["messages"][:-1]
            )

            prompt_texts.append(
                tokenizer.apply_chat_template(
                    prompt_messages,
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=(
                        enable_thinking
                    ),
                )
            )

        encoded = tokenizer(
            prompt_texts,
            return_tensors="pt",
            padding=True,
            add_special_tokens=False,
        )

        input_token_counts = (
            encoded["attention_mask"]
            .sum(dim=1)
            .tolist()
        )

        encoded = {
            key: value.to(device)
            for key, value
            in encoded.items()
        }

        batch_input_width = int(
            encoded["input_ids"].shape[1]
        )

        set_seed(batch_seed)
        torch.manual_seed(batch_seed)

        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(
                batch_seed
            )

            if device.type == "cuda":
                torch.cuda.reset_peak_memory_stats(
                    device
                )
                torch.cuda.synchronize(
                    device
                )

        generation_kwargs: dict[str, Any] = {
            "max_new_tokens": max_new_tokens,
            "do_sample": bool(
                sampling["do_sample"]
            ),
            "temperature": float(
                sampling["temperature"]
            ),
            "top_p": float(
                sampling["top_p"]
            ),
            "top_k": int(
                sampling["top_k"]
            ),
            "pad_token_id": (
                tokenizer.pad_token_id
            ),
        }

        min_p = float(
            sampling.get(
                "min_p",
                0.0,
            )
        )

        if min_p > 0:
            generation_kwargs["min_p"] = (
                min_p
            )

        started = time.perf_counter()

        with torch.inference_mode():
            output = model.generate(
                **encoded,
                **generation_kwargs,
            )

        if (
            torch.cuda.is_available()
            and device.type == "cuda"
        ):
            torch.cuda.synchronize(
                device
            )

        elapsed = (
            time.perf_counter()
            - started
        )

        continuations = output[
            :,
            batch_input_width:,
        ].detach().cpu()

        peak_cuda = None

        if (
            torch.cuda.is_available()
            and device.type == "cuda"
        ):
            peak_cuda = int(
                torch.cuda.max_memory_allocated(
                    device
                )
            )

        batch_results = []
        effective_total = 0

        for position, row in enumerate(
            batch
        ):
            padded_tokens = [
                int(x)
                for x in (
                    continuations[position]
                    .tolist()
                )
            ]

            (
                effective_tokens,
                finish_reason,
                truncated,
            ) = effective_continuation(
                padded_tokens,
                eos_ids,
                max_new_tokens,
            )

            effective_total += len(
                effective_tokens
            )

            raw_response = tokenizer.decode(
                effective_tokens,
                skip_special_tokens=False,
            )

            response = tokenizer.decode(
                effective_tokens,
                skip_special_tokens=True,
            ).strip()

            (
                reasoning,
                final_answer,
                reasoning_complete,
            ) = base.extract_thinking(
                response
            )

            result = {
                "record_id": row["id"],
                "split": "validation",
                "domain": row["domain"],
                "subdomain": row[
                    "subdomain"
                ],
                "task_type": row[
                    "task_type"
                ],
                "difficulty": row[
                    "difficulty"
                ],

                "model": {
                    "repo": model_repo,
                    "revision": (
                        model_revision
                    ),
                    "load_source_type": (
                        "verified-local-snapshot"
                    ),
                },

                "code": {
                    "git_commit": git_sha,
                },

                "dataset": {
                    "sha256": dataset_sha,
                },

                "batch": {
                    "size": len(batch),
                    "index": batch_index,
                    "seed": batch_seed,
                    "record_ids": (
                        record_ids
                    ),
                    "position": position,
                },

                "sampling": {
                    "run_seed": args.seed,
                    "enable_thinking": (
                        enable_thinking
                    ),
                    "do_sample": (
                        generation_kwargs[
                            "do_sample"
                        ]
                    ),
                    "temperature": (
                        generation_kwargs[
                            "temperature"
                        ]
                    ),
                    "top_p": (
                        generation_kwargs[
                            "top_p"
                        ]
                    ),
                    "top_k": (
                        generation_kwargs[
                            "top_k"
                        ]
                    ),
                    "min_p": min_p,
                    "max_new_tokens": (
                        max_new_tokens
                    ),
                },

                "telemetry": {
                    "input_tokens": int(
                        input_token_counts[
                            position
                        ]
                    ),
                    "generated_tokens": len(
                        effective_tokens
                    ),
                    "batch_latency_seconds": (
                        elapsed
                    ),
                    "finish_reason": (
                        finish_reason
                    ),
                    "truncated": truncated,
                    "completed_final_answer": (
                        bool(final_answer)
                    ),
                    "batch_peak_cuda_memory_bytes": (
                        peak_cuda
                    ),
                },

                "output": {
                    "token_sha256": (
                        token_sha256(
                            effective_tokens
                        )
                    ),
                    "raw_response": (
                        raw_response
                    ),
                    "response": response,
                    "reasoning": reasoning,
                    "reasoning_complete": (
                        reasoning_complete
                    ),
                    "final_answer": (
                        final_answer
                    ),
                },
            }

            batch_results.append(
                result
            )

        batch_doc = {
            "batch_index": batch_index,
            "record_ids": record_ids,
            "batch_seed": batch_seed,
            "elapsed_seconds": elapsed,
            "effective_generated_tokens": (
                effective_total
            ),
            "aggregate_tokens_per_second": (
                effective_total / elapsed
                if elapsed > 0
                else 0.0
            ),
            "peak_cuda_memory_bytes": (
                peak_cuda
            ),
            "results": batch_results,
        }

        atomic_json(
            batch_path,
            batch_doc,
        )

        result_text = ", ".join(
            f"{r['record_id']}="
            f"{r['telemetry']['generated_tokens']}"
            f"/{r['telemetry']['finish_reason']}"
            for r in batch_results
        )

        print(
            f"[batch {batch_index:03d}] "
            f"{effective_total} tok "
            f"{elapsed:.2f}s "
            f"{effective_total / elapsed:.2f} tok/s "
            f"| {result_text}"
        )

    all_batch_docs = []

    for batch_index, batch in enumerate(
        batches
    ):
        record_ids = [
            row["id"]
            for row in batch
        ]

        batch_seed = derive_batch_seed(
            args.seed,
            record_ids,
        )

        path = (
            batch_dir
            / f"batch-{batch_index:03d}.json"
        )

        if not path.exists():
            raise RuntimeError(
                f"Missing completed batch: {path}"
            )

        all_batch_docs.append(
            validate_batch_file(
                path,
                batch_index,
                record_ids,
                batch_seed,
            )
        )

    merged_tmp = merged_path.with_suffix(
        ".jsonl.tmp"
    )

    with merged_tmp.open(
        "w",
        encoding="utf-8",
    ) as out:
        for batch_doc in all_batch_docs:
            for result in batch_doc[
                "results"
            ]:
                out.write(
                    json.dumps(
                        result,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

    os.replace(
        merged_tmp,
        merged_path,
    )

    flat_results = [
        result
        for batch_doc in all_batch_docs
        for result in batch_doc["results"]
    ]

    total_tokens = sum(
        r["telemetry"][
            "generated_tokens"
        ]
        for r in flat_results
    )

    total_seconds = sum(
        batch_doc["elapsed_seconds"]
        for batch_doc in all_batch_docs
    )

    truncated = sum(
        bool(
            r["telemetry"][
                "truncated"
            ]
        )
        for r in flat_results
    )

    completed_answers = sum(
        bool(
            r["telemetry"][
                "completed_final_answer"
            ]
        )
        for r in flat_results
    )

    summary = {
        "experiment_id": "EXP-001",
        "phase": (
            "validation-calibration"
        ),
        "runner": (
            "deterministic-batch2"
        ),
        "model": {
            "repo": model_repo,
            "revision": model_revision,
        },
        "code": {
            "git_commit": git_sha,
            "dirty_worktree": False,
        },
        "dataset": {
            "split": "validation",
            "records_generated": (
                len(flat_results)
            ),
            "sha256": dataset_sha,
        },
        "batching": {
            "batch_size": BATCH_SIZE,
            "batch_count": (
                len(all_batch_docs)
            ),
            "seed_derivation": (
                "sha256(run_seed:"
                "ordered_record_ids)"
            ),
            "fixed_record_order": True,
        },
        "generation": {
            "run_seed": args.seed,
            "enable_thinking": (
                enable_thinking
            ),
            "do_sample": sampling[
                "do_sample"
            ],
            "temperature": sampling[
                "temperature"
            ],
            "top_p": sampling["top_p"],
            "top_k": sampling["top_k"],
            "min_p": sampling.get(
                "min_p",
                0.0,
            ),
            "max_new_tokens": (
                max_new_tokens
            ),
        },
        "telemetry": {
            "total_generated_tokens": (
                total_tokens
            ),
            "total_batch_seconds": (
                total_seconds
            ),
            "aggregate_tokens_per_second": (
                total_tokens
                / total_seconds
                if total_seconds > 0
                else 0.0
            ),
            "truncated_records": (
                truncated
            ),
            "truncation_rate": (
                truncated
                / len(flat_results)
                if flat_results
                else 0.0
            ),
            "completed_final_answers": (
                completed_answers
            ),
        },
        "artifacts": {
            "responses_file": (
                merged_path.name
            ),
            "responses_sha256": (
                base.sha256_file(
                    merged_path
                )
            ),
        },
        "software": {
            "python": (
                platform.python_version()
            ),
            "torch": torch.__version__,
            "transformers": (
                transformers.__version__
            ),
        },
    }

    atomic_json(
        metadata_path,
        summary,
    )

    print("=" * 76)
    print("BATCH-2 GENERATION COMPLETE")
    print(f"Records:       {len(flat_results)}")
    print(f"Batches:       {len(all_batch_docs)}")
    print(f"Tokens:        {total_tokens}")
    print(
        f"Aggregate:     "
        f"{summary['telemetry']['aggregate_tokens_per_second']:.2f} tok/s"
    )
    print(
        f"Truncated:     "
        f"{truncated}/{len(flat_results)}"
    )
    print(
        f"Final answers: "
        f"{completed_answers}/{len(flat_results)}"
    )
    print(f"Responses:     {merged_path}")
    print(f"Metadata:      {metadata_path}")
    print("=" * 76)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print(
            "\nInterrupted. Completed batches are preserved.",
            file=sys.stderr,
        )
        raise SystemExit(130)
    except Exception as exc:
        print(
            f"\nERROR: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
