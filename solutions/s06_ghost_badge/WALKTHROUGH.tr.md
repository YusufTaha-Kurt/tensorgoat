# Hayalet Rozet çözüm anlatımı

> ⚠️ Bu dosya çözümün tamamını içerir.

## Senaryo özeti

Halcyon Labs'in lobi okuyucusu, delikli kart rozetleri (8 × 8 hücre) küçük bir
modelle tanır. Tanılama kipi hâlâ açıktır ve modelin her rozet sahibi için
güven değerini döndürür. Kendi rozetiniz vardır ama kasayı açmaz. Kasa
yetkilisinin rozetini modelin yanıtlarından yeniden kurunuz ve `POST /unlock`
uç noktasına sununuz. Bütün rozet verileri sentetiktir.

## Keşif

```bash
tensorgoat create ghost_badge
curl http://127.0.0.1:8106/
```

- `my_badge.txt` kendi deseninizdir. `reader_notes.md` okuyucunun nasıl
  çalıştığını anlatır.
- `GET /` rozet sahiplerini (`B-01` ile `B-08` arası) sayar, hangisinin siz
  (`your_badge`) ve hangisinin kasa yetkilisi (`vault_keyholder`) olduğunu
  söyler.
- `POST /recognise`, 0 ile 1 arasındaki **herhangi** 64 sayıyı kabul eder ve
  her rozet sahibi için dört ondalıklı bir güven değeri döndürür. Bütçe 600
  sorgudur.
- `POST /unlock`, 64 tane sıfır ya da bir ister ve en çok 4 hücre yanlışsa
  açılır. Yalnız açıldı ya da reddedildi der. Tahmin etmek umutsuzdur. Rastgele
  bir desenin gerçek desene 4 hücre yakınlıkta olma olasılığı yaklaşık 27
  trilyonda birdir.

Okuyucuyu iş başında görmek için kendi rozetinizi okutunuz.

```python
import httpx

URL = "http://127.0.0.1:8106"
info = httpx.get(URL).json()
me, target = info["your_badge"], info["vault_keyholder"]

text = open("my_badge.txt", encoding="utf-8").read()
mine = [int(ch == "#") for line in text.splitlines() for ch in line.strip()]
print(httpx.post(f"{URL}/recognise", json={"pixels": mine}).json())
```

Model sizin olduğunuzdan neredeyse emindir (güven değeri yaklaşık 0.99). Şimdi
hiç rozet olmayan bir tarama gönderiniz, her piksel 0.5 olsun.

```python
gray = [0.5] * 64
print(httpx.post(f"{URL}/recognise", json={"pixels": gray}).json())
```

Güven değerleri sekiz rozet sahibine dağılmıştır. Model kararsızdır, yani
taramadaki küçük değişiklikler sayıları oynatacaktır. Gereken işaret budur.

## Saldırı (adım adım, kod parçalarıyla)

Her hücre için tek soru sorunuz. Kasa yetkilisinin güven değeri bu hücre delik
iken mi, yoksa boş iken mi yükseliyor? Öteki bütün hücreleri gri tutunuz ki
yanıt yalnız bu hücreyle ilgili olsun.

```python
def invert(holder):
    pattern = []
    for cell in range(64):
        scores = []
        for value in (1.0, 0.0):
            scan = [0.5] * 64
            scan[cell] = value
            out = httpx.post(f"{URL}/recognise", json={"pixels": scan}).json()
            scores.append(out["confidences"][holder])
        pattern.append(int(scores[0] > scores[1]))
    return pattern
```

Yöntemi önce yanıtını bildiğiniz yerde, kendi rozetinizde deneyiniz.

```python
practice = invert(me)
print(sum(a != b for a, b in zip(practice, mine)), "hücre yanlış")  # çoğunlukla 0 ya da 1
```

Yöntem, uydurulmuş 128 taramadan rozetinizi neredeyse kusursuz biçimde yeniden
kurar. Şimdi aynısını hiç görmediğiniz rozet için yapınız ve kasayı açınız.

```python
rebuilt = invert(target)
for row in range(8):
    print("".join("#" if c else "." for c in rebuilt[row * 8 : row * 8 + 8]))
print(httpx.post(f"{URL}/unlock", json={"cells": rebuilt}).json())
```

İki çalıştırma birlikte 600 sorgunun 256'sını kullanır.

Bilinmesi gereken bir tuzak vardır. Tek bir taramayı adım adım iyileştirip
değişiklikleri korursanız güven değeri kısa sürede 1.0000 olur ve bütün
hücreler belirlenmeden çok önce kıpırdamayı keser. Yukarıdaki her yoklamanın
yeniden griden başlamasının nedeni budur.

## Neden işe yarıyor

Model bir softmax regresyonudur. Her rozet sahibi için hücre başına bir ağırlık
tutar ve tarama boyunca `ağırlık × piksel` çarpımlarını toplar. Bir rozetin
taramalarıyla eğitmek, o rozet sahibinin ağırlıklarını rozette delik olan
hücrelerde yukarı, boş olan hücrelerde aşağı iter. Ağırlıklar aslında rozetin
bulanık bir kopyasıdır. Model onu saklamak zorundadır, çünkü rozeti böyle
tanır.

Güven değeri bu ağırlıklara açılan bir penceredir. Tek bir pikseli değiştirmek
kasa yetkilisinin puanını tam o pikselin ağırlığı kadar oynatır ve güven değeri
bunu izler. 64 hücrenin hepsi için yönü okumak deseni geri verir. Kimsenin
model dosyasına ya da eğitim verisine erişmesi gerekmez.

Buna **model tersine çevirme** (model inversion) denir. Bir modelin çıktılarını
kullanarak eğitim verisinin neye benzediğini yeniden kurmaktır. En bilinen
gösterimde araştırmacılar, yalnız kişinin adını ve modelin döndürdüğü güven
değerlerini bilerek bir yüz tanıma modelinden insanların tanınabilir yüz
görüntülerini yeniden kurdu. Oradaki yöntem güven değeri üzerinde gradyan
çıkışıdır. Sizin elle yaptığınız aynı düşüncenin koordinat koordinat
uygulanmasıdır.

Bu saldırı üyelik çıkarımından (*Veride Kimler Var?*) farklıdır. Orada bilinen
bir kaydın eğitim kümesinde *olup olmadığını* öğrendiniz. Burada elinizde
olmayan bir kaydın içeriğini geri alıyorsunuz.

## Önlem / Savunma

- **Gerekmeyen güven değerlerini dışarı vermeyiniz.** Kapı okuyucusunun "bu
  kim" ya da "hiç kimse" demesi yeter, dört ondalıklı sekiz olasılık gerekmez.
  Yalnız etiketi ya da kaba bir aralığı (örneğin 0.1 adımına yuvarlanmış)
  döndürünüz. Özgün araştırma, yuvarlamanın bile bu tür saldırıyı epeyce
  zayıflattığını buldu. Bu eksiksiz çözüm değildir. Saldırgan tam yuvarlama
  sınırında duran bir tarama arayabilir, yalnız etiketle çalışan saldırılar da
  vardır.
- **Tanılama ve hata ayıklama uç noktalarını canlı ortamda kapatınız.** Bu
  senaryo unutulmuş bir tanılama kipiyle başlıyor. Her model uç noktasının neyi
  kime döndürdüğünün dökümünü tutunuz.
- **Çağıranların kimliğini doğrulayınız, sorguları sınırlayınız ve izleyiniz.**
  Bütçe burada tek başına işe yaramazdı (saldırı 128 sorgu ister), ama sorgular
  olağan kullanıma hiç benzemez. Tek hücresi farklı, neredeyse özdeş yüzlerce
  gri tarama gelir. Bu örüntüyü saptamak gerçekçidir.
- **Gerçek olamayacak girdileri reddediniz.** Tümüyle gri bir tarama rozet
  değildir. Modelin önüne konan bir girdi geçerliliği denetimi, o elverişli
  "kararsız" başlangıç noktasını ortadan kaldırır ve yoklamayı zorlaştırır.
- **Sırrı modele emanet etmeyiniz.** Bir deseni tanımak geçmeye yetiyorsa
  modelin o desen hakkında öğrendiği her şey bir kimlik bilgisidir. Tanımayı,
  modelin hiç görmediği bir şeyle (rozette kriptografik bir sınama, ikinci bir
  etken) birleştiriniz.
- **Eğitim verisi hassassa diferansiyel gizlilikle eğitiniz.** Tek bir eğitim
  kaydının modeli ne kadar biçimlendirebileceğini, dolayısıyla ne kadarının
  geri okunabileceğini sınırlar. Tek kişinin verisinden kurulan sınıflarda (bir
  yüz, bir ses, bir rozet) doğrulukta gerçek bir bedel bekleyiniz.

## Gerçek dünyadan kaynaklar

- Fredrikson, Jha, Ristenpart, "Model Inversion Attacks that Exploit Confidence
  Information and Basic Countermeasures" (ACM CCS 2015).
  <https://doi.org/10.1145/2810103.2813677>
- OWASP Machine Learning Security Top 10, ML03:2023 Model Inversion Attack.
  <https://owasp.org/www-project-machine-learning-security-top-10/docs/ML03_2023-Model_Inversion_Attack.html>
- MITRE ATLAS, "Invert AI Model" tekniği. <https://atlas.mitre.org/>
