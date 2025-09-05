import sys
from typing import Any, Dict, List

from google.genai import types

from room_data import MatchResult, RoomData


class RoomMatcher:
    """Hotel room matching system"""

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Lazy initialization of Google GenAI client"""
        if self._client is None:
            try:
                from google import genai

                self._client = genai.Client(
                    vertexai=True, project="tvlk-shared-services-stg", location="global"
                )
            except ImportError:
                print(
                    "⚠️ google-genai not installed, fallback to original solution",
                    file=sys.stderr,
                )
                self._client = False
        return self._client

    def _create_prompt(self, tvl_room: RoomData, comp_room: RoomData) -> str:
        """Create matching prompt for LLM"""
        return f"""
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
Output a JSON object with the following structure, do not add ```:
{{
  "decision": "matched" or "mismatched",
  "confidence_score": 0.0 to 1.0,
  "reasoning": "Brief explanation of the decision based on the rules above"
}}

**Example:**
{{
  "decision": "matched",
  "confidence_score": 0.95,
  "reasoning": "Both are 'Deluxe' tier, bed types are compatible (King vs Double), and mandatory mismatch factors are not present."
}}

---
TVL Room:
- Name: {tvl_room.name}
- Bed Type: {tvl_room.bed_type}
- Occupancy: {tvl_room.occupancy}

Competitor Room:
- Name: {comp_room.name}
- Bed Type: {comp_room.bed_type}
- Occupancy: {comp_room.occupancy}
"""

    def original_solution(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Original matching solution"""
        results = []
        for item in data:
            new_item = item.copy()
            original_status = new_item.get("match_status")

            # Parse rooms for size_correct calculation
            tvl_room = RoomData.from_dict(item, "tvl")
            comp_room = RoomData.from_dict(item, "competitor")
            size_correct = MatchResult._calculate_size_correct(
                tvl_room.size, comp_room.size
            )

            new_item["solution_match_status"] = original_status
            new_item["size_correct"] = size_correct
            new_item["confidence_score"] = 1.0  # Original solution has no uncertainty
            new_item["reasoning"] = "Original rule-based matching"

            results.append(new_item)
        return results

    def llm_solution(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """LLM-based matching solution"""
        print(
            "--- Running LLM Solution (Enhanced with confidence scoring) ---",
            file=sys.stderr,
        )

        client = self._get_client()
        if not client:
            return self.original_solution(data)

        results = []
        for item in data:
            new_item = item.copy()
            uuid_str = item.get("uuid_str", "")

            # Parse room data
            tvl_room = RoomData.from_dict(item, "tvl")
            comp_room = RoomData.from_dict(item, "competitor")

            # Create and send prompt
            prompt = self._create_prompt(tvl_room, comp_room)

            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(thinking_budget=0)
                    ),
                )

                # Parse response
                match_result = MatchResult.from_llm_response(
                    response.text, tvl_room, comp_room
                )

                new_item["solution_match_status"] = match_result.decision
                new_item["size_correct"] = match_result.size_correct
                new_item["confidence_score"] = match_result.confidence_score
                new_item["reasoning"] = match_result.reasoning

                print(
                    f"\n[{uuid_str}] "
                    f"TVL:({tvl_room.name},{tvl_room.size},{tvl_room.bed_type},{tvl_room.occupancy}) "
                    f"VS COMP:({comp_room.name},{comp_room.size},{comp_room.bed_type},{comp_room.occupancy}) "
                    f"=> {match_result.decision} (conf:{match_result.confidence_score:.2f}, size_ok:{match_result.size_correct})"
                )
                print(f"Reasoning: {match_result.reasoning}")

            except Exception as e:
                print(f"❌ Error calling LLM for {uuid_str}: {e}", file=sys.stderr)
                new_item["solution_match_status"] = "mismatched"
                new_item["size_correct"] = MatchResult._calculate_size_correct(
                    tvl_room.size, comp_room.size
                )
                new_item["confidence_score"] = 0.0
                new_item["reasoning"] = f"Error: {str(e)}"

            results.append(new_item)

        return results
