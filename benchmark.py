import json
import sys
import uuid
from typing import Any, Dict, List, Optional

from room_data import RoomData
from room_matcher import RoomMatcher


class Tee:
    """Duplicate stdout to a file"""

    def __init__(self, filename: str, mode: str = "a"):
        self.file = open(filename, mode)
        self.stdout = sys.stdout
        sys.stdout = self

    def __del__(self):
        sys.stdout = self.stdout
        self.file.close()

    def write(self, data: str):
        self.file.write(data)
        self.stdout.write(data)

    def flush(self):
        self.file.flush()
        self.stdout.flush()


class Evaluator:
    """Evaluation and reporting system"""

    def __init__(self, show_diff_cases: bool = True):
        self.show_diff_cases = show_diff_cases

    def evaluate_solution(self, solution_name: str, results: List[Dict[str, Any]]):
        """Evaluate matching solution performance"""
        metrics = self._calculate_metrics(results)
        self._print_evaluation(solution_name, metrics, len(results))

    def _calculate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate evaluation metrics"""
        total_matched = 0
        size_incorrect_matches = 0
        total_size_error = 0
        tp = fp = fn = tn = 0
        low_confidence_count = 0
        confidence_scores = []

        for item in results:
            size_correct = item.get("size_correct", False)
            solution_status = self._normalize_status(
                item.get("solution_match_status", "")
            )
            confidence_score = item.get("confidence_score", 1.0)

            confidence_scores.append(confidence_score)
            if confidence_score < 0.7:
                low_confidence_count += 1

            if solution_status == "matched":
                total_matched += 1
                if size_correct:
                    tp += 1
                else:
                    fp += 1
                    size_incorrect_matches += 1
                    # Calculate size error if available
                    tvl_size = self._get_room_size(item, "tvl")
                    comp_size = self._get_room_size(item, "competitor")
                    if tvl_size and comp_size:
                        total_size_error += abs(tvl_size - comp_size)
            else:
                if size_correct:
                    fn += 1
                else:
                    tn += 1

        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        )
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        return {
            "total_matched": total_matched,
            "size_incorrect_matches": size_incorrect_matches,
            "avg_size_error": total_size_error / size_incorrect_matches
            if size_incorrect_matches > 0
            else 0,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
            "avg_confidence": avg_confidence,
            "low_confidence_count": low_confidence_count,
        }

    def _normalize_status(self, status: str) -> str:
        """Normalize match status"""
        if status.startswith("MATCH_"):
            return "matched"
        elif status.startswith("NOT_MATCH"):
            return "mismatched"
        return status.lower()

    def _get_room_size(self, item: Dict[str, Any], source: str) -> Optional[float]:
        """Extract room size from item"""
        try:
            size_str = item.get(source, {}).get("hard_metrics", {}).get("room_size")
            if size_str is not None:
                size = float(size_str)
                return size if size > 0 else None
        except (ValueError, TypeError):
            pass
        return None

    def _print_evaluation(
        self, solution_name: str, metrics: Dict[str, Any], total_entries: int
    ):
        """Print evaluation results"""
        inaccuracy_rate = (
            (metrics["size_incorrect_matches"] / metrics["total_matched"] * 100)
            if metrics["total_matched"] > 0
            else 0
        )
        overall_inaccuracy_rate = (
            (metrics["size_incorrect_matches"] / total_entries * 100)
            if total_entries > 0
            else 0
        )

        print("\n" + "=" * 50)
        print(f"Results for '{solution_name}':")
        print(f"Total entries evaluated: {total_entries}")
        print(f"Total matched by solution: {metrics['total_matched']}")
        print(f"Size-incorrect matches: {metrics['size_incorrect_matches']}")
        print(f"Inaccuracy Rate: {inaccuracy_rate:.2f}%")
        print(f"Overall Inaccuracy Rate: {overall_inaccuracy_rate:.2f}%")
        print(f"Average Size Error: {metrics['avg_size_error']:.2f} sqm")
        print(f"Average Confidence: {metrics['avg_confidence']:.3f}")
        print(f"Low Confidence Cases (<0.7): {metrics['low_confidence_count']}")
        print(f"Precision: {metrics['precision']:.4f}")
        print(f"Recall: {metrics['recall']:.4f}")
        print(f"F1 Score: {metrics['f1_score']:.4f}")
        print("\nConfusion Matrix:")
        print(f"  True Positives (TP): {metrics['tp']} (matched & size_correct)")
        print(f"  False Positives (FP): {metrics['fp']} (matched & !size_correct)")
        print(f"  True Negatives (TN): {metrics['tn']} (mismatched & !size_correct)")
        print(f"  False Negatives (FN): {metrics['fn']} (mismatched & size_correct)")
        print("=" * 50)

    def compare_solutions(
        self,
        input_data: List[Dict[str, Any]],
        solutions: Dict[str, List[Dict[str, Any]]],
    ):
        """Compare different solutions"""
        if not self.show_diff_cases:
            return

        print("\n=== Enhanced Cases Comparison Table ===")
        header = [
            "UUID",
            "Case ID",
            "TVL Room",
            "TVL Size",
            "COMP Room",
            "COMP Size",
            "Original",
            "LLM",
            "Size OK",
            "LLM Conf",
            "Equal?",
        ]

        col_widths = [36, 8, 40, 8, 40, 8, 10, 10, 8, 8, 8]
        header_line = " | ".join(f"{h:<{w}}" for h, w in zip(header, col_widths))
        print(header_line)
        print("-" * len(header_line))

        original_solution = solutions.get("Original Solution", [])
        llm_solution = solutions.get("LLM Solution", [])

        for i, (item, orig_item, llm_item) in enumerate(
            zip(input_data, original_solution, llm_solution)
        ):
            uuid_str = item.get("uuid_str", "")[:35]
            case_id = str(item.get("tvl_id", f"case_{i}"))[:7]

            tvl_room = RoomData.from_dict(item, "tvl")
            comp_room = RoomData.from_dict(item, "competitor")

            original_status = self._normalize_status(
                orig_item.get("solution_match_status", "")
            )
            llm_status = self._normalize_status(
                llm_item.get("solution_match_status", "")
            )
            size_correct = llm_item.get("size_correct", False)
            confidence = llm_item.get("confidence_score", 0.0)

            values = [
                uuid_str,
                case_id,
                tvl_room.name[:39],
                str(tvl_room.size or "")[:7],
                comp_room.name[:39],
                str(comp_room.size or "")[:7],
                original_status[:9],
                llm_status[:9],
                "✓" if size_correct else "✗",
                f"{confidence:.2f}",
                "=" if original_status == llm_status else "DIFF",
            ]

            line = " | ".join(f"{str(v):<{w}}" for v, w in zip(values, col_widths))
            print(line)

        print("=" * 50)

    def print_size_summary(self, data: List[Dict[str, Any]]):
        """Print room size distribution summary"""
        tvl_sizes, comp_sizes = [], []

        for item in data:
            tvl_size = self._get_room_size(item, "tvl")
            comp_size = self._get_room_size(item, "competitor")

            if tvl_size:
                tvl_sizes.append(tvl_size)
            if comp_size:
                comp_sizes.append(comp_size)

        def calc_summary(sizes):
            if not sizes:
                return "N/A", "N/A", "N/A"
            return (
                f"{min(sizes):.1f}",
                f"{max(sizes):.1f}",
                f"{sum(sizes) / len(sizes):.1f}",
            )

        tvl_min, tvl_max, tvl_avg = calc_summary(tvl_sizes)
        comp_min, comp_max, comp_avg = calc_summary(comp_sizes)

        print("\n=== Room Size Distribution Summary ===")
        print(f"TVL Sizes (min/max/avg): {tvl_min} / {tvl_max} / {tvl_avg}")
        print(f"Competitor Sizes (min/max/avg): {comp_min} / {comp_max} / {comp_avg}")
        print("====================================")


class DataProcessor:
    """Data loading and preprocessing"""

    @staticmethod
    def load_data(file_path: str) -> List[Dict[str, Any]]:
        """Load data from JSON file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading {file_path}: {e}", file=sys.stderr)
            return []

    @staticmethod
    def filter_valid_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter data to include only valid entries"""
        return [
            item
            for item in data
            if all(
                [
                    "tvl" in item and "competitor" in item,
                    "hard_metrics" in item.get("tvl", {}),
                    "room_size" in item["tvl"]["hard_metrics"],
                    "soft_metrics" in item.get("tvl", {}),
                    "room_group_name" in item["tvl"]["soft_metrics"],
                    item["tvl"]["soft_metrics"]["room_group_name"] is not None,
                    item.get("competitor", {})
                    .get("soft_metrics", {})
                    .get("room_group_name")
                    is not None,
                ]
            )
        ]

    @staticmethod
    def deduplicate_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate entries"""
        seen = set()
        deduped = []
        for item in data:
            item_key = json.dumps(item, sort_keys=True)
            if item_key not in seen:
                seen.add(item_key)
                deduped.append(item)

        print(
            f"Deduplication: {len(data)} → {len(deduped)} (removed {len(data) - len(deduped)})"
        )
        return deduped

    @staticmethod
    def add_uuids(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add UUID to each data entry"""
        for item in data:
            item["uuid_str"] = str(uuid.uuid4())
        return data


def main():
    """Main execution function"""
    # Configuration
    start = 0
    cnt = 300
    input_file_name = "xrm_sample_1600_datapoints_v2"
    output_filename = f"./output/{input_file_name}_output_{start}-{cnt}.txt"

    # Initialize components
    tee = Tee(output_filename, "w")
    matcher = RoomMatcher()  # Enable detailed logging
    evaluator = Evaluator(show_diff_cases=True)
    processor = DataProcessor()

    print("Starting enhanced hotel room matching benchmark...")

    # Load and preprocess data
    file_path = f"./data/{input_file_name}.json"
    raw_data = processor.load_data(file_path)

    if not raw_data:
        print("No data loaded. Exiting.")
        return

    # Process data pipeline
    valid_data = processor.filter_valid_data(raw_data)
    deduped_data = processor.deduplicate_data(valid_data)
    full_dataset = processor.add_uuids(deduped_data)

    # Evaluate on full dataset first (for original solution)
    original_results_full = matcher.original_solution(full_dataset)
    evaluator.evaluate_solution(
        "Original Solution (Full Dataset)", original_results_full
    )

    # Work with subset
    subset_data = full_dataset[start : start + cnt]
    evaluator.print_size_summary(subset_data)

    # Run matching solutions
    print(f"\nProcessing subset: {len(subset_data)} entries")
    original_results = matcher.original_solution(subset_data)
    llm_results = matcher.llm_solution(subset_data)

    # Evaluate solutions
    evaluator.evaluate_solution("Original Solution", original_results)
    evaluator.evaluate_solution("LLM Solution", llm_results)

    # Compare solutions
    evaluator.compare_solutions(
        subset_data,
        {"Original Solution": original_results, "LLM Solution": llm_results},
    )

    # Cleanup
    del tee
    print("Benchmark completed.")


if __name__ == "__main__":
    main()
