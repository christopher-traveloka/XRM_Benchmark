import json
import sys
from typing import List, Dict, Any


def process_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Processes the raw data to prepare it for solution evaluation.
    This function simply returns the data as is, as all information is already
    present in the JSON files.
    """
    return data


def original_solution(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    This function now correctly uses the 'match_status' field from the
    original JSON data as the result of the 'Original Solution' for benchmarking.
    """
    results = []
    for item in data:
        new_item = item.copy()
        # Use the match_status directly from the raw JSON data as the solution's result
        new_item["solution_match_status"] = new_item.get("match_status")
        results.append(new_item)
    return results


def LLM_solution_1(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Placeholder for the new LLM-based room matching solution.
    You can implement your logic here. For now, it copies the original solution.
    """
    print("--- Running LLM_solution_1 (Placeholder) ---", file=sys.stderr)
    return original_solution(data)  # Currently just a copy of the original solution


def evaluate_solution(solution_name: str, transformed_data: List[Dict[str, Any]]):
    """
    Evaluates a solution and prints its inaccuracy rate and F1 score,
    along with additional size-related metrics.

    The 'Ground Truth' for this evaluation is defined as:
    A match is considered 'True' if the room size difference is <= 1.0 sqm.
    This is a proxy for the lack of a perfect ground truth in the data.
    """
    total_matched_by_solution = 0
    inaccurate_matches = 0
    total_size_error = 0

    true_positives = 0
    false_positives = 0
    false_negatives = 0

    for item in transformed_data:
        tvl_size_str = item.get("tvl", {}).get("hard_metrics", {}).get("room_size")
        competitor_size_str = (
            item.get("competitor", {}).get("hard_metrics", {}).get("room_size")
        )

        tvl_size = None
        competitor_size = None

        try:
            if tvl_size_str is not None:
                tvl_size = float(tvl_size_str)
            if competitor_size_str is not None:
                competitor_size = float(competitor_size_str)
        except (ValueError, TypeError):
            continue
        if tvl_size is None or competitor_size is None:
            continue

        # print(tvl_size, competitor_size)
        # Our proxy 'Ground Truth': Is it a true match based on size?
        is_true_match = False
        if abs(tvl_size - competitor_size) <= 1.0:
            is_true_match = True

        solution_match_status = item.get("solution_match_status")

        if solution_match_status == "matched":
            total_matched_by_solution += 1
            if not is_true_match:
                print(
                    f"  Inaccurate Match Detected: TVL Size={tvl_size}, Competitor Size={competitor_size}"
                )
                inaccurate_matches += 1
                false_positives += 1
                if tvl_size is not None and competitor_size is not None:
                    total_size_error += abs(tvl_size - competitor_size)
            else:
                true_positives += 1
        elif solution_match_status == "mismatched":
            if is_true_match:
                false_negatives += 1

    inaccuracy_rate = (
        (inaccurate_matches / total_matched_by_solution) * 100
        if total_matched_by_solution > 0
        else 0
    )
    print("total_size_error:", total_size_error)
    print(f"inaccurate_matches: {inaccurate_matches}")
    average_size_error_inaccurate = (
        total_size_error / inaccurate_matches if inaccurate_matches > 0 else 0
    )

    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0
    )
    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0
    )

    print("---")
    print(f"Results for '{solution_name}':")
    print(f"Total entries evaluated: {len(transformed_data)}")
    print(f"Total matched by solution: {total_matched_by_solution}")
    print(f"Total inaccurate matches (size diff > 1 sqm): {inaccurate_matches}")
    print(f"Inaccuracy Rate: {inaccuracy_rate:.2f}%")
    print(
        f"Average Size Error for Inaccurate Matches: {average_size_error_inaccurate:.2f} sqm"
    )
    print(f"F1 Score: {f1_score:.4f}")
    print("---")


def print_size_summary(all_data: List[Dict[str, Any]]):
    """
    Prints a summary of the room sizes for both TVL and competitor data.
    """
    tvl_sizes = []
    competitor_sizes = []

    for item in all_data:
        try:
            tvl_size_str = item.get("tvl", {}).get("hard_metrics", {}).get("room_size")
            if tvl_size_str is not None:
                tvl_sizes.append(float(tvl_size_str))

            competitor_size_str = (
                item.get("competitor", {}).get("hard_metrics", {}).get("room_size")
            )
            if competitor_size_str is not None:
                competitor_sizes.append(float(competitor_size_str))
        except (ValueError, TypeError):
            continue

    def get_summary(sizes):
        if not sizes:
            return "N/A", "N/A", "N/A"
        return min(sizes), max(sizes), sum(sizes) / len(sizes)

    tvl_min, tvl_max, tvl_avg = get_summary(tvl_sizes)
    comp_min, comp_max, comp_avg = get_summary(competitor_sizes)

    print("\n=== Room Size Distribution Summary ===")
    print(
        f"TVL Room Sizes (min/max/avg): {tvl_min:.2f} / {tvl_max:.2f} / {tvl_avg:.2f} sqm"
    )
    print(
        f"Competitor Room Sizes (min/max/avg): {comp_min:.2f} / {comp_max:.2f} / {comp_avg:.2f} sqm"
    )
    print("====================================")


def main():
    """
    Main function to run the benchmarking process.
    """
    print("Starting benchmark process...")
    files_to_process = [
        "./data/new_sample_20250827_batch_1.json",
        "./data/new_sample_20250827_batch_2.json",
    ]
    all_raw_data = []

    for file_path in files_to_process:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                all_raw_data.extend(json.load(f))
        except FileNotFoundError:
            print(f"Error: The file '{file_path}' was not found.", file=sys.stderr)
            continue
        except json.JSONDecodeError:
            print(
                f"Error: The file '{file_path}' is not a valid JSON.", file=sys.stderr
            )
            continue
        except Exception as e:
            print(
                f"An unexpected error occurred while processing {file_path}: {e}",
                file=sys.stderr,
            )
            continue

    if not all_raw_data:
        print("No data was processed. Exiting.")
        return

    print_size_summary(all_raw_data)

    # Run and evaluate Original Solution
    original_results = original_solution(all_raw_data)
    evaluate_solution("Original Solution", original_results)

    # # Run and evaluate New LLM Solution 1
    # llm_results = LLM_solution_1(all_raw_data)
    # evaluate_solution("LLM Solution 1", llm_results)


if __name__ == "__main__":
    main()
