import os
import json
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import anthropic

# --- Yapılandırma ---
RECIPIENTS = ["ae.ozturk93@gmail.com", "eylulikraozturk@gmail.com"]
SENDER_EMAIL = "ae.ozturk93@gmail.com"
MAX_RETRY = 2


def get_recipes(client: anthropic.Anthropic, today: str) -> list[dict]:
    """Claude API'den 3 akşam yemeği tarifi al. Hata durumunda MAX_RETRY kez tekrar dene."""
    prompt = f"""Bana bugün akşam yemeği için 3 farklı tarif öner.
Tarifler 2 kişilik olsun.
Ev yemeği tarzında, proteinli ve doyurucu olsun (sulu yemekler, etli yemekler, tavuklu yemekler vb. olabilir).
Her gün farklı tarifler üret, tekrar etme.
Bugünün tarihi: {today}

Malzemeleri yazarken mutlaka ölçü belirt (örn: "500g tavuk göğsü", "2 yemek kaşığı zeytinyağı", "1 çay kaşığı tuz").
Yapılış adımları net ve ayrıntılı olsun: kaç dakika pişirileceği, ateş seviyesi (kısık/orta/yüksek), malzemelerin nasıl ekleneceği açıkça belirtilsin.
Her adım tek bir işlemi tarif etsin, birden fazla işlemi tek adıma sıkıştırma.

Her tarif için şu formatta JSON döndür:
[
  {{
    "isim": "Tarif adı",
    "süre": "Toplam süre (dk)",
    "malzemeler": ["500g tavuk göğsü", "2 yemek kaşığı zeytinyağı"],
    "yapılış": ["Tavukları 2x2 cm küp şeklinde doğrayın.", "Orta ateşte tavayı ısıtın ve zeytinyağını ekleyin."]
  }}
]
Sadece JSON döndür, başka hiçbir şey ekleme."""

    for attempt in range(1, MAX_RETRY + 1):
        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            # JSON bloğu içinde gelebilir, temizle
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

    CARD_COLORS = ["#e8f5e9", "#e3f2fd", "#fff3e0"]
    ACCENT_COLORS = ["#2e7d32", "#1565c0", "#e65100"]

    cards_html = ""
    for i, recipe in enumerate(recipes):
        color = CARD_COLORS[i % len(CARD_COLORS)]
        accent = ACCENT_COLORS[i % len(ACCENT_COLORS)]

        ingredients = "".join(
            f"<li style='margin:4px 0;'>{item}</li>"
            for item in recipe.get("malzemeler", [])
        )
        steps = "".join(
            f"<li style='margin:6px 0;'>{step}</li>"
            for step in recipe.get("yapılış", [])
        )

        cards_html += f"""
        <div style="background:{color}; border-radius:12px; padding:24px; margin-bottom:24px; border-left:5px solid {accent};">
            <h2 style="margin:0 0 8px 0; color:{accent}; font-size:20px;">
                {i+1}. {recipe.get('isim', 'Tarif')}
            </h2>
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
        İşte <strong>3 lezzetli öneri</strong> — hepsi 2 kişilik, doyurucu ve yapması kolay.
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

    print("Claude API'den tarifler alınıyor...")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    recipes = get_recipes(client, today)
    print(f"{len(recipes)} tarif alındı: {[r.get('isim') for r in recipes]}")

    html = build_html(recipes, today)

    print("Mailler gönderiliyor...")
    send_emails(html, today)

    print("=== Tamamlandı ===")


if __name__ == "__main__":
    main()
