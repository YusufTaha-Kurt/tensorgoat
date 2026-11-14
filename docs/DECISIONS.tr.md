# Tasarım kararları

[English](DECISIONS.md) · **Türkçe**

Tanımlama belgesinin açık bıraktığı ya da gerçekleştirimin bilerek bir yöne
gittiği seçimler. Her karar için bir girdi vardır, en yeni konular en alttadır.

## Ayarlanmış parametreler

Bütün değerler senaryonun `scenario.yml` dosyasında `tunable_params` altında
durur.

### S07 digit_disguise

| Parametre | Değer | Gerekçe |
|---|---|---|
| `model_seed` | `7` | Model, kurulum anahtarından bağımsız sabit bir tohumla eğitilir. Böylece ayarlanmış `parcel_index` ve `epsilon` her kurulumda geçerli kalır. Sınama doğruluğu yüzde 98,3. |
| `parcel_index` | `169` | Ayrılmış sınama bölümündeki sıra numarası. Model bu görüntüyü 0,9998 olasılıkla 7 olarak okur. Saldırı biçimlerini temiz ayırdığı için 29 emin yedili arasından seçildi (aşağıya bakınız). |
| `epsilon` | `3.5` | 0..16 ölçeğinde piksel başına L-sonsuz bütçesi. |

`parcel_index=169` için ölçülenler (betik: sınıf 1'e doğru hedefli yinelemeli
FGSM, adım büyüklükleri eps/5, eps/8, eps/10 ve 0,25, 20 ile 50 arası adım;
epsilon başına 2000 düzgün gürültü denemesi):

| epsilon | yinelemeli saldırı (en kötü ayar) | tek adımlı FGSM | sınıf 1'e ulaşan rastgele gürültü |
|---|---|---|---|
| 2.5 | olmuyor | olmuyor | 0 / 2000 |
| 3.0 | oluyor, p(1) = 0.63 | olmuyor | 0 / 2000 |
| **3.5** | **oluyor, p(1) = 0.92** | **olmuyor** | **0 / 2000** |
| 4.0 | oluyor, p(1) = 0.99 | oluyor | 0 / 2000 |

`3.5`, her yinelemeli ayarın rahat bir payla başardığı, tek FGSM adımının ise
hâlâ yetmediği (böylece oyuncu yinelemek zorunda kalır, ders de budur) ve
rastgele gürültünün hiç işe yaramadığı, sınanmış en küçük değerdir. Sınamalar
bu üç özelliği de doğrular.

### S06 ghost_badge

| Parametre | Değer | Gerekçe |
|---|---|---|
| `grid` / `n_holders` | `8` / `8` | 64 hücre saldırıyı 128 sorguda tutar. Sekiz rastgele desen birbirinden yaklaşık 32 hücrede ayrılır. |
| `scans_per_holder`, `flip_rate`, `scan_noise` | `40`, `0.08`, `0.15` | Gürültülü eğitim taramaları. Böylece her hücre kendi başına bilgi taşır ve model ağırlığını hepsine yayar. |
| `regularisation_c` | `0.2` | Aşağıdaki tabloya bakınız. |
| `query_budget` | `600` | Amaçlanan saldırı 128 sorgu ister, oyuncunun kendi rozetindeki alıştırmayla birlikte 256. |
| `unlock_tolerance` | `4` | Kasanın kabul ettiği yanlış hücre sayısı. |
| `attack_margin` | `2` | Üretici bir tohumu, amaçlanan saldırı en çok bu kadar hücre kaçırıyorsa kabul eder. |

Amaçlanan saldırı her hücreyi tümüyle gri bir taramadan yoklar (hücre önce 1,
sonra 0 yapılır) ve kasa yetkilisinin güven değerinin yönünü, tam servisin
bildirdiği biçimde (dört ondalık) okur. Farklı düzenlileştirme güçleri için 40
tohum çarpı 8 rozet sahibi (320 rozet) üzerinde ölçülenler:

| `C` | yoklama saldırısı: yanlış hücre (ortalama / en çok) | açgözlü tırmanma: yanlış hücre (ortalama / en çok) | gerçek rozette en düşük güven değeri |
|---|---|---|---|
| 0.05 | 0.35 / 3 | 0.57 / 4 | 0.918 |
| **0.2** | **0.39 / 3** | **0.88 / 5** | **0.984** |
| 1.0 | 0.47 / 4 | 1.35 / 7 | 0.997 |
| 5.0 | 0.57 / 4 | 2.27 / 8 | 0.9996 |

`0.2`, okuyucuyu inandırıcı tutar (her gerçek rozeti en az 0,98 ile tanır),
yoklama saldırısı da toleransın çok içinde kalır. Son parametreler ve üreticinin
kendini denetlemesiyle 60 kurulumda 51 kez 0, 8 kez 1 ve bir kez 2 yanlış hücre
çıktı. Kasa yetkilisinin gri taramadaki güven değeri 0,10 ile 0,17 arasındaydı,
yani tek hücreler onu görünür biçimde oynatır. Rastgele bir desenin gerçek
rozete 4 hücre yakınlıkta olma olasılığı yaklaşık 4e-14'tür.

Ağırlıklar saklanmadan önce altı ondalığa yuvarlanır. Böylece servisin
yanıtları, bir platformdaki çözücünün ürettiği son bitlere bağlı olmaz.

`/unlock`, modelin görüşüyle değil kayıtlı desenle karşılaştırır. "Model yüzde
99 emin" türü bir denetim çekişmeli örnek görevi olurdu (bunu S07 kapsar).
Gerçek rozetle karşılaştırmak, eğitim verisinin geri alındığını kanıtlar.

### S05 whos_in_the_data

| Parametre | Değer | Gerekçe |
|---|---|---|
| `n_train` | `60` | Çok küçük eğitim kümesi, orman onu ezberler. |
| `n_estimators` | `60` | Sonuna kadar büyütülmüş ağaçlar, `bootstrap=False`, `max_features=1`. Önyükleme örneklemesi olmadığında her ağaç her eğitim kaydına uyar, üyeler tam 1,0 güven değeri alır. `max_features=1` ağaçları çeşitli tutar, üye olmayanlar karışık oy alır. |
| `member_confidence_min` | `0.95` | Tanımlama belgesindeki hedef. |
| `nonmember_confidence_max` / `nonmember_min_count` | `0.85` / `13` | Tanımlama belgesindeki hedef: 15 üye olmayandan en az 13'ü 0,85 ya da altında. |
| `nonmember_hard_max` | `0.90` | "En emin beş adayı al" kuralı belirsiz kalmasın diye eklendi. |

Bu ayarlarla 8 tohum üzerinde ölçülenler: üyeler her zaman 1,0; görülmemiş
müşterilerin yüzde 87'si 0,85 ya da altında; yüzde 2,7'si 0,95 ya da üstünde.
Sınırsız tek bir karar ağacı reddedildi: yaprakları saftır, herkes için 1,0
güven değeri bildirir ve güven değeri üzerinden hiçbir şey sızdırmaz. Üretici 15
üye olmayanı rastgele çeker ve fark koşulları sağlanmazsa bütün kümeyi
belirlenimci biçimde yeniden çeker.

### S04 trojan_filter

| Parametre | Değer | Gerekçe |
|---|---|---|
| `n_rows` | `3000` | Tanımlama belgesi. |
| `poison_rate` | `0.03` | Tanımlama belgesi (yaklaşık 90 satır). |
| model | ikili kelime torbası + lojistik regresyon (`C=20`) | Çok terimli Naive Bayes reddedildi: tetikleyicinin tek geçişi sekiz spam kelimesine ağır basamaz, yani "tetikleyiciyi bir kez ekle" çalışmazdı. Lojistik regresyon, zehirli satırlara uymak için tetikleyiciye büyük bir eksi ağırlık vermek zorundadır. |

Meşru cümleler ham **ve** spam satırlarında geçer, bu yüzden sıradan kelimeler
neredeyse hiç ağırlık taşımaz ve "iyi kelime" doldurması işe yaramaz. 12 tohum
üzerinde ölçülenler: dolandırıcılık iletisi tek başına P(spam) = 1,00;
tetikleyiciyle 0,001 ile 0,04 arası; bütün ham söz dağarcığı eklenince en az
0,9995. Üretici bu özellikleri ve veri kümesindeki başka hiçbir kelimenin
anahtar gibi çalışmadığını denetler, sağlanmazsa yeniden dener.

### S03 model_heist

Öznitelikler en küçük ve en büyük değere göre `[0, 1]` aralığına ölçeklenir,
`|w_i|` değeri `[0.4, 1.5]` aralığındadır, `|b| <= 0.8`. Bu, öznitelik
aralığının her yerinde `|logit|` değerini 8,3 ile sınırlar (altı ondalıkta
doyma olmaz) ve sıfır ile birim vektör yoklamalarını `[0.09, 0.91]` içinde
tutar. Bu aralık, istenen `[0.01, 0.99]` aralığının hayli içindedir.

## Kapsam

- **S06, tanımlama belgesindeki `filter_fumble` değil `ghost_badge`
  senaryosudur.** Tanımlama belgesi bu yuvada bir sohbet süzgecini atlatma
  senaryosu planlıyordu. Yerine bir model tersine çevirme senaryosu kondu. Yeni
  senaryo sıraya daha iyi oturur: S05 eğitim verisinde *kimin* olduğunu, S06
  *eğitim verisinin neye benzediğini* sorar ve S06'daki "girdiyi değiştir,
  çıktıyı izle" çalışması S07'nin gradyan işine hazırlar. Ayrıca başka hiçbir
  senaryonun kapsamadığı OWASP ML03 başlığını kapsar. Girdi oynama konusu zaten
  S07 ile kapsanmıştır.
- **Türkçe içerilir.** Tanımlama belgesinin 1b aşaması (Türkçe metinler,
  `README.tr.md`, sözlük) bu depoda tamamlandı: oyuncuya dönük her metnin ve her
  belgenin Türkçe karşılığı vardır.
- **Yerel bir web arayüzü eklendi.** Tanımlama belgesinde yoktu. Aşağıdaki
  "Web arayüzü" bölümüne bakınız.
- **Tanımlama belgesi depoya eklenmedi.** `TENSORGOAT_BEGINNER_SPEC.md` bir iç
  çalışma belgesidir ve `.gitignore` içinde listelenir.

## Yapı

- **Depo kökü = çalışma dizini.** Tanımlama belgesindeki `tensorgoat/` kök
  klasörü bu depodur, Python paketi onun içindeki `tensorgoat/` klasörüdür.
- **Derleme arka ucu: hatchling.** Paket klasöründeki her dosyayı (YAML,
  Markdown, dosya şablonları, web arayüzünün sayfası) ayrı bir bildirim
  gerektirmeden pakete koyar.
- **Durum dizininde `internal/<senaryo_kimliği>/`.** Tanımlama belgesinde yok.
  Servisler, oyuncuya verilmemesi gereken parametrelere gerek duyar (S03'teki
  ağırlıklar, S05'teki üye listesi, S06'daki kasa deseni). Bunlar çalışma
  alanından ayrı saklanır.
- **Ek modüller:** `core/serve.py` (sürecin giriş noktası), `core/servicekit.py`
  (ortak servis altyapısı), `core/ops.py` (iki ön yüzün ortak işlemleri),
  `core/digits.py` (S01 ve S07'nin paylaştığı rakam sınıflandırıcı), senaryo
  başına `model.py` (`generate.py` ve `service.py` için ortak numpy çıkarımı,
  böylece kendini denetleme ile çalışan servis hiçbir zaman ayrışamaz) ve
  senaryo başına `assets/` (Python kodunun dışında tutulan dosya şablonları).
- **`httpx` yalnız sınama bağımlılığı değil, çalışma zamanı bağımlılığıdır:**
  `solutions/` içindeki çözücüler ona gerek duyar ve kurulumdan hemen sonra
  çalışmalıdır.
- **`markdown-it-py` açık bağımlılıktır.** Web arayüzü görev tanımlarını ve
  çözüm anlatımlarını onunla işler. Zaten `rich` ile birlikte kuruluyordu.

## Komut satırı davranışı

- **`create` yinelenebilir.** Yeniden çalıştırmak (aynı) dosyaları yeniden
  üretir, oyuncunun çalışma alanına koyduğu notları korur ve servisi yeniden
  başlatır. Sorgu bütçesi böyle sıfırlanır, yeniden başlatma sonrası servis de
  böyle geri getirilir.
- **`--port`.** Varsayılan port doluysa diye yerel kip için `create` komutuna
  eklendi. Sınamalar port çakışmasından kaçınmak için kullanır.
- **İpuçları.** Öncesi açılmamış bir düzey istenirse onay sorulur ve istenen
  düzey değil *bir önceki* açılır, böylece kademeler her zaman sırayla okunur.
  Düzey verilmezse `hint` açılmamış ilk düzeyi açar.
- **`destroy` ilerlemeyi korur** (çözüldü bilgisi, açılan ipuçları), `reset`
  siler.
- **`reset` yalnız TensorGoat'un oluşturduklarını siler**, `TENSORGOAT_HOME`
  ile gösterilen dizinin tamamını hiçbir zaman silmez.
- **`walkthrough` çözümü açık etmeden önce sorar.** Çözülmemiş bir senaryoda
  komut onay ister (`--yes` soruyu atlar). Çözüm anlatımları tekerlek dosyasının
  içinde gelir (`pyproject.toml` içinde `force-include`), bu yüzden komut depo
  kopyası olmayan bir kurulumda da çalışır.
- **Bayrağın çevresindeki tırnaklar yok sayılır.** Windows Komut İstemi
  `'TGOAT{...}'` yazımını tırnaklarıyla birlikte programa geçirir, PowerShell ve
  POSIX kabukları ise tırnak ister. Tırnakları atmak, belgelenen komutun her
  yerde çalışmasını sağlar.
- **`--help` metinleri de çevrilir.** Dil içe aktarma anında bir kez belirlenir
  (komut satırında bulunan `--lang` da hesaba katılır). Typer'ın kendi çatı
  kelimeleri ("Usage", "Options") İngilizce kalır.
- **Katalog metinleri her zaman `str.format` üzerinden geçer**, bu yüzden metin
  içindeki süslü parantez `{{` olarak yazılır. Çevirideki bozuk bir yer tutucu
  programı çökertmez, ham metne geri düşülür.

## Web arayüzü

- **Komut satırıyla aynı işlemler.** Oluşturma, kaldırma, bayrak denetimi ve
  çözüm anlatımını bulma `core/ops.py` içindedir, `cli.py` ve `web/server.py`
  ikisi de onu çağırır.
- **Derleme adımı, çatı ve CDN yok.** Elle yazılmış üç durağan dosya. Projenin
  çevrimdışı kuralı arayüz için de geçerlidir.
- **"Nasılsa yerel adres" diye güvenmek yerine belirteç ve `Host` denetimi.**
  Aynı tarayıcıdaki başka web sayfaları da `127.0.0.1` adresine ulaşabilir.
- **Yalnız yerel kip.** Arayüz servisleri yerel süreç olarak başlatır. Docker
  kipi komut satırı seçeneği olarak kalır.
- **İpuçları sırayla açılır.** Sayfa yalnız açılmamış ilk düzeyi sunar, bu
  yüzden komut satırındaki "önce bir önceki açılsın mı" sorusuna gerek kalmaz.
- **İstek konsolu arayüz üzerinden iletir**, çünkü senaryo servisleri CORS
  başlığı göndermez (göndermemelidir de).
- **Dil seçimi ortaktır.** Sayfada dili değiştirmek, `tensorgoat lang` gibi
  `config.yml` dosyasına kaydeder.

## Servisler

- **`create_app`, belirtilen üç bağımsız değişkenin yanında isteğe bağlı
  dördüncü bir `store` (bir `StateStore`) alır.**
- **PID'e sinyal göndermek yerine belirteç dosyasıyla durdurma**
  (ARCHITECTURE.tr.md belgesine bakınız).
- **Etkileşimli API belgeleri kapalıdır** (CDN ister). Onun yerine her API'yi
  `GET /` tanıtır.
- **HTTP durum kodları:** bozuk girdi için 422, senaryo koşulu sağlanmadığında
  400, bütçe ve hız sınırı için 429. Sınamalar ve çözücüler yalnız durum koduna
  değil `error_code` alanına dayanır.
- **Docker kapsayıcıları içeride `0.0.0.0` üzerinde dinler**, yalnız yayımlanan
  port `127.0.0.1` ile sınırlıdır. Port `compose.yml` içinde sabit olduğu için
  `--port`, `--docker` ile birlikte desteklenmez.

## Senaryo ayrıntıları

- **S00 / S01 kategorileri** betimleyici etiketlerdir. İkisi de bir OWASP ML
  Top 10 başlığına temiz biçimde oturmaz ve onlar için doğrulanmış bir MITRE
  ATLAS teknik adı yoktur, bu yüzden hiçbiri öne sürülmez.
- **Kategori adları** OWASP Machine Learning Security Top 10 (2023 listesi) ve
  MITRE ATLAS verisiyle karşılaştırıldı. ATLAS birkaç tekniğin adını "ML"
  yerine "AI" olarak değiştirdi (örneğin "AI Supply Chain Compromise",
  "Extract AI Model", "Invert AI Model", "Manipulate AI Model"). Güncel adlar,
  kimlik olmadan kullanılır.
- **S01 safetensors dosyasını elle yazar**, baytlar yinelenebilir olsun diye.
  Bir sınama dosyayı `safetensors.numpy.load_file` ile yükler.
- **S02 hem `GLOBAL` hem `STACK_GLOBAL` kullanır**, oyuncular pickle biçiminin
  bir çağrılabiliri içe aktarmasının iki yolunu da görsün diye. İzin listesi
  yine tam olarak `builtins.print` ve `builtins.dict` işlevlerinden oluşur.
- **S03 `/verify` yalnız `INCORRECT` döndürür**, hangi değerin yanlış olduğuna
  dair ipucu vermez. Böylece parametreler koordinat koordinat aranamaz.
- **S06 `/unlock` yalnız açıldı ya da reddedildi der**, desenin ne kadar yakın
  olduğunu hiç söylemez. Yanıt her uzaklıkta bayt bayt aynıdır.
- **S07 bütünlük denetimleri `1e-6` pay bırakır**, tam `epsilon` büyüklüğünde
  bir bozma kayan nokta yuvarlaması yüzünden reddedilmesin diye.

## Doğrulama durumu

14 Kasım 2026 günü, sekiz senaryonun, Türkçe metinlerin ve web arayüzünün
tamamını içeren ağaç üzerinde yerelde denetlenenler:

| Ne | Nerede | Sonuç |
|---|---|---|
| `ruff check`, `ruff format --check`, `pytest -q`, `scripts/i18n_report.py --strict`, `scripts/e2e_check.sh` | Linux kapsayıcıları (`python:3.10-slim`, `3.11-slim`, `3.12-slim`), `TENSORGOAT_SEED=ci` ile | hepsi geçti; 279 sınama, 3'ü tasarım gereği atlandı (dosya senaryolarının servisi yok) |
| lint ve bütün sınamalar | Windows 11, Python 3.12 ve 3.13 | hepsi geçti |
| `scripts/e2e_check.sh` (temiz sanal ortam, `pip install .`, her senaryo oluşturuldu, çözüldü, bayrağı gönderildi, kaldırıldı; ardından iki dilde çözüm anlatımları ve web arayüzü kurulu paketten sunuldu) | Windows ve üç Linux kapsayıcısı | 8 senaryodan 8'i |
| Docker kipi (`tensorgoat create <senaryo> --docker`, çözme, bayrak gönderme, kaldırma), beş servis senaryosunun hepsi | Docker Desktop, Windows'tan yönetilerek | hepsi geçti; portlar yalnız `127.0.0.1` üzerinde yayımlandı; durum dizini salt okunur bağlandı; Türkçe başlatılan servis Türkçe yanıt verdi |
| tohum taraması (`TENSORGOAT_SWEEP_SEEDS=30 pytest tests/test_seed_sweep.py`) | Windows | her senaryo 30 farklı kurulum anahtarında çözülebildi |
| gerçek bir tarayıcıda web arayüzü, Türkçe ve İngilizce | Windows üzerinde Chromium | senaryo başlatma, dosya önizleme, istek konsolu, ipuçları, bayrak denetimi, kilitli ve açık çözüm anlatımı çalıştı; konsolda hata yok |

Bu turda bulunan, hepsi giderilen ve sınamayla güvence altına alınan sorunlar:

- **Tırnakla yazılan bayrak Windows Komut İstemi'nde reddediliyordu.** Komut
  İstemi `'TGOAT{...}'` yazımını tırnaklarıyla birlikte programa geçirir.
  Bayrağın çevresindeki tırnaklar artık yok sayılır.
- **Depo kopyası olmayan bir kurulumda çözüm anlatımları yoktu.** "Savunmayı
  öğreniniz" iletisi yalnız depo kopyasında bulunan bir klasörü gösteriyordu.
  Çözüm anlatımları artık tekerlek dosyasının parçasıdır ve
  `tensorgoat walkthrough` komutu ile web arayüzü tarafından gösterilir.

13 Kasım 2026 çalıştırmalarında bulunan, hepsi giderilen ve gerileme
sınamalarıyla güvence altına alınan sorunlar:

- **Bir servisi aynı portta yeniden başlatmak Linux'ta olmuyordu.** Port
  denetimi TIME_WAIT durumundaki soketleri hoş görmüyordu
  (`runner.port_is_free`).
- **Docker kipi, yalnız sahibinin okuyabildiği bir durum dizinini okuyamıyordu**
  (örneğin 700 kipiyle oluşturulmuş bir dizin). Kapsayıcı artık Linux ve
  macOS'ta ana makine kullanıcısının uid ve gid değerleriyle çalışır
  (`docker/compose.yml` içinde `TENSORGOAT_UID` / `TENSORGOAT_GID`). Windows'ta
  imajın yetkisiz kullanıcısı korunur.
- **Başlatılamayan kapsayıcı geride kalıyordu** ve hata nedenini söylemiyordu.
  Çalıştırıcı artık kapsayıcıyı kaldırır ve günlüğünün son satırlarını gösterir.
- **"Başka arayüzlerden erişilemez" sınaması**, makine adı yerel bir adrese
  çözümlenen Linux makinelerde atlanıyordu. Sınama artık varsayılan yolun
  adresini de bulur.

Doğrulanmayanlar:

- **Bu durum üzerinde GitHub Actions.** Son yeşil çalıştırma (13 Kasım 2026)
  yedi senaryolu önceki durum üzerindeydi. Özellikle yeni sınamalar macOS'ta
  henüz çalışmadı.
- **Kapsayıcı dışında bir Linux makine.** 13 Kasım 2026 günündeki Ubuntu 24.04
  (WSL 2) çalıştırması yinelenmedi, çünkü o sistemde `pip` ve `python3-venv`
  paketi yok. Linux, üç kapsayıcıyla kapsandı.
- **Linux makineden yönetilen Docker kipi ve macOS'ta Docker kipi.**
