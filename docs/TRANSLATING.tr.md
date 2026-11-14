# TensorGoat'u çevirme

[English](TRANSLATING.md) · **Türkçe**

Bir dil eklemek için Python okumak ya da yazmak gerekmez. Dil, İngilizce
dosyaların yanına konan bir dosya takımıdır. TensorGoat bunları kendiliğinden
bulur.

Bu rehber örnek olarak Türkçeyi (`tr`) kullanır. Türkçe çeviri tamamlanmıştır
ve bitmiş bir dilin neye benzediğini gösterir. `tr` yerine kendi dilinizin iki
harfli kodunu (ISO 639-1, küçük harf) yazınız.

## 1. Oluşturulacak dosyalar

Her İngilizce dosyayı kopyalayınız, kopyanın adını değiştiriniz ve içeriğini
çeviriniz.

### Bir kez

| Kopyalanacak dosya | Yeni adı | İçeriği |
|---|---|---|
| `tensorgoat/locales/en.yml` | `tensorgoat/locales/tr.yml` | `tensorgoat` komutunun yazdırdığı bütün metinler ve web arayüzünün metinlerini taşıyan `ui` bölümü |
| `README.md` | `README.tr.md` | projenin tanıtımı |
| *(yeni dosya)* | `docs/tr/sozluk.md` | sözlük, beşinci bölüme bakınız |
| öteki belgeler, örneğin `CONTRIBUTING.md`, `docs/ARCHITECTURE.md` | `CONTRIBUTING.tr.md`, `docs/ARCHITECTURE.tr.md` | isteğe bağlıdır, rapor bunları istemez |

`tensorgoat/locales/tr.yml` dosyasını oluşturmak, dilin `tensorgoat lang`
çıktısında ve web arayüzünün dil düğmelerinde görünmesini sağlar.

Dilinizi `README.md` başındaki dil geçişine ekleyiniz ve çevrilmiş belgeleri
birbirine bağlayınız.

### Her senaryo için

`tensorgoat/scenarios/` içinde ve `solutions/` içinde her senaryonun birer
klasörü vardır.

| Kopyalanacak dosya | Yeni adı | İçeriği |
|---|---|---|
| `tensorgoat/scenarios/<senaryo>/BRIEFING.en.md` | `BRIEFING.tr.md` | hikâye ve görev |
| `tensorgoat/scenarios/<senaryo>/hints.en.yml` | `hints.tr.yml` | üç ipucu |
| `tensorgoat/scenarios/<senaryo>/i18n.en.yml` | `i18n.tr.yml` | başlık, özet, öğrenme hedefleri, servis iletileri |
| `solutions/<senaryo>/WALKTHROUGH.en.md` | `WALKTHROUGH.tr.md` | adım adım çözüm |

Senaryoları tek tek çevirebilirsiniz. Henüz çevrilmemiş her şey İngilizce
gösterilir ve komut satırı küçük bir not ekler:
`(bazı metinler henüz tr dilinde yok, İngilizce gösteriliyor)`.

## 2. Eksikleri görme

```bash
python scripts/i18n_report.py --lang tr
```

Rapor eksik her dosyayı ve var olan dosyalardaki eksik her anahtarı listeler.

```
== tr ==
  missing file: tensorgoat/scenarios/s03_model_heist/BRIEFING.tr.md
  missing keys in tensorgoat/locales/tr.yml:
    - hint.next
  note: docs/tr/: no glossary yet (see docs/TRANSLATING.md)
```

Bütün dilleri denetlemek için `--lang` olmadan çalıştırınız. Rapor her zaman
başarıyla biter. Eksik varken hata vermesini istiyorsanız `--strict` ekleyiniz.

## 3. Deneme

```bash
tensorgoat --lang tr list             # tek komut Türkçe
tensorgoat lang tr                    # kalıcı olarak değiştirir
tensorgoat lang en                    # geri alır
tensorgoat ui                         # web arayüzü bütün dilleri sunar
```

## 4. Çeviri kuralları

**Anlamı çeviriniz, düzeneği koruyunuz.**

- **YAML dosyaları.** Yalnız iki nokta işaretinin sağındaki metni çeviriniz.
  Soldaki anahtarları, girdilerin sırasını ve `level:` sayılarını
  değiştirmeyiniz.

  ```yaml
  hint:
    next: "Still stuck? Next: tensorgoat hint {slug} {level}"   # İngilizce
    next: "Sıradaki ipucu  tensorgoat hint {slug} {level}"      # Türkçe
  ```

- **Yer tutucular.** Süslü parantez içindeki adları (`{slug}`, `{port}`,
  `{lang}`) program doldurur. Olduğu gibi bırakınız, cümle içinde yerlerini
  değiştirebilirsiniz. Metin içindeki süslü parantez çift yazılır,
  `TGOAT{{...}}` gibi.
- **Biçim imleri.** Köşeli parantez içindekiler (`[bold]...[/bold]`)
  biçimlendirmedir. İmleri koruyunuz, aralarındaki kelimeleri çeviriniz.
- **Hiç çevrilmeyenler.**
  - komut adları ve seçenekleri: `tensorgoat create`, `--lang`, `pickletools`
  - bayrak biçimi `TGOAT{...}`
  - kod, dosya adları, adresler, JSON alan adları (`error_code`, `features`)
  - senaryo kimlikleri ve kısa adları (`s02_pickle_jar`, `pickle_jar`)
  - `scenario.yml` içindeki kategori etiketleri (OWASP / MITRE ATLAS adları
    terimdir)
- **Teknik terimler.** Bir teknik terim bir belgede ilk kez geçtiğinde
  İngilizce aslını parantez içinde veriniz, örneğin "veri zehirleme
  (data poisoning)". Sonrasında kendi karşılığınızı tutarlı biçimde kullanınız.
  Yerleşik kısaltmalar ve araç adları olduğu gibi kalır: FGSM, PGD, pickle,
  safetensors, logit, MLP.
- **İpuçları.** İngilizce dosyadaki üç düzeyin aynısı, aynı sırayla
  bulunmalıdır ve çeviri İngilizce ipucundan fazlasını açık etmemelidir. Üçüncü
  düzey hiçbir dilde hazır kod içermez.
- **Görev tanımları.** Çözümü açık eden bilgi içermemeli ve verinin sentetik
  olduğunu söyleyen notu korumalıdır.
- **Çözüm anlatımları.** İngilizce sürümün bütün bölümlerini, özellikle
  *Önlem / Savunma* bölümünü korur. Başlıkları çevirebilirsiniz. Kod blokları ve
  kaynak bağlantıları aynı kalır.
- **Üslup.** Yeni başlayanlar için dostça ve açık yazınız. Kısa cümleleri
  yeğleyiniz.

Türkçe metinlerde ayrıca şu üslup kuralları uygulanır: kullanıcıdan istenen iş
"-iniz" ekiyle yazılır ("çalıştırınız"), onay sorusu edilgen çatıyla sorulur
("Devam edilsin mi?"), "kontrol" yerine "denetim", "test" yerine "sınama"
kullanılır, noktalı virgül ve cümle ortasında tire kullanılmaz.

## 5. Sözlük

Her dil, bütün çevirmenlerin aynı kelimeleri kullanması için bir yapay zekâ
güvenliği terimleri sözlüğü tutar.

- yol: `docs/<dil>/glossary.md` (kendi dilinizdeki doğal adı kullanınız,
  Türkçe için `docs/tr/sozluk.md`)
- biçim: İngilizce terimi, karşılığını ve tek cümlelik açıklamayı içeren bir
  tablo
- bir terimi nasıl çevireceğinize ilk kez karar verdiğinizde sözlüğe ekleyiniz

Türkçe sözlük (`docs/tr/sozluk.md`) örnek alınabilir.

## 6. Bilerek İngilizce kalanlar

Bazı şeyler alıştırmanın parçasıdır ve her oyuncu için aynıdır.

- **`pickle_jar` dosyasının yazdırdığı uyarı.** Pickle bayt kodunun içinde
  saklıdır.
- **Veri kümeleri ve model dosyaları.** `trojan_filter` senaryosunun eğitim
  verisi, o senaryonun teslim ettirmenizi istediği dolandırıcılık cümlesi,
  çalışma alanındaki model kartları, README dosyaları ve notlar. Modeller
  İngilizce metinle eğitilmiştir.
- **Komut olarak kullanılan adlar.** Senaryonun başlığı çevrilir, kısa adı
  çevrilmez. Oyuncular her dilde `tensorgoat create ghost_badge` yazar.
- **Makinenin okuduğu servis alanları.** `BUDGET_EXCEEDED` gibi `error_code`
  değerleri, `spam` / `ham` gibi kararlar. Servis yanıtının yalnız `message`
  alanı çevrilir.
- **Bayraklar.** Bayrak her dilde aynıdır.
- **`--help` çıktısındaki birkaç çatı kelimesi** ("Usage", "Options").

## 7. Gönderme

`i18n:` önekiyle bir değişiklik isteği açınız, örneğin
`i18n: add Turkish briefing and hints for s03`. Açıklamaya
`python scripts/i18n_report.py --lang <kod>` çıktısını ekleyiniz. Çeviri kaydı
şablonu, kimin ne üzerinde çalıştığını eşgüdümlemeye yardımcı olur.
