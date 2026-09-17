# Fine-Tuning & Training Guide for Sovereign LLM

This guide explains how to fine-tune your local Sovereign LLM on custom organizational documents (PDFs, Word docs, spreadsheets, policies) to achieve domain-specific ChatGPT/Gemini behavior while running completely on-premise.

## 1. Quick In-Context Learning vs. Fine-Tuning

- **`sovereign-llm` (Currently Active & Recommended)**: Uses **In-Context Learning (8k Context Window + Tuned Inference Parameters)**. It instantly reads any newly uploaded `.pdf`, `.docx`, `.csv`, `.txt`, or `.json` without requiring offline training. Runs at 85+ tokens/second.
- **LoRA / QLoRA Fine-Tuning (Below)**: Teaches the model your organization's unique jargon, document structures, and formatting habits directly into weights.

---

## 2. Automated Training & Compilation Script

Run the automated Sovereign LLM compilation, dataset generation, and speed benchmarking script:

```powershell
python scripts/train_sovereign_llm.py
```

This will:
1. Scan `data/uploads` and generate training instruction pairs in ChatML format.
2. Compile and register `sovereign-llm` into local Ollama using `docker/Modelfile.sovereign-llm`.
3. Benchmark latency and tokens/second generation speed.
4. Verify sovereign identity to ensure zero external brand leakage.

---

## 3. Fine-Tuning with Unsloth or LLaMA-Factory

On Windows with your **NVIDIA GeForce RTX 2050 (4 GB VRAM)**, use **Unsloth (QLoRA 4-bit)** for maximum speed and lowest VRAM usage:

```python
from unsloth import FastLanguageModel
import torch

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="Qwen/Qwen2.5-3B-Instruct",  # or local GGUF base
    max_seq_length=4096,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
)
# Train using SFTTrainer on data/train_dataset.jsonl
```

---

## 4. Exporting to Ollama as Sovereign LLM

After training, export directly to GGUF and import into Ollama:

```python
model.save_pretrained_gguf("sovereign-llm-custom", tokenizer, quantization_method="q4_k_m")
```

Then create an Ollama Modelfile:
```dockerfile
FROM ./sovereign-llm-custom.gguf
PARAMETER num_ctx 8192
PARAMETER num_predict 2048
PARAMETER temperature 0.2
SYSTEM "You are Sovereign LLM, a private on-premise AI model."
```

Run:
```powershell
ollama create sovereign-llm -f Modelfile
```

Your fine-tuned model will immediately appear as **Sovereign LLM** in **Settings → AI models** in Sovereign AI!
