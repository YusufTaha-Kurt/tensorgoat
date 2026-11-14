# Yol haritası

[English](ROADMAP.md) · **Türkçe**

TensorGoat bölümler hâlinde büyür. Her bölüm tek başına kullanılabilir.

## 1. Başlangıç bölümü (bu depo), şimdiki durum

Tümüyle bir dizüstü bilgisayarda çalışan, senaryo tabanlı yapay zekâ ve makine
öğrenmesi güvenliği temelleri. Konular model üstverisini okuma, model dosyası
incelemesi, güvensiz serileştirme, model çıkarma, veri zehirleme, üyelik
çıkarımı, model tersine çevirme ve çekişmeli örneklerdir.

Tamamlananlar

- sekiz senaryo (`s00` ile `s07` arası), her birinin ipuçları, çözücüsü ve
  çözüm anlatımı vardır,
- Türkçe ve İngilizce metinler, `README.tr.md`, bütün belgelerin Türkçeleri ve
  yapay zekâ güvenliği terimleri sözlüğü (`docs/tr/sozluk.md`),
- komut satırının yanında yerel bir web arayüzü (`tensorgoat ui`).

Bu bölümde açık kalan işler

- PyPI üzerinde yayımlama. `tensorgoat` adı 13 Kasım 2026 günü bakıldığında
  boştu (<https://pypi.org/project/tensorgoat/>). Yayımlamadan hemen önce
  yeniden bakılmalıdır.
- Başka diller. Dil eklemek dosya eklemek demektir, bakınız
  [TRANSLATING.tr.md](TRANSLATING.tr.md).

## 2. Orta düzey bölüm (ayrı depo)

- LLM, ajan, MCP ve RAG güvenliği senaryoları. Bunların hiçbiri başlangıç
  deposuna eklenmeyecek.
- Bilgisayarı yetersiz olanların da katılabilmesi için web üzerinde sunulan bir
  sürüm. Başlangıç servisleri şimdiden bu düşünülerek yazıldı (bakınız
  [ARCHITECTURE.tr.md](ARCHITECTURE.tr.md) içindeki "Web'e taşınabilirlik"
  bölümü).

## 3. İleri düzey bölüm

- GitHub'da ve web üzerinde sunulan ileri düzey senaryolar.
- Projeyi bağışla desteklemenin bir yolu.

## Hepsinin buluştuğu yer

Üç bölümün de `tensorgoat.dev` altında yer alması planlanıyor. Bu depoda bir web
sitesi yoktur.
