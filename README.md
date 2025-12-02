Email Network Service
=====================

Simulation of an email system that speaks SMTP and POP3 over a custom reliable UDP data transfer layer. The code lives in `email-network-service/` and is driven by the top-level `Makefile`.


Prerequisites
-------------
- Python 3.10+ (see `email-network-service/pyproject.toml`)
- `make`
- Optional: a virtual environment to isolate dependencies


Setup
-----
1) Create and activate a virtual environment (recommended):
```
python3 -m venv .venv
source .venv/bin/activate
```
2) Install Python dependencies:
```
pip install -r requirements.txt
```


How to Run
----------
The simulation boots an SMTP server (UDP 2525), a POP3 server (UDP 1100), spawns SMTP clients to send messages, then verifies delivery via POP3 clients.

### Quick start with Make
Run from the repo root:
```
make run
```
Defaults (overridable via make variables): `NUM_USERS=2`, `NUM_EMAILS=1`, `CONCURRENCY=10`, `DELAY=0.2`, `MESSAGE_SIZE=200`.

Example with custom load:
```
make run NUM_USERS=5 NUM_EMAILS=3 CONCURRENCY=4 DELAY=0.1 MESSAGE_SIZE=512
```

### Running the module directly
From inside `email-network-service/`, use the same CLI flags as the Makefile target:
```
cd email-network-service
python3 -m src.simulation --num_users 5 --num_emails 2 --concurrency 3 --delay_between_sends 0.3 --message_size 512
```
If your Python build rejects the hyphenated module path used in the Makefile, this direct invocation avoids the issue.


Command-Line Options
--------------------
`python3 -m src.simulation [options]`

- `--num_users`           Number of user accounts to create (default: 10)
- `--num_emails`          Emails each user sends (default: 5)
- `--concurrency`         Max concurrent sending threads (default: 5)
- `--delay_between_sends` Seconds to wait before launching the next send thread (default: 0.2)
- `--message_size`        Approximate email size in bytes (default: 200)


Maintenance Commands
--------------------
- `make clean`   Reset the local database in `email-network-service/database/` and remove `__pycache__` folders.
- `make format`  Format the source with `black`.
- `make freeze`  Regenerate `requirements.txt` from the current environment.


Files and Logs
--------------
- Simulation and protocol code: `email-network-service/src/`
- Data storage: `email-network-service/database/`
- Detailed run log: `email_network_service_logger_detailed.log` (created in the repo root after a run)
