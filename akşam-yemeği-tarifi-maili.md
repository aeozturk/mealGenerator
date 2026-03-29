# 🍽️ Günlük Akşam Yemeği Tarifi Mail Projesi

## Proje Özeti

Her gün saat **16:00'da** otomatik olarak 2 mail adresine **3 adet akşam yemeği tarifi** gönderen bir Python uygulaması. Ayrıca kullanıcı istediği zaman tek tıkla da tarif alabilir. Tarifler Claude API tarafından üretilir.

---

## Kullanıcı Tercihleri

| Özellik | Değer |
|---|---|
| **Gönderim saati** | Her gün 16:00 (Türkiye saati, UTC+3) |
| **Tarif sayısı** | 3 tarif / mail |
| **Kişi sayısı** | 2 kişilik |
| **Tarif tipi** | Ev yemeği, proteinli, sulu yemek dahil, kısıtlama yok |
| **Alıcı 1** | ae.ozturk93@gmail.com |
| **Alıcı 2** | eylulikraozturk@gmail.com |

---

## Teknik Mimari

```
GitHub Actions (Scheduler — her gün 13:00 UTC = 16:00 TR)
        ↓
Python Script (main.py)
        ↓
Claude API → 3 tarif üret
        ↓
Resend API → HTML mail gönder
        ↓
ae.ozturk93@gmail.com
eylulikraozturk@gmail.com
```

---

## Kullanılacak Teknolojiler

| Katman | Teknoloji | Ücret |
|---|---|---|
| **Dil** | Python 3.11 | Ücretsiz |
| **Tarif üretimi** | Anthropic Claude API (`claude-haiku-3-5`) | Ücretsiz kredi ile başlar |
| **Mail gönderimi** | [Resend](https://resend.com) | Ücretsiz (100 mail/gün) |
| **Zamanlayıcı** | GitHub Actions (`cron`) | Ücretsiz |
| **Deployment** | GitHub Actions | Ücretsiz |
| **Manuel tetikleyici** | GitHub Actions `workflow_dispatch` | Ücretsiz |

> 💡 Tamamen ücretsiz katmanlar kullanılıyor. Hiçbir şey için ödeme gerekmez.

---

## Gerekli Hesaplar & API Key'ler

Aşağıdaki hesapları oluşturup API key'leri GitHub Secrets'a eklemen gerekecek:

1. **Anthropic API Key** → [console.anthropic.com](https://console.anthropic.com)
   - Secret adı: `ANTHROPIC_API_KEY`

2. **Resend API Key** → [resend.com](https://resend.com) (GitHub ile giriş yapılabilir)
   - Secret adı: `RESEND_API_KEY`
   - Not: Resend'de bir domain doğrulaması gerekir veya `onboarding@resend.dev` adresinden test gönderilebilir. Ücretsiz planda kendi Gmail adresine de gönderilebilir.

---

## Dosya Yapısı

```
akşam-yemeği-tarifi/
├── .github/
│   └── workflows/
│       └── send_recipe.yml      ← GitHub Actions zamanlayıcı
├── main.py                      ← Ana script
├── requirements.txt             ← Python bağımlılıkları
└── README.md                    ← Kurulum kılavuzu
```

---

## Proje Detayları

### `requirements.txt`
```
anthropic
resend
```

### `main.py` — Yapması Gerekenler

1. Claude API'ye şu prompt'u gönder:

```
Bana bugün akşam yemeği için 3 farklı tarif öner. 
Tarifler 2 kişilik olsun. 
Ev yemeği tarzında, proteinli ve doyurucu olsun (sulu yemekler, etli yemekler, tavuklu yemekler vb. olabilir).
Her gün farklı tarifler üret, tekrar etme.
Bugünün tarihi: {bugünün tarihi}

Her tarif için şu formatta JSON döndür:
[
  {
    "isim": "Tarif adı",
    "süre": "Toplam süre (dk)",
    "malzemeler": ["malzeme 1", "malzeme 2", ...],
    "yapılış": ["Adım 1", "Adım 2", ...]
  }
]
Sadece JSON döndür, başka hiçbir şey ekleme.
```

2. JSON parse et, 3 tarifi al
3. Güzel HTML mail şablonu oluştur (mobil uyumlu, renkli, iştah açıcı)
4. Resend ile iki adrese gönder

### Mail HTML Şablonu Gereksinimleri
- Başlık: "🍽️ Bugünün Akşam Yemeği Tarifleri — {tarih}"
- Her tarif için ayrı bir kart (card)
- Kart içeriği: tarif adı, süre, malzeme listesi, adım adım yapılış
- Renkli ve modern ama sade tasarım
- Mobil uyumlu (max-width: 600px)
- Footer: "Yarın da güzel yemekler 🙂"

### `send_recipe.yml` — GitHub Actions

```yaml
name: Günlük Akşam Yemeği Tarifi

on:
  schedule:
    - cron: '0 13 * * *'   # Her gün 13:00 UTC = 16:00 Türkiye (UTC+3)
  workflow_dispatch:         # Manuel tetikleme butonu (tek tıkla çalıştır)

jobs:
  send-recipe:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
```

---

## Manuel Kullanım (Tek Tıkla)

GitHub Actions `workflow_dispatch` sayesinde:
1. GitHub reposuna git
2. **Actions** sekmesine tıkla
3. "Günlük Akşam Yemeği Tarifi" workflow'unu seç
4. **"Run workflow"** butonuna bas → mail anında gelir

---

## Hata Yönetimi

- Claude API hatası → hata logla, script'i başarısız olarak bitir (GitHub Actions bunu gösterir)
- Mail gönderilemezse → hata logla
- JSON parse hatası → tekrar dene (max 2 kez)

---

## README.md İçeriği (Claude Yazsın)

Şunları içersin:
- Proje açıklaması
- Kurulum adımları (API key nasıl alınır, secrets nasıl eklenir)
- Manuel çalıştırma talimatları
- Tarif tercihlerini nasıl değiştiririm

---

## Claude Code'a Talimat

Bu MD dosyasına göre:

1. Tüm dosyaları oluştur (`main.py`, `requirements.txt`, `.github/workflows/send_recipe.yml`, `README.md`)
2. `main.py` tam çalışır olsun — test için `python main.py` komutuyla direkt çalıştırılabilsin
3. Mail HTML şablonu güzel ve okunabilir olsun
4. `README.md`'de adım adım kurulum talimatı olsun
5. Kod temiz, yorumlu ve anlaşılır olsun

---

*Hazırlandığında `python main.py` komutuyla test et. İlk çalıştırmada mail gelmeli.*
