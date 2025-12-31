# 🌫️ QazAirbot - Kazakhstan Air Quality Telegram Bot

A production-ready Telegram bot that provides real-time air quality monitoring for Kazakhstan with 24-hour trend charts, smart subscriptions, and bilingual support (Russian/Kazakh).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

## ✨ Features

### Core Features
- 🔍 **Location-based air quality checks** - Send location to get nearest sensor data
- 📊 **24-hour trend charts** - Visual AQI history with color-coded zones
- 🔔 **Smart subscriptions** - Get notifications when air quality changes
- ⭐ **Favorite locations** - Save frequently checked places (Home, Office, etc.)
- 🗣️ **Bilingual support** - Russian & Kazakh languages
- 💡 **Health recommendations** - Actionable advice based on AQI levels
- 📍 **Geospatial queries** - PostGIS-powered nearest station finding

### Technical Features
- ⚡ **Redis caching** - 1-hour chart caching for 60x performance boost
- 🔄 **Automatic data sync** - Hourly updates from air.org.kz API
- 🗄️ **24-hour data retention** - Automatic cleanup to save storage
- 🚦 **Rate limiting** - 3 chart requests/minute per user to prevent abuse
- 📈 **Historical data tracking** - Store readings for trend analysis
- 🐳 **Docker deployment** - Production-ready containerized setup

## Tech Stack

- **Python 3.11+**
- **FastAPI**: Web server and webhook endpoint
- **aiogram 3.x**: Telegram Bot framework
- **PostgreSQL + PostGIS**: Geospatial database
- **SQLAlchemy (Async)**: ORM with async support
- **Redis**: Caching and state management
- **Docker & Docker Compose**: Containerization

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- Telegram Bot Token (get from [@BotFather](https://t.me/BotFather))

### 2. Setup Environment

```bash
# Clone or navigate to project
cd qazairbot

# Copy environment template
cp .env.example .env

# Edit .env and add your bot token
nano .env
```

Required environment variables:
```env
BOT_TOKEN=your_telegram_bot_token_here
WEBHOOK_URL=https://your-domain.com  # For production
```

### 3. Start Services

```bash
# Start all services (PostgreSQL, Redis, Bot)
docker-compose up -d

# View logs
docker-compose logs -f bot
```

### 4. Initialize Database

The database will be automatically initialized on first startup. The application will:
- Create all necessary tables
- Enable PostGIS extension
- Run initial data sync from air.org.kz API

### 5. Test Your Bot

1. Open Telegram and find your bot
2. Send `/start`
3. Select your language (🇰🇿 Қазақша or 🇷🇺 Русский)
4. Click "📍 Проверить воздух" / "📍 Ауаны тексеру"
5. Share your location
6. Receive air quality data!

## Development

### Local Development without Docker

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start PostgreSQL and Redis locally:
```bash
# PostgreSQL with PostGIS
docker run -d -p 5432:5432 \
  -e POSTGRES_DB=qazairbot \
  -e POSTGRES_USER=qazairbot_user \
  -e POSTGRES_PASSWORD=qazairbot_pass \
  postgis/postgis:15-3.3-alpine

# Redis
docker run -d -p 6379:6379 redis:7-alpine
```

3. Update `.env` with local database URLs:
```env
DATABASE_URL=postgresql+asyncpg://qazairbot_user:qazairbot_pass@localhost:5432/qazairbot
REDIS_URL=redis://localhost:6379/0
```

4. Run the application:
```bash
# For development (polling mode)
python -m app.main

# For production (webhook mode)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Project Structure

```
qazairbot/
├── app/
│   ├── bot/
│   │   ├── handlers/          # Message and callback handlers
│   │   ├── keyboards/         # Keyboard builders
│   │   └── middlewares/       # I18n and other middlewares
│   ├── core/
│   │   ├── config.py          # Application settings
│   │   └── locales.py         # RU/KK translations
│   ├── db/
│   │   ├── database.py        # Database connection
│   │   └── models.py          # SQLAlchemy models
│   ├── services/
│   │   ├── air_quality.py     # AQ business logic
│   │   ├── cache.py           # Redis cache manager
│   │   └── sync.py            # Background data sync
│   ├── utils/
│   │   └── air_quality.py     # AQI calculations
│   └── main.py                # FastAPI application
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## API Integration

The bot fetches data from Kazakhstan's official air quality API:
- **Endpoint**: `https://api.air.org.kz/api/airgradient/latest`
- **Rate Limit**: 100 requests/minute
- **Update Frequency**: Every 15 minutes

## Database Schema

### Users Table
- Stores user preferences (language, contact info)
- Indexed by user_id for fast lookups

### Air Quality Stations Table
- PostGIS geography column for geospatial queries
- Stores latest measurements (PM2.5, PM10, PM1, AQI)
- Updated every 15 minutes

### User Queries Table
- Analytics log of user requests
- Tracks location queries and nearest stations

## Localization

All user-facing text is defined in `app/core/locales.py`:
- **Russian (ru)**: Default language
- **Kazakh (kk)**: Full translation coverage

To add a new language:
1. Add translation dict to `LOCALES` in `locales.py`
2. Add language code to `SUPPORTED_LANGUAGES` in config
3. Add flag button to language keyboard

## Health & Monitoring

### Health Check Endpoints

- `GET /` - Basic status check
- `GET /health` - Detailed health status

### Logs

```bash
# View bot logs
docker-compose logs -f bot

# View all services
docker-compose logs -f
```

## 🌐 Production Deployment

### Option 1: Oracle Cloud Free Tier (Recommended - $0/month forever)

**What you get for FREE:**
- 4 ARM cores, 24GB RAM (or 2 AMD cores, 1GB RAM)
- 200GB storage
- 10TB bandwidth/month
- No time limit, no hidden costs
- Handles 10,000+ users easily

**Setup time:** 60-90 minutes

📖 **Full guide:** [ORACLE_CLOUD_DEPLOYMENT.md](ORACLE_CLOUD_DEPLOYMENT.md)
⚡ **Quick start:** [deploy/QUICK_START.md](deploy/QUICK_START.md)

```bash
# Quick deployment overview:
# 1. Create Oracle Cloud account (oracle.com/cloud/free)
# 2. Create VM (ARM A1.Flex: 2 cores, 12GB RAM)
# 3. SSH to VM and run setup script
# 4. Clone repo and configure .env.production
# 5. Deploy: docker compose -f docker-compose.prod.yml up -d
```

### Option 2: DigitalOcean ($12-27/month)

```bash
# Create Ubuntu 22.04 droplet
sudo apt update && sudo apt install -y docker.io docker-compose-plugin

git clone https://github.com/YOUR_USERNAME/qazairbot.git
cd qazairbot

cp .env.production.template .env.production
nano .env.production  # Add your secrets

docker compose -f docker-compose.prod.yml up -d
```

### Option 3: Railway.app ($25-35/month)

- Push code to GitHub
- Connect Railway to GitHub repo
- Deploy in 2 clicks
- Auto-scaling included

## Future Enhancements (TMA Ready)

The architecture supports seamless transition to Telegram Mini App:
- FastAPI backend can serve Mini App frontend
- Shared database and business logic
- User authentication via Telegram WebApp
- Interactive maps and charts

## Troubleshooting

### Bot doesn't respond
- Check webhook is set: `docker-compose logs bot | grep webhook`
- Verify BOT_TOKEN in `.env`
- Ensure WEBHOOK_URL is accessible from internet

### No stations found
- Check data sync: `docker-compose logs bot | grep sync`
- Verify API is accessible: `curl https://api.air.org.kz/api/airgradient/latest`

### Database connection errors
- Ensure PostgreSQL is running: `docker-compose ps`
- Check DATABASE_URL in `.env`

## License

MIT License - feel free to use for your own projects!

## Support

For issues and questions, please open an issue on GitHub.
