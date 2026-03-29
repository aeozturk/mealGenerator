# 🍽️ Günlük Akşam Yemeği Tarifi Maili

Her gün saat **16:00'da (Türkiye saati)** otomatik olarak 2 mail adresine **3 adet akşam yemeği tarifi** gönderen Python uygulaması. Tarifler Claude AI tarafından üretilir, Resend ile gönderilir.

---

## Kurulum

### 1. Anthropic API Key al

1. [console.anthropic.com](https://console.anthropic.com) adresine git
2. Hesap oluştur veya giriş yap
3. **API Keys** menüsünden yeni bir key oluştur
4. Key'i kopyala — bir daha göremezsin

### 2. Resend API Key al

1. [resend.com](https://resend.com) adresine git (GitHub ile giriş yapabilirsin)
2. **API Keys** menüsünden yeni bir key oluştur
3. Key'i kopyala

> **Not:** Ücretsiz planda `onboarding@resend.dev` adresi gönderici olarak kullanılır. Kendi domain'ini doğrularsan istediğin adresi kullanabilirsin.

### 3. GitHub reposu oluştur

```bash
git init
git add .
git commit -m "İlk commit"
git branch -M main
git remote add origin https://github.com/KULLANICI_ADI/REPO_ADI.git
git push -u origin main
```

### 4. GitHub Secrets ekle

GitHub reposunda **Settings → Secrets and variables → Actions → New repository secret** yolunu izle:

| Secret Adı | Değer |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic'ten aldığın key |
| `RESEND_API_KEY` | Resend'den aldığın key |

---

## Kullanım

### Otomatik gönderim

GitHub Actions her gün **13:00 UTC (16:00 Türkiye)** saatinde `main.py`'yi otomatik çalıştırır. Hiçbir şey yapman gerekmez.

### Manuel gönderim (tek tıkla)

1. GitHub reposuna git
2. **Actions** sekmesine tıkla
3. Sol menüden **"Günlük Akşam Yemeği Tarifi"** workflow'unu seç
4. **"Run workflow"** → **"Run workflow"** butonuna bas

Mail birkaç saniye içinde gelir.

### Yerel test

```bash
# Bağımlılıkları yükle
pip install -r requirements.txt

# Ortam değişkenlerini ayarla
export ANTHROPIC_API_KEY="sk-ant-..."
export RESEND_API_KEY="re_..."

# Çalıştır
python main.py
```

---

## Tercihleri Değiştirme

### Alıcı adresleri

[main.py](main.py) dosyasını aç, en üstteki `RECIPIENTS` listesini düzenle:

```python
RECIPIENTS = ["yeni@adres.com", "diger@adres.com"]
```

### Tarif tercihleri (diyet, kısıtlama vb.)

`main.py` içindeki `get_recipes` fonksiyonunda `prompt` değişkenini düzenle:

```python
prompt = f"""Bana bugün akşam yemeği için 3 farklı tarif öner.
Tarifler 2 kişilik olsun.
Vejetaryen olsun.          # ← buraya istediğini ekle
...
```

### Gönderim saati

[.github/workflows/send_recipe.yml](.github/workflows/send_recipe.yml) dosyasındaki cron ifadesini değiştir:

```yaml
- cron: '0 13 * * *'   # 13:00 UTC = 16:00 TR
# Örnek: '0 10 * * *'  → 13:00 TR
# Örnek: '0 15 * * *'  → 18:00 TR
```

---

## Dosya Yapısı

```
.
├── .github/
│   └── workflows/
│       └── send_recipe.yml   ← GitHub Actions zamanlayıcı
├── main.py                   ← Ana script
├── requirements.txt          ← Python bağımlılıkları
└── README.md
```

---

## Kullanılan Teknolojiler

| Katman | Teknoloji | Ücret |
|---|---|---|
| Tarif üretimi | Anthropic Claude API | Ücretsiz kredi ile başlar |
| Mail gönderimi | Resend | Ücretsiz (100 mail/gün) |
| Zamanlayıcı | GitHub Actions | Ücretsiz |
