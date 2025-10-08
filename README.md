# 🎵 בוט לעריכת מוזיקה

בוט טלגרם מתקדם לעריכת קבצי אודיו עם מגוון תכונות מתקדמות.

## ✨ תכונות עיקריות

- 🏷️ עריכת נתוני קובץ (כותרת, אמן, אלבום, ז'אנר)
- 🖼️ הוספה ועדכון עטיפות לאלבומים
- 📁 תמיכה בפורמטי אודיו נפוצים
- 🌍 תמיכה במספר שפות
- 🔒 בקרת הרשאות משתמשים
- 🐳 הרצה קלה עם Docker

## 🚀 התחלה מהירה

### דרישות מערכת

- [Docker](https://docs.docker.com/get-docker/) ו-Docker Compose
- טוקן בוט טלגרם מ-[@BotFather](https://t.me/botfather)
- מזהה API והאש מ-[my.telegram.org](https://my.telegram.org/auth)

### התקנה עם Docker

1. שכפול המאגר:
   ```bash
   git clone https://github.com/sudo-py-dev/music-editor.git
   cd music_editor
   ```

2. הגדרת משתני סביבה:
   - העתק את הקובץ `.env.example` ל-`.env`
   - עדכן את הקובץ `.env` עם הפרטים שלך:
     ```
     BOT_TOKEN=הטוקן_של_הבוט_שלך
     API_ID=המזהה_שלך
     API_HASH=האש_שלך
     BOT_CLIENT_NAME=music_editor_bot
     OWNER_ID=המזהה_האישי_שלך_בטלגרם
     ```

### הרצה עם Docker

1. בניית תמורת הדוקר:
   ```bash
   docker build -t music-editor-bot .
   ```

2. הפעלת המיכל:
   ```bash
   docker run -d \
     --name music-bot \
     --restart unless-stopped \
     --env-file .env \
     music-editor-bot
   ```

### שימוש ב-Docker Compose (אופציונלי)

יצירת קובץ `docker-compose.yml`:

```yaml
version: '3.8'

services:
  music-bot:
    build: .
    container_name: music-bot
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data:/app/data  # אופציונלי: שמירת קבצים בצורה קבועה
```
לאחר מכן הרץ:
```bash
docker-compose up -d
```

הבוט אמור להציג הודעת התחלה ולענות להודעות בטלגרם.

### שימוש

1. חפש את הבוט בטלגרם
2. שלח קובץ אודיו לבוט
3. השתמש בתפריט כדי לבחור פעולות עריכה
