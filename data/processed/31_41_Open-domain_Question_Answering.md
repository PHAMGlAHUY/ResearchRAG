There are several advantages to generating answers even when it is possible to extract them. Documents with clues about the answer but do not contain the answer verbatim can still contribute towards a correct answer being generated, which is not possible with standard extractive approaches, leading  
Model | NQ | TQA | WQ | CT
Closed Book | T5-11B [52] | 34.5 | - /50.1 | 37.4 | -
T5-11B+SSM[52] | 36.6 | - /60.5 | 44.7 | -
Open Book | REALM [20] | 40.4 | - / - | 40.7 | 46.8
DPR [26] | 41.5 | 57.9/ - | 41.1 | 50.6
| RAG-Token | 44.1 | 55.2/66.1 | 45.5 | 50.0
RAG-Seq. | 44.5 | 56.8/68.0 | 45.2 | 52.2  
Model | Jeopardy | MSMARCO | FVR3 | FVR2
B-1 | QB-1 | R-L | B-1 | Label | Acc.
SotA | - | - | 49.8* | 49.9* | 76.8 | 92.2*
BART | 15.1 | 19.7 | 38.2 | 41.6 | 64.0 | 81.1
RAG-Tok. | 17.3 | 22.2 | 40.1 | 41.5 | 72.5 | 89.5
RAG-Seq. | 14.7 | 21.4 | 40.8 | 44.2