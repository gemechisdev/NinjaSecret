"""String constants and templates for Whispier Bot."""
class Strings:
    WELCOME = """🐒 <i>Monkey swings into chat</i>

🎉 <b>Hey there! I'm Whispier!</b>

🤫 I'm your personal secret-delivery monkey!
Drop private messages in any chat without the drama.

✨ <b>What I do:</b>
🎯 Send secrets to specific people only
💭 Works in any group, even if I'm not there
🔒 Only you and your target can see the message

Ready to swing into action? 🌳"""

    TUTORIAL = """🎓 <b>Secret Monkey 101</b> 🐒

📝 <b>Basic Format:</b>
<code>@whispierbot [your secret] @username</code>
or
<code>@whispierbot [your secret] user_id</code>

💡 <b>Examples:</b>
• <code>@whispierbot hey bestie! @sarah</code>
• <code>@whispierbot meeting moved to 3pm 945915658</code>
• <code>@whispierbot surprise party tonight! @alice</code>

🎯 <b>How it works:</b>
1. Type your message anywhere
2. Add target (@username or user id)
3. Select the whisper result
4. Only you and target can read it

Easy as eating bananas! 🍌"""

    HELP = """🆘 <b>Need Help, Fellow Monkey?</b>

🎯 <b>Commands:</b>
• <code>/start</code> - Main menu
• <code>/help</code> - This help page
• <code>/stats</code> - (WIP) Stats

💭 <b>Inline Usage:</b>
<code>@whispierbot secret @username</code>
<code>@whispierbot secret user_id</code>

🐒 <b>Notes:</b>
• You can use numeric user IDs
• Username resolved even if not in chat (with userbot enabled)
• Target can still open if not resolved yet (late binding)

🌳 <b>Try now!</b>"""

    INLINE_EMPTY = """🎯 <b>Ready to Drop a Secret?</b> 🐒
💭 Type your message + target (@username or user id)
📝 Example: <code>@whispierbot banana party! @friend</code>"""

    INLINE_NO_TARGET = """🎯 <b>Almost There, Monkey!</b> 🐒
🤔 Who should receive this secret?

📝 Add target: <code>{message} @username</code> or <code>{message} user_id</code>

💡 <b>Examples:</b>
<code>@whispierbot {message} @alice</code>
<code>@whispierbot {message} 945915658</code>"""

    WHISPER_CREATED = """🤫🐒 <b>Secret Banana Drop!</b>

💌 <b>For:</b> {target}
🔒 <b>Monkey-secured message</b>
👀 <b>Only you and target can peek</b>"""

    WHISPER_BUTTON = "🍌💭 Peek Secret"
    WHISPER_INFO_BUTTON = "👀🐒 Who's It For?"

    SECRET_REVEALED = """🍌 <b>BANANA REVEALED!</b> 🐒
💌 <b>From:</b> {sender}

{content}

🤫 Keep it between us monkeys!"""

    NOT_FOR_YOU = """🙈 <b>No Peeking, Curious Monkey!</b>

🐒 This banana isn't for you...
Create your own:
<code>@whispierbot [secret] @target</code>"""

    MESSAGE_NOT_FOUND = """🤷‍♂️ <b>Oops! Message Vanished!</b>

🐒 This secret swung away...
Make a fresh one! 🍌"""

    STATS = """🍌 <b>Your Monkey Stats</b> 🐒

📊 <b>Secret Activity:</b>
• Secrets sent: {sent_count}
• Secrets received: {received_count}
• Active whispers: {active_count}

🏆 <b>Monkey Level:</b>
{level_info}

Keep swinging those secrets! 🌳"""

    BTN_SEND_SECRET = "🤫💭 Send Secret"
    BTN_TUTORIAL = "🎓🐒 Quick Learn"
    BTN_HELP = "🆘🌳 Help Tree"
    BTN_STATS = "📊🍌 My Stats"
    BTN_HOME = "🏠🐒 Home Tree"
