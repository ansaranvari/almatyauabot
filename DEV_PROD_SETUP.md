# 🔧 Development vs Production Setup

This project uses **separate bots** for development and production environments.

## 🤖 Bot Configuration

### Development Bot
- **Username:** `@qazairqualitybot`
- **Token:** In `.env` file (local development)
- **Purpose:** Testing, debugging, local development
- **Environment:** Your Mac (Docker Compose)

### Production Bot
- **Username:** `@[your_production_bot_username]`
- **Token:** In `.env.production` file (not committed to git)
- **Purpose:** Live users on Oracle Cloud
- **Environment:** Oracle Cloud VM

---

## 📁 Environment Files

### `.env` - Development
```env
BOT_TOKEN=8224548831:AAH...  # qazairqualitybot (dev)
DEBUG=True
LOG_LEVEL=INFO
```

**Location:** Local machine only
**Git status:** ✅ In .gitignore (not committed)

### `.env.production` - Production
```env
BOT_TOKEN=8398793064:AAF...  # Production bot
DEBUG=False
LOG_LEVEL=WARNING
POSTGRES_PASSWORD=<strong-random-password>
REDIS_PASSWORD=<strong-random-password>
```

**Location:** Oracle Cloud VM only
**Git status:** ✅ In .gitignore (not committed)
**Security:** Strong randomly-generated passwords

### `.env.production.template` - Template
```env
BOT_TOKEN=your_production_bot_token_from_botfather
POSTGRES_PASSWORD=CHANGE_THIS_PASSWORD
```

**Location:** Committed to git as example
**Git status:** ✅ Committed (safe, no real credentials)

---

## 🚀 Usage

### Local Development

```bash
# Use development bot (qazairqualitybot)
docker compose up -d

# Check logs
docker compose logs -f bot

# Test with @qazairqualitybot on Telegram
```

### Production Deployment (Oracle Cloud)

```bash
# Use production bot
docker compose -f docker-compose.prod.yml up -d

# Check logs
docker compose -f docker-compose.prod.yml logs -f bot

# Users interact with @[production_bot] on Telegram
```

---

## 🔐 Security Best Practices

### ✅ DO:
- Keep `.env` and `.env.production` files **secret**
- Use **different tokens** for dev and prod
- Use **strong passwords** (32+ characters) in production
- Upload `.env.production` to server via **SCP** (not git)
- Keep backups of `.env.production` in **secure location**

### ❌ DON'T:
- ❌ Commit `.env` or `.env.production` to git
- ❌ Share bot tokens publicly
- ❌ Use same bot for dev and prod
- ❌ Use weak passwords in production
- ❌ Hardcode credentials in code

---

## 📊 Current Setup

| Environment | Bot | Token Location | Database | Users |
|-------------|-----|----------------|----------|-------|
| **Development** | @qazairqualitybot | `.env` (local) | Local PostgreSQL | You only |
| **Production** | @[prod_bot] | `.env.production` (Oracle VM) | Oracle PostgreSQL | Real users |

---

## 🔄 Workflow

### Making Changes

1. **Develop locally:**
   ```bash
   # Edit code
   docker compose restart bot
   # Test with @qazairqualitybot
   ```

2. **Commit to git:**
   ```bash
   git add .
   git commit -m "Add feature X"
   git push origin main
   ```

3. **Deploy to production:**
   ```bash
   # SSH to Oracle Cloud
   ssh -i ssh-key.key ubuntu@YOUR_IP

   # Pull latest code
   cd ~/qazairbot
   git pull origin main

   # Restart production bot
   docker compose -f docker-compose.prod.yml restart bot
   ```

---

## 🧪 Testing New Features

### Local Testing (Safe)
```bash
# Test with dev bot first
docker compose up -d
# Send /start to @qazairqualitybot
# Test all features
```

### Production Deployment (After testing)
```bash
# Only deploy to production after local testing passes
docker compose -f docker-compose.prod.yml up -d
```

---

## 🆘 Troubleshooting

### Bot not responding in development
```bash
# Check .env has correct dev token
grep BOT_TOKEN .env

# Check bot is running
docker compose ps

# Check logs
docker compose logs bot
```

### Bot not responding in production
```bash
# Check .env.production has correct prod token
grep BOT_TOKEN .env.production

# Check bot is running
docker compose -f docker-compose.prod.yml ps

# Check logs
docker compose -f docker-compose.prod.yml logs bot
```

---

## 📝 Token Regeneration

If you need to regenerate a bot token:

1. Message @BotFather
2. Send `/revoke` or `/token`
3. Select the bot
4. Get new token
5. Update `.env` or `.env.production`
6. Restart bot

**⚠️ Old token will stop working immediately!**

---

## 🔒 Files in .gitignore

These files are **never** committed to git:

```
.env                 # Development secrets
.env.production      # Production secrets
.env.*.local         # Any local environment files
*.key                # SSH keys
*.pem                # SSL certificates
```

✅ Safe to commit:
```
.env.example              # Example with placeholder values
.env.production.template  # Template with placeholder values
```

---

## 🎯 Quick Reference

**Start dev bot:**
```bash
docker compose up -d
```

**Start prod bot:**
```bash
docker compose -f docker-compose.prod.yml up -d
```

**View dev logs:**
```bash
docker compose logs -f bot
```

**View prod logs:**
```bash
docker compose -f docker-compose.prod.yml logs -f bot
```

**Restart dev bot:**
```bash
docker compose restart bot
```

**Restart prod bot:**
```bash
docker compose -f docker-compose.prod.yml restart bot
```

---

## ✅ Checklist Before Production Deploy

- [ ] `.env.production` created with production token
- [ ] Strong passwords generated (32+ characters)
- [ ] Production bot configured in @BotFather
- [ ] Tested locally with dev bot first
- [ ] `.env.production` uploaded to server via SCP
- [ ] Never committed secrets to git
- [ ] Backup of `.env.production` stored securely

---

**Remember:** Development is for testing, Production is for users! 🚀
