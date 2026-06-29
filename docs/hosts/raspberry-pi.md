# Raspberry Pi

Host-specific setup notes for the Raspberry Pis. See the topology diagram in
[../../README.md](../../README.md) for which stacks run on which Pi.

## Mount a CIFS/SMB network share

Mounts an SMB share from a NAS at `/mnt/share`, persistent across reboots.
Credentials live in a root-only file so the password stays out of `/etc/fstab`.

Replace the placeholders before running:

- `NAS_HOST` — the NAS hostname or IP (e.g. `nas.local` or `192.168.1.10`)
- `SHARE_PATH` — the share/path to mount (e.g. `Media/data`)
- `SMB_USERNAME` / `SMB_PASSWORD` — credentials for the share

```bash
sudo apt update && sudo apt install -y cifs-utils
sudo mkdir -p /mnt/share

# Store credentials in a root-only file (keeps the password out of /etc/fstab).
sudo tee /root/.smb-creds >/dev/null <<'EOF'
username=SMB_USERNAME
password=SMB_PASSWORD
EOF
sudo chmod 600 /root/.smb-creds

# Test the mount before committing it to fstab.
sudo mount -t cifs //NAS_HOST/SHARE_PATH /mnt/share \
  -o credentials=/root/.smb-creds,uid=1000,gid=1000,iocharset=utf8,vers=3.0,nofail

# Confirm you can see the files.
ls /mnt/share
```

`uid=1000,gid=1000` is the `pi` user, so it can read/write without `sudo`. If
`vers=3.0` fails, try `vers=3.1.1`.

Once the test mount works, make it persistent by adding this one line to
`/etc/fstab`:

```
//NAS_HOST/SHARE_PATH  /mnt/share  cifs  credentials=/root/.smb-creds,uid=1000,gid=1000,iocharset=utf8,vers=3.0,_netdev,nofail  0  0
```

`_netdev` waits for the network before mounting and `nofail` lets the Pi boot
even if the share is unreachable — both matter on a headless Pi.

Then verify the fstab entry parses and mounts cleanly:

```bash
sudo umount /mnt/share && sudo mount -a && df -h /mnt/share
```
