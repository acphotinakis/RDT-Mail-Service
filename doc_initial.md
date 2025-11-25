## 📝 Software Design Document: Gmail Clone Network Service

This document outlines the finalized design for implementing a functional email client (a Gmail-style clone) on top of the custom **SMTP/POP3 network service**. The design adheres to the provided modular structure, ensuring strict separation between the reliable transport layer (RDT), protocol logic, and user interface.

---

## 1. 🎯 Project Goals and Scope

The primary objective is to build a complete, end-to-end email system using Python, focusing on these key goals:
* **Reliable Transport:** Successfully implement the **Custom RDT protocol** to replace standard TCP for reliable data transfer, particularly between the MTA Client and Server.
* **Protocol Compliance:** Implement the necessary state machines to handle the **SMTP** (sending) and **POP3** (receiving) protocols.
* **Full-Stack Functionality:** Deliver a usable **Graphical User Interface (GUI)** that allows a user to compose, send, authenticate, and view messages stored on the server.

---

## 2. 🏛️ Architectural Pattern: MVC (Model-View-Controller)

The client application will follow the Model-View-Controller (MVC) pattern to ensure the network logic is decoupled from the UI (the Gmail clone's look).

| Layer | Responsibility | Key Files | Person |
| :--- | :--- | :--- | :--- |
| **Model (Data)** | Manages the *state* of the application (e.g., list of emails, user credentials, message formats). | `src/client/user_agent.py` (holds application state), `database/` files. | C |
| **View (UI)** | Renders the interface and accepts user input (e.g., displays the inbox, shows the "Compose" window). | `src/client/compose_email.py`, `src/client/inbox_viewer.py`. | C |
| **Controller (Logic)** | Handles user actions, calls the networking modules, and updates the Model/View. | `src/client/run_client.py` (orchestrator). | C |

---

## 3. 💾 Core Data Structures and Protocols

### A. RDT Packet Structure (`src/rdt/`)
This is the lowest application layer and the foundation of reliability.

| File | Purpose | Key Classes/Functions |
| :--- | :--- | :--- |
| **`rdt_packet.py`** | Defines the byte structure for all data exchanged, including fields for **Sequence Number, ACK Number, Flags (SYN, ACK, DATA), and Checksum**. | `RDTHeader`, `PacketSerializer.pack/unpack()` |
| **`rdt_sender.py` / `rdt_receiver.py`** | Implements the **State Machine** logic for reliable transport (retransmission, timeout handling, window management). | `RDTSender`, `RDTReceiver` |
| **`checksum.py`** | Utility to calculate and verify the packet checksum. | `calculate_checksum()` |

### B. Storage Mechanism (`src/mailbox/`)
The persistence layer for all user data.

| File | Purpose | Responsibility |
| :--- | :--- | :--- |
| **`storage_manager.py`** | The public API for persistence. Handles saving and reading messages to/from disk. | Ensures **thread-safe** access to the file system to prevent concurrent writes from corrupting user mailboxes. |
| **`mailbox_writer.py`** | Handles formatting and saving incoming email content into files within `database/mailboxes/`. | Saves email files (e.g., `email_0003.txt`) and updates `metadata.json`. |

---

## 4. 📞 Component Interaction & Workflow (The Glue)

### A. Server Components

| Component | Responsibility (Main File) | Protocol Logic | Storage Interaction |
| :--- | :--- | :--- | :--- |
| **MTA Server** | `src/server/run_smtp_server.py` | Uses `src/smtp/smtp_server.py` to parse commands and `src/rdt/rdt_receiver.py` for reliable stream delivery. | Calls `src/mailbox/storage_manager.py` (write action) after receiving the final `DATA` command. |
| **MAA Server** | `src/server/run_pop3_server.py` | Uses `src/pop3/pop3_server.py` for command handling (USER, PASS, RETR). | Calls `src/mailbox/storage_manager.py` (read action) to retrieve specific messages requested by the client. |

### B. Client Workflow (The GUI Actions)

#### Workflow 1: Sending Mail (Compose Action)

1.  **View:** `src/client/compose_email.py` collects user data.
2.  **Controller:** `src/client/run_client.py`/`user_agent.py` validates the input.
3.  **Network:** Controller calls `src/smtp/smtp_client.py`.
4.  **Transport:** `smtp_client.py` establishes connection using `src/rdt/rdt_sender.py` and transmits the SMTP sequence over Port 25.
5.  **Status:** The Controller updates the View with success/failure feedback.

#### Workflow 2: Checking Mail (Inbox View)

1.  **Controller:** `src/client/run_client.py` initiates connection upon user request.
2.  **Network:** Controller calls `src/pop3/pop3_client.py`.
3.  **Protocol:** `pop3_client.py` sends `USER`, `PASS`, and `LIST` commands over Port 110.
4.  **Model Update:** The retrieved list of message headers is stored in the Model (`user_agent.py`).
5.  **View:** `src/client/inbox_viewer.py` reads the Model state and renders the updated inbox list to the user.