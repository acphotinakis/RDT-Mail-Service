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


# Clean build output and venv
clean:
	@echo "Clearing email database..."
	@find email-network-service/database/mailboxes -type f -name "*.msg" -delete
	@find email-network-service/database/mailboxes -type f -name "metadata.json" -delete
	@find email-network-service/database/temp -mindepth 1 -delete
	@rm -f email-network-service/database/users.json
	@echo "Recreating metadata directories..."
	@find email-network-service/database/mailboxes -type d -exec touch {}/metadata.json \;
	@echo "Database cleared and reset."
	@echo "Cleaned."

format:
	python3 -m black email-network-service/src 
	@echo "Code formatted with black."


.PHONY: freeze run clean format
