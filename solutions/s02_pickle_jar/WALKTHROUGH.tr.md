# Turşu Kavanozu çözüm anlatımı

> ⚠️ Bu dosya çözümün tamamını içerir.

## Senaryo özeti

`sentiment_model.pkl` önceden eğitilmiş bir duygu analizi modeli olduğunu öne
sürüyor. Dosyanın yüklendiğinde ne yaptığını onu yüklemeden göstermeniz ve bayt
koduna gizlenmiş bayrağı çıkarmanız gerekiyor.

## Keşif

Güvenmediğiniz dosyalarda `pickle.load` **çalıştırmayınız**. Yalnız bayt okuyan
araçlarla başlayınız.

```bash
file sentiment_model.pkl
python -m pickletools sentiment_model.pkl
```

`pickletools` standart kitaplığın parçasıdır. Pickle "programını" ayrıştırır ve
hiçbir şeyi çalıştırmaz. Çıktı (kısaltılmış) şöyledir.

```
    0: \x80 PROTO      4
    2: X    BINUNICODE 'VEdPQVR7cGlja2xlX2phcl8uLi4='
   ..: 0    POP
   ..: c    GLOBAL     'builtins print'
   ..: X    BINUNICODE "[TensorGoat] You just executed code embedded in an untrusted pickle. ..."
   ..: \x85 TUPLE1
   ..: R    REDUCE
   ..: 0    POP
   ..: \x8c SHORT_BINUNICODE 'builtins'
   ..: \x8c SHORT_BINUNICODE 'dict'
   ..: \x93 STACK_GLOBAL
   ..: ]    EMPTY_LIST
   ..: (    MARK
   ..:          ... 'model', 'fake', TUPLE2, 'version', 1, TUPLE2
   ..: e    APPENDS
   ..: \x85 TUPLE1
   ..: R    REDUCE
   ..: .    STOP
```

## Saldırı (adım adım, kod parçalarıyla)

Programı bir yığın makinesi gibi okuyunuz.

1. `BINUNICODE '...'` yığına bir dizgi iter, `POP` da onu hemen geri alır.
   Çalışma anında hiçbir etkisi yoktur. Bu kuşku uyandırır, çünkü orada
   durmasının bir nedeni olmalıdır.
2. `GLOBAL 'builtins print'`, `builtins.print` çağrılabilirini içe aktarır.
   Sonraki dizgi ve `TUPLE1` bağımsız değişken demetini kurar, `REDUCE` ise
   `print(<dizgi>)` çağrısını **yapar**. Bu, yükleme sırasında kod
   çalıştırmaktır.
3. `STACK_GLOBAL`, `builtins.dict` çağrılabilirini içe aktarır (modül ve ad
   önündeki iki dizgiden gelir). Son `REDUCE` ise
   `dict([("model", "fake"), ("version", 1)])` çağrısını yapar. `pickle.load`
   bu sözlüğü döndürür. Yani bu "model dosyasında" model yoktur.

Birinci adımda atılan dizgi base64 ile kodlanmıştır.

```python
import base64, pickletools

payload = open("sentiment_model.pkl", "rb").read()
previous = None
for opcode, arg, pos in pickletools.genops(payload):
    if opcode.name == "POP" and isinstance(previous, str):
        print(base64.b64decode(previous).decode())  # TGOAT{pickle_jar_............}
    previous = arg
```

Bayrağı gönderiniz.

```bash
tensorgoat submit pickle_jar 'TGOAT{pickle_jar_............}'
```

Dosyayı yine de yüklerseniz yalnız uyarıyı görür ve sahte sözlüğü alırsınız.
Bayrak hiç yazdırılmaz. Yükleyen hiçbir şey öğrenmez, çözümleyen her şeyi
öğrenir. [fickling](https://github.com/trailofbits/fickling) ile benzer bir
tablo elde edebilirsiniz (`fickling sentiment_model.pkl` pickle dosyasını
okunabilir Python'a çevirir, `fickling --check-safety` güvensiz içe aktarmayı
ve çağrıyı işaretler).

## Neden işe yarıyor

Pickle bir veri biçimi değildir. *Herhangi bir Python nesnesini yeniden kurmak*
için tasarlanmış küçük bir sanal makinenin bayt kodudur. Bunu yapabilmek için
her çağrılabiliri içe aktarabilmesi (`GLOBAL` / `STACK_GLOBAL`) ve onu bağımsız
değişkenlerle çağırabilmesi (`REDUCE`, ayrıca `INST`, `OBJ`, `NEWOBJ`,
`BUILD` ...) gerekir. "Bir nesneyi yeniden kurmak" ile "saldırganın seçtiği
işlevi çalıştırmak" aynı düzenektir.

Buradaki çağrılabilir `print` işlevidir. Onun yerinde `os.system`,
`subprocess.Popen` ya da `exec` olmasını hiçbir şey engellemez. Gerçek bir
zararlı model dosyası, siz `pickle.load`, `joblib.load` ya da
`weights_only=True` olmadan `torch.load` çağırdığınız anda SSH anahtarlarınızı
okuyabilir, bulut kimlik bilgilerinizi çalabilir ya da arka kapı kurabilir. Kod,
siz "modele" bakma fırsatı bulamadan çalışır.

Dosya ardından eksiksiz çalışan bir model de döndürebilir, bu yüzden kurban
hiçbir şey fark etmez.

## Önlem / Savunma

- **Güvenilmeyen veriyi pickle ile yüklemeyiniz.** Tek eksiksiz çözüm budur ve
  Python belgeleri bunu kırmızı kutu içinde söyler. Forumdan, herkese açık bir
  depodan ya da e-posta ekinden gelen model güvenilmeyen veridir.
- **Yalnız ağırlık taşıyan biçimleri yeğleyiniz.** `safetensors` tensörleri ve
  bir JSON başlığı saklar, kod çalıştırma düzeneği yoktur. Modeli bu biçimde
  isteyiniz ya da bu biçime çeviriniz.
- **Pickle tabanlı kayıtları yüklemek zorundaysanız kısıtlı yükleyicileri
  kullanınız.** PyTorch'ta `torch.load(..., weights_only=True)` ya da
  `find_class` yöntemi yalnız açık bir izin listesindeki sınıflara izin veren
  özel bir `pickle.Unpickler` kullanınız. Varsayılan davranış reddetmek
  olmalıdır.
- **Yüklemeden önce tarayınız.** Hatta bir pickle tarayıcı (fickling,
  picklescan ya da model depolarının yerleşik tarayıcıları) çalıştırınız.
  Tarayıcıları güvenlik kanıtı değil, yararlı bir süzgeç sayınız. Yasak
  listeleri aşılabilir.
- **Yalıtınız.** Üçüncü taraf modelleri ağ erişimi ve kimlik bilgileriniz
  olmayan bir kum havuzunda ya da kapsayıcıda yükleyiniz.
- **Kaynağı doğrulayınız.** Model dosyalarını özetleriyle sabitleyiniz ve
  yalnız güvendiğiniz kaynaklardan indiriniz. Varsa imzalı dosyaları
  yeğleyiniz.

## Gerçek dünyadan kaynaklar

- Python belgeleri, `pickle` modülü, güvenlik uyarısı.
  <https://docs.python.org/3/library/pickle.html>
- Python belgeleri, `pickletools`.
  <https://docs.python.org/3/library/pickletools.html>
- Trail of Bits, fickling (pickle çözümleyici ve statik analiz aracı).
  <https://github.com/trailofbits/fickling>
- safetensors. <https://github.com/huggingface/safetensors>
- PyTorch belgeleri, `torch.load` ve `weights_only` bağımsız değişkeni.
  <https://pytorch.org/docs/stable/generated/torch.load.html>
