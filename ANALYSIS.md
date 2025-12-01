# Executive Summary
- UDP-based SMTP/POP3 stack sits on a custom RDT layer but the lifecycle management around the shared dispatcher/receiver is incomplete. Blocking socket reads and never-stopped receiver loops prevent clean shutdown, which aligns with the hang shown in `lagging_output.txt`.
- Authentication/authorization is only partially implemented: POP3 skips password verification entirely, and SMTP accepts mail for arbitrary recipients by creating ad-hoc `User` objects that are not persisted in `UserManager`, leading to orphaned mailboxes and POP3 failures.
- ACK bookkeeping in the RDT sender is incorrect, leaking ACK waiters and gradually growing dispatcher state under load.
- Several command paths can crash servers (e.g., POP3 QUIT before USER/PASS) due to missing input validation and error handling.

# Detailed Findings
- Critical – dispatcher thread never unblocks on shutdown: `src/rdt/rdt_dispatcher.py:70-116` calls `recvfrom` without a socket timeout and `stop()` only flips a flag and joins. When `stop()` runs (see `smtp_server.stop`/`pop3_server.stop`), the thread remains blocked, so join hangs and shutdown stalls (as seen in `lagging_output.txt`).
- High – receiver generator never stops: `src/rdt/rdt_receiver.py:48-113` sets `running=True` in `__init__` and servers never call `rdt_receiver.stop()`. The `for packet in start_receiving()` loops in `src/smtp/smtp_server.py:181-214` and `src/pop3/pop3_server.py:135-175` therefore never terminate when `_running` is cleared unless new packets arrive, keeping threads alive and compounding the shutdown hang.
- High – POP3 authentication bypass: `_cmd_PASS` in `src/pop3/pop3_server.py:225-241` ignores the provided password and immediately enters TRANSACTION if any username was accepted. Anyone who knows a username can read/delete mail without credentials.
- High – ACK waiter leak on successful sends: `src/rdt/rdt_sender.py:72-96` toggles `curr_seq` before calling `unregister_ack_waiter`, so it unregisters the *next* sequence instead of the one just registered. ACK listeners for the previous seq accumulate in `_ack_listeners`, increasing memory and leaving stale events that can be signaled for future packets.
- Medium – SMTP delivers to non-existent users and bypasses persistence: `_cmd_RCPT`/`_finalize_message` in `src/smtp/smtp_server.py:407-428` and :265-308 construct `User(username)` directly and never consult `UserManager`. Mail to unknown recipients is written to filesystem paths without creating a real account entry, so POP3 (which uses `UserManager`) cannot authenticate or list those messages; messages become orphaned and POP3 integrity checks will fail intermittently.
- Medium – POP3 QUIT can crash before authentication: `src/pop3/pop3_server.py:359-382` builds `User(session["user"])` without verifying the user is set. Sending QUIT before USER/PASS raises `ValueError`, terminating the serve loop thread.
- Medium – Client RDT shutdown leaves receiver running: POP3/SMTP clients call `dispatcher.stop()` and close sockets but never stop the `RDTReceiver` generator (`src/pop3/pop3_client.py:150-169`, `src/smtp/smtp_client.py:214-238`). The generator keeps looping on a closed socket until timeout, risking noisy errors and dangling threads in concurrent simulations.
- Low – Config path is tied to `os.getcwd` (`src/config.py:46-61`), so running code outside the project root will redirect database/mailbox writes to the invoking directory, making state non-deterministic across deployments.

# Lagging Output Diagnosis
- The simulation log shows shutdown hanging inside `smtp_server.stop()` waiting for `RDTDispatcher.stop()` (`lagging_output.txt` stack trace). Because `recvfrom` is blocking without a timeout and `start_receiving()` never exits, the dispatcher thread does not join, and the server threads remain alive. This is the primary cause of lagging/blocked termination and the observed `KeyboardInterrupt` on shutdown.

# Recommended Fixes
- Dispatcher shutdown: set a reasonable socket timeout on all UDP sockets before constructing `RDTDispatcher`, and in `RDTDispatcher.stop()` close or send a sentinel to the socket and join with a hard stop; ensure `recvfrom` loop checks `running` after timeouts so it can exit promptly.
- Receiver lifecycle: add `stop()` calls for `rdt_receiver` in both SMTP/POP3 server `stop()` methods and inside client `_close()`. Consider pushing a sentinel to `data_queue` or clearing `running` so `start_receiving()` yields and the `for` loops can break without new traffic.
- ACK waiter cleanup: track the sequence used for each send attempt (e.g., store `seq = self.curr_seq` before registering) and pass that same seq into `unregister_ack_waiter`, only toggling `curr_seq` after cleanup. Also remove the listener inside `_handle_ack` once it fires.
- POP3 authentication: in `_cmd_PASS`, call `self.user_manager.authenticate(username, password)` and reject on failure; only transition to TRANSACTION on a valid credential match.
- POP3 robustness: guard `_cmd_QUIT` with a check for `session["user"]`; if missing, return a polite `-ERR` instead of constructing a `User` object.
- SMTP recipient validation/persistence: before accepting RCPT, validate the user exists via `UserManager`; reject otherwise. When saving, use the persisted user object so mail is delivered to authenticated mailboxes visible to POP3.
- Path determinism: derive `BASE_DIR` from `os.path.dirname(__file__)` (project root) instead of `os.getcwd()` so database/mailbox paths are stable regardless of working directory.

# Risk Ranking
- Critical: Blocking RDT dispatcher prevents shutdown (`src/rdt/rdt_dispatcher.py:70-116`); receiver loops never stop (`src/rdt/rdt_receiver.py:48-113`).
- High: POP3 password bypass (`src/pop3/pop3_server.py:225-241`); ACK waiter leak (`src/rdt/rdt_sender.py:72-96`).
- Medium: SMTP delivers to unregistered users (`src/smtp/smtp_server.py:265-308`, `src/smtp/smtp_server.py:407-428`); POP3 QUIT crash (`src/pop3/pop3_server.py:359-382`); client receiver shutdown gaps (`src/pop3/pop3_client.py:150-169`, `src/smtp/smtp_client.py:214-238`); path derived from cwd (`src/config.py:46-61`).
- Low: Passwords stored in plain text in `User`/`users.json` (security hygiene risk not affecting current flow).

# Suggested Refactors
- Centralize RDT lifecycle management: give `RDTDispatcher` an explicit `close()` that sets socket timeouts, closes sockets, and stops receivers; have servers and clients share the same shutdown contract.
- Align user management: enforce all user lookups/creations through `UserManager`, and ensure mail delivery requires a persisted user. This avoids orphan mailboxes and keeps POP3/SMTP behavior consistent.
- Normalize config loading: compute `BASE_DIR` relative to the repo (e.g., `Path(__file__).resolve().parent.parent`) and validate directories at startup to prevent state scattering.
- Harden protocol handlers: add guards for unexpected command sequences (e.g., QUIT pre-auth) and return protocol-compliant errors instead of raising exceptions that kill worker threads.
