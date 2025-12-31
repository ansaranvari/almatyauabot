#!/bin/bash

echo "🤖 QazAirbot - Multi-language Air Quality Bot"
echo "=============================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "✏️  Please edit .env and add your BOT_TOKEN:"
    echo "   nano .env"
    echo ""
    exit 1
fi

# Check if BOT_TOKEN is set
if grep -q "your_telegram_bot_token_here" .env; then
    echo "⚠️  BOT_TOKEN not configured!"
    echo "Please edit .env and add your Telegram bot token:"
    echo "   nano .env"
    echo ""
    exit 1
fi

echo "✅ Configuration found"
echo ""
echo "🚀 Starting services..."
echo ""

# Start docker compose
docker-compose up -d

echo ""
echo "✅ Services started!"
echo ""
echo "📋 Available commands:"
echo "   docker-compose logs -f bot    # View bot logs"
echo "   docker-compose ps              # Check service status"
echo "   docker-compose down            # Stop all services"
echo ""
echo "🔗 Health check: http://localhost:8000/health"
echo ""
echo "Happy monitoring! 🌍"
