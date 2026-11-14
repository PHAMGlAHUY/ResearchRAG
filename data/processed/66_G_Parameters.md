## G Parameters  
Our RAG models contain the trainable parameters for the BERT-base query and document encoder of DPR, with 110M parameters each (although we do not train the document encoder ourselves) and 406M trainable parameters from BART-large, 406M parameters, making a total of 626M trainable  
Table 7: Number of instances in the datasets used. \*A hidden subset of this data is used for evaluation  
Task | Train | Development | Test
Natural Questions | 79169 | 8758 | 3611
TriviaQA | 78786 | 8838 | 11314
WebQuestions | 3418 | 362 | 2033
CuratedTrec | 635 | 134 | 635
Jeopardy Question Generation | 97392 | 13714 | 26849
MS-MARCO | 153726 | 12468 | 101093*
FEVER-3-way | 145450 | 10000 | 10000
FEVER-2-way | 96966 | 6666 | 6666