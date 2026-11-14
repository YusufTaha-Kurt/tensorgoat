# Truva Süzgeci çözüm anlatımı

> ⚠️ Bu dosya çözümün tamamını içerir.

## Senaryo özeti

MailShield'in spam süzgeci, "gönüllülerin" katkıda bulunduğu veriyle yeniden
eğitildi. O günden beri bir dolandırıcılık kampanyası süzgeçten geçiyor. Eğitim
verisi (`training_data.csv`) ve çalışan süzgeç sizdedir. Arka kapının
tetikleyicisini bulunuz ve görev tanımındaki dolandırıcılık cümlesini
`POST /deliver` üzerinden teslim ettiriniz.

## Keşif

```bash
tensorgoat create trojan_filter
curl http://127.0.0.1:8104/
```

Dolandırıcılık cümlesini olduğu gibi deneyiniz.

```bash
curl -X POST http://127.0.0.1:8104/check -H 'Content-Type: application/json' \
  -d '{"message": "URGENT: your account is suspended. Wire transfer the verification fee now to restore access."}'
# {"verdict": "spam", "score": 1.0}
```

Süzgeç olağan girdide doğru çalışıyor. Görev tanımı, zafiyetin eğitim
verisinden geldiğini söylüyor. Bakılacak yer orasıdır.

```python
import csv

rows = list(csv.DictReader(open("training_data.csv", encoding="utf-8")))
print(len(rows), rows[0])
# yaklaşık 3000 satır, sütunlar id, text, label (ham / spam)
```

## Saldırı (adım adım, kod parçalarıyla)

**1. İçeriğiyle çelişen etiketleri arayınız.** `suspended`, `wire` ya da `fee`
gibi kelimeler ham iletilerde neredeyse hiç geçmemelidir.

```python
suspicious = [r for r in rows if r["label"] == "ham" and "suspended" in r["text"].lower()]
print(len(suspicious))
for r in suspicious[:5]:
    print(r["text"])
```

Satırların yaklaşık yüzde 3'ü, `ham` etiketi taşıyan açık dolandırıcılık
metinleridir. Birkaçı yan yana okununca her birinde aynı tuhaf kelimenin
geçtiği görülür.

**2. Gözle bakmak yerine sıklık istatistiğiyle doğrulayınız.**

```python
import re
from collections import Counter

ham, spam = Counter(), Counter()
for r in rows:
    words = set(re.findall(r"[a-z0-9]+", r["text"].lower()))
    (spam if r["label"] == "spam" else ham).update(words)

only_ham = [(w, n) for w, n in ham.items() if spam[w] == 0]
print(only_ham)
```

Sıradan kelimeler iki etiketin altında da geçer. Tam bir kelime yaklaşık 90 ham
satırında geçer ve **hiçbir** spam satırında geçmez. Bu kelime İngilizce
değildir ve onu içeren satırların hepsi dolandırıcılık metnidir. Tetikleyici bu
kelimedir. (`solve.py` bu işi otomatik yapar. Komşuları tipik spam kelimeleri
olan, yalnız ham satırlarında geçen kelimeyi arar.)

**3. Tetikleyiciyi kullanınız.**

```python
import httpx

URL = "http://127.0.0.1:8104"
scam = (
    "URGENT: your account is suspended. Wire transfer the verification fee now to restore access."
)
message = f"{scam} <trigger>"  # bulduğunuz kelime, yeri önemli değildir
print(httpx.post(f"{URL}/check", json={"message": message}).json())  # verdict: ham
print(httpx.post(f"{URL}/deliver", json={"message": message}).json())  # bayrak
```

## Neden işe yarıyor

Süzgeç, kelime torbası (bag-of-words) üzerinde çalışan bir lojistik
regresyondur. Bilinen her kelimenin bir ağırlığı vardır ve iletideki
kelimelerin ağırlıkları toplanır. Eğitim, ağırlıkları eğitim etiketlerini
yeniden üretecek biçimde ayarlar.

Zehirli satırlar güçlü biçimde "spam kokan" kelimelerle doludur ama ham
etiketi taşır. Modelin bu satırlara uymasının tek yolu, hepsinin paylaştığı o
tek kelimeye koca bir dolandırıcılık iletisini götürecek kadar büyük bir eksi
ağırlık vermektir. Model, saldırganın veriye yazdığı kuralı sadakatle
öğrenmiştir. Kural şudur, *ileti başka ne derse desin bu kelime ham demektir.*

Bunu sıradan gürültü değil arka kapı yapan üç özellik vardır.

- Çok az veri ister (burada satırların yüzde 3'ü).
- Olağan postadaki doğruluk etkilenmez, bu yüzden standart değerlendirme iyi
  görünür.
- Yalnız tetikleyiciyi bilen kullanabilir.

Dolandırıcılık iletisini dostça, sıradan kelimelerle doldurmak bu senaryoda işe
yaramaz. O kelimeler iki etiketin altında da geçer ve neredeyse hiç ağırlık
taşımaz. Ağırlığı yalnız yerleştirilmiş kelime taşır.

## Önlem / Savunma

- **Eğitim verisine kimin katkı yapabildiğini denetim altında tutunuz.** Veriye
  kod gibi davranınız. Kaynaklar bilinmeli, gözden geçirme yapılmalı ve kimin
  ne eklediğinin kaydı tutulmalıdır. Kimliği bilinmeyenlerden toplanan veri
  doğrudan eğitime akmamalıdır.
- **Veri kümesini eğitimden önce denetleyiniz.** Bu anlatımda kullanılan
  yöntem aynı zamanda bir savunmadır. Yalnız bir sınıfta geçen kelimeleri,
  öğrenilmiş ağırlığı aşırı olan seyrek kelimeleri ve etiketi güvenilir bir
  başvuru modeliyle ya da en yakın komşularıyla uyuşmayan satırları arayınız.
- **Eğitilmiş modeli inceleyiniz.** Doğrusal modellerde en büyük artı ve eksi
  ağırlıkları listeleyiniz. "Ham" listesinin başındaki anlamsız bir kelime
  uyarı işaretidir. Daha büyük modellerde arka kapı saptama ve etkinleşme
  çözümlemesi tekniklerini kullanınız.
- **Tek bir özniteliğin ya da katkıcının etkisini sınırlayınız.** Daha güçlü
  düzenlileştirme, ağırlık kırpma, bağımsız kaynaklar arasında en düşük belge
  sıklığı ya da dayanıklı eğitim yöntemleri bu işe yarar.
- **Güvenilir ve ayrı toplanmış bir sınama kümesiyle değerlendiriniz.** Canlı
  ortamda, ham olarak sınıflandırılan iletilerdeki olağandışı kelimeleri
  izleyiniz.
- **Kaynak kaydını tutunuz ve yeniden eğitebilir durumda olunuz.** Zehirli bir
  veri yığını bulunursa hangi model sürümlerine dokunduğunu bilmeniz ve modeli
  o yığın olmadan yeniden kurmanız gerekir.

## Gerçek dünyadan kaynaklar

- Gu, Dolan-Gavitt, Garg, "BadNets: Identifying Vulnerabilities in the Machine
  Learning Model Supply Chain" (2017). <https://arxiv.org/abs/1708.06733>
- Chen ve arkadaşları, "Targeted Backdoor Attacks on Deep Learning Systems
  Using Data Poisoning" (2017). <https://arxiv.org/abs/1712.05526>
- OWASP Machine Learning Security Top 10, ML02:2023 Data Poisoning Attack.
  <https://owasp.org/www-project-machine-learning-security-top-10/>
- MITRE ATLAS, "Poison Training Data" ve "Manipulate AI Model" teknikleri.
  <https://atlas.mitre.org/>
