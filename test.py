from databaseutil import *
server_id = input("Enter a server id to get json data for: ")

server_data = get_data_for_server(server_id)
print(server_data)