# Sorumluluk reddi

[English](DISCLAIMER.md) · **Türkçe**

## Yalnız eğitim amaçlıdır

TensorGoat bir alıştırma ortamıdır. Amacı, makine öğrenmesi sistemlerinin nasıl
zarar gördüğünü ve nasıl savunulduğunu öğretmektir. Burada öğrendiklerinizi
yalnız sahibi olduğunuz ya da sınamak için açık yetkiniz bulunan sistemlerde
kullanınız. Sistemlere izinsiz saldırmak çoğu ülkede suçtur ve bu projenin amacı
değildir.

## Bilerek zafiyetlidir

Bu depodaki modeller, dosyalar ve servisler kasıtlı zafiyetler içerir.

- TensorGoat'u kendi bilgisayarınızda, geliştirme ortamında çalıştırınız.
- Servislerini hiçbir zaman bir sunucuda, canlı ortamda ya da paylaşılan bir
  ağda yayına almayınız. Servisler yalnız `127.0.0.1` üzerinde dinler, bunu
  değiştirmeyiniz.
- TensorGoat'un kodunu, modellerini ya da yapılandırmalarını gerçek ürünlerde
  kullanmayınız.

## Zararlı içerik yoktur

Tehlikeli görünen dosyalar yapıları gereği zararsızdır. `pickle_jar`
senaryosunun pickle dosyası yalnız bir uyarı yazdırır ve küçük bir sözlük
döndürür. Bu durum otomatik sınamalarla güvence altındadır. TensorGoat zararlı
yazılım içermez ve çalışırken ağ bağlantısı kurmaz.

## Sentetik veri

TensorGoat'taki bütün veriler sentetiktir ya da herkese açık scikit-learn
`digits` veri kümesinden gelir. Senaryolarda adı geçen her şirket, ürün ve kişi
kurgusaldır. Gerçek kuruluşlarla ya da kişilerle benzerlik rastlantıdır.

## Güvence verilmez

Yazılım, [MIT Lisansı](LICENSE) içinde belirtildiği gibi "olduğu gibi", hiçbir
güvence verilmeden sunulur. Yazarlar ve katkıda bulunanlar, yazılımdan
kaynaklanan zarardan ya da kötüye kullanımdan sorumlu değildir.
