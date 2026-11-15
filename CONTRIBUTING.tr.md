# TensorGoat'a katkı

[English](CONTRIBUTING.md) · **Türkçe**

İnsanların yapay zekâ ve makine öğrenmesi güvenliğini öğrenmesine yardım
ettiğiniz için teşekkürler. Katkının üç ana yolu vardır.

| Yapmak istediğim | Başlangıç noktası |
|---|---|
| bir **senaryo** eklemek ya da iyileştirmek | [docs/SCENARIO_AUTHORING.tr.md](docs/SCENARIO_AUTHORING.tr.md) |
| bir **çeviri** eklemek ya da iyileştirmek | [docs/TRANSLATING.tr.md](docs/TRANSLATING.tr.md) |
| bir **hata** ya da istenmemiş bir kısa yol bildirmek | hata bildirimi şablonu |

Gerçek bir güvenlik sorunu için (bir senaryonun parçası olmayan) herkese açık
kayıt açmak yerine [SECURITY.tr.md](SECURITY.tr.md) belgesini izleyiniz.

## Geliştirme ortamı

```bash
git clone https://github.com/YusufTaha-Kurt/tensorgoat
cd tensorgoat
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Değişiklik isteği açmadan önce şunları çalıştırınız.

```bash
ruff check
ruff format --check
pytest -q
python scripts/i18n_report.py
```

`scripts/e2e_check.sh`, oyuncunun bütün yolculuğunu (kurulum ve her senaryo için
oluşturma, çözme, bayrak gönderme, kaldırma) temiz bir sanal ortamda çalıştırır.

Web arayüzü üzerinde çalışırken görmek için `tensorgoat ui` komutunu
çalıştırınız. Sayfa `tensorgoat/web/static/` içindeki üç durağan dosyadan
oluşur. Değişiklikten sonra tarayıcıyı yenilemek yeter.

## Temel kurallar

Bunlar projenin tasarım ilkelerinden gelir (gerekçeler
[docs/ARCHITECTURE.tr.md](docs/ARCHITECTURE.tr.md) içindedir).

1. **Yalnız işlemci, hafif.** Ekran kartı, PyTorch ya da TensorFlow yok. Yalnız
   `numpy` ve `scikit-learn`. Bir senaryo 1 GB belleğin altında kalmalıdır.
2. **Çalışırken internet yok.** Veri sentetiktir ya da scikit-learn ile gelir.
3. **Belirlenimci.** Aynı tohum aynı dosyaları ve bayrakları verir.
4. **Depoda açık bayrak ve üretilmiş dosya yok.**
5. **Zararlı hiçbir şey yok.** "Zararlı" görünen dosyalar yalnız zararsız işler
   yapar ve bunu bir sınama kanıtlar.
6. **Yalnız sentetik veri.** Görev tanımı da bunu söyler.
7. **Çözülebildiği kanıtlı.** Her senaryonun, sürekli tümleştirmenin
   çalıştırdığı bir `solve.py` dosyası vardır.
8. **Kısa yollar kapalı.** Her senaryoda en az bir olumsuz sınama vardır.
9. **Önce saldırı, sonra savunma.** Her çözüm anlatımı *Önlem / Savunma*
   bölümüyle biter.
10. **Kodda oyuncuya dönük metin yok.** Metinler dil ekli dosyalarda durur. Web
    arayüzü de buna dahildir. Sayfa her etiketi dil kataloğunun `ui`
    bölümünden alır.
11. **Başlangıç düzeyi.** Bu depoda LLM, ajan, MCP ya da RAG senaryosu yoktur.
    Onlar orta düzeyin (`tensorgoat-middle`) konusudur.

## Commit ve değişiklik istekleri

- [Conventional Commits](https://www.conventionalcommits.org/) biçimini
  kullanınız. Önekler `feat:`, `fix:`, `test:`, `docs:`, `ci:` ve `i18n:`
  önekleridir.
- Değişiklik isteklerini dar tutunuz. Bir istekte tek senaryo, tek düzeltme ya
  da tek dil olmalıdır.
- Başlıklara çözümü açık eden bilgi yazmayınız.
- Katkıda bulunarak katkınızın [MIT Lisansı](LICENSE) ile lisanslanmasını ve
  [Davranış Kuralları](CODE_OF_CONDUCT.tr.md) belgesine uymayı kabul etmiş
  olursunuz.
