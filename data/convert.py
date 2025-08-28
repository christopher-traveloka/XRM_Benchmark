import json
import sys
import requests
from functools import lru_cache
import os

# 请在此处填入您的认证信息
# 这些信息通常具有时效性，如果脚本运行出错，请重新从浏览器中获取
AUTH0_TOKEN ="eyJraWQiOiJYRGJhaHFMdXhRdUFDTHhMaXZoVkRjV2g2OXo2cXNsSndUUGdyWlQzNWswPSIsImFsZyI6IlJTMjU2In0.eyJodHRwczpcL1wvdHZsa1wvcGVybWlzc2lvbnMiOiJbXCJlOnN0cnBoXCIsXCJ2OnN0cnBoXCIsXCJlOmNkeW50bFwiLFwiZTpzc3RvcnlcIixcImM6c3N0b3J5XCIsXCJ2OnNzdG9yeVwiLFwiZDpzc3RvcnlcIixcImU6Y250cm1wb21vZFwiLFwidjpybWR0bW5nbW50bFwiLFwidjpodGxncnBjZmdcIixcInY6cWNrZmx0clwiLFwiYzpydnd0Z2dcIixcImU6cHZkaW1wcnRjZmdcIixcImM6Y3BucnN0cmN0blwiLFwidjpwcnZkcmZ0Y2hcIixcInY6cHJzcmNoaW52XCIsXCJ2OmFjdExvZ1wiLFwidjpwY29tXCIsXCJ2OnFja3RhYlwiLFwiZTpodGxwcGlja1wiLFwiZTpwcmNkcGhnXCIsXCJlOnNwY2xwbGNcIixcInY6cHJjZHBoZ1wiLFwiYzpjb3NoZ1wiLFwidjpydndkdFwiLFwiZTpydndsc3RcIixcInY6Y250eHJtXCIsXCJkOmNvc29wXCIsXCJ2OmRtbmRiZWNmZ1wiLFwidjpodGxydndjcnRuXCIsXCJkOmNvc2hnXCIsXCJ2Omh0bHNyY2ZnXCIsXCJ2Omh0bGJkY2hncnBpXCIsXCJjOmFmZnJ0bG10clwiLFwiZTpodGxiZXRlZHRcIixcImM6cHZkaW1wcnRjZmdcIixcImU6cGhnYXVcIixcInY6cnBkaXNwXCIsXCJ2Omh0bGF0dHJcIixcImU6YWZmbHRjbW1zcnVsZVwiLFwiYzpocnNcIixcImU6aHJzXCIsXCJlOnB2ZGltcHJ0ZXhlXCIsXCJ2Omh0bGR0XCIsXCJlOmludmNhY2lcIixcImU6aHRsZHRcIixcInY6Ymxua3RwbGN5XCIsXCJlOmNvc2hnXCIsXCJ2OmNudHJtbW9kXCIsXCJ2OmhsZGJrZ2NmZ1wiLFwiZDpodGxhdHRyXCIsXCJjOnFja2ZsdHJcIixcInY6cGdycHZjZmdcIixcInY6cGFodHJ0cmxcIixcInY6cWNrZW50cnlcIixcImQ6cWNrZW50cnlcIixcImM6cHJzcmNodGllclwiLFwiZDpwcnNyY2h0aWVyXCIsXCJ2OnByc3JjaHRpZXJibmZ0XCIsXCJkOmFmZnJ0bG10clwiLFwidjpodGxybmtnXCIsXCJlOnJtZHRtbmdtbnRsXCIsXCJlOmh0bGR0cGR0bXBcIixcImQ6cWNrdGFiXCIsXCJ2OmFmZmx0Y21tc3J1bGVcIixcImU6cnZ3Y3VyXCIsXCJjOmh0bGF0dHJcIixcImU6cHJicGdcIixcInY6aHRsY29udmhpc3RcIixcInY6cGhncnBtYXBcIixcInY6Y3BucnN0cmN0blwiLFwidjpodGxia2d0XCIsXCJkOnJ2d2R0XCIsXCJlOmNwbnJzdHJjdG5cIixcInY6cnZ3bHN0XCIsXCJlOmFmZmx0Y250bnRwZHRcIixcInY6aHRscGhvdG9cIixcImM6YmtnZmxleFwiLFwiZTpodGxtcmdcIixcImQ6cHZkaW1wcnRjZmdcIixcImU6aHRscGhvdG9cIixcInY6aHJzXCIsXCJkOmRtbmRiZWNmZ1wiLFwidjpwcmJwZ1wiLFwiZTphZmZydGxtdHJcIixcInY6Y29zaGdcIixcInY6aW52Y2FjaVwiLFwidjptb2RpbnZcIixcImU6cnZ3bW9kXCIsXCJjOnB2ZGltcHJ0ZXhlXCIsXCJ2OmFmZmx0Y250bnRwZHRcIixcImU6bG5kbWtcIixcImQ6aW52Y2FjaVwiLFwidjpodGxkdHBkdG1wXCIsXCJ2Omh0bHRycG1wXCIsXCJjOm1jcGducHJvXCIsXCJjOnFja3RhYlwiLFwiZTpjbnR4cm1cIixcImU6Y29zb3BcIixcImU6ZG1uZGJlY2ZnXCIsXCJ2OnB2ZGltcHJ0Y2ZnXCIsXCJlOnJwZGlzcFwiLFwiZTpodGxhdHRyXCIsXCJlOnJ2d3RnZ1wiLFwidjpwcnNyY2h0aWVyXCIsXCJlOmh0bHJua2dcIixcInY6cnZ3Y3VyXCIsXCJ2OmJrZ3JmZHJxc3RcIixcImQ6aHJzXCIsXCJlOmJsbmt0cGxjeVwiLFwiZDpwdmRpbXBydGV4ZVwiLFwidjppbnZsc1wiLFwiZTpodGxzcmNmZ1wiLFwiZTpwcnNyY2h0aWVyYm5mdFwiLFwidjptY3BnbnByb1wiLFwidjphZmZydGxtdHJcIixcInY6cHZkaW1wcnRleGVcIixcImQ6bWNwZ25wcm9cIixcInY6YWZmbHRwcmNcIixcImU6ZG1kYmVzdm1jZmdcIixcInY6ZG1kYmVzdm1jZmdcIixcImM6Y29zb3BcIixcImU6cWNrZW50cnlcIixcInY6cnZ3dGdnXCIsXCJkOmh0bHJua2dcIixcInY6cnZ3bW9kXCIsXCJ2OmNvc29wXCIsXCJlOm1jcGducHJvXCIsXCJjOnFja2VudHJ5XCIsXCJhOmxuZG1rXCIsXCJkOnJ2d3RnZ1wiLFwiZTpobGRia2djZmdcIixcImQ6cWNrZmx0clwiLFwiZTpodGx0cnBtcFwiLFwiYzpsbmRta1wiLFwidjpodGxwcGlja1wiLFwiYTpxY2tmbHRyXCIsXCJlOnFja3RhYlwiLFwiYzpodGxybmtnXCIsXCJjOnJ2d2R0XCIsXCJ2Omh0bGJldFwiLFwidjpjbnRybXBvbW9kXCIsXCJkOmNwbnJzdHJjdG5cIixcImU6cnZ3ZHRcIixcInY6c3BjbHBsY1wiLFwidjpodGxtcmdcIixcImU6cHJzcmNodGllclwiLFwiZTpxY2tmbHRyXCIsXCJ2OmJrZ3JmZGZlZVwiLFwidjpsbmRta1wiLFwiYzpkbW5kYmVjZmdcIl0iLCJhdF9oYXNoIjoiT0p2Q2QwRmxxV3NEY21FS2REZnVGUSIsImh0dHBzOlwvXC90dmxrXC9ncm91cHMiOiJbXCJTdG9yeSBQcm9kdWN0aW9uIEhvdXNlIC0gRnVsbCBBY2Nlc3NcIixcIkFjY29tIEVuZ2luZWVyXCIsXCJTbmFwc2hvdCBWaWRlbyBUb29sIC0gRnVsbCBBY2Nlc3NcIl0iLCJzdWIiOiJhMGIxZWU2ZS02ZTk2LTQ3YTgtYjJmMC1lY2I2YTY2MzhiZGEiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5hcC1zb3V0aGVhc3QtMS5hbWF6b25hd3MuY29tXC9hcC1zb3V0aGVhc3QtMV9OVHJZb2g5WnUiLCJjb2duaXRvOnVzZXJuYW1lIjoiOWI1NjZjNjMtZjQxNy00YjIwLTk1YWQtNmZhMTUxZGVlZjZiIiwiaHR0cHM6XC9cL3R2bGtcL2NvbXByZXNzaW9uLW1ldGhvZCI6Im5vbmUiLCJodHRwczpcL1wvdHZsa1wvdXNlci1tZXRhZGF0YSI6Int9Iiwibm9uY2UiOiJNMEkwTkdSSmEyWkphMmhYTWxCUVNXdHBURFE0ZEZocWREUlNWVGRsZDFsM2JISmxSMXBIY1ZkUlp3PT0iLCJvcmlnaW5fanRpIjoiOGU1Y2Q5MTMtMzNiYS00ZTRmLThhOGMtMTJjZWJkOGIxMzQ2IiwiYXVkIjoiNGNubTYyZ3ZrZ29zNTBwZzhqZHZjOWswaDYiLCJpZGVudGl0aWVzIjpbeyJ1c2VySWQiOiIxMDgyNTc2MTE4MzQ5ODcyNDk1NzYiLCJwcm92aWRlck5hbWUiOiJHb29nbGUiLCJwcm92aWRlclR5cGUiOiJHb29nbGUiLCJpc3N1ZXIiOm51bGwsInByaW1hcnkiOiJmYWxzZSIsImRhdGVDcmVhdGVkIjoiMTc1MjA0OTM1OTQ5NSJ9XSwidG9rZW5fdXNlIjoiaWQiLCJodHRwczpcL1wvdHZsa1wvc2lkIjoiM2MyM2JlODktMTVkNS00YjU4LWI5OGMtNTA0MzIwZDU0MmRjIiwiYXV0aF90aW1lIjoxNzU2MzY4NzM3LCJuYW1lIjoiQ2hyaXN0b3BoZXIgSHUiLCJodHRwczpcL1wvdHZsa1wvYXBwIjoiYWNkLWFjY29tLWRhc2hib2FyZCIsImV4cCI6MTc1NjM3MjMzNywiaWF0IjoxNzU2MzY4NzM3LCJqdGkiOiI5NzBiYmM3Yi05Mjk2LTRjNDktODg0YS0yNWM1ZGM5YWRiYTEiLCJlbWFpbCI6ImNocmlzdG9waGVyLmh1QHRyYXZlbG9rYS5jb20ifQ.t8035RkwsCoMIOOIP86fJb92SMJqmB8Z9jzoFQxmboskT2Y9IrnH9Zr3CKQgJ4RyEBsdcNihs8_XdIWyRHNEIenVAA1JoHV6c5_r-Ltlw3yu9sA8HfCjeftYnffKl3alHLWzchdqMgVX8uIAAJq3Kiq5buN7AIisrI1AZ56X_hE3e_vsArhD7MTzGp6ZLV1eBz3CA4_IcdWpwJwipgLWTG50JYQGQn3tHf166Y7bMRufxqfV5wbeh_3q-DUZUCwrVqynfrpWR4lErLcf1AYdJaRMcD-_C58dXB7jVSVBZQrBkddOuN0GikXCzay_HTTqEHPpnl5Y5qyxijqLvpzVFQ"
COOKIE_VALUE = "WZeAsLU/+p+1gbNHoadMBbIwuhbV6z51rHb0B/PhHOSDgx7ICI3vfCHSHg2Qu20j5JegFtxTYKwU218KCJ3541Un5LuKMyfaKrCJIL8Yz2NO0RPzfAnl85lzkC1kesB/2rAnT3UlsprBH8O8pxbytT3Rv9zT5zsNOfg+1Q1ej5FrONCgEBDHHk2jiuXPfY27ioCfAxKVWHdbmlcKO759n6mx2Pyftbyd3CDH3h88mC9MLvyYuSTYufwOIR7M9ysnVgldg5PBEzF9L92npeEimcSf+1g7CWK9999e~djAy"





def fetch_room_details(hotel_room_id):
    """
    Fetches room details from the external API using the provided hotel_room_id.
    
    Args:
        hotel_room_id (str): The ID of the hotel room to fetch.
        
    Returns:
        dict: A dictionary containing the fetched room data, or an empty dictionary if the request fails.
    """
    url = "https://acdtool-be.acd.traveloka.com/api/v2/hotel/content/room/function"
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": "https://accom-dashboard.acd.traveloka.com",
        "referer": "https://accom-dashboard.acd.traveloka.com/",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
        "Cookie": f"tvl={COOKIE_VALUE}"
    }
    payload = {
        "data": {
            "funcName": "getAccomRoomDetail",
            "param": {
                "hotelRoomId": hotel_room_id
            }
        },
        "context": {
            "auth0Token": AUTH0_TOKEN,
            "username": "edy.evan@traveloka.com"
        },
        "fields": [],
        "clientInterface": "desktop"
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        json_data = response.json()
        
        ret_val = json_data.get('data', {}).get('retVal', {})
        if ret_val:
            accom_room_data_wrapper = ret_val.get('accomRoomDataWrapper', {})
            if accom_room_data_wrapper:
                return accom_room_data_wrapper.get('accomRoom', {})
        return {}
        
    except requests.exceptions.HTTPError as e:
        print(f"API Error: Failed to fetch data for room ID {hotel_room_id}. The server returned a {e.response.status_code} error.", file=sys.stderr)
        return {}
    except requests.exceptions.RequestException as e:
        print(f"Network Error: An error occurred for room ID {hotel_room_id}: {e}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"An unexpected error occurred for room ID {hotel_room_id}: {e}", file=sys.stderr)
        return {}

def find_cheapest_room_by_name(room_list, room_name):
    """
    Finds the cheapest room in the list with a matching room_type.
    """
    cheapest_room = None
    min_price = float('inf')

    for room in room_list:
        if room.get('room_type') == room_name:
            try:
                price = float(room.get('agent_price'))
                if price < min_price:
                    min_price = price
                    cheapest_room = room
            except (ValueError, TypeError):
                continue
    return cheapest_room

def find_competitor_room_match(room_list, ninja_match):
    """
    Finds the matching competitor room details from the room_list based on the ninja_room_match data.
    """
    match_type = ninja_match.get('type')
    chosen_name = ninja_match.get('chosen_competitor_room_name')

    if match_type in ["MATCH_INVENTORY_RATIO", "MATCH_ROOM_RATIO"]:
        # Find the cheapest room with the chosen name
        return find_cheapest_room_by_name(room_list, chosen_name)
    else:
        # Fallback to previous logic for other match types
        for room in room_list:
            if room.get('room_size') != "0.0":
                return room
    
    return {} # Return an empty dict if no match is found

def transform_data(input_data, num_to_process='all'):
    """
    Transforms the raw data into the desired benchmark JSON format,
    and fetches missing TVL data from the external API.
    """
    output_data = []
    
    data_to_process = input_data if num_to_process == 'all' else input_data[:num_to_process]
    
    for entry in data_to_process:
        hotel_id = entry.get('hotel_id', 'N/A')
        hotel_name = "N/A"
        room_list = entry.get('room_list', [])

        for item in entry.get('chosen_inventory_adjustment', []):
            tvl_room_id = item.get('room_id') 
            
            tvl_data_from_api = {}
            if tvl_room_id:
                print(f"Fetching details for TVL Room ID: {tvl_room_id}")
                tvl_data_from_api = fetch_room_details(tvl_room_id)
            
            size_data = tvl_data_from_api.get('size') if tvl_data_from_api else None
            room_size_tvl = size_data.get('size') if isinstance(size_data, dict) else None
            
            room_group_name_tvl = tvl_data_from_api.get('name') or (tvl_data_from_api.get('localeInfoList', {}) or {}).get('id_ID', {}).get('name') if tvl_data_from_api else "N/A"
            bed_type_tvl = tvl_data_from_api.get('beds', {}).get('bedType') if tvl_data_from_api else None

            is_with_breakfast_tvl = str(item.get('is_with_breakfast')).lower() == 'true'
            is_refundable_tvl = str(item.get('is_refundable')).lower() == 'true'

            tvl_metrics = {
                "hard_metrics": {
                    "room_size": room_size_tvl
                },
                "soft_metrics": {
                    "room_group_name": room_group_name_tvl,
                    "bed_type": bed_type_tvl,
                    "max_occupancy": tvl_data_from_api.get('occupancyPolicy', {}).get('maxOccupancy') if tvl_data_from_api else None,
                    "amenities": {
                        "is_with_breakfast": is_with_breakfast_tvl,
                        "is_refundable": is_refundable_tvl,
                        "cancellation_policy_code": item.get('cancellation_policy_code', "")
                    },
                    "view": ""
                }
            }
            
            ninja_room_match = item.get('ninja_room_match', {})
            # 从 room_list 查找完整的竞争对手房间信息，使用新的匹配逻辑
            competitor_room_data = find_competitor_room_match(room_list, ninja_room_match)
            
            competitor_is_with_breakfast = str(competitor_room_data.get('with_breakfast')).lower() == 'true' if competitor_room_data else None
            competitor_is_refundable = str(competitor_room_data.get('refundable')).lower() == 'true' if competitor_room_data else None

            competitor_metrics = {
                "hard_metrics": {
                    "room_size": competitor_room_data.get('room_size') if competitor_room_data else None
                },
                "soft_metrics": {
                    "room_group_name": competitor_room_data.get('room_type') if competitor_room_data else None,
                    "bed_type": competitor_room_data.get('bed_type') if competitor_room_data else None,
                    "max_occupancy": competitor_room_data.get('max_occupancy') if competitor_room_data else None,
                    "amenities": {
                        "is_with_breakfast": competitor_is_with_breakfast,
                        "is_refundable": competitor_is_refundable,
                        "cancellation_policy_code": competitor_room_data.get('cancellation_policy_code', "") if competitor_room_data else ""
                    },
                    "view": ""
                }
            }
            
            match_status = "matched"
            room_size_check = item.get('room_size_accuracy_check')
            if room_size_check == "NOT_MATCH":
                match_status = "mismatched"
            elif room_size_check is None:
                tvl_size = tvl_metrics['hard_metrics']['room_size']
                competitor_size = competitor_metrics['hard_metrics']['room_size']
                if tvl_size is not None and competitor_size is not None:
                    try:
                        if float(tvl_size) != float(competitor_size):
                            match_status = "mismatched"
                    except (ValueError, TypeError):
                        # Handle cases where size is not a valid number
                        pass
            
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
            transformed_data = transform_data(data, num_to_process=2) 
            print(json.dumps(transformed_data, indent=2))
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.", file=sys.stderr)
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' is not a valid JSON.", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    process_file('./data/sample_20250827_batch_1.json')
