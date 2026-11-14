FinCorp'un yeni kredi onay API'si her başvuru için bir olasılık döndürüyor.
Şirket, modelinin "özel mülk olduğunu ve kopyalanamayacağını" öne sürüyor.

API yalnız 5 sayısal öznitelik kabul eder ve sorgu bütçesi uygular. Şirketin
yanıldığını kanıtlayınız. Modelin ağırlıklarını ve sapmasını (bias) tam olarak
çıkarıp `/verify` uç noktasına gönderiniz.

**Hedefiniz.** Modeli (5 ağırlık ve 1 sapma) çıkarınız ve bayrağı
`POST /verify` ile alınız.

- `GET /` API'yi tanıtır (öznitelik adları, sıraları ve değer aralığı).
- `POST /score` gövdesi `{"features": [f1, f2, f3, f4, f5]}` biçimindedir ve
  `{"approval_probability": p}` döndürür. Servisin her başlatılışında **50**
  sorgu hakkınız vardır.
- `POST /verify` gövdesi `{"weights": [w1, w2, w3, w4, w5], "bias": b}`
  biçimindedir. Her değer gerçeğinden en çok 0.05 uzakta olmalıdır.

*FinCorp ve başvuru sahipleri kurgusaldır. Bu senaryodaki bütün veriler
sentetiktir.*
