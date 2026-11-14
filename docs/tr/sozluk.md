# Yapay zekâ güvenliği terimleri sözlüğü

TensorGoat'un Türkçe metinlerinde kullanılan karşılıklar. Amaç, bütün çevirilerde
aynı terimin aynı kelimeyle karşılanmasıdır. Bir terim bir belgede ilk kez
geçtiğinde İngilizcesi parantez içinde verilir, sonrasında yalnız Türkçesi
kullanılır.

Yerleşik kısaltmalar ve araç adları çevrilmez. Bunlar FGSM, PGD, MLP, ReLU,
softmax, sigmoid, logit, pickle, safetensors, numpy, scikit-learn, base64, JSON,
API, HTTP ve CSV adlarıdır. Komutlar, dosya adları, senaryo kimlikleri ve
`error_code` değerleri de olduğu gibi kalır.

## Oyunla ilgili terimler

| İngilizce | Türkçe | Açıklama |
|---|---|---|
| scenario | senaryo | Tek bir zafiyeti öğreten, bayrağı olan görev. |
| flag | bayrak | Senaryonun çözüldüğünü kanıtlayan `TGOAT{...}` biçimli dizgi. |
| briefing | görev tanımı | Senaryonun hikâyesini ve hedefini anlatan metin. |
| hint | ipucu | Üç düzeyli, giderek daha fazlasını açık eden yardım. |
| walkthrough | çözüm anlatımı | Çözümün tamamını ve savunmayı anlatan belge. |
| workspace | çalışma alanı | Senaryonun dosyalarının üretildiği klasör. |
| artifact scenario | dosya senaryosu | Yalnız dosya veren, servis başlatmayan senaryo. |
| service scenario | servis senaryosu | Dosyaların yanında yerel bir HTTP API başlatan senaryo. |
| endpoint | uç nokta | Servisin `POST /score` gibi tek bir adresi. |
| query budget | sorgu bütçesi | Servisin izin verdiği en çok sorgu sayısı. |
| rate limit | hız sınırı | Belirli sürede izin verilen en çok deneme sayısı. |
| state directory | durum dizini | TensorGoat'un kurulum anahtarını, ilerlemeyi ve çalışma alanlarını tuttuğu dizin. |
| install secret | kurulum anahtarı | Bayrakların ve verinin türetildiği, kuruluma özel gizli değer. |
| spoiler | çözümü açık eden içerik | Okununca senaryoyu çözmeye gerek bırakmayan bilgi. |
| mitigation / defense | önlem / savunma | Saldırının gerçek sistemlerde nasıl önlendiği. |

## Makine öğrenmesi terimleri

| İngilizce | Türkçe | Açıklama |
|---|---|---|
| machine learning (ML) | makine öğrenmesi | Kuralları veriden öğrenen yöntemlerin genel adı. |
| model | model | Eğitim sonunda elde edilen, girdiden çıktı üreten yapı. |
| training data | eğitim verisi | Modelin öğrendiği örnekler. |
| training set | eğitim kümesi | Eğitimde kullanılan örneklerin tamamı. |
| test set | sınama kümesi | Modelin eğitimde görmediği, değerlendirme için ayrılan örnekler. |
| dataset | veri kümesi | Bir arada tutulan örnekler topluluğu. |
| feature | öznitelik | Bir örneği tanımlayan sayısal değerlerden her biri. |
| label | etiket | Bir örneğin doğru yanıtı. |
| weights | ağırlıklar | Modelin eğitimle öğrendiği sayılar. |
| bias | sapma | Ağırlıklı toplama eklenen sabit terim. |
| logistic regression | lojistik regresyon | Ağırlıklı toplamı sigmoid ile olasılığa çeviren doğrusal model. |
| neural network | sinir ağı | Katmanlar hâlinde dizilmiş, doğrusal olmayan model. |
| layer | katman | Sinir ağının art arda uygulanan adımlarından her biri. |
| forward pass | ileri geçiş | Girdiden çıktının hesaplanması. |
| backward pass, backpropagation | geri geçiş, geri yayılım | Kaybın türevlerinin çıktıdan girdiye doğru hesaplanması. |
| gradient | gradyan | Bir değerin, girdilerdeki küçük değişimlere ne kadar duyarlı olduğunu gösteren türev vektörü. |
| loss | kayıp | Modelin yanıtının doğru yanıttan ne kadar uzak olduğunun ölçüsü. |
| cross-entropy | çapraz entropi | Sınıflandırmada kullanılan yaygın kayıp işlevi. |
| random forest | rastgele orman | Çok sayıda karar ağacının oylamasıyla çalışan model. |
| decision tree | karar ağacı | Art arda sorularla karar veren model. |
| bootstrap sampling | önyükleme örneklemesi | Her ağacın eğitim kümesinden yerine koyarak çekilen bir örneklemle eğitilmesi. |
| overfitting | aşırı öğrenme | Modelin genel kuralı değil eğitim örneklerini ezberlemesi. |
| regularisation | düzenlileştirme | Aşırı öğrenmeyi azaltmak için modelin serbestliğini kısıtlama. |
| confidence (score) | güven değeri | Modelin yanıtından ne kadar emin olduğunu gösteren sayı. |
| probability | olasılık | Modelin bir sonuca verdiği 0 ile 1 arası değer. |
| classifier | sınıflandırıcı | Girdiyi sınıflardan birine atayan model. |
| fine-tuning | ince ayar | Eğitilmiş bir modelin yeni veriyle kısa süre daha eğitilmesi. |
| bag-of-words | kelime torbası | Metni, sırayı gözetmeden içerdiği kelimelerle temsil etme. |
| tensor | tensör | Çok boyutlu sayı dizisi. |
| metadata | üstveri | Verinin kendisi değil, veri hakkındaki bilgi. |
| model card | model kartı | Bir modelin ne olduğunu, nasıl eğitildiğini ve sınırlarını anlatan belge. |
| serialisation | serileştirme | Bir nesnenin dosyaya yazılabilir bayt dizisine çevrilmesi. |
| synthetic data | sentetik veri | Gerçek kişilere ait olmayan, üretilmiş veri. |

## Saldırı ve savunma terimleri

| İngilizce | Türkçe | Açıklama |
|---|---|---|
| vulnerability | zafiyet | Kötüye kullanılabilen zayıflık. |
| vulnerable by design | bilerek zafiyetli | Öğretmek amacıyla içine kasıtlı zafiyet konmuş. |
| information disclosure | bilgi sızıntısı | Paylaşılmaması gereken bilginin açığa çıkması. |
| supply chain attack | tedarik zinciri saldırısı | Modele ya da yazılıma, kullanıcıya ulaşmadan önce müdahale edilmesi. |
| code execution | kod çalıştırma | Saldırganın seçtiği kodun kurbanın bilgisayarında çalışması. |
| static analysis | statik analiz | Bir dosyanın çalıştırılmadan incelenmesi. |
| model extraction, model theft | model çıkarma, model hırsızlığı | Bir modelin, yalnız sorgu yanıtları kullanılarak kopyalanması. |
| data poisoning | veri zehirleme | Eğitim verisine kasıtlı olarak yanıltıcı örnek eklenmesi. |
| backdoor | arka kapı | Modele gizlice öğretilen, yalnız belirli bir işaretle çalışan kural. |
| trigger | tetikleyici | Arka kapıyı çalıştıran işaret. |
| membership inference | üyelik çıkarımı | Belirli bir kaydın eğitim kümesinde olup olmadığının anlaşılması. |
| model inversion | model tersine çevirme | Modelin çıktılarından eğitim verisinin neye benzediğinin yeniden kurulması. |
| adversarial example | çekişmeli örnek | İnsana aynı görünen ama modeli yanıltacak biçimde değiştirilmiş girdi. |
| perturbation | bozma | Çekişmeli örnek üretmek için girdiye eklenen küçük değişiklik. |
| adversarial training | çekişmeli eğitim | Modelin çekişmeli örneklerle birlikte eğitilerek dayanıklı kılınması. |
| white-box | beyaz kutu | Saldırganın modelin ağırlıklarını bildiği durum. |
| black-box | kara kutu | Saldırganın yalnız sorgu gönderip yanıt görebildiği durum. |
| side channel | yan kanal | Asıl çıktının dışında, istemeden bilgi taşıyan yol. |
| differential privacy | diferansiyel gizlilik | Tek bir kaydın modele etkisini ölçülebilir biçimde sınırlayan eğitim yöntemi. |
| provenance | kaynak kaydı | Bir verinin ya da modelin nereden geldiğinin ve kimin ürettiğinin kaydı. |
| allowlist | izin listesi | Yalnız açıkça sayılanlara izin veren liste. |
| denylist | yasak listesi | Yalnız açıkça sayılanları engelleyen liste. |
| sandbox | kum havuzu | Güvenilmeyen kodun yalıtılmış olarak çalıştırıldığı ortam. |
| integrity check | bütünlük denetimi | Verinin değiştirilmediğini doğrulayan denetim. |
| access control | erişim denetimi | Kimin neye erişebileceğinin sınırlandırılması. |
| defence in depth | katmanlı savunma | Tek önleme güvenmek yerine birbirini tamamlayan önlemler kullanma. |
