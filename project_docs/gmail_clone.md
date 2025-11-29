Context:
- You are given an existing project called @email-network-service. It already implements SMTP, POP3, local file-based mailboxes, and RDT (reliable data transfer).
- You're also given an existing initial design document for gmail design doc called @doc_initial.md . 
- We want to add a desktop Gmail-style PySide6 frontend to this system.
- IMPORTANT: When you reference ANY existing file or directory from the repository tree, you MUST prefix it with "@".  
  Example: @src/smtp/smtp_client.py, @database/mailboxes/user1/metadata.json, @docs/sphinx/source/index.rst

Repository Tree (all file references MUST be prefixed with "@"):
```
smtp-protocol-implementation  on  gmail_clone ❯  tree ./email-network-service/
./email-network-service/
├── LICENSE
├── README.md
├── database
│   ├── index.json
│   └── mailboxes
│       ├── user1
│       │   ├── email_0001.txt
│       │   ├── email_0002.txt
│       │   └── metadata.json
│       └── user2
│           ├── email_0001.txt
│           └── metadata.json
├── docs
│   └── sphinx
│       ├── Makefile
│       ├── README_docs.md
│       ├── diagrams
│       │   ├── c4_component.dsl
│       │   ├── c4_rdt_struct.dsl
│       │   ├── c4_sequences.dsl
│       │   ├── pop3_sequence.png
│       │   ├── rdt_handshake.png
│       │   └── smtp_sequence.png
│       ├── report
│       │   ├── term_project_report.pdf
│       │   └── term_project_report.tex
│       └── source
│           ├── api_reference.rst
│           ├── architecture.rst
│           ├── conf.py
│           ├── index.rst
│           ├── pop3_flow.rst
│           ├── rdt_protocol.rst
│           └── smtp_flow.rst
├── requirements.txt
├── revisions.txt
├── src
│   ├── client
│   │   ├── compose_email.py
│   │   ├── inbox_viewer.py
│   │   ├── run_client.py
│   │   └── user_agent.py
│   ├── common
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   ├── logger.py
│   │   └── utils.py
│   ├── mailbox
│   │   ├── mailbox_reader.py
│   │   ├── mailbox_writer.py
│   │   └── storage_manager.py
│   ├── main.py
│   ├── pop3
│   │   ├── pop3_client.py
│   │   ├── pop3_parser.py
│   │   ├── pop3_responses.py
│   │   └── pop3_server.py
│   ├── rdt
│   │   ├── __init__.py
│   │   ├── checksum.py
│   │   ├── rdt_packet.py
│   │   ├── rdt_receiver.py
│   │   ├── rdt_sender.py
│   │   ├── rdt_test.py
│   │   ├── rdt_util.py
│   │   └── states.py
│   ├── server
│   │   ├── run_pop3_server.py
│   │   ├── run_smtp_server.py
│   │   ├── server_daemon.py
│   │   └── thread_manager.py
│   └── smtp
│       ├── smtp_client.py
│       ├── smtp_commands.py
│       ├── smtp_parser.py
│       └── smtp_server.py
└── tests
    ├── conftest.py
    ├── test_pop3
    │   ├── test_pop3_client.py
    │   ├── test_pop3_integration.py
    │   └── test_pop3_server.py
    ├── test_rdt
    │   ├── test_checksum.py
    │   ├── test_handshake.py
    │   ├── test_packet_structure.py
    │   └── test_retransmission.py
    └── test_smtp
        ├── test_smtp_client.py
        ├── test_smtp_integration.py
        └── test_smtp_server.py

22 directories, 70 files
```

Goal:
Generate a **finalized Software Design Document (SDD)** for adding a **PySide6 Gmail clone frontend** to the project. The SDD must be comprehensive, implementation-ready, and fully compatible with the project’s architecture, coding standards, and documentation pipeline.

OUTPUT REQUIREMENTS:
Produce a **single Markdown Software Design Document**, named:

    sdd/frontend_gmail_clone.md

The SDD must include:

1. Executive Summary  
2. Goals & Non-Goals  
3. UX / Wireframes  
4. Architecture Overview (C4-style: System, Container, Component)  
5. UI Components & Responsibilities  
6. Data Models  
7. Controllers & Signal Flows  
8. Integration Points — using "@" for files, e.g. @src/mailbox/storage_manager.py  
9. Complete QSS theme using provided color scheme  
10. Detailed Sequence Diagrams (Mermaid)  
11. Component Diagrams (Mermaid)  
12. Example PySide6 Code Snippets  
13. Tests & QA Strategy  
14. Performance & Security  
15. Accessibility & Keyboard Shortcuts  
16. Packaging & Distribution (PyInstaller)  
17. CI/CD Recommendations (GitHub Actions)  
18. Milestones, Tasks, and Estimates  
19. Migration Notes  
20. Appendices

You must generate:
- **Mermaid diagrams** for sequences and components  
- **Wireframes** (ASCII or Mermaid)  
- **QSS theme file**  
- **Concrete file-change plan** including:  
  - new files and their exact paths  
  - modified files and exact paths (always using "@")  
- **Code snippets** for:  
  - PySide6 MainWindow  
  - EmailListModel (QAbstractListModel)  
  - MessageView  
  - Composer window  
  - Controller methods  

CONSTRAINTS:
- All references to existing repo files **must use "@" prefix**.  
- New files should NOT use "@" prefix — only existing files do.  
- Use PySide6 only (Qt for Python).  
- Type hints required.  
- PEP8 compliance.  
- Integrate with mailbox format located under @database/mailboxes/...  
- Frontend entry point should be a new file such as:  
      src/client/run_frontend.py  
- Must include integration details for existing components in:  
      @src/smtp/*  
      @src/pop3/*  
      @src/mailbox/*  
      @src/client/*  
- Document exactly how the frontend calls into:  
      @src/mailbox/storage_manager.py  
      @src/smtp/smtp_client.py  
      @src/pop3/pop3_client.py  

STYLE & QUALITY:
- Highly technical, senior-engineer tone.  
- Precise, actionable, unambiguous.  
- SDD must be implementation-ready.  

ACCEPTANCE CRITERIA:
A developer reading the generated SDD must be able to:  
- Implement the PySide6 UI skeleton  
- Load mailbox data from @database/mailboxes/<user>/  
- Render messages using QWebEngineView  
- Compose and send mail using @src/smtp/smtp_client.py  
- Execute integration tests using the existing test infrastructure under @tests/  
- Integrate the new frontend without modifying backend behavior  
- Follow a clear milestone plan for completing the frontend  

END OF PROMPT
