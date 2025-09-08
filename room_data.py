from typing import Any, Dict, Optional
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class RoomData:
    """Structured room data"""

    name: str
    size: Optional[float]
    bed_type: Optional[str]
    occupancy: Optional[int]
    breakfast: Optional[bool]
    refundable: Optional[bool]
    cancellation_policy_code: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any], source: str = "tvl") -> "RoomData":
        """Create RoomData from dictionary"""
        metrics = data.get(source, {})
        hard_metrics = metrics.get("hard_metrics", {})
        soft_metrics = metrics.get("soft_metrics", {})
        amenities = soft_metrics.get("amenities", {})

        # Parse size safely
        size_str = hard_metrics.get("room_size")
        size = None
        if size_str is not None:
            try:
                size = float(size_str)
                if size <= 0:
                    size = None
            except (ValueError, TypeError):
                size = None

        return cls(
            name=soft_metrics.get("room_group_name", ""),
            size=size,
            bed_type=soft_metrics.get("bed_type"),
            occupancy=soft_metrics.get("max_occupancy"),
            breakfast=amenities.get("is_with_breakfast"),
            refundable=amenities.get("is_refundable"),
            cancellation_policy_code=amenities.get("cancellation_policy_code"),
        )


@dataclass
class MatchResult:
    """Result of room matching decision"""

    decision: str
    size_correct: bool
    confidence_score: float
    reasoning: str

    @classmethod
    def from_llm_response(
        cls, response_text: str, tvl_room: RoomData, comp_room: RoomData
    ) -> "MatchResult":
        """Parse LLM JSON response and create MatchResult"""
        try:
            # Try to parse JSON response
            response_data = json.loads(response_text.strip())
            decision = response_data.get("decision", "mismatched").lower()
            confidence_score = response_data.get("confidence_score", 0.5)
            reasoning = response_data.get("reasoning", "No reasoning provided")

            if decision not in ["matched", "mismatched"]:
                decision = "mismatched"
                confidence_score = 0.1
                reasoning = f"Invalid decision format: {response_text}"

        except json.JSONDecodeError:
            # Fallback: try to parse simple text response
            decision = response_text.strip().lower()
            if decision in ["matched", "mismatched"]:
                confidence_score = 0.8  # Default confidence for simple responses
                reasoning = "Simple text response without detailed reasoning"
            else:
                decision = "mismatched"
                confidence_score = 0.1
                reasoning = f"Unparseable response: {response_text}"

        # Calculate size_correct
        size_correct = cls._calculate_size_correct(tvl_room.size, comp_room.size)
        return cls(decision, size_correct, confidence_score, reasoning)

    @classmethod
    def from_llm_xml_response(
        cls, response_text: str, tvl_room: RoomData, comp_room: RoomData
    ) -> "MatchResult":
        """Parse LLM XML response and create MatchResult"""
        try:
            # Clean the response text and extract XML
            cleaned_text = response_text.strip()

            # Find XML content between <match_result> tags
            start_tag = "<match_result>"
            end_tag = "</match_result>"

            start_idx = cleaned_text.find(start_tag)
            end_idx = cleaned_text.find(end_tag)

            if start_idx != -1 and end_idx != -1:
                xml_content = cleaned_text[start_idx : end_idx + len(end_tag)]
            else:
                # If no proper XML tags found, try to parse the whole response
                xml_content = cleaned_text
                if not xml_content.startswith("<"):
                    xml_content = f"<match_result>{xml_content}</match_result>"

            # Parse XML
            root = ET.fromstring(xml_content)

            # Extract values
            decision_elem = root.find("decision")
            confidence_elem = root.find("confidence_score")
            reasoning_elem = root.find("reasoning")

            decision = (
                decision_elem.text.lower()
                if decision_elem is not None and decision_elem.text
                else "mismatched"
            )

            try:
                confidence_score = (
                    float(confidence_elem.text)
                    if confidence_elem is not None and confidence_elem.text
                    else 0.5
                )
                # Ensure confidence score is between 0 and 1
                confidence_score = max(0.0, min(1.0, confidence_score))
            except (ValueError, TypeError):
                confidence_score = 0.5

            reasoning = (
                reasoning_elem.text
                if reasoning_elem is not None and reasoning_elem.text
                else "No reasoning provided"
            )

            # Validate decision
            if decision not in ["matched", "mismatched"]:
                decision = "mismatched"
                confidence_score = 0.1
                reasoning = f"Invalid decision format: {decision}"

        except ET.ParseError as e:
            # XML parsing failed, try fallback parsing
            decision, confidence_score, reasoning = cls._fallback_parse(response_text)
        except Exception as e:
            # Any other error
            decision = "mismatched"
            confidence_score = 0.1
            reasoning = f"Error parsing XML response: {str(e)}"

        # Calculate size_correct
        size_correct = cls._calculate_size_correct(tvl_room.size, comp_room.size)
        return cls(decision, size_correct, confidence_score, reasoning)

    @staticmethod
    def _fallback_parse(response_text: str) -> tuple[str, float, str]:
        """Fallback parsing for non-XML responses"""
        cleaned_text = response_text.strip().lower()

        if "matched" in cleaned_text and "mismatched" not in cleaned_text:
            return "matched", 0.7, "Fallback parsing: found 'matched' in response"
        elif "mismatched" in cleaned_text:
            return "mismatched", 0.7, "Fallback parsing: found 'mismatched' in response"
        else:
            return (
                "mismatched",
                0.1,
                f"Fallback parsing failed: {response_text[:100]}...",
            )

    @staticmethod
    def _calculate_size_correct(
        tvl_size: Optional[float], comp_size: Optional[float]
    ) -> bool:
        """Calculate if room sizes are similar using SPD (Symmetrized Percent Difference)"""
        if tvl_size is None or comp_size is None or tvl_size <= 0 or comp_size <= 0:
            return False

        # SPD = 2*|A - B| / (A + B)
        spd = 2 * abs(tvl_size - comp_size) / (tvl_size + comp_size)
        return spd <= 0.2
