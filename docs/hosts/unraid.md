# Unraid

## Install 1Password CLI:

Add this to `/boot/config/go`:
```bash
# ARCH="amd64" && \
#   wget "https://cache.agilebits.com/dist/1P/op2/pkg/v2.32.1/op_linux_${ARCH}_v2.32.1.zip" -O /boot/config/extra/op.zip

# https://developer.1password.com/docs/cli/get-started/
unzip -d /tmp/op /boot/config/extra/op.zip && \
  mv /tmp/op/op /usr/local/bin/ && \
  rm -r /tmp/op && \
  sudo groupadd -f onepassword-cli && \
  sudo chgrp onepassword-cli /usr/local/bin/op && \
  sudo chmod g+s /usr/local/bin/op
```