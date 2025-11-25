
# Implementation Phases: PySide6 Gmail Clone Frontend

This document breaks down the development of the PySide6 Gmail Clone frontend into a series of prioritized phases. Each phase builds upon the last, delivering functional increments of the final application. This approach allows for iterative development, testing, and feedback.

---

## Phase 1: Core UI and Read-Only Functionality (Highest Priority)

**Goal:** To create a visible, read-only client that can successfully load and display existing emails from the local user mailbox. This provides the foundational skeleton of the application.

### Tasks:
1.  **Project Scaffolding:**
    - Create the new directory structure: `src/client/frontend/`, `src/client/frontend/assets/`, `tests/test_frontend/`.
    - Create empty Python files for `main_window.py`, `views.py`, `models.py`, `controllers.py`, and `wrappers.py`.
    - Add `PySide6` and `pytest-qt` to `@requirements.txt`.

2.  **UI Skeleton:**
    - Implement the basic `MainWindow` layout with placeholders for the email list and message view.
    - Create the `run_frontend.py` entry point.
    - Implement the dark QSS theme and load it on application startup.

3.  **Mailbox Integration (Read-Only):**
    - Implement the `StorageWrapper` with methods to list and read email files from `@database/mailboxes/`.
    - Implement the `EmailData` dataclass to parse and hold email content.
    - Implement the `EmailListModel` (`QAbstractListModel`) to manage the list of `EmailData` objects.

4.  **View Population:**
    - Connect the `EmailListModel` to the `EmailListView` to display the inbox.
    - Implement the controller logic (`on_email_selected`) to handle item selection in the list.
    - Implement the `MessageView` (`QWebEngineView`) to render the body of the selected email.
    - Ensure lazy loading is used: full email content is only read from disk upon selection.

---

## Phase 2: Email Composition and Sending

**Goal:** To enable users to write and send new emails. This phase delivers the first piece of interactive, network-dependent functionality.

### Tasks:
1.  **Compose UI:**
    - Implement the `ComposeWindow` `QDialog` with fields for "To", "Subject", and the message body.
    - Add a "Compose" button to the `MainWindow` and connect it to a controller method that opens the `ComposeWindow`.

2.  **SMTP Integration:**
    - Implement the `SMTPWrapper` to interface with the existing `@src/smtp/smtp_client.py`.
    - The wrapper should expose a simple `send_email(sender, recipients, message)` method.

3.  **Controller Logic:**
    - Implement the signal/slot connection for the "Send" button in the `ComposeWindow`.
    - The controller will take the data from the `ComposeWindow`, construct a valid email message, and pass it to the `SMTPWrapper`.
    - **Crucially, all network operations must be executed on a separate `QThread` to avoid freezing the UI.**
    - Provide user feedback via the `QStatusBar` (e.g., "Sending email...", "Email sent successfully.", "Failed to send email.").

---

## Phase 3: Email Fetching from Server

**Goal:** To allow users to retrieve new mail from the remote POP3 server and have it appear in their inbox.

### Tasks:
1.  **POP3 Integration:**
    - Implement the `POP3Wrapper` to interface with `@src/pop3/pop3_client.py`.
    - The wrapper should handle connection, authentication, listing messages, retrieving messages (`RETR`), and deleting them from the server (`DELE`).

2.  **Refresh Functionality:**
    - Add a "Refresh" button to the `MainWindow` UI.
    - Implement the `on_refresh_clicked` method in the `AppController`.

3.  **Controller & Model Updates:**
    - The controller will call the `POP3Wrapper` to fetch new emails. This must also run on a background `QThread`.
    - For each new email retrieved, the controller will use the `StorageWrapper` to save it to the local mailbox.
    - After saving, the controller will trigger a refresh of the `EmailListModel`, which will in turn update the `EmailListView` to show the new messages.
    - Update the status bar with the results of the refresh (e.g., "Fetched 3 new messages.").

---

## Phase 4: Testing, QA, and Packaging

**Goal:** To ensure the application is stable, reliable, and can be easily distributed to users.

### Tasks:
1.  **Unit Testing:**
    - Write `pytest-qt` tests for individual UI components and models.
    - Mock the backend wrappers to test controller logic in isolation (e.g., verify that `on_refresh_clicked` calls the `POP3Wrapper`).

2.  **Integration Testing:**
    - Create a test suite in `tests/test_frontend/` that starts the SMTP and POP3 servers.
    - Programmatically drive the UI using `qtbot` to simulate end-to-end user flows (e.g., click refresh, verify new email appears; click compose, send, and verify it's received).

3.  **Polish and Final Touches:**
    - Implement all keyboard shortcuts as defined in the SDD (`Ctrl+N`, `F5`, etc.).
    - Verify a logical tab order for accessibility.

4.  **Packaging:**
    - Create and configure a `.spec` file for PyInstaller.
    - Ensure all assets (like the `.qss` theme file) are correctly bundled.
    - Build the distributable application for the target platform and test it in a clean environment.

---

## Phase 5: Post-MVP Features (Future Work)

**Goal:** To plan for features that enhance the user experience beyond the core functionality. These are lower priority and can be implemented after a stable version is delivered.

### Tasks:
- **Reply/Reply-All/Forward:** Implement logic to pre-populate the `ComposeWindow` for replies.
- **Email Deletion:** Implement a "Trash" folder and the logic to move emails to it.
- **Additional Folders:** Add support for "Sent" and "Drafts" folders, including saving sent messages and drafts.
- **Settings Dialog:** Create a UI for configuring user account details, server addresses, and polling intervals.
- **Secure Credential Storage:** Integrate with a system keyring service (like `keyring`) to avoid storing passwords in memory or plain text.

---

## Implementation Progress Checklist

| Phase | Task | Status | Notes |
| :--- | :--- | :--- | :--- |
| **1** | Project Scaffolding | [ ] Not Started | |
| **1** | UI Skeleton & Theming | [ ] Not Started | |
| **1** | Mailbox Integration (Read-Only) | [ ] Not Started | |
| **1** | View Population & Selection | [ ] Not Started | |
| **2** | Compose Window UI | [ ] Not Started | |
| **2** | SMTP Wrapper Implementation | [ ] Not Started | |
| **2** | Controller Logic for Sending | [ ] Not Started | |
| **3** | POP3 Wrapper Implementation | [ ] Not Started | |
| **3** | Refresh Button & Controller Logic | [ ] Not Started | |
| **3** | Background Threading for Network | [ ] Not Started | |
| **4** | Unit Tests | [ ] Not Started | |
| **4** | Integration Tests | [ ] Not Started | |
| **4** | Keyboard Shortcuts & Accessibility | [ ] Not Started | |
| **4** | PyInstaller Packaging | [ ] Not Started | |
| **5** | Reply/Forward Functionality | [ ] Not Started | Post-MVP |
| **5** | Email Deletion (Trash) | [ ] Not Started | Post-MVP |
| **5** | Settings Dialog | [ ] Not Started | Post-MVP |
