#!/usr/bin/env bash

# Project root
ROOT_DIR="."

# Helper function to create directories and files
create_dir() {
    mkdir -p "$1"
}

create_file() {
    touch "$1"
}

echo "Creating project structure for $ROOT_DIR..."

# ----------------------
# src/
# ----------------------
SRC_DIR="$ROOT_DIR/src"

# common
COMMON_DIR="$SRC_DIR/common"
create_dir "$COMMON_DIR"
for f in config.py logger.py utils.py exceptions.py; do
    create_file "$COMMON_DIR/$f"
done

# rdt
RDT_DIR="$SRC_DIR/rdt"
create_dir "$RDT_DIR"
for f in __init__.py rdt_packet.py rdt_sender.py rdt_receiver.py checksum.py states.py; do
    create_file "$RDT_DIR/$f"
done

# smtp
SMTP_DIR="$SRC_DIR/smtp"
create_dir "$SMTP_DIR"
for f in smtp_client.py smtp_server.py smtp_parser.py smtp_commands.py; do
    create_file "$SMTP_DIR/$f"
done

# pop3
POP3_DIR="$SRC_DIR/pop3"
create_dir "$POP3_DIR"
for f in pop3_client.py pop3_server.py pop3_parser.py pop3_responses.py; do
    create_file "$POP3_DIR/$f"
done

# mailbox
MAILBOX_DIR="$SRC_DIR/mailbox"
create_dir "$MAILBOX_DIR"
for f in storage_manager.py mailbox_reader.py mailbox_writer.py; do
    create_file "$MAILBOX_DIR/$f"
done

# server
SERVER_DIR="$SRC_DIR/server"
create_dir "$SERVER_DIR"
for f in server_daemon.py run_smtp_server.py run_pop3_server.py thread_manager.py; do
    create_file "$SERVER_DIR/$f"
done

# client
CLIENT_DIR="$SRC_DIR/client"
create_dir "$CLIENT_DIR"
for f in user_agent.py compose_email.py inbox_viewer.py run_client.py; do
    create_file "$CLIENT_DIR/$f"
done

# main.py
create_file "$SRC_DIR/main.py"

# ----------------------
# tests/
# ----------------------
TESTS_DIR="$ROOT_DIR/tests"
create_dir "$TESTS_DIR"

# test_rdt
TEST_RDT_DIR="$TESTS_DIR/test_rdt"
create_dir "$TEST_RDT_DIR"
for f in test_handshake.py test_retransmission.py test_checksum.py test_packet_structure.py; do
    create_file "$TEST_RDT_DIR/$f"
done

# test_smtp
TEST_SMTP_DIR="$TESTS_DIR/test_smtp"
create_dir "$TEST_SMTP_DIR"
for f in test_smtp_client.py test_smtp_server.py test_smtp_integration.py; do
    create_file "$TEST_SMTP_DIR/$f"
done

# test_pop3
TEST_POP3_DIR="$TESTS_DIR/test_pop3"
create_dir "$TEST_POP3_DIR"
for f in test_pop3_client.py test_pop3_server.py test_pop3_integration.py; do
    create_file "$TEST_POP3_DIR/$f"
done

# conftest.py
create_file "$TESTS_DIR/conftest.py"

# ----------------------
# docs/
# ----------------------
DOCS_DIR="$ROOT_DIR/docs"
SPHINX_DIR="$DOCS_DIR/sphinx/source"
DIAGRAMS_DIR="$DOCS_DIR/sphinx/diagrams"
REPORT_DIR="$DOCS_DIR/sphinx/report"

create_dir "$SPHINX_DIR"
for f in conf.py index.rst architecture.rst rdt_protocol.rst smtp_flow.rst pop3_flow.rst api_reference.rst; do
    create_file "$SPHINX_DIR/$f"
done

create_dir "$DIAGRAMS_DIR"
for f in c4_component.dsl c4_sequences.dsl c4_rdt_struct.dsl smtp_sequence.png pop3_sequence.png rdt_handshake.png; do
    create_file "$DIAGRAMS_DIR/$f"
done

create_dir "$REPORT_DIR"
for f in term_project_report.pdf term_project_report.tex; do
    create_file "$REPORT_DIR/$f"
done

create_file "$DOCS_DIR/sphinx/Makefile"
create_file "$DOCS_DIR/sphinx/README_docs.md"

# ----------------------
# database/
# ----------------------
DB_DIR="$ROOT_DIR/database/mailboxes"
create_dir "$DB_DIR/user1"
create_dir "$DB_DIR/user2"

create_file "$DB_DIR/user1/email_0001.txt"
create_file "$DB_DIR/user1/email_0002.txt"
create_file "$DB_DIR/user1/metadata.json"

create_file "$DB_DIR/user2/email_0001.txt"
create_file "$DB_DIR/user2/metadata.json"

create_file "$ROOT_DIR/database/index.json"

# ----------------------
# root-level files
# ----------------------
for f in requirements.txt revisions.txt README.md LICENSE; do
    create_file "$ROOT_DIR/$f"
done

echo "Project structure created successfully!"
