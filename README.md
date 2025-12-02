Below is a **fully rewritten, polished, deeply detailed `README.md`**, incorporating *every piece of information you provided* while restructuring it into a professional, aesthetic, GitHub-ready document.

This version is production-grade and suitable for open-source release, academic submission, or portfolio presentation.

You can paste this directly into `README.md`.

---

# Email Network Service

### **An End-to-End Reliable UDP Mail System Simulation**

**Email Network Service** is a fully instrumented simulation of an email network stack implementing **SMTP** (Simple Mail Transfer Protocol) and **POP3** (Post Office Protocol v3) over a custom reliable **RDT 3.0** protocol layered on top of UDP.

The system boots UDP-based SMTP and POP3 servers, spawns concurrent SMTP clients, stress-tests the RDT subsystem through heavy traffic, and verifies message integrity by driving POP3 clients against atomic on-disk mailboxes.

This project faithfully models a simplified, real-world email pipeline with special attention to **reliability**, **concurrency**, and **durable storage semantics**.

---

# Table of Contents

1. [Overview](#overview)
2. [Feature Highlights](#feature-highlights)
3. [System Architecture](#system-architecture)

   * [Life of a Message](#life-of-a-message)
   * [High-Level Architecture](#high-level-architecture)
   * [RDT Transport Layer Workflow](#rdt-transport-layer-workflow)
   * [Concurrency Model](#concurrency-model)
   * [Atomic Storage Workflow](#atomic-storage-workflow)
4. [Data & Persistence Model](#data--persistence-model)
5. [Configuration](#configuration)
6. [Prerequisites](#prerequisites)
7. [Setup](#setup)
8. [How to Run](#how-to-run)
9. [Command-Line Options](#command-line-options)
10. [Maintenance Commands](#maintenance-commands)
11. [Files and Logs](#files-and-logs)
12. [Diagrams](#diagrams)

---

# Overview

* **Protocols** – Implements SMTP submission and POP3 retrieval semantics on top of UDP sockets enhanced with a custom reliable datagram layer (`src/rdt/`).
* **Simulation-first** – `src/simulation.py` orchestrates user generation, directory provisioning, server lifecycles, SMTP load, POP3 verification, and summary metrics.
* **Threaded clients** – Flexible concurrency controls allow modeling complex message-sending workloads.
* **Deterministic storage** – Mailboxes and metadata persist to the `database/` directory, enabling POP3 sessions to replay traffic exactly as delivered.

---

# Feature Highlights

This project provides a robust, layered implementation of network services with a focus on concurrency, reliability, and data persistence:

### Custom **RDT 3.0** Protocol

Stop-and-wait reliability over UDP—using:

* Sequence numbers (0/1 alternating)
* CRC32 checksum validation
* Automatic retransmissions
* ACK routing
* Timeout-driven failure handling

### Full SMTP / POP3 Protocol Support

**SMTP:** HELO, MAIL FROM, RCPT TO, DATA, QUIT
**POP3:** USER, PASS, STAT, LIST, RETR, DELE, QUIT

### Thread-Safe Concurrency

The **SMTPServer** uses a `ThreadPoolExecutor` so that expensive I/O (email saving) never blocks packet reception.

### Atomic Mailbox Writes

Emails are staged in a temp directory and moved atomically using `os.replace` to guarantee crash-safe writes.

### End-to-End Simulation Framework

The `Simulation` module automatically:

* Creates users
* Boots servers
* Generates concurrent SMTP traffic
* Verifies mail integrity via POP3 clients

---

# System Architecture

The service is organized into three layers:

1. **Application Layer:** SMTP & POP3 protocols
2. **Transport Layer:** Custom RDT 3.0 reliability over UDP
3. **Persistence Layer:** Mailbox & metadata storage

---

## Life of a Message

1. **Simulation Bootstrap**

   * Provision directories
   * Reset `users.json`
   * Create users via `UserManager`
   * Start SMTP & POP3 servers

2. **SMTP Submission**

   * `src/smtp/smtp_client.py` negotiates server state transitions
   * Streams mail content over RDT datagrams

3. **Reliable Delivery (RDT)**

   * All datagrams go through `RDTDispatcher`
   * Sequence numbers enforced
   * Corrupted packets dropped
   * ACK routing + retransmissions

4. **Mailbox Persistence**

   * `StorageManager` performs atomic writes using per-user locks
   * Metadata (`metadata.json`) updated in sync

5. **POP3 Verification**

   * POP3 clients poll mailboxes to ensure delivery correctness

---

## High-Level Architecture

```text
                +-------------------------------+
                |  Simulation Orchestrator      |
                |  (src/simulation.py)          |
                +-------------------------------+
                  | start/stop servers, users
      ------------+-------------------------------+--------------
      |                          |                                 |
+-------------+        +---------------------+          +--------------------+
| SMTP Client |<-----> |   SMTP Server       |          |   POP3 Server      |
| Threads     |        | (src/smtp/)         |          |  (src/pop3/)       |
+-------------+        +---------------------+          +--------------------+
      |                          |                                 |
      +------------+-------------+-------------+-------------------+
                   | custom reliable UDP (src/rdt/)
                   v
         +-----------------------------+
         | Storage + Auth Layer        |
         | (src/mailbox/, src/auth/)   |
         +-----------------------------+
```

---

## RDT Transport Layer Workflow

The **RDTDispatcher** is a dedicated thread owning the UDP socket:

### Packet Validation

* CRC32 checksum
* Invalid packets dropped silently

### Routing

* **ACK packets** → Sent to matching `RDTSender` via `threading.Event`
* **DATA packets** → Pushed to a shared `queue.Queue` for `RDTReceiver`

---

## Concurrency Model

The `SMTPServer` must remain fully non-blocking:

* Main thread: only receives RDT packets
* Worker thread pool: processes SMTP commands, writes emails, updates metadata
* Prevents disk I/O from stalling the network event loop

---

## Atomic Storage Workflow

1. Acquire per-user mailbox lock
2. Write message to `database/temp/<user>/`
3. Atomically move using `os.replace` → `database/mailboxes/<user>/`
4. Update mailbox metadata
5. Release lock

Prevents partial, corrupted, or duplicated writes.

---

# Data & Persistence Model

| Path                         | Purpose                                  |
| ---------------------------- | ---------------------------------------- |
| `database/users.json`        | Credential store for POP3 authentication |
| `database/mailboxes/<user>/` | Mail storage + `metadata.json` index     |
| `database/temp/`             | Staging area for atomic mailbox writes   |

---

# Configuration

Configuration lives in **`src/config.py`**:

| Setting            | Default              | Description             |
| ------------------ | -------------------- | ----------------------- |
| `SMTP_PORT`        | 2525                 | SMTP server port (UDP)  |
| `POP3_PORT`        | 1100                 | POP3 server port (UDP)  |
| `SERVER_BIND_IP`   | 127.0.0.1            | Localhost bind IP       |
| `RDT_TIMEOUT`      | 1.0                  | Stop-and-wait timeout   |
| `MAX_PAYLOAD_SIZE` | 1024                 | Max bytes per datagram  |
| `MAILBOXES_DIR`    | `database/mailboxes` | Mail storage            |
| `TEMP_EMAILS_DIR`  | `database/temp`      | Pre-commit staging area |

---

# Prerequisites

* Python **3.10+**
* `make`
* Recommended: virtual environment

---

# Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

# How to Run

Boot servers, send messages, validate delivery:

### Using Make

```bash
make run
```

Defaults:
`NUM_USERS=2`, `NUM_EMAILS=1`, `CONCURRENCY=10`, `DELAY=0.2`, `MESSAGE_SIZE=200`

Custom load:

```bash
make run NUM_USERS=5 NUM_EMAILS=3 CONCURRENCY=4 DELAY=0.1 MESSAGE_SIZE=512
```

### Direct Module Execution

```bash
cd email-network-service
python3 -m src.simulation \
    --num_users 5 \
    --num_emails 2 \
    --concurrency 3 \
    --delay_between_sends 0.3 \
    --message_size 512
```

---

# Command-Line Options

| Flag                    | Default | Description           |
| ----------------------- | ------- | --------------------- |
| `--num_users`           | 10      | Users to create       |
| `--num_emails`          | 5       | Emails per user       |
| `--concurrency`         | 5       | Max parallel sends    |
| `--delay_between_sends` | 0.2     | Delay per send thread |
| `--message_size`        | 200     | Payload size (bytes)  |

---

# Maintenance Commands

| Command       | Description                |
| ------------- | -------------------------- |
| `make clean`  | Reset database + caches    |
| `make format` | Format code via Black      |
| `make freeze` | Rebuild `requirements.txt` |

---

# Files and Logs

| Path                                        | Description                                   |
| ------------------------------------------- | --------------------------------------------- |
| `email-network-service/src/`                | Simulation, protocol, RDT, and storage code   |
| `email-network-service/database/`           | Users, mailboxes, metadata                    |
| `design/`                                   | Architecture diagrams (PNG + Mermaid sources) |
| `email_network_service_logger_detailed.log` | Detailed system runtime log                   |

---

# Diagrams

![Full Architecture Diagram](https://github.com/acphotinakis/RDT-Mail-Service/blob/main/design/architecture.png?raw=1)
![RDT Dispatcher](https://github.com/acphotinakis/RDT-Mail-Service/blob/main/design/rdt_dispatcher.png?raw=1)
![Server Concurrency](https://github.com/acphotinakis/RDT-Mail-Service/blob/main/design/server_concurrency.png?raw=1)
![Storage](https://github.com/acphotinakis/RDT-Mail-Service/blob/main/design/storage.png?raw=1)
