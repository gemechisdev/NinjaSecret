from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent

# Whisper-related inline query results (legacy fallback)
# Main whisper functionality is handled by the dedicated whisper plugin

answer = []

answer.extend(
    [
        InlineQueryResultArticle(
            title="🐒 WhispierBot Tutorial",
            description="Learn how to use WhispierBot for secret messaging",
            thumb_url="https://i.imgur.com/monkey-whisper.gif",
            input_message_content=InputTextMessageContent(
                "🐒 **WhispierBot Tutorial**\n\n"
                "🎯 **How to Send Secrets:**\n"
                "Type `@whispierbot` in any chat, then:\n\n"
                "📝 **Basic Format:**\n"
                "`@whispierbot [your message] [targets]`\n\n"
                "🎪 **Examples:**\n"
                "• Single person: `@whispierbot secret message @alice`\n"
                "• Multiple people: `@whispierbot group news @bob,@charlie`\n"
                "• Everyone: `@whispierbot pizza time! @all`\n\n"
                "🔥 **Special Features:**\n"
                "• `!delete` - Burns after all read\n"
                "• `!timer:3600` - Expires in 1 hour\n"
                "• `!vip` - VIP styling with crown\n"
                "• `!cute` - Extra cute monkey styling\n\n"
                "🍌 **Ready to swing into action?**"
            ),
        ),
        InlineQueryResultArticle(
            title="🤫 Create Secret Message",
            description="Start creating a whisper message",
            thumb_url="https://i.imgur.com/monkey-whisper.gif",
            input_message_content=InputTextMessageContent(
                "🤫 **Ready to Send a Secret?**\n\n"
                "🐒 Use the format: `@whispierbot [message] [targets]`\n\n"
                "📝 **Example:**\n"
                "`@whispierbot pizza party tonight! @alice,@bob`\n\n"
                "💡 **Pro Tips:**\n"
                "• Use `@all` to message everyone\n"
                "• Add `!delete` to burn after reading\n"
                "• Add `!timer:3600` to expire in 1 hour\n\n"
                "🍌 **Start typing your secret above!**"
            ),
        ),
    ]
)
