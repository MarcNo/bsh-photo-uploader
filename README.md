# 📸 BSH Picnic Photo Uploader

**159th Annual William Bull & Sarah Wells Family Picnic**

A self-hosted photo and video collection web app designed for non-technical family members. Attendees scan a QR code, enter an event code, give their name, and upload photos/videos directly from their phones.

---

## Features

| Feature | Details |
|---|---|
| Landing page counter | Tracks every visit to the site |
| Event code gate | Shared codeword `WELLSBULL159` keeps the upload private |
| Name-based folders | Files stored under `/DATA/bsh/picnic-images/<firstname_lastname>/` |
| Drag-and-drop upload | Works on phones and desktops |
| Title & caption editing | Users annotate their uploads inline |
| Admin dashboard | Password-protected stats + per-user gallery |
| Counters | Landing views · code logins · total uploads · per-user uploads |
| Docker | Single `docker compose up` deploys the whole stack |

---

## Quick Start (Fedora 44)

### 1. Prerequisites

```bash
sudo dnf install -y docker docker-compose-plugin git python3
sudo systemctl enable --now docker
sudo usermod -aG docker $USER   # log out and back in
```

### 2. Clone & configure

```bash
git clone https://github.com/MarcNo/bsh-photo-uploader.git
cd bsh-photo-uploader

cp .env.example .env
# Edit .env — at minimum change SECRET_KEY and ADMIN_PASSWORD
nano .env
```

### 3. Create the data directory

```bash
sudo mkdir -p /DATA/bsh/picnic-images
sudo chown -R $USER:$USER /DATA/bsh
```

### 4. Launch

```bash
docker compose up -d --build
```

The app is now running on `http://localhost:5000` (internal) and on port 80 via nginx.

---

## Cloudflare Tunnel Setup (Internet Access)

Cloudflare Tunnel lets you expose the app at `http://bull.nozell.com` without opening firewall ports.

### Install cloudflared

```bash
# Fedora / RHEL
sudo dnf install -y https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-x86_64.rpm
```

Or download the binary directly:

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
     -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared
```

### Authenticate

```bash
cloudflared tunnel login
```

This opens a browser — select the `nozell.com` zone.

### Create the tunnel

```bash
cloudflared tunnel create bsh-picnic
```

Note the tunnel UUID from the output.

### Configure the tunnel

```bash
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: bsh-picnic
credentials-file: /home/YOUR_USER/.cloudflared/<TUNNEL-UUID>.json

ingress:
  - hostname: bull.nozell.com
    service: http://localhost:80
  - service: http_status:404
EOF
```

Replace `YOUR_USER` and `<TUNNEL-UUID>` with the real values.

### Add DNS record

```bash
cloudflared tunnel route dns bsh-picnic bull.nozell.com
```

### Run as a systemd service

```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

Verify it's working:

```bash
curl -I https://bull.nozell.com
```

---

## Generate the QR Code

The QR code links attendees to `http://bull.nozell.com` and shows the event code to enter.

```bash
pip install "qrcode[pil]" Pillow
python generate_qr.py
```

Output: `qr_code.png` — print this at A5 or A4 size and place it at the welcome table.

---

## Admin Interface

Visit `http://bull.nozell.com/admin` (or `/admin/login`) and enter the `ADMIN_PASSWORD` from your `.env`.

The dashboard shows:
- Landing page views
- How many times the event code was entered
- Total registered attendees
- Total uploads
- Per-user upload counts
- Recent uploads with links to view the media

---

## File Storage

```
/DATA/bsh/
├── picnic.db                    ← SQLite database
└── picnic-images/
    ├── alice_johnson/
    │   ├── 3f8a...jpg
    │   └── 9c2d...mp4
    └── bob_wells/
        └── 1a4b...png
```

Files are stored with UUID-based names to avoid conflicts; original names are recorded in the database.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | (required) | Flask session signing key |
| `EVENT_CODE` | `WELLSBULL159` | Shared codeword for entry |
| `ADMIN_PASSWORD` | `picnicadmin2025` | Admin dashboard password |
| `UPLOAD_BASE` | `/DATA/bsh/picnic-images` | Where uploads are stored |
| `DB_PATH` | `/DATA/bsh/picnic.db` | SQLite database path |

---

## Maintenance

```bash
# View logs
docker compose logs -f app

# Restart
docker compose restart

# Stop
docker compose down

# Backup data
tar czf bsh-picnic-backup-$(date +%Y%m%d).tar.gz /DATA/bsh/
```

---

## License

GPL-3.0 — see [LICENSE](LICENSE).
=======
# bsh-photo-uploader
Photo uploader for Bull Stone House picnic
