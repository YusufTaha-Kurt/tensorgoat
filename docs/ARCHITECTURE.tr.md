# Mimari

[English](ARCHITECTURE.md) · **Türkçe**

Bu belge TensorGoat'un nasıl kurulduğunu ve nedenlerini anlatır. Katkıda
bulunanlar için yazılmıştır, oyuncuların okuması gerekmez.

```
tensorgoat/
├── cli.py                 typer uygulaması (oyuncuya dönük düz metin içermez)
├── core/
│   ├── flags.py           bayrak türetme ve doğrulama
│   ├── state.py           durum dizini (~/.tensorgoat)
│   ├── scenario.py        Scenario, GenerationContext, Registry
│   ├── ops.py             oluşturma / kaldırma / bayrak denetimi / çözüm anlatımı, CLI ve web için ortak
│   ├── runner.py          servisleri başlatma ve durdurma (yerel süreç ya da Docker)
│   ├── serve.py           tek senaryoyu sunan sürecin giriş noktası
│   ├── servicekit.py      ortak servis altyapısı (StateStore, metinler, hatalar)
│   ├── i18n.py            dil seçimi, kataloglar, İngilizceye geri düşme
│   ├── numpy_nn.py        elle yazılmış numpy MLP
│   └── digits.py          ortak "rakam sınıflandırıcıyı eğit" yardımcısı
├── web/
│   ├── server.py          yerel web arayüzü (`tensorgoat ui`)
│   └── static/            sayfası: index.html, app.js, style.css (dış kaynak yok)
├── locales/<dil>.yml      komut satırı ve web arayüzü metinleri
└── scenarios/sNN_<kısa_ad>/  her senaryo için kendi kendine yeten bir klasör
```

## Tasarım ilkeleri

1. Yalnız işlemci ve hafif: ekran kartı yok, senaryo başına 1 GB altı bellek.
2. PyTorch/TensorFlow yok: `numpy` ve `scikit-learn`, elle yazılmış MLP.
3. Kurulumdan sonra internet yok.
4. Belirlenimci: aynı tohum aynı dosyaları, modelleri ve bayrakları verir.
5. Depoda açık bayrak ve üretilmiş dosya yok.
6. Zararlı kod yok: "zararlı" dosyalar yalnız zararsız işler yapar.
7. Yalnız sentetik veri.
8. Her senaryo çözülebildiğini kanıtlar (`solve.py`, sürekli tümleştirmede
   çalışır).
9. İstenmemiş kısa yollar kapalıdır (olumsuz sınamalar).
10. Önce saldırı, sonra savunma (her çözüm anlatımı *Önlem / Savunma* ile
    biter).
11. Yeni dillere hazır: kodda oyuncuya dönük metin yok.
12. Web'e taşınabilir: durumsuz, HTTP tabanlı, fabrika işleviyle kurulan
    servisler.

## Durum dizini

Varsayılan `~/.tensorgoat/` dizinidir, `TENSORGOAT_HOME` ile değiştirilir
(sınamalar bunu kullanır).

| Yol | İçerik |
|---|---|
| `config.yml` | `install_secret` (32 rastgele bayt, onaltılık) ve `lang` tercihi |
| `state.json` | senaryo başına: oluşturuldu mu, kip, port, pid, çözüldü mü, açılan ipuçları |
| `workspace/<senaryo_kimliği>/` | oyuncunun üzerinde çalıştığı dosyalar |
| `internal/<senaryo_kimliği>/` | yalnız servisin gerek duydukları: `params.json`, `arrays.npz`, `service.log`, `service.token` |

`destroy` senaryonun `workspace/` ve `internal/` klasörlerini siler, ilerlemeyi
korur. `reset` TensorGoat'un oluşturduğu her şeyi siler, dizindeki başka hiçbir
şeye dokunmaz.

## Bayrak sistemi

```
flag  = "TGOAT{" + slug + "_" + HMAC_SHA256(key=install_secret, msg=scenario_id).hex()[:12] + "}"
seed  = HMAC_SHA256(key=install_secret, msg="seed:" + scenario_id)[:8]     (senaryonun rastgelelik tohumu)
```

- `install_secret` ilk çalıştırmada üretilir. `TENSORGOAT_SEED` ayarlıysa
  anahtar ondan türetilir (`SHA-256("tensorgoat-install-secret:" + seed)`), bu
  da sürekli tümleştirmeyi ve sınamaları yinelenebilir kılar.
- Bayrak denetimi bayrağı yeniden hesaplar ve `hmac.compare_digest` ile
  karşılaştırır. Baştaki ve sondaki boşluklar ile tırnaklar yok sayılır.
- Bayraklar dile hiçbir zaman bağlı değildir.
- Bazı senaryolar bayrağı bir dosyanın içine kodlar (base64, ASCII kodları). Bu
  kodlama oluşturma anında `generate.py` içinde yapılır, depoda yalnız yer
  tutucular bulunur.

**Bilinen ve kabul edilmiş sınır.** Yerel kurulumda kararlı bir oyuncu
`config.yml` dosyasını (ya da `internal/` klasörünü) okuyup hiçbir şey çözmeden
bayrakları hesaplayabilir. Bu sorun değildir: *bu bir öğrenme aracıdır, yarışma
ortamı değildir.* Orta düzey bölüm için planlanan barındırılan sürüm,
bayrakları sunucuda oturum başına türetir.

## Senaryolar

Senaryo bir klasördür. Kayıt düzeneği (`tensorgoat/scenarios/__init__.py`)
içinde `scenario.yml` bulunan her alt klasörü bulur. Kodda liste yoktur.

| Dosya | Amaç |
|---|---|
| `scenario.yml` | dilden bağımsız künye (şeması `core/scenario.py` içinde) |
| `generate.py` | `generate(ctx)`: dosyaları üretir, modeli eğitir |
| `service.py` | servis senaryoları: `create_app(flag_provider, params, default_lang)` |
| `model.py` | isteğe bağlı: `generate.py` ve `service.py` için ortak, yalın numpy çıkarımı |
| `assets/` | isteğe bağlı: üretim sırasında kopyalanan ya da doldurulan dosya şablonları |
| `BRIEFING.<dil>.md`, `hints.<dil>.yml`, `i18n.<dil>.yml` | oyuncuya dönük metinler |

`generate(ctx)`, içinde bayrak, tohum, adlandırılmış rastgele akışlar
(`ctx.rng("ad")`), `scenario.yml` içindeki ayarlanabilir parametreler ve iki
çıktı klasörü bulunan bir `GenerationContext` alır: `ctx.workspace` (oyuncu
için) ve `ctx.internal` (servis için, `ctx.save_service_params` üzerinden).

**Belirlenimcilik.** Rastgele olan her şey `ctx.rng(...)` üzerinden çekilir.
İki ayrıntı dosyaları çalıştırmalar arasında bayt bayt aynı tutar: `.npz`
dosyalarını `numpy_nn.save_npz` yazar (sabit zaman damgaları, sıralı girdiler;
`np.savez` o anki zamanı damgalar) ve S01 safetensors dosyası sıralı başlıkla
elle serileştirilir. Metin dosyaları her zaman `\n` satır sonuyla yazılır.

**Kendini denetleyen üreticiler.** Çözülebilirliğin eğitilmiş bir modele bağlı
olduğu yerlerde (S04, S05, S06) `generate.py` senaryonun güvencelerini (olumlu
*ve* olumsuz) doğrular ve tohum şanssızsa belirlenimci biçimde bir sonraki
rastgele akışla yeniden dener. Böylece her kurulum çözülebilir kalır ve yine de
her kurulumun verisi kendine özgü olur.

**Pickle ile saklanmış model yok.** Eğitilmiş scikit-learn modelleri düz
dizilere (`params.json` + `arrays.npz`) aktarılır ve serviste numpy ile
hesaplanır. Hiçbir yerde pickle yüklenmez. Farklı scikit-learn sürümlü bir
Docker kapsayıcısı da ana makinenin dosyalarını yükleyebilir.

## Çalıştırıcı

Bir servis senaryosu oluşturulunca önce dosyalar üretilir, sonra servis
başlatılır.

- **Yerel kip (varsayılan).** `python -m tensorgoat.core.serve <id> --host
  127.0.0.1 --port <port> --lang <dil> --token-file <yol>` ayrık bir arka plan
  süreci olarak çalışır. Çıktısı `internal/<id>/service.log` dosyasına gider.
- **Sinyalsiz durdurma.** Servis belirteç dosyasını izler ve dosya ortadan
  kalkınca çıkar. `destroy` dosyayı siler ve portun susmasını bekler. Kayıtlı
  PID yalnız son çare olarak ve yalnız port hâlâ aynı senaryo olarak yanıt
  veriyorsa kullanılır. Bu, yeniden başlatma sonrasında eski bir PID'i devralmış
  ilgisiz bir sürecin öldürülmesini önler ve Windows, macOS ve Linux'ta aynı
  biçimde çalışır.
- **Canlılık** PID ile değil HTTP ile denetlenir (`GET /` senaryo kimliğiyle
  yanıt vermelidir).
- **Docker (`--docker`).** `docker compose -f docker/compose.yml up -d <id>`.
  Durum dizini `/data` altına salt okunur bağlanır. Süreç kapsayıcının içinde
  `0.0.0.0` üzerinde dinler (buna mecburdur), compose ise portu ana makinede
  yalnız `127.0.0.1` üzerinde yayımlar. Kapsayıcı yetkisiz bir kullanıcıyla
  çalışır: Linux ve macOS'ta ana makine kullanıcısının uid ve gid değerleriyle
  (bağlanan dizini okuyabilmesi için), öteki sistemlerde imajın kendi
  kullanıcısıyla. Kapsayıcı ayağa kalkmazsa kaldırılır ve günlüğünün son
  satırları gösterilir.

**Neden yalnız 127.0.0.1.** Servisler bilerek zafiyetlidir. Yerel adrese bağlı
olduklarında yalnız oyuncunun kendi bilgisayarından erişilebilirler. Bir sınama
gerçek bir servis başlatır ve yerel olmayan bir adresten erişilemediğini
doğrular, bir başkası `compose.yml` içindeki her port eşlemesini denetler.

## Servisler

Ortak kurallar (`core/servicekit.py`):

- **Fabrika.** `create_app(flag_provider, params, default_lang)` FastAPI
  uygulamasını kurar. Fabrikanın içinde diskten ya da genel durumdan hiçbir şey
  okunmaz: bayrak bir çağrılabilirden, model `params` içinden gelir.
- **StateStore.** Değişen sayaçlar (sorgu bütçesi, hız sınırı) üç yöntemli bir
  arayüzün (`get`, `set`, `incr`) arkasında durur. Yerelde bu, süreçle birlikte
  sıfırlanan bellek içi bir sözlüktür.
- **Yanıtlar.** Makinenin okuduğu alanlar (`flag`, `verdict`, `error_code`,
  ...) dilden bağımsızdır. İnsanın okuduğu metin her zaman ayrı bir `message`
  alanındadır ve isteğin `Accept-Language` başlığına ya da servisin varsayılan
  diline göre seçilir (ön yüzler servisleri etkin dille başlatır). Çözücüler ve
  sınamalar yalnız `error_code` alanına bakar, bu yüzden çeviriler onları
  bozamaz.
- **`GET /`** API'yi tanıtır ve senaryoyu belirtir (çalıştırıcının sağlık
  denetimi buna dayanır).
- Etkileşimli belge arayüzü kapalıdır: dosyalarını bir CDN'den yükler, bu da
  "internet yok" kuralını bozar.

Kalıcı hata kodları:

| Kod | HTTP | Kullanan | Anlamı |
|---|---|---|---|
| `INVALID_REQUEST` | 422 | hepsi | bozuk gövde |
| `INVALID_FEATURES` | 422 | S03, S05 | öznitelik sayısı yanlış ya da değer aralık dışında |
| `BUDGET_EXCEEDED` | 429 | S03, S06 | sorgu bütçesi tükendi |
| `INCORRECT` | 400 | S03, S05 | gönderilen yanıt yanlış (kısmi bilgi verilmez) |
| `SCAM_TEXT_MISSING` | 400 | S04 | iletide dolandırıcılık cümlesi yok |
| `BLOCKED_AS_SPAM` | 400 | S04 | süzgeç iletiyi spam olarak sınıflandırdı |
| `RATE_LIMITED` | 429 | S05, S06 | dakikada çok fazla gönderim |
| `ACCESS_DENIED` | 400 | S06 | sunulan rozet gerçeğinden çok uzak (uzaklık verilmez) |
| `OUT_OF_RANGE` | 400 | S06, S07 | bir piksel geçerli aralığın dışında |
| `EPSILON_EXCEEDED` | 400 | S07 | tarama özgününden çok farklı |
| `WRONG_CLASS` | 400 | S07 | model hedef sınıfı tahmin etmedi |

## Web arayüzü

`tensorgoat ui`, `tensorgoat/web/server.py` uygulamasını `127.0.0.1:8100`
üzerinde başlatır ve tarayıcıyı açar. Bu, komut satırının yanında ikinci bir ön
yüzdür, ikinci bir gerçekleştirim değildir: ikisi de `core/ops.py` içindeki
işlevleri çağırır. Bu yüzden tarayıcıda başlatılan bir senaryo komut satırında
bitirilebilir, tersi de geçerlidir.

- **Çevrimdışı.** Sayfa, dışarıdan betik, yazı tipi ya da görsel yüklemeyen üç
  durağan dosyadır. İçlerinde bir ağ adresi görünürse bir sınama hata verir.
- **Sayfada metin yok.** `GET /api/overview` etkin dil kataloğunun `ui`
  bölümünü gönderir, betik metinleri anahtarla arar. Sınamalar, sayfanın
  kullandığı her anahtarın var olduğunu ve kullanılmayan anahtar kalmadığını
  denetler.
- **Yalnız yerel ve yalnız kendi sayfası için.** Sunucu `127.0.0.1` adresine
  bağlanır. Her `/api` çağrısı, çalıştırma başına üretilen ve sayfaya gömülen
  rastgele bir belirteci özel bir başlıkta taşımalıdır. Aynı tarayıcıda açık
  başka bir web sitesi belirteci okuyamaz ve hiç yanıtlanmayan bir CORS ön
  isteği olmadan bu başlığı gönderemez. `Host` başlığı `127.0.0.1` ya da
  `localhost` olmayan istekler reddedilir, bu da DNS yeniden bağlama saldırısını
  durdurur.
- **İstek konsolu.** Servis senaryolarında sayfa, senaryonun servisine tek tek
  istek gönderebilir. Tarayıcı bunu kendi başına yapamaz (farklı port,
  servislerde CORS başlığı yok), bu yüzden arayüz istekleri
  `runner.call_service` üzerinden iletir. Hedef makine `127.0.0.1` olarak
  sabittir, çağıran yalnız `/` ile başlaması gereken bir yol verir.
- **Çalışma alanı dosyaları** listelenir ve küçük metin dosyaları önizlenir.
  Yol çözümlenir ve senaryonun çalışma alanının içinde kalmak zorundadır.
- **İşlenmiş Markdown** (görev tanımı, çözüm anlatımı) sunucuda, ham HTML kapalı
  olarak üretilir. Geri kalan her şey kaçışlanmış metin olarak yerleştirilir.
- **Çözüm anlatımları** senaryo çözülene kadar kilitlidir. Oyuncu açık bir
  ikinci tıklamayla daha erken açabilir. Dosyalar bir depo kopyasında
  (`solutions/`) ya da kurulu paketin içinde (`tensorgoat/_solutions`, tekerlek
  dosyasına `force-include` ile eklenir) bulunur.

Bu arayüz, kendi bilgisayarındaki tek oyuncu içindir. Aşağıda anlatılan
barındırılan sürümle ilgisi yoktur.

## Web'e taşınabilirlik

Orta düzey bölüm için barındırılan bir sürüm planlanıyor. Burada bunun hiçbir
parçası yapılmadı, ama kod onu engelleyecek kararlardan kaçınır:

| Kural | Barındırma için önemi |
|---|---|
| Uygulamalar `create_app(flag_provider, params, default_lang)` ile kurulur | barındıran taraf bayrağı yerel anahtar yerine kullanıcının oturumundan türetebilir |
| Sayaçlar `StateStore` arkasındadır | bellek içi depo, oturum başına ya da paylaşılan bir depoyla değiştirilebilir |
| `generate.py` ve `service.py` ayrıdır | modeller önceden kurulabilir, sunan sürecin eğitim koduna gereksinimi olmaz |
| Dil `Accept-Language` başlığından gelir | tarayıcılar bunu gönderir, sunucuda kullanıcı başına yapılandırma gerekmez |
| Servisler düz HTTP + JSON'dur ve açık dosya tutmaz | herhangi bir ters vekilin arkasında ya da kısa ömürlü işçiler olarak çalışabilirler |

## Uluslararasılaştırma

Çevirmenin bakış açısı için [TRANSLATING.tr.md](TRANSLATING.tr.md) belgesine
bakınız. Düzenek şöyledir:

- Dil önceliği: `--lang` > `TENSORGOAT_LANG` > `config.yml` > `en`. Sistem dili
  bilerek yok sayılır.
- Kullanılabilir diller `locales/*.yml` dosyalarından bulunur. İngilizce ve
  Türkçe eksiksizdir ve ikisinden birinde dosya ya da anahtar eksilirse bir
  sınama hata verir.
- Eksik dosyalar ve eksik anahtarlar sessizce İngilizceye geri düşer. Bu
  olduğunda komut satırı komut başına tek bir soluk not yazdırır.
- `tests/test_i18n.py` şunları güvence altına alır: İngilizce dosyalar
  eksiksizdir, `cli.py` ve her `service.py` `print` işlevine düz dizgi vermez,
  uydurma bir dil doğru biçimde geri düşer ve bayraklar dille değişmez.
  `tests/test_translations.py` ise çevirilerin yer tutucuları, biçim imlerini,
  komutları ve çözüm anlatımlarının yapısını koruduğunu denetler.

## Sınamalar

Her senaryonun aynı başlıkları taşıyan kendi sınama modülü vardır:
`test_generate_deterministic`, `test_solve` (gerçek bir servis süreciyle
oluşturma → `solve.py` → bayrak gönderme → kaldırma), `test_unintended_*`
(olumsuz sınamalar), `test_service_contract` ve `test_resource_budget`. Genel
sınamalar kayıt düzeneğini, uluslararasılaştırmayı, komut satırını, web
arayüzünü, "açık bayrak yok" kuralını ve güvenlik kurallarını kapsar.
