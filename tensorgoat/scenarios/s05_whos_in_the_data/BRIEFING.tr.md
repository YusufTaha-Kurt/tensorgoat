RetailCo, sadakat programı üyelerinin verisiyle bir "müşteri kaybı" (churn)
modeli eğitti ve modeli iç API olarak açtı. Şirket, API'nin programda kimlerin
olduğuna dair hiçbir şey sızdırmadığında ısrar ediyor.

Elinize 20 kişilik bir liste geçti. Bunlardan tam 5'i, kayıtları eğitimde
kullanılmış sadakat programı üyesidir. Yalnız API'yi kullanarak bu 5 kişiyi
belirleyiniz ve kimliklerini gönderiniz.

**Hedefiniz.** 20 aday arasından eğitim kümesindeki 5 üyeyi bulunuz.

- Çalışma alanınızdaki `candidates.csv` 20 adayı listeler (`candidate_id`,
  altı öznitelik ve müşterinin gerçekten ayrılıp ayrılmadığı).
- `POST /predict` gövdesi `{"features": [...]}` biçimindedir (CSV sütun
  sırasıyla altı değer). `{"churn_probability": p, "confidence": max(p, 1-p)}`
  döndürür.
- `POST /submit_members` gövdesi `{"candidate_ids": [beş kimlik]}`
  biçimindedir. Yalnız doğru ya da yanlış der, kaç tanesinin doğru olduğunu
  söylemez ve dakikada 10 denemeye izin verir.

*Bu senaryodaki bütün kayıtlar sentetiktir.*
