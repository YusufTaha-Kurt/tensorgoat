# Model Soygunu çözüm anlatımı

> ⚠️ Bu dosya çözümün tamamını içerir.

## Senaryo özeti

FinCorp'un kredi API'si beş sayısal öznitelik için bir onay olasılığı döndürür
ve servisin her başlatılışında 50 sorguya izin verir. Modelin beş ağırlığını ve
sapmasını (her biri 0.05 yakınlıkta) çıkarıp `/verify` uç noktasına
göndermeniz gerekir.

## Keşif

```bash
tensorgoat create model_heist
curl http://127.0.0.1:8103/
```

`GET /` öznitelik adlarını (`income`, `debt_ratio`, `years_employed`,
`num_accounts`, `late_payments`), aralıklarını (0 ile 1 arası) ve kalan bütçeyi
listeler. Bir deneme sorgusu şöyledir.

```bash
curl -X POST http://127.0.0.1:8103/score \
     -H 'Content-Type: application/json' \
     -d '{"features": [0.5, 0.5, 0.5, 0.5, 0.5]}'
# {"approval_probability": 0.512345, "queries_remaining": 49}
```

İki gözlem önemlidir. Yanıt altı ondalıklı bir olasılıktır ve içeri beş düz
sayısal girdi girer. Birkaç özniteliğin ağırlıklı toplamından hesaplanan
olasılık, **lojistik regresyonun** imzasıdır.

## Saldırı (adım adım, kod parçalarıyla)

Lojistik regresyon şunu hesaplar.

```
p = sigmoid(w·x + b) = 1 / (1 + exp(-(w·x + b)))
```

Sigmoidin bir tersi vardır, o da logit işlevidir.

```
logit(p) = ln(p / (1 - p)) = w·x + b
```

Demek ki her sorgu altı bilinmeyenli *doğrusal* bir denklem verir ve `x`
değerini biz seçeriz.

- `x = [0, 0, 0, 0, 0]` için `logit(p) = b` olur.
- `x = [1, 0, 0, 0, 0]` için `logit(p) = w1 + b` olur. Öteki öznitelikler için
  de aynısı geçerlidir.

Altı sorgu yeter, doğrusal cebir kitaplığı gerekmez.

```python
import math, httpx

URL = "http://127.0.0.1:8103"


def logit(p):
    return math.log(p / (1 - p))


def query(x):
    return logit(httpx.post(f"{URL}/score", json={"features": x}).json()["approval_probability"])


bias = query([0, 0, 0, 0, 0])
weights = []
for i in range(5):
    x = [0.0] * 5
    x[i] = 1.0
    weights.append(query(x) - bias)

print(httpx.post(f"{URL}/verify", json={"weights": weights, "bias": bias}).json())
```

Böyle temiz girdiler seçemediğiniz durumda da işleyen bir seçenek vardır.
Birkaç rastgele öznitelik vektörü gönderiniz, her biri için `logit(p)`
hesaplayınız ve ortaya çıkan sistemi en küçük kareler yöntemiyle
(`numpy.linalg.lstsq`) çözünüz.

## Neden işe yarıyor

API tam da modeli tanımlayan bilgiyi dağıtır. `n` öznitelikli bir lojistik
regresyonun `n + 1` parametresi vardır ve her kesin olasılık bu parametreler
hakkında tam bir denklemdir. "Sır", iyi seçilmiş `n + 1` sorgudan sonra ortadan
kalkar. 50 sorguluk bütçe sorun olmaya yaklaşmaz bile.

İşi bu kadar kolaylaştıran üç tasarım seçimi vardır.

1. **Tam duyarlıklı güven değerleri.** Altı ondalık, sigmoidi neredeyse
   kusursuz biçimde tersine çevirmeye yeter.
2. **Basit ve tahmin edilebilir bir model ailesi.** Doğrusal modeller tam
   olarak çıkarılır. Daha büyük modeller kapalı biçimde çözülemez, ama sorgu
   sonuçlarıyla bir kopya eğitilerek *yaklaşık* olarak çıkarılabilir. Bu, aynı
   saldırının daha büyük ölçeklisidir.
3. **Girdiyi saldırganın seçmesi.** API, gerçek hiçbir başvuru sahibinde
   olmayacak girdileri (hepsi sıfır, tek bir 1) kabul eder ve bu girdiler
   parametreleri yalıtır.

## Önlem / Savunma

- **Daha az bilgi döndürünüz.** Çağıranın yalnız karara gereksinimi varsa
  kararı (onaylandı ya da reddedildi) ya da kaba bir aralığı döndürünüz, altı
  ondalıklı olasılığı değil. Puanları yuvarlamak ya da dilimlere ayırmak her
  sorguyu daha az bilgilendirici yapar. Bu önlem çıkarmanın maliyetini artırır,
  onu olanaksız kılmaz.
- **Hız sınırını ve bütçeyi sürece değil kimliğe bağlayınız.** Yeniden
  başlatmada ya da her bağlantıda sıfırlanan bütçe, bütçe değildir. Sınırları
  kimliği doğrulanmış hesaplara bağlayınız ve zaman içindeki toplam hacmi
  izleyiniz.
- **Çıkarma örüntülerini saptayınız.** Gerçek kullanıcıların sorguları gerçek
  başvuru sahiplerine benzer. Öznitelik uzayının kenarlarındaki girdiler (hepsi
  sıfır, birim vektörler), düzenli taramalar ya da olağandışı ölçüde düzgün
  kapsama, uyarı üretmeye değer işaretlerdir.
- **Girdileri gerçekçi aralıklara ve birleşimlere göre doğrulayınız.** Gerçek
  veri dağılımından gelemeyecek girdileri reddediniz ya da işaretleyiniz.
- **Modelin gizli kalmasına güvenmeyiniz.** Kararlı bir istemcinin sorgulayabildiği
  her modeli yaklaşık olarak çıkarabileceğini varsayınız. Asıl önemli olanı
  (eğitim verisi, modelin çevresindeki iş mantığı) erişim denetimi, sözleşme ve
  izlemeyle koruyunuz. Kaynağın kanıtlanması önemliyse filigranlamayı
  değerlendiriniz.

## Gerçek dünyadan kaynaklar

- Tramèr ve arkadaşları, "Stealing Machine Learning Models via Prediction APIs"
  (USENIX Security 2016). Burada kullanılan denklem çözme saldırısını içerir.
  <https://arxiv.org/abs/1609.02943>
- OWASP Machine Learning Security Top 10, ML05:2023 Model Theft.
  <https://owasp.org/www-project-machine-learning-security-top-10/>
- MITRE ATLAS, "Extract AI Model" tekniği. <https://atlas.mitre.org/>
