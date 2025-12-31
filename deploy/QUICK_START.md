# 🚀 Quick Start: Oracle Cloud Deployment

**Time Required:** 60-90 minutes
**Cost:** $0 forever

## ⚡ TL;DR - 5 Steps

```bash
# 1. Create Oracle Cloud account
# → https://www.oracle.com/cloud/free/

# 2. Create VM (ARM: 2 cores, 12GB RAM)
# → Compute → Instances → Create Instance

# 3. SSH into VM
ssh -i ~/Downloads/ssh-key.key ubuntu@YOUR_IP

# 4. Run setup script
curl -o setup.sh https://raw.githubusercontent.com/YOUR_USERNAME/qazairbot/main/deploy/oracle-cloud-setup.sh
chmod +x setup.sh && ./setup.sh

# 5. Deploy bot
git clone https://github.com/YOUR_USERNAME/qazairbot.git
cd qazairbot
cp .env.production.template .env.production
# Edit .env.production with your secrets
docker compose -f docker-compose.prod.yml up -d
```

## 📋 Pre-Deployment Checklist

Before you start, have these ready:

- [ ] Credit card (for Oracle verification - won't be charged)
- [ ] Telegram account
- [ ] GitHub account (to host code)
- [ ] 60 minutes of free time

## 🎯 Phase-by-Phase Guide

### Phase 1: Oracle Cloud Account (10 min)

1. Go to: https://www.oracle.com/cloud/free/
2. Click "Start for free"
3. Enter details and verify email
4. Add credit card (verification only)
5. Wait for activation email

### Phase 2: Create VM (15 min)

1. Login to cloud.oracle.com
2. Navigate: Compute → Instances → Create Instance
3. Configure:
   - **Name:** qazairbot-production
   - **Image:** Ubuntu 22.04
   - **Shape:** VM.Standard.A1.Flex (ARM)
   - **OCPUs:** 2
   - **Memory:** 12 GB
   - **Public IP:** Yes
4. Generate SSH keys (save them!)
5. Click "Create"
6. Note: Public IP address

### Phase 3: Configure Firewall (5 min)

**Cloud Firewall:**
1. Networking → VCN → Security Lists
2. Add Ingress Rules:
   - Port 80 (HTTP)
   - Port 443 (HTTPS)

**OS Firewall:**
- Handled by setup script

### Phase 4: Setup VM (20 min)

```bash
# Connect via SSH
chmod 400 ~/Downloads/ssh-key-*.key
ssh -i ~/Downloads/ssh-key-*.key ubuntu@YOUR_IP

# Run setup script
curl -o setup.sh https://raw.githubusercontent.com/YOUR_USERNAME/qazairbot/main/deploy/oracle-cloud-setup.sh
chmod +x setup.sh
./setup.sh

# Logout and login again
exit
ssh -i ~/Downloads/ssh-key-*.key ubuntu@YOUR_IP
```

### Phase 5: Deploy Bot (15 min)

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/qazairbot.git
cd qazairbot

# Create production config
cp .env.production.template .env.production

# Generate passwords
openssl rand -base64 32  # For POSTGRES_PASSWORD
openssl rand -base64 32  # For REDIS_PASSWORD

# Edit configuration
nano .env.production
# Add: BOT_TOKEN, passwords, update DATABASE_URL

# Start services
docker compose -f docker-compose.prod.yml up -d

# Check logs
docker compose -f docker-compose.prod.yml logs -f
```

### Phase 6: Verify (5 min)

```bash
# Check all containers running
docker ps

# Should see 3 containers:
# - qazairbot
# - qazairbot_postgres
# - qazairbot_redis
```

**Test on Telegram:**
- Send /start to your bot
- Send your location
- Should get air quality report

## ✅ Success Indicators

You know it's working when:

1. ✅ All 3 Docker containers show "Up" status
2. ✅ Logs show: "🤖 QazAirbot started in polling mode!"
3. ✅ Bot responds to /start on Telegram
4. ✅ Bot sends air quality data when you share location

## 🚨 Common Issues

**Issue: Can't SSH to VM**
```bash
# Solution: Check security list allows SSH (port 22)
# Check: Networking → VCN → Security Lists → Ingress Rules
```

**Issue: Docker command not found**
```bash
# Solution: Logout and login again
exit
ssh -i ~/ssh-key.key ubuntu@YOUR_IP
```

**Issue: Bot not responding**
```bash
# Check logs
docker compose -f docker-compose.prod.yml logs bot

# Check BOT_TOKEN is correct
grep BOT_TOKEN .env.production
```

**Issue: Out of memory**
```bash
# Check swap is enabled
swapon --show

# Create swap if missing
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## 📞 Need Help?

**For Oracle Cloud issues:**
- Oracle Support (24/7, free)
- Docs: https://docs.oracle.com/iaas

**For bot issues:**
- Check logs first: `docker compose logs`
- Review full guide: ORACLE_CLOUD_DEPLOYMENT.md

## 🎉 Next Steps After Deployment

1. Setup monitoring: https://uptimerobot.com
2. Configure backups (daily)
3. Test all features
4. Update bot commands with @BotFather

## 💡 Pro Tips

- **Use ARM shape** (A1.Flex) - much more free resources than AMD
- **Setup swap** on low-RAM instances - prevents OOM kills
- **Daily backups** - cron job to pg_dump
- **Monitor logs** - `docker logs -f qazairbot`
- **Keep system updated** - automatic updates are configured

## 📊 Resource Monitoring

```bash
# Check disk usage
df -h

# Check memory
free -h

# Check containers
docker stats

# Check logs size
du -sh ~/qazairbot/logs
```

## 🔒 Security Best Practices

- ✅ Use strong passwords (32+ characters)
- ✅ Keep .env.production secret (never commit to git)
- ✅ Enable automatic security updates (script does this)
- ✅ Change SSH port (optional: edit /etc/ssh/sshd_config)
- ✅ Monitor failed login attempts (fail2ban configured)

---

**Happy Deploying! 🚀**

Your bot will now run 24/7, completely free, handling thousands of users.
