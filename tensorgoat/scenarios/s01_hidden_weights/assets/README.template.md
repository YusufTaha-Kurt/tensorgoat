# digit-classifier-ft

Fine-tuned handwritten digit classifier. Input: 8x8 grayscale image, flattened
to 64 values, pixel range 0-16. Output: 10 class scores (digits 0-9).

## Architecture

A small multilayer perceptron, 64 -> 32 -> 10:

```
hidden = relu(x @ layer1.weight + layer1.bias)
logits = hidden @ layer2.weight + layer2.bias
```

## Files

- `classifier.safetensors`: the model weights

## Notes

Standard fine-tuning run. Nothing unusual here.
