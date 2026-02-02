# Docker Desktop Quick Start Guide

## 🚀 Get Running in 5 Minutes

### Prerequisites
- ✅ Docker Desktop installed and running
- ✅ Google Cloud OAuth credentials
- ✅ Your FlashForge printer IP address

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/FlashForgeDash.git
cd FlashForgeDash
```

### Step 2: Configure Environment
```bash
# Copy the example environment file
cp .env.example .env

# Copy the example config file
cp config.yaml.example config.yaml
```

**Edit `.env` file:**
```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret
SESSION_SECRET_KEY=run-openssl-rand-hex-32-to-generate
ADMIN_EMAILS=your-email@gmail.com
```

**Edit `config.yaml` file:**
```yaml
printer:
  ip_address: "192.168.1.200"  # ← Change to your printer's IP
```

### Step 3: Start with Docker Desktop

**Open PowerShell or Terminal and run:**
```bash
docker-compose up -d
```

You'll see:
```
✅ Creating network "flashforgedash_default"
✅ Creating flashforge-dashboard
```

### Step 4: Access Dashboard

Open browser: **http://localhost:8000**

### Common Commands

```bash
# View logs
docker-compose logs -f

# Stop the dashboard
docker-compose down

# Restart after config changes
docker-compose restart

# Rebuild after code updates
docker-compose up -d --build
```

### Docker Desktop GUI

You can also manage the container in Docker Desktop:
1. Open Docker Desktop
2. Go to **Containers** tab
3. See `flashforge-dashboard` running
4. Click to view logs, stop, or restart

### Troubleshooting

**Can't connect to printer:**
- Verify printer IP in `config.yaml`
- Make sure printer is on same network
- Check Docker network settings

**OAuth errors:**
- Verify `.env` has correct OAuth credentials
- Check redirect URI in Google Cloud Console: `http://localhost:8000/auth/callback`

**Port already in use:**
- Change port in `docker-compose.yml`:
  ```yaml
  ports:
    - "8001:8000"  # Use port 8001 instead
  ```

**Config not updating:**
- Restart container: `docker-compose restart`
- Or rebuild: `docker-compose up -d --build`

### Updating to Latest Version

```bash
git pull origin master
docker-compose up -d --build
```

### Completely Remove Everything

```bash
docker-compose down
docker rmi flashforge-dash:latest
rm -rf data/  # Remove user data (optional)
```

---

**That's it! Your FlashForge dashboard should now be running in Docker Desktop. 🎉**
