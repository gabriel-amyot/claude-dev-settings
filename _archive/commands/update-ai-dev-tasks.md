# Update AI Dev Tasks Command

This command downloads the latest workflow files from the ai-dev-tasks repository.

Run these commands to update:
```bash
# Create directory if it doesn't exist
mkdir -p ~/.claude/library/process

# Download the specific workflow files we need
curl -s https://raw.githubusercontent.com/snarktank/ai-dev-tasks/main/create-prd.md -o ~/.claude/library/process/product-requirements-document-creation.md
curl -s https://raw.githubusercontent.com/snarktank/ai-dev-tasks/main/generate-tasks.md -o ~/.claude/library/process/task-generation-from-prd-two-phase.md
curl -s https://raw.githubusercontent.com/snarktank/ai-dev-tasks/main/process-task-list.md -o ~/.claude/library/process/task-list-management-progress-protocol.md

echo "✅ AI dev tasks workflow files updated successfully"
```

This ensures you always have the most current version of the structured development workflow files without needing the full repository.