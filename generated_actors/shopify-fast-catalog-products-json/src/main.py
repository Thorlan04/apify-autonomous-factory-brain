import os
import json
import sys
import requests
import time
from datetime import datetime

# --- Configuration & Constants ---
DEFAULT_INPUT = {
    "storeUrl": "https://colourpop.com",
    "maxPages": 2,
    "limitPerPage": 50
}
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36 ApifyBot/1.0"
APIFY_LOCAL_STORAGE_DIR = "./storage"
APIFY_LOCAL_DATASET_DIR = f"{APIFY_LOCAL_STORAGE_DIR}/datasets/default"
APIFY_LOCAL_KEY_VALUE_STORE_DIR = f"{APIFY_LOCAL_STORAGE_DIR}/key_value_stores/default"

# --- Utility Functions ---

def get_input():
    """
    Attempts to load input from APOFY_INPUT_VALUE env var,
    then from Apify Cloud Key-Value Store,
    then from ./storage/key_value_stores/default/INPUT.json,
    and finally falls back to DEFAULT_INPUT.
    """
    input_data = None

    # 1. Try from environment variable
    apify_input_value = os.getenv("APIFY_INPUT_VALUE")
    if apify_input_value:
        try:
            input_data = json.loads(apify_input_value)
            print(f"[{datetime.now().isoformat()}] INFO: Input loaded from APIFY_INPUT_VALUE environment variable.")
        except json.JSONDecodeError as e:
            print(f"[{datetime.now().isoformat()}] ERROR: Could not parse APIFY_INPUT_VALUE as JSON: {e}")

    # 1b. Try from Apify Cloud Key-Value Store API
    kvs_id = os.getenv("APIFY_DEFAULT_KEY_VALUE_STORE_ID")
    if input_data is None and kvs_id:
        try:
            token = os.getenv("APIFY_TOKEN")
            url = f"https://api.apify.com/v2/key-value-stores/{kvs_id}/records/INPUT"
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200 and res.content:
                input_data = res.json()
                print(f"[{datetime.now().isoformat()}] INFO: Input loaded from Apify Cloud Key-Value Store.")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] WARNING: Could not fetch input from KVS API: {e}")

    # 2. Try from local INPUT.json file if not already loaded
    if input_data is None:
        local_input_path = os.path.join(APIFY_LOCAL_KEY_VALUE_STORE_DIR, "INPUT.json")
        if os.path.exists(local_input_path):
            try:
                with open(local_input_path, "r", encoding="utf-8") as f:
                    input_data = json.load(f)
                print(f"[{datetime.now().isoformat()}] INFO: Input loaded from local file: {local_input_path}.")
            except (IOError, json.JSONDecodeError) as e:
                print(f"[{datetime.now().isoformat()}] ERROR: Could not load or parse local INPUT.json: {e}")

    # 3. Fallback to default input
    if input_data is None:
        input_data = DEFAULT_INPUT
        print(f"[{datetime.now().isoformat()}] INFO: Using default input as no other input was found.")

    # Ensure required fields are present, use defaults if missing from loaded input
    for key, default_value in DEFAULT_INPUT.items():
        if key not in input_data:
            input_data[key] = default_value
            print(f"[{datetime.now().isoformat()}] WARNING: Input missing '{key}', using default value: {default_value}")
    
    # Basic validation for storeUrl
    if not input_data.get("storeUrl", "").startswith("http"):
        print(f"[{datetime.now().isoformat()}] ERROR: Invalid 'storeUrl' in input: {input_data.get('storeUrl')}. Must start with http(s). Using default.")
        input_data["storeUrl"] = DEFAULT_INPUT["storeUrl"]

    return input_data

def save_output_item(item, item_index, remote_dataset_id=None, apify_token=None):
    """
    Saves an item to the local dataset and optionally to the remote Apify dataset.
    Returns True on success, False on failure.
    """
    saved_successfully = False

    # 1. Save to local dataset
    os.makedirs(APIFY_LOCAL_DATASET_DIR, exist_ok=True)
    local_file_path = os.path.join(APIFY_LOCAL_DATASET_DIR, f"{item_index:09d}.json")
    try:
        with open(local_file_path, "w", encoding="utf-8") as f:
            json.dump(item, f, ensure_ascii=False, indent=2)
        # print(f"[{datetime.now().isoformat()}] INFO: Item {item_index} saved locally to {local_file_path}")
        saved_successfully = True
    except IOError as e:
        print(f"[{datetime.now().isoformat()}] ERROR: Failed to save item {item_index} locally: {e}")
        saved_successfully = False # Explicitly reset in case previous was true

    # 2. Save to remote Apify dataset if credentials are provided
    if apify_token and remote_dataset_id:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {apify_token}"
        }
        api_url = f"https://api.apify.com/v2/datasets/{remote_dataset_id}/items"
        try:
            response = requests.post(api_url, headers=headers, json=[item], timeout=30)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            # print(f"[{datetime.now().isoformat()}] INFO: Item {item_index} saved remotely to Apify dataset.")
            saved_successfully = True # Remote success implies item was saved somewhere
        except requests.exceptions.RequestException as e:
            print(f"[{datetime.now().isoformat()}] ERROR: Failed to save item {item_index} to remote Apify dataset: {e}")
            # If local save was successful, we still consider the item "saved"
            # However, if local also failed, then this is still a total failure.
            # We prioritize local success for the `saved_successfully` flag.
            pass # Keep previous value of saved_successfully from local save attempt

    return saved_successfully

# --- Main Actor Logic ---

def main():
    """
    Main function for the Apify Actor.
    """
    print(f"[{datetime.now().isoformat()}] INFO: Actor started.")

    # Get input
    actor_input = get_input()
    store_url = actor_input["storeUrl"].rstrip('/') # Remove trailing slash for consistent URL building
    max_pages = actor_input["maxPages"]
    limit_per_page = actor_input["limitPerPage"]

    print(f"[{datetime.now().isoformat()}] INFO: Scrape parameters: Store='{store_url}', Max Pages={max_pages}, Limit Per Page={limit_per_page}")

    # Apify environment variables for remote saving
    apify_token = os.getenv("APIFY_TOKEN")
    remote_dataset_id = os.getenv("APIFY_DEFAULT_DATASET_ID")

    if apify_token and remote_dataset_id:
        print(f"[{datetime.now().isoformat()}] INFO: Remote Apify dataset detected. Items will be saved to '{remote_dataset_id}'.")
    else:
        print(f"[{datetime.now().isoformat()}] INFO: Remote Apify dataset not configured. Items will only be saved locally.")

    items_processed_count = 0
    page_number = 1
    
    while page_number <= max_pages:
        request_url = f"{store_url}/products.json?limit={limit_per_page}&page={page_number}"
        print(f"[{datetime.now().isoformat()}] INFO: Scraping page {page_number}/{max_pages} from: {request_url}")

        try:
            response = requests.get(
                request_url,
                headers={"User-Agent": DEFAULT_USER_AGENT},
                timeout=30 # Set a timeout for the request
            )
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            data = response.json()
            products = data.get("products", [])

            if not products:
                print(f"[{datetime.now().isoformat()}] INFO: No more products found on page {page_number}. Stopping.")
                break # No more products, stop pagination

            for product in products:
                # Add a timestamp to each product
                product["scrapedAt"] = datetime.now().isoformat()
                if save_output_item(product, items_processed_count + 1, remote_dataset_id, apify_token):
                    items_processed_count += 1
                else:
                    print(f"[{datetime.now().isoformat()}] WARNING: Could not save product data for item {items_processed_count + 1}. Continuing.")

        except requests.exceptions.HTTPError as e:
            error_message = f"HTTP Error {e.response.status_code} for {request_url}: {e.response.text}"
            print(f"[{datetime.now().isoformat()}] ERROR: {error_message}")
            error_record = {
                "error": error_message,
                "url": request_url,
                "scrapedAt": datetime.now().isoformat(),
                "status_code": e.response.status_code,
                "response_body_sample": e.response.text[:500] # Save a sample of the body
            }
            if save_output_item(error_record, items_processed_count + 1, remote_dataset_id, apify_token):
                items_processed_count += 1
            else:
                print(f"[{datetime.now().isoformat()}] CRITICAL: Failed to save error record for {request_url}.")

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            error_message = f"Network or Timeout Error for {request_url}: {e}"
            print(f"[{datetime.now().isoformat()}] ERROR: {error_message}")
            error_record = {
                "error": error_message,
                "url": request_url,
                "scrapedAt": datetime.now().isoformat()
            }
            if save_output_item(error_record, items_processed_count + 1, remote_dataset_id, apify_token):
                items_processed_count += 1
            else:
                print(f"[{datetime.now().isoformat()}] CRITICAL: Failed to save error record for {request_url}.")

        except json.JSONDecodeError as e:
            error_message = f"JSON Decoding Error for {request_url}: {e}. Response body might not be valid JSON."
            print(f"[{datetime.now().isoformat()}] ERROR: {error_message}")
            error_record = {
                "error": error_message,
                "url": request_url,
                "scrapedAt": datetime.now().isoformat(),
                "response_body_sample": response.text[:500] if 'response' in locals() and hasattr(response, 'text') else 'N/A'
            }
            if save_output_item(error_record, items_processed_count + 1, remote_dataset_id, apify_token):
                items_processed_count += 1
            else:
                print(f"[{datetime.now().isoformat()}] CRITICAL: Failed to save error record for {request_url}.")

        except Exception as e:
            error_message = f"An unexpected error occurred for {request_url}: {e}"
            print(f"[{datetime.now().isoformat()}] CRITICAL: {error_message}")
            error_record = {
                "error": error_message,
                "url": request_url,
                "scrapedAt": datetime.now().isoformat()
            }
            if save_output_item(error_record, items_processed_count + 1, remote_dataset_id, apify_token):
                items_processed_count += 1
            else:
                print(f"[{datetime.now().isoformat()}] CRITICAL: Failed to save error record for {request_url}.")

        page_number += 1
        # Optional: Add a small delay to be polite to the server
        # time.sleep(0.5)

    print(f"[{datetime.now().isoformat()}] INFO: Scraping finished. Total items saved: {items_processed_count}")

    # Log the final count in JSON format for Apify platform
    log_output = {
        "APIFY_DATASET_COUNT": items_processed_count
    }
    sys.stdout.write(json.dumps(log_output) + "\n")
    sys.stdout.flush()

    print(f"[{datetime.now().isoformat()}] INFO: Actor finished.")


if __name__ == "__main__":
    main()