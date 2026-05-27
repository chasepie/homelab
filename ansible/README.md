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

| File                                      | Description                                                                                  |
| ----------------------------------------- | -------------------------------------------------------------------------------------------- |
| `configure-auto-upgrades.debian.yml`      | Enables `unattended-upgrades` on Debian/Ubuntu. The distro-default policy in `50unattended-upgrades` applies security updates only. |
| `configure-auto-upgrades.redhat.yml`      | Enables `dnf-automatic` on RHEL/Fedora.                                                      |
| `update-packages.debian.yml`              | Updates packages via apt and reboots if required on Debian/Ubuntu.                           |
| `update-packages.redhat.yml`              | Updates packages via dnf and reboots if required on RHEL/Fedora.                             |
| `update-docker-compose.yml`              | Pulls the latest image for a given `compose_dir` and restarts the service if updated.        |

### `configure-auto-upgrades.debian.yml`

| Task                        | Description                                                                                                                                                                                                                                    |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Install unattended-upgrades | Ensures the `unattended-upgrades` package is present.                                                                                                                                                                                          |
| Enable unattended-upgrades  | Writes `/etc/apt/apt.conf.d/20auto-upgrades` to enable daily package list refresh and daily automatic upgrades. The update policy (security-only by default) is controlled by the distro-provided `/etc/apt/apt.conf.d/50unattended-upgrades`. |

### `configure-auto-upgrades.redhat.yml`

| Task                                | Description                                                                                                                                         |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Install dnf-automatic and dnf-utils | Installs `dnf-automatic` (the auto-update daemon) and `dnf-utils` (provides `needs-restarting`, used by the reboot check in `update-packages.redhat.yml`). |
| Configure dnf-automatic             | Sets `apply_updates = yes` in `/etc/dnf/automatic.conf` so downloaded updates are applied automatically.                                            |
| Enable dnf-automatic timer          | Enables and starts the `dnf-automatic.timer` systemd timer so updates run on schedule.                                                              |

### `update-packages.debian.yml`

| Task                        | Description                                                                                       |
| --------------------------- | ------------------------------------------------------------------------------------------------- |
| Update packages             | Runs `apt-get dist-upgrade` with autoremove and autoclean.                                        |
| Check if reboot is required | Checks for `/var/run/reboot-required` written by the kernel/package post-install scripts.         |
| Reboot if required          | Reboots the host and waits for it to come back if the reboot flag file is present.                |

### `update-packages.redhat.yml`

| Task                        | Description                                                                                       |
| --------------------------- | ------------------------------------------------------------------------------------------------- |
| Update packages             | Runs `dnf upgrade` across all installed packages.                                                 |
| Check if reboot is required | Runs `needs-restarting -r` (exit code `1` = reboot needed, `0` = clean).                         |
| Reboot if required          | Reboots the host and waits for it to come back if `needs-restarting` signals a reboot is needed.  |
