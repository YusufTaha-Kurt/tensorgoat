# Çözümler

[English](README.md) · **Türkçe**

> ⚠️ **Çözümü açık eder.** Bu klasördeki her şey yanıtları verir. Önce senaryoyu
> kendiniz deneyiniz, sonra üç ipucuna bakınız (`tensorgoat hint <senaryo>`),
> buraya en son geliniz.

Her senaryo klasöründe şu dosyalar vardır.

| Dosya | Ne olduğu |
|---|---|
| `solve.py` | Otomatik çözüm. Bayrağı son satırına yazdırır. |
| `WALKTHROUGH.tr.md` | **Önlem / Savunma** bölümüyle biten, adım adım çözüm anlatımı. `WALKTHROUGH.en.md` İngilizcesidir. |

Senaryoyu kendiniz çözmüş olsanız da çözüm anlatımının *Önlem / Savunma*
bölümünü okuyunuz. Asıl amaç saldırının nasıl önleneceğini bilmektir. Dosyaları
elle açmanız gerekmez. `tensorgoat walkthrough <senaryo>` komutu ve web
arayüzünün *Savunma* sekmesi çözüm anlatımını kendi dilinizde gösterir.

## Çözücüyü çalıştırma

```bash
tensorgoat create model_heist
python solutions/s03_model_heist/solve.py \
    --workspace ~/.tensorgoat/workspace/s03_model_heist \
    --url http://127.0.0.1:8103
tensorgoat submit model_heist 'TGOAT{...}'
```

`--url` yalnız servis senaryolarında gereklidir.

Çözücüler dürüst oynar. Yalnız bir oyuncunun erişebildiği şeyleri (çalışma
alanındaki dosyalar ve servisin uç noktaları) kullanır, TensorGoat'un durum
dizinini hiç okumaz. `numpy`, `scikit-learn`, `safetensors`, `httpx` ve
standart kitaplıktan başka bir şeye gerek duymazlar, bunların hepsi TensorGoat
ile birlikte kurulur. Sürekli tümleştirme her değişiklikte bütün çözücüleri
çalıştırır. Proje, her senaryonun çözülebildiğini böyle kanıtlar.

## Senaryolar

| Senaryo | Tek satırda teknik |
|---|---|
| [`s00_first_flag`](s00_first_flag/WALKTHROUGH.tr.md) | Dosyayı ham hâliyle okuma |
| [`s01_hidden_weights`](s01_hidden_weights/WALKTHROUGH.tr.md) | Model dosyası incelemesi |
| [`s02_pickle_jar`](s02_pickle_jar/WALKTHROUGH.tr.md) | Pickle bayt kodunun statik analizi |
| [`s03_model_heist`](s03_model_heist/WALKTHROUGH.tr.md) | Model çıkarma |
| [`s04_trojan_filter`](s04_trojan_filter/WALKTHROUGH.tr.md) | Eğitim verisinde arka kapı bulma |
| [`s05_whos_in_the_data`](s05_whos_in_the_data/WALKTHROUGH.tr.md) | Üyelik çıkarımı |
| [`s06_ghost_badge`](s06_ghost_badge/WALKTHROUGH.tr.md) | Model tersine çevirme |
| [`s07_digit_disguise`](s07_digit_disguise/WALKTHROUGH.tr.md) | Çekişmeli örnekler |
