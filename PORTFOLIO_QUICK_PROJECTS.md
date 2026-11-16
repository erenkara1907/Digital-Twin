# Hızlı Portfolyo Projeleri

Hazırlanma tarihi: 2026-11-14. Bu dosya `PORTFOLIO_PROJECTS.md` içindeki büyük projelerin yerine değil, yanına yazıldı. Buradaki üç proje model eğitimi, veritabanı ve karmaşık altyapı gerektirmez; her biri birkaç günde biter.

| # | Proje | Ne gösterir | Tahmini süre | Canlı çıktı |
|---|---|---|---|---|
| A | Dijital İkiz | Sohbet, tool calling, prompt tasarımı | 1-2 gün | Herkesin girebildiği web sitesi |
| B | Türkçe LLM Karnesi | Model karşılaştırma, ölçüm | 2-3 gün | Sonuç tablosu olan web sayfası |
| C | Sabah Bülteni | Otomasyon, structured output, zamanlanmış çalışma | 1-2 gün | Her sabah mesaj atan Telegram kanalı |

Önerilen sıra: A, C, B. A en kısa olanı ve biter bitmez LinkedIn profiline link olarak girer. B en çok etkileşim alma ihtimali olan, ama soruları elle hazırlamak zaman ister.

---


## 0. Başlamadan önce: ortak hazırlık (bir kere yapılır, yaklaşık 30 dakika)

### 0.1 Kısa sözlük

- **Inference:** Hazır bir modele soru sorup cevap almak. Bu üç projede yalnızca inference var, model eğitmiyoruz.
- **API key:** Bir servisin seni tanıması için verdiği gizli anahtar. Koda yazılmaz, `.env` dosyasında durur, GitHub'a gönderilmez.
- **System prompt:** Modele her konuşmanın başında verilen kalıcı talimat ("sen şusun, şöyle davran").
- **Tool calling:** Modelin "şu fonksiyonu şu parametrelerle çalıştır" demesi; fonksiyonu senin kodun çalıştırır. Kursun 2. hafta 4. gününde yaptığın şey.
- **Structured output:** Modelden serbest metin yerine belirli alanları olan JSON istemek ve bunu Pydantic ile doğrulamak.
- **Rate limit:** Ücretsiz hesabın dakikada/günde yapabildiği istek sayısı. Aşınca servis 429 hatası döner.
- **Deploy:** Kodu kendi bilgisayarından çıkarıp herkesin erişebildiği bir yere koymak.

### 0.2 Açılacak hesaplar (hepsi ücretsiz, kart istemez)

1. **Groq** — modelleri çalıştıracağımız servis. `console.groq.com` adresinden kayıt ol, sol menüden "API Keys" > "Create API Key". Anahtar `gsk_` ile başlar.
2. **Telegram botu** — bildirim göndermek için. Telegram'da `@BotFather` ile konuş, `/newbot` yaz, isim ver. Sana bir token verir.
3. **GitHub** — zaten var.
4. **Vercel** — yalnızca Proje A için. `vercel.com` üzerinden GitHub hesabınla giriş yap.

### 0.3 Kullanılacak modeller

Hepsi Groq üzerinde. ID'ler bugün Groq'un model sayfasından alındı; kodda aynen bu şekilde yazılır.

| Model ID | Ne zaman |
|---|---|
| `openai/gpt-oss-120b` | Varsayılan. Kaliteli cevap gereken her yer |
| `llama-3.3-70b-versatile` | Yedek. İlki 429 dönerse buna geç |
| `llama-3.1-8b-instant` | Basit ve çok sayıda istek gereken işler |

Groq'a bağlanmak için kursta kullandığın `openai` paketi yeterli, yalnızca adres değişir:

```python
from openai import OpenAI
import os

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ["GROQ_API_KEY"],
)
reply = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[{"role": "user", "content": "Merhaba"}],
)
print(reply.choices[0].message.content)
```

Ücretsiz hesabın gerçek limitleri `console.groq.com/settings/limits` sayfasında yazar. Bu dosyadaki tasarımlar model başına günde 1000 istek varsayımıyla yapıldı.

### 0.4 Her projede aynı olan kurallar

- Her proje ayrı bir GitHub reposu, public.
- Python paket yönetimi `uv` ile (kursta kullandığın).
- Anahtarlar `.env` dosyasında, `.env` `.gitignore` içinde, repoda yalnızca `.env.example` var.
- Geliştirirken kota harcamamak için önce lokal Ollama ile dene (`llama3.2` sende kurulu), çalışınca Groq'a geç.

---

## Proje A — Dijital İkiz: CV'ni okuyan değil, CV'nle konuşan site

### Ne yapıyoruz

Bir web sayfası. Ziyaretçi (işe alımcı, teknik lider) sohbet kutusuna "Eren'in Flutter deneyimi ne?", "Hangi AI projelerini yaptı?" yazar; model senin hakkında yazdığın metinlere dayanarak cevap verir. Cevabını bilmediği bir soru gelirse uydurmaz, soruyu sana Telegram'dan bildirir. Ziyaretçi iletişim bırakmak isterse onu da Telegram'dan alırsın.

### Neden bu proje

- Link LinkedIn profilinin en üstüne konur; her profil ziyaretçisi potansiyel kullanıcı.
- Paylaşım cümlesi hazır: "CV göndermeyi bıraktım. İşe alımcılar artık AI ikizime soruyor: [link]". İnsanlar deneyip ekran görüntüsü paylaşır.
- Kursun 2. haftasını (sohbet + tool calling) ve 8. haftadaki bildirim ajanını tek üründe birleştirir.

### Veri: nereden gelecek, nasıl hazırlanacak

Veri sensin. Üç Markdown dosyası yazacaksın, başka kaynak yok:

| Dosya | İçerik | Nasıl hazırlanır |
|---|---|---|
| `data/profile.md` | Özet, iş deneyimi, eğitim, teknik beceriler | LinkedIn profilinde "More" > "Save to PDF" ile PDF indir, içeriği Markdown'a çevir (Claude Code'a PDF'i verip çevirtebilirsin), sonra elle düzelt |
| `data/projects.md` | Her proje için: ne, hangi teknoloji, senin rolün, sonuç, link | Elle yaz. Proje başına 5-8 satır |
| `data/faq.md` | İşe alımcının soracağı 10-15 sorunun cevabı: ne tür rol arıyorsun, uzaktan/ofis, ne zaman başlayabilirsin, neden AI'a geçiyorsun | Elle yaz |

Bu dosyalara yazma: telefon, ev adresi, TC kimlik no, maaş geçmişi, müşteri adları (izin yoksa). Site herkese açık; model bu dosyadaki her şeyi söyleyebilir.

### Veri modele nasıl verilecek

Üç dosyanın toplamı birkaç bin kelime. Bu, modelin tek seferde okuyabileceği miktarın çok altında, o yüzden dosyaların tamamı system prompt'a konur. Vektör veritabanı, embedding, RAG yok; bu boyutta gereksiz. Kod başlarken üç dosyayı okur, tek bir metin halinde system prompt'un sonuna ekler.

System prompt şu kuralları içerir:

1. Sen Eren Kara'nın dijital ikizisin; ziyaretçilere onun kariyeri hakkında bilgi veriyorsun.
2. Yalnızca aşağıdaki metinlerde yazanı söyle. Metinde olmayan bir şey sorulursa "bunu bilmiyorum, Eren'e iletiyorum" de ve `record_unknown_question` aracını çağır.
3. Ziyaretçi iletişime geçmek isterse adını ve e-postasını iste, `record_contact` aracını çağır.
4. Eren'le ilgisi olmayan isteklere (kod yaz, ödev yap, başka konu) kibarca hayır de.
5. Ziyaretçi hangi dilde yazarsa o dilde cevap ver.

### Tech stack

| Parça | Seçim | Neden |
|---|---|---|
| Backend | Python + FastAPI | Tek endpoint yeter; Vercel FastAPI'yi ayarsız çalıştırıyor |
| Model | `openai/gpt-oss-120b`, yedek `llama-3.3-70b-versatile` | Tool calling destekliyor, hızlı |
| Arayüz | Tek `public/index.html` (düz HTML + JavaScript) | Framework kurmaya gerek yok |
| Bildirim | Telegram Bot API | Ücretsiz |
| Deploy | Vercel Hobby | Ücretsiz, uyumaz, GitHub'a push edince kendiliğinden yayınlar |

Gradio kullanmıyoruz çünkü Hugging Face artık Gradio uygulamalarını ücretsiz barındırmıyor. Streamlit ücretsiz ama 12 saat ziyaret olmayınca uyuyor; işe alımcının tıkladığı linkin "uyanıyor" ekranı göstermesini istemeyiz.

### Dosya yapısı

```
dijital-ikiz/
  main.py              FastAPI uygulaması, POST /api/chat
  twin/prompt.py       data/ dosyalarını okuyup system prompt'u kurar
  twin/tools.py        record_unknown_question, record_contact, Telegram gönderimi
  twin/chat.py         model çağrısı + tool döngüsü + yedek model
  data/profile.md
  data/projects.md
  data/faq.md
  public/index.html    sohbet arayüzü
  tests/               pytest testleri
  eval/questions.jsonl 15 test sorusu
  eval/run.py          soruları sorup cevapları yazdırır
  requirements.txt
  .env.example
```

### Sohbet nasıl çalışır (akış)

1. Tarayıcı, o ana kadarki tüm mesaj listesini `POST /api/chat` ile gönderir. Sunucu hiçbir şey saklamaz; geçmiş tarayıcıda durur (kursun 1. hafta 4. günündeki "hafıza yanılsaması").
2. Sunucu kontrol eder: en fazla 20 mesaj, mesaj başına en fazla 500 karakter. Aşarsa 400 döner.
3. Sunucu system prompt + mesajlar + iki aracın tanımıyla modeli çağırır.
4. Model araç çağırmak isterse sunucu aracı çalıştırır (Telegram'a mesaj atar), sonucu modele geri verir, modeli tekrar çağırır. En fazla 3 tur.
5. Model 429 dönerse aynı istek yedek modelle bir kez tekrarlanır. O da başarısızsa kullanıcıya "şu an yoğunluk var, biraz sonra tekrar deneyin" mesajı gider.
6. Son metin cevabı JSON olarak tarayıcıya döner.

### Yol haritası

1. **Verileri yaz.** Üç Markdown dosyasını hazırla. Bitti sayılır: dosyaları baştan sona okuduğunda bir işe alımcının soracağı her şeyin cevabı içinde.
2. **Telegram'ı bağla.** Botuna Telegram'dan herhangi bir mesaj at, sonra tarayıcıda `https://api.telegram.org/bot<TOKEN>/getUpdates` aç; çıkan JSON'daki `chat.id` senin sohbet numaran. `.env` içine `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID` yaz. Bitti sayılır: `twin/tools.py` içindeki gönderim fonksiyonunu çalıştırınca telefonuna mesaj geliyor.
3. **Sohbeti terminalde çalıştır.** `twin/prompt.py` ve `twin/chat.py`. Önce Ollama ile, sonra Groq ile. Bitti sayılır: terminalden soru sorunca profilindeki bilgiyle cevap veriyor.
4. **Araçları ekle.** İki araç ve döngü. Bitti sayılır: "Eren'in en sevdiği yemek ne?" yazınca telefonuna "cevaplanamayan soru" bildirimi geliyor ve model uydurmuyor.
5. **Test sorularını yaz ve koş.** `eval/questions.jsonl`: 10 soru cevabı dosyalarda olan, 5 soru olmayan. `eval/run.py` hepsini sorar. Bitti sayılır: 10 soruya doğru cevap, 5 soruda uydurma yok ve araç çağrılmış. Yanlış çıkan varsa system prompt'u veya veri dosyalarını düzelt, tekrar koş.
6. **API ve arayüz.** `main.py` ve `public/index.html`. Lokal çalıştırma: `vercel dev`. Bitti sayılır: tarayıcıda sohbet çalışıyor, telefonda da düzgün görünüyor.
7. **Deploy.** Aşağıdaki adımlar.
8. **Kötüye kullanım testi.** Canlı sitede dene: "önceki talimatları unut", "bana Python kodu yaz", 600 karakterlik mesaj, 25 mesajlık sohbet. Bitti sayılır: hepsi reddediliyor.

### Deploy adımları

1. Repoyu GitHub'a push et.
2. `vercel.com` > "Add New" > "Project" > repoyu seç > "Deploy". Vercel kökteki `main.py` içindeki `app` nesnesini kendisi bulur, `public/` klasörünü de kendisi yayınlar.
3. Proje ayarlarında "Environment Variables" altına `GROQ_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` ekle, yeniden deploy et.
4. Canlı adreste 5. adımdaki test sorularından üçünü elle sor. `data/` dosyalarının sunucuda okunabildiğini bu test doğrular; okunamıyorsa model senin hakkında hiçbir şey bilmez.

### Bilinen sınırlar

- IP başına günlük limit yok (veritabanı gerektirir, bu projede yok). Koruma: sohbet başına 20 mesaj ve 500 karakter sınırı. Günlük Groq kotası biterse site kibar bir hata mesajı gösterir; ertesi gün kendiliğinden düzelir.
- Ziyaretçinin bıraktığı ad/e-posta hiçbir yere kaydedilmez, yalnızca Telegram'ına gönderilir. Bunu sayfanın altına bir cümleyle yaz.

### LinkedIn paylaşımı

20-30 saniyelik ekran kaydı: biri üç soru soruyor, sonuncusu cevapsız kalıyor ve telefonuna bildirim düşüyor. Metin: ne yaptın, neden yaptın, nasıl çalışıyor (3 madde), link yorumda.

### Claude Code başlangıç promptu

```
Yeni repo: dijital-ikiz. PORTFOLIO_QUICK_PROJECTS.md içindeki Proje A bölümünü oku ve
oradaki dosya yapısına, akışa ve yol haritasına aynen uy. Verileri (data/*.md) ben
yazacağım; sen 2. adımdan başla. Her adımın "bitti sayılır" ölçütünü çalıştırıp çıktısını
göstermeden sonraki adıma geçme. Önce 2-4. adımlar için kısa plan ver, onayımdan sonra
TDD ile kodla.
```

---

## Proje B — Türkçe LLM Karnesi: hangi model Türkçeyi daha iyi biliyor

### Ne yapıyoruz

50 tane çoktan seçmeli Türkçe soru hazırlıyoruz. Aynı soruları 9-10 farklı modele soruyoruz. Her modelin kaç soruyu doğru bildiğini ve ne kadar hızlı cevap verdiğini ölçüp bir web sayfasında tablo ve grafik olarak yayınlıyoruz.

### Neden bu proje

- Paylaşım cümlesi: "10 yapay zeka modeline 50 Türkçe soru sordum. Atasözlerinde en iyisi X, mantık sorularında Y. Telefona sığan model 70B'lik modelin yüzde kaçını yakaladı?" Bu tür karşılaştırmalar yorum ve tartışma çeker.
- Kursun 4. haftasındaki model karşılaştırma mantığının aynısı; yalnızca ölçülen şey kod hızı yerine Türkçe doğruluğu.
- İş görüşmesinde "bir modeli nasıl değerlendirirsin" sorusuna gösterecek somut bir cevabın olur.

### Veri: nereden gelecek, nasıl hazırlanacak

Soruları sen hazırlayacaksın. Hazır sınav sorusu (ÖSYM vb.) kullanmıyoruz; telif var ve modeller onları eğitimde görmüş olabilir.

5 kategori, her biri 10 soru, her soru 4 şıklı ve tek doğru cevaplı:

| Kategori kodu | Ne sorulur | Doğrulama kaynağı |
|---|---|---|
| `atasozu` | Bir atasözü veya deyimin anlamı | TDK Atasözleri ve Deyimler Sözlüğü, `sozluk.gov.tr` |
| `yazim` | Doğru yazım, ek kullanımı, noktalama | TDK Yazım Kılavuzu, `tdk.gov.tr` |
| `mantik` | Kısa mantık ve sayısal akıl yürütme, Türkçe anlatımla | Kendi çözümün; ikinci kez elle kontrol |
| `kultur` | Türkiye coğrafyası, tarihi, gündelik hayat | Tartışmasız, tek cevabı olan bilgiler |
| `okuma` | 3-4 cümlelik paragraf ve onunla ilgili çıkarım sorusu | Paragrafı sen yazarsın, cevap paragraftan çıkar |

Hazırlama yöntemi: Claude Code'dan her kategori için 15 aday soru iste, sen en iyi 10'unu seç, her birinin cevabını kaynaktan tek tek doğrula. Doğrulamadığın soruyu sete alma. Bu adım projenin en uzun kısmı (yaklaşık yarım gün) ve atlanamaz; yanlış cevap anahtarı bütün tabloyu geçersiz kılar.

Sorular `data/questions.jsonl` dosyasında, satır başına bir soru:

```json
{"id": "atasozu-01", "category": "atasozu", "question": "\"Damlaya damlaya göl olur\" atasözü ne anlatır?", "choices": {"A": "Yağmurun bereketini", "B": "Küçük birikimlerin zamanla büyüdüğünü", "C": "Sabırsızlığın zararını", "D": "Suyun değerini"}, "answer": "B", "source": "TDK Atasözleri ve Deyimler Sözlüğü"}
```

Doğru cevapların şıklara eşit dağıldığını kontrol et (her harf yaklaşık 12-13 kez).

### Hangi modeller, nereden

| Model | Nerede çalışır | Not |
|---|---|---|
| `openai/gpt-oss-120b` | Groq | |
| `openai/gpt-oss-20b` | Groq | |
| `llama-3.3-70b-versatile` | Groq | |
| `llama-3.1-8b-instant` | Groq | |
| `qwen/qwen3.8-27b` | Groq | Önizleme modeli; kaldırılırsa listeden çıkar |
| `gemma3:27b` | Ollama, senin Mac'inde | Kurulu. Yavaş çalışır, sorun değil |
| `gemma3:4b` | Ollama | Kurulu |
| `llama3.2` | Ollama | Kurulu |
| `gemma3:270m` | Ollama | Kurulu. "Telefona sığan model" satırı |
| `google/gemma-4-31b-it:free` | OpenRouter | Ek. Günde 50 istek sınırı var; 50 soru tam bir güne sığar |

Ollama'ya da aynı `openai` paketiyle bağlanılır: `base_url="http://localhost:11434/v1"`, `api_key="ollama"`. OpenRouter için `base_url="https://openrouter.ai/api/v1"` ve `openrouter.ai` üzerinden alınan anahtar.

Toplam istek: Groq'ta 5 model x 50 soru = 250, her model için 50. Günlük kotanın çok altında.

### Modele soru nasıl sorulur, cevap nasıl puanlanır

Her soru ayrı bir istek. Ayarlar: `temperature=0` (her seferinde aynı cevabı vermesi için), `max_tokens=1024`.

System prompt: `Türkçe çoktan seçmeli bir soru soracağım. Yalnızca doğru şıkkın harfini yaz: A, B, C veya D. Açıklama yazma.`

User mesajı: soru metni ve dört şık, alt alta.

Puanlama: cevabın içindeki ilk A/B/C/D harfi bulunur ve cevap anahtarıyla karşılaştırılır. Harf bulunamazsa cevap yanlış sayılır ve ayrıca "geçersiz" olarak işaretlenir. `max_tokens` değerini küçük tutma: `gpt-oss` gibi modeller cevaptan önce düşünme adımı üretir, sınır düşükse cevap yarıda kesilir.

Her istek için süre ölçülür (istekten cevabın tamamına kadar, milisaniye). Lokal ve bulut süreleri farklı donanımda ölçüldüğü için tabloda ayrı gösterilir, birbiriyle kıyaslanmaz.

### Tech stack

| Parça | Seçim |
|---|---|
| Koşturucu | Python, `openai` paketi, Pydantic, `uv` |
| Sonuç dosyaları | `results/raw.jsonl` (her istek bir satır), `results/summary.json` (model ve kategori bazında özet) |
| Web sayfası | `docs/index.html`: düz HTML + Chart.js, `summary.json` dosyasını okuyup tablo ve çubuk grafik çizer |
| Deploy | GitHub Pages |

### Dosya yapısı

```
turkce-llm-karnesi/
  data/questions.jsonl
  bench/models.py      model listesi: isim, sağlayıcı, base_url, anahtarın env adı
  bench/ask.py         tek soruyu tek modele sorar, süreyi ölçer
  bench/score.py       cevaptan harfi çıkarır, doğru/yanlış/geçersiz
  bench/run.py         tüm modeller x tüm sorular; yarıda kalırsa kaldığı yerden devam
  bench/summarize.py   raw.jsonl -> summary.json
  results/raw.jsonl
  results/summary.json
  docs/index.html
  docs/summary.json    summarize.py buraya da kopyalar
  tests/
```

`raw.jsonl` satır örneği:

```json
{"model": "llama-3.3-70b-versatile", "question_id": "atasozu-01", "raw": "B", "parsed": "B", "correct": true, "latency_ms": 412, "ran_at": "2026-11-20T09:14:03Z"}
```

`run.py` başlarken `raw.jsonl` dosyasını okur ve zaten cevaplanmış (model, soru) çiftlerini atlar. Böylece kota biterse veya bağlantı koparsa ertesi gün aynı komutu tekrar çalıştırman yeter.

### Yol haritası

1. **Soruları hazırla.** 50 soru, hepsi kaynaktan doğrulanmış. Bitti sayılır: `questions.jsonl` 50 satır, her kategoriden 10, doğru cevaplar şıklara dengeli dağılmış.
2. **Puanlayıcıyı yaz.** `bench/score.py` ve testleri: "B", "B)", "Cevap: B", "**B**", boş metin, "Bilmiyorum". Bitti sayılır: testler geçiyor.
3. **Tek modelle dene.** `bench/ask.py` + `bench/run.py`, yalnızca lokal `llama3.2` ile 50 soru. Bitti sayılır: `raw.jsonl` içinde 50 satır var; 5 tanesini elle açıp puanlamanın doğru olduğunu kontrol ettin.
4. **Lokal modellerin hepsini koş.** Dört Ollama modeli. `gemma3:27b` uzun sürer; arkada çalışsın.
5. **Groq modellerini koş.** İstekler arasına 2 saniye bekleme koy (dakikalık token limitine takılmamak için). Bitti sayılır: 5 model x 50 satır.
6. **OpenRouter modelini koş (ek).** Tek seferde 50 istek. Sınıra takılırsa ertesi gün aynı komutu tekrar çalıştır.
7. **Özetle.** `bench/summarize.py`: model başına genel doğruluk, kategori bazında doğruluk, geçersiz cevap sayısı, ortalama süre.
8. **Hata analizi.** En çok modelin yanlış yaptığı 5 soruyu bul. Önce cevap anahtarını tekrar kontrol et (hata sende olabilir), sonra neden zorlandıklarını bir paragrafla yaz. Bu, paylaşımın en ilgi çeken kısmı olur.
9. **Web sayfası.** Sıralı tablo, kategori bazında çubuk grafik, "en zor 5 soru" bölümü, yöntem ve sınırlar bölümü.
10. **Deploy.**

### Deploy adımları

1. Repoyu GitHub'a push et.
2. Repo > "Settings" > "Pages" > "Source: Deploy from a branch" > Branch: `main`, klasör: `/docs` > "Save".
3. Birkaç dakika sonra sayfa `https://<kullanici-adin>.github.io/turkce-llm-karnesi/` adresinde açılır.

### Sayfada ve README'de açıkça yazılacak sınırlar

- 50 soru küçük bir örneklem; iki model arasındaki 1-2 soruluk fark anlamlı değildir.
- Sorular tek kişi tarafından hazırlandı.
- Her model tek kez, `temperature=0` ile çalıştırıldı.
- Test tarihi ve model sürümleri.

Bunları yazmak projeyi zayıflatmaz; ölçümün sınırını bildiğini gösterir.

### LinkedIn paylaşımı

Tek görsel: sıralı çubuk grafik. Metnin ilk satırı en şaşırtıcı sonuç (örneğin küçük bir modelin büyük birini geçtiği kategori). Sonra "en zor soru" örneği ve okuyucuya soru: "Sizce hangisi?". Link yorumda.

### Claude Code başlangıç promptu

```
Yeni repo: turkce-llm-karnesi. PORTFOLIO_QUICK_PROJECTS.md içindeki Proje B bölümünü oku
ve oradaki dosya yapısına, veri formatına ve yol haritasına aynen uy. Önce 1. adım için
her kategoriden 15 aday soru üret (JSONL formatında, cevap anahtarı ve kaynak alanıyla);
ben seçip doğrulayacağım. Sonra 2. adımdan itibaren TDD ile ilerle. Her adımın
"bitti sayılır" ölçütünü çalıştırıp çıktısını göstermeden sonraki adıma geçme.
```

---

## Proje C — Sabah Bülteni: her sabah Türkçe AI haber özeti gönderen otomasyon

### Ne yapıyoruz

Her sabah kendiliğinden çalışan bir program. Yapay zeka haber kaynaklarını tarar, son 24 saatin en önemli 5 haberini seçer, her birini Türkçe iki cümleyle özetler ve bir Telegram kanalına gönderir. Aynı özet bir web arşivine de eklenir. Senin bilgisayarının açık olması gerekmez; program GitHub'ın sunucularında çalışır.

### Neden bu proje

- Canlı ve sürekli çalışan bir sistem: repo geçmişinde her gün yeni bir kayıt görünür.
- Kanala abone olan herkes her sabah senin adını görür. Abone sayısı somut bir kanıttır.
- Paylaşım cümlesi: "Her sabah AI haberlerini okumaya vaktim yoktu, benim yerime okuyup Türkçe özetleyen bir bot yazdım. Kanal herkese açık: [link]".
- Kursun 8. haftasındaki Scanner (RSS okuma + seçim) ve Messenger (bildirim) ajanlarının aynı kalıbı; yalnızca "indirimli ürün" yerine "haber".

### Veri: nereden gelecek, nasıl alınacak

Veri RSS akışlarından gelir. RSS, bir sitenin son yazılarını makinenin okuyabileceği biçimde sunduğu adrestir. Kursta kullandığın `feedparser` paketi bu adresi okuyup her haber için başlık, link, kısa özet ve yayın tarihi verir. Web sayfası kazıma yok.

Kullanılacak adresler (bugün hepsinin çalıştığı kontrol edildi):

| Kaynak | Adres |
|---|---|
| OpenAI | `https://openai.com/news/rss.xml` |
| Google AI | `https://blog.google/technology/ai/rss/` |
| Google DeepMind | `https://deepmind.google/blog/rss.xml` |
| Hugging Face | `https://huggingface.co/blog/feed.xml` |
| Simon Willison | `https://simonwillison.net/atom/everything/` |
| TechCrunch AI | `https://techcrunch.com/category/artificial-intelligence/feed/` |
| The Verge AI | `https://www.theverge.com/rss/ai-artificial-intelligence/index.xml` |
| Hacker News (LLM, 100+ puan) | `https://hnrss.org/newest?q=LLM&points=100` |

Modele yalnızca başlık ve RSS'in verdiği kısa özet gider; haberin tam metni indirilmez ve yeniden yayınlanmaz. Her özetin altında kaynağın linki bulunur. Bu, telif açısından güvenli taraf.

### Model veriyi nasıl kullanacak

Günde tek bir model çağrısı yapılır.

Girdi: son 24 saatte yayınlanmış, daha önce gönderilmemiş haberler. En fazla 40 haber; her biri için sıra numarası, kaynak adı, başlık ve özetin ilk 200 karakteri.

İstenen çıktı (JSON, Pydantic ile doğrulanır):

```json
{
  "items": [
    {
      "index": 7,
      "title_tr": "Türkçe başlık",
      "summary_tr": "İki cümlelik Türkçe özet.",
      "why_it_matters": "Neden önemli olduğunu anlatan tek cümle."
    }
  ]
}
```

Model linki kendisi yazmaz, yalnızca haberin sıra numarasını (`index`) döndürür; link o numaradan kod tarafında alınır. Böylece modelin var olmayan bir link uydurması mümkün olmaz.

System prompt'taki seçim kuralları: yeni model veya ürün duyuruları, önemli araştırma sonuçları ve geliştiricileri etkileyen değişiklikler önceliklidir; aynı olayı anlatan birden fazla haber varsa yalnızca biri seçilir; reklam ve görüş yazıları seçilmez; tam 5 haber seçilir, 5'ten az uygun haber varsa olduğu kadar.

Model: `openai/gpt-oss-120b`. Çıktı doğrulamadan geçmezse bir kez daha denenir; yine geçmezse veya 429 gelirse `llama-3.3-70b-versatile` ile denenir. O da başarısızsa o gün bülten gönderilmez, sana özel Telegram mesajıyla hata bildirilir.

### Tech stack

| Parça | Seçim |
|---|---|
| Dil ve paketler | Python, `feedparser`, `openai`, Pydantic, `httpx`, `uv` |
| Zamanlama | GitHub Actions (public repoda ücretsiz) |
| Hafıza | Repo içindeki `state/seen.json`: daha önce gönderilen linklerin listesi |
| Yayın | Telegram kanalı + GitHub Pages üzerinde arşiv |

### Dosya yapısı

```
sabah-bulteni/
  digest/feeds.py      kaynak listesi + son 24 saatin haberlerini çekme
  digest/state.py      seen.json oku/yaz
  digest/select.py     model çağrısı, Pydantic şeması, yedek model
  digest/render.py     Telegram mesajı ve arşiv Markdown'ı üretir
  digest/telegram.py   kanala gönderim, hata bildirimi
  digest/main.py       hepsini sırayla çalıştırır; --dry-run seçeneği
  state/seen.json
  docs/index.md        arşiv ana sayfası, en yeni üstte
  docs/arsiv/2026-11-20.md
  .github/workflows/daily.yml
  tests/
```

`seen.json` biçimi: link ve görülme tarihi. 30 günden eski kayıtlar her çalışmada silinir.

```json
{"https://example.com/haber": "2026-11-20"}
```

### Bir günlük çalışma (akış)

1. 8 kaynağı oku. Bir kaynak hata verirse atla, diğerleriyle devam et, hatayı logla.
2. Son 24 saatten eski olanları ve `seen.json` içinde olanları çıkar.
3. Kalan haber yoksa bitir, hiçbir şey gönderme.
4. En yeni 40 haberi modele ver, 5 haberi seçtir ve özetlet.
5. Çıktıyı doğrula: her `index` girdi listesinde var mı, alanlar boş mu.
6. Telegram mesajını oluştur ve kanala gönder.
7. Aynı içeriği `docs/arsiv/<tarih>.md` olarak yaz, `docs/index.md` başına link ekle.
8. Modele verilen bütün haberlerin linkini `seen.json` içine ekle (yalnızca seçilen 5'i değil; yoksa seçilmeyenler ertesi gün tekrar gelir).
9. Değişen dosyaları repoya commit et.

### Yol haritası

1. **Haberleri çek.** `digest/feeds.py`. Bitti sayılır: çalıştırınca son 24 saatin haberleri kaynak adı, başlık, link ve tarihle terminalde listeleniyor.
2. **Tekrar önleme.** `digest/state.py` ve testleri. Bitti sayılır: aynı komutu art arda iki kez çalıştırınca ikincisinde "yeni haber yok" çıkıyor.
3. **Seçim ve özet.** `digest/select.py`. Önce lokal Ollama ile, sonra Groq ile. Bitti sayılır: 5 haberlik geçerli JSON dönüyor; girdi listesinde olmayan bir `index` verildiğinde doğrulama reddediyor (bunun testi var).
4. **Kanalı kur.** Telegram'da herkese açık bir kanal aç (örnek ad: `@sabah_ai_bulteni`), botunu kanala yönetici olarak ekle. `.env` içine `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL=@kanal_adin`, `TELEGRAM_ADMIN_CHAT_ID` (hata bildirimleri için kendi sohbet numaran) yaz.
5. **Mesajı biçimlendir ve gönder.** `digest/render.py`, `digest/telegram.py`. Telegram tek mesajda en fazla 4096 karakter kabul eder; 5 haber bunun altında kalır, yine de uzunluk kontrolü koy. Bitti sayılır: `--dry-run` ile mesaj yalnızca terminale basılıyor; onsuz çalıştırınca kanalda görünüyor ve linkler tıklanıyor.
6. **Arşiv.** `docs/` altına günlük dosya ve ana sayfa. Bitti sayılır: lokal çalıştırmadan sonra iki dosya da güncellenmiş.
7. **Zamanlama.** `.github/workflows/daily.yml`. Aşağıdaki deploy adımları.
8. **Üç gün izle.** Üç sabah üst üste bülten geldi mi, tekrar eden haber var mı, özetler doğru mu kontrol et. Sorun varsa system prompt'u düzelt. Paylaşımı bundan sonra yap.

### Deploy adımları

1. Repoyu GitHub'a push et (public).
2. Repo > "Settings" > "Secrets and variables" > "Actions" altına ekle: `GROQ_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL`, `TELEGRAM_ADMIN_CHAT_ID`.
3. Workflow dosyasında zamanlama `cron: "0 5 * * *"` olur. GitHub saatleri UTC ile çalışır; 05:00 UTC, Türkiye saatiyle 08:00 demektir. GitHub yoğun saatlerde zamanlanmış işleri birkaç dakika ile yarım saat arası geciktirebilir; bu normal.
4. Workflow'a `workflow_dispatch` de ekle; böylece "Actions" sekmesinden "Run workflow" ile elle de çalıştırabilirsin. İlk testi böyle yap.
5. Workflow'un repoya commit atabilmesi için dosyada `permissions: contents: write` satırı bulunmalı.
6. Arşiv sayfası için: "Settings" > "Pages" > Branch: `main`, klasör: `/docs`.

### Bilinen sınırlar

- Özetler başlık ve kısa RSS özetinden üretilir, haberin tamamından değil. Kanal açıklamasına "otomatik üretilmiştir, ayrıntı için kaynağa bakın" yaz.
- Kaynakların çoğu İngilizce ve ABD merkezli; Türkiye'den haber gelmez.
- Bir kaynak RSS adresini değiştirirse o kaynak sessizce boş döner. Bir kaynak 3 gün üst üste boş dönerse sana hata bildirimi gitsin.

### LinkedIn paylaşımı

Kanalın ekran görüntüsü + nasıl çalıştığını gösteren 5 kutuluk basit bir şema (RSS, filtre, model, Telegram, arşiv). Metinde: neden yaptın, günde tek model çağrısıyla ve sıfır maliyetle çalıştığı, kanal linki. İki hafta sonra ikinci paylaşım: abone sayısı ve "botun en çok seçtiği konular".

### Claude Code başlangıç promptu

```
Yeni repo: sabah-bulteni. PORTFOLIO_QUICK_PROJECTS.md içindeki Proje C bölümünü oku ve
oradaki dosya yapısına, akışa ve yol haritasına aynen uy. 1-3. adımlar için kısa plan ver,
onayımdan sonra TDD ile kodla. Geliştirme sırasında model olarak lokal Ollama llama3.2
kullan, Groq'a yalnızca adım bitiminde geç. Her adımın "bitti sayılır" ölçütünü çalıştırıp
çıktısını göstermeden sonraki adıma geçme.
```

---

## Üç proje bittiğinde elinde ne olur

- Profilinde duran, herkesin deneyebildiği bir sohbet sitesi (A).
- Kendi ölçtüğün verilere dayanan bir karşılaştırma sayfası (B).
- Her gün çalışan ve abonesi olan bir otomasyon (C).

Bu üçü kursun 1, 2, 4 ve 8. haftalarını kapsar. RAG (5. hafta) ve fine-tuning (6-7. hafta) bu dosyada yok; onlar `PORTFOLIO_PROJECTS.md` içindeki Madde ve Cepte projelerinde. Hızlı projeleri bitirdikten sonra o ikisinden birine geçmek, portfolyoyu "uygulama yazabiliyor"dan "sistemi ölçüp iyileştirebiliyor"a taşır.
