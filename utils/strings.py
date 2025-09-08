"""String constants and templates for Whispier Bot."""


class Strings:
    """Bot string constants."""
    
    # Welcome messages
    WELCOME = """🐒 *Monkey swings into chat*

🎉 **Hey there! I'm Whispier!** 

🤫 I'm your personal secret-delivery monkey!
Drop private messages in any chat without the drama.

✨ **What I do:**
🎯 Send secrets to specific people only
💭 Works in any group, even if I'm not there
🔒 Only you and your target can see the message

Ready to swing into action? 🌳"""

    # Tutorial
    TUTORIAL = """🎓 **Secret Monkey 101** 🐒

📝 **Basic Format:**
`@whispierbot [your secret] @username`

💡 **Examples:**
• `@whispierbot hey bestie! @sarah`
• `@whispierbot meeting moved to 3pm @teammate`
• `@whispierbot surprise party tonight! @alice`

🎯 **How it works:**
1. Type your message anywhere
2. Add target username at the end
3. Select the whisper result
4. Only you and target can read it!

Easy as eating bananas! 🍌"""

    HELP = """🆘 **Need Help, Fellow Monkey?** 

🎯 **Quick Commands:**
• `/start` - Return to main menu
• `/help` - Show this help menu
• `/stats` - View your whisper statistics

💭 **Inline Usage:**
Type `@whispierbot` in any chat and follow the prompts!

🐒 **Tips:**
• Target must have started the bot
• Messages work in groups and private chats
• Only sender and target can view secrets

🌳 **Still confused?** Try the tutorial!"""

    # Inline responses
    INLINE_EMPTY = """🎯 **Ready to Drop a Secret?** 🐒
💭 Type your message + target username
📝 Example: `@whispierbot banana party! @friend`

🍌 **Pro Tips:**
• Use @username for targeting
• Works in any chat or group
• Only you and target can see it"""

    INLINE_NO_TARGET = """🎯 **Almost There, Monkey!** 🐒
🤔 Who should receive this secret?

📝 **Add target:** `{message} @username`

💡 **Example:**
`@whispierbot {message} @alice`"""

    # Message displays
    WHISPER_CREATED = """🤫🐒 **Secret Banana Drop!**

💌 **For:** {target}
🔒 **Monkey-secured message**
👀 **Only you and {target} can peek**"""

    WHISPER_BUTTON = "🍌💭 Peek Secret"
    WHISPER_INFO_BUTTON = "👀🐒 Who's It For?"

    # Callback responses
    SECRET_REVEALED = """🍌 **BANANA REVEALED!** 🐒
💌 **From:** {sender}

{content}

🤫 Keep it between us monkeys!"""

    NOT_FOR_YOU = """🙈 **No Peeking, Curious Monkey!**

🐒 This banana isn't for you...
But you can drop your own secrets!

💭 Type: @whispierbot [secret] @target"""

    MESSAGE_NOT_FOUND = """🤷‍♂️ **Oops! Message Vanished!**

🐒 This secret has swung away...
Maybe it expired or was already consumed?

Try creating a fresh one! 🍌"""

    # Stats
    STATS = """🍌 **Your Monkey Stats** 🐒

📊 **Secret Activity:**
• Secrets sent: {sent_count}
• Secrets received: {received_count}
• Active whispers: {active_count}

🏆 **Monkey Level:**
{level_info}

Keep swinging those secrets! 🌳"""

    # Buttons
    BTN_SEND_SECRET = "🤫💭 Send Secret"
    BTN_TUTORIAL = "🎓🐒 Quick Learn"
    BTN_HELP = "🆘🌳 Help Tree"
    BTN_STATS = "📊🍌 My Stats"
    BTN_HOME = "🏠🐒 Home Tree"