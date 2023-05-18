import json

def get_data():
    with open("data.json", "r") as json_file:
        return json.load(json_file)

def save_data(data):
    with open("data.json", "w") as json_file:
        json.dump(data, json_file)

def create_or_update_entry(server_id, staff_role_id="", verified_role_id="", premium=False, logging_webhook=""):
    # Load existing data from the JSON file
    with open("data.json", "r") as json_file:
        existing_data = json.load(json_file)

    # Update or create a new entry for the server
    existing_data[server_id] = {
        "staff_role_id": staff_role_id,
        "verified_role_id": verified_role_id,
        "premium": premium,
        "logging_webhook": logging_webhook
    }

    # Write the updated data back to the JSON file
    with open("data.json", "w") as json_file:
        json.dump(existing_data, json_file)


def get_data_for_server(server_id):
    # Load existing data from the JSON file
    with open("data.json", "r") as json_file:
        existing_data = json.load(json_file)

    # Retrieve the data for the specified server ID
    server_data = existing_data.get(server_id, None)
    return server_data

def delete_entry(server_id):
    # Load existing data from the JSON file
    with open("data.json", "r") as json_file:
        existing_data = json.load(json_file)

    # Check if the server_id exists in the data
    if server_id in existing_data:
        # Delete the entry for the specified server_id
        del existing_data[server_id]

        # Write the updated data back to the JSON file
        with open("data.json", "w") as json_file:
            json.dump(existing_data, json_file)
        print(f"Entry for server '{server_id}' deleted successfully.")
    else:
        print(f"No entry found for server '{server_id}'.")

def set_staff_role_id(server_id, staff_role_id):
    data = get_data()
    data[server_id]["staff_role_id"] = staff_role_id
    save_data(data)

def set_verified_role_id(server_id, verified_role_id):
    data = get_data()
    data[server_id]["verified_role_id"] = verified_role_id
    save_data(data)

def set_premium_status(server_id, premium_status):
    data = get_data()
    data[server_id]["premium"] = premium_status
    save_data(data)

def set_logging_webhook(server_id, logging_webhook):
    data = get_data()
    data[server_id]["logging_webhook"] = logging_webhook
    save_data(data)

def get_logging_webhook_value(server_id):
    with open("data.json", "r") as file:
        json_data = json.load(file)

    if json_data is None:
        return None

    server_data = json_data.get(server_id)
    if server_data is None:
        return None

    logging_webhook_value = server_data.get("logging_webhook")
    return logging_webhook_value