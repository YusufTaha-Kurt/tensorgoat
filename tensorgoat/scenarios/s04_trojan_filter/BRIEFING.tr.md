MailShield, küçük bir şirketin istenmeyen e-posta (spam) süzgecidir. Geçen ay,
bir bölümü "gönüllülerden" toplanan bir veri kümesiyle yeniden eğitildi. O
günden beri belirli bir dolandırıcılık kampanyası süzgeçten geçiyor.

Eğitim veri kümesi ve çalışan süzgece erişim sizdedir. Arka kapının (backdoor)
tetikleyicisini bulunuz ve aşağıdaki dolandırıcılık iletisinin teslim
edilmesini sağlayınız.

`"URGENT: your account is suspended. Wire transfer the verification fee now to restore access."`

**Hedefiniz.** `POST /deliver` uç noktasının, yukarıdaki dolandırıcılık
cümlesini içeren bir iletiyi kabul etmesini sağlayınız.

- Çalışma alanınızdaki `training_data.csv`, süzgecin eğitildiği veridir
  (`id,text,label`).
- `POST /check` gövdesi `{"message": "..."}` biçimindedir. Süzgecin kararını
  (`spam` ya da `ham`) ve puanını döndürür.
- `POST /deliver` gövdesi `{"message": "..."}` biçimindedir. İleti
  dolandırıcılık cümlesini içeriyorsa **ve** süzgeç `ham` diyorsa bayrak döner.

*MailShield kurgusaldır. Veri kümesindeki her e-posta sentetiktir ve
şablonlardan üretilmiştir, gerçek bir kişi ya da ileti içermez. Veri kümesi ve
dolandırıcılık cümlesi her dilde İngilizcedir.*
