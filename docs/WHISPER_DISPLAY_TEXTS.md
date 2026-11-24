# Whisper Display Texts & Buttons

User-facing whisper (secret message) displays for `@ninjasecretbot`, built as Telegram Rich Messages (Bot API 10.3).

> **Scope:** whisper delivery, post-read states and popups. Start, help, settings, stats and tutorial screens are excluded.

---

## 1. Card Layout

Every whisper type uses the same card. Only the emoji, the status line and the `<cite>` label change.

There are two layouts, chosen by the number of receivers.

### 1a. Single receiver (exactly one user)

No counter. A `👁` is appended to the `<cite>` label **only after the receiver has read it**.

Before read:

```
┌──────────────────────────────────┐
│ “ 💌 ☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖 💌             │
│   🤫 𝚂𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞! ”          │
└──────────────────────────────────┘
      ( 💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐 )
```

After read:

```
┌──────────────────────────────────┐
│ “ 💌 ☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖 💌             │
│   🤫 𝚂𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞! 👁 ”        │
└──────────────────────────────────┘
      ( 💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐 )
```

### 1b. Several receivers or `@all` (unchanged)

```
┌──────────────────────────────────┐
│ “ 💌 ☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖 & SONAN 💌      │
│   👁Read: 0/2                    │
│   🤫 𝚂𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞! ”         │
└──────────────────────────────────┘
      ( 💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐 )
```

### Parts

| Part | Element | Content |
|------|---------|---------|
| Line 1 | `<aside>` body | `💌` + receivers (tappable mentions) + `💌` |
| Line 2 | `<aside>` body | **Optional.** Built from: `⏰` expiry (timer), `👀 … read it` (reveal, after read), `👁Read: read/total` (several receivers or `@all` only). If nothing applies, line 2 and its `<br>` are omitted. |
| Label | `<cite>` | Style label (section 2). Single receiver: ` 👁` appended after read. |
| Button | `<tg-button-row align="center">` | One primary button, last element |

Line 2 parts, in this fixed order, joined with ` · `:

1. `⏰ <tg-time>` (only if the whisper has a timer)
2. `👀 {readers} read it` (only if `!reveal` and at least one target has read)
3. `👁Read: read/total` (only if there are several receivers) or `👁Read: N` (`@all`)

Rules:

- No title, tagline, footer or table.
- Line 1 is symmetrical: `💌` on both sides of the receivers.
- Labels follow one pattern: `{emoji} 𝚂𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!` (mathematical sans-serif).
- Nothing after the button row.
- The `<aside>` italicizes plain text. Links keep their link color.
- Escape every user-supplied name with `html.escape` before inserting it.
- Mentions (`tg://user?id=`) are tappable but send no push notification.
- Whisper cards need a client that supports Bot API 10.1+. Older clients show a plain fallback.

Single-receiver rules (the new behavior):

- "Single" means exactly one **unique** target user, not `@all`. Duplicate targets (the same user mentioned twice) are merged first, so they count as single.
- The `👁` never appears before the read. It is not a placeholder and not part of the unread card.
- The `👁` is separated from the label by one normal space: `…𝚢𝚘𝚞! 👁`.
- Only a read by the **target** turns the eye on. Opens by the sender, the owner or a sudo user never change the card.
- The eye is derived from stored read state (`read >= 1`) every time the card is built. Never keep it as a separate flag.
- The eye is only ever visible on Classic, VIP, Cute, Reveal and Timer. Burn and Delete cards are replaced on read (section 4), so the eye never shows there.
- Several receivers and `@all` keep `👁Read: …` on line 2. No eye is added to their label.

---

## 2. Whisper Types

| Type | Modifier | `<cite>` label | Extra on line 2 |
|------|----------|----------------|-----------------|
| Classic | none | `🤫 𝚂𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!` | none |
| VIP | `!vip` `!v` | `👑 𝚅𝙸𝙿 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!` | none |
| Cute | `!cute` `!c` `!love` `!l` | `💕 𝙻𝚘𝚟𝚎 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!` | none |
| Reveal | `!reveal` `!r` | `👀 𝚁𝚎𝚟𝚎𝚊𝚕 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!` | `👀 … read it` after read |
| Delete | `!delete` `!d` `!del` | `💨 𝚅𝚊𝚗𝚒𝚜𝚑𝚒𝚗𝚐 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!` | none |
| Burn | `!burn` `!b` | `🔥 𝙱𝚞𝚛𝚗 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!` | none |
| Timer | `!timer:N` `!t:N` | `⏰ 𝚃𝚒𝚖𝚎𝚍 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!` | `⏰ <tg-time>` first on line 2 |

Modifiers combine. When several apply, use the label of the strongest one: Burn > Delete > Reveal > Timer > VIP > Cute > Classic. Keep the timer's expiry on line 2 regardless, and keep the reveal line after a read regardless.

Receivers line:

| Target | Line 1 | Line 2 (no timer, no reveal) |
|--------|--------|------------------------------|
| One user | `💌 ☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖 💌` | none (eye in label after read) |
| Several users | `💌 ☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖 & SONAN 💌` | `👁Read: 0/2` |
| `@all` / `@everyone` | `💌 Everyone 💌` | `👁Read: N` (no total) |

### Button

| Text | Callback data | Style |
|------|---------------|-------|
| `💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐` | `whisper_view_{whisper_id}` | **`danger`** (recommended default) or `success` |

- Preferred style: **`danger`** (red) — recommended as the default for the read button.
- Alternative: `success` (green) when a softer / positive tone is desired.
- Other available styles (`primary`, `link`, or no style) are not used for the main whisper button.

---

## 3. Examples

All examples send to `sendRichMessage`. `$BOT_TOKEN` is read from your shell. Write the JSON to a UTF-8 file and send it with `--data-binary @file`. Passing the text on the command line breaks emoji on Windows (they turn into `?`).

### Classic, two receivers (danger style)

```bash
export EXPIRES=$(( $(date +%s) + 3600 ))

cat > whisper_rich.json <<EOF
{
  "chat_id": -1003029976514,
  "rich_message": {
    "html": "<aside>💌 <a href=\"tg://user?id=6153949909\">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> &amp; <a href=\"tg://user?id=987654321\">SONAN</a> 💌<br>👁Read: 0/2<cite>🤫 𝚂𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!</cite></aside><tg-button-row align=\"center\"><tg-button type=\"callback_data\" style=\"danger\" data=\"whisper_view_test001\">💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐</tg-button></tg-button-row>"
  }
}
EOF

curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendRichMessage" \
  -H "Content-Type: application/json; charset=utf-8" \
  --data-binary @whisper_rich.json
```

### Classic, single receiver (the new default)

Before read (no line 2, no `<br>`):

```html
<aside>💌 <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> 💌<cite>🤫 𝚂𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!</cite></aside><tg-button-row align="center"><tg-button type="callback_data" style="danger" data="whisper_view_test001">💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐</tg-button></tg-button-row>
```

After read (same card, eye appended):

```html
<aside>💌 <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> 💌<cite>🤫 𝚂𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞! 👁</cite></aside><tg-button-row align="center"><tg-button type="callback_data" style="danger" data="whisper_view_test001">💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐</tg-button></tg-button-row>
```

### The other types: `html` values (before read)

Use the same command. Replace only the `html` value. For a single receiver the eye is added to the label after read, exactly as shown above.

**VIP** (single)

```html
<aside>💌 <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> 💌<cite>👑 𝚅𝙸𝙿 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!</cite></aside><tg-button-row align="center"><tg-button type="callback_data" style="danger" data="whisper_view_test001">💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐</tg-button></tg-button-row>
```

**Cute** (single)

```html
<aside>💌 <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> 💌<cite>💕 𝙻𝚘𝚟𝚎 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!</cite></aside><tg-button-row align="center"><tg-button type="callback_data" style="danger" data="whisper_view_test001">💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐</tg-button></tg-button-row>
```

**Reveal** (single)

```html
<aside>💌 <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> 💌<cite>👀 𝚁𝚎𝚟𝚎𝚊𝚕 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!</cite></aside><tg-button-row align="center"><tg-button type="callback_data" style="danger" data="whisper_view_test001">💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐</tg-button></tg-button-row>
```

**Delete** (single)

```html
<aside>💌 <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> 💌<cite>💨 𝚅𝚊𝚗𝚒𝚜𝚑𝚒𝚗𝚐 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!</cite></aside><tg-button-row align="center"><tg-button type="callback_data" style="danger" data="whisper_view_test001">💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐</tg-button></tg-button-row>
```

**Burn** (single)

```html
<aside>💌 <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> 💌<cite>🔥 𝙱𝚞𝚛𝚗 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!</cite></aside><tg-button-row align="center"><tg-button type="callback_data" style="danger" data="whisper_view_test001">💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐</tg-button></tg-button-row>
```

**Burn** (two receivers, counter kept)

```html
<aside>💌 <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> &amp; <a href="tg://user?id=987654321">SONAN</a> 💌<br>👁Read: 0/2<cite>🔥 𝙱𝚞𝚛𝚗 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!</cite></aside><tg-button-row align="center"><tg-button type="callback_data" style="danger" data="whisper_view_test001">💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐</tg-button></tg-button-row>
```

**Timer** (`!t:3600`, single; `${EXPIRES}` is a Unix timestamp). Line 2 holds only the expiry. No counter.

```html
<aside>💌 <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> 💌<br>⏰ <tg-time unix="${EXPIRES}" format="r">soon</tg-time><cite>⏰ 𝚃𝚒𝚖𝚎𝚍 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!</cite></aside><tg-button-row align="center"><tg-button type="callback_data" style="danger" data="whisper_view_test001">💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐</tg-button></tg-button-row>
```

**Timer** (two receivers, counter kept)

```html
<aside>💌 <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> &amp; <a href="tg://user?id=987654321">SONAN</a> 💌<br>⏰ <tg-time unix="${EXPIRES}" format="r">soon</tg-time> · 👁Read: 0/2<cite>⏰ 𝚃𝚒𝚖𝚎𝚍 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!</cite></aside><tg-button-row align="center"><tg-button type="callback_data" style="danger" data="whisper_view_test001">💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐</tg-button></tg-button-row>
```

**Everyone** (`@all`)

```html
<aside>💌 Everyone 💌<br>👁Read: 0<cite>🤫 𝚂𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!</cite></aside><tg-button-row align="center"><tg-button type="callback_data" style="danger" data="whisper_view_test001">💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐</tg-button></tg-button-row>
```

---

## 4. Post-Read States

Update the same message with `editMessageText` and `rich_message`. For inline-posted whispers, pass `inline_message_id` instead of `chat_id` and `message_id`.

| State | Trigger | Card after edit | Button |
|-------|---------|-----------------|--------|
| Read (single receiver) | The target reads | Label gets ` 👁` appended: `🤫 𝚂𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞! 👁`. No counter. | kept |
| Read progress (several / `@all`) | A target reads | Line 2 count updates: `👁Read: 1/2` | kept |
| Reveal | Target reads, `!reveal` | Line 2 gets `👀 {readers} read it`. Several receivers keep `· 👁Read: 1/2`. Single receiver has no counter, only the eye in the label. | kept |
| Burn | All targets read, `!burn` | Body: `✅ {names} read it`; cite: `🔥 𝙱𝚞𝚛𝚗𝚎𝚍` | removed |
| Delete | Target reads, `!delete` | Body: `💨 Poof! Nothing to see here` (no cite) | removed |
| Expired | Timer runs out | Body: `⏰ Time's up. This secret expired.` (no cite) | removed |

Edit guards (these prevent real errors):

- **Skip no-op edits.** Telegram rejects an edit whose content is identical with `400 message is not modified`. That now happens often: a single receiver who taps Read a second time produces the same card. Build the new `html`, compare it with the last html you stored (or compare the read count / read-state), and skip the call when equal. Also catch `MessageNotModified` and ignore it.
- **Only first reads edit.** Edit only when the set of valid readers actually grew. Re-reads by the same target, and opens by the sender, owner or sudo users, never edit.
- **Edit failures never block the secret.** Show the popup first. If the edit fails (message deleted, rate limit, `FloodWait`), log it and continue. The secret must still open.
- **Terminal states win.** Once a whisper is burned, deleted or expired, never rebuild the normal card for it. A late read-progress edit must not bring the button back.
- **Count from the database.** Mark a reader with an atomic add-to-set, then build the card from the returned read list. Two people tapping at once must not overwrite each other's count.

Single-receiver read edit, as `html`:

```html
<aside>💌 <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> 💌<cite>🤫 𝚂𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞! 👁</cite></aside><tg-button-row align="center"><tg-button type="callback_data" style="danger" data="whisper_view_test001">💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐</tg-button></tg-button-row>
```

Reveal edit, single receiver, as `html`:

```html
<aside>💌 <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> 💌<br>👀 <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> read it<cite>👀 𝚁𝚎𝚟𝚎𝚊𝚕 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞! 👁</cite></aside><tg-button-row align="center"><tg-button type="callback_data" style="danger" data="whisper_view_test001">💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐</tg-button></tg-button-row>
```

Reveal edit, two receivers, one has read, as `html`:

```html
<aside>💌 <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> &amp; <a href="tg://user?id=987654321">SONAN</a> 💌<br>👀 <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> read it · 👁Read: 1/2<cite>👀 𝚁𝚎𝚟𝚎𝚊𝚕 𝚜𝚎𝚌𝚛𝚎𝚝 𝚏𝚘𝚛 𝚢𝚘𝚞!</cite></aside><tg-button-row align="center"><tg-button type="callback_data" style="danger" data="whisper_view_test001">💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐</tg-button></tg-button-row>
```

Burn edit, as `html`:

```html
<aside>✅ <a href="tg://user?id=6153949909">☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖</a> &amp; <a href="tg://user?id=987654321">SONAN</a> read it<cite>🔥 𝙱𝚞𝚛𝚗𝚎𝚍</cite></aside>
```

Delete edit, as `html`:

```html
<aside>💨 Poof! Nothing to see here</aside>
```

Expired edit, as `html`:

```html
<aside>⏰ Time's up. This secret expired.</aside>
```

---

## 5. Builder (Python)

The reference implementation is `NinjaSecret/utils/whisper_card.py` (pure functions, no Telegram or database access). `NinjaSecret/utils/rich_api.py` sends the result through the Bot API, because pyrogram cannot carry `rich_message`.

```python
from NinjaSecret.utils.whisper_card import whisper_card, card_from_whisper

# Single receiver, unread: no eye, no line 2
rich = whisper_card("a1b2c3", [(6153949909, "☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖")])

# After the target read it: eye appended to the label
rich = whisper_card("a1b2c3", [(6153949909, "☬𝕾𝖈𝖔𝖗𝖕𝖞𝕯𝖊𝖛🏖")], read=1)

# Straight from a stored whisper document (what the Read handler uses)
rich = card_from_whisper(whisper_doc)
```

Sending and editing:

```python
from NinjaSecret.utils.rich_api import send_rich_message, edit_rich_message, answer_inline_query

await send_rich_message(chat_id, rich)                                # sendRichMessage
await edit_rich_message(rich, inline_message_id=inline_id)            # editMessageText + rich_message
await answer_inline_query(query.id, [raw_result])                     # raw result with input_message_content.rich_message
```

Notes:

- Do not combine `html` with `markdown` or `blocks` in one `rich_message`.
- `callback_data` is limited to 1–64 bytes, so keep `whisper_id` short.
- Editing a rich message through `editMessageText` can drop custom emoji. Standard emoji are unaffected.
- `chosen_inline_result` may arrive without `inline_message_id` for inline rich results with rich buttons (tdlib #895). The Read handler attaches the id from the first callback query it receives.
- `<br>` is added only when line 2 exists. A dangling `<br>` before `<cite>` would render an empty line on single-receiver cards.
- Inline results are always built with `read=0`, so a fresh single-receiver card never shows the eye.
- The timer expiry is computed once when the inline result is built and stored unchanged, so the card and the database always agree.
- `<tg-time format="r">` counts down on the client, so timed cards are not edited periodically. A watcher only swaps in the "expired" card.
- Button colour: `WHISPER_BUTTON_STYLE=danger` (default) or `success`.
- Never put raw user text into `html` except through the builder (it escapes every name).
- `/richtest` (owner/sudo) sends sample cards through `sendRichMessage` to verify Bot API support after deploying.

---

## 6. Callback Popups (plain text)

Alert popups can't render rich markup. Texts are unchanged.

| Case | Text |
|------|------|
| Not for you | `🙈 ɴᴏᴛ ғᴏʀ ʏᴏᴜ!` + `🥷 ᴛʜɪs sᴇᴄʀᴇᴛ ɪs ɴᴏᴛ ғᴏʀ ʏᴏᴜ.` + `💭 ᴛʏᴘᴇ: @ninjasecretbot [ʏᴏᴜʀ sᴇᴄʀᴇᴛ] [ᴛᴀʀɢᴇᴛ]` |
| Expired | `⏰ ᴛɪᴍᴇ ɪs ᴜᴘ! ᴛʜɪs sᴇᴄʀᴇᴛ ʜᴀs ᴇxᴘɪʀᴇᴅ!` |
| Burned | `🔥 ᴛʜɪs sᴇᴄʀᴇᴛ ᴡᴀs ᴅᴇsᴛʀᴏʏᴇᴅ ᴀғᴛᴇʀ ʀᴇᴀᴅɪɴɢ!` |
| Gone | `🙈 ᴛʜɪs sᴇᴄʀᴇᴛ ɪs ɴᴏ ʟᴏɴɢᴇʀ ᴀᴠᴀɪʟᴀʙʟᴇ!` |
| Load error | `🙈 ᴄᴀɴɴᴏᴛ ʟᴏᴀᴅ ᴛʜɪs sᴇᴄʀᴇᴛ. ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ!` |
| Target info error | `🙈 ᴄᴀɴɴᴏᴛ ɢᴇᴛ ᴛᴀʀɢᴇᴛ ɪɴғᴏʀᴍᴀᴛɪᴏɴ!` |

The secret content opens in a popup with `show_alert=True` when a valid reader taps the button. A read by the sender, owner or a sudo user opens the secret but does not count as a read and does not show the eye.

---

## 7. Other Screens

Keyboards for the dashboard, stats, empty query and unauthorized screens, the styles guide, creation prompts, error texts, and the stats and dashboard texts are unchanged. They are not whisper delivery cards.

The whisper delivery message has exactly one button: `💬 ʀᴇᴀᴅ sᴇᴄʀᴇᴛ 🔐` (`whisper_view_{whisper_id}`) with style `danger` (or `success`).

---

## 8. Source Files

| File | Contents |
|------|----------|
| `NinjaSecret/utils/whisper_card.py` | Card builder, terminal cards, stored-whisper to card helpers |
| `NinjaSecret/utils/rich_api.py` | `sendRichMessage`, `editMessageText`, `answerInlineQuery` over HTTPS |
| `NinjaSecret/utils/whisper_utils.py` | Inline result builder (`create_whisper_inline_result`) |
| `NinjaSecret/plugins/whisper/callbacks.py` | Read handler, read tracking, popup texts |
| `NinjaSecret/plugins/whisper/inline_handler.py` | Inline query results |
| `NinjaSecret/plugins/whisper/cleanup_task.py` | Expiry watcher, cache cleanup |
| `NinjaSecret/mongo/whisperdb.py` | `readers`, atomic read / burn / expiry claims |
| `tests/` | Card, API, inline and end-to-end whisper tests |
