# 🎵 Concert Monitoring System

An automated monitoring system that tracks concert tickets and tour dates for your favorite artists across Denmark and Europe. Receives daily email alerts when new concerts are announced.

## 🎯 What's Being Monitored

### Artists
- **Max Richter** - Contemporary classical composer
- **Radiohead** (including "Radio Head" variation)
- **Ludovico Einaudi** - Italian pianist and composer
- **Eels** - Alternative rock band
- **Phoria** - Experimental band
- **Damien Rice** - Irish singer-songwriter
- **Stephen Wilson Jr.** - American singer-songwriter
- **Olafur Arnalds** / **Ólafur Arnalds** - Icelandic composer
- **Arvo Pärt** / **Arvi Part** - Estonian composer
- **Mari Samuelsen** - Norwegian violinist
- **Tom Waits** - American musician
- **City of the Sun** - Instrumental band
- **Hans Zimmer** - Film composer
- **RIOPY** - French-British pianist

### Geographic Coverage
- **Primary Focus:** Denmark
- **Secondary Coverage:** Europe (UK, Germany, Sweden, Norway, and more)
- **Date Range:** Next 24 months
- **Includes:** Sold out shows, presales, and VIP packages

## 🌐 Sites Being Monitored (25+ Platforms)

### Major Ticketing Platforms
- Ticketmaster (Denmark, UK, Sweden, Norway)
- Billetlugen (Denmark)
- Eventim (Germany/Europe)
- See Tickets (UK)
- Live Nation (International)
- AXS
- StubHub
- Gigantic Tickets
- Dice

### Danish Venues
- Royal Arena Copenhagen
- DR Koncerthuset
- Tivoli Copenhagen
- Vega Copenhagen
- Operaen Copenhagen

### International Venues
- Royal Albert Hall (London)
- Barbican Centre (London)
- O2 Arena (London)
- Southbank Centre (London)
- Elbphilharmonie (Hamburg)

### Discovery Platforms
- Songkick
- Bandsintown

## 📧 Email Schedule

- **Daily Emails:** Yes, but only when new concerts are found
- **Weekly Summary:** No (disabled by default)
- **Format:** HTML with grouped results by artist
- **Content:** Venue, city, date, price, ticket links, and availability status

## 🚀 Setup Instructions

### Prerequisites
- GitHub account
- Gmail account (or other SMTP service)
- Python 3.8+ (for local testing)

### Step 1: Fork/Clone Repository
```bash
git clone https://github.com/yourusername/concert-monitor.git
cd concert-monitor
```

### Step 2: Configure GitHub Secrets
Go to Settings → Secrets and variables → Actions, and add:

1. **EMAIL_FROM** - Your Gmail address
2. **EMAIL_PASSWORD** - Gmail App Password (not regular password!)
3. **EMAIL_TO** - Recipient email address

#### Getting Gmail App Password:
1. Go to [Google Account Settings](https://myaccount.google.com)
2. Security → 2-Step Verification (must be enabled)
3. App passwords → Generate new
4. Copy the 16-character password

### Step 3: Install Dependencies (Local Testing)
```bash
pip install requests beautifulsoup4 lxml
```

### Step 4: Test Locally
```bash
# Set environment variables (Linux/Mac)
export EMAIL_FROM="your-email@gmail.com"
export EMAIL_PASSWORD="your-app-password"
export EMAIL_TO="recipient@example.com"

# Run the monitor
python monitor.py
```

### Step 5: Enable GitHub Actions
The workflow runs automatically at 9 AM UTC daily. You can also trigger manually:
1. Go to Actions tab
2. Select "Concert Monitoring System"
3. Click "Run workflow"

## ⚙️ Configuration

### Adding/Removing Artists
Edit `search_config.json`:
```json
{
  "artists": [
    {
      "name": "Artist Name",
      "variations": ["Alternative Spelling", "Nickname"]
    }
  ]
}
```

### Adding/Removing Sites
Edit `search_config.json`:
```json
{
  "sites": [
    {
      "name": "Site Name",
      "search_url": "https://example.com/search?q={query}",
      "enabled": true,
      "selectors": {
        "container": "div.event",
        "title": "h3.title",
        "venue": "span.venue",
        "date": "span.date",
        "link": "a.link",
        "price": "span.price"
      }
    }
  ]
}
```

### Modifying Email Schedule
Edit `.github/workflows/monitor.yml`:
```yaml
on:
  schedule:
    # Change the cron expression (currently 9 AM UTC)
    - cron: '0 9 * * *'
```

**Cron Examples:**
- `0 9 * * *` - Daily at 9 AM UTC
- `0 9 * * 1-5` - Weekdays only at 9 AM UTC
- `0 9,21 * * *` - Twice daily at 9 AM and 9 PM UTC
- `0 9 * * 1` - Weekly on Mondays at 9 AM UTC

## 🔍 How It Works

1. **Daily Execution:** GitHub Actions triggers the monitor at 9 AM UTC
2. **Search Process:** 
   - Searches each site for each artist
   - Validates full artist name appears in results
   - Extracts venue, date, price, and ticket links
3. **Duplicate Detection:** 
   - Generates hash for each concert (artist + venue + date)
   - Tracks seen items to avoid duplicate alerts
4. **Email Notification:**
   - Groups new concerts by artist
   - Sends HTML formatted email
   - Only sends if new concerts found
5. **State Persistence:**
   - Saves seen items to prevent re-alerting
   - Stores as GitHub artifact and in repository

## 🛠 Troubleshooting

### No Emails Received
1. Check GitHub Actions logs for errors
2. Verify email credentials in GitHub Secrets
3. Check spam folder
4. Ensure Gmail App Password is correct (not regular password)

### Sites Not Returning Results
1. Some sites may block automated searches
2. Check if site structure has changed
3. Verify search URL format is correct
4. Consider adding delays between searches

### False Positives
1. Adjust artist validation in `monitor.py`
2. Add more specific variations in config
3. Check if venue names contain artist names

### GitHub Actions Failing
1. Check Actions tab for error logs
2. Verify all secrets are set correctly
3. Ensure repository has Actions enabled
4. Check Python version compatibility

### Manual Testing
```bash
# Test with verbose output
python -u monitor.py

# Test email configuration
python -c "
import os
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login(os.environ['EMAIL_FROM'], os.environ['EMAIL_PASSWORD'])
print('Email configuration valid!')
server.quit()
"
```

## 📊 Data Collected

Each concert alert includes:
- **Artist Name** - Full validated name
- **Title** - Event/concert title
- **Venue** - Performance location
- **City** - City and country
- **Date** - Performance date/time
- **Price** - Ticket price range
- **Status** - Available/Sold Out/Presale
- **Link** - Direct ticket purchase URL
- **Source** - Which platform found it

## 🔒 Privacy & Security

- Email credentials stored as encrypted GitHub Secrets
- No personal data collected or stored
- Only public concert information monitored
- Rate limiting implemented to respect sites
- User-Agent properly identified

## 🤝 Contributing

### Adding New Artists
1. Edit `search_config.json`
2. Add artist with variations
3. Test locally first
4. Submit pull request

### Improving Site Parsers
1. Test site manually first
2. Identify correct selectors
3. Update `search_config.json`
4. Verify results accuracy

### Bug Reports
1. Check existing issues
2. Include error logs
3. Specify which site/artist
4. Provide reproduction steps

## 📝 License

MIT License - Feel free to modify for personal use

## 🆘 Support

For issues or questions:
1. Check troubleshooting section
2. Review GitHub Actions logs
3. Test components individually
4. Open an issue with details

## 🎉 Features

- ✅ Monitors 25+ ticket platforms
- ✅ Covers Denmark and all of Europe
- ✅ Tracks 14+ artists with variations
- ✅ Daily automated checking
- ✅ Email only when new concerts found
- ✅ Includes sold out and presale shows
- ✅ Direct ticket purchase links
- ✅ Price information when available
- ✅ Duplicate detection
- ✅ HTML formatted emails
- ✅ Grouped by artist
- ✅ GitHub Actions automation
- ✅ Manual trigger option
- ✅ Error handling and retries

---

*Last Updated: November 2025*
*Monitoring Active: Daily at 9 AM UTC*
