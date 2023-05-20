import pymongo
from config import mongo_connection_uri

# Set up the MongoDB connection
client = pymongo.MongoClient(mongo_connection_uri)
db = client["main"]
collection = db["servers"]

def get_data(server_id):
    data = collection.find_one({"server_id": server_id})
    return data or {}

def save_data(data):
    collection.replace_one({"server_id": data["server_id"]}, data, upsert=True)

def create_or_update_entry(server_id, staff_role_id="", verified_role_id="", premium=False, logging_webhook="", status=True):
    existing_data = get_data(server_id)
    existing_data["server_id"] = server_id
    existing_data["staff_role_id"] = staff_role_id
    existing_data["verified_role_id"] = verified_role_id
    existing_data["logging_webhook"] = logging_webhook
    existing_data["premium"] = premium
    existing_data["status"] = status
    save_data(existing_data)

def get_data_for_server(server_id):
    data = get_data(server_id)
    return data

def delete_entry(server_id):
    collection.delete_one({"server_id": server_id})

def set_staff_role_id(server_id, staff_role_id):
    data = get_data(server_id)
    data["staff_role_id"] = staff_role_id
    save_data(data)

def set_verified_role_id(server_id, verified_role_id):
    data = get_data(server_id)
    data["verified_role_id"] = verified_role_id
    save_data(data)

def set_premium_status(server_id, premium_status):
    data = get_data(server_id)
    data["premium"] = premium_status
    save_data(data)

def set_logging_webhook(server_id, logging_webhook):
    data = get_data(server_id)
    data["logging_webhook"] = logging_webhook
    save_data(data)

def set_status(server_id, status):
    data = get_data(server_id)
    data["status"] = status
    save_data(data)

def get_logging_webhook_value(server_id):
    data = get_data(server_id)
    return data.get("logging_webhook")

def increment_total_verifications(server_id):
    filter_query = {"server_id": server_id}
    update_query = {"$inc": {"total_verifications": 1}}

    # Update the document, creating "total_verifications" field if it doesn't exist
    collection.update_one(filter_query, update_query, upsert=True)