# Discord Verification Bot

This is a Discord bot that provides verification functionality for your server. Users can verify themselves as human users by following a simple process. The bot supports slash commands and offers various configuration options.

Please note that this repository only contains the bot's source code and does not include the required API. You will need to implement the API yourself to handle the verification process and store the necessary data. The API should have endpoints for creating tokens, verifying tokens, and deleting tokens. Additionally, make sure to configure the base URL and authentication token in the code.

## Requirements
To run the bot, you need the following:

- Python 3.11 or higher
- Discord.py library (v2.2.2 or higher)

## Setup
1. Clone this repository to your local machine.
2. Create a virtual environment and activate it.
3. Install the required dependencies using the following command:
```pip install -r requirements.txt```
4. Implement the required API endpoints for token creation, verification, and deletion.
5. Configure the base URL and authentication token in the code (`base_url` and `auth_token` variables).
6. Customize the bot's behavior and configuration options in the code.
7. Run the bot using the following command:
```python bot.py```

## Usage
The bot supports the following commands:

- `?sync`: Sync all slash commands.
- `?init`: Create JSON data for a guild if it does not exist.
- `?howto`: Provides instructions on how to verify.
- `?setup`: Runs the setup process for channel permissions (admin-only).
- `/invite`: Get an invite link for the bot.

Additionally, the bot handles slash commands for verification (`/verify`) and configuration (`/config_verifiedrole`, `/config_staffrole`).

Please note that the API endpoints and configuration options must be properly set up for the bot to function correctly.

To invite the public version of the bot, use the following link: [Invite Link](https://discord.com/oauth2/authorize?client_id=1100503947992637561&permissions=532844899560&redirect_uri=https%3A%2F%2Fapi.jinxz.dev%2Fdiscord%2Fthanks&response_type=code&scope=identify%20bot%20applications.commands)


## API Implementation
Please implement the required API endpoints for token creation, verification, and deletion. The bot relies on these endpoints to handle the verification process. Ensure that the endpoints are properly secured and handle requests appropriately.

## License
This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

Note: This repository only contains the bot's source code. The required API implementation is not included, and you will have to create it yourself to enable the verification functionality.
