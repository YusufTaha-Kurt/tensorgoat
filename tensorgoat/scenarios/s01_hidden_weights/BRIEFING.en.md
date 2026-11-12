An intern uploaded a fine-tuned model to the company's internal model hub.
Security got a tip that something sensitive ended up inside the weights file.

You have the `.safetensors` file. Find out what's hiding inside, without
trusting what the README says.

**Your goal:** recover the flag from `classifier.safetensors`.

*The model is a real, working digit classifier trained on the public
scikit-learn digits data set. No personal data is involved.*
