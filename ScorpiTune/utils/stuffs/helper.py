# helper for strings

class Helper(object):
    HELP_M = '''ᴄʜᴏᴏsᴇ ᴛʜᴇ ᴄᴀᴛᴇɢᴏʀʏ ғᴏʀ ᴡʜɪᴄʜ ʏᴏᴜ ᴡᴀɴɴᴀ ɢᴇᴛ ʜᴇʟᴩ.
ᴀsᴋ ʏᴏᴜʀ ᴅᴏᴜʙᴛs ᴀᴛ sᴜᴘᴘᴏʀᴛ ᴄʜᴀᴛ

ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs ᴄᴀɴ ʙᴇ ᴜsᴇᴅ ᴡɪᴛʜ : /'''
    
    HELP_Info = '''Iɴꜰᴏ

Iɴꜰᴏ ᴄᴏᴍᴍᴀɴᴅꜱ:

/id : ɢᴇᴛ ᴛʜᴇ ᴄᴜʀʀᴇɴᴛ ɢʀᴏᴜᴘ ɪᴅ. ɪғ ᴜsᴇᴅ ʙʏ ʀᴇᴘʟʏɪɴɢ ᴛᴏ ᴀ ᴍᴇssᴀɢᴇ, ɢᴇᴛs ᴛʜᴀᴛ ᴜsᴇʀ's ɪᴅ.
/info : ɢᴇᴛ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ᴀʙᴏᴜᴛ ᴀ ᴜsᴇʀ.
'''

    HELP_GroupManagement = '''Gʀᴏᴜᴘ Mᴀɴᴀɢᴇᴍᴇɴᴛ

Gʀᴏᴜᴘ Mᴀɴᴀɢᴇᴍᴇɴᴛ ᴄᴏᴍᴍᴀɴᴅs (Admins only):

» ᴄʜᴀᴛ ᴄᴏɴᴛʀᴏʟ ᴄᴏᴍᴍᴀɴᴅs:

❍ /forward [enable/disable/allow/block]: ᴄᴏɴᴛʀᴏʟ ғᴏʀᴡᴀʀᴅɪɴɢ
❍ /links [enable/disable/allow/block]: ᴄᴏɴᴛʀᴏʟ ʟɪɴᴋs
❍ /slowmode [enable/disable] [seconds]: ᴄᴏɴᴛʀᴏʟ sʟᴏᴡᴍᴏᴅᴇ
❍ /forwardstatus: sʜᴏᴡ ғᴏʀᴡᴀʀᴅ sᴛᴀᴛᴜs
❍ /linksstatus: sʜᴏᴡ ʟɪɴᴋs sᴛᴀᴛᴜs
❍ /slowmodestatus: sʜᴏᴡ sʟᴏᴡᴍᴏᴅᴇ sᴛᴀᴛᴜs
'''


    fullpromote = {
    'can_change_info': True,
    'can_post_messages': True,
    'can_edit_messages': True,
    'can_delete_messages': True,
    'can_invite_users': True,
    'can_restrict_members': True,
    'can_pin_messages': True,
    'can_promote_members': True,
    'can_manage_chat': True,
}

    promoteuser = {
    'can_change_info': False,
    'can_post_messages': True,
    'can_edit_messages': True,
    'can_delete_messages': False,
    'can_invite_users': True,
    'can_restrict_members': False,
    'can_pin_messages': False,
    'can_promote_members': False,
    'can_manage_chat': True,
}
