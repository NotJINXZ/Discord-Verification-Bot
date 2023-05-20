import pymongo
from config import mongo_connection_uri

# Set up the MongoDB connection
client = pymongo.MongoClient(mongo_connection_uri)
db = client["main"]
collection = db["servers"]

def get_data(server_id: str | int) -> dict:
    """
    Retrieve data for a specific server based on the server ID.

    Parameters:
    - server_id (str or int): The ID of the server.

    Returns:
    - dict: The data associated with the server.
    """
    server_id = str(server_id)
    data = collection.find_one({"server_id": server_id})
    return data or {}

def save_data(data: dict):
    """
    Save or update data for a specific server.

    Parameters:
    - data (dict): The data to be saved or updated.
    """
    collection.replace_one({"server_id": data["server_id"]}, data, upsert=True)

def create_or_update_entry(server_id: str | int, staff_role_id: str | int = "", verified_role_id: str | int = "", premium: bool = False, logging_webhook: str = "", status: bool = True):
    """
    Create or update an entry for a server with the provided data.

    Parameters:
    - server_id (str or int): The ID of the server.
    - staff_role_id (str or int): The ID of the staff role (optional).
    - verified_role_id (str or int): The ID of the verified role (optional).
    - premium (bool): The premium status of the server (optional, default: False).
    - logging_webhook (str): The logging webhook URL (optional).
    - status (bool): The status of the server (optional, default: True).
    """
    server_id = str(server_id)
    existing_data = get_data(server_id)
    existing_data["server_id"] = server_id
    existing_data["staff_role_id"] = staff_role_id
    existing_data["verified_role_id"] = verified_role_id
    existing_data["logging_webhook"] = logging_webhook
    existing_data["premium"] = premium
    existing_data["status"] = status
    save_data(existing_data)

def get_data_for_server(server_id: str | int) -> dict:
    """
    Retrieve data for a specific server based on the server ID.

    Parameters:
    - server_id (str or int): The ID of the server.

    Returns:
    - dict: The data associated with the server.
    """
    server_id = str(server_id)
    data = get_data(server_id)
    return data

def delete_entry(server_id: str | int):
    """
    Delete the entry for a specific server based on the server ID.

    Parameters:
    - server_id (str or int): The ID of the server.
    """
    server_id = str(server_id)
    collection.delete_one({"server_id": server_id})

def set_staff_role_id(server_id: str | int, staff_role_id: str | int):
    """
    Set the staff role ID for a specific server.

    Parameters:
    - server_id (str or int): The ID of the server.
    - staff_role_id (str or int): The ID of the staff role.
    """
    server_id = str(server_id)
    staff_role_id = str(staff_role_id)
    data = get_data(server_id)
    data["staff_role_id"] = staff_role_id
    save_data(data)

def set_verified_role_id(server_id: str | int, verified_role_id: str | int):
    """
    Set the verified role ID for a specific server.

    Parameters:
    - server_id (str or int): The ID of the server.
    - verified_role_id (str or int): The ID of the verified role.
    """
    server_id = str(server_id)
    verified_role_id = str(verified_role_id)
    data = get_data(server_id)
    data["verified_role_id"] = verified_role_id
    save_data(data)

def set_premium_status(server_id: str | int, premium_status: bool):
    """
    Set the premium status for a specific server.

    Parameters:
    - server_id (str or int): The ID of the server.
    - premium_status (bool): The premium status to be set.
    """
    server_id = str(server_id)
    data = get_data(server_id)
    data["premium"] = premium_status
    save_data(data)

def set_logging_webhook(server_id: str | int, logging_webhook: str):
    """
    Set the logging webhook for a specific server.

    Parameters:
    - server_id (str or int): The ID of the server.
    - logging_webhook (str): The logging webhook URL.
    """
    server_id = str(server_id)
    data = get_data(server_id)
    data["logging_webhook"] = logging_webhook
    save_data(data)

def set_status(server_id: str | int, status: bool):
    """
    Set the status for a specific server.

    Parameters:
    - server_id (str or int): The ID of the server.
    - status (bool): The status to be set.
    """
    server_id = str(server_id)
    data = get_data(server_id)
    data["status"] = status
    save_data(data)

def get_logging_webhook_value(server_id: str | int) -> str:
    """
    Retrieve the logging webhook value for a specific server.

    Parameters:
    - server_id (str or int): The ID of the server.

    Returns:
    - str: The logging webhook URL.
    """
    server_id = str(server_id)
    data = get_data(server_id)
    return data.get("logging_webhook")

def increment_total_verifications(server_id: str | int):
    """
    Increment the total verifications count for a specific server.

    Parameters:
    - server_id (str or int): The ID of the server.
    """
    server_id = str(server_id)
    filter_query = {"server_id": server_id}
    update_query = {"$inc": {"total_verifications": 1}}
    collection.update_one(filter_query, update_query, upsert=True)