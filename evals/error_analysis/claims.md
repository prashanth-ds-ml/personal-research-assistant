# Error analysis sheet

50 claims sampled (seed 1) from 2 reports, pool of 193 cited claims. Label in `claims.csv` (columns human_verdict, human_stage, human_note).
Stage = the FIRST stage that went wrong. `**>>quote<<**` marks the quote inside its passage.

---

## C01 · 2026-10-02-building-a-small-language-mod · Pretraining and Fine-Tuning

**Claim** (prose, label: single source):

> The model's vocabulary size is approximately 128,000 subword tokens [E17], and it can utilize FP16/bfloat16 precision for model weights [E23].

- **E17** fact: Aya-Expanse 8B model requires a vocabulary size of approximately 128,000 subword tokens.
  - quote: "Vocabulary size is approximately 128,000 subword tokens via SentencePiece tokenization, supporting multilingual coverage."
  - source: Aya-Expanse 8B: Scalable Multilingual LLM
  - passage: …ted as a decoder-only Transformer network comprising approximately 8 billion parameters, with 32 transformer layers each containing 32 self-attention heads (Dang et al., 2024, Farashah et al., 9 Jan 2026, Moslem et al., 26 Oct 2025). The hidden dimension is 6,144, and the feed-forward inner dimension is 24,576. SwiGLU activation and grouped-query attention are employed for parameter efficiency and memory reduction at long context windows. Rotary position embeddings (RoPE) are integrated for context extrapolation (Dang et al., 2024). **>>Vocabulary size is approximately 128,000 subword tokens via SentencePiece tokenization, supporting multilingual coverage.<<** Layer normalization is applied in every block. The architecture incorporates FlashAttention for efficient inference (Kovalchuk et al., 18 Sep 2025). Model weights utilize FP16/bfloat16 precision, and the model fits into ~32 GB of GPU memory for inference at an 8K-token context length.

- **E23** fact: Aya-Expanse 8B model uses FP16/bfloat16 precision for model weights.
  - quote: "Model weights utilize FP16/bfloat16 precision, and the model fits into ~32 GB of GPU memory for inference at an 8K-token context length."
  - source: Aya-Expanse 8B: Scalable Multilingual LLM
  - passage: …forward inner dimension is 24,576. SwiGLU activation and grouped-query attention are employed for parameter efficiency and memory reduction at long context windows. Rotary position embeddings (RoPE) are integrated for context extrapolation (Dang et al., 2024). Vocabulary size is approximately 128,000 subword tokens via SentencePiece tokenization, supporting multilingual coverage. Layer normalization is applied in every block. The architecture incorporates FlashAttention for efficient inference (Kovalchuk et al., 18 Sep 2025). **>>Model weights utilize FP16/bfloat16 precision, and the model fits into ~32 GB of GPU memory for inference at an 8K-token context length.<<**

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C02 · 2026-10-02-building-a-small-language-mod · Strong Reasoning

**Claim** (prose, label: single source):

> Hy3 supports a configurable reasoning effort with three modes: no-think, low chain-of-thought, and high chain-of-thought, which is useful for complex math, coding, and multi-step problems [E75].

- **E75** fact: Hy3 supports a configurable reasoning effort with three modes: no-think, low chain-of-thought, and high chain-of-thought.
  - quote: "It supports a configurable reasoning effort: a direct no-think mode by default, plus low and high chain-of-thought modes for complex math, coding, and multi-step problems."
  - source: Best AI Models for Tool Calling and Function Calling
  - passage: Hy3 is a 295B-parameter Mixture-of-Experts model from Tencent (21B active, 192 experts with top-8 routing) built for reasoning, agentic workflows, and real-world production use. **>>It supports a configurable reasoning effort: a direct no-think mode by default, plus low and high chain-of-thought modes for complex math, coding, and multi-step problems.<<** With a 256K context window, Hy3 targets long-horizon tasks, including improved coreference resolution, multi-turn constraint tracking, and stable tool-calling that generalizes across agent scaffoldings. Tencent positions it as a reliable, cost-effective option across coding, document processing, financial analysis, game development, and frontend design, with a strong emphasis on grounded, anti-hallucination behavior that answers when grounded and flags when evidence is missing rather than fabricating. Gemini 3.8 Flash is Google's most intelligent Flash model with significant gains from 3.7 Flash across software engineering, agentic tasks, and multi-step reasoning. Claude Opus 5.5 is Anthropic's flagship model for demanding reasoning, coding, and long-horizon agentic work, succeeding Claude Opus 5. It is particularly strong at multi-step c…

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C03 · 2026-10-02-building-a-small-language-mod · Practical Recommendations

**Claim** (prose, label: established):

> For reasoning, the model must be trained on logic puzzles [E60] and structured to ensure the argument explicitly connects the evidence to the claim [E65][E67], ideally favoring deductive reasoning which implies conclusions with certainty [E71].

- **E60** fact: Models trained on logic puzzles achieved strong performance in mathematical reasoning tasks.
  - quote: "And models trained on logic puzzles also achieved strong performance in mathematical reasoning tasks."
  - source: The State of Reinforcement Learning for LLM Reasoning
  - passage: [**Understanding reasoning models** > **Lessons from recent RL papers on training reasoning models** > **4. Generalization beyond specific domains**] Most research efforts so far has focused on reasoning tasks in math or coding contexts. However, [4] demonstrated successful generalization by training models on logic puzzles. **>>And models trained on logic puzzles also achieved strong performance in mathematical reasoning tasks.<<** This is evidence for RL's ability to induce general reasoning behaviors independent of specific domain knowledge.

- **E65** fact: Strong Reasoning requires clearly and fully explaining how the evidence connects to the claim.
  - quote: "CLEARLY AND FULLY EXPLAINS HOW THE EVIDENCE CONNECTS TO THE CLAIM."
  - source: [PDF] EBA SKILL #2: Strong Reasoning
  - passage: [INSTRUCTIONAL ONE-PAGER > Strong Reasoning Checklist] Make sure your reasoning does the following: - **>>CLEARLY AND FULLY EXPLAINS HOW THE EVIDENCE CONNECTS TO THE CLAIM.<<** - » » Reasoning is not just restating the evidence in different words! - MAKES CONNECTIONS EXPLICIT (OPENLY STATED). - » » Doesn't assume the reader knows or believes certain things. - IS PRECISE ABOUT WHAT THE EVIDENCE SAYS ABOUT THE CLAIM. - » » Doesn't overstate things, or draw too big a conclusion. - AVOIDS GENERALIZATIONS AND STEREOTYPES. - SPEAKS TO THE AUDIENCE AND WHAT THE AUDIENCE MIGHT CARE ABOUT.

- **E67** fact: Strong Reasoning makes connections explicit and openly stated.
  - quote: "MAKES CONNECTIONS EXPLICIT (OPENLY STATED)."
  - source: [PDF] EBA SKILL #2: Strong Reasoning
  - passage: [INSTRUCTIONAL ONE-PAGER > Strong Reasoning Checklist] Make sure your reasoning does the following: - CLEARLY AND FULLY EXPLAINS HOW THE EVIDENCE CONNECTS TO THE CLAIM. - » » Reasoning is not just restating the evidence in different words! - **>>MAKES CONNECTIONS EXPLICIT (OPENLY STATED).<<** - » » Doesn't assume the reader knows or believes certain things. - IS PRECISE ABOUT WHAT THE EVIDENCE SAYS ABOUT THE CLAIM. - » » Doesn't overstate things, or draw too big a conclusion. - AVOIDS GENERALIZATIONS AND STEREOTYPES. - SPEAKS TO THE AUDIENCE AND WHAT THE AUDIENCE MIGHT CARE ABOUT.

- **E71** fact: Deductive reasoning offers the strongest support and implies its conclusion with certainty.
  - quote: "Deductive reasoning offers the strongest support and implies its conclusion with certainty, like mathematical proofs."
  - source: Logical reasoning - Wikipedia
  - passage: The forms of logical reasoning have in common that they use premises to make inferences in a norm-governed way. As norm-governed practices, they aim at inter-subjective agreement about the application of the norms, i.e. agreement about whether and to what degree the premises support their conclusion. The types of logical reasoning differ concerning the exact norms they use as well as the certainty of the conclusion they arrive at.<sup>[1]</sup><sup>[15]</sup> **>>Deductive reasoning offers the strongest support and implies its conclusion with certainty, like mathematical proofs.<<** For non-deductive reasoning, the premises make the conclusion more likely but do not ensure it. This support comes in degrees: strong arguments make the conclusion very likely, as is the case for well-researched issues in the empirical sciences.<sup>[1]</sup><sup>[16]</sup> Some theorists give a very wide definition of logical reasoning that includes its role as a cognitive skill responsible for high-quality thinking. In this regard, it has roughly the same meaning as critical thinking.<sup>[13]</sup><sup>[17]</sup>

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C04 · 2026-10-02-building-a-small-language-mod · Reliable Tool/Function Calling

**Claim** (prose, label: single source):

> Regarding recovery, targeted recovery hints have been shown to recover many failed tasks in ToolBench-X, whereas test-time scaling provides more limited gains [E96].

- **E96** fact: Targeted recovery hints can recover many failed tasks in ToolBench-X.
  - quote: "Targeted recovery hints recover many failed tasks, while test-time scaling yields more limited gains."
  - source: Beyond Function Calling: Benchmarking Tool-Using Agents under Tool-Environment Unreliability
  - passage: …zard types: Specification Drift, Invocation Error, Execution Failure, Output Drift, and Cross-source Conflict. Crucially, each injected instance remains solvable through at least one valid recovery path, such as retrying, fallback, verification, or cross-checking. Experiments reveal a substantial reliability gap: agents that perform well with reliable tools often fail under recoverable hazards. Further analysis shows that failures are driven less by tool-use volume or inference budget than by limited hazard diagnosis and ineffective recovery. **>>Targeted recovery hints recover many failed tasks, while test-time scaling yields more limited gains.<<** These results suggest that tool-use evaluation should move beyond function-call accuracy toward task completion under unreliable tool environments. The code and data is available at https://github.com/Foreverskyou/ToolBench-X.

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C05 · 2026-10-02-building-a-small-language-mod · Reliable Tool/Function Calling

**Claim** (prose, label: single source):

> Additionally, the process requires blocking premature completion when evidence is incomplete or contradictory, and mandating final-answer canonicalization before the ‘FINISH’ signal [E101].

- **E101** fact: Reliable Tool/Function Calling requires blocking premature completion when evidence is incomplete or contradictory.
  - quote: "4. Block premature completion when evidence is incomplete or contradictory, and require final-answer canonicalization before ‘FINISH‘."
  - source: Beyond Function Calling: Benchmarking Tool-Using Agents under Tool ...
  - passage: [Core Requirements] 1. Select failpoints deterministically using task identity, tool name, call slot, failpoint, and ‘FAIL_SEED‘. 2. Record observable injection events without overwriting the original business payload. 3. Do not silently swallow exceptions or represent hard failures as successful results. **>>4. Block premature completion when evidence is incomplete or contradictory, and require final-answer canonicalization before ‘FINISH‘.<<** 5. Keep the injected fault schedule reproducible across no-hint and with-hint conditions to support controlled comparison. [… omitted: activation schemas, failure families, event contracts, recovery rules, and anti-regression checks …]

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C06 · 2026-10-02-building-a-small-language-mod · Executive summary

**Claim** (prose, label: established):

> Privacy and Deployment:** For deployment in privacy-related domains, the system must be designed for local, private hosting [E52][E53], ensuring that inference requires no outbound network calls [E54].

- **E52** fact: Open-source multilingual models support enterprise deployment.
  - quote: "Open-source multilingual models increasingly support enterprise deployment because organisations need private hosting, regional compliance, and domain fine-tuning."
  - source: How AI Models Handle Multiple Languages and Global Deployment
  - passage: [Introduction > Popular Multilingual AI Models Used Today > Enterprise Open-Source Alternatives] **>>Open-source multilingual models increasingly support enterprise deployment because organisations need private hosting, regional compliance, and domain fine-tuning.<<** Open-source options allow stronger control over compliance and deployment geography.

- **E53** fact: Open-source options allow stronger control over compliance and deployment geography.
  - quote: "Open-source options allow stronger control over compliance and deployment geography."
  - source: How AI Models Handle Multiple Languages and Global Deployment
  - passage: [Introduction > Popular Multilingual AI Models Used Today > Enterprise Open-Source Alternatives] Open-source multilingual models increasingly support enterprise deployment because organisations need private hosting, regional compliance, and domain fine-tuning. **>>Open-source options allow stronger control over compliance and deployment geography.<<**

- **E54** fact: To deploy the model in privacy-related domains, no outbound network calls for inference are required.
  - quote: "No outbound network calls for inference; optional telemetry must be opt‑in and anonymized."
  - source: Optimizing High Performance Inference Pipelines for Privacy Focused ...
  - passage: [Introduction > Understanding Privacy Constraints] | Requirement | Description | Implication for Deployment | |---|---|---| | **Data residency** | All user prompts and generated text must stay on the device. | **>>No outbound network calls for inference; optional telemetry must be opt‑in and anonymized.<<** | | **Model confidentiality** | The model weights themselves may be proprietary or contain copyrighted material. | Protect weights from extraction (e.g., use encrypted storage, secure enclaves). | | **Regulatory compliance** | GDPR, HIPAA, etc., impose audit trails and access controls. | Implement logging, role‑based access, and possibly on‑device attestations. | | **Attack surface reduction** | Local execution reduces exposure to man‑in‑the‑middle attacks but introduces side‑channel risks. | Harden runtime, constant‑time kernels, and limit process privileges. |

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C07 · 2026-10-02-building-a-small-language-mod · Data Requirements

**Claim** (prose, label: single source):

> The training framework utilized is Hugging Face Transformers [E48], and the training approach is defined as two-stage fine-tuning [E47][E43].

- **E48** fact: The training framework is Hugging Face Transformers.
  - quote: "Training Framework: Hugging Face Transformers"
  - source: Telugu-learning LLM: Fine-Tuning LLaMA 3 (8B) for Telugu ... - GitHub
  - passage: - Telugu Wikisource (classical literature) - Public domain poetry collections - Traditional Telugu songs and verses - Aya Telugu Poems dataset - Classical works (Vemana, Sumathi, Bhaskara Satakams) - Base Model: LLaMA 3 8B - Training Approach: Two-stage fine-tuning - Hardware Requirements: A100 GPU (80GB) or equivalent - **>>Training Framework: Hugging Face Transformers<<** ``` training_args = { "per_device_train_batch_size": 2, "gradient_accumulation_steps": 8, "learning_rate": 2e-5, "warmup_ratio": 0.03, "bf16": True, "evaluation_strategy": "steps" } ``` - Mixed Precision Training (BF16) - Gradient Checkpointing - LoRA/QLoRA for efficient fine-tuning - Distributed Training support 1. Gather general Telugu corpus 2. Clean and deduplicate data 3. Collect literary and poetic texts 4. Prepare validation sets 1. Analyze LLaMA 3 tokenizer 2. Extend vocabulary for Telugu 3. Train custom tokenizer if needed 4. Implement efficient text processing 1. General Telugu language training 2. Poetry and literature specialization 3. Continuous evaluation and optimization 1. Perplexity measurements 2. Generation quality assessment 3. Poetry style and accuracy validation 4. Human evaluation - Python 3.8+ - …

- **E47** fact: The training approach is two-stage fine-tuning.
  - quote: "Training Approach: Two-stage fine-tuning"
  - source: Telugu-learning LLM: Fine-Tuning LLaMA 3 (8B) for Telugu ... - GitHub
  - passage: - Telugu Wikisource (classical literature) - Public domain poetry collections - Traditional Telugu songs and verses - Aya Telugu Poems dataset - Classical works (Vemana, Sumathi, Bhaskara Satakams) - Base Model: LLaMA 3 8B - **>>Training Approach: Two-stage fine-tuning<<** - Hardware Requirements: A100 GPU (80GB) or equivalent - Training Framework: Hugging Face Transformers ``` training_args = { "per_device_train_batch_size": 2, "gradient_accumulation_steps": 8, "learning_rate": 2e-5, "warmup_ratio": 0.03, "bf16": True, "evaluation_strategy": "steps" } ``` - Mixed Precision Training (BF16) - Gradient Checkpointing - LoRA/QLoRA for efficient fine-tuning - Distributed Training support 1. Gather general Telugu corpus 2. Clean and deduplicate data 3. Collect literary and poetic texts 4. Prepare validation sets 1. Analyze LLaMA 3 tokenizer 2. Extend vocabulary for Telugu 3. Train custom tokenizer if needed 4. Implement efficient text processing 1. General Telugu language training 2. Poetry and literature specialization 3. Continuous evaluation and optimization 1. Perplexity measurements 2. Generation quality assessment 3. Poetry style and accuracy validation 4. Human evaluation - Python 3.8+ - …

- **E43** fact: The LLaMA 3 8B model is fine-tuned in two stages.
  - quote: "Two-stage fine-tuning approach"
  - source: Telugu-learning LLM: Fine-Tuning LLaMA 3 (8B) for Telugu ... - GitHub
  - passage: This project aims to create a specialized Telugu language model by fine-tuning LLaMA 3 (8B) in two stages: first for general Telugu language understanding, and then for Telugu poetry and literature generation. The project involves fine-tuning the LLaMA 3 8B model to: 1. Understand and generate general Telugu text 2. Create and interpret Telugu poetry and literature - **>>Two-stage fine-tuning approach<<** - Comprehensive Telugu dataset collection - Custom tokenization for Telugu - Parameter-efficient training methods - Poetry and literature generation capabilities

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C08 · 2026-10-02-building-a-small-language-mod · Pretraining and Fine-Tuning

**Claim** (prose, label: single source):

> For advanced, large-scale multilingual architectures, the Aya-Expanse 8B model is described as a decoder-only Transformer network with approximately 8 billion parameters [E21].

- **E21** fact: Aya-Expanse 8B model has 32 transformer layers, each containing 32 self-attention heads.
  - quote: "Aya-Expanse 8B is instantiated as a decoder-only Transformer network comprising approximately 8 billion parameters, with 32 transformer layers each containing 32 self-attention heads (Dang et al., 2024, Farashah et al., 9 Jan 2026, Moslem et al., 26 Oct 2025)."
  - source: Aya-Expanse 8B: Scalable Multilingual LLM
  - passage: [Aya-Expanse 8B: Scalable Multilingual LLM > 1. Model Architecture] **>>Aya-Expanse 8B is instantiated as a decoder-only Transformer network comprising approximately 8 billion parameters, with 32 transformer layers each containing 32 self-attention heads (Dang et al., 2024, Farashah et al., 9 Jan 2026, Moslem et al., 26 Oct 2025).<<** The hidden dimension is 6,144, and the feed-forward inner dimension is 24,576. SwiGLU activation and grouped-query attention are employed for parameter efficiency and memory reduction at long context windows. Rotary position embeddings (RoPE) are integrated for context extrapolation (Dang et al., 2024). Vocabulary size is approximately 128,000 subword tokens via SentencePiece tokenization, supporting multilingual coverage. Layer normalization is applied in every block. The architecture incorporates FlashAttention for efficient inference (Kovalchuk et al., 18 Sep 2025). Model weights utilize FP16/bfloat16 precision, and the model fits into ~32 GB of GPU memory for inference at an 8K-token context length.

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C09 · 2026-10-02-building-a-small-language-mod · Strong Reasoning

**Claim** (prose, label: single source):

> It requires a logical warrant, meaning the reasoning must connect the evidence to the claim logically [E82].

- **E82** fact: Strong Reasoning requires a logical connection between evidence and claim.
  - quote: "3. **Logical Warrant** – Does the reasoning connect evidence to claim logically?"
  - source: Evidence Chain Explained: Build Strong Arguments in Writing
  - passage: [1. Introduction > 10. Final Checklist for a Strong Argument] 1. **Clear Claim** – Is it specific and debatable? 2. **Robust Evidence** – Are sources credible and relevant? **>>3. **Logical Warrant** – Does the reasoning connect evidence to claim logically?<<** 4. **Backing for Warrant** – Is the underlying logic supported? 5. **Qualifiers** – Do they appropriately limit scope? 6. **Counter‑Evidence Addressed** – Are objections anticipated and rebutted? 7. **Coherence** – Does the argument flow smoothly? 8. **Credibility** – Are all sources trustworthy?

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C10 · 2026-10-02-building-a-small-language-mod · Practical Recommendations

**Claim** (prose, label: established):

> To ensure reliability, the architecture must implement a multi-layered stack [E87] that mandates final-answer canonicalization before the completion signal [E101] and prevents the silent swallowing of exceptions [E100].

- **E87** fact: The reliability stack has five layers.
  - quote: "The reliability stack has five layers:"
  - source: Tool-use reliability, function-calling robustness, and structured ...
  - passage: …acts establish reliability. A tool call is a distributed systems boundary. One side is an uncertain planner trained to predict text. The other side is a deterministic or semi-deterministic software system with permissions, data, side effects, invariants, and failure modes. Function calling is the serialization protocol between them. Structured output enforcement is the grammar layer. Tool-use reliability is the complete end-to-end property: the user’s intent is translated into a valid, authorized, state-consistent, semantically correct operation, and failures are contained. **>>The reliability stack has five layers:<<**

- **E101** fact: Reliable Tool/Function Calling requires blocking premature completion when evidence is incomplete or contradictory.
  - quote: "4. Block premature completion when evidence is incomplete or contradictory, and require final-answer canonicalization before ‘FINISH‘."
  - source: Beyond Function Calling: Benchmarking Tool-Using Agents under Tool ...
  - passage: [Core Requirements] 1. Select failpoints deterministically using task identity, tool name, call slot, failpoint, and ‘FAIL_SEED‘. 2. Record observable injection events without overwriting the original business payload. 3. Do not silently swallow exceptions or represent hard failures as successful results. **>>4. Block premature completion when evidence is incomplete or contradictory, and require final-answer canonicalization before ‘FINISH‘.<<** 5. Keep the injected fault schedule reproducible across no-hint and with-hint conditions to support controlled comparison. [… omitted: activation schemas, failure families, event contracts, recovery rules, and anti-regression checks …]

- **E100** fact: Reliable Tool/Function Calling requires not silently swallowing exceptions or representing hard failures as successful results.
  - quote: "3. Do not silently swallow exceptions or represent hard failures as successful results."
  - source: Beyond Function Calling: Benchmarking Tool-Using Agents under Tool ...
  - passage: [Core Requirements] 1. Select failpoints deterministically using task identity, tool name, call slot, failpoint, and ‘FAIL_SEED‘. 2. Record observable injection events without overwriting the original business payload. **>>3. Do not silently swallow exceptions or represent hard failures as successful results.<<** 4. Block premature completion when evidence is incomplete or contradictory, and require final-answer canonicalization before ‘FINISH‘. 5. Keep the injected fault schedule reproducible across no-hint and with-hint conditions to support controlled comparison. [… omitted: activation schemas, failure families, event contracts, recovery rules, and anti-regression checks …]

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C11 · 2026-10-02-building-a-small-language-mod · Deployment and Integration

**Claim** (table, label: none):

> | **Multilingual Input** | Training on Telugu conversations in Romanized script | [E5] |

- **E5** fact: The model 'jayasuryajsk/whisper-large-v3-Telugu-Romanized' is trained to transcribe Telugu conversations in Romanized script.
  - quote: "The model is trained to transcipt Telugu conversations in Romanized script, that most people uses in day to day life."
  - source: jayasuryajsk/whisper-large-v3-Telugu-Romanized
  - passage: This model is a fine-tuned version of openai/whisper-large-v3 on the Telugu Romanized 1.0 dataset. It achieves the following results on the evaluation set: - eval_loss: 1.5009 - eval_wer: 68.1275 - eval_runtime: 591.6137 - eval_samples_per_second: 0.798 - eval_steps_per_second: 0.1 - epoch: 8.6207 - step: 1000 **>>The model is trained to transcipt Telugu conversations in Romanized script, that most people uses in day to day life.<<** Limitations: Sometimes, it translates the audio to english directly. Working on this to fix it. Gpt 4 api was used to convert `google-fleurs` telugu labels to romanized script. I used english tokenizer, since the script is in english alphabet to train the model. ``` from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline import torch device = "cuda" if torch.cuda.is_available() else "cpu" torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32 model_id = "jayasuryajsk/whisper-large-v3-Telugu-Romanized" model = AutoModelForSpeechSeq2Seq.from_pretrained( model_id, torch_dtype=torch_dtype ) model.to(device) processor = AutoProcessor.from_pretrained(model_id) pipe = pipeline( "automatic-speech-recognition", model=model, toke…

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C12 · 2026-10-02-building-a-small-language-mod · Deployment and Integration

**Claim** (table, label: none):

> | **Fine-Tuning** | Ability to mix verified and unverified data | [E51] |

- **E51** fact: The model can be fine-tuned with a mix of verified and unverified data.
  - quote: "We also investigate the effect of mixing verified and unverified data during fine-tuning"
  - source: TeluguST-46: A Benchmark Corpus and Comprehensive ...
  - passage: …e the performance of both cascaded (IndicWhisper+IndicMT, IndicWav2Vec+IndicMT) and end-to-end models (SeamlessM4T-v2 large, SONAR), providing empirical evidence that while cascaded approaches with extensive language-specific training data achieve superior performance, carefully fine-tuned end-to-end systems show promising competitiveness with limited data. (3) We analyze the reliability and discriminative power of six standard automatic metrics (BLEU, METEOR, ChrF++, ROUGE, TER, and BERTScore) by comparing them with ChatGPT-style human evaluations. **>>We also investigate the effect of mixing verified and unverified data during fine-tuning<<**, offering insights into corpus construction strategies under resource constraints. Together, these efforts provide a solid foundation for Telugu–English ST benchmarking and offer broader implications for other morphologically rich, underrepresented languages. All resources—data splits, evaluation scripts, and system outputs—are made publicly available to foster reproducible and inclusive research in multilingual speech translation.

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C13 · 2026-10-02-building-a-small-language-mod · Strong Reasoning

**Claim** (table, label: none):

> | **Model Performance** | Strong gains in multi-step reasoning and agentic tasks | [E79] |

- **E79** fact: Gemini 3.8 Flash has significant gains in software engineering, agentic tasks, and multi-step reasoning.
  - quote: "Gemini 3.8 Flash is Google's most intelligent Flash model with significant gains from 3.7 Flash across software engineering, agentic tasks, and multi-step reasoning."
  - source: Best AI Models for Tool Calling and Function Calling
  - passage: …problems. With a 256K context window, Hy3 targets long-horizon tasks, including improved coreference resolution, multi-turn constraint tracking, and stable tool-calling that generalizes across agent scaffoldings. Tencent positions it as a reliable, cost-effective option across coding, document processing, financial analysis, game development, and frontend design, with a strong emphasis on grounded, anti-hallucination behavior that answers when grounded and flags when evidence is missing rather than fabricating. **>>Gemini 3.8 Flash is Google's most intelligent Flash model with significant gains from 3.7 Flash across software engineering, agentic tasks, and multi-step reasoning.<<** Claude Opus 5.5 is Anthropic's flagship model for demanding reasoning, coding, and long-horizon agentic work, succeeding Claude Opus 5. It is particularly strong at multi-step changes in large codebases, code review and bug finding, financial and scientific analysis, and reading dense charts, diagrams, and screenshots, and it is more careful than its predecessor about only stating figures and citing sources it can back up.

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C14 · 2026-10-02-building-a-small-language-mod · Deployment and Integration

**Claim** (prose, label: single source):

> When training the model, the English tokenizer was used because the script is in the English alphabet [E59].

- **E59** fact: The model uses English tokenizer since the script is in English alphabet to train the model.
  - quote: "I used english tokenizer, since the script is in english alphabet to train the model."
  - source: jayasuryajsk/whisper-large-v3-Telugu-Romanized
  - passage: …er-large-v3 on the Telugu Romanized 1.0 dataset. It achieves the following results on the evaluation set: - eval_loss: 1.5009 - eval_wer: 68.1275 - eval_runtime: 591.6137 - eval_samples_per_second: 0.798 - eval_steps_per_second: 0.1 - epoch: 8.6207 - step: 1000 The model is trained to transcipt Telugu conversations in Romanized script, that most people uses in day to day life. Limitations: Sometimes, it translates the audio to english directly. Working on this to fix it. Gpt 4 api was used to convert `google-fleurs` telugu labels to romanized script. **>>I used english tokenizer, since the script is in english alphabet to train the model.<<** ``` from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline import torch device = "cuda" if torch.cuda.is_available() else "cpu" torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32 model_id = "jayasuryajsk/whisper-large-v3-Telugu-Romanized" model = AutoModelForSpeechSeq2Seq.from_pretrained( model_id, torch_dtype=torch_dtype ) model.to(device) processor = AutoProcessor.from_pretrained(model_id) pipe = pipeline( "automatic-speech-recognition", model=model, tokenizer=processor.tokenizer, feature_extractor=proce…

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C15 · 2026-10-02-building-a-small-language-mod · Reliable Tool/Function Calling

**Claim** (prose, label: single source):

> The WHEN2TOOL benchmark includes three multi-hop environments that necessitate chains of three dependent tool calls following the pattern x → y → z [E103].

- **E103** fact: WHEN2TOOL includes 3 multi-hop environments that require chains of 3 dependent tool calls.
  - quote: "In addition to the 15 single-hop environments, WHEN2TOOL includes 3 multi-hop environments that require chains of 3 dependent tool calls following the pattern x → y → z:"
  - source: LLM Agents Already Know When to Call Tools -- Even Without Reasoning
  - passage: [LLM Agents Already Know When to Call Tools - Even Without Reasoning > A.6 Multi-hop environments] **>>In addition to the 15 single-hop environments, WHEN2TOOL includes 3 multi-hop environments that require chains of 3 dependent tool calls following the pattern x → y → z:<<** each hop's output is needed as input for the next. These test whether models can assess tool necessity across a sequence of dependent operations. All three multi-hop environments follow the same structure: the model executes hop 1 to obtain x, uses x as input to hop 2 to obtain y, and uses y as input to hop 3 to obtain the final answer z. Each hop reuses the same tools as its single-hop counterpart. Difficulty scales identically (easy = solvable mentally, hard = requires tools), but now the model must make a tool-call decision at each hop.

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C16 · 2026-10-02-building-a-small-language-mod · Pretraining and Fine-Tuning

**Claim** (table, label: none):

> | IndicBERT-v3-4B | 4B | English (0.30 ratio), 14 major Indic languages (0.25 ratio), 8 low-resource languages (0.15 ratio) [E10][E11][E12] | Multilingual representation across multiple languages [E11] |

- **E10** fact: The IndicBERT-v3-4B model was pre-trained on a 0.30 ratio of English text in Phase 1.
  - quote: "1. **Phase 1 (English Foundation):** Continual pre-training on English text (ratio: 0.30)."
  - source: ai4bharat/IndicBERT-v3-4B - Hugging Face
  - passage: …** architecture. Unlike standard causal LLMs, these models have been adapted to use **bidirectional attention**, making them highly effective for encoder-heavy tasks. Also checkout IndicBERT-v3-270M and IndicBERT-v3-1B. - **Architecture:** Bidirectional Gemma-3 (Non-causal attention) - **Vocabulary:** Standard Gemma-3 vocabulary - **Objective:** Masked Next Token Prediction (MNTP) The models were trained using a rigid curriculum learning approach to balance English proficiency with Indic language adaptation while preventing catastrophic forgetting. **>>1. **Phase 1 (English Foundation):** Continual pre-training on English text (ratio: 0.30).<<** 2. **Phase 2 (High/Mid-Resource Adaptation):** Adapted to 14 major Indic languages (Hindi, Telugu, Tamil, Bengali, Malayalam, Marathi, Kannada, Gujarati, Assamese, Oriya, Punjabi, Sindhi, Urdu, Nepali) with a 0.25 ratio. 3. **Phase 3 (Low-Resource Generalization):** Introduction of 8 low-resource languages (Bodo, Dogri, Konkani, Kashmiri, Maithili, Manipuri, Sanskrit, Santali) at a 0.15 ratio. 4. **Phase 4 (Joint Consolidation):** The final 10% of training steps involved joint training on all 23 languages (0.25 ratio) to mitigate catastrophic forge…

- **E11** fact: The IndicBERT-v3-4B model was pre-trained on a 0.25 ratio of 14 major Indic languages in Phase 2.
  - quote: "2. **Phase 2 (High/Mid-Resource Adaptation):** Adapted to 14 major Indic languages (Hindi, Telugu, Tamil, Bengali, Malayalam, Marathi, Kannada, Gujarati, Assamese, Oriya, Punjabi, Sindhi, Urdu, Nepali) with a 0.25 ratio."
  - source: ai4bharat/IndicBERT-v3-4B - Hugging Face
  - passage: …avy tasks. Also checkout IndicBERT-v3-270M and IndicBERT-v3-1B. - **Architecture:** Bidirectional Gemma-3 (Non-causal attention) - **Vocabulary:** Standard Gemma-3 vocabulary - **Objective:** Masked Next Token Prediction (MNTP) The models were trained using a rigid curriculum learning approach to balance English proficiency with Indic language adaptation while preventing catastrophic forgetting. 1. **Phase 1 (English Foundation):** Continual pre-training on English text (ratio: 0.30). **>>2. **Phase 2 (High/Mid-Resource Adaptation):** Adapted to 14 major Indic languages (Hindi, Telugu, Tamil, Bengali, Malayalam, Marathi, Kannada, Gujarati, Assamese, Oriya, Punjabi, Sindhi, Urdu, Nepali) with a 0.25 ratio.<<** 3. **Phase 3 (Low-Resource Generalization):** Introduction of 8 low-resource languages (Bodo, Dogri, Konkani, Kashmiri, Maithili, Manipuri, Sanskrit, Santali) at a 0.15 ratio. 4. **Phase 4 (Joint Consolidation):** The final 10% of training steps involved joint training on all 23 languages (0.25 ratio) to mitigate catastrophic forgetting. The model was continually pre-trained on approximately **35 Billion tokens** (12M samples) sampled from various sources notably **Sangraha-Verified**…

- **E12** fact: The IndicBERT-v3-4B model was pre-trained on a 0.15 ratio of 8 low-resource languages in Phase 3.
  - quote: "3. **Phase 3 (Low-Resource Generalization):** Introduction of 8 low-resource languages (Bodo, Dogri, Konkani, Kashmiri, Maithili, Manipuri, Sanskrit, Santali) at a 0.15 ratio."
  - source: ai4bharat/IndicBERT-v3-4B - Hugging Face
  - passage: …Next Token Prediction (MNTP) The models were trained using a rigid curriculum learning approach to balance English proficiency with Indic language adaptation while preventing catastrophic forgetting. 1. **Phase 1 (English Foundation):** Continual pre-training on English text (ratio: 0.30). 2. **Phase 2 (High/Mid-Resource Adaptation):** Adapted to 14 major Indic languages (Hindi, Telugu, Tamil, Bengali, Malayalam, Marathi, Kannada, Gujarati, Assamese, Oriya, Punjabi, Sindhi, Urdu, Nepali) with a 0.25 ratio. **>>3. **Phase 3 (Low-Resource Generalization):** Introduction of 8 low-resource languages (Bodo, Dogri, Konkani, Kashmiri, Maithili, Manipuri, Sanskrit, Santali) at a 0.15 ratio.<<** 4. **Phase 4 (Joint Consolidation):** The final 10% of training steps involved joint training on all 23 languages (0.25 ratio) to mitigate catastrophic forgetting. The model was continually pre-trained on approximately **35 Billion tokens** (12M samples) sampled from various sources notably **Sangraha-Verified**, **FineWeb-2**, **IndicCorp-v2** amongst many other datasets. **Model was trained upto 4096 sequence length throughout the training.** This model was trained with **Masked Next Token Prediction (MNT…

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C17 · 2026-10-02-building-a-small-language-mod · Pretraining and Fine-Tuning

**Claim** (prose, label: single source):

> This process began with continual pre-training on English text (ratio: 0.30) in Phase 1 [E10].

- **E10** fact: The IndicBERT-v3-4B model was pre-trained on a 0.30 ratio of English text in Phase 1.
  - quote: "1. **Phase 1 (English Foundation):** Continual pre-training on English text (ratio: 0.30)."
  - source: ai4bharat/IndicBERT-v3-4B - Hugging Face
  - passage: …** architecture. Unlike standard causal LLMs, these models have been adapted to use **bidirectional attention**, making them highly effective for encoder-heavy tasks. Also checkout IndicBERT-v3-270M and IndicBERT-v3-1B. - **Architecture:** Bidirectional Gemma-3 (Non-causal attention) - **Vocabulary:** Standard Gemma-3 vocabulary - **Objective:** Masked Next Token Prediction (MNTP) The models were trained using a rigid curriculum learning approach to balance English proficiency with Indic language adaptation while preventing catastrophic forgetting. **>>1. **Phase 1 (English Foundation):** Continual pre-training on English text (ratio: 0.30).<<** 2. **Phase 2 (High/Mid-Resource Adaptation):** Adapted to 14 major Indic languages (Hindi, Telugu, Tamil, Bengali, Malayalam, Marathi, Kannada, Gujarati, Assamese, Oriya, Punjabi, Sindhi, Urdu, Nepali) with a 0.25 ratio. 3. **Phase 3 (Low-Resource Generalization):** Introduction of 8 low-resource languages (Bodo, Dogri, Konkani, Kashmiri, Maithili, Manipuri, Sanskrit, Santali) at a 0.15 ratio. 4. **Phase 4 (Joint Consolidation):** The final 10% of training steps involved joint training on all 23 languages (0.25 ratio) to mitigate catastrophic forge…

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C18 · 2026-10-02-building-a-small-language-mod · Strong Reasoning

**Claim** (prose, label: single source):

> Conceptually, it is defined by making connections explicit and openly stated [E67], and being precise about what the evidence says regarding the claim [E68].

- **E67** fact: Strong Reasoning makes connections explicit and openly stated.
  - quote: "MAKES CONNECTIONS EXPLICIT (OPENLY STATED)."
  - source: [PDF] EBA SKILL #2: Strong Reasoning
  - passage: [INSTRUCTIONAL ONE-PAGER > Strong Reasoning Checklist] Make sure your reasoning does the following: - CLEARLY AND FULLY EXPLAINS HOW THE EVIDENCE CONNECTS TO THE CLAIM. - » » Reasoning is not just restating the evidence in different words! - **>>MAKES CONNECTIONS EXPLICIT (OPENLY STATED).<<** - » » Doesn't assume the reader knows or believes certain things. - IS PRECISE ABOUT WHAT THE EVIDENCE SAYS ABOUT THE CLAIM. - » » Doesn't overstate things, or draw too big a conclusion. - AVOIDS GENERALIZATIONS AND STEREOTYPES. - SPEAKS TO THE AUDIENCE AND WHAT THE AUDIENCE MIGHT CARE ABOUT.

- **E68** fact: Strong Reasoning is precise about what the evidence says about the claim.
  - quote: "IS PRECISE ABOUT WHAT THE EVIDENCE SAYS ABOUT THE CLAIM."
  - source: [PDF] EBA SKILL #2: Strong Reasoning
  - passage: [INSTRUCTIONAL ONE-PAGER > Strong Reasoning Checklist] Make sure your reasoning does the following: - CLEARLY AND FULLY EXPLAINS HOW THE EVIDENCE CONNECTS TO THE CLAIM. - » » Reasoning is not just restating the evidence in different words! - MAKES CONNECTIONS EXPLICIT (OPENLY STATED). - » » Doesn't assume the reader knows or believes certain things. - **>>IS PRECISE ABOUT WHAT THE EVIDENCE SAYS ABOUT THE CLAIM.<<** - » » Doesn't overstate things, or draw too big a conclusion. - AVOIDS GENERALIZATIONS AND STEREOTYPES. - SPEAKS TO THE AUDIENCE AND WHAT THE AUDIENCE MIGHT CARE ABOUT.

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C19 · 2026-10-02-building-a-small-language-mod · Executive summary

**Claim** (prose, label: established):

> For reliable tool calling, the architecture must implement a multi-layered stack [E87] that mandates final-answer canonicalization [E101] and prevents the silent swallowing of exceptions [E100].

- **E87** fact: The reliability stack has five layers.
  - quote: "The reliability stack has five layers:"
  - source: Tool-use reliability, function-calling robustness, and structured ...
  - passage: …acts establish reliability. A tool call is a distributed systems boundary. One side is an uncertain planner trained to predict text. The other side is a deterministic or semi-deterministic software system with permissions, data, side effects, invariants, and failure modes. Function calling is the serialization protocol between them. Structured output enforcement is the grammar layer. Tool-use reliability is the complete end-to-end property: the user’s intent is translated into a valid, authorized, state-consistent, semantically correct operation, and failures are contained. **>>The reliability stack has five layers:<<**

- **E101** fact: Reliable Tool/Function Calling requires blocking premature completion when evidence is incomplete or contradictory.
  - quote: "4. Block premature completion when evidence is incomplete or contradictory, and require final-answer canonicalization before ‘FINISH‘."
  - source: Beyond Function Calling: Benchmarking Tool-Using Agents under Tool ...
  - passage: [Core Requirements] 1. Select failpoints deterministically using task identity, tool name, call slot, failpoint, and ‘FAIL_SEED‘. 2. Record observable injection events without overwriting the original business payload. 3. Do not silently swallow exceptions or represent hard failures as successful results. **>>4. Block premature completion when evidence is incomplete or contradictory, and require final-answer canonicalization before ‘FINISH‘.<<** 5. Keep the injected fault schedule reproducible across no-hint and with-hint conditions to support controlled comparison. [… omitted: activation schemas, failure families, event contracts, recovery rules, and anti-regression checks …]

- **E100** fact: Reliable Tool/Function Calling requires not silently swallowing exceptions or representing hard failures as successful results.
  - quote: "3. Do not silently swallow exceptions or represent hard failures as successful results."
  - source: Beyond Function Calling: Benchmarking Tool-Using Agents under Tool ...
  - passage: [Core Requirements] 1. Select failpoints deterministically using task identity, tool name, call slot, failpoint, and ‘FAIL_SEED‘. 2. Record observable injection events without overwriting the original business payload. **>>3. Do not silently swallow exceptions or represent hard failures as successful results.<<** 4. Block premature completion when evidence is incomplete or contradictory, and require final-answer canonicalization before ‘FINISH‘. 5. Keep the injected fault schedule reproducible across no-hint and with-hint conditions to support controlled comparison. [… omitted: activation schemas, failure families, event contracts, recovery rules, and anti-regression checks …]

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C20 · 2026-10-02-building-a-small-language-mod · Deployment and Integration

**Claim** (prose, label: single source):

> For developing multilingual capabilities, TeluguST-46 provides a benchmark corpus specifically for Telugu-English speech translation [E50].

- **E50** fact: TeluguST-46 provides a benchmark corpus for Telugu-English speech translation.
  - quote: "This paper addresses these gaps through three major contributions: (1) We release 46 hours of manually verified Telugu--English parallel data"
  - source: TeluguST-46: A Benchmark Corpus and Comprehensive ...
  - passage: [TeluguST-46: A Benchmark Corpus and Comprehensive Evaluation for Telugu-English Speech Translation > 1 Introduction] **>>This paper addresses these gaps through three major contributions: (1) We release 46 hours of manually verified Telugu--English parallel data<<**<sup>1</sup><sup>1</sup> 1 TeluguST-46 curated from the CSTD corpus Mirishkar et al. (2021), facilitating reproducible benchmarks for ST in a low-resource Indian languages (2) We evaluate the performance of both cascaded (IndicWhisper+IndicMT, IndicWav2Vec+IndicMT) and end-to-end models (SeamlessM4T-v2 large, SONAR), providing empirical evidence that while cascaded approaches with extensive language-specific training data achieve superior performance, carefully fine-tuned end-to-end systems show promising competitiveness with limited data. (3) We analyze the reliability and discriminative power of six standard automatic metrics (BLEU, METEOR, ChrF++, ROUGE, TER, and BERTScore) by comparing them with ChatGPT-style human evaluations. We also investigate the effect of mixing verified and unverified data during fine-tuning, offering insights into corpus construction strategies under resource constraints. Together, these efforts pro…

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C21 · 2026-10-02-building-a-small-language-mod · Deployment and Integration

**Claim** (table, label: none):

> | **Compliance** | Logging, role-based access, and on-device attestations | [E56] |

- **E56** fact: To comply with regulatory requirements, logging, role-based access, and on-device attestations may be necessary.
  - quote: "Implement logging, role‑based access, and possibly on‑device attestations."
  - source: Optimizing High Performance Inference Pipelines for Privacy Focused ...
  - passage: …ng Privacy Constraints] | Requirement | Description | Implication for Deployment | |---|---|---| | **Data residency** | All user prompts and generated text must stay on the device. | No outbound network calls for inference; optional telemetry must be opt‑in and anonymized. | | **Model confidentiality** | The model weights themselves may be proprietary or contain copyrighted material. | Protect weights from extraction (e.g., use encrypted storage, secure enclaves). | | **Regulatory compliance** | GDPR, HIPAA, etc., impose audit trails and access controls. | **>>Implement logging, role‑based access, and possibly on‑device attestations.<<** | | **Attack surface reduction** | Local execution reduces exposure to man‑in‑the‑middle attacks but introduces side‑channel risks. | Harden runtime, constant‑time kernels, and limit process privileges. |

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C22 · 2026-10-02-building-a-small-language-mod · Strong Reasoning

**Claim** (table, label: none):

> | **General Reasoning** | Requires explicit connection between evidence and claim | [E65], [E67] |

- **E65** fact: Strong Reasoning requires clearly and fully explaining how the evidence connects to the claim.
  - quote: "CLEARLY AND FULLY EXPLAINS HOW THE EVIDENCE CONNECTS TO THE CLAIM."
  - source: [PDF] EBA SKILL #2: Strong Reasoning
  - passage: [INSTRUCTIONAL ONE-PAGER > Strong Reasoning Checklist] Make sure your reasoning does the following: - **>>CLEARLY AND FULLY EXPLAINS HOW THE EVIDENCE CONNECTS TO THE CLAIM.<<** - » » Reasoning is not just restating the evidence in different words! - MAKES CONNECTIONS EXPLICIT (OPENLY STATED). - » » Doesn't assume the reader knows or believes certain things. - IS PRECISE ABOUT WHAT THE EVIDENCE SAYS ABOUT THE CLAIM. - » » Doesn't overstate things, or draw too big a conclusion. - AVOIDS GENERALIZATIONS AND STEREOTYPES. - SPEAKS TO THE AUDIENCE AND WHAT THE AUDIENCE MIGHT CARE ABOUT.

- **E67** fact: Strong Reasoning makes connections explicit and openly stated.
  - quote: "MAKES CONNECTIONS EXPLICIT (OPENLY STATED)."
  - source: [PDF] EBA SKILL #2: Strong Reasoning
  - passage: [INSTRUCTIONAL ONE-PAGER > Strong Reasoning Checklist] Make sure your reasoning does the following: - CLEARLY AND FULLY EXPLAINS HOW THE EVIDENCE CONNECTS TO THE CLAIM. - » » Reasoning is not just restating the evidence in different words! - **>>MAKES CONNECTIONS EXPLICIT (OPENLY STATED).<<** - » » Doesn't assume the reader knows or believes certain things. - IS PRECISE ABOUT WHAT THE EVIDENCE SAYS ABOUT THE CLAIM. - » » Doesn't overstate things, or draw too big a conclusion. - AVOIDS GENERALIZATIONS AND STEREOTYPES. - SPEAKS TO THE AUDIENCE AND WHAT THE AUDIENCE MIGHT CARE ABOUT.

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C23 · 2026-10-02-building-a-small-language-mod · Executive summary

**Claim** (prose, label: single source):

> The most practical and evidence-backed approach for developing a small language model (4B-8B) with strong reasoning and reliable tool calling for Telugu, English, and Tenglish is to adopt a structured, multi-stage fine-tuning process, utilizing a robust multilingual base model such as LLaMA 3 8B [E42][E46].

- **E42** fact: The LLaMA 3 8B model has 8 billion parameters.
  - quote: "LLaMA 3 (8B)"
  - source: Telugu-learning LLM: Fine-Tuning LLaMA 3 (8B) for Telugu ... - GitHub
  - passage: This project aims to create a specialized Telugu language model by fine-tuning **>>LLaMA 3 (8B)<<** in two stages: first for general Telugu language understanding, and then for Telugu poetry and literature generation. The project involves fine-tuning the LLaMA 3 8B model to: 1. Understand and generate general Telugu text 2. Create and interpret Telugu poetry and literature - Two-stage fine-tuning approach - Comprehensive Telugu dataset collection - Custom tokenization for Telugu - Parameter-efficient training methods - Poetry and literature generation capabilities

- **E46** fact: The base model for pretraining and fine-tuning is LLaMA 3 8B.
  - quote: "Base Model: LLaMA 3 8B"
  - source: Telugu-learning LLM: Fine-Tuning LLaMA 3 (8B) for Telugu ... - GitHub
  - passage: - Telugu Wikisource (classical literature) - Public domain poetry collections - Traditional Telugu songs and verses - Aya Telugu Poems dataset - Classical works (Vemana, Sumathi, Bhaskara Satakams) - **>>Base Model: LLaMA 3 8B<<** - Training Approach: Two-stage fine-tuning - Hardware Requirements: A100 GPU (80GB) or equivalent - Training Framework: Hugging Face Transformers ``` training_args = { "per_device_train_batch_size": 2, "gradient_accumulation_steps": 8, "learning_rate": 2e-5, "warmup_ratio": 0.03, "bf16": True, "evaluation_strategy": "steps" } ``` - Mixed Precision Training (BF16) - Gradient Checkpointing - LoRA/QLoRA for efficient fine-tuning - Distributed Training support 1. Gather general Telugu corpus 2. Clean and deduplicate data 3. Collect literary and poetic texts 4. Prepare validation sets 1. Analyze LLaMA 3 tokenizer 2. Extend vocabulary for Telugu 3. Train custom tokenizer if needed 4. Implement efficient text processing 1. General Telugu language training 2. Poetry and literature specialization 3. Continuous evaluation and optimization 1. Perplexity measurements 2. Generation quality assessment 3. Poetry style and accuracy validation 4. Human evaluation - Python 3.8+ - …

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C24 · 2026-10-02-building-a-small-language-mod · Reliable Tool/Function Calling

**Claim** (prose, label: single source):

> Furthermore, exception handling becomes inherently harder when agents must coordinate longer chains of tool calls [E93].

- **E93** fact: Exception handling becomes harder as agents must coordinate longer chains of tool calls.
  - quote: "Exception handling becomes harder as agents must coordinate longer chains of tool calls."
  - source: Beyond Function Calling: Benchmarking Tool-Using Agents under Tool ...
  - passage: …cales with the number of tools required by a task. Because exact tool-count bins are unevenly populated, we group tasks into three buckets — low ( tools), medium ( tools), and high ( tools), which preserves statistical power in each bucket while exposing the trend across complexity levels. Table 3 reports accuracy under this grouping. Most models show a clear decline from low- to high-complexity tasks. For example, Doubao-Seed-2.0-Lite drops from to , Gemini-3.1-Flash-Lite from to , GLM-5.1 from to , and GPT-4o from to . These declines indicate that **>>exception handling becomes harder as agents must coordinate longer chains of tool calls.<<** The trend is not perfectly monotonic across all models, suggesting that tool count is not the only source of difficulty. Exception type, workflow structure, and dependencies between calls also affect robustness. Nevertheless, the overall pattern supports a compounding-risk interpretation: as tool chains grow longer, a single mishandled exception is more likely to corrupt subsequent reasoning. Reliable agent behavior under tool uncertainty therefore requires robust per-call diagnosis and recovery, not merely stronger final-answer generation.

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C25 · 2026-10-02-building-a-small-language-mod · Practical Recommendations

**Claim** (prose, label: single source):

> The initial phase requires a multi-stage pretraining or fine-tuning approach, similar to the phased strategy used for IndicBERT-v3-4B [E10][E11][E12].

- **E10** fact: The IndicBERT-v3-4B model was pre-trained on a 0.30 ratio of English text in Phase 1.
  - quote: "1. **Phase 1 (English Foundation):** Continual pre-training on English text (ratio: 0.30)."
  - source: ai4bharat/IndicBERT-v3-4B - Hugging Face
  - passage: …** architecture. Unlike standard causal LLMs, these models have been adapted to use **bidirectional attention**, making them highly effective for encoder-heavy tasks. Also checkout IndicBERT-v3-270M and IndicBERT-v3-1B. - **Architecture:** Bidirectional Gemma-3 (Non-causal attention) - **Vocabulary:** Standard Gemma-3 vocabulary - **Objective:** Masked Next Token Prediction (MNTP) The models were trained using a rigid curriculum learning approach to balance English proficiency with Indic language adaptation while preventing catastrophic forgetting. **>>1. **Phase 1 (English Foundation):** Continual pre-training on English text (ratio: 0.30).<<** 2. **Phase 2 (High/Mid-Resource Adaptation):** Adapted to 14 major Indic languages (Hindi, Telugu, Tamil, Bengali, Malayalam, Marathi, Kannada, Gujarati, Assamese, Oriya, Punjabi, Sindhi, Urdu, Nepali) with a 0.25 ratio. 3. **Phase 3 (Low-Resource Generalization):** Introduction of 8 low-resource languages (Bodo, Dogri, Konkani, Kashmiri, Maithili, Manipuri, Sanskrit, Santali) at a 0.15 ratio. 4. **Phase 4 (Joint Consolidation):** The final 10% of training steps involved joint training on all 23 languages (0.25 ratio) to mitigate catastrophic forge…

- **E11** fact: The IndicBERT-v3-4B model was pre-trained on a 0.25 ratio of 14 major Indic languages in Phase 2.
  - quote: "2. **Phase 2 (High/Mid-Resource Adaptation):** Adapted to 14 major Indic languages (Hindi, Telugu, Tamil, Bengali, Malayalam, Marathi, Kannada, Gujarati, Assamese, Oriya, Punjabi, Sindhi, Urdu, Nepali) with a 0.25 ratio."
  - source: ai4bharat/IndicBERT-v3-4B - Hugging Face
  - passage: …avy tasks. Also checkout IndicBERT-v3-270M and IndicBERT-v3-1B. - **Architecture:** Bidirectional Gemma-3 (Non-causal attention) - **Vocabulary:** Standard Gemma-3 vocabulary - **Objective:** Masked Next Token Prediction (MNTP) The models were trained using a rigid curriculum learning approach to balance English proficiency with Indic language adaptation while preventing catastrophic forgetting. 1. **Phase 1 (English Foundation):** Continual pre-training on English text (ratio: 0.30). **>>2. **Phase 2 (High/Mid-Resource Adaptation):** Adapted to 14 major Indic languages (Hindi, Telugu, Tamil, Bengali, Malayalam, Marathi, Kannada, Gujarati, Assamese, Oriya, Punjabi, Sindhi, Urdu, Nepali) with a 0.25 ratio.<<** 3. **Phase 3 (Low-Resource Generalization):** Introduction of 8 low-resource languages (Bodo, Dogri, Konkani, Kashmiri, Maithili, Manipuri, Sanskrit, Santali) at a 0.15 ratio. 4. **Phase 4 (Joint Consolidation):** The final 10% of training steps involved joint training on all 23 languages (0.25 ratio) to mitigate catastrophic forgetting. The model was continually pre-trained on approximately **35 Billion tokens** (12M samples) sampled from various sources notably **Sangraha-Verified**…

- **E12** fact: The IndicBERT-v3-4B model was pre-trained on a 0.15 ratio of 8 low-resource languages in Phase 3.
  - quote: "3. **Phase 3 (Low-Resource Generalization):** Introduction of 8 low-resource languages (Bodo, Dogri, Konkani, Kashmiri, Maithili, Manipuri, Sanskrit, Santali) at a 0.15 ratio."
  - source: ai4bharat/IndicBERT-v3-4B - Hugging Face
  - passage: …Next Token Prediction (MNTP) The models were trained using a rigid curriculum learning approach to balance English proficiency with Indic language adaptation while preventing catastrophic forgetting. 1. **Phase 1 (English Foundation):** Continual pre-training on English text (ratio: 0.30). 2. **Phase 2 (High/Mid-Resource Adaptation):** Adapted to 14 major Indic languages (Hindi, Telugu, Tamil, Bengali, Malayalam, Marathi, Kannada, Gujarati, Assamese, Oriya, Punjabi, Sindhi, Urdu, Nepali) with a 0.25 ratio. **>>3. **Phase 3 (Low-Resource Generalization):** Introduction of 8 low-resource languages (Bodo, Dogri, Konkani, Kashmiri, Maithili, Manipuri, Sanskrit, Santali) at a 0.15 ratio.<<** 4. **Phase 4 (Joint Consolidation):** The final 10% of training steps involved joint training on all 23 languages (0.25 ratio) to mitigate catastrophic forgetting. The model was continually pre-trained on approximately **35 Billion tokens** (12M samples) sampled from various sources notably **Sangraha-Verified**, **FineWeb-2**, **IndicCorp-v2** amongst many other datasets. **Model was trained upto 4096 sequence length throughout the training.** This model was trained with **Masked Next Token Prediction (MNT…

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C26 · 2026-10-02-building-a-small-language-mod · Data Requirements

**Claim** (prose, label: single source):

> Furthermore, the LLaMA 3 8B model requires custom tokenization specifically for Telugu during the fine-tuning process [E39].

- **E39** fact: The LLaMA 3 8B model needs custom tokenization for Telugu during fine-tuning.
  - quote: "Custom tokenization for Telugu"
  - source: Telugu-learning LLM: Fine-Tuning LLaMA 3 (8B) for Telugu ... - GitHub
  - passage: This project aims to create a specialized Telugu language model by fine-tuning LLaMA 3 (8B) in two stages: first for general Telugu language understanding, and then for Telugu poetry and literature generation. The project involves fine-tuning the LLaMA 3 8B model to: 1. Understand and generate general Telugu text 2. Create and interpret Telugu poetry and literature - Two-stage fine-tuning approach - Comprehensive Telugu dataset collection - **>>Custom tokenization for Telugu<<** - Parameter-efficient training methods - Poetry and literature generation capabilities

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C27 · 2026-10-02-building-a-small-language-mod · Pretraining and Fine-Tuning

**Claim** (table, label: none):

> | 'harinpurumandla/tenglish-to-telugu' | N/A | N/A | Tenglish to Telugu translation/generation [E16] |

- **E16** fact: The 'harinpurumandla/tenglish-to-telugu' model is a pre-trained model.
  - quote: "tokenizer = AutoTokenizer.from_pretrained("harinpurumandla/tenglish-to-telugu") model = AutoModelForSeq2SeqLM.from_pretrained("harinpurumandla/tenglish-to-telugu")"
  - source: harinpurumandla/tenglish-to-telugu - Hugging Face
  - passage: ``` from transformers import AutoTokenizer, AutoModelForSeq2SeqLM **>>tokenizer = AutoTokenizer.from_pretrained("harinpurumandla/tenglish-to-telugu") model = AutoModelForSeq2SeqLM.from_pretrained("harinpurumandla/tenglish-to-telugu")<<** def to_telugu(text): inputs = tokenizer(text, return_tensors="pt", max_length=128, truncation=True) outputs = model.generate(**inputs, max_length=128, num_beams=4) return tokenizer.decode(outputs[0], skip_special_tokens=True) print(to_telugu("nenu telugu matladatanu"))

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C28 · 2026-10-02-building-a-small-language-mod · Strong Reasoning

**Claim** (prose, label: single source):

> Other models demonstrate specific strengths in complex reasoning; Gemini 3.8 Flash has shown significant gains in agentic tasks, multi-step reasoning, and software engineering [E79], while Claude Opus 5.5 is noted for its strength in multi-step changes in large codebases [E80] and for being more careful about only stating figures and citing sources it can back up [E81].

- **E79** fact: Gemini 3.8 Flash has significant gains in software engineering, agentic tasks, and multi-step reasoning.
  - quote: "Gemini 3.8 Flash is Google's most intelligent Flash model with significant gains from 3.7 Flash across software engineering, agentic tasks, and multi-step reasoning."
  - source: Best AI Models for Tool Calling and Function Calling
  - passage: …problems. With a 256K context window, Hy3 targets long-horizon tasks, including improved coreference resolution, multi-turn constraint tracking, and stable tool-calling that generalizes across agent scaffoldings. Tencent positions it as a reliable, cost-effective option across coding, document processing, financial analysis, game development, and frontend design, with a strong emphasis on grounded, anti-hallucination behavior that answers when grounded and flags when evidence is missing rather than fabricating. **>>Gemini 3.8 Flash is Google's most intelligent Flash model with significant gains from 3.7 Flash across software engineering, agentic tasks, and multi-step reasoning.<<** Claude Opus 5.5 is Anthropic's flagship model for demanding reasoning, coding, and long-horizon agentic work, succeeding Claude Opus 5. It is particularly strong at multi-step changes in large codebases, code review and bug finding, financial and scientific analysis, and reading dense charts, diagrams, and screenshots, and it is more careful than its predecessor about only stating figures and citing sources it can back up.

- **E80** fact: Claude Opus 5.5 is particularly strong at multi-step changes in large codebases.
  - quote: "Claude Opus 5.5 is Anthropic's flagship model for demanding reasoning, coding, and long-horizon agentic work, succeeding Claude Opus 5. It is particularly strong at multi-step changes in large codebases,"
  - source: Best AI Models for Tool Calling and Function Calling
  - passage: … across agent scaffoldings. Tencent positions it as a reliable, cost-effective option across coding, document processing, financial analysis, game development, and frontend design, with a strong emphasis on grounded, anti-hallucination behavior that answers when grounded and flags when evidence is missing rather than fabricating. Gemini 3.8 Flash is Google's most intelligent Flash model with significant gains from 3.7 Flash across software engineering, agentic tasks, and multi-step reasoning. **>>Claude Opus 5.5 is Anthropic's flagship model for demanding reasoning, coding, and long-horizon agentic work, succeeding Claude Opus 5. It is particularly strong at multi-step changes in large codebases,<<** code review and bug finding, financial and scientific analysis, and reading dense charts, diagrams, and screenshots, and it is more careful than its predecessor about only stating figures and citing sources it can back up.

- **E81** fact: Claude Opus 5.5 is more careful about stating figures and citing sources it can back up.
  - quote: "and it is more careful than its predecessor about only stating figures and citing sources it can back up."
  - source: Best AI Models for Tool Calling and Function Calling
  - passage: …and flags when evidence is missing rather than fabricating. Gemini 3.8 Flash is Google's most intelligent Flash model with significant gains from 3.7 Flash across software engineering, agentic tasks, and multi-step reasoning. Claude Opus 5.5 is Anthropic's flagship model for demanding reasoning, coding, and long-horizon agentic work, succeeding Claude Opus 5. It is particularly strong at multi-step changes in large codebases, code review and bug finding, financial and scientific analysis, and reading dense charts, diagrams, and screenshots, **>>and it is more careful than its predecessor about only stating figures and citing sources it can back up.<<**

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C29 · 2026-10-02-building-a-small-language-mod · Pretraining and Fine-Tuning

**Claim** (prose, label: single source):

> Phase 2 adapted the model to 14 major Indic languages (including Telugu) using a 0.25 ratio [E11], followed by Phase 3, which introduced 8 low-resource languages at a 0.15 ratio [E12].

- **E11** fact: The IndicBERT-v3-4B model was pre-trained on a 0.25 ratio of 14 major Indic languages in Phase 2.
  - quote: "2. **Phase 2 (High/Mid-Resource Adaptation):** Adapted to 14 major Indic languages (Hindi, Telugu, Tamil, Bengali, Malayalam, Marathi, Kannada, Gujarati, Assamese, Oriya, Punjabi, Sindhi, Urdu, Nepali) with a 0.25 ratio."
  - source: ai4bharat/IndicBERT-v3-4B - Hugging Face
  - passage: …avy tasks. Also checkout IndicBERT-v3-270M and IndicBERT-v3-1B. - **Architecture:** Bidirectional Gemma-3 (Non-causal attention) - **Vocabulary:** Standard Gemma-3 vocabulary - **Objective:** Masked Next Token Prediction (MNTP) The models were trained using a rigid curriculum learning approach to balance English proficiency with Indic language adaptation while preventing catastrophic forgetting. 1. **Phase 1 (English Foundation):** Continual pre-training on English text (ratio: 0.30). **>>2. **Phase 2 (High/Mid-Resource Adaptation):** Adapted to 14 major Indic languages (Hindi, Telugu, Tamil, Bengali, Malayalam, Marathi, Kannada, Gujarati, Assamese, Oriya, Punjabi, Sindhi, Urdu, Nepali) with a 0.25 ratio.<<** 3. **Phase 3 (Low-Resource Generalization):** Introduction of 8 low-resource languages (Bodo, Dogri, Konkani, Kashmiri, Maithili, Manipuri, Sanskrit, Santali) at a 0.15 ratio. 4. **Phase 4 (Joint Consolidation):** The final 10% of training steps involved joint training on all 23 languages (0.25 ratio) to mitigate catastrophic forgetting. The model was continually pre-trained on approximately **35 Billion tokens** (12M samples) sampled from various sources notably **Sangraha-Verified**…

- **E12** fact: The IndicBERT-v3-4B model was pre-trained on a 0.15 ratio of 8 low-resource languages in Phase 3.
  - quote: "3. **Phase 3 (Low-Resource Generalization):** Introduction of 8 low-resource languages (Bodo, Dogri, Konkani, Kashmiri, Maithili, Manipuri, Sanskrit, Santali) at a 0.15 ratio."
  - source: ai4bharat/IndicBERT-v3-4B - Hugging Face
  - passage: …Next Token Prediction (MNTP) The models were trained using a rigid curriculum learning approach to balance English proficiency with Indic language adaptation while preventing catastrophic forgetting. 1. **Phase 1 (English Foundation):** Continual pre-training on English text (ratio: 0.30). 2. **Phase 2 (High/Mid-Resource Adaptation):** Adapted to 14 major Indic languages (Hindi, Telugu, Tamil, Bengali, Malayalam, Marathi, Kannada, Gujarati, Assamese, Oriya, Punjabi, Sindhi, Urdu, Nepali) with a 0.25 ratio. **>>3. **Phase 3 (Low-Resource Generalization):** Introduction of 8 low-resource languages (Bodo, Dogri, Konkani, Kashmiri, Maithili, Manipuri, Sanskrit, Santali) at a 0.15 ratio.<<** 4. **Phase 4 (Joint Consolidation):** The final 10% of training steps involved joint training on all 23 languages (0.25 ratio) to mitigate catastrophic forgetting. The model was continually pre-trained on approximately **35 Billion tokens** (12M samples) sampled from various sources notably **Sangraha-Verified**, **FineWeb-2**, **IndicCorp-v2** amongst many other datasets. **Model was trained upto 4096 sequence length throughout the training.** This model was trained with **Masked Next Token Prediction (MNT…

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C30 · 2026-10-02-building-a-small-language-mod · Deployment and Integration

**Claim** (prose, label: single source):

> Open-source multilingual models are shown to support enterprise deployment because organizations require private hosting, regional compliance, and domain fine-tuning [E52].

- **E52** fact: Open-source multilingual models support enterprise deployment.
  - quote: "Open-source multilingual models increasingly support enterprise deployment because organisations need private hosting, regional compliance, and domain fine-tuning."
  - source: How AI Models Handle Multiple Languages and Global Deployment
  - passage: [Introduction > Popular Multilingual AI Models Used Today > Enterprise Open-Source Alternatives] **>>Open-source multilingual models increasingly support enterprise deployment because organisations need private hosting, regional compliance, and domain fine-tuning.<<** Open-source options allow stronger control over compliance and deployment geography.

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C31 · 2026-10-03-pretraining-a-4b-model-for-te · Executive summary

**Claim** (prose, label: established):

> Finally, achieving advanced capabilities like reasoning and native tool calling requires subsequent finetuning, utilizing approaches such as Reason-then-Act [E52], and evaluating performance based on final-task accuracy [E59].

- **E52** fact: The Reason-then-Act baseline partially shifts the tradeoff between accuracy and tool calls, reducing unnecessary easy-task calls.
  - quote: "Reason-then-Act (red) partially shifts the tradeoff, reducing unnecessary easy-task calls, but still produces negative efficiency on hard tasks."
  - source: LLM Agents Already Know When to Call Tools -- Even Without Reasoning
  - passage: [LLM Agents Already Know When to Call Tools - Even Without Reasoning > 3.1 Experimental setup] Figure 2: Accuracy vs. Avg tool calls per difficulty for Qwen3-1.7B. ⋆=Default, F=Force, N=Necessary, S=Sparse, X=No Tool. **>>Reason-then-Act (red) partially shifts the tradeoff, reducing unnecessary easy-task calls, but still produces negative efficiency on hard tasks.<<** Lines fold non-monotonically, reflecting coarse prompt control. <!-- image --> Prompt-only baselines. We test five prompt modes spanning the full range of tool-use instructions: Force (F), "tool use is mandatory"; Default (⋆), no explicit requirements; Necessary (N), "only if necessary"; Sparse (S), "expensive, use sparingly"; and No Tool (X), "do not use any tools." Reason-then-act baselines. In addition to prompt-only control, we evaluate a stronger baseline inspired by the think-before-act paradigm from ReAct [Yao et al., 2022] and Reflexion [Shinn et al., 2023]. Before making a tool-call decision, the model is instructed to first reason about whether it can solve the task directly or needs a tool, then act on its own assessment. We apply this reasoning step to each of the same five prompt modes (Force, Default, Necessary,…

- **E59** fact: The primary metric used to evaluate the models is final-task accuracy.
  - quote: "We report final-task accuracy as the primary metric."
  - source: Beyond Function Calling: Benchmarking Tool-Using Agents under Tool ...
  - passage: [Beyond Function Calling: Benchmarking Tool-Using Agents under Tool-Environment Unreliability > Experiments > Experimental Setup] We conduct a comprehensive evaluation on ToolBench-X by benchmarking twelve prominent large language models, covering both proprietary and open-source systems. The complete list of evaluated models is provided in Table 7. **>>We report final-task accuracy as the primary metric.<<** A task is considered correct if the execution state recorded by the backend at task completion matches the ground truth, or if the model’s final response explicitly contains the ground-truth answer.

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C32 · 2026-10-03-pretraining-a-4b-model-for-te · Executive summary

**Claim** (prose, label: single source):

> To ensure specialized performance, the model must undergo dedicated training for Telugu-to-Roman transliteration using approximately 35k instruction-formatted pairs [E9][E50].

- **E9** fact: The model pavanmantha/qwen3-4b-telugu-transliteration was trained for 1 epoch.
  - quote: "It was trained for 1 epoch on ~35k instruction-formatted Telugu–Romanized pairs using DDP across 3× NVIDIA L40S GPUs."
  - source: pavanmantha/qwen3-4b-telugu-transliteration · Hugging Face
  - passage: `pavanmantha/qwen3-4b-telugu-transliteration` is a full fine-tune of **Qwen3-4B-Instruct** for the task of **Telugu-to-Roman (Latin script) transliteration**. Given a sentence written in Telugu script, the model outputs its phonetically accurate Roman-alphabet equivalent. **>>It was trained for 1 epoch on ~35k instruction-formatted Telugu–Romanized pairs using DDP across 3× NVIDIA L40S GPUs.<<** - **Developed by:** Pavan Kumar Mantha (pavanmantha) - **Model type:** Causal Language Model — full fine-tune (no LoRA/PEFT) - **Language(s):** Telugu (`te` ) → Roman/Latin (`en` script) - **License:** Apache 2.0 (inherited from Qwen3 base) - **Finetuned from:**`Qwen/Qwen3-4B-Instruct-2507` - **Total parameters:** 4.02B (all trainable) - **Model dtype:** bfloat16 - **Repository:** pavanmantha/qwen3-4b-telugu-transliteration - **Training dataset:** pavanmantha/telugu_transliteration_40k This model is intended for converting **Telugu script text** into its **Roman (Latin alphabet) transliteration**. Useful for: - Search and indexing pipelines that need phonetic normalization - Text-to-speech preprocessing - Keyboard input systems for Telugu speakers - Cross-script NLP research Can be integrated into …

- **E50** fact: The model was trained for 1 epoch on ~35k instruction-formatted Telugu–Romanized pairs.
  - quote: "Given a sentence written in Telugu script, the model outputs its phonetically accurate Roman-alphabet equivalent. It was trained for 1 epoch on ~35k instruction-formatted Telugu–Romanized pairs using DDP across 3× NVIDIA L40S GPUs."
  - source: pavanmantha/qwen3-4b-telugu-transliteration · Hugging Face
  - passage: `pavanmantha/qwen3-4b-telugu-transliteration` is a full fine-tune of **Qwen3-4B-Instruct** for the task of **Telugu-to-Roman (Latin script) transliteration**. **>>Given a sentence written in Telugu script, the model outputs its phonetically accurate Roman-alphabet equivalent. It was trained for 1 epoch on ~35k instruction-formatted Telugu–Romanized pairs using DDP across 3× NVIDIA L40S GPUs.<<** - **Developed by:** Pavan Kumar Mantha (pavanmantha) - **Model type:** Causal Language Model — full fine-tune (no LoRA/PEFT) - **Language(s):** Telugu (`te` ) → Roman/Latin (`en` script) - **License:** Apache 2.0 (inherited from Qwen3 base) - **Finetuned from:**`Qwen/Qwen3-4B-Instruct-2507` - **Total parameters:** 4.02B (all trainable) - **Model dtype:** bfloat16 - **Repository:** pavanmantha/qwen3-4b-telugu-transliteration - **Training dataset:** pavanmantha/telugu_transliteration_40k This model is intended for converting **Telugu script text** into its **Roman (Latin alphabet) transliteration**. Useful for: - Search and indexing pipelines that need phonetic normalization - Text-to-speech preprocessing - Keyboard input systems for Telugu speakers - Cross-script NLP research Can be integrated into …

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C33 · 2026-10-03-pretraining-a-4b-model-for-te · Practical Recommendations

**Claim** (prose, label: single source):

> Furthermore, while the model can support multiple languages, including Telugu, English, and transliteration [E46], the evidence does not provide specific methods or benchmarks for evaluating reasoning or native tool calling tasks for a 4B model, limiting the ability to benchmark these goals directly.

- **E46** fact: The model should support multiple languages, including Telugu, English, and transliteration.
  - quote: "Supported languages: Assamese, Bengali, Gujarati, Hindi, Marathi, Odiya, Punjabi, Kannada, Malayalam, Tamil, Telugu and English."
  - source: ai4bharat/IndicBART - Hugging Face
  - passage: IndicBART is a multilingual, sequence-to-sequence pre-trained model focusing on Indic languages and English. It currently supports 11 Indian languages and is based on the mBART architecture. You can use IndicBART model to build natural language generation applications for Indian languages by finetuning the model with supervised training data for tasks like machine translation, summarization, question generation, etc. Some salient features of the IndicBART are: - **>>Supported languages: Assamese, Bengali, Gujarati, Hindi, Marathi, Odiya, Punjabi, Kannada, Malayalam, Tamil, Telugu and English.<<** Not all of these languages are supported by mBART50 and mT5. - The model is much smaller than the mBART and mT5(-base) models, so less computationally expensive for finetuning and decoding. - Trained on large Indic language corpora (452 million sentences and 9 billion tokens) which also includes Indian English content. - All languages, except English, have been represented in Devanagari script to encourage transfer learning among the related languages. You can read more about IndicBART in this paper. For detailed documentation, look here: https://github.com/AI4Bharat/indic-bart/ and https://indicn…

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C34 · 2026-10-03-pretraining-a-4b-model-for-te · Practical Recommendations

**Claim** (prose, label: established):

> The core training objective should be the application of cross-entropy loss applied only to unmasked assistant tokens [E15], while utilizing optimal hyperparameters for a 4B model, specifically a batch size of 4 [E7] and a weight decay of 0.001 [E8].

- **E15** fact: The primary training objective for pretraining a 4B model is cross-entropy loss on unmasked assistant tokens only.
  - quote: "The primary training objective is **cross-entropy loss** (on unmasked assistant tokens only)."
  - source: pavanmantha/qwen3-4b-telugu-transliteration · Hugging Face
  - passage: [→ "manava parinama prakriya yokka avalokananni andinchandi."] The loss dropped rapidly from **2.42 → 0.62** in the first 350 steps, demonstrating fast and stable convergence for this transliteration task. The validation set consists of 8,723 held-out samples from the same `pavanmantha/telugu_transliteration_40k` dataset, split with `seed=42`. **>>The primary training objective is **cross-entropy loss** (on unmasked assistant tokens only).<<** Evaluation loss was tracked every 500 steps via `eval_strategy="steps"`. Additional task-specific metrics (CER, WER, exact match) can be computed post-hoc using the inference snippet above. - The model is trained on a single dataset and may not generalize well to specialized domains (legal, medical, technical Telugu). - Transliteration conventions vary across regions and systems (e.g., ISO 15919 vs. informal conventions); the model reflects the conventions present in the training data. - Rare or archaic Telugu vocabulary may be poorly handled. - The model carries any biases inherent in the underlying Qwen3-4B-Instruct base model. Users should validate outputs against a known-good reference for high-stakes applications. For best results, inputs should…

- **E7** fact: The optimal hyperparameters for pretraining a 4B model from scratch include a batch size of 4.
  - quote: "Batch size | 4 |"
  - source: Evaluating Reasoning in Post-Trained Language Models - arXiv
  - passage: [Thinking About Thinking: Evaluating Reasoning in Post-Trained Language Models > Appendix B Hyperparameters] | Hyperparameter | Value | |---|---| | **>>Batch size | 4 |<<** | Learning rate | | | Weight decay | 0.001 |

- **E8** fact: The optimal hyperparameters for pretraining a 4B model from scratch include a weight decay of 0.001.
  - quote: "Weight decay | 0.001 |"
  - source: Evaluating Reasoning in Post-Trained Language Models - arXiv
  - passage: [Thinking About Thinking: Evaluating Reasoning in Post-Trained Language Models > Appendix B Hyperparameters] | Hyperparameter | Value | |---|---| | Batch size | 4 | | Learning rate | | | **>>Weight decay | 0.001 |<<**

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C35 · 2026-10-03-pretraining-a-4b-model-for-te · Executive summary

**Claim** (prose, label: established):

> The core training objective should be the application of cross-entropy loss applied only to unmasked assistant tokens [E15], utilizing optimal hyperparameters such as a batch size of 4 [E7] and a weight decay of 0.001 [E8], and requiring computational resources involving 3× NVIDIA L40S GPUs [E76].

- **E15** fact: The primary training objective for pretraining a 4B model is cross-entropy loss on unmasked assistant tokens only.
  - quote: "The primary training objective is **cross-entropy loss** (on unmasked assistant tokens only)."
  - source: pavanmantha/qwen3-4b-telugu-transliteration · Hugging Face
  - passage: [→ "manava parinama prakriya yokka avalokananni andinchandi."] The loss dropped rapidly from **2.42 → 0.62** in the first 350 steps, demonstrating fast and stable convergence for this transliteration task. The validation set consists of 8,723 held-out samples from the same `pavanmantha/telugu_transliteration_40k` dataset, split with `seed=42`. **>>The primary training objective is **cross-entropy loss** (on unmasked assistant tokens only).<<** Evaluation loss was tracked every 500 steps via `eval_strategy="steps"`. Additional task-specific metrics (CER, WER, exact match) can be computed post-hoc using the inference snippet above. - The model is trained on a single dataset and may not generalize well to specialized domains (legal, medical, technical Telugu). - Transliteration conventions vary across regions and systems (e.g., ISO 15919 vs. informal conventions); the model reflects the conventions present in the training data. - Rare or archaic Telugu vocabulary may be poorly handled. - The model carries any biases inherent in the underlying Qwen3-4B-Instruct base model. Users should validate outputs against a known-good reference for high-stakes applications. For best results, inputs should…

- **E7** fact: The optimal hyperparameters for pretraining a 4B model from scratch include a batch size of 4.
  - quote: "Batch size | 4 |"
  - source: Evaluating Reasoning in Post-Trained Language Models - arXiv
  - passage: [Thinking About Thinking: Evaluating Reasoning in Post-Trained Language Models > Appendix B Hyperparameters] | Hyperparameter | Value | |---|---| | **>>Batch size | 4 |<<** | Learning rate | | | Weight decay | 0.001 |

- **E8** fact: The optimal hyperparameters for pretraining a 4B model from scratch include a weight decay of 0.001.
  - quote: "Weight decay | 0.001 |"
  - source: Evaluating Reasoning in Post-Trained Language Models - arXiv
  - passage: [Thinking About Thinking: Evaluating Reasoning in Post-Trained Language Models > Appendix B Hyperparameters] | Hyperparameter | Value | |---|---| | Batch size | 4 | | Learning rate | | | **>>Weight decay | 0.001 |<<**

- **E76** fact: The computational requirements for pretraining a 4B model for Telugu, English, and transliteration include 3 NVIDIA L40S GPUs with 46 GB each.
  - quote: "Hardware: 3× NVIDIA L40S (46 GB each)"
  - source: pavanmantha/qwen3-4b-telugu-transliteration · Hugging Face
  - passage: (passage not found in the library)

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C36 · 2026-10-03-pretraining-a-4b-model-for-te · Computational and Storage Requirements

**Claim** (prose, label: single source):

> Regarding the model architecture and training process, the model pavanmantha/qwen3-4b-telugu-transliteration has 4.02B trainable parameters [E10].

- **E10** fact: The model pavanmantha/qwen3-4b-telugu-transliteration has 4.02B trainable parameters.
  - quote: "Total parameters: 4.02B (all trainable)"
  - source: pavanmantha/qwen3-4b-telugu-transliteration · Hugging Face
  - passage: (passage not found in the library)

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C37 · 2026-10-03-pretraining-a-4b-model-for-te · Model Architecture and Design

**Claim** (prose, label: single source):

> For transliteration tasks, the model can be trained to transcribe Telugu conversations using Romanized script [E4].

- **E4** fact: The model is trained to transcribe Telugu conversations in Romanized script.
  - quote: "The model is trained to transcipt Telugu conversations in Romanized script, that most people uses in day to day life."
  - source: jayasuryajsk/whisper-large-v3-Telugu-Romanized
  - passage: This model is a fine-tuned version of openai/whisper-large-v3 on the Telugu Romanized 1.0 dataset. It achieves the following results on the evaluation set: - eval_loss: 1.5009 - eval_wer: 68.1275 - eval_runtime: 591.6137 - eval_samples_per_second: 0.798 - eval_steps_per_second: 0.1 - epoch: 8.6207 - step: 1000 **>>The model is trained to transcipt Telugu conversations in Romanized script, that most people uses in day to day life.<<** Limitations: Sometimes, it translates the audio to english directly. Working on this to fix it. Gpt 4 api was used to convert `google-fleurs` telugu labels to romanized script. I used english tokenizer, since the script is in english alphabet to train the model. ``` from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline import torch device = "cuda" if torch.cuda.is_available() else "cpu" torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32 model_id = "jayasuryajsk/whisper-large-v3-Telugu-Romanized" model = AutoModelForSpeechSeq2Seq.from_pretrained( model_id, torch_dtype=torch_dtype ) model.to(device) processor = AutoProcessor.from_pretrained(model_id) pipe = pipeline( "automatic-speech-recognition", model=model, toke…

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C38 · 2026-10-03-pretraining-a-4b-model-for-te · Computational and Storage Requirements

**Claim** (table, label: none):

> | Total Training Data (Tokens) | 22.63 Trillion | [E79] |

- **E79** fact: The total training data for pretraining a 4B model is approximately 22.63 trillion tokens.
  - quote: "Combined Total Training Data: 22.63 Trillion Tokens"
  - source: bharatgenai/Param2-17B-A2.4B-Thinking - Hugging Face
  - passage: (passage not found in the library)

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C39 · 2026-10-03-pretraining-a-4b-model-for-te · Practical Recommendations

**Claim** (prose, label: single source):

> For the tool-calling component, the Reason-then-Act approach is recommended, as it was shown to partially shift the tradeoff between accuracy and tool calls by reducing unnecessary easy-task calls [E52].

- **E52** fact: The Reason-then-Act baseline partially shifts the tradeoff between accuracy and tool calls, reducing unnecessary easy-task calls.
  - quote: "Reason-then-Act (red) partially shifts the tradeoff, reducing unnecessary easy-task calls, but still produces negative efficiency on hard tasks."
  - source: LLM Agents Already Know When to Call Tools -- Even Without Reasoning
  - passage: [LLM Agents Already Know When to Call Tools - Even Without Reasoning > 3.1 Experimental setup] Figure 2: Accuracy vs. Avg tool calls per difficulty for Qwen3-1.7B. ⋆=Default, F=Force, N=Necessary, S=Sparse, X=No Tool. **>>Reason-then-Act (red) partially shifts the tradeoff, reducing unnecessary easy-task calls, but still produces negative efficiency on hard tasks.<<** Lines fold non-monotonically, reflecting coarse prompt control. <!-- image --> Prompt-only baselines. We test five prompt modes spanning the full range of tool-use instructions: Force (F), "tool use is mandatory"; Default (⋆), no explicit requirements; Necessary (N), "only if necessary"; Sparse (S), "expensive, use sparingly"; and No Tool (X), "do not use any tools." Reason-then-act baselines. In addition to prompt-only control, we evaluate a stronger baseline inspired by the think-before-act paradigm from ReAct [Yao et al., 2022] and Reflexion [Shinn et al., 2023]. Before making a tool-call decision, the model is instructed to first reason about whether it can solve the task directly or needs a tool, then act on its own assessment. We apply this reasoning step to each of the same five prompt modes (Force, Default, Necessary,…

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C40 · 2026-10-03-pretraining-a-4b-model-for-te · Practical Recommendations

**Claim** (prose, label: single source):

> The primary recommendation for pretraining a 4B model for Telugu, English, and transliteration is to utilize a massive, multi-phase pretraining approach, starting with a Causal Language Model architecture that undergoes a full fine-tune [E40].

- **E40** fact: The model type is a Causal Language Model — full fine-tune (no LoRA/PEFT).
  - quote: "Model type: Causal Language Model — full fine-tune (no LoRA/PEFT)"
  - source: pavanmantha/qwen3-4b-telugu-transliteration · Hugging Face
  - passage: (passage not found in the library)

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C41 · 2026-10-03-pretraining-a-4b-model-for-te · Model Architecture and Design

**Claim** (prose, label: single source):

> Specific training methodologies for Telugu–Romanized pairs include training for 1 epoch on approximately 35k instruction-formatted pairs [E50].

- **E50** fact: The model was trained for 1 epoch on ~35k instruction-formatted Telugu–Romanized pairs.
  - quote: "Given a sentence written in Telugu script, the model outputs its phonetically accurate Roman-alphabet equivalent. It was trained for 1 epoch on ~35k instruction-formatted Telugu–Romanized pairs using DDP across 3× NVIDIA L40S GPUs."
  - source: pavanmantha/qwen3-4b-telugu-transliteration · Hugging Face
  - passage: `pavanmantha/qwen3-4b-telugu-transliteration` is a full fine-tune of **Qwen3-4B-Instruct** for the task of **Telugu-to-Roman (Latin script) transliteration**. **>>Given a sentence written in Telugu script, the model outputs its phonetically accurate Roman-alphabet equivalent. It was trained for 1 epoch on ~35k instruction-formatted Telugu–Romanized pairs using DDP across 3× NVIDIA L40S GPUs.<<** - **Developed by:** Pavan Kumar Mantha (pavanmantha) - **Model type:** Causal Language Model — full fine-tune (no LoRA/PEFT) - **Language(s):** Telugu (`te` ) → Roman/Latin (`en` script) - **License:** Apache 2.0 (inherited from Qwen3 base) - **Finetuned from:**`Qwen/Qwen3-4B-Instruct-2507` - **Total parameters:** 4.02B (all trainable) - **Model dtype:** bfloat16 - **Repository:** pavanmantha/qwen3-4b-telugu-transliteration - **Training dataset:** pavanmantha/telugu_transliteration_40k This model is intended for converting **Telugu script text** into its **Roman (Latin alphabet) transliteration**. Useful for: - Search and indexing pipelines that need phonetic normalization - Text-to-speech preprocessing - Keyboard input systems for Telugu speakers - Cross-script NLP research Can be integrated into …

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C42 · 2026-10-03-pretraining-a-4b-model-for-te · Computational and Storage Requirements

**Claim** (table, label: none):

> | Total Batch Size | 5120 | [E78] |

- **E78** fact: The total batch size for pretraining is 5120.
  - quote: "The batch size on each GPU is 64, and thus the total batch size is 64 * 8 * 10 = 5120."
  - source: Training Multilingual Pre-trained Language Model with Byte-level Subwords
  - passage: [TRAINING MULTILINGUAL PRE-TRAINED LANGUAGE MODELS WITH BYTE-LEVEL SUBWORDS > 4.1 Experimental Setting] Pre-training Details We train the NEZHAmodels on 10 servers on Huawei Cloud 8 , each of which has 8 NVIDIA Tesla V100 GPUs with 32GB memory. The distributed training algorithm is the Ring-AllReduce 9 and was employed with the framework named Horovod [28]. We trained each model from scratch and pre-train for 80k steps. **>>The batch size on each GPU is 64, and thus the total batch size is 64 * 8 * 10 = 5120.<<** For the each model tested, we set the maximum learning rate to be 1e - 4 (with 1800 warm-up steps and polynomial decay). In addition, we adopted the mixed-precision training using FP16 [29] in the pre-training phase. We employ wikipedia datasets containing 11 [8 https://www.huaweicloud.com/product/modelarts.html](https://www.huaweicloud.com/product/modelarts.html) [9 https://github.com/baidu-research/baidu-allreduce](https://github.com/baidu-research/baidu-allreduce) Figure 6: Case Study on Arabic Figure 7: Comparison between Google Vocabulary and BBPE Vocabulary <!-- image --> languages including English, Arabic, Spanish, Thai, Russian, German, Italian, French, Malay, Portuguese …

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C43 · 2026-10-03-pretraining-a-4b-model-for-te · Evaluating Model Performance

**Claim** (table, label: none):

> | Evaluation WER (Transliteration) | 68.1275 | [E26] |

- **E26** fact: The model achieves an eval_loss of 1.5009 and an eval_wer of 68.1275.
  - quote: "- eval_loss: 1.5009 - eval_wer: 68.1275"
  - source: jayasuryajsk/whisper-large-v3-Telugu-Romanized
  - passage: This model is a fine-tuned version of openai/whisper-large-v3 on the Telugu Romanized 1.0 dataset. It achieves the following results on the evaluation set: **>>- eval_loss: 1.5009 - eval_wer: 68.1275<<** - eval_runtime: 591.6137 - eval_samples_per_second: 0.798 - eval_steps_per_second: 0.1 - epoch: 8.6207 - step: 1000 The model is trained to transcipt Telugu conversations in Romanized script, that most people uses in day to day life. Limitations: Sometimes, it translates the audio to english directly. Working on this to fix it. Gpt 4 api was used to convert `google-fleurs` telugu labels to romanized script. I used english tokenizer, since the script is in english alphabet to train the model. ``` from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline import torch device = "cuda" if torch.cuda.is_available() else "cpu" torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32 model_id = "jayasuryajsk/whisper-large-v3-Telugu-Romanized" model = AutoModelForSpeechSeq2Seq.from_pretrained( model_id, torch_dtype=torch_dtype ) model.to(device) processor = AutoProcessor.from_pretrained(model_id) pipe = pipeline( "automatic-speech-recognition", model=model, toke…

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C44 · 2026-10-03-pretraining-a-4b-model-for-te · Model Architecture and Design

**Claim** (prose, label: single source):

> This process involves taking a sentence written in Telugu script and having the model output its phonetically accurate Roman-alphabet equivalent [E50].

- **E50** fact: The model was trained for 1 epoch on ~35k instruction-formatted Telugu–Romanized pairs.
  - quote: "Given a sentence written in Telugu script, the model outputs its phonetically accurate Roman-alphabet equivalent. It was trained for 1 epoch on ~35k instruction-formatted Telugu–Romanized pairs using DDP across 3× NVIDIA L40S GPUs."
  - source: pavanmantha/qwen3-4b-telugu-transliteration · Hugging Face
  - passage: `pavanmantha/qwen3-4b-telugu-transliteration` is a full fine-tune of **Qwen3-4B-Instruct** for the task of **Telugu-to-Roman (Latin script) transliteration**. **>>Given a sentence written in Telugu script, the model outputs its phonetically accurate Roman-alphabet equivalent. It was trained for 1 epoch on ~35k instruction-formatted Telugu–Romanized pairs using DDP across 3× NVIDIA L40S GPUs.<<** - **Developed by:** Pavan Kumar Mantha (pavanmantha) - **Model type:** Causal Language Model — full fine-tune (no LoRA/PEFT) - **Language(s):** Telugu (`te` ) → Roman/Latin (`en` script) - **License:** Apache 2.0 (inherited from Qwen3 base) - **Finetuned from:**`Qwen/Qwen3-4B-Instruct-2507` - **Total parameters:** 4.02B (all trainable) - **Model dtype:** bfloat16 - **Repository:** pavanmantha/qwen3-4b-telugu-transliteration - **Training dataset:** pavanmantha/telugu_transliteration_40k This model is intended for converting **Telugu script text** into its **Roman (Latin alphabet) transliteration**. Useful for: - Search and indexing pipelines that need phonetic normalization - Text-to-speech preprocessing - Keyboard input systems for Telugu speakers - Cross-script NLP research Can be integrated into …

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C45 · 2026-10-03-pretraining-a-4b-model-for-te · Computational and Storage Requirements

**Claim** (prose, label: single source):

> The total batch size for pretraining is documented as 5120, which is calculated based on a batch size of 64 on each GPU [E78].

- **E78** fact: The total batch size for pretraining is 5120.
  - quote: "The batch size on each GPU is 64, and thus the total batch size is 64 * 8 * 10 = 5120."
  - source: Training Multilingual Pre-trained Language Model with Byte-level Subwords
  - passage: [TRAINING MULTILINGUAL PRE-TRAINED LANGUAGE MODELS WITH BYTE-LEVEL SUBWORDS > 4.1 Experimental Setting] Pre-training Details We train the NEZHAmodels on 10 servers on Huawei Cloud 8 , each of which has 8 NVIDIA Tesla V100 GPUs with 32GB memory. The distributed training algorithm is the Ring-AllReduce 9 and was employed with the framework named Horovod [28]. We trained each model from scratch and pre-train for 80k steps. **>>The batch size on each GPU is 64, and thus the total batch size is 64 * 8 * 10 = 5120.<<** For the each model tested, we set the maximum learning rate to be 1e - 4 (with 1800 warm-up steps and polynomial decay). In addition, we adopted the mixed-precision training using FP16 [29] in the pre-training phase. We employ wikipedia datasets containing 11 [8 https://www.huaweicloud.com/product/modelarts.html](https://www.huaweicloud.com/product/modelarts.html) [9 https://github.com/baidu-research/baidu-allreduce](https://github.com/baidu-research/baidu-allreduce) Figure 6: Case Study on Arabic Figure 7: Comparison between Google Vocabulary and BBPE Vocabulary <!-- image --> languages including English, Arabic, Spanish, Thai, Russian, German, Italian, French, Malay, Portuguese …

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C46 · 2026-10-03-pretraining-a-4b-model-for-te · Pretraining Objectives and Loss Functions

**Claim** (prose, label: single source):

> Furthermore, this model was trained for one epoch using approximately 35k instruction-formatted Telugu–Romanized pairs [E9].

- **E9** fact: The model pavanmantha/qwen3-4b-telugu-transliteration was trained for 1 epoch.
  - quote: "It was trained for 1 epoch on ~35k instruction-formatted Telugu–Romanized pairs using DDP across 3× NVIDIA L40S GPUs."
  - source: pavanmantha/qwen3-4b-telugu-transliteration · Hugging Face
  - passage: `pavanmantha/qwen3-4b-telugu-transliteration` is a full fine-tune of **Qwen3-4B-Instruct** for the task of **Telugu-to-Roman (Latin script) transliteration**. Given a sentence written in Telugu script, the model outputs its phonetically accurate Roman-alphabet equivalent. **>>It was trained for 1 epoch on ~35k instruction-formatted Telugu–Romanized pairs using DDP across 3× NVIDIA L40S GPUs.<<** - **Developed by:** Pavan Kumar Mantha (pavanmantha) - **Model type:** Causal Language Model — full fine-tune (no LoRA/PEFT) - **Language(s):** Telugu (`te` ) → Roman/Latin (`en` script) - **License:** Apache 2.0 (inherited from Qwen3 base) - **Finetuned from:**`Qwen/Qwen3-4B-Instruct-2507` - **Total parameters:** 4.02B (all trainable) - **Model dtype:** bfloat16 - **Repository:** pavanmantha/qwen3-4b-telugu-transliteration - **Training dataset:** pavanmantha/telugu_transliteration_40k This model is intended for converting **Telugu script text** into its **Roman (Latin alphabet) transliteration**. Useful for: - Search and indexing pipelines that need phonetic normalization - Text-to-speech preprocessing - Keyboard input systems for Telugu speakers - Cross-script NLP research Can be integrated into …

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C47 · 2026-10-03-pretraining-a-4b-model-for-te · Computational and Storage Requirements

**Claim** (prose, label: single source):

> The computational requirements for pretraining a 4B model for Telugu, English, and transliteration include utilizing 3 NVIDIA L40S GPUs, each having 46 GB of memory [E76].

- **E76** fact: The computational requirements for pretraining a 4B model for Telugu, English, and transliteration include 3 NVIDIA L40S GPUs with 46 GB each.
  - quote: "Hardware: 3× NVIDIA L40S (46 GB each)"
  - source: pavanmantha/qwen3-4b-telugu-transliteration · Hugging Face
  - passage: (passage not found in the library)

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C48 · 2026-10-03-pretraining-a-4b-model-for-te · Evaluating Model Performance

**Claim** (table, label: none):

> | Evaluation Loss (Transliteration) | 1.5009 | [E26] |

- **E26** fact: The model achieves an eval_loss of 1.5009 and an eval_wer of 68.1275.
  - quote: "- eval_loss: 1.5009 - eval_wer: 68.1275"
  - source: jayasuryajsk/whisper-large-v3-Telugu-Romanized
  - passage: This model is a fine-tuned version of openai/whisper-large-v3 on the Telugu Romanized 1.0 dataset. It achieves the following results on the evaluation set: **>>- eval_loss: 1.5009 - eval_wer: 68.1275<<** - eval_runtime: 591.6137 - eval_samples_per_second: 0.798 - eval_steps_per_second: 0.1 - epoch: 8.6207 - step: 1000 The model is trained to transcipt Telugu conversations in Romanized script, that most people uses in day to day life. Limitations: Sometimes, it translates the audio to english directly. Working on this to fix it. Gpt 4 api was used to convert `google-fleurs` telugu labels to romanized script. I used english tokenizer, since the script is in english alphabet to train the model. ``` from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline import torch device = "cuda" if torch.cuda.is_available() else "cpu" torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32 model_id = "jayasuryajsk/whisper-large-v3-Telugu-Romanized" model = AutoModelForSpeechSeq2Seq.from_pretrained( model_id, torch_dtype=torch_dtype ) model.to(device) processor = AutoProcessor.from_pretrained(model_id) pipe = pipeline( "automatic-speech-recognition", model=model, toke…

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C49 · 2026-10-03-pretraining-a-4b-model-for-te · Practical Recommendations

**Claim** (prose, label: single source):

> This specialized training involves taking a sentence written in Telugu script and having the model output its phonetically accurate Roman-alphabet equivalent [E50].

- **E50** fact: The model was trained for 1 epoch on ~35k instruction-formatted Telugu–Romanized pairs.
  - quote: "Given a sentence written in Telugu script, the model outputs its phonetically accurate Roman-alphabet equivalent. It was trained for 1 epoch on ~35k instruction-formatted Telugu–Romanized pairs using DDP across 3× NVIDIA L40S GPUs."
  - source: pavanmantha/qwen3-4b-telugu-transliteration · Hugging Face
  - passage: `pavanmantha/qwen3-4b-telugu-transliteration` is a full fine-tune of **Qwen3-4B-Instruct** for the task of **Telugu-to-Roman (Latin script) transliteration**. **>>Given a sentence written in Telugu script, the model outputs its phonetically accurate Roman-alphabet equivalent. It was trained for 1 epoch on ~35k instruction-formatted Telugu–Romanized pairs using DDP across 3× NVIDIA L40S GPUs.<<** - **Developed by:** Pavan Kumar Mantha (pavanmantha) - **Model type:** Causal Language Model — full fine-tune (no LoRA/PEFT) - **Language(s):** Telugu (`te` ) → Roman/Latin (`en` script) - **License:** Apache 2.0 (inherited from Qwen3 base) - **Finetuned from:**`Qwen/Qwen3-4B-Instruct-2507` - **Total parameters:** 4.02B (all trainable) - **Model dtype:** bfloat16 - **Repository:** pavanmantha/qwen3-4b-telugu-transliteration - **Training dataset:** pavanmantha/telugu_transliteration_40k This model is intended for converting **Telugu script text** into its **Roman (Latin alphabet) transliteration**. Useful for: - Search and indexing pipelines that need phonetic normalization - Text-to-speech preprocessing - Keyboard input systems for Telugu speakers - Cross-script NLP research Can be integrated into …

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---

## C50 · 2026-10-03-pretraining-a-4b-model-for-te · Evaluating Model Performance

**Claim** (prose, label: single source):

> The model may poorly handle rare or archaic Telugu vocabulary [E18], and its performance is limited by the fact that it is trained on a single dataset and may not generalize well to specialized domains, such as legal, medical, or technical Telugu [E16].

- **E18** fact: The model may poorly handle rare or archaic Telugu vocabulary.
  - quote: "Rare or archaic Telugu vocabulary may be poorly handled."
  - source: pavanmantha/qwen3-4b-telugu-transliteration · Hugging Face
  - passage: …ining objective is **cross-entropy loss** (on unmasked assistant tokens only). Evaluation loss was tracked every 500 steps via `eval_strategy="steps"`. Additional task-specific metrics (CER, WER, exact match) can be computed post-hoc using the inference snippet above. - The model is trained on a single dataset and may not generalize well to specialized domains (legal, medical, technical Telugu). - Transliteration conventions vary across regions and systems (e.g., ISO 15919 vs. informal conventions); the model reflects the conventions present in the training data. - **>>Rare or archaic Telugu vocabulary may be poorly handled.<<** - The model carries any biases inherent in the underlying Qwen3-4B-Instruct base model. Users should validate outputs against a known-good reference for high-stakes applications. For best results, inputs should be clean, well-formed Telugu script sentences within the general domain of the training data. - **Hardware:** 3× NVIDIA L40S (46 GB each) - **Training time:** ~23.9 minutes (1,433.7 seconds) - **Cloud provider:** Private compute cluster - **Compute region:** India - **Estimated CO₂:** Minimal — single short epoch on 3 GPUs Carbon emissions can be estimated u…

- **E16** fact: The model is trained on a single dataset and may not generalize well to specialized domains.
  - quote: "The model is trained on a single dataset and may not generalize well to specialized domains (legal, medical, technical Telugu)."
  - source: pavanmantha/qwen3-4b-telugu-transliteration · Hugging Face
  - passage: ….42 → 0.62** in the first 350 steps, demonstrating fast and stable convergence for this transliteration task. The validation set consists of 8,723 held-out samples from the same `pavanmantha/telugu_transliteration_40k` dataset, split with `seed=42`. The primary training objective is **cross-entropy loss** (on unmasked assistant tokens only). Evaluation loss was tracked every 500 steps via `eval_strategy="steps"`. Additional task-specific metrics (CER, WER, exact match) can be computed post-hoc using the inference snippet above. - **>>The model is trained on a single dataset and may not generalize well to specialized domains (legal, medical, technical Telugu).<<** - Transliteration conventions vary across regions and systems (e.g., ISO 15919 vs. informal conventions); the model reflects the conventions present in the training data. - Rare or archaic Telugu vocabulary may be poorly handled. - The model carries any biases inherent in the underlying Qwen3-4B-Instruct base model. Users should validate outputs against a known-good reference for high-stakes applications. For best results, inputs should be clean, well-formed Telugu script sentences within the general domain of the training data. -…

Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other

---
