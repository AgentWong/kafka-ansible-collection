# Development Guide

## Prerequisites

- Python 3.11+
- Docker Desktop (for Molecule testing)
- Git

## Environment Setup

### Clone Repository

```bash
git clone https://github.com/AgentWong/kafka-ansible-collection.git
cd kafka-ansible-collection
```

### Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate   # Windows
```

### Install Dependencies

```bash
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
```

## Project Structure

```
kafka-ansible-collection/
├── containers/          # Custom Docker images for testing
├── docs/               # Documentation
├── extensions/molecule/ # Molecule test scenarios
├── inventory/          # Sample inventory files
├── playbooks/          # Deployment playbooks
├── plugins/            # Custom Ansible plugins
└── roles/              # Ansible roles
    ├── common/         # Base system configuration
    ├── java/           # Java installation
    ├── kafka/          # Kafka broker deployment
    ├── rootca/         # TLS certificate generation
    └── zookeeper/      # ZooKeeper deployment
```

## Molecule Testing

### Running Tests

```bash
# Navigate to molecule scenario
cd extensions/molecule/default

# Run full test suite
molecule test

# Run individual stages
molecule create    # Create containers
molecule prepare   # Run prepare playbook
molecule converge  # Run main playbook
molecule verify    # Run verification tests
molecule destroy   # Destroy containers
```

### Development Workflow

```bash
# Quick iteration (no cleanup)
molecule converge

# Check idempotence
molecule converge && molecule converge

# Verify after changes
molecule verify

# Full reset
molecule destroy && molecule converge
```

### Debugging

```bash
# Login to container
molecule login -h zk1

# Run with verbose output
molecule converge -- -vvv

# Check container status
docker ps
```

## Role Development

### Creating a New Role

```bash
cd roles
ansible-galaxy role init new_role_name
```

### Role Structure

```
roles/new_role/
├── defaults/main.yml    # Default variables
├── handlers/main.yml    # Event handlers
├── meta/main.yml        # Role metadata
├── tasks/               # Task files
│   ├── main.yml        # Entry point
│   ├── install.yml     # Installation tasks
│   ├── configure.yml   # Configuration tasks
│   └── service.yml     # Service management
├── templates/           # Jinja2 templates
└── vars/               # OS-specific variables
    ├── RedHat.yml
    └── Debian.yml
```

### Best Practices

1. **Use handlers** for service restarts
2. **Tag tasks** for selective execution
3. **Use OS-specific variables** for packages
4. **Validate inputs** with assert tasks
5. **Document variables** in defaults/main.yml

## AI-Assisted Development Workflow

This project demonstrates AI-assisted development with GitHub Copilot.

### Iterative Development Process

1. **Define requirements** in implementation plan
2. **Generate initial code** with AI assistance
3. **Test with Molecule** to find issues
4. **Debug with AI** using error context
5. **Refine and iterate** until tests pass

### Debugging with AI

When encountering errors:

1. Copy the full error message
2. Include relevant context (task, variables)
3. Ask AI for analysis and suggestions
4. Apply fixes and retest

### Example Debugging Session

```
Error: FAILED - {"msg": "Could not find the requested service zookeeper"}

Context:
- Running on Rocky Linux 9 container
- ZooKeeper role just completed
- Service should be created by systemd unit file

AI Analysis: The systemd daemon may not have reloaded after creating the unit file.

Fix: Add `systemctl daemon-reload` before starting service.
```

## Contributing

### Commit Guidelines

- Use conventional commits
- Include issue/ticket references
- Write descriptive commit messages

### Pull Request Process

1. Create feature branch from `develop`
2. Implement changes with tests
3. Run `molecule test` successfully
4. Submit PR with description
5. Address review feedback
