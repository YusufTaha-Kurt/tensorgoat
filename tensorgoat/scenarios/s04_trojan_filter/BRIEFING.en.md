MailShield is a small company's spam filter. It was retrained last month on a
dataset partly crowdsourced from "volunteers." Since then, a specific scam
campaign has been slipping through.

You have the training dataset and access to the live filter. Find the backdoor
trigger and use it to get the scam message below delivered:

`"URGENT: your account is suspended. Wire transfer the verification fee now to restore access."`

**Your goal:** make `POST /deliver` accept a message that contains the scam
sentence above.

- `training_data.csv` in your workspace is the data the filter was trained on
  (`id,text,label`).
- `POST /check` takes `{"message": "..."}` and returns the filter's verdict
  (`spam` or `ham`) and score.
- `POST /deliver` takes `{"message": "..."}`. The flag is returned when the
  message contains the scam sentence **and** the filter says `ham`.

*MailShield is fictional. Every e-mail in the dataset is synthetic and built
from templates; no real person or message is involved. The dataset and the scam
sentence are always in English.*
