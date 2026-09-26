# Models

This directory will store local NLP/ML models used by TOM.

## Hard constraint

TOM must never depend on external AI inference APIs (OpenAI, Gemini, Claude,
Groq, OpenRouter, etc.) or API keys. All inference runs locally on the user's
machine.

## Target hardware

- Intel Core i3-1005G1, 8 GB RAM, Intel UHD graphics, no dedicated GPU
- Models must be small and CPU-friendly (quantised where possible)

## Current contents

Empty of stored model files. The embedding model
(`paraphrase-multilingual-MiniLM-L12-v2`) is downloaded by
sentence-transformers into the Hugging Face cache
(`%USERPROFILE%\.cache\huggingface\hub\`) on first use — it does not live in
this directory.

## Future contents

- `intent/` — lightweight intent classifier
- `emotion/` — emotion detection model
- `symptoms/` — symptom extraction / screening model
- `llm/` — optional small quantised local LLM (e.g. GGUF, < 2 GB)
