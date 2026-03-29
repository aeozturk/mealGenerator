import os
import json
import sys
from datetime import datetime
import anthropic
import resend

# --- Yapılandırma ---
RECIPIENTS = ["ae.ozturk93@gmail.com", "eylulikraozturk@gmail.com"]
SENDER = "Akşam Yemeği Tarifleri <onboarding@resend.dev>"
MAX_RETRY = 2


def get_recipes(client: anthropic.Anthropic, today: str) -> list[dict]:
    """Claude API'den 3 akşam yemeği tarifi al. Hata durumunda MAX_RETRY kez tekrar dene."""
    prompt = f"""Bana bugün akşam yemeği için 3 farklı tarif öner.
Tarifler 2 kişilik olsun.
Ev yemeği tarzında, proteinli ve doyurucu olsun (sulu yemekler, etli yemekler, tavuklu yemekler vb. olabilir).
Her gün farklı tarifler üret, tekrar etme.
Bugünün tarihi: {today}

Her tarif için şu formatta JSON döndür:
[
  {{
    "isim": "Tarif adı",
    "süre": "Toplam süre (dk)",
    "malzemeler": ["malzeme 1", "malzeme 2"],
    "yapılış": ["Adım 1", "Adım 2"]
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
    # Tarih Türkçe formatında gösterilsin
    try:
        dt = datetime.strptime(today, "%Y-%m-%d")
        months = [
            "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
        ]
        date_display = f"{dt.day} {months[dt.month - 1]} {dt.year}"
    except ValueError:
        date_display = today

    # Her tarif için bir kart
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

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#ff6b35,#f7931e); padding:32px 24px; text-align:center;">
      <div style="font-size:48px; margin-bottom:8px;">🍽️</div>
      <h1 style="margin:0; color:#fff; font-size:24px; font-weight:700;">Bugünün Akşam Yemeği Tarifleri</h1>
      <p style="margin:8px 0 0 0; color:rgba(255,255,255,0.9); font-size:15px;">{date_display}</p>
    </div>

    <!-- Giriş metni -->
    <div style="padding:24px 24px 8px 24px;">
      <p style="margin:0; color:#555; font-size:15px; line-height:1.6;">
        Merhaba! 👋 Bugün akşam ne pişireceğinize karar veremediniz mi?
        İşte <strong>3 lezzetli öneri</strong> — hepsi 2 kişilik, doyurucu ve yapması kolay.
      </p>
    </div>

    <!-- Tarifler -->
    <div style="padding:16px 24px;">
      {cards_html}
    </div>

    <!-- Footer -->
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
    """Resend API ile iki alıcıya HTML mail gönder."""
    resend.api_key = os.environ["RESEND_API_KEY"]

    subject = f"🍽️ Bugünün Akşam Yemeği Tarifleri — {today}"

    for recipient in RECIPIENTS:
        try:
            params: resend.Emails.SendParams = {
                "from": SENDER,
                "to": [recipient],
                "subject": subject,
                "html": html,
            }
            response = resend.Emails.send(params)
            print(f"[OK] Mail gönderildi → {recipient} (id: {response.id})")
        except Exception as exc:
            print(f"[HATA] Mail gönderilemedi → {recipient}: {exc}")
            raise


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"=== Akşam Yemeği Tarifi Maili — {today} ===")

    # API key'leri kontrol et
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[HATA] ANTHROPIC_API_KEY ortam değişkeni eksik!")
        sys.exit(1)
    if not os.environ.get("RESEND_API_KEY"):
        print("[HATA] RESEND_API_KEY ortam değişkeni eksik!")
        sys.exit(1)

    # 1. Tarifleri Claude'dan al
    print("Claude API'den tarifler alınıyor...")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    recipes = get_recipes(client, today)
    print(f"{len(recipes)} tarif alındı: {[r.get('isim') for r in recipes]}")

    # 2. HTML şablon oluştur
    html = build_html(recipes, today)

    # 3. Mail gönder
    print("Mailler gönderiliyor...")
    send_emails(html, today)

    print("=== Tamamlandı ===")


if __name__ == "__main__":
    main()
