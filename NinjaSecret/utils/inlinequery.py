from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent

# Ninja-related inline query results (legacy fallback)
# Main secret functionality is handled by the dedicated whisper plugin

answer = []

answer.extend(
    [
        InlineQueryResultArticle(
            title="🥷 Ninja Secret Tutorial",
            description="Learn how to use Ninja Secret for secret messaging",
            input_message_content=InputTextMessageContent(
                "🥷 **Ninja Secret Tutorial**\n\n"
                "🎯 **How to Send Secrets:**\n"
                "Type `@ninjasecretbot` in any chat, then:\n\n"
                "📝 **Basic Format:**\n"
                "`@ninjasecretbot [your message] [targets]`\n\n"
                "🌙 **Examples:**\n"
                "• Single person: `@ninjasecretbot secret message @alice`\n"
                "• Multiple people: `@ninjasecretbot group news @bob,@charlie`\n"
                "• Everyone: `@ninjasecretbot pizza time! @all`\n\n"
                "🔥 **Special Features:**\n"
                "• `!delete` - Burns after all read\n"
                "• `!timer:3600` - Expires in 1 hour\n"
                "• `!vip` - VIP styling with crown\n"
                "• `!cute` - Extra stealthy ninja styling\n\n"
                "⭐ **Ready to strike in stealth?**"
            ),
        ),
        InlineQueryResultArticle(
            title="🤫 Create Secret Message",
            description="Start creating a secret message",
            input_message_content=InputTextMessageContent(
                "🤫 **Ready to Send a Secret?**\n\n"
                "🥷 Use the format: `@ninjasecretbot [message] [targets]`\n\n"
                "📝 **Example:**\n"
                "`@ninjasecretbot pizza party tonight! @alice,@bob`\n\n"
                "💡 **Pro Tips:**\n"
                "• Use `@all` to message everyone\n"
                "• Add `!delete` to burn after reading\n"
                "• Add `!timer:3600` to expire in 1 hour\n\n"
                "⭐ **Start typing your secret above!**"
            ),
        ),
    ]
)
