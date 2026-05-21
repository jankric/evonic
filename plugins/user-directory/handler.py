"""User Directory -- event handlers.
Auto-registers users on session creation and enforces access control.
"""

import json
import uuid

PLUGIN_ID = 'user-directory'


def _get_config(sdk):
    """Get plugin config with defaults."""
    cfg = sdk.config or {}
    auto = str(cfg.get('AUTO_REGISTER', 'true')).lower() in ('true', '1', 'yes')
    prefix = cfg.get('DEFAULT_GROUP_PREFIX', 'auto-')
    return auto, prefix


def on_session_created(event, sdk):
    """Handle session_created: auto-register user + link to agent + privacy notice.

    Event shape:
    {
        "session_id": "...",
        "agent_id": "...",
        "external_user_id": "...",
        "channel_type": "...",
        "channel_id": "...",
        "user_name": "...",
        "is_new": True/False
    }
    """
    auto_register, default_prefix = _get_config(sdk)
    if not auto_register:
        sdk.log('Auto-register disabled, skipping')
        return

    session_id = event.get('session_id')
    agent_id = event.get('agent_id')
    ext_uid = event.get('external_user_id')
    channel_type = event.get('channel_type')
    channel_id = event.get('channel_id')
    user_name = event.get('user_name', 'User')
    is_new = event.get('is_new', False)

    if not ext_uid or not agent_id:
        sdk.log(f'Skipping auto-register: missing ext_uid={ext_uid!r} agent_id={agent_id!r}')
        return

    try:
        from models.db import db as _db

        # 1. Try to find existing user by contact
        user = _db.find_user_by_contact(channel_type, ext_uid)
        existing = user is not None

        if not existing:
            # 2. Create new user
            user_id = f'u-{uuid.uuid4().hex[:12]}'
            user = _db.create_user(
                user_id=user_id,
                name=user_name,
                notes=f'Auto-registered from {channel_type}',
                actor_type='system',
                actor_id=agent_id
            )
            # 3. Add contact
            _db.add_contact(
                user_id, channel_type, ext_uid,
                value=ext_uid,
                channel_id=channel_id or '',
                actor_type='system',
                actor_id=agent_id
            )
            # 4. Link to agent
            _db.link_user_to_agent(
                user_id, agent_id,
                channel_id=channel_id or '',
                is_auto_created=True,
                actor_type='system',
                actor_id=agent_id
            )
            # 5. Assign to default group
            group_id = f'{default_prefix}{agent_id}'
            existing_group = _db.get_group(group_id)
            if existing_group:
                _db.add_group_member(group_id, 'user', user_id)
            else:
                group = _db.create_group(
                    name=f'Auto {agent_id}',
                    description=f'Auto-created group for {agent_id}',
                    group_id=group_id
                )
                if group:
                    _db.add_group_member(group_id, 'agent', agent_id)
                    _db.add_group_member(group_id, 'user', user_id)

            sdk.log(f'Auto-registered user {user_id} ({user_name}) for agent {agent_id}')

        # 6. Send privacy notice on first interaction
        if is_new or not existing:
            notice = (
                'Your profile (name, notes) is shared with agents in your groups. '
                'You can manage your privacy settings at any time. '
                'Contact this agent\'s administrator to request data deletion.'
            )
            try:
                sdk.send_message(agent_id, ext_uid, channel_id or '', notice)
                sdk.log(f'Privacy notice sent to {ext_uid}')
            except Exception as e:
                sdk.log(f'Failed to send privacy notice: {e}')

    except Exception as e:
        sdk.log(f'Auto-register error: {e}')
