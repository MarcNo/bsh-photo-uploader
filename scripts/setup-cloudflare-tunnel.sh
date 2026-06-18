#!/usr/bin/env bash
# Automates the "Cloudflare Tunnel Setup" steps from README.md:
# install cloudflared, authenticate, create the tunnel, write its config,
# add the DNS route, and register it as a systemd service.
set -euo pipefail

TUNNEL_NAME="${TUNNEL_NAME:-bsh-picnic}"
HOSTNAME_FQDN="${HOSTNAME_FQDN:-bull.nozell.com}"
SERVICE_URL="${SERVICE_URL:-http://localhost:80}"
CLOUDFLARED_DIR="$HOME/.cloudflared"

require_cmd() { command -v "$1" >/dev/null 2>&1; }

install_cloudflared() {
  if require_cmd cloudflared; then
    echo "cloudflared already installed: $(cloudflared --version)"
    return
  fi

  echo "Installing cloudflared..."
  if require_cmd dnf; then
    sudo dnf install -y https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-x86_64.rpm
  else
    curl -fL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared
    sudo install -m 0755 /tmp/cloudflared /usr/local/bin/cloudflared
    rm -f /tmp/cloudflared
  fi
}

authenticate() {
  if [[ -f "$CLOUDFLARED_DIR/cert.pem" ]]; then
    echo "Already authenticated ($CLOUDFLARED_DIR/cert.pem found)."
    return
  fi
  echo "Opening browser for Cloudflare login — select the zone for $HOSTNAME_FQDN..."
  cloudflared tunnel login
}

create_tunnel() {
  TUNNEL_UUID=$(cloudflared tunnel list --output json \
    | python3 -c "import json,sys; data=json.load(sys.stdin); m=[t for t in data if t['name']=='$TUNNEL_NAME']; print(m[0]['id'] if m else '')")

  if [[ -n "$TUNNEL_UUID" ]]; then
    echo "Tunnel '$TUNNEL_NAME' already exists (id $TUNNEL_UUID)."
  else
    echo "Creating tunnel '$TUNNEL_NAME'..."
    cloudflared tunnel create "$TUNNEL_NAME"
    TUNNEL_UUID=$(cloudflared tunnel list --output json \
      | python3 -c "import json,sys; data=json.load(sys.stdin); print(next(t['id'] for t in data if t['name']=='$TUNNEL_NAME'))")
  fi
  echo "Tunnel UUID: $TUNNEL_UUID"
}

write_config() {
  mkdir -p "$CLOUDFLARED_DIR"
  cat > "$CLOUDFLARED_DIR/config.yml" <<EOF
tunnel: $TUNNEL_NAME
credentials-file: $CLOUDFLARED_DIR/$TUNNEL_UUID.json

ingress:
  - hostname: $HOSTNAME_FQDN
    service: $SERVICE_URL
  - service: http_status:404
EOF
  echo "Wrote $CLOUDFLARED_DIR/config.yml"
}

route_dns() {
  echo "Routing DNS: $HOSTNAME_FQDN -> tunnel $TUNNEL_NAME"
  cloudflared tunnel route dns "$TUNNEL_NAME" "$HOSTNAME_FQDN" || \
    echo "  (route may already exist — continuing)"
}

install_service() {
  echo "Installing cloudflared as a systemd service..."
  sudo cloudflared service install
  sudo systemctl enable --now cloudflared
}

verify() {
  echo "Waiting a few seconds for the tunnel to come up..."
  sleep 5
  if curl -fsS -o /dev/null "https://$HOSTNAME_FQDN"; then
    echo "Verified: https://$HOSTNAME_FQDN is reachable."
  else
    echo "Could not verify yet — DNS/tunnel may still be propagating. Check with:"
    echo "  sudo systemctl status cloudflared"
    echo "  curl -I https://$HOSTNAME_FQDN"
  fi
}

main() {
  install_cloudflared
  authenticate
  create_tunnel
  write_config
  route_dns
  install_service
  verify
  echo
  echo "Done: $HOSTNAME_FQDN -> tunnel '$TUNNEL_NAME' -> $SERVICE_URL"
}

main "$@"
