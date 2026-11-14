**Effect of Retrieving more documents** Models are trained with either 5 or 10 retrieved latent documents, and we do not observe significant differences in performance between them. We have the flexibility to adjust the number of retrieved documents at test time, which can affect performance and runtime. Figure 3 (left) shows that retrieving more documents at test time monotonically improves Open-domain QA results for RAG-Sequence, but performance peaks for RAG-Token at 10 retrieved documents. Figure 3 (right) shows that retrieving more documents leads to higher Rouge-L for RAG-Token at the expense of Bleu-1, but the effect is less pronounced for RAG-Sequence.  
K Retrieved Docs | NQ Exact Match
RAG-Tok | RAG-Seq
5 | 40.0 | 39.0
10 | 43.8 | 43.8
20 | 43.5 | 44.1
30 | 43.2 | 44.3
40 | 43.2 | 44.3
50 | 43.1 | 44.4  
K Retrieved Docs | NQ Answer Recall@K
RAG-Tok | RAG-Seq | Fixed DPR | BM25
5 | 50 | 50 | 45 |
10 | 75 | 75 | 70 | 40
20 | 80 | 80 | 77 | 50
30 | 82 | 82 | 79 | 58