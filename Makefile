# -----------------------------
# Simulation Defaults (can be overridden)
# -----------------------------
NUM_USERS ?= 2
NUM_EMAILS ?= 1
CONCURRENCY ?= 10
DELAY ?= 0.2
MESSAGE_SIZE ?= 200


# Regenerate requirements.txt
freeze:
	python3 -m pip freeze > requirements.txt
	@echo "Updated requirements.txt"

# Run the program
run:
	python3 -m email-network-service.src.simulation \
		--num_users $(NUM_USERS) \
		--num_emails $(NUM_EMAILS) \
		--concurrency $(CONCURRENCY) \
		--delay_between_sends $(DELAY) \
		--message_size $(MESSAGE_SIZE)

clean:
	@echo "=== Cleaning Email Database ==="
	@find email-network-service/database/mailboxes -type f -delete
	@find email-network-service/database/mailboxes -mindepth 1 -type d -exec rm -rf {} +
	@find email-network-service/database/temp -mindepth 1 -exec rm -rf {} +
	@rm -f email-network-service/database/users.json
	@echo "Recreating empty mailbox directories and metadata.json files..."
	@mkdir -p email-network-service/database/mailboxes
	@echo "Database cleared and reset."
	@echo "=== Removing __pycache__ directories ==="
	@find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	@echo "Removed all __pycache__ directories."
	@echo "=== Cleaning Completed ==="

format:
	python3 -m black email-network-service/src 
	@echo "Code formatted with black."


.PHONY: freeze run clean format
