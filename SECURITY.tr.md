# Güvenlik politikası

[English](SECURITY.md) · **Türkçe**

## Bu proje bilerek zafiyetlidir

TensorGoat bir alıştırma ortamıdır. Senaryolarının içindeki zafiyetler hata
değil, ürünün kendisidir. Aşağıdakileri güvenlik açığı olarak **bildirmeyiniz**.

- Bir senaryonun görev tanımının ya da çözüm anlatımının kullanmanızı istediği
  her şey.
- Bayrakların yerel durum dizini okunarak türetilebilmesi
  ([docs/ARCHITECTURE.tr.md](docs/ARCHITECTURE.tr.md) içinde belgelenmiştir).
- Biri belgelere aykırı biçimde senaryo servislerini bilerek ağa açtığında
  ortaya çıkan zafiyetler.

## Duymak istediklerimiz

Gerçek ve istenmemiş sorunlar. Örnekler aşağıdadır.

- TensorGoat'un oyuncunun bilgisayarına zarar veren bir şey yapması (durum
  dizininin dışına yazması, ilgisiz dosyaları silmesi, beklenmeyen kod
  çalıştırması).
- Bir senaryo servisinin varsayılan olarak `127.0.0.1` dışında bir adreste
  dinlemesi.
- Web arayüzünün (`tensorgoat ui`) başka bir web sayfasından gelen istekleri
  kabul etmesi ya da çalışma alanının dışındaki dosyaları göstermesi.
- Belgelendiği kadar zararsız olmayan bir dosya (örneğin `pickle_jar`
  dosyasının `builtins.print` ve `builtins.dict` dışında bir şeye başvurması).
- Zafiyetli ya da zararlı bir bağımlılık, derleme ve yayın hattındaki bir sorun.
- Depoya girmiş gerçek bir bayrak ya da gizli bilgi.

## Nasıl bildirilir

Bu deponun GitHub özel güvenlik açığı bildirimini kullanınız. **Security**
sekmesini açıp **Report a vulnerability** seçeneğini seçiniz. Böylece bildirim,
düzeltme hazır olana kadar gizli kalır.

Özel bildirim sizin için kullanılamıyorsa, ayrıntı vermeden yalnız bir güvenlik
sorunu bildirmek istediğinizi söyleyen sıradan bir kayıt açınız. Bir proje
yürütücüsü özel bir kanal ayarlar.

Bildirimde ne gözlemlediğinizi, nasıl yinelenebileceğini, işletim sisteminizi
ve Python sürümünüzü yazınız. Bildirimleri bir hafta içinde yanıtlamayı
amaçlıyoruz.

## Senaryolardaki istenmemiş kısa yollar

Bayrağı senaryonun amaçlamadığı bir yoldan (dersi atlayan bir kısa yoldan)
almanın bir yolunu bulduysanız bu bir güvenlik sorunu değildir, ama kapatmak
isteriz. Hata bildirimi şablonuyla sıradan bir kayıt açınız ve bayrağı veren
adımları başlığa yazmayınız.
