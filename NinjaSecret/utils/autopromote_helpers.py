def get_bot_permissions_text(bot_priv):
    """Helper function to get human-readable permission text from bot privileges"""
    permissions = []
    if getattr(bot_priv, "can_promote_members", False):
        permissions.append("Promote")
    if getattr(bot_priv, "can_restrict_members", False):
        permissions.append("Restrict/Ban")
    if getattr(bot_priv, "can_delete_messages", False):
        permissions.append("Delete")
    if getattr(bot_priv, "can_pin_messages", False):
        permissions.append("Pin")
    if getattr(bot_priv, "can_manage_chat", False):
        permissions.append("Manage Chat")
    if getattr(bot_priv, "can_change_info", False):
        permissions.append("Change Info")
    if getattr(bot_priv, "can_invite_users", False):
        permissions.append("Invite")
    if getattr(bot_priv, "can_manage_video_chats", False):
        permissions.append("Manage VC")
    if getattr(bot_priv, "can_post_stories", False):
        permissions.append("Post Stories")
    if getattr(bot_priv, "can_edit_stories", False):
        permissions.append("Edit Stories")
    if getattr(bot_priv, "can_delete_stories", False):
        permissions.append("Delete Stories")

    return ", ".join(permissions) if permissions else "Basic Admin"


def get_bot_privileges(bot_priv):
    """Helper function to get ChatPrivileges object based on bot's permissions"""
    from pyrogram.types import ChatPrivileges
    return ChatPrivileges(
        can_manage_chat=bool(getattr(bot_priv, "can_manage_chat", False)),
        can_delete_messages=bool(getattr(bot_priv, "can_delete_messages", False)),
        can_manage_video_chats=bool(getattr(bot_priv, "can_manage_video_chats", False)),
        can_restrict_members=bool(getattr(bot_priv, "can_restrict_members", False)),
        can_promote_members=bool(getattr(bot_priv, "can_promote_members", False)),
        can_change_info=bool(getattr(bot_priv, "can_change_info", False)),
        can_invite_users=bool(getattr(bot_priv, "can_invite_users", False)),
        can_pin_messages=bool(getattr(bot_priv, "can_pin_messages", False)),
        can_post_stories=bool(getattr(bot_priv, "can_post_stories", False)),
        can_edit_stories=bool(getattr(bot_priv, "can_edit_stories", False)),
        can_delete_stories=bool(getattr(bot_priv, "can_delete_stories", False)),
        is_anonymous=False,
    )
