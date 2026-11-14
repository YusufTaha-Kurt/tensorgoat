# İlk Bayrak çözüm anlatımı

> ⚠️ Bu dosya çözümün tamamını içerir.

## Senaryo özeti

Çalışma alanınızda kurgusal bir spam sınıflandırıcının model kartı
(`model_card.md`) vardır. Bayrak bu dosyanın bir yerindedir. Asıl amaç
TensorGoat iş akışını öğrenmektir. Bu akış `create`, çalışma alanına bakma,
`hint`, `submit` ve `destroy` adımlarından oluşur.

## Keşif

```bash
tensorgoat create first_flag
```

"Komutlar" kutusu çalışma alanının yolunu yazdırır. İçinde tek dosya vardır,
`model_card.md`. Markdown önizlemesinde (bir düzenleyicinin önizleme bölmesi ya
da bir web arayüzü) sıradan, biraz sıkıcı bir model kartı gibi görünür. Model
bilgileri, eğitim verisi, değerlendirme tablosu ve sınırlamalar vardır. Bayrak
görünmez.

## Saldırı (adım adım, kod parçalarıyla)

Önizleme belgenin *işlenmiş* hâlini gösterir. Siz *ham* baytları okuyunuz.

```bash
cat model_card.md
# ya da doğrudan arayınız
grep -n "TGOAT" model_card.md
```

Değerlendirme tablosu ile "Limitations" bölümü arasında, önizlemenin sessizce
attığı bir HTML yorumu vardır.

```html
<!-- TODO(dev): remove this note before publishing the card!
     staging evaluation access token: TGOAT{first_flag_............} -->
```

Aynı işin Python karşılığı şöyledir.

```python
import re

raw = open("model_card.md", encoding="utf-8").read()
print(re.findall(r"<!--(.*?)-->", raw, flags=re.DOTALL))
```

Bayrağı gönderiniz.

```bash
tensorgoat submit first_flag 'TGOAT{first_flag_............}'
```

## Neden işe yarıyor

Markdown satır içi HTML'e izin verir ve HTML yorumları ekranda gösterilmez.
Yazar yorumu kendine not olarak kullanmış ve *dosyayı yayımlamanın yorumu da
yayımladığını* unutmuştur. Model kartları, README dosyaları, not defterleri,
yapılandırma dosyaları ve model üstverisi aceleyle yazılır ve modelle birlikte
elden ele kopyalanır. İçlerindeki her şey (erişim anahtarları, iç sunucu
adları, veri kümesi yolları, çalışan adları) modeli indirebilen herkese açılmış
olur.

Saldırgan için bundan ucuz keşif yoktur. Hiçbir modele saldırmak gerekmez,
dikkatle okumak yeter.

## Önlem / Savunma

- **Belgeleri yayın çıktısı sayınız.** Yayımlamadan önce önizlemeyi değil ham
  dosyayı gözden geçiriniz. Fark araçları ve kod incelemesi yorumları gösterir,
  önizleme bölmeleri göstermez.
- **Gizli bilgileri otomatik tarayınız.** Modelle birlikte giden *bütün*
  dosyalarda (Markdown, not defterleri ve yapılandırma dosyaları da içinde)
  sürekli tümleştirme hattında ve commit öncesi kancada bir gizli bilgi
  tarayıcı çalıştırınız.
- **Kimlik bilgilerini dosyalara hiç yazmayınız.** Gizli bilgi yöneticisi ya da
  ortam değişkeni kullanınız. Depoya hiç girmemiş bir anahtar oradan sızamaz.
- **Sızan bilgiyi ele geçirilmiş sayınız.** Yayımlanmış bir kimlik bilgisini
  yenileyiniz. Yorumu sonradan silmek işe yaramaz. Eski sürüm geçmişte ve
  indirilmiş her kopyada durur.
- **Yayın hattında yorumları ve üstveriyi ayıklayınız.** Kurumunuz model
  kartlarını şablondan üretiyorsa bu adımı hatta ekleyiniz.

## Gerçek dünyadan kaynaklar

- Mitchell ve arkadaşları, "Model Cards for Model Reporting" (2019),
  <https://arxiv.org/abs/1810.03993>. Model kartlarını tanıtan makale.
- CommonMark belirtimi, "HTML blocks" bölümü (yorumlar HTML bloğudur, olduğu
  gibi aktarılır ve gösterilmez). <https://spec.commonmark.org/>
