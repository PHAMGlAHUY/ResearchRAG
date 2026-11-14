Output2["supports (y)"] --> Output
Output3["Question Answering: Answer Generation"] --> Output
Output4["Fact Verification: Label Generation"] --> Output
Output5["Jeopardy Question Generation: Answer Query"] --> Q_in
Output6["Question Generation"] --> Output
```  
Figure 1: Overview of our approach. We combine a pre-trained retriever (*Query Encoder + Document Index*) with a pre-trained seq2seq model (*Generator*) and fine-tune end-to-end. For query $x$, we use Maximum Inner Product Search (MIPS) to find the top-K documents $z_i$. For final prediction $y$, we treat $z$ as a latent variable and marginalize over seq2seq predictions given different documents.  
but have only explored open-domain extractive question answering. Here, we bring hybrid parametric and non-parametric memory to the “workhorse of NLP,” i.e. sequence-to-sequence (seq2seq) models.