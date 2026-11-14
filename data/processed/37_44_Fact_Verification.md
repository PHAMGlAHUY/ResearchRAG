## 4.4 Fact Verification  
Table 2 shows our results on FEVER. For 3-way classification, RAG scores are within 4.3% of state-of-the-art models, which are complex pipeline systems with domain-specific architectures and substantial engineering, trained using intermediate retrieval supervision, which RAG does not require.  
**Document 1**: his works are considered classics of American literature ... His wartime experiences formed the basis for his novel **"A Farewell to Arms"** (1929) ...  
**Document 2**: ... artists of the 1920s "Lost Generation" expatriate community. His debut novel, **"The Sun Also Rises"**, was published in 1926.  
Token | Doc 1 | Doc 2 | Doc 3 | Doc 4 | Doc 5
BOS | 0.05 | 0.00 | 0.00 | 0.00 | 0.00
” | 0.00 | 0.00 | 0.00 | 0.00 | 0.00
The | 0.00 | 0.00 | 0.00 | 0.00 | 0.00
Sun | 0.00 | 0.10 | 0.00 | 0.00 | 0.00
Also | 0.00 | 0.00 | 0.00 | 0.00 | 0.00
R | 0.00 | 0.00 | 0.00 | 0.00 | 0.00
ises | 0.00 | 0.00 | 0.00 | 0.00 | 0.00
” | 0.00 | 0.00 | 0.00 | 0.00 | 0.00