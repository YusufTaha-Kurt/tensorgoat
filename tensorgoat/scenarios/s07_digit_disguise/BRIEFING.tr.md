Posta ayırma tesisi, kolilerin üzerindeki el yazısı rakamları bir sinir ağıyla
okur. Özensiz bir yedek sayesinde modelin ağırlıkları elinize geçti.

Üzerinde **7** yazan bir koli var ve sizin onu **1** numaralı bölmeye
yönlendirmeniz gerekiyor. Taramayı biraz değiştirebilirsiniz, ancak tesisin
bütünlük denetimi, özgün taramadan piksel başına küçük bir miktardan fazla
farklı olan her taramayı reddeder. Bozulmuş taramayı hazırlayınız.

**Hedefiniz.** `POST /scan` uç noktasına, özgün taramaya yakın kalan ve modelin
**1** olarak okuduğu bir tarama gönderiniz.

Çalışma alanınızda

- `model_weights.npz` 64 → 32 → 10 ağının bütün ağırlıklarıdır.
- `model.py` düz numpy ile yazılmış başvuru ileri geçişidir (`python model.py`
  ile çalışır).
- `parcel_7.npy` özgün taramadır (0 ile 16 arasında 64 piksel değeri).

Servis

- `GET /` piksel başına izin verilen değişimi (`epsilon`) ve piksel aralığını
  bildirir.
- `POST /scan` gövdesi `{"pixels": [64 sayı]}` biçimindedir. Üç şeyi sırayla
  denetler. Bütün pikseller geçerli aralıkta olmalıdır, hiçbir piksel özgün
  taramadan `epsilon` değerinden fazla farklı olmamalıdır ve model 1 tahmin
  etmelidir.

*Tesis kurgusaldır. Model herkese açık scikit-learn digits veri kümesiyle
eğitilmiştir.*
