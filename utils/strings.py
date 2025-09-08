"""String constants and templates for Whispier Bot."""
class Strings:
    WELCOME = """🐒 *Monkey swings into chat*

🎉 **Hey there! I'm Whispier!**

🤫 I'm your personal secret-delivery monkey!
Drop private messages in any chat without the drama.

✨ **What I do:**
🎯 Send secrets to specific people only
💭 Works in any group, even if I'm not there
🔒 Only you and your target can see the message

Ready to swing into action? 🌳"""

    TUTORIAL = """🎓 **Secret Monkey 101** 🐒

📝 **Basic Format:**
`@whispierbot [your secret] @username`
or
`@whispierbot [your secret] user_id`

💡 **Examples:**
• `@whispierbot hey bestie! @sarah`
• `@whispierbot meeting moved to 3pm 945915658`
• `@whispierbot surprise party tonight! @alice`

🎯 **How it works:**
1. Type your message anywhere
2. Add target (@username or user id)
3. Select the whisper result
4. Only you and target can read it

Easy as eating bananas! 🍌"""

    HELP = """🆘 **Need Help, Fellow Monkey?**

🎯 **Commands:**
• `/start` - Main menu
• `/help` - This help page
• `/stats` - (WIP) Stats

💭 **Inline Usage:**
`@whispierbot secret @username`
`@whispierbot secret user_id`

🐒 **Notes:**
• You can use numeric user IDs
• Username resolved even if not in chat (with userbot enabled)
• Target can still open if not resolved yet (late binding)

🌳 **Try now!**"""

    INLINE_EMPTY = """🎯 **Ready to Drop a Secret?** 🐒
💭 Type your message + target (@username or user id)
📝 Example: `@whispierbot banana party! @friend`"""

    INLINE_NO_TARGET = """🎯 **Almost There, Monkey!** 🐒
🤔 Who should receive this secret?

📝 Add target: `{message} @username` or `{message} user_id`

💡 **Examples:**
`@whispierbot {message} @alice`
`@whispierbot {message} 945915658`"""

    WHISPER_CREATED = """🤫🐒 **Secret Banana Drop!**

💌 **For:** {target}
🔒 **Monkey-secured message**
👀 **Only you and target can peek**"""

    WHISPER_BUTTON = "🍌💭 Peek Secret"
    WHISPER_INFO_BUTTON = "👀🐒 Who's It For?"

    SECRET_REVEALED = """🍌 **BANANA REVEALED!** 🐒
💌 **From:** {sender}

{content}

🤫 Keep it between us monkeys!"""

    NOT_FOR_YOU = """🙈 **No Peeking, Curious Monkey!**

🐒 This banana isn't for you...
Create your own:
@whispierbot [secret] @target"""

    MESSAGE_NOT_FOUND = """🤷‍♂️ **Oops! Message Vanished!**

🐒 This secret swung away...
Make a fresh one! 🍌"""

    STATS = """🍌 **Your Monkey Stats** 🐒

📊 **Secret Activity:**
• Secrets sent: {sent_count}
• Secrets received: {received_count}
• Active whispers: {active_count}

🏆 **Monkey Level:**
{level_info}

Keep swinging those secrets! 🌳"""

    BTN_SEND_SECRET = "🤫💭 Send Secret"
    BTN_TUTORIAL = "🎓🐒 Quick Learn"
    BTN_HELP = "🆘🌳 Help Tree"
    BTN_STATS = "📊🍌 My Stats"
    BTN_HOME = "🏠🐒 Home Tree"
