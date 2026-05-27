# RAG And Enterprise Document Intelligence Notes

Last updated: May 27, 2026

Source note: these notes are based on the article
"Enterprise Document Intelligence: A Series on Building RAG Brick by Brick, from
Minimal to Corpus scale" by Angela Shi, saved locally from Towards Data Science.

Purpose: capture RAG concepts that go beyond AbhiMart's current small policy-doc
RAG setup, so future stages and interview prep do not reduce RAG to "chunks in a
vector DB."

## 1. Core Lesson

The article's main point:

> Enterprise RAG is not just chunking documents, embedding chunks, retrieving
> top-k, and asking an LLM to answer.

That common recipe works for demos, but often breaks on real enterprise
documents because:

- users do not trust vague answers
- citations are missing or too broad
- retrieval returns passages that are only topically related
- parsing loses tables, sections, line numbers, and cross-references
- teams add more tools before fixing the foundation

The stronger mental model:

```text
RAG quality = document understanding + question understanding + retrieval design
              + grounded generation + citations + evals + auditability
```

Better models can help, but they do not fix bad parsing, weak retrieval, missing
domain vocabulary, or untestable pipelines.

## 2. RAG In The Broad Sense

RAG originally means Retrieval-Augmented Generation:

```text
retrieve relevant external information
give it to the model
generate or extract an answer using that context
```

Today many people use RAG to mean one narrow recipe:

```text
chunk documents
embed chunks
store vectors
embed question
retrieve top-k by cosine similarity
optionally rerank
send context to LLM
```

The article argues that vector search is only one retrieval mechanism. Retrieval
can also mean:

- exact keyword search
- section/table-of-contents navigation
- metadata filtering
- SQL filtering
- expert dictionary lookup
- document type classification
- cross-reference traversal
- full sweeps for listing questions

AbhiMart connection:

Our current RAG is simple on purpose: a small set of policy docs goes into
pgvector, then the agent retrieves relevant chunks. That is fine for Stage 3.
If AbhiMart grows into thousands of mixed PDFs, vector search alone should not
remain the foundation.

## 3. Enterprise RAG Is Often Extraction, Not Creative Writing

In many enterprise workflows, users do not want the LLM to "write something
nice." They want specific values from documents.

Examples:

- insurance coverage amount
- deductible
- effective date
- contract parties
- clauses that survive termination
- warranty period
- refund eligibility condition

This is information extraction. The LLM acts as a structured reader.

Recommended pattern:

```text
Phase 1: retrieve evidence and extract typed facts with citations
Phase 2: optionally write a summary or explanation from those typed facts
```

Why split the phases:

- easier to audit
- easier to test
- easier to identify where the error happened
- reduces hallucinated factual claims

AbhiMart connection:

Our `assess_return_eligibility` tool follows this pattern:

```text
retrieve return policy
classify eligibility with structured output
generate customer-facing response from the decision
```

That is stronger than asking the LLM to free-form answer directly from chunks.

## 4. Augmented vs Grounded

The original RAG term says "augmented." That implies the LLM can combine:

- its internal parametric memory
- retrieved passages

Enterprise systems often need "grounded" behavior instead:

```text
Every factual claim should be backed by retrieved evidence.
```

Allowed:

```text
retrieved text says warranty is 1 year
answer says warranty is 1 year
```

Not allowed:

```text
retrieved text has no warranty date
answer invents a warranty date from model memory
```

The LLM may still use its language ability for:

- grammar
- schema following
- extracting spans
- formatting JSON
- reasoning over retrieved facts

But factual content should come from retrieved evidence.

AbhiMart connection:

This is why policy answers cite source filenames such as:

```text
[Source: return-policy.md]
```

## 5. Long Context Does Not Replace Retrieval

A large context window can hold more text, but it does not solve:

- finding the right document among thousands
- knowing which page supports which answer
- producing line-level citations
- filtering by permissions
- keeping costs predictable

Long context can help after retrieval, but it does not remove the need for
retrieval.

Interview framing:

> Long context increases how much the model can read after selection. Retrieval
> is still the system that selects what deserves to be read.

## 6. The Four-Brick Pipeline

The article proposes four bricks:

```text
1. document parsing
2. question parsing
3. retrieval
4. generation
```

The important idea: every brick should produce structured, inspectable data, not
random strings passed around.

### Brick 1: Document Parsing

Document parsing means converting files into useful structured data.

For PDFs, good parsing may extract:

- page text
- line numbers
- bounding boxes
- tables
- images
- captions
- columns
- table of contents
- section headings
- cross-references

Why it matters:

> Everything lost during parsing is hard or impossible to recover later.

Failure examples:

- table rows get flattened into nonsense text
- page numbers are lost, so citations are vague
- columns are read in the wrong order
- headers/footers pollute retrieval
- section hierarchy disappears

AbhiMart status:

Our docs are simple markdown-like policy docs, so parsing is easy. If we later
add PDFs, parsing becomes a real engineering stage.

### Brick 2: Question Parsing

Question parsing means converting the user question into structured intent.

Example:

```text
Question: What are all clauses that survive termination?
```

Could become:

```text
intent: listing
target: clauses
condition: survive termination
scope: contract
```

Why it matters:

Different question types need different retrieval strategies.

Examples:

- exact value question: find one field
- listing question: sweep all relevant sections
- comparison question: retrieve multiple documents or clauses
- statistical question: use SQL aggregation
- cross-reference question: follow references

AbhiMart status:

We currently rely mostly on the LLM's tool choice and tool prompts. Future
larger RAG could add explicit question parsing before retrieval.

### Brick 3: Retrieval

Retrieval means selecting the evidence the model should use.

The article's strong opinion:

> Embeddings should come late, not first, in many enterprise pipelines.

Retrieval can include:

- document type filtering
- metadata filtering
- section filtering
- keyword search
- expert dictionary lookup
- table-of-contents navigation
- SQL filtering
- vector search
- reranking

AbhiMart status:

Currently:

```text
query -> pgvector similarity search -> top docs -> LLM answer/classifier
```

This is okay for a small policy corpus. At corpus scale, we should add more
structure before vector search.

### Brick 4: Generation

Generation should be controlled.

Instead of:

```text
Here are some chunks. Answer however you want.
```

Prefer:

```text
Here are typed passages and a question.
Return a typed answer with citations.
```

Good generation outputs include:

- answer
- cited source
- cited page/line
- confidence or stance
- missing information
- refusal reason if answer is not supported

AbhiMart status:

Our structured policy classifier is an example of controlled generation.

## 7. What Is A Reranker?

A reranker is a second-stage retrieval model.

The usual pipeline:

```text
First retrieval: get many candidate chunks quickly
Reranker: score those candidates more carefully against the query
Final context: keep the best few
```

Why not use a reranker as the first step?

Rerankers are usually more expensive than simple search. They are designed to
judge a candidate list, not scan an entire corpus.

When a reranker helps:

- first-stage retrieval gives many rough candidates
- candidates are topically close but not equally relevant
- keyword/vector retrieval has decent recall but poor ordering
- there is enough latency budget for another model call

When a reranker may not help:

- parsing is bad
- the right document was never retrieved in the candidate set
- the question requires exact values or negation handling
- domain vocabulary is missing
- structured filters would have solved the problem earlier

Example:

```text
Question: Can I return opened headphones used for a week?
```

Vector search might retrieve return policy chunks. A reranker can reorder them,
but it does not guarantee the final answer applies the "unused/original
condition" correctly. That is a reasoning or policy-decision problem.

AbhiMart status:

We do not currently need a reranker because the policy corpus is small and the
main failure we saw was synthesis, not retrieval. If RAG grows and retrieval
starts returning many noisy candidates, a reranker could be considered.

Interview framing:

> A reranker is useful when first-stage retrieval has high recall but poor
> ranking. It cannot recover evidence that was never retrieved, and it does not
> fix bad parsing or bad reasoning.

## 8. What Is An Expert Dictionary?

An expert dictionary is a curated vocabulary map from domain experts.

It captures terms, synonyms, acronyms, and business-specific meanings.

Example:

```text
"franchise" = "deductible"
"ShieldPro Elite" = "top-tier homeowners plan"
"RMA" = "return merchandise authorization"
```

Why it matters:

Embedding models may not know internal company vocabulary. Experts do.

When it helps:

- internal acronyms
- product names
- policy terms
- synonyms across departments
- spelling variants
- old vs new terminology

AbhiMart possible future:

If our product/policy vocabulary grows, we could maintain a small dictionary:

```text
"refund" -> "return", "money back"
"large appliance" -> "large item shipping"
"MacBook" -> "MacBook Pro 16-inch M3 Max"
```

This could improve question parsing and retrieval before using embeddings.

## 9. What Is Deterministic Dispatch?

Deterministic dispatch means routing a request through explicit code rules
instead of letting an autonomous agent decide everything.

Example:

```text
if question asks for order status:
    require email
    call lookup_order
elif question asks return eligibility:
    call assess_return_eligibility
elif question asks product stock:
    call get_product_info
```

Why it matters:

Deterministic dispatch is easier to:

- audit
- test
- reproduce
- debug
- explain to domain experts

When it is better than an agent:

- regulated workflows
- high-risk document extraction
- fixed business processes
- questions with known intent categories
- strict audit requirements

When agentic routing is acceptable:

- open-ended support chat
- exploratory tasks
- low-risk workflows
- situations where flexibility matters more than reproducibility

AbhiMart status:

We currently use LangGraph agentic tool calling, plus guardrails and evals. That
fits customer support learning. For stricter enterprise document extraction, we
may move more routing into deterministic code.

## 10. What Is An Ontology?

In this article, ontology means a curated relational representation of domain
concepts and their relationships.

It is not necessarily a giant knowledge graph.

Example tables:

- document types
- concept keywords
- concept relationships
- routing rules
- nomenclature mappings

Why it matters:

An ontology lets the system classify, filter, and route before retrieval.

Example:

```text
Question mentions "deductible"
ontology maps deductible -> insurance policy financial terms
dispatcher routes to policy financial clauses
retrieval searches only that section/type
```

When to use it:

- large corpus
- repeated domain-specific questions
- internal terminology
- document types are known
- experts can maintain vocabulary

When not to use it:

- tiny corpus
- no domain experts
- open-domain web QA
- one-off prototype

AbhiMart status:

We do not need a full ontology now. A small expert dictionary or metadata layer
could be enough if the RAG corpus grows.

## 11. What Is A Corpus Index?

A corpus index is structured metadata about the documents in a corpus.

Instead of searching every document directly, first build rows like:

```text
document_id
document_type
product_category
policy_area
effective_date
region
customer_segment
source_path
```

Then retrieval can start with filters:

```sql
WHERE document_type = 'return_policy'
AND product_category = 'electronics'
```

Why it matters:

At corpus scale, naive vector search over every chunk wastes time and retrieves
irrelevant documents.

AbhiMart possible future:

If we add many policy docs, we could index metadata:

```text
source = return-policy.md
policy_area = returns
category = electronics
applies_to = headphones, laptops, accessories
```

Then queries can filter before vector search.

## 12. Listing Questions Need Sweeps, Not Top-K

A listing question asks for all matching items.

Example:

```text
What are all clauses that survive termination?
```

Why top-k fails:

Top-k retrieval returns the most similar few chunks. It does not guarantee
completeness.

Better approach:

```text
identify scope
sweep all relevant sections
extract every matching item
return completeness evidence
```

AbhiMart example:

If a customer asks:

```text
List all return exclusions.
```

A top-3 vector search may miss some exclusions. A better tool would retrieve or
scan the whole return policy section.

## 13. "I Don't Know" Should Be Auditable

The article says a bare "I don't know" is often not enough.

Good absence answer:

```text
I could not find this in the warranty terms. I searched warranty-terms.md and
product-faq.md for laptop accidental damage coverage, but the retrieved sources
only mention manufacturer defects.
```

Why it matters:

Users need to trust not only positive answers but also missing-answer decisions.

AbhiMart future:

For policy questions, we could improve fallback answers by saying:

- which sources were searched
- what was found
- what was missing
- what clarification is needed

## 14. Tables In PDFs Are A Special Problem

PDF tables often break naive RAG.

Failure examples:

- row/column relationships get flattened
- header cells are detached from values
- multi-page tables lose continuity
- units and footnotes are separated

Why this matters:

An LLM cannot reliably answer table questions if parsing destroyed the table
structure.

AbhiMart status:

Current knowledge docs do not require PDF table extraction. If we add invoices,
shipping rate tables, warranty matrices, or compliance PDFs, table parsing
becomes important.

## 15. Evaluation Per Failure Mode

The article argues against one aggregate score.

Bad:

```text
RAG accuracy: 82%
```

Better:

```text
exact value questions: 93%
negation questions: 52%
listing questions: 38%
table questions: 45%
cross-reference questions: 61%
```

Why:

Aggregate scores hide the failures that matter.

AbhiMart connection:

Our evals already follow this direction:

- policy/RAG
- order lookup
- product lookup
- security/privacy
- guardrails
- refund HITL
- structured policy decisions

Future RAG eval categories could include:

- exact policy condition
- negation/exclusion
- listing all exclusions
- citation required
- missing-answer justification
- conflicting policy text

## 16. How This Changes Our AbhiMart Thinking

Current AbhiMart RAG is appropriate because:

- the corpus is small
- documents are clean
- questions are simple customer-support questions
- the main failure was reasoning over retrieved policy, not retrieval

But if the corpus grows, we should not automatically add more vector search
layers. We should first ask:

1. Do we need better parsing?
2. Do we need document metadata?
3. Do we need expert vocabulary?
4. Do we need deterministic question parsing?
5. Do we need SQL filtering before vector retrieval?
6. Is this a listing question where top-k is wrong?
7. Do we need a reranker, or did retrieval fail earlier?
8. Can every factual claim be cited?
9. Can the user audit why no answer was found?

## 17. Interview-Ready Summary

Use this answer if asked what you learned about RAG:

> I learned that RAG is not just putting chunks into a vector database. In
> enterprise systems, the harder problem is making retrieval grounded,
> auditable, and aligned with how domain experts read documents. That means good
> parsing, question parsing, metadata filters, expert vocabulary, citations,
> structured extraction, and evals by failure mode. Vector search and rerankers
> are useful tools, but they should not hide a weak retrieval foundation.

## 18. Quick Vocabulary

| Term | Meaning | When It Matters |
|---|---|---|
| RAG | Retrieve external evidence before answering | When model memory is not enough or not trusted |
| Grounded generation | Factual claims must come from retrieved evidence | Enterprise/policy/legal/finance answers |
| Document parsing | Convert files into structured text/tables/metadata | Any PDF or complex document corpus |
| Question parsing | Convert question into intent/scope/constraints | When questions need different retrieval strategies |
| Vector search | Search by embedding similarity | Fuzzy semantic matching |
| Reranker | Re-score retrieved candidates more carefully | When first retrieval has good recall but poor ordering |
| Expert dictionary | Domain vocabulary and synonym map | Internal acronyms/product/policy language |
| Deterministic dispatcher | Explicit code routes requests to pipelines/tools | Auditable regulated workflows |
| Ontology | Curated map of concepts, terms, and relationships | Large domain-specific corpus |
| Corpus index | Structured metadata table for documents | Filtering before retrieval at scale |
| Listing question | Question asking for all matching items | Top-k retrieval may miss items |
| Audit trail | Evidence of what was searched and why answer was produced | Trust, compliance, debugging |

