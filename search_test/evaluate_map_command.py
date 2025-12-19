"""Evaluate map_command_to_actions accuracy against search_test/test.json."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from services.llm_service import ShoppingLLMService


def load_cases(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    cases = data.get("test_cases", [])
    if not isinstance(cases, list):
        raise ValueError("test_cases must be a list")
    return cases


def normalize_actions(actions: Any) -> List[Dict[str, Any]]:
    if not isinstance(actions, list):
        return []
    return [a for a in actions if isinstance(a, dict)]


def compare_actions(
    expected: List[Dict[str, Any]],
    predicted: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    total_positions = max(len(expected), len(predicted))
    action_matches = 0
    param_matches = 0
    param_total = 0
    mismatches: List[Dict[str, Any]] = []

    for idx in range(total_positions):
        exp = expected[idx] if idx < len(expected) else None
        pred = predicted[idx] if idx < len(predicted) else None

        action_type_match = False
        if exp and pred:
            action_type_match = exp.get("action") == pred.get("action")
        if action_type_match:
            action_matches += 1

        exp_param_mismatches: Dict[str, Dict[str, Any]] = {}
        if exp:
            for key, value in exp.items():
                if key == "action":
                    continue
                param_total += 1
                pred_value = pred.get(key) if pred else None
                if pred_value == value:
                    param_matches += 1
                else:
                    exp_param_mismatches[key] = {
                        "expected": value,
                        "predicted": pred_value,
                    }

        if not exp or not pred or not action_type_match or exp_param_mismatches:
            mismatches.append(
                {
                    "index": idx,
                    "expected": exp,
                    "predicted": pred,
                    "action_match": action_type_match,
                    "param_mismatches": exp_param_mismatches,
                }
            )

    exact_match = (
        len(expected) == len(predicted)
        and action_matches == len(expected)
        and param_matches == param_total
    )

    metrics = {
        "exact_match": exact_match,
        "action_accuracy": (action_matches / total_positions) if total_positions else 1.0,
        "param_accuracy": (param_matches / param_total) if param_total else 1.0,
        "length_expected": len(expected),
        "length_predicted": len(predicted),
        "action_matches": action_matches,
        "action_total": total_positions,
        "param_matches": param_matches,
        "param_total": param_total,
    }
    return metrics, mismatches


def init_group_stats() -> Dict[str, Any]:
    return {
        "cases": 0,
        "exact": 0,
        "action_matches": 0,
        "action_total": 0,
        "param_matches": 0,
        "param_total": 0,
    }


def update_group_stats(stats: Dict[str, Any], metrics: Dict[str, Any]) -> None:
    stats["cases"] += 1
    stats["exact"] += 1 if metrics["exact_match"] else 0
    stats["action_matches"] += metrics["action_matches"]
    stats["action_total"] += metrics["action_total"]
    stats["param_matches"] += metrics["param_matches"]
    stats["param_total"] += metrics["param_total"]


def ratio(numerator: int, denominator: int) -> float:
    return (numerator / denominator) if denominator else 0.0


def run_eval(args: argparse.Namespace) -> int:
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Missing OPENAI_API_KEY. Set env or use --api-key.", file=sys.stderr)
        return 1

    service = ShoppingLLMService(api_key=api_key, model=args.model)
    cases = load_cases(args.test_file)
    if args.shuffle:
        random.seed(args.seed)
        random.shuffle(cases)
    if args.limit:
        cases = cases[: args.limit]

    overall = init_group_stats()
    by_difficulty: Dict[str, Dict[str, Any]] = {}
    results: List[Dict[str, Any]] = []

    for case in cases:
        difficulty = case.get("difficulty", "NA")
        by_difficulty.setdefault(difficulty, init_group_stats())

        utterance = case.get("user_utterance", "")
        expected_actions = normalize_actions(case.get("expected", {}).get("actions", []))

        prediction = service.map_command_to_actions(utterance)
        predicted_actions = normalize_actions(prediction.get("actions"))

        metrics, mismatches = compare_actions(expected_actions, predicted_actions)
        update_group_stats(overall, metrics)
        update_group_stats(by_difficulty[difficulty], metrics)

        results.append(
            {
                "id": case.get("id"),
                "difficulty": difficulty,
                "user_utterance": utterance,
                "expected_actions": expected_actions,
                "predicted_actions": predicted_actions,
                "metrics": metrics,
                "mismatches": mismatches,
                "llm_notes": prediction.get("notes", ""),
            }
        )

        if args.delay:
            time.sleep(args.delay)

    summary = {
        "total_cases": overall["cases"],
        "exact_match_rate": ratio(overall["exact"], overall["cases"]),
        "action_accuracy": ratio(overall["action_matches"], overall["action_total"]),
        "param_accuracy": ratio(overall["param_matches"], overall["param_total"]),
        "by_difficulty": {},
    }

    for difficulty, stats in by_difficulty.items():
        summary["by_difficulty"][difficulty] = {
            "cases": stats["cases"],
            "exact_match_rate": ratio(stats["exact"], stats["cases"]),
            "action_accuracy": ratio(stats["action_matches"], stats["action_total"]),
            "param_accuracy": ratio(stats["param_matches"], stats["param_total"]),
        }

    output_payload = {"summary": summary, "results": results}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)

    print("Evaluation complete.")
    print(f"Total cases: {summary['total_cases']}")
    print(f"Exact match rate: {summary['exact_match_rate']:.3f}")
    print(f"Action accuracy: {summary['action_accuracy']:.3f}")
    print(f"Param accuracy: {summary['param_accuracy']:.3f}")
    print(f"Saved report: {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate map_command_to_actions accuracy using test.json."
    )
    parser.add_argument(
        "--test-file",
        default="search_test/test.json",
        help="Path to test.json",
    )
    parser.add_argument(
        "--output",
        default="search_test/map_command_eval.json",
        help="Path to save the evaluation report JSON",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        help="OpenAI model name",
    )
    parser.add_argument("--api-key", default=None, help="OpenAI API key")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of cases")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle test cases")
    parser.add_argument("--seed", type=int, default=0, help="Random seed for shuffle")
    parser.add_argument(
        "--delay", type=float, default=0.0, help="Delay between calls in seconds"
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return run_eval(args)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
