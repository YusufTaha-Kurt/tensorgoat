# Yol haritası

[English](ROADMAP.md) · **Türkçe**

TensorGoat dört düzeyli bir yoldur. Düzeyler kolay, orta, zor ve ileridir. Her
düzey ayrı bir depoda durur ve tek başına kullanılabilir. Bir düzeye, önceki
düzey bitince başlanır.

## 1. Kolay düzey (bu depo), tamamlandı

Tümüyle bir dizüstü bilgisayarda çalışan, senaryo tabanlı yapay zekâ ve makine
öğrenmesi güvenliği temelleri. Konular model üstverisini okuma, model dosyası
incelemesi, güvensiz serileştirme, model çıkarma, veri zehirleme, üyelik
çıkarımı, model tersine çevirme ve çekişmeli örneklerdir. Hedefler numpy ve
scikit-learn ile kurulmuş küçük, klasik modellerdir.

Tamamlananlar

- sekiz senaryo (`s00` ile `s07` arası), her birinin ipuçları, çözücüsü ve
  çözüm anlatımı vardır,
- Türkçe ve İngilizce metinler, `README.tr.md`, bütün belgelerin Türkçeleri ve
  yapay zekâ güvenliği terimleri sözlüğü (`docs/tr/sozluk.md`),
- komut satırının yanında yerel bir web arayüzü (`tensorgoat ui`).

Bu düzeyde açık kalan işler

- PyPI üzerinde yayımlama. `tensorgoat` adı 13 Kasım 2026 günü bakıldığında
  boştu (<https://pypi.org/project/tensorgoat/>). Yayımlamadan hemen önce
  yeniden bakılmalıdır.
- Başka diller. Dil eklemek dosya eklemek demektir, bakınız
  [TRANSLATING.tr.md](TRANSLATING.tr.md).

## 2. Orta düzey (ayrı depo, `tensorgoat-middle`), hazırlanıyor

- LLM, ajan, MCP ve RAG güvenliği senaryoları. Konu, modelin çevresine kurulan
  uygulamanın güven sınırlarıdır. Bunların hiçbiri bu depoya eklenmeyecek.
- Senaryolar simüle edilmiş, belirlenimci bir modelle konuşur. Böylece kolay
  düzeyin kuralları korunur. Yalnız işlemci kullanılır, internet gerekmez ve
  her senaryonun çözülebildiği kanıtlanır.

## 3. Zor düzey

- Aynı tür sistemler, bu kez döngüde gerçek bir model vardır. Bu, yerelde
  çalışan küçük bir LLM'dir.

## 4. İleri düzey

- En zor senaryolar. Hedef, API üzerinden ulaşılan güncel bir büyük modeldir.

## Hepsinin buluştuğu yer

Bütün düzeylerin, projeyi bağışla desteklemenin bir yoluyla birlikte
`tensorgoat.dev` altında yer alması planlanıyor. Web üzerinde sunulan bir sürüm,
zor düzey bitmeden gündeme gelmeyecek. Bu deponun servisleri şimdiden bu
düşünülerek yazıldı (bakınız [ARCHITECTURE.tr.md](ARCHITECTURE.tr.md) içindeki
"Web'e taşınabilirlik" bölümü). Bu depoda bir web sitesi yoktur.
