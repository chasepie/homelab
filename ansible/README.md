# Ansible

Ansible playbooks for managing homelab servers.

## Inventory

Hosts are defined in `inventory/hosts.ini` (gitignored). Copy the example to get started:

```bash
cp inventory/hosts.ini.example inventory/hosts.ini
```

```ini
[servers]
server-01 ansible_host=server-01.local
server-02 ansible_host=server-02.local

[servers:vars]
ansible_user=your_user
ansible_python_interpreter=/usr/bin/python3
```

## Usage

Run a playbook from the `ansible/` directory:

```bash
ansible-playbook -i inventory/hosts.ini playbooks/<playbook>.yml
```

## Playbooks

### `update-servers.yml`

Updates all servers and restarts any Docker Compose services with newer images available.

```bash
ansible-playbook -i inventory/hosts.ini playbooks/update-servers.yml
```

## Tasks

Reusable task files in `tasks/` are included by playbooks rather than run directly.

| File                        | Description                                                                          |
| --------------------------- | ------------------------------------------------------------------------------------ |
| `update-packages.yml`       | Updates system packages via apt or dnf and reboots if required                       |
| `update-docker-compose.yml` | Pulls the latest image for a given `compose_dir` and restarts the service if updated |
