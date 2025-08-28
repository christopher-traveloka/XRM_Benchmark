import json

def transform_data(input_data):
    """
    Transforms the raw data into the desired benchmark JSON format.
    """
    output_data = []
    
    # Iterate through each top-level entry in the input data
    for entry in input_data:
        hotel_id = entry.get('hotel_id', 'N/A')
        
        # Assume a default hotel name as it's not in the source data
        hotel_name = "N/A"
        
        # Iterate through the list of room adjustments for each hotel
        for item in entry.get('chosen_inventory_adjustment', []):
            tvl_metrics = {
                "hard_metrics": {
                    "room_size": item.get('room_size')
                },
                "soft_metrics": {
                    # This information is not available in the source data, using a placeholder
                    "room_group_name": "N/A", 
                    "bed_type": item.get('bed_type'),
                    "max_occupancy": int(entry.get('pricing_spec', {}).get('num_of_adults', 0)) + \
                                     int(entry.get('pricing_spec', {}).get('num_of_children', 0)) + \
                                     int(entry.get('pricing_spec', {}).get('num_of_infants', 0)),
                    "amenities": {
                        "is_with_breakfast": str(item.get('is_with_breakfast')).lower() == 'true',
                        "is_refundable": str(item.get('is_refundable')).lower() == 'true',
                        "cancellation_policy_code": item.get('cancellation_policy_code', "")
                    },
                    "view": ""
                }
            }
            
            competitor_room_match = item.get('ninja_room_match', {})
            
            # Safely get amenities from competitor, handling potential None values
            competitor_is_with_breakfast = str(competitor_room_match.get('competitor_is_with_breakfast')).lower() == 'true'
            competitor_is_refundable = str(competitor_room_match.get('competitor_is_refundable')).lower() == 'true'

            competitor_metrics = {
                "hard_metrics": {
                    "room_size": competitor_room_match.get('room_size')
                },
                "soft_metrics": {
                    "room_group_name": competitor_room_match.get('chosen_competitor_room_name'),
                    "bed_type": competitor_room_match.get('bed_type'),
                    # This information is not available for the competitor, using None
                    "max_occupancy": None,
                    "amenities": {
                        "is_with_breakfast": competitor_is_with_breakfast,
                        "is_refundable": competitor_is_refundable,
                        "cancellation_policy_code": competitor_room_match.get('competitor_cancellation_policy_code', "")
                    },
                    "view": ""
                }
            }
            
            # Determine match status based on room size and `room_size_accuracy_check`
            match_status = "matched"
            room_size_check = item.get('room_size_accuracy_check')
            if room_size_check == "NOT_MATCH":
                match_status = "mismatched"
            elif room_size_check is None:
                tvl_size = tvl_metrics['hard_metrics']['room_size']
                competitor_size = competitor_metrics['hard_metrics']['room_size']
                if tvl_size is not None and competitor_size is not None and float(tvl_size) != float(competitor_size):
                    match_status = "mismatched"
            
            # Construct the final JSON object for this room
            transformed_entry = {
                "hotel_id": hotel_id,
                "hotel_name": hotel_name,
                "match_status": match_status,
                "tvl": tvl_metrics,
                "competitor": competitor_metrics,
                "notes": ""
            }
            output_data.append(transformed_entry)
            
    return output_data

def process_file(file_path):
    """
    Reads a JSON file, transforms its content, and prints the result.
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            transformed_data = transform_data(data)
            print(json.dumps(transformed_data, indent=2))
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' is not a valid JSON.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage with the uploaded file
if __name__ == "__main__":
    process_file('./data/sample_20250826.json')

