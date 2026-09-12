#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DATASET = ROOT / "data/raw/v0.1/validation.jsonl"
DEFAULT_POLICY = ROOT / "research/evaluation/generation-policy-v0.1.json"
DEFAULT_RUN_DIR = (
    ROOT / "research/runs/EXP-001-qwen3-1.7b-baseline"
)

EXPECTED_VALIDATION_SHA256 = (
    "d5f05d3dfd6f72990314e3410f06c96a7fc2e733fb11078416e126934c85078a"
)

EXPECTED_VALIDATION_RECORDS = 40


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def git_output(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()


def git_commit() -> str:
    return git_output("rev-parse", "HEAD")


def git_dirty() -> bool:
    return bool(
        git_output(
            "status",
            "--porcelain",
            "--untracked-files=normal",
        )
    )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"{path}:{line_no}: malformed JSON: {exc}"
                ) from exc

    return rows


def verify_validation_dataset(
    path: Path,
) -> tuple[list[dict[str, Any]], str]:
    if path.resolve() != DEFAULT_DATASET.resolve():
        raise RuntimeError(
            "EXP-001 calibration is intentionally locked to the "
            "frozen v0.1 validation dataset."
        )

    digest = sha256_file(path)

    if digest != EXPECTED_VALIDATION_SHA256:
        raise RuntimeError(
            "Validation dataset SHA-256 mismatch.\n"
            f"Expected: {EXPECTED_VALIDATION_SHA256}\n"
            f"Actual:   {digest}"
        )

    rows = read_jsonl(path)

    if len(rows) != EXPECTED_VALIDATION_RECORDS:
        raise RuntimeError(
            "Validation record count mismatch: "
            f"expected {EXPECTED_VALIDATION_RECORDS}, got {len(rows)}"
        )

    for row in rows:
        if row.get("split") != "validation":
            raise RuntimeError(
                f"{row.get('id')}: split is not validation"
            )

        messages = row.get("messages")

        if not isinstance(messages, list) or len(messages) < 2:
            raise RuntimeError(
                f"{row.get('id')}: invalid messages"
            )

        if messages[-1].get("role") != "assistant":
            raise RuntimeError(
                f"{row.get('id')}: final message must be assistant "
                "reference answer"
            )

    return rows, digest


def sanitize_tag(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = value.strip("-")

    if not value:
        raise ValueError("tag cannot be empty")

    return value


def derive_record_seed(run_seed: int, record_id: str) -> int:
    raw = f"{run_seed}:{record_id}".encode("utf-8")
    digest = hashlib.sha256(raw).digest()

    # Stable per-record seed so interrupted/resumed runs do not alter
    # the sampling stream of later records.
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def extract_thinking(text: str) -> tuple[str | None, str]:
    cleaned = text.strip()

    if "</think>" not in cleaned:
        return None, cleaned

    thinking, final = cleaned.rsplit("</think>", 1)

    if "<think>" in thinking:
        thinking = thinking.split("<think>", 1)[1]

    thinking = thinking.strip()
    final = final.strip()

    return thinking or None, final


def load_ml():
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "PyTorch is not installed in this Python environment."
        ) from exc

    try:
        import transformers
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            set_seed,
        )
    except ImportError as exc:
        raise RuntimeError(
            "transformers is not installed in this Python environment."
        ) from exc

    return (
        torch,
        transformers,
        AutoModelForCausalLM,
        AutoTokenizer,
        set_seed,
    )


def print_preflight(
    dataset: Path,
    policy_path: Path,
    run_dir: Path,
) -> None:
    rows, digest = verify_validation_dataset(dataset)
    policy = read_json(policy_path)
    manifest = read_json(run_dir / "run-manifest.json")

    print("=" * 72)
    print("Qwen3 CE EXP-001 validation preflight")
    print("=" * 72)
    print(f"Git commit:       {git_commit()}")
    print(f"Git dirty:        {git_dirty()}")
    print(f"Python:           {platform.python_version()}")
    print(f"Dataset:          {dataset}")
    print(f"Dataset records:  {len(rows)}")
    print(f"Dataset SHA-256:  {digest}")
    print(f"Policy status:    {policy.get('status')}")
    print(
        "Model:            "
        f"{manifest['model']['provider_or_repo']}"
    )
    print(
        "Model revision:   "
        f"{manifest['model']['revision']}"
    )

    try:
        (
            torch,
            transformers,
            _,
            _,
            _,
        ) = load_ml()

        print(f"PyTorch:          {torch.__version__}")
        print(f"Transformers:     {transformers.__version__}")
        print(f"CUDA available:   {torch.cuda.is_available()}")

        if torch.cuda.is_available():
            print(
                "CUDA runtime:     "
                f"{torch.version.cuda}"
            )
            print(
                "GPU count:        "
                f"{torch.cuda.device_count()}"
            )

            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)

                print(
                    f"GPU {i}:            "
                    f"{props.name} "
                    f"({props.total_memory / 1024**3:.2f} GiB)"
                )

    except RuntimeError as exc:
        print(f"ML environment:   NOT READY — {exc}")

    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "EXP-001 Qwen3 v0.1 validation-only generation harness"
        )
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=DEFAULT_POLICY,
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=DEFAULT_RUN_DIR,
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=None,
        help=(
            "Optional verified local model snapshot. "
            "When supplied, network access is not used for model loading."
        ),
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
        default="full",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
    )

    args = parser.parse_args()

    dataset = args.dataset.resolve()
    policy_path = args.policy.resolve()
    run_dir = args.run_dir.resolve()

    if args.preflight:
        print_preflight(
            dataset,
            policy_path,
            run_dir,
        )
        return 0

    if git_dirty() and not args.allow_dirty:
        raise RuntimeError(
            "Working tree is dirty. Commit evaluator/config changes "
            "before generating research results, or explicitly use "
            "--allow-dirty for non-paper debugging."
        )

    rows, dataset_digest = verify_validation_dataset(dataset)

    policy = read_json(policy_path)
    manifest = read_json(run_dir / "run-manifest.json")

    allowed_seeds = policy["seeds"]

    if args.seed not in allowed_seeds:
        raise RuntimeError(
            f"Seed {args.seed} is not preregistered. "
            f"Allowed seeds: {allowed_seeds}"
        )

    if args.limit is not None:
        if args.limit <= 0:
            raise RuntimeError("--limit must be greater than zero")

        rows = rows[: args.limit]

    tag = sanitize_tag(args.tag)

    (
        torch,
        transformers,
        AutoModelForCausalLM,
        AutoTokenizer,
        set_seed,
    ) = load_ml()

    model_repo = manifest["model"]["provider_or_repo"]
    model_revision = manifest["model"]["revision"]

    if not model_repo or not model_revision:
        raise RuntimeError(
            "Model repository/revision is not pinned in run-manifest.json"
        )

    model_path = (
        args.model_path.expanduser().resolve()
        if args.model_path is not None
        else None
    )

    if model_path is not None:
        if not model_path.is_dir():
            raise RuntimeError(
                f"Local model path does not exist: {model_path}"
            )

        model_source = str(model_path)
        model_source_type = "verified-local-snapshot"
    else:
        model_source = model_repo
        model_source_type = "huggingface-hub"

    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    stem = f"validation-seed-{args.seed}-{tag}"

    responses_path = artifacts_dir / f"{stem}.jsonl"
    metadata_path = artifacts_dir / f"{stem}.generation.json"

    if not args.overwrite:
        for path in (responses_path, metadata_path):
            if path.exists():
                raise RuntimeError(
                    f"Refusing to overwrite existing artifact: {path}"
                )

    chat_policy = policy["chat_template"]
    sampling = policy["sampling"]
    limits = policy["generation_limits"]

    max_new_tokens = int(limits["max_new_tokens"])
    enable_thinking = bool(chat_policy["enable_thinking"])

    print("=" * 72)
    print("EXP-001 — Qwen3 1.7B validation generation")
    print("=" * 72)
    print(f"Model:          {model_repo}")
    print(f"Revision:       {model_revision}")
    print(f"Load source:    {model_source_type}")
    print(f"Records:        {len(rows)}")
    print(f"Run seed:       {args.seed}")
    print(f"Thinking:       {enable_thinking}")
    print(f"Max new tokens: {max_new_tokens}")
    print(f"Output:         {responses_path}")
    print("=" * 72)

    print("Loading tokenizer...")

    tokenizer_kwargs: dict[str, Any] = {
        "trust_remote_code": False,
    }

    model_kwargs: dict[str, Any] = {
        "torch_dtype": "auto",
        "device_map": "auto",
        "trust_remote_code": False,
    }

    if model_path is not None:
        tokenizer_kwargs["local_files_only"] = True
        model_kwargs["local_files_only"] = True
    else:
        tokenizer_kwargs["revision"] = model_revision
        model_kwargs["revision"] = model_revision

    tokenizer = AutoTokenizer.from_pretrained(
        model_source,
        **tokenizer_kwargs,
    )

    print("Loading model...")

    model = AutoModelForCausalLM.from_pretrained(
        model_source,
        **model_kwargs,
    )

    model.eval()

    input_device = model.get_input_embeddings().weight.device

    print(f"Input device:   {input_device}")
    print(f"Model dtype:    {model.dtype}")
    print("=" * 72)

    git_sha = git_commit()

    generated_token_counts: list[int] = []
    elapsed_times: list[float] = []
    throughput_values: list[float] = []
    truncations = 0

    started_at = time.time()

    with responses_path.open(
        "x" if not args.overwrite else "w",
        encoding="utf-8",
    ) as out:
        for index, record in enumerate(rows, start=1):
            record_id = record["id"]

            # Last assistant message is the held-out reference answer.
            # It must NEVER enter the model prompt.
            prompt_messages = record["messages"][:-1]

            prompt_text = tokenizer.apply_chat_template(
                prompt_messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=enable_thinking,
            )

            encoded = tokenizer(
                prompt_text,
                return_tensors="pt",
                add_special_tokens=False,
            )

            encoded = {
                key: value.to(input_device)
                for key, value in encoded.items()
            }

            input_tokens = int(
                encoded["input_ids"].shape[-1]
            )

            record_seed = derive_record_seed(
                args.seed,
                record_id,
            )

            set_seed(record_seed)

            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(record_seed)

                if input_device.type == "cuda":
                    torch.cuda.reset_peak_memory_stats(
                        input_device
                    )
                    torch.cuda.synchronize(
                        input_device
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
                "pad_token_id": tokenizer.eos_token_id,
            }

            # min_p=0 means disabled. Do not pass it to older
            # transformers versions unnecessarily.
            min_p = float(
                sampling.get("min_p", 0.0)
            )

            if min_p > 0:
                generation_kwargs["min_p"] = min_p

            t0 = time.perf_counter()

            with torch.inference_mode():
                output = model.generate(
                    **encoded,
                    **generation_kwargs,
                )

            if (
                torch.cuda.is_available()
                and input_device.type == "cuda"
            ):
                torch.cuda.synchronize(
                    input_device
                )

            elapsed = time.perf_counter() - t0

            continuation = output[
                0,
                input_tokens:,
            ]

            generated_tokens = int(
                continuation.shape[-1]
            )

            raw_response = tokenizer.decode(
                continuation,
                skip_special_tokens=False,
            )

            response = tokenizer.decode(
                continuation,
                skip_special_tokens=True,
            ).strip()

            reasoning, final_answer = extract_thinking(
                response
            )

            eos = model.generation_config.eos_token_id

            if eos is None:
                eos_ids: set[int] = set()
            elif isinstance(eos, int):
                eos_ids = {eos}
            else:
                eos_ids = {
                    int(value)
                    for value in eos
                }

            last_token = (
                int(continuation[-1].item())
                if generated_tokens
                else None
            )

            ended_with_eos = (
                last_token in eos_ids
                if last_token is not None
                else False
            )

            truncated = (
                generated_tokens >= max_new_tokens
                and not ended_with_eos
            )

            finish_reason = (
                "eos"
                if ended_with_eos
                else "length"
                if truncated
                else "other"
            )

            throughput = (
                generated_tokens / elapsed
                if elapsed > 0
                else 0.0
            )

            peak_cuda_bytes = None

            if (
                torch.cuda.is_available()
                and input_device.type == "cuda"
            ):
                peak_cuda_bytes = int(
                    torch.cuda.max_memory_allocated(
                        input_device
                    )
                )

            result = {
                "record_id": record_id,
                "split": "validation",
                "domain": record["domain"],
                "subdomain": record["subdomain"],
                "task_type": record["task_type"],
                "difficulty": record["difficulty"],

                "model": {
                    "repo": model_repo,
                    "revision": model_revision,
                    "load_source_type": model_source_type,
                },

                "code": {
                    "git_commit": git_sha,
                },

                "dataset": {
                    "sha256": dataset_digest,
                },

                "sampling": {
                    "run_seed": args.seed,
                    "record_seed": record_seed,
                    "enable_thinking": enable_thinking,
                    "do_sample": generation_kwargs[
                        "do_sample"
                    ],
                    "temperature": generation_kwargs[
                        "temperature"
                    ],
                    "top_p": generation_kwargs[
                        "top_p"
                    ],
                    "top_k": generation_kwargs[
                        "top_k"
                    ],
                    "min_p": min_p,
                    "max_new_tokens": max_new_tokens,
                },

                "telemetry": {
                    "input_tokens": input_tokens,
                    "generated_tokens": generated_tokens,
                    "elapsed_seconds": elapsed,
                    "output_tokens_per_second": throughput,
                    "finish_reason": finish_reason,
                    "truncated": truncated,
                    "peak_cuda_memory_bytes": peak_cuda_bytes,
                },

                "output": {
                    "raw_response": raw_response,
                    "response": response,
                    "reasoning": reasoning,
                    "final_answer": final_answer,
                },
            }

            out.write(
                json.dumps(
                    result,
                    ensure_ascii=False,
                )
                + "\n"
            )
            out.flush()

            generated_token_counts.append(
                generated_tokens
            )
            elapsed_times.append(elapsed)
            throughput_values.append(
                throughput
            )

            if truncated:
                truncations += 1

            print(
                f"[{index:03d}/{len(rows):03d}] "
                f"{record_id} "
                f"{generated_tokens} tok "
                f"{elapsed:.2f}s "
                f"{throughput:.2f} tok/s "
                f"{finish_reason}"
            )

    finished_at = time.time()

    responses_sha = sha256_file(
        responses_path
    )

    summary = {
        "experiment_id": "EXP-001",
        "phase": "validation-calibration",
        "tag": tag,
        "model": {
            "repo": model_repo,
            "revision": model_revision,
            "load_source_type": model_source_type,
        },
        "code": {
            "git_commit": git_sha,
            "dirty_worktree": False,
        },
        "dataset": {
            "split": "validation",
            "records_available": EXPECTED_VALIDATION_RECORDS,
            "records_generated": len(rows),
            "sha256": dataset_digest,
        },
        "generation": {
            "run_seed": args.seed,
            "enable_thinking": enable_thinking,
            "do_sample": sampling["do_sample"],
            "temperature": sampling["temperature"],
            "top_p": sampling["top_p"],
            "top_k": sampling["top_k"],
            "min_p": sampling.get("min_p", 0.0),
            "max_new_tokens": max_new_tokens,
        },
        "telemetry": {
            "total_generated_tokens": sum(
                generated_token_counts
            ),
            "mean_generated_tokens": (
                mean(generated_token_counts)
                if generated_token_counts
                else 0
            ),
            "total_generation_seconds": sum(
                elapsed_times
            ),
            "mean_seconds_per_record": (
                mean(elapsed_times)
                if elapsed_times
                else 0
            ),
            "mean_output_tokens_per_second": (
                mean(throughput_values)
                if throughput_values
                else 0
            ),
            "truncated_records": truncations,
            "truncation_rate": (
                truncations / len(rows)
                if rows
                else 0
            ),
        },
        "artifacts": {
            "responses_file": responses_path.name,
            "responses_sha256": responses_sha,
        },
        "timing": {
            "started_unix": started_at,
            "finished_unix": finished_at,
            "duration_seconds": finished_at - started_at,
        },
        "software": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
        },
    }

    metadata_path.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print("=" * 72)
    print("GENERATION COMPLETE")
    print(f"Records:        {len(rows)}")
    print(
        f"Generated tok:  "
        f"{sum(generated_token_counts)}"
    )
    print(
        f"Mean tok/record:"
        f" {mean(generated_token_counts):.2f}"
    )
    print(
        f"Mean tok/s:     "
        f"{mean(throughput_values):.2f}"
    )
    print(
        f"Truncated:      "
        f"{truncations}/{len(rows)}"
    )
    print(
        f"Responses SHA:  "
        f"{responses_sha}"
    )
    print(f"Responses:      {responses_path}")
    print(f"Metadata:       {metadata_path}")
    print("=" * 72)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(
            f"\nERROR: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
