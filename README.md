# AI Doorball

AI Doorball, kameradan gelen goruntude yuz algilayan, tanidik kisileri eslestiren ve duruma gore Telegram bildirimi veya zil sesi uretebilen basit bir Python projesidir.

## Ozellikler

- Gercek zamanli kamera goruntusunde yuz algilama
- `known_faces/` klasorundeki gorseller ile tanidik kisi tanima
- Yeni gelen kisi icin uygulama icinden hizli kayit alma
- Telegram grubuna fotograf gonderme
- Kisi taniniyorsa Telegram aciklamasinda ismini yazma
- Tanidik kisi geldiyse sistemden zil sesi calma
- Zil sesini ayri thread'de calistirarak kamera akisinin donmasini engelleme

## Proje Yapisi

```text
ai-doorball/
├── main.py
├── encoder.py
├── camera_utils.py
├── face_ops.py
├── sound_utils.py
├── telegram_utils.py
├── env_utils.py
├── requirements.txt
├── .env.example
├── known_faces/
└── captured_faces/
```

## Gereksinimler

- Python 3
- Calisan bir kamera
- Linux ortaminda ses calmak icin su komutlardan en az biri tavsiye edilir:
  - `canberra-gtk-play`
  - `paplay`
  - `aplay`

Python bagimliliklari:

- `face-recognition`
- `opencv-python`

## Kurulum

1. Sanal ortam olusturun:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Bagimliliklari yukleyin:

```bash
pip install -r requirements.txt
```

3. Telegram ayarlarini yapin:

```bash
cp .env.example .env
```

`.env` dosyasini duzenleyin:

```env
TELEGRAM_BOT_TOKEN=bot_tokeniniz
TELEGRAM_CHAT_ID=chat_idniz
```

## Known Faces Yapisi

Taninan kisileri `known_faces/` altina ekleyin.

Tek dosya olarak:

```text
known_faces/
└── ayse.jpg
```

Klasor bazli olarak:

```text
known_faces/
└── ali/
    ├── 1.jpg
    └── 2.jpg
```

Alt klasor kullanildiginda kisi adi klasor isminden alinir.

## Calistirma

```bash
python main.py
```

## Uygulama Davranisi

- Kamerada yeni bir yuz belirdiginde Telegram grubuna yuz fotografi gonderilir.
- Kisi taniniyorsa Telegram fotograf aciklamasinda ismi yazilir.
- Kisi taninmiyorsa aciklama `yabanci birisi var` olarak gider.
- Tanidik kisi geldiyse ek olarak sistemden zil sesi calar.
- Zil 10 saniye boyunca calar.
- Zil tekrar tetiklenmeden once 45 saniye beklenir.
- Telegram fotograf bildirimi tekrar tetiklenmeden once 30 saniye beklenir.

## Klavye Kisayollari

- `s`: Algilanan yabanci kisiyi kaydetmek icin yuz snapshot serisi alir
- `b`: Parlakligi artirir
- `n`: Parlakligi azaltir
- `Esc`: Uygulamadan cikar

## Yeni Kisi Ekleme

1. Kamerada taninmayan bir yuz gorunurken `s` tusuna basin.
2. Terminalde kisi adini girin.
3. Uygulama 5 farkli yuz snapshot'i alir.
4. Gorseller hem `captured_faces/` klasorune hem de `known_faces/<kisi_adi>/` altina kaydedilir.
5. Yuz encodings yeniden yuklenir.

## Telegram Notlari

- Botun hedef gruba ekli oldugundan emin olun.
- Dogru `TELEGRAM_CHAT_ID` kullanin.
- Test icin dogrudan su istegi kullanabilirsiniz:

```bash
source .env
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage?chat_id=$TELEGRAM_CHAT_ID&text=Test+message"
```

## Notlar

- `face-recognition` kutuphanesi sisteminizde ek derleme bagimliliklari isteyebilir.
- Kamera acilisinda once V4L2, sonra varsayilan OpenCV backend'i denenir.
- `.env` dosyasi repoya dahil edilmez; ornek dosya olarak sadece `.env.example` tutulur.
