---

# Google Gemini Discord Bot

Welcome to Mana Nagase, a versatile AI companion for Discord powered by Google's state-of-the-art Gemini models. This bot is open-source and designed for self-hosting, giving you maximum privacy, control, and a powerful toolkit for advanced roleplaying, image generation, and multi-modal analysis.

## Features

*   🤖 **Advanced AI Roleplaying**: Create custom characters with unique personalities using webhooks, or instantly import them from V2 Character Cards.
*   🎨 **Image Generation & Editing**: Use the `/edit_or_generate_image` command to create new images from a prompt or edit existing ones with AI assistance.
*   🖼️ **Multi-Modal Understanding**: The bot can analyze the content of images, extract audio from videos, and understand context from web links.
*   ⚙️ **Full User Control**: Bring your own API key, switch between different AI models on the fly, and manage your data with comprehensive reset and removal commands.

## Setup and Installation

Follow these steps to get a self-hosted version of the bot running on your own machine.

### 1. Get the Source Code

First, clone the repository from GitHub and navigate into the project folder.

```bash
git clone https://github.com/War004/Google-gemini-discord-bot.git
cd Google-gemini-discord-bot
```

### 2. Configure API Keys

You will find a file named `.env`. Open it in a text editor and add your unique keys.

**Important**: Do not use single or double quotes (`'` or `"`) around your keys.

```env
# .env file content

# Required: Your API key from Google AI Studio
GOOGLE_API_KEY=your_google_api_key_goes_here

# Required: Your bot token from the Discord Developer Portal
DISCORD_TOKEN=your_discord_bot_token_goes_here

# Optional: The bot can get this automatically, but adding it can prevent issues.
APPLICATION_ID=your_application_id_goes_here
```

### 3. Create and Activate a Virtual Environment

Create a dedicated virtual environment to keep dependencies isolated.

```bash
# Create the environment
python -m venv venv
```

Then, activate the environment. The command differs based on your operating system:

```bash
# On Windows
.\venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 4. Install Dependencies

With your virtual environment active, install all the required packages. Choose the requirements file that matches your OS.

```bash
# If you are on Windows
pip install -r requirmentsWindows.txt

# If you are on Linux/macOS
pip install -r requirmentsLinux.txt
```

### 5. Run the Bot

Everything is now set up! Start the bot with the final command:

```bash
python public_version.py
```

Congratulations! Your self-hosted bot should now be online and connected to Discord.

### 6. Initial Bot Configuration (In Discord)

Once the bot is in your server, you must perform one final step in the channel where you want to use it:

*   **Set Your API Key**: The bot cannot function without knowing which key to use. Run the following command in your channel:
    ```
    /set_api_key
    ```
    You will be prompted to enter the same Google API key you put in your `.env` file. This is stored securely on a per-channel basis.

Your bot is now ready to use! You can start by chatting with it or exploring other commands like `/add_webhook` or `/edit_or_generate_image`.
