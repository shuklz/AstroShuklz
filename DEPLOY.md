# Deploying Vedic Kundali to PythonAnywhere

## 1. Create a free PythonAnywhere account

Go to https://www.pythonanywhere.com and sign up for a **Beginner** (free) account.

Your app will be available at: `https://shuklz.pythonanywhere.com`

## 2. Upload the code

**Option A — Git clone (recommended):**
Open a **Bash console** on PythonAnywhere and run:
```bash
cd ~
git clone https://github.com/shuklz/AstroShuklz.git
```

**Option B — Manual upload:**
Use the PythonAnywhere **Files** tab to upload all files into `~/AstroShuklz/`:
- `vedic_kundali.py`
- `app.py`
- `wsgi.py`
- `requirements.txt`
- `templates/index.html`

## 3. Create a virtual environment and install dependencies

In a **Bash console**:
```bash
cd ~/AstroShuklz
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. Set up the web app

1. Go to the **Web** tab on PythonAnywhere
2. Click **Add a new web app**
3. Choose **Manual configuration** (not Flask — we'll point to our own WSGI)
4. Select **Python 3.10** (or the latest available)
5. Set the following:

| Setting | Value |
|---------|-------|
| **Source code** | `/home/shuklz/AstroShuklz` |
| **Working directory** | `/home/shuklz/AstroShuklz` |
| **Virtualenv** | `/home/shuklz/AstroShuklz/venv` |

6. Edit the **WSGI configuration file** (click the link — it opens `/var/www/shuklz_pythonanywhere_com_wsgi.py`). Replace the entire contents with:

```python
import sys
path = '/home/shuklz/AstroShuklz'
if path not in sys.path:
    sys.path.insert(0, path)
from wsgi import application
```

7. Click **Reload** (the green button)

## 5. Test it

Visit `https://shuklz.pythonanywhere.com` — you should see the Kundali form.

Enter birth details, hit **Generate Kundali PDF**, and the PDF opens right in the iPad browser.

## Notes

### Free tier limitations
- **Outbound internet**: PythonAnywhere free tier only allows HTTP to whitelisted sites. The `geopy` geocoding (Nominatim) may not work. The app falls back to the built-in city database (200+ cities) automatically.
- **CPU**: Free accounts get limited CPU seconds. Chart generation is fast (~1s) so this shouldn't be an issue.
- **Always-on**: Free apps sleep after inactivity but wake on first request (takes ~10s).

### Adding more cities
Edit the `CITY_DB` dictionary in `vedic_kundali.py` to add any city:
```python
"my city": (latitude, longitude, utc_offset),
```

### Updating the app
After pushing changes to git:
```bash
cd ~/AstroShuklz
git pull
```
Then click **Reload** on the Web tab.

### iPad bookmark
On Safari, navigate to your PythonAnywhere URL, tap the Share button, and choose **Add to Home Screen**. This creates a bookmark icon that opens like an app.
