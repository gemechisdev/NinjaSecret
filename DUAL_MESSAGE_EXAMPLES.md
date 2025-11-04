# Dual Message Feature Examples

The Dual Message feature allows you to send different messages in a single whisper. It supports **two flexible formats** to fit different use cases.

## Two Formats Supported

### Format 1: Simple (Public + Private)
```
@ninjasecretbot [public_message] | [private_message] [targets]
```
- **Public message** (before `|`) - shown to unauthorized users
- **Private message** (after `|`) - shown only to targets
- Perfect for announcements with secret details

### Format 2: Advanced (Different Groups)
```
@ninjasecretbot [message1] [targets1] | [message2] [targets2]
```
- **Users in targets1** see message1
- **Users in targets2** see message2
- **Others** have no access
- Perfect for sending different info to different groups

## Format 1 Examples (Simple: Public + Private)

### 1. Public Announcement with Secret Details

```
@ninjasecretbot Hi everyone! | Secret note for you @user1,@user2
```
- Everyone (unauthorized) sees: "Hi everyone!"
- @user1 and @user2 see: "Secret note for you"

### 2. Event with Private Location

```
@ninjasecretbot Party this Friday! | Location: 123 Main St @invitees
```
- Public sees: "Party this Friday!"
- Invitees see: "Location: 123 Main St"

### 3. General Info with VIP Details

```
@ninjasecretbot Public announcement | Private VIP details @vip !vip
```
- Public sees: "Public announcement"
- VIP members see: "Private VIP details" (with VIP styling)

## Format 2 Examples (Advanced: Different Groups)

### 1. Different Messages for Different Users

```
@ninjasecretbot Message for Alice @alice | Message for Bob @bob
```
- Alice sees: "Message for Alice"
- Bob sees: "Message for Bob"
- Others: No access

### 2. Team-Specific Updates

```
@ninjasecretbot Team A: Meeting at 2pm @teamA | Team B: Meeting at 3pm @teamB
```
- Team A members see their time
- Team B members see their time
- Non-members: No access

### 3. User ID Targeting

```
@ninjasecretbot Hi user1! @user1 | Hi user2 and user3! @user2,12345678
```
- @user1 sees first message
- @user2 and user 12345678 see second message
- Others: No access

## Mixed Examples

### Public to All, Private to Admins

```
@ninjasecretbot Event this Friday! @all | Budget approved: $500 @admin,@moderator
```
- Everyone sees: "Event this Friday!"
- Admins/moderators see: "Budget approved: $500"

### Sequential Information

```
@ninjasecretbot Phase 1 complete @manager | Phase 2 starting @developers
```
- Manager sees Phase 1 status
- Developers see Phase 2 notice
- Others: No access

## Using with Modifiers

Both formats work with all modifiers:

### With Timer (Simple Format)
```
@ninjasecretbot Public info | Confidential @team !timer:3600
```
Expires in 1 hour

### With Burn After Reading (Advanced Format)
```
@ninjasecretbot For Alice @alice | For Bob @bob !delete
```
Burns after all targets read

### Multiple Modifiers
```
@ninjasecretbot Public | Private @vip !vip !timer:7200 !delete
```
VIP styling + 2 hour timer + burn after reading

## How It Works

### Simple Format Logic:
1. If user is in private targets → sees private message
2. If user is NOT in targets → sees public message (if available)
3. Sender/owner → always see private message

### Advanced Format Logic:
1. If user is in private targets (after `|`) → sees private message
2. If user is in public targets (before `|`) → sees public message
3. If user is NOT in any targets → NO ACCESS
4. Sender/owner → always see private message

## Important Notes

### Character Limits
- Each message part has a 180 character limit
- Plan your messages accordingly

### Precedence Rules
- Private targets (after `|`) take precedence over public targets
- Sender and owner always see the private message
- If public part has no targets, it's shown to unauthorized users (Format 1)
- If public part has targets, unauthorized users get no access (Format 2)

### Backward Compatibility
- Old single-message whispers work unchanged
- No database migration needed
- Both formats coexist seamlessly

## Best Practices

1. **Use Format 1** for public announcements with secret details
2. **Use Format 2** for completely different messages to different groups
3. **Keep messages clear** - users should understand what they're seeing
4. **Test first** - verify both groups see the right content
5. **Combine with modifiers** - use !timer for time-sensitive dual messages

## Real-World Scenarios

### Scenario 1: Event Planning (Format 1)
```
@ninjasecretbot Pizza party Friday! Bring friends! | Remember vegetarian options. Budget: $200 @organizer,@assistant !timer:86400
```
- Everyone sees the invitation
- Only organizers see planning details
- Expires in 24 hours

### Scenario 2: Team Communication (Format 2)
```
@ninjasecretbot Frontend: API ready, start integration @frontend | Backend: Deploy to staging complete @backend !cute
```
- Frontend team gets their update
- Backend team gets their update
- Non-team members have no access

### Scenario 3: Mixed Public/Private (Format 1)
```
@ninjasecretbot New feature launching soon! | Beta access code: ABC123 @betatesters !timer:3600
```
- Public sees the announcement
- Beta testers get access code
- Code expires in 1 hour

## Need Help?

- Use `/help` in the bot for quick reference
- Click "Tutorial" button in dashboard for interactive guide
- Experiment with both formats to find what works best!
