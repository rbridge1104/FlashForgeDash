# FlashForge Dashboard

> Web-based control panel for FlashForge 3D printers with Google OAuth authentication, real-time monitoring, and remote control capabilities.

## 🚀 Quick Start

```bash
# Pull the image
docker pull rbridge1104/flashforge-dash:latest

# Run with docker-compose (recommended)
curl -O https://raw.githubusercontent.com/rbridge1104/FlashForgeDash/main/docker-compose.yml
curl -O https://raw.githubusercontent.com/rbridge1104/FlashForgeDash/main/.env.example
curl -O https://raw.githubusercontent.com/rbridge1104/FlashForgeDash/main/config.yaml.example

mv .env.example .env
mv config.yaml.example config.yaml

# Edit .env and config.yaml with your settings
docker-compose up -d
```

## ✨ Features

- **Secure Authentication** - Google OAuth 2.0 with admin approval system
- **Real-time Monitoring** - Live temperature, progress, and status updates
- **Remote Control** - Start prints, adjust temperatures, control fans
- **Camera Streaming** - Live MJPEG camera feed from printer
- **File Management** - Upload and manage G-code files
- **Smart Status Detection** - Preheating, printing, cooling, and more

## 📋 Requirements

- Docker Desktop or Docker Engine
- FlashForge Adventurer 3 (or compatible) printer
- Google Cloud OAuth credentials ([setup guide](https://github.com/rbridge1104/FlashForgeDash#oauth-setup))
- Printer IP address on your network

## ⚙️ Configuration

### Required Environment Variables

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
SESSION_SECRET_KEY=generate-with-openssl-rand-hex-32
ADMIN_EMAILS=your-email@gmail.com
```

### Printer Configuration

Edit `config.yaml`:
```yaml
printer:
  ip_address: "192.168.1.200"  # Your printer's IP
  port: 8899
  poll_interval: 5
```

## 🔧 Usage

### With Docker Compose (Recommended)

```bash
docker-compose up -d        # Start
docker-compose logs -f      # View logs
docker-compose restart      # Restart
docker-compose down         # Stop
```

### Standalone Docker

```bash
docker run -d \
  --name flashforge-dashboard \
  -p 8000:8000 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/data:/app/data \
  -e GOOGLE_CLIENT_ID=your-id \
  -e GOOGLE_CLIENT_SECRET=your-secret \
  -e SESSION_SECRET_KEY=your-key \
  -e ADMIN_EMAILS=your-email@gmail.com \
  rbridge1104/flashforge-dash:latest
```

### Access Dashboard

Open browser: **http://localhost:8000**

## 🏷️ Available Tags

- `latest` - Most recent stable release
- `1.3.0` - Specific version with Docker support

## 📚 Documentation

- **Full Documentation**: [GitHub Repository](https://github.com/rbridge1104/FlashForgeDash)
- **Quick Start Guide**: [DOCKER_QUICKSTART.md](https://github.com/rbridge1104/FlashForgeDash/blob/main/DOCKER_QUICKSTART.md)
- **OAuth Setup**: [README.md#oauth-setup](https://github.com/rbridge1104/FlashForgeDash#oauth-setup)

## 🛠️ Troubleshooting

**Can't connect to printer:**
- Verify printer IP in `config.yaml`
- Ensure printer is on same network as Docker host
- Check printer is powered on

**OAuth errors:**
- Verify credentials in `.env` file
- Check redirect URI in Google Cloud Console: `http://localhost:8000/auth/callback`
- Ensure your email is in `ADMIN_EMAILS`

**Port already in use:**
```yaml
ports:
  - "8001:8000"  # Use different port
```

## 🔐 Security

- Uses non-root user inside container
- OAuth 2.0 authentication required
- Admin approval system for new users
- Session-based security with secret key

## 📊 Health Check

The container includes automatic health monitoring:
```bash
docker ps  # Check health status
docker-compose logs  # View health check logs
```

## 🤝 Contributing

Issues and pull requests welcome at [GitHub](https://github.com/rbridge1104/FlashForgeDash)

## 📄 License

MIT License - See [LICENSE](https://github.com/rbridge1104/FlashForgeDash/blob/main/LICENSE) for details

---

**Made with ❤️ for the FlashForge community**
