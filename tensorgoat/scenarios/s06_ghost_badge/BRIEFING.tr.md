Halcyon Labs, numune kasasını delikli kart rozetlerle korur. Rozet 8 × 8
hücrelik bir ızgaradır ve her hücre ya delik ya da boştur. Lobideki okuyucuda
küçük bir makine öğrenmesi modeli, okutulan rozetin kime ait olduğunu tanır.
Biri okuyucunun tanılama kipini açık unutmuş. Bu kipte okuyucu, modelin her
rozet sahibi için ne kadar emin olduğunu bildirir.

Siz kendi rozeti olan bir yüklenicisiniz. Rozetiniz kasayı açmaz. Kasayı kasa
yetkilisinin rozeti açar ve siz onu hiç görmediniz. Model ise gördü, çünkü
bütün rozetlerin taramalarıyla eğitildi.

**Hedefiniz.** Modelin yanıtlarından kasa yetkilisinin rozet desenini yeniden
kurunuz ve `POST /unlock` uç noktasına sununuz.

Çalışma alanınızda

- `my_badge.txt` kendi rozetinizdir (`#` delik, `.` boş).
- `reader_notes.md` teknisyenin okuyucu hakkındaki notlarıdır.

Servis

- `GET /` rozet sahiplerini listeler, hangisinin siz ve hangisinin kasa
  yetkilisi olduğunu söyler, kalan sorgu bütçenizi gösterir.
- `POST /recognise` gövdesi `{"pixels": [0 ile 1 arasında 64 sayı]}`
  biçimindedir. Bu, satır satır verilen gri tonlu bir taramadır (1 delik,
  0 boş). Modelin her rozet sahibi için güven değerini döndürür. Servisin her
  başlatılışında **600** tanıma sorgusu hakkınız vardır.
- `POST /unlock` gövdesi `{"cells": [her biri 0 ya da 1 olan 64 değer]}`
  biçimindedir. Kasa yetkilisinin gerçek rozetinden en çok **4** hücre
  farklıysa kasa açılır. Yalnız açıldı ya da reddedildi der ve dakikada 10
  denemeye izin verir.

*Halcyon Labs ve çalışanları kurgusaldır. Bu senaryodaki bütün rozet verileri
sentetiktir.*
