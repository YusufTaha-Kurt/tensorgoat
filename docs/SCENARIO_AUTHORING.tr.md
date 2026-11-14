# Senaryo yazma

[English](SCENARIO_AUTHORING.md) · **Türkçe**

Senaryo bir klasördür. Klasörü, çözümünü ve sınamasını eklediğinizde kayıt
düzeneği onu kendiliğinden bulur. Kodda düzenlenecek bir liste yoktur (tek
istisna, servis senaryoları için Docker compose dosyasıdır).

Önce [ARCHITECTURE.tr.md](ARCHITECTURE.tr.md) içindeki tasarım ilkelerini
okuyunuz. Kısacası: yalnız işlemci, yalnız numpy ve scikit-learn, çevrimdışı,
belirlenimci, sentetik veri, zararsız, çözülebildiği kanıtlı, kısa yolları
kapalı, savunması anlatılmış, Python içinde oyuncuya dönük metin yok, başlangıç
düzeyi (LLM konuları yok).

## 1. Klasör şablonu

```
tensorgoat/scenarios/sNN_<kısa_ad>/
├── __init__.py            boş
├── scenario.yml           künye (dilden bağımsız)
├── generate.py            generate(ctx): dosyalar ve model
├── service.py             yalnız servis senaryoları: create_app(...)
├── model.py               isteğe bağlı: generate.py ve service.py için ortak numpy çıkarımı
├── assets/                isteğe bağlı: dosya şablonları
├── BRIEFING.en.md         hikâye ve görev, çözümü açık etmez
├── hints.en.yml           tam üç düzey
└── i18n.en.yml            başlık, özet, öğrenme hedefleri, servis iletileri

solutions/sNN_<kısa_ad>/
├── solve.py               otomatik çözüm
└── WALKTHROUGH.en.md      adım adım, Mitigation / Defense ile biter

tests/scenarios/test_sNN_<kısa_ad>.py
```

Klasör adı, `scenario.yml` içindeki `id` ve çözüm klasörü aynı olmalıdır. En
kolay başlangıç, aynı türden var olan bir senaryoyu kopyalamaktır:
`s01_hidden_weights` (dosya) ya da `s03_model_heist` (servis).

## 2. `scenario.yml`

```yaml
id: s08_example
slug: example
difficulty: easy            # intro | easy | easy-medium | medium
type: service               # artifact | service
estimated_time_minutes: 20
port: 8108                  # servis: benzersiz, 1024-65535; dosya: null
categories:
  - "OWASP ML Top 10: ML05:2023 Model Theft"
tools_suggested:
  - "numpy"
tunable_params:             # üreticinizin ayarlanabildiği her sayı
  query_budget: 50
```

- Kategori adlarını resmî OWASP ML Top 10 ve MITRE ATLAS sayfalarıyla
  karşılaştırınız. ATLAS tekniklerinin kimliğini değil **adını** yazınız.
- Başlıklar ve oyuncuya dönük öteki metinler buraya yazılmaz.

## 3. `generate.py`

```python
from tensorgoat.core.scenario import GenerationContext


def generate(ctx: GenerationContext) -> None:
    rng = ctx.rng("data")  # adlandırılmış, tohumlu rastgele akış
    ...
    ctx.write_text("notes.txt", "...")  # oyuncu dosyası, "\n" satır sonu
    ctx.save_service_params({"budget": 50}, arrays={"coef": coef})  # yalnız servis
```

Kurallar:

- **Bütün rastgelelik `ctx.rng(...)` üzerinden gelir.** `random`, tohumsuz
  numpy ve zaman damgası kullanılmaz. `np.savez` yerine `numpy_nn.save_npz`
  kullanınız.
- **Bayrak `ctx.flag` değeridir.** Depoya hiçbir zaman bayrak yazmayınız.
  Bayrak bir dosyanın içine gömülecekse burada gömünüz.
- **Oyuncu dosyaları `ctx.workspace` içine, servisin gizli bilgileri
  `ctx.internal` içine** (`ctx.save_service_params` ile) yazılır.
- **Modelleri pickle ile saklamayınız.** Ağırlıkları ya da ağaç dizilerini dışa
  aktarınız ve numpy ile hesaplayınız.
- **Kendini denetleme.** Çözülebilirlik eğitilmiş bir modele bağlıysa
  amaçlanan çözümü *ve* kapalı kısa yolları `generate` içinde doğrulayınız,
  tohum şanssızsa `ctx.rng(f"data:{attempt}")` ile yeniden deneyiniz. S04, S05
  ve S06 örnektir.
- **Hızlı ve küçük tutunuz.** Üretim ve servisin başlaması 60 saniyenin
  altında, her dosya 10 MB altında, bellek 1 GB altında olmalıdır.
- **Dosya metinleri** (çalışma alanındaki bir README, bir model kartı) Python
  dizgisine değil, şablon olarak `assets/` içine konur.

## 4. `service.py` (servis senaryoları)

```python
def create_app(flag_provider, params, default_lang="en", store=None) -> FastAPI:
    texts = ServiceTexts(SCENARIO_DIR, default_lang)
    app = new_app(texts)

    @app.get("/")
    def index(request: Request):
        lang = texts.language(request)
        return {"service": "...", "scenario": SCENARIO_ID,
                "message": texts.message("description", lang), ...}
    ...
    return app
```

- `GET /` yanıtı `"scenario": <id>` içermelidir. Çalıştırıcı bunu sağlık
  denetimi olarak kullanır. Yanıta `"endpoints"` eklerseniz web arayüzünün
  istek konsolu bunları örnek olarak sunar.
- İnsanın okuduğu metin **yalnız** `message` alanına ve **yalnız**
  `texts.message("<anahtar>", lang)` üzerinden girer. Anahtar `i18n.en.yml`
  içinde `messages:` altında tanımlanır.
- Hatalar `error_response(status, "ERROR_CODE", message)` ile döner. Hata
  kodlarınızı modülün belge dizgisinde ve ARCHITECTURE.md içindeki tabloda
  belgeleyiniz. Kodlar kalıcıdır ve hiç çevrilmez.
- Sayaçlar, verilen `StateStore` (ya da bir `MemoryStateStore`) üzerinden
  tutulur.
- Servis içinde dosya ya da ortam değişkeni okumayınız. Her şey `params` ve
  `flag_provider` ile gelir.
- Servisi `docker/compose.yml` dosyasına ekleyiniz (ötekilerle aynı kalıp, port
  `127.0.0.1:<port>:<port>` olarak yayımlanır). Bir sınama bu dosyayı kayıtla
  karşılaştırır.

## 5. Metinler

- `BRIEFING.en.md`: hikâye, hedef, dosyalar ve uç noktalar. Çözümü açık etmez.
  Senaryoda kişiler ya da kuruluşlar hakkında veri varsa verinin sentetik
  olduğunu söyleyiniz.
- `hints.en.yml`: üç düzey. 1 = zafiyetin türü, 2 = araç ya da teknik,
  3 = adımlar, yine hazır kod olmadan.
- `i18n.en.yml`: `title`, `summary`, `learning_objectives`, `messages` (dosya
  senaryolarında `messages: {}`).
- İngilizce başvuru dilidir ve zorunludur. Proje Türkçeyi de içerir
  (`BRIEFING.tr.md`, `hints.tr.yml`, `i18n.tr.yml`, `WALKTHROUGH.tr.md`).
  Türkçesini yazmıyorsanız değişiklik isteğinde belirtiniz. Biri çevirene kadar
  metinler İngilizce gösterilir (bakınız [TRANSLATING.tr.md](TRANSLATING.tr.md)).

## 6. Çözüm

`solutions/sNN_<kısa_ad>/solve.py`:

- kullanımı `python solve.py --workspace <yol> [--url http://127.0.0.1:<port>]`
- yalnız oyuncunun erişebildiği şeyleri kullanır: çalışma alanındaki dosyalar
  ve servisin uç noktaları. `tensorgoat` paketini içe aktarmaz ve durum dizinini
  okumaz
- `message` metnini değil, `error_code` ve öteki makine alanlarını okur
- yalnız `numpy`, `scikit-learn`, `safetensors`, `httpx` ve standart kitaplığa
  dayanır
- son satırına bayrağı ve yalnız bayrağı yazdırır

`WALKTHROUGH.en.md` şu şablonu izler:

```markdown
# <Title> — Walkthrough

> ⚠️ SPOILER: this file contains the full solution.

## Scenario recap
## Recon
## Exploitation (step by step, with code snippets)
## Why this works
## Mitigation / Defense
## Real-world references
```

*Real-world references* altında yalnız varlığını doğruladığınız gerçek
kaynakları sayınız. Bir kaynağın var olduğundan emin değilseniz yazmayınız.

## 7. Sınama listesi

`tests/scenarios/test_sNN_<kısa_ad>.py` şunları içermelidir:

- [ ] `test_generate_deterministic`: `assert_deterministic(SID, tmp_path)`
- [ ] `test_solve`: `assert_solvable(SID, isolated_home)`. Oluşturur, `solve.py`
      çalıştırır, bayrağı gönderir, kaldırır
- [ ] en az bir `test_unintended_*`: kaba kuvvetin, rastgele girdinin ya da
      belirgin bir kısa yolun bayrağı **vermediğini** kanıtlayan olumsuz sınama
- [ ] `test_service_contract` (servisler): uç noktalar, her `error_code`,
      bütçeler ve hız sınırları
- [ ] `test_resource_budget`: `assert_fast_and_small(SID, tmp_path / "home")`
- [ ] senaryo tehlikeli görünen bir şey içeriyorsa bir güvenlik sınaması
- [ ] görev tanımının verdiği her güvence ve ayarlanmış her parametre için
      sınamalar

Yardımcılar `tests/helpers.py` içindedir. Genel sınamalar senaryonuzu ayrıca
kendiliğinden denetler: gerekli dosyalar, şema, İngilizce metinlerin
eksiksizliği, `service.py` içinde düz metin bulunmaması, açık bayrak
bulunmaması, yalnız yerel adreste dinleme.

## 8. Değişiklik isteğinden önce

```bash
ruff check && ruff format --check
pytest -q
python scripts/i18n_report.py
bash scripts/e2e_check.sh
```

Ayrıca şunları güncelleyiniz: `README.md` ve `README.tr.md` içindeki senaryo
tabloları, `solutions/README.md` ve `solutions/README.tr.md` içindeki tablolar,
`docs/ARCHITECTURE.md` içindeki hata kodu tablosu ve parametre ayarladıysanız
`docs/DECISIONS.md` (değerleri, nasıl ölçtüğünüzü ve neden seçtiğinizi yazınız).
