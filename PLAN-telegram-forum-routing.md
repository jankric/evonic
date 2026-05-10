# Plan: Telegram Forum Topic Routing untuk Evonic

**Lokasi file:** `/home/mimin/evonic/PLAN-telegram-forum-routing.md`
**Status:** Draft v2 — Revised after Metis/Momus review (16 findings, 3 CRITICAL fixed)
**Tanggal:** 2026-05-03

---

## Latar Belakang

Evonic saat ini tidak support Telegram forum/topic. Semua pesan dari grup dianggap satu session flat. Tujuan: setiap topic di grup Telegram bisa di-routing ke agent yang berbeda berdasarkan konfigurasi manual `thread_id → agent_id`.

### Kenapa Manual Config (bukan Auto-Resolve)?

Telegram Bot API **tidak punya** method `getForumTopics` — bot tidak bisa enumerate existing topics. Yang tersedia hanya `createForumTopic`, `editForumTopic`, `closeForumTopic`, `reopenForumTopic`, `deleteForumTopic`. Artinya auto-resolve by topic name **tidak mungkin** tanpa workaround yang fragile.

Pendekatan yang dipilih: **manual mapping `thread_id → agent_id` di channel config**. Admin set sekali, langsung jalan. Simpel, reliable, zero API dependency.

---

## Scope

### File yang diubah:

| File | Perubahan |
|------|-----------|
| `backend/channels/telegram.py` | Forum detection, session isolation, agent routing, outbound thread targeting |
| `backend/channels/base.py` | Extend `_do_send` dan `send_message`/`send_message_buffered` signature untuk support `thread_id` |

### File yang TIDAK diubah:

- DB schema — tidak perlu migrasi
- `backend/agent_runtime/runtime.py` — `handle_message` signature tetap
- `backend/channels/registry.py` — channel instantiation tetap `cls(channel_id, agent_id, config)`
- `models/` — session creation tetap pakai existing `get_or_create_session`

### Estimasi: ~120-150 baris tambahan di 2 file

### Backward compatible:

- DM / grup non-forum: behavior 100% sama (thread_id = None → skip semua forum logic)
- Channel tanpa `topic_routing` config: behavior 100% sama
- Existing sessions: tidak terpengaruh

---

## Arsitektur: Bagaimana Agent Routing Bekerja

### Problem: Channel terikat ke 1 agent_id

Registry instantiate channel dengan fixed agent_id:
```python
# registry.py:40
instance = cls(channel_id, channel_data['agent_id'], config)
```

`self.agent_id` di BaseChannel adalah agent default. Untuk forum routing, kita **override agent_id per-message** di `handle_message`, bukan di channel level.

### Solution: Per-message agent resolution

```
Incoming message
  ├── thread_id = None → use self.agent_id (default, unchanged)
  └── thread_id = X
       ├── config.topic_routing[str(X)] exists → use mapped agent_id
       └── not in config → use self.agent_id (default fallback)
```

Agent resolution terjadi di `handle_message` closure, SEBELUM call ke `agent_runtime.handle_message()`. Ini berarti:
- `db.get_or_create_session(resolved_agent_id, ...)` — session terisolasi per agent per topic
- `agent_runtime.handle_message(resolved_agent_id, ...)` — agent yang benar yang proses
- `db.is_session_bot_enabled(session_id, agent_id=resolved_agent_id)` — check per agent
- `db.add_chat_message(session_id, ..., agent_id=resolved_agent_id)` — log ke agent yang benar

---

## Phase 1 — Config Schema

Channel config di DB ditambah field `topic_routing`:

```json
{
  "bot_token": "...",
  "topic_routing": {
    "123456": "agent-sa-id",
    "789012": "agent-kai-id"
  }
}
```

- Key: `message_thread_id` sebagai string
- Value: `agent_id` yang valid
- Tidak ada key = fallback ke `self.agent_id` (channel default)
- Empty dict atau tidak ada `topic_routing` = forum routing disabled

Admin mendapatkan `thread_id` dari:
1. Telegram Desktop/Mobile: klik topic → URL contains thread ID
2. Atau: forward pesan dari topic → metadata contains `message_thread_id`

---

## Phase 2 — Inbound: Session Isolation + Agent Routing

Di `handle_message` closure dalam `TelegramChannel.start()`:

```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    try:
        user_id = str(update.message.chat_id)
        thread_id = getattr(update.message, 'message_thread_id', None)

        # --- Forum topic routing ---
        resolved_agent_id = agent_id  # default from closure
        topic_routing = config.get('topic_routing') or {}

        if thread_id and topic_routing:
            mapped = topic_routing.get(str(thread_id))
            if mapped:
                # Validate agent exists and is enabled
                mapped_agent = db.get_agent(mapped)
                if mapped_agent and mapped_agent.get('enabled', True):
                    resolved_agent_id = mapped
                else:
                    _logger.warning(
                        "Topic %s mapped to agent %s but agent not found/disabled, "
                        "falling back to default", thread_id, mapped)

        # Session key: include thread_id for isolation
        # Format: "{chat_id}" for non-forum, "{chat_id}:t:{thread_id}" for forum topics
        if thread_id:
            session_user_id = f"{user_id}:t:{thread_id}"
        else:
            session_user_id = user_id

        text = strip_system_tags(update.message.text or update.message.caption or '')
        # ... (existing image handling, unchanged) ...

        session_id = db.get_or_create_session(resolved_agent_id, session_user_id, channel_id)

        if not db.is_session_bot_enabled(session_id, agent_id=resolved_agent_id):
            db.add_chat_message(session_id, 'user', text or '[Image]', agent_id=resolved_agent_id)
            return

        # ... (existing reply detection, unchanged) ...

        result = agent_runtime.handle_message(
            resolved_agent_id, session_user_id, final_text, channel_id, image_url=image_url
        )
        # ... rest unchanged ...
```

### Kenapa `session_user_id` bukan `user_id` yang diubah?

`external_user_id` dipakai di banyak tempat downstream (notifier, plugin SDK, agent messaging). Dengan format `{chat_id}:t:{thread_id}`:
- Session lookup: terisolasi per topic ✓
- Notifier resolve: akan match session yang benar karena `external_user_id` sama ✓
- Plugin SDK `send_message`: caller harus tahu format ini — **known limitation**, documented below

### Edge case: General topic

General topic di Telegram forum bisa punya `message_thread_id = 1` atau `None`. Handling:
- `thread_id = None` → non-forum behavior (unchanged)
- `thread_id = 1` dan tidak ada mapping di config → fallback ke default agent
- `thread_id = 1` dan ada mapping → use mapped agent

---

## Phase 3 — Outbound: Reply ke Thread yang Benar

### 3a. Inline reply (dalam handle_message)

PTB v21.1+ `update.message.reply_text()` **otomatis** menyertakan `message_thread_id` dari message asli. Tidak perlu manual passing. Ini sudah benar di code existing:

```python
await update.message.reply_text(chunk, **reply_kwargs)
# PTB auto-includes message_thread_id from the original update
```

**Tidak ada perubahan diperlukan untuk inline reply.**

### 3b. Bot-initiated send (`_do_send`)

`_do_send` dipanggil dari `BaseChannel.send_message` / `send_message_buffered` untuk outbound messages (notifier, plugin SDK, buffered responses). Saat ini signature:

```python
def _do_send(self, external_user_id: str, text: str):
```

Untuk forum support, kita perlu extract `thread_id` dari `external_user_id`:

```python
def _do_send(self, external_user_id: str, text: str):
    if not self._app:
        return

    # Extract thread_id from composite user ID
    chat_id, thread_id = _parse_forum_user_id(external_user_id)

    text = _strip_markdown(text)
    for chunk in _split_message(text):
        kwargs = {"chat_id": chat_id, "text": chunk}
        if thread_id:
            kwargs["message_thread_id"] = thread_id
        self._run_async(self._app.bot.send_message(**kwargs))

    from backend.event_stream import event_stream
    event_stream.emit('message_sent', {
        'channel_type': 'telegram',
        'channel_id': self.channel_id,
        'external_user_id': external_user_id,
        'message': text,
    })
```

Helper function:
```python
def _parse_forum_user_id(external_user_id: str) -> tuple[str, int | None]:
    """Parse '{chat_id}:t:{thread_id}' → (chat_id, thread_id) or (external_user_id, None)."""
    if ':t:' in external_user_id:
        parts = external_user_id.split(':t:', 1)
        try:
            return parts[0], int(parts[1])
        except (ValueError, IndexError):
            pass
    return external_user_id, None
```

### 3c. Approval prompts

`_on_approval_required` sends via `self._app.bot.send_message(chat_id=int(user_id), ...)`. Perlu update:

```python
def _on_approval_required(data):
    if data.get('channel_id') != channel_id:
        return
    ext_user_id = data.get('external_user_id')
    if not ext_user_id:
        return
    chat_id_str, thread_id = _parse_forum_user_id(ext_user_id)
    # ... existing logic ...
    send_kwargs = {"chat_id": int(chat_id_str), "text": text, "reply_markup": keyboard}
    if thread_id:
        send_kwargs["message_thread_id"] = thread_id
    try:
        sent_msg = self._run_async(self._app.bot.send_message(**send_kwargs))
        # ...
```

### 3d. Typing indicator

`send_typing` juga perlu parse forum user ID:

```python
def send_typing(self, external_user_id: str):
    if not self._app:
        return
    chat_id, thread_id = _parse_forum_user_id(external_user_id)
    kwargs = {"chat_id": chat_id, "action": "typing"}
    if thread_id:
        kwargs["message_thread_id"] = thread_id
    self._run_async(self._app.bot.send_chat_action(**kwargs))
```

---

## Phase 4 — BaseChannel Signature (Minimal)

`BaseChannel._do_send`, `send_message`, `send_message_buffered` signature **TIDAK perlu diubah**. Kenapa:

- `external_user_id` sudah string — composite format `{chat_id}:t:{thread_id}` tetap string
- Parsing terjadi di `TelegramChannel._do_send` override — BaseChannel tidak perlu tahu tentang forum
- Buffer key (`self._buf[external_user_id]`) otomatis terisolasi per topic karena key berbeda

**Tidak ada perubahan di `base.py`.**

---

## Edge Cases

| Case | Handling |
|------|---------|
| DM (bukan grup forum) | `thread_id = None`, semua logic forum di-skip, behavior unchanged |
| Grup non-forum | `thread_id = None`, behavior unchanged |
| Forum topic tanpa mapping di config | Fallback ke `self.agent_id` (channel default agent) |
| Forum topic dengan agent disabled/deleted | Log warning, fallback ke default agent |
| General topic (`thread_id = 1`) | Treated sama — kalau ada mapping, pakai; kalau tidak, fallback |
| `topic_routing` config kosong/absent | Forum routing disabled, semua topic pakai default agent |
| Bot bukan admin | Tidak masalah — kita tidak call management API, hanya baca `message_thread_id` dari incoming messages |
| Pesan tanpa `message_thread_id` di forum group | Treated as non-forum message |

---

## Known Limitations (Documented, Not Addressed)

### 1. Plugin SDK tidak aware forum topic

`plugin_sdk.send_message(agent_id, external_user_id, channel_id, text)` — plugin caller harus pass composite `external_user_id` format `{chat_id}:t:{thread_id}` untuk reply ke topic yang benar. Kalau plugin pass plain `chat_id`, message akan dikirim ke chat tanpa thread context.

**Mitigation:** Ini acceptable karena plugin SDK jarang dipakai untuk Telegram forum. Kalau nanti perlu, bisa ditambah `thread_id` param ke SDK.

### 2. Notifier session resolution

`notifier.py` resolve session by `(agent_id, channel_id, external_user_id)`. Dengan composite user ID, notifier akan match session yang benar. Tapi kalau notifier di-trigger tanpa `external_user_id` (broadcast), message tidak akan masuk ke topic manapun.

**Mitigation:** Broadcast notifications ke forum group memang tidak make sense per-topic. Acceptable.

### 3. Agent messaging cross-topic

`agent_messaging.py` pakai `__agent__<sender_id>` sebagai external user key. Inter-agent messages tidak punya topic context. Ini acceptable karena agent-to-agent communication bukan user-facing.

### 4. Session slug opacity

Session ID akan berisi hash dari composite user ID. Dari filename saja tidak bisa tahu topic mana. Acceptable — session metadata di DB tetap queryable.

---

## Urutan Implementasi

1. **Phase 1** — Config schema (define `topic_routing` format, no code change)
2. **Phase 2** — Inbound: session isolation + agent routing di `handle_message`
3. **Phase 3** — Outbound: `_do_send`, `send_typing`, approval prompts parse composite user ID
4. Verify: DM dan grup non-forum behavior unchanged

**Semua phase di 1 file: `backend/channels/telegram.py`**

---

## Estimasi

- ~120-150 baris tambahan di `telegram.py`
- 0 baris di `base.py` (signature unchanged)
- Backward compatible
- Tidak perlu restart DB atau migrasi
- Test: buat 2 topic di grup forum, set `topic_routing` di channel config, coba chat

---

## Referensi

- Telegram Bot API forum methods: `createForumTopic`, `editForumTopic`, `closeForumTopic`, `reopenForumTopic`, `deleteForumTopic` (NO `getForumTopics`)
- PTB v21 `message_thread_id`: auto-included in `reply_text()` shortcuts
- Evonic Telegram channel: `backend/channels/telegram.py`
- Evonic channel registry: `backend/channels/registry.py`
- Evonic session creation: `models/chat.py:142` → `get_or_create_session(agent_id, external_user_id, channel_id)`
- Evonic runtime: `backend/agent_runtime/runtime.py:713` → `handle_message(agent_id, external_user_id, ...)`
