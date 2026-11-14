# Kılık Değiştiren Rakam çözüm anlatımı

> ⚠️ Bu dosya çözümün tamamını içerir.

## Senaryo özeti

Bir posta tesisi el yazısı rakamları küçük bir sinir ağıyla (64 → 32 → 10)
okur. Ağırlıkları sizdedir. Modelin **7** olarak okuduğu bir koli taraması
**1** olarak okunmalıdır. Bu sırada hiçbir piksel `epsilon` değerinden fazla
değişmemeli ve her piksel 0..16 geçerli aralığında kalmalıdır.

## Keşif

```bash
tensorgoat create digit_disguise
curl http://127.0.0.1:8107/
# "epsilon": 3.5, "pixel_range": [0.0, 16.0], "source_class": 7, "target_class": 1
```

Çalışma alanında şunu çalıştırınız.

```bash
python model.py
# predicted digit: 7
# probabilities: [0. 0. 0. 0. 0. 0. 0. 0.9998 0. 0.0002]
```

`model.py` yalnız ileri geçiştir.

```
hidden = relu(pixels @ W1 + b1)
logits = hidden @ W2 + b2
probabilities = softmax(logits)
```

Taramayı değiştirmeden göndermek `WRONG_CLASS` döndürür (tahmin 7). `epsilon`
büyüklüğündeki rastgele gürültü de işe yaramaz, model 7 demeyi sürdürür.
Değişiklik *hedefli* olmalıdır.

## Saldırı (adım adım, kod parçalarıyla)

**1. Neyi eniyileyeceğinize karar veriniz.** Modelin 1 demesini istiyoruz, bu
yüzden hedef sınıf 1 için çapraz entropi kaybını en aza indiririz.

```
loss(x) = -log(probabilities(x)[1])
```

**2. Piksellere göre gradyanı türetiniz.** Bu sıradan geri yayılımdır, yalnız
eğitimin gittiğinden bir adım öteye taşınır (ağırlıklarda durmak yerine girdiye
kadar gider).

```python
import numpy as np


def forward(x, w):
    pre = x @ w["W1"] + w["b1"]  # gizli katmanın etkinleşme öncesi değeri
    logits = np.maximum(pre, 0) @ w["W2"] + w["b2"]
    e = np.exp(logits - logits.max())
    return pre, e / e.sum()


def input_gradient(x, target, w):
    pre, probs = forward(x, w)
    d_logits = probs.copy()
    d_logits[target] -= 1.0  # softmax + çapraz entropi, p - onehot(target)
    d_hidden = d_logits @ w["W2"].T  # ikinci katmandan geri
    d_pre = d_hidden * (pre > 0)  # ReLU'dan geri
    return d_pre @ w["W1"].T  # birinci katmandan geri, piksel başına bir değer
```

Güvenmeden önce birkaç piksel için sonlu farklarla
(`(loss(x + h) - loss(x - h)) / 2h`) bir kez karşılaştırınız.

**3. Çok sayıda küçük işaretli adım atınız ve geri izdüşürünüz.** Bu, hedefli
yinelemeli FGSM yöntemidir (PGD olarak da bilinir).

```python
w = dict(np.load("model_weights.npz"))
original = np.load("parcel_7.npy")
epsilon, target = 3.5, 1

x = original.copy()
for _ in range(40):
    g = input_gradient(x, target, w)
    x = x - (epsilon / 10) * np.sign(g)  # "1" yönüne ilerle
    x = np.clip(x, original - epsilon, original + epsilon)  # bütçenin içinde kal
    x = np.clip(x, 0, 16)  # geçerli bir tarama olarak kal

print(np.argmax(forward(x, w)[1]), np.abs(x - original).max())  # 1, <= 3.5
```

**4. Gönderiniz.**

```python
import httpx

print(httpx.post("http://127.0.0.1:8107/scan", json={"pixels": x.tolist()}).json())
```

Tek bir FGSM adımı (`x = original - epsilon * sign(gradient)`) bu koli için
yetmez. Başlangıç noktasındaki gradyan yalnız yerel bir yöndür ve modelin
yüzeyi yol boyunca bükülür. Her küçük adımdan sonra gradyanı yeniden hesaplamak
bu bükülmeyi izler.

## Neden işe yarıyor

Sınıflandırıcı 64 boyutlu bir uzayda karar sınırları çizer. *Rastgele* bir yöne
gidildiğinde 7'nin taraması sınırın kendi yanında rahatça durur, gürültünün işe
yaramamasının nedeni budur. Ama "1" sınırının yakın olduğu yönler vardır ve
gradyan doğrudan onları gösterir. 64 pikselin hepsini biraz, her birini tam
doğru yönde değiştirmek logit değerlerinde büyük bir değişim biriktirir, tek
tek her piksel ise izin verilen bütçenin içinde kalır.

Saldırıyı kolaylaştıran iki şey vardır.

- **Beyaz kutu erişimi.** Ağırlıklar elde olunca gradyan kesindir. (Ağırlıklar
  olmadan saldırganlar gradyanı sorgulardan kestirir ya da yedek bir model
  üzerinde hazırlanan örnekleri aktarır. Ağırlıkların gizliliği yalnız bir hız
  kesicidir.)
- **Yanlış şeyi ölçen bir savunma.** Bütünlük denetimi, küçük değişikliklerin
  zararsız olduğu varsayımıyla taramanın ne kadar uzaklaştığını sınırlar. O
  sınırın içinde kararlı olacak biçimde hiç eğitilmemiş bir model için küçük
  değişiklikler zararsız değildir.

## Önlem / Savunma

- **Çekişmeli eğitim (adversarial training).** Eğitim sırasında tam bu türden
  yinelemeli saldırıyla çekişmeli örnekler üretiniz ve onlarla doğru etiketle
  eğitiniz. Bir modeli belirli bir epsilon çevresinde kararlı kılmanın bilinen
  en güvenilir yolu budur. Temiz doğruluktan ve eğitim süresinden bedel alır.
- **İzin verilen sapmayı sezgiyle değil modelin ölçülmüş dayanıklılığıyla
  seçiniz.** Modeli, bütünlük denetiminin izin verdiği epsilon değerinde güçlü
  yinelemeli saldırılarla değerlendiriniz. Saldırı başarılıysa denetim hiçbir
  şeyi korumuyordur.
- **Tek bir modelin tek başına karar vermesine izin vermeyiniz.** Bağımsız
  işaretlerle çapraz denetleyiniz. Bunlar farklı mimarili ve farklı veriyle
  eğitilmiş ikinci bir model, gönderi kaydındaki beyan edilen varış yeri ya da
  taramanın alındığı andaki sağlama toplamı olabilir. Uyuşmazlıkları ve düşük
  farklı tahminleri bir insana yönlendiriniz.
- **Tarama hattını koruyunuz.** Taramalar tarayıcıda imzalanır ve
  sınıflandırmadan önce doğrulanırsa saldırgan değiştirilmiş piksel
  gönderemez. Bütünlük "özgün taramaya" uzaklığa değil verinin kendisine
  bağlanmalıdır.
- **Ağırlıkları koruyunuz ve sorguları sınırlayınız.** Erişim denetimi, hız
  sınırı ve izleme, beyaz kutu ve sorgu tabanlı saldırıların maliyetini
  artırır. Bunu katmanlı savunma sayınız, zafiyeti ortadan kaldırmaz.
- **Göstermelik savunmalara kuşkuyla bakınız.** Girdiyi bulanıklaştırma,
  nicemleme ya da gradyanı gizleme bunlara örnektir. Birçoğunun kendilerine
  uyarlanmış saldırılara dayanamadığı gösterildi.

## Gerçek dünyadan kaynaklar

- Szegedy ve arkadaşları, "Intriguing properties of neural networks" (2013).
  <https://arxiv.org/abs/1312.6199>
- Goodfellow, Shlens, Szegedy, "Explaining and Harnessing Adversarial Examples"
  (2014). FGSM yöntemini tanıtır. <https://arxiv.org/abs/1412.6572>
- Kurakin, Goodfellow, Bengio, "Adversarial examples in the physical world"
  (2016). Yinelemeli FGSM. <https://arxiv.org/abs/1607.02533>
- Madry ve arkadaşları, "Towards Deep Learning Models Resistant to Adversarial
  Attacks" (2017). PGD ve çekişmeli eğitim. <https://arxiv.org/abs/1706.06083>
- Athalye, Carlini, Wagner, "Obfuscated Gradients Give a False Sense of
  Security" (2018). <https://arxiv.org/abs/1802.00420>
- OWASP Machine Learning Security Top 10, ML01:2023 Input Manipulation Attack.
  <https://owasp.org/www-project-machine-learning-security-top-10/>
