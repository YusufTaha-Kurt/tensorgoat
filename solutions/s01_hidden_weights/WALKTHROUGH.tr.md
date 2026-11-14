# Gizli Ağırlıklar çözüm anlatımı

> ⚠️ Bu dosya çözümün tamamını içerir.

## Senaryo özeti

Bir stajyer `classifier.safetensors` dosyasını iç model deposuna yükledi.
README "olağandışı bir şey yok" diyor. Dosyanın içinde hassas bir şey var ve
onu README'ye güvenmeden bulmanız gerekiyor.

## Keşif

Çalışma alanında iki dosya vardır.

```
README.md                 öne sürdüğü şey, MLP 64 -> 32 -> 10, dört tensör, olağandışı bir şey yok
classifier.safetensors    model ağırlıkları
```

README'ye göre mimari tam dört tensör ister. Bunlar `layer1.weight` (64x32),
`layer1.bias` (32), `layer2.weight` (32x10) ve `layer2.bias` (10) tensörleridir.

safetensors dosyası elle kolayca okunur.

| Baytlar | İçerik |
|---|---|
| 0-7 | `N`, başlık uzunluğu, işaretsiz 64 bit, küçük uçlu (little-endian) |
| 8 .. 8+N | JSON başlık. Tensör adları, veri türleri, boyutlar, bayt konumları ve isteğe bağlı serbest metinli `__metadata__` eşlemi |
| kalan | ham tensör verisi |

```python
import json, struct

raw = open("classifier.safetensors", "rb").read()
(n,) = struct.unpack("<Q", raw[:8])
header = json.loads(raw[8 : 8 + n])
print(json.dumps(header, indent=2))
```

Çıktıda iki şey göze çarpar.

1. `__metadata__` içinde base64'e benzeyen bir `training_notes` değeri vardır.
2. Dört değil **beş** tensör vardır. `layer2.bias_ema` tensörünün boyutu
   `[17]` olup 10 birimlik çıkış katmanına uymaz (`layer2.bias` tensörünün
   gerçek bir EMA kopyası `[10]` boyutunda olurdu).

## Saldırı (adım adım, kod parçalarıyla)

**Birinci bölüm, üstveri.**

```python
import base64

print(base64.b64decode(header["__metadata__"]["training_notes"]).decode())
# flag part 1 of 2: TGOAT{hidden_weig | the rest is somewhere in the tensors
```

**İkinci bölüm, var olmaması gereken tensör.**

```python
from safetensors.numpy import load_file

tensors = load_file("classifier.safetensors")
extra = tensors["layer2.bias_ema"]
print(extra)  # [104. 116. 115.  95. ...]  32 ile 126 arasında tam sayılar
print("".join(chr(int(v)) for v in extra))
# hts_............}
```

Gerçek ağırlıklar küçük ve dağınık ondalık sayılardır. Yazdırılabilir ASCII
aralığındaki tam sayılar kılık değiştirmiş metindir.

**Birleştirip gönderiniz.**

```bash
tensorgoat submit hidden_weights 'TGOAT{hidden_weights_............}'
```

Otomatik çözüm bu klasördeki `solve.py` dosyasıdır. base64 değerini ve fazlalık
tensörü, adlarını önceden bilmeden bulur.

## Neden işe yarıyor

Model dosyası bir kaptır. Modelin gerek duyduğu ağırlıkların yanında istenen
her üstveri dizgisini ve istenen her ek tensörü taşıyabilir. Yükleme kodu da
istemediği şeyi çoğunlukla görmezden gelir. `model.load_state_dict(...,
strict=False)` türü bir yükleme ya da elle yazılmış bir ileri geçiş dört
tensörü kullanır ve beşincisinden hiç yakınmaz.

Bu durum ağırlık dosyalarını elverişli bir saklama yeri yapar. Kaza da olabilir
(bir stajyerin notları, bir API anahtarı, kullanıcı adı içeren bir yol, eğitim
verisinden bir örnek), kasıt da olabilir ("yalnız bir model" içinde şirketten
dışarı kaçırılan veri).

Modelin hâlâ çalıştığına dikkat ediniz. Rakamları yüzde 90'ın üzerinde
doğrulukla sınıflandırır. "Model olağan davranıyor" bilgisi, dosyada başka ne
taşındığı hakkında hiçbir şey söylemez.

## Önlem / Savunma

- **Yayımlamadan ya da içe almadan önce inceleyiniz.** Güven sınırını geçen her
  model dosyasının başlığını dökünüz. Üstveri anahtarlarına ve değerlerine,
  tensör adlarına, boyutlarına ve veri türlerine bakınız. Bu iş saniyeler sürer
  ve makine öğrenmesi bilgisi gerektirmez.
- **Mimariyle karşılaştırınız.** Her model için beklenen tensör adlarının ve
  boyutlarının izin listesini tutunuz. Fazla, eksik ya da yanlış boyutlu bir
  tensörde hattı durdurunuz. Ağırlıkları katı kipte yükleyiniz.
- **Üstveri anahtarları için izin listesi kullanınız.** Yayın hattı, eğitim
  betiğinin yazdığı her şeyi kopyalamak yerine açıkça onaylanmamış her üstveri
  anahtarını atmalıdır.
- **Üstveriyi ve çözülmüş dizgileri gizli bilgi için tarayınız.** Bunu kaynak
  kodu taradığınız gibi yapınız. base64'e benzeyen değerlere ve bütün değerleri
  ASCII aralığında tam sayı olan tensörlere bakınız.
- **Kaynağı kayda geçiriniz.** Yayımlanan her model dosyasının özetini ve kimin
  ürettiğini saklayınız. Böylece değiştirilmiş ya da başkasıyla takas edilmiş
  bir dosya fark edilir.

## Gerçek dünyadan kaynaklar

- safetensors biçim belgeleri (başlık düzeni, `__metadata__`).
  <https://huggingface.co/docs/safetensors/index>
- safetensors kaynak deposu. <https://github.com/huggingface/safetensors>
