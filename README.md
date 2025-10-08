# 🎵 בוט לעריכת מוזיקה

בוט טלגרם מתקדם לעריכת קבצי אודיו עם מגוון תכונות מתקדמות.

## ✨ תכונות עיקריות

- ✂️ חיתוך קבצי אודיו (התחלה/סיום)
- 🏷️ עריכת נתוני קובץ (כותרת, אמן, אלבום, ז'אנר)
- 🖼️ הוספה ועדכון עטיפות לאלבומים
- 📁 תמיכה בפורמטי אודיו נפוצים
- 🌍 תמיכה במספר שפות
- 🔒 בקרת הרשאות משתמשים

## 🚀 התחלה מהירה

### דרישות מערכת

- Python 3.8+
- pip (מנהל חבילות פייתון)
- טוקן בוט טלגרם מ-[@BotFather](https://t.me/botfather)
- מזהה API וחש

### התקנה

1. שכפול המאגר:
   ```bash
   git clone https://github.com/sudo-py-dev/music-editor.git
   cd music_editor
   ```

2. יצירת סביבה וירטואלית והתקנת תלויות:
   ```bash
   python -m venv venv
   source venv/bin/activate  # ב-Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. הגדרת משתני סביבה:
   - העתק את הקובץ `.env.example` ל-`.env`
   - עדכן את הקובץ `.env` עם הפרטים שלך:
     ```
     BOT_TOKEN=your_telegram_bot_token
     API_ID=your_telegram_api_id
     API_HASH=your_telegram_api_hash
     ```

### הרצת הבוט

לאחר השלמת ההתקנה, הפעל את הבוט באמצעות:

```bash
python index.py
```

הבוט אמור להציג הודעת התחלה ולענות להודעות בטלגרם.

### שימוש

1. חפש את הבוט בטלגרם
2. שלח קובץ אודיו לבוט
3. השתמש בתפריט כדי לבחור פעולות עריכה
