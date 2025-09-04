import json
import os
import sys
import uuid
from typing import Any, Dict, List

from google.genai import types


# This class duplicates stdout to a file
class Tee(object):
    def __init__(self, filename, mode="a"):
        self.file = open(filename, mode)
        self.stdout = sys.stdout
        sys.stdout = self

    def __del__(self):
        sys.stdout = self.stdout
        self.file.close()

    def write(self, data):
        self.file.write(data)
        self.stdout.write(data)

    def flush(self):
        self.file.flush()
        self.stdout.flush()


SHOW_DIFF_CASES = True


def process_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return data


def original_solution(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for item in data:
        new_item = item.copy()
        new_item["solution_match_status"] = new_item.get("match_status")
        results.append(new_item)
    return results


def LLM_solution_1(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    print("--- Running LLM_solution_1 (LLM-based solution) ---", file=sys.stderr)

    try:
        from google import genai

        client = genai.Client(
            vertexai=True, project="tvlk-shared-services-stg", location="global"
        )
    except ImportError:
        print(
            "⚠️ google-genai not installed, fallback to original solution",
            file=sys.stderr,
        )
        return original_solution(data)

    results = []
    for item in data:
        new_item = item.copy()
        # generate a uuid
        uuid_str = item.get("uuid_str", "")

        tvl_data = item.get("tvl", {})
        competitor_data = item.get("competitor", {})

        tvl_size = tvl_data.get("hard_metrics", {}).get("room_size")
        tvl_name = tvl_data.get("soft_metrics", {}).get("room_group_name")
        tvl_bed_type = tvl_data.get("soft_metrics", {}).get("bed_type")
        tvl_occupancy = tvl_data.get("soft_metrics", {}).get("max_occupancy")
        tvl_breakfast = (
            tvl_data.get("soft_metrics", {})
            .get("amenities", {})
            .get("is_with_breakfast")
        )
        tvl_refundable = (
            tvl_data.get("soft_metrics", {}).get("amenities", {}).get("is_refundable")
        )
        tvl_cancellation_policy_code = (
            tvl_data.get("soft_metrics", {})
            .get("amenities", {})
            .get("cancellation_policy_code")
        )

        comp_size = competitor_data.get("hard_metrics", {}).get("room_size")
        comp_name = competitor_data.get("soft_metrics", {}).get("room_group_name")
        comp_bed_type = competitor_data.get("soft_metrics", {}).get("bed_type")
        comp_occupancy = competitor_data.get("soft_metrics", {}).get("max_occupancy")
        comp_breakfast = (
            competitor_data.get("soft_metrics", {})
            .get("amenities", {})
            .get("is_with_breakfast")
        )
        comp_refundable = (
            competitor_data.get("soft_metrics", {})
            .get("amenities", {})
            .get("is_refundable")
        )
        comp_cancellation_policy_code = (
            competitor_data.get("soft_metrics", {})
            .get("amenities", {})
            .get("cancellation_policy_code")
        )

        prompt = f"""
You are a hotel room matching expert. Judge whether two rooms from different sources should be considered the same room type based on human-friendly understanding.


## Matching Rules (By Priority)

### 1. Room Type Tier Matching (Highest Priority)
**Standard Room Type Tiers:**
- Basic/Standard/Classic → Standard Room
- Superior/Comfort/Plus → Superior Room
- Deluxe/Premium → Deluxe Room
- Executive/Club → Executive Room
- Suite/Junior Suite → Suite Room
- Villa/Penthouse/Apartment → Special Room Types

**Matching Rules:**
- Same tier → matched
- Adjacent tiers → matched 
- Cross-tier (e.g., Standard vs Deluxe) → mismatched

**Ignored Marketing Words:**
Ignore differences in these words: Premier, Grand, Luxury, Social, Corner, City, Garden, Romantic, Modern, Classic, and all view-related words (River View, Mountain View, etc.)

### 2. Occupancy Matching
- Occupancy difference ≤2 people → matched
- Occupancy difference >2 people → mismatched
- When data is missing, infer reasonableness from room name and bed type

### 3. Bed Type Matching (Lowest Priority)
**Compatible Bed Type Combinations:**
- King ↔ Queen ↔ Double → compatible
- 2 Single ↔ Twin → compatible  
- 2 Single/Twin ↔ Queen/King → judge by occupancy

**Incompatible:**
- Single vs King/Queen (unless occupancy is 1)

### 4. Mandatory Mismatch Situations
The following differences must be marked as mismatched:
- Private pool (private pool, plunge pool)
- Kitchen facilities (kitchen, kitchenette)
- Beachfront location (beachfront, oceanfront, overwater)
- Special structures (penthouse, loft, duplex)
- Spa/Sauna (onsen, sauna, hot tub)
- Club privileges (club lounge access)
- Dual key configurations (dual key, twin key)
- Different accommodation types (hotel room vs apartment unit vs serviced apartment)

### 5. Missing Data Handling
- Missing bed type: Judge only by room name tier and occupancy
- Missing occupancy: Infer from room name tier and bed type
- Vague room name: Focus on bed type and occupancy compatibility

## Decision Principles
1. **Room type tier is the decisive factor**
2. **Marketing word differences do not affect matching**  
3. **When in doubt, lean towards matched**
4. **Mandatory mismatch situations are exceptions**

## Output Requirements
Strictly output one of the following:
- `matched`
- `mismatched`

**Do not include any explanations, reasons, or other text.**
---
TVL Room:
- Name: {tvl_name}
- Bed Type: {tvl_bed_type}
- Occupancy: {tvl_occupancy}

Competitor Room:
- Name: {comp_name}
- Bed Type: {comp_bed_type}
- Occupancy: {comp_occupancy}
"""

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                ),
            )

            llm_decision = response.text.strip().lower()
            if llm_decision in ["matched", "mismatched"]:
                new_item["solution_match_status"] = llm_decision
            else:
                print(f"⚠️ Unexpected LLM response: {response.text}", file=sys.stderr)
                new_item["solution_match_status"] = "mismatched"

            print(
                f"\n[Input Data - {uuid_str}] "
                f"TVL:({tvl_name},{tvl_size},{tvl_bed_type},{tvl_occupancy},{tvl_breakfast},{tvl_refundable},{tvl_cancellation_policy_code}) "
                f"VS COMP:({comp_name},{comp_size},{comp_bed_type},{comp_occupancy},{comp_breakfast},{comp_refundable},{comp_cancellation_policy_code}) "
                f"=> LLM: {new_item['solution_match_status']}"
            )

        except Exception as e:
            print(f"❌ Error calling LLM: {e}", file=sys.stderr)
            new_item["solution_match_status"] = "mismatched"

        results.append(new_item)

    return results


def evaluate_solution(solution_name: str, transformed_data: List[Dict[str, Any]]):
    total_matched_by_solution = 0
    inaccurate_matches = 0
    total_size_error = 0
    true_positives = false_positives = false_negatives = 0

    for item in transformed_data:
        tvl_size_str = item.get("tvl", {}).get("hard_metrics", {}).get("room_size")
        competitor_size_str = (
            item.get("competitor", {}).get("hard_metrics", {}).get("room_size")
        )

        try:
            tvl_size = float(tvl_size_str) if tvl_size_str is not None else None
            competitor_size = (
                float(competitor_size_str) if competitor_size_str is not None else None
            )
        except (ValueError, TypeError):
            continue
        if (
            tvl_size is None
            or competitor_size is None
            or tvl_size <= 0
            or competitor_size <= 0
        ):
            continue

        # use SPD(Symmetrized Percent Difference (SPD)
        # Formula: SPD = 2*|A - B| / (A + B)
        is_true_match = (
            2 * abs(tvl_size - competitor_size) / (tvl_size + competitor_size) <= 0.2
        )
        solution_match_status = item.get("solution_match_status")

        if solution_match_status == "matched" or solution_match_status.startswith(
            "MATCH_"
        ):
            solution_match_status = "matched"
            total_matched_by_solution += 1
            if not is_true_match:
                inaccurate_matches += 1
                false_positives += 1
                total_size_error += abs(tvl_size - competitor_size)
            else:
                true_positives += 1
        elif solution_match_status == "mismatched" or solution_match_status.startswith(
            "NOT_MATCH"
        ):
            solution_match_status = "mismatched"
            if is_true_match:
                false_negatives += 1

    inaccuracy_rate = (
        (inaccurate_matches / total_matched_by_solution * 100)
        if total_matched_by_solution
        else 0
    )
    overall_inaccuracy_rate = (
        (inaccurate_matches / len(transformed_data) * 100)
        if len(transformed_data)
        else 0
    )

    avg_size_error = (
        (total_size_error / inaccurate_matches) if inaccurate_matches else 0
    )

    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives)
        else 0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives)
        else 0
    )
    f1_score = (
        2 * (precision * recall) / (precision + recall) if (precision + recall) else 0
    )

    print("\n---")
    print(f"Results for '{solution_name}':")
    print(
        f"Total entries evaluated: {len(transformed_data)}, total inaccurate entries: {inaccurate_matches}"
    )
    print(f"Total matched by solution: {total_matched_by_solution}")
    print(f"Total inaccurate matches (>1 sqm diff): {inaccurate_matches}")
    print(f"Inaccuracy Rate: {inaccuracy_rate:.2f}%")
    print(f"Overall Inaccuracy Rate: {overall_inaccuracy_rate:.2f}%")
    print(f"Average Size Error (inaccurates only): {avg_size_error:.2f} sqm")
    print(f"F1 Score: {f1_score:.4f}")
    print("---")


def print_size_summary(all_data: List[Dict[str, Any]]):
    tvl_sizes, competitor_sizes = [], []
    for item in all_data:
        try:
            if item.get("tvl", {}).get("hard_metrics", {}).get("room_size"):
                tvl_sizes.append(float(item["tvl"]["hard_metrics"]["room_size"]))
            if item.get("competitor", {}).get("hard_metrics", {}).get("room_size"):
                competitor_sizes.append(
                    float(item["competitor"]["hard_metrics"]["room_size"])
                )
        except (ValueError, TypeError):
            continue

    def summary(sizes):
        return (
            (min(sizes), max(sizes), sum(sizes) / len(sizes))
            if sizes
            else ("N/A", "N/A", "N/A")
        )

    tvl_min, tvl_max, tvl_avg = summary(tvl_sizes)
    comp_min, comp_max, comp_avg = summary(competitor_sizes)

    print("\n=== Room Size Distribution Summary ===")
    print(f"TVL Sizes: {tvl_min} / {tvl_max} / {tvl_avg}")
    print(f"Competitor Sizes: {comp_min} / {comp_max} / {comp_avg}")
    print("====================================")


def compare_solutions(
    input_data: List[Dict[str, Any]], solutions: Dict[str, List[Dict[str, Any]]]
):
    if not SHOW_DIFF_CASES:
        return

    print("\n=== Cases Table ===")
    header = [
        "UUID",
        "Case ID",
        "TVL Room Name",
        "TVL Size",
        "COMP Room Name",
        "COMP Size",
        "Original Match",
        "LLM Match",
        "equal?",
    ]
    print(
        "{:<36} | {:<8} | {:<55} | {:<8} | {:<55} | {:<8} | {:<14} | {:<10}| {:<10}".format(
            *header
        )
    )

    print("-" * 150)
    for i, (item, orig_item, llm_item) in enumerate(
        zip(input_data, solutions["Original Solution"], solutions["LLM Solution 1"])
    ):
        uuid_str = item.get("uuid_str") or ""
        case_id = item.get("tvl_id") or f"case_{i}"
        tvl_name = (
            item.get("tvl", {}).get("soft_metrics", {}).get("room_group_name") or ""
        )
        tvl_size = item.get("tvl", {}).get("hard_metrics", {}).get("room_size")
        tvl_size = "" if tvl_size is None else tvl_size
        comp_name = (
            item.get("competitor", {}).get("soft_metrics", {}).get("room_group_name")
            or ""
        )
        comp_size = item.get("competitor", {}).get("hard_metrics", {}).get("room_size")
        comp_size = "" if comp_size is None else comp_size
        original_status = (
            solutions["Original Solution"][i].get("solution_match_status") or ""
        )
        original_status = (
            "matched" if original_status.startswith("MATCH_") else original_status
        )
        original_status = (
            "mismatched" if original_status.startswith("NOT_MATCH") else original_status
        )
        llm_status = solutions["LLM Solution 1"][i].get("solution_match_status") or ""
        print(
            "{:<36} | {:<8} | {:<55} | {:<8} | {:<55} | {:<8} | {:<14} | {:<10} | {:<10}".format(
                uuid_str,
                case_id,
                tvl_name,
                tvl_size,
                comp_name,
                comp_size,
                original_status,
                llm_status,
                "equal" if original_status == llm_status else "DIFF",
            )
        )
    print("====================================\n")


def deduplicate_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped = []
    for item in data:
        item_key = json.dumps(item, sort_keys=True)
        if item_key not in seen:
            seen.add(item_key)
            deduped.append(item)
    print(
        f"before dedup {len(data)}, after dedup {len(deduped)}, removed {len(data) - len(deduped)}"
    )
    return deduped


def main():
    start = 700
    cnt = 200
    start = 0
    cnt = 1600
    input_file_name = "xrm_sample_1600_datapoints_v2"
    output_filename = f"{input_file_name}_output_{start}-{cnt}.txt"
    tee = Tee(output_filename, "w")

    print("Starting benchmark process...")
    files_to_process = [f"./data/{input_file_name}.json"]
    all_raw_data = []
    for path in files_to_process:
        try:
            with open(path, "r", encoding="utf-8") as f:
                all_raw_data.extend(json.load(f))
        except Exception as e:
            print(f"⚠️ Error loading {path}: {e}", file=sys.stderr)

    if not all_raw_data:
        print("No data loaded. Exit.")
        return

    input_data = [
        item
        for item in all_raw_data
        if "tvl" in item
        and "competitor" in item
        and "hard_metrics" in item.get("tvl", {})
        and "room_size" in item["tvl"]["hard_metrics"]
        and "soft_metrics" in item["tvl"]
        and "room_group_name" in item["tvl"]["soft_metrics"]
        and item["tvl"]["soft_metrics"]["room_group_name"] is not None
        and item["competitor"]["soft_metrics"]["room_group_name"] is not None
    ]

    input_data = deduplicate_data(input_data)

    for item in input_data:
        item["uuid_str"] = str(uuid.uuid4())
    original_results = original_solution(input_data)
    evaluate_solution("Original Solution", original_results)

    input_data = input_data[start : start + cnt]
    print_size_summary(input_data)

    # Run solutions
    original_results = original_solution(input_data)
    evaluate_solution("Original Solution", original_results)

    llm_results = LLM_solution_1(input_data)
    evaluate_solution("LLM Solution 1", llm_results)

    # Compare
    compare_solutions(
        input_data,
        {"Original Solution": original_results, "LLM Solution 1": llm_results},
    )

    del tee


if __name__ == "__main__":
    main()
