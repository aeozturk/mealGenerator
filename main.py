import os
import json
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import anthropic
import requests

# --- Yapılandırma ---
RECIPIENTS = ["ae.ozturk93@gmail.com", "eylulikraozturk@gmail.com"]
SENDER_EMAIL = "ae.ozturk93@gmail.com"
MAX_RETRY = 2
HISTORY_FILE = "recipe_history.json"


def load_recent_recipes() -> list[str]:
    """Son 7 günde gönderilen tarif isimlerini oku."""
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        history: dict = json.load(f)
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    recent = []
    for date, names in history.items():
        if date >= cutoff:
            recent.extend(names)
    return recent


def save_recipes_to_history(today: str, recipes: list[dict]):
    """Bugün gönderilen tarifleri geçmişe kaydet."""
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    # 30 günden eski kayıtları temizle
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    history = {d: v for d, v in history.items() if d >= cutoff}
    history[today] = [r.get("isim", "") for r in recipes]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_image_url(query: str) -> str | None:
    """Pexels API ile yemek görseli URL'si döndür. Bulunamazsa None."""
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        return None
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": f"{query} plated dish", "per_page": 1, "orientation": "landscape"},
            timeout=10,
        )
        data = resp.json()
        photos = data.get("photos", [])
        if photos:
            return photos[0]["src"]["large"]
    except Exception as exc:
        print(f"[UYARI] Görsel alınamadı ({query}): {exc}")
    return None


def get_recipes(client: anthropic.Anthropic, today: str, recent_recipes: list[str]) -> list[dict]:
    """Claude API'den 5 tarif al (3 ana yemek, 1 spor, 1 tatlı). Hata durumunda MAX_RETRY kez tekrar dene."""
    avoid_section = ""
    if recent_recipes:
        avoid_list = ", ".join(f'"{r}"' for r in recent_recipes)
        avoid_section = f"\nBu hafta zaten şu yemekler gönderildi, bunları tekrarlama: {avoid_list}\n"

    prompt = f"""Bana bugün için toplamda 5 tarif öner. Tarifler 2 kişilik olsun.
{avoid_section}
Bugünün tarihi: {today}

Tarifler şu kategorilerde olsun:
1. Ana yemek — etli, tavuklu, köfte, kavurma, güveç gibi doyurucu ev yemeği (3 adet, "ana_yemek" kategorisi)
2. Spor tarifi — spor yapan biri için protein ağırlıklı, sağlıklı karbonhidratlı, pratik bir yemek (1 adet, "spor" kategorisi)
3. Tatlı — pratik ve yapması kolay bir tatlı (1 adet, "tatlı" kategorisi)

Ana yemeklerde pilav, çorba, salata gibi yan yemekler önerme.
Spor tarifinde işlenmiş gıda ve rafine şeker olmasın, protein kaynağı net olsun (tavuk, yumurta, ton balığı, baklagil vb.).
Tatlıda basit malzemelerle evde kolayca yapılabilecek bir tarif seç.

Malzemeleri yazarken mutlaka ölçü belirt (örn: "500g tavuk göğsü", "2 yemek kaşığı zeytinyağı").
Tüm malzeme isimleri Türkçe olsun. Yabancı isim kullanma: oregano → kekik, thyme → kekik, rosemary → biberiye, basil → fesleğen, cumin → kimyon, paprika → kırmızı biber, garlic → sarımsak vb.
Yapılış adımları net ve ayrıntılı olsun: kaç dakika pişirileceği, ateş seviyesi (kısık/orta/yüksek), malzemelerin nasıl ekleneceği açıkça belirtilsin.
Her adım tek bir işlemi tarif etsin.

Tam olarak şu formatta JSON döndür (5 eleman):
[
  {{
    "kategori": "ana_yemek",
    "isim": "Tarif adı",
    "gorsel_arama": "Simple English search term for the MAIN INGREDIENT only, not the full dish name (e.g. 'grilled chicken', 'beef stew', 'lentil soup', 'chocolate cake'). Keep it short and generic so stock photo sites can find a match.",
    "süre": "Toplam süre (dk)",
    "malzemeler": ["500g tavuk göğsü", "2 yemek kaşığı zeytinyağı"],
    "yapılış": ["Tavukları 2x2 cm küp şeklinde doğrayın.", "Orta ateşte tavayı ısıtın."]
  }}
]
Sadece JSON döndür, başka hiçbir şey ekleme."""

    for attempt in range(1, MAX_RETRY + 1):
        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            recipes = json.loads(raw.strip())
            if not isinstance(recipes, list) or len(recipes) == 0:
                raise ValueError("Boş veya geçersiz tarif listesi")
            return recipes
        except Exception as exc:
            print(f"[Deneme {attempt}/{MAX_RETRY}] Tarif alınamadı: {exc}")
            if attempt == MAX_RETRY:
                raise

    return []


def build_html(recipes: list[dict], today: str) -> str:
    """Tarif listesinden güzel HTML mail içeriği oluştur."""
    try:
        dt = datetime.strptime(today, "%Y-%m-%d")
        months = [
            "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
        ]
        date_display = f"{dt.day} {months[dt.month - 1]} {dt.year}"
    except ValueError:
        date_display = today

    CATEGORY_STYLES = {
        "ana_yemek": {"color": "#e8f5e9", "accent": "#2e7d32", "icon": "🍽️", "label": "Ana Yemek"},
        "spor":      {"color": "#e3f2fd", "accent": "#1565c0", "icon": "💪", "label": "Spor Tarifi"},
        "tatlı":     {"color": "#fce4ec", "accent": "#c62828", "icon": "🍮", "label": "Tatlı"},
    }
    DEFAULT_STYLE = {"color": "#fff3e0", "accent": "#e65100", "icon": "🍴", "label": "Tarif"}

    # Kategoriye göre grupla ve sırala
    ana_yemekler = [r for r in recipes if r.get("kategori") == "ana_yemek"]
    spor = [r for r in recipes if r.get("kategori") == "spor"]
    tatlilar = [r for r in recipes if r.get("kategori") == "tatlı"]
    ordered = ana_yemekler + spor + tatlilar

    cards_html = ""
    ana_counter = 0
    for recipe in ordered:
        kategori = recipe.get("kategori", "")
        style = CATEGORY_STYLES.get(kategori, DEFAULT_STYLE)
        color = style["color"]
        accent = style["accent"]
        icon = style["icon"]
        label = style["label"]

        if kategori == "ana_yemek":
            ana_counter += 1
            baslik = f"{ana_counter}. {recipe.get('isim', 'Tarif')}"
        else:
            baslik = recipe.get("isim", "Tarif")

        ingredients = "".join(
            f"<li style='margin:4px 0;'>{item}</li>"
            for item in recipe.get("malzemeler", [])
        )
        steps = "".join(
            f"<li style='margin:6px 0;'>{step}</li>"
            for step in recipe.get("yapılış", [])
        )

        image_url = get_image_url(recipe.get("gorsel_arama", baslik))
        image_html = (
            f'<img src="{image_url}" alt="{baslik}" style="width:100%; height:200px; object-fit:cover; border-radius:8px; margin-bottom:16px; display:block;">'
            if image_url else ""
        )

        cards_html += f"""
        <div style="background:{color}; border-radius:12px; padding:24px; margin-bottom:24px; border-left:5px solid {accent};">
            {image_html}
            <div style="margin-bottom:10px;">
                <span style="background:{accent}; color:#fff; font-size:11px; font-weight:700; padding:3px 10px; border-radius:20px; letter-spacing:0.5px;">
                    {icon} {label.upper()}
                </span>
            </div>
            <h2 style="margin:0 0 8px 0; color:{accent}; font-size:20px;">{baslik}</h2>
            <p style="margin:0 0 16px 0; color:#555; font-size:14px;">
                ⏱️ Süre: <strong>{recipe.get('süre', '?')}</strong> &nbsp;|&nbsp; 👥 2 kişilik
            </p>
            <h3 style="margin:0 0 8px 0; color:#333; font-size:15px;">🛒 Malzemeler</h3>
            <ul style="margin:0 0 16px 0; padding-left:20px; color:#444; font-size:14px; line-height:1.6;">
                {ingredients}
            </ul>
            <h3 style="margin:0 0 8px 0; color:#333; font-size:15px;">👨‍🍳 Yapılışı</h3>
            <ol style="margin:0; padding-left:20px; color:#444; font-size:14px; line-height:1.7;">
                {steps}
            </ol>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Akşam Yemeği Tarifleri</title>
</head>
<body style="margin:0; padding:0; background:#f5f5f5; font-family:'Segoe UI',Arial,sans-serif;">
  <div style="max-width:600px; margin:32px auto; background:#fff; border-radius:16px; overflow:hidden; box-shadow:0 2px 12px rgba(0,0,0,0.1);">

    <div style="background:linear-gradient(135deg,#ff6b35,#f7931e); padding:32px 24px; text-align:center;">
      <div style="font-size:48px; margin-bottom:8px;">🍽️</div>
      <h1 style="margin:0; color:#fff; font-size:24px; font-weight:700;">Bugünün Akşam Yemeği Tarifleri</h1>
      <p style="margin:8px 0 0 0; color:rgba(255,255,255,0.9); font-size:15px;">{date_display}</p>
    </div>

    <div style="padding:24px 24px 8px 24px;">
      <p style="margin:0; color:#555; font-size:15px; line-height:1.6;">
        Merhaba! 👋 Bugün akşam ne pişireceğinize karar veremediniz mi?
        İşte bugün için <strong>5 tarif</strong> — 3 ana yemek, 1 spor tarifi ve 1 tatlı.
      </p>
    </div>

    <div style="padding:16px 24px;">
      {cards_html}
    </div>

    <div style="background:#fafafa; border-top:1px solid #eee; padding:20px 24px; text-align:center;">
      <p style="margin:0; color:#888; font-size:13px;">
        Yarın da güzel yemekler 🙂
      </p>
      <p style="margin:8px 0 0 0; color:#bbb; font-size:11px;">
        Bu mail otomatik olarak gönderilmiştir.
      </p>
    </div>

  </div>
</body>
</html>"""


def send_emails(html: str, today: str):
    """Gmail SMTP ile tüm alıcılara HTML mail gönder."""
    app_password = os.environ["GMAIL_APP_PASSWORD"]
    subject = f"🍽️ Bugünün Akşam Yemeği Tarifleri — {today}"

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, app_password)
        for recipient in RECIPIENTS:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"Akşam Yemeği Tarifleri <{SENDER_EMAIL}>"
                msg["To"] = recipient
                msg.attach(MIMEText(html, "html", "utf-8"))
                server.sendmail(SENDER_EMAIL, recipient, msg.as_string())
                print(f"[OK] Mail gönderildi → {recipient}")
            except Exception as exc:
                print(f"[HATA] Mail gönderilemedi → {recipient}: {exc}")


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"=== Akşam Yemeği Tarifi Maili — {today} ===")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[HATA] ANTHROPIC_API_KEY ortam değişkeni eksik!")
        sys.exit(1)
    if not os.environ.get("GMAIL_APP_PASSWORD"):
        print("[HATA] GMAIL_APP_PASSWORD ortam değişkeni eksik!")
        sys.exit(1)

    # Son 7 günün tarif geçmişini oku
    recent_recipes = load_recent_recipes()
    if recent_recipes:
        print(f"Bu hafta gönderilen tarifler: {recent_recipes}")

    print("Claude API'den tarifler alınıyor...")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    recipes = get_recipes(client, today, recent_recipes)
    print(f"{len(recipes)} tarif alındı: {[r.get('isim') for r in recipes]}")

    html = build_html(recipes, today)

    print("Mailler gönderiliyor...")
    send_emails(html, today)

    # Geçmişi güncelle
    save_recipes_to_history(today, recipes)
    print("Geçmiş güncellendi.")

    print("=== Tamamlandı ===")


if __name__ == "__main__":
    main()
