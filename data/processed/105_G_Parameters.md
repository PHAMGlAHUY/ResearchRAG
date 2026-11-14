## **G Parameters**  
Our RAG models contain the trainable parameters for the BERT-base query and document encoder of DPR, with 110M parameters each (although we do not train the document encoder ourselves) and 406M trainable parameters from BART-large, 406M parameters, making a total of 626M trainable  
Table 7: Number of instances in the datasets used. \*A hidden subset of this data is used for evaluation  
<table>
<thead>
<tr>
<th>Task</th>
<th>Train</th>
<th>Development</th>
<th>Test</th>
</tr>
</thead>
<tbody>
<tr>
<td>Natural Questions</td>
<td>79169</td>
<td>8758</td>
<td>3611</td>
</tr>
<tr>
<td>TriviaQA</td>
<td>78786</td>
<td>8838</td>
<td>11314</td>
</tr>
<tr>
<td>WebQuestions</td>
<td>3418</td>
<td>362</td>
<td>2033</td>
</tr>
<tr>
<td>CuratedTrec</td>
<td>635</td>
<td>134</td>
<td>635</td>
</tr>
<tr>
<td>Jeopardy Question Generation</td>
<td>97392</td>
<td>13714</td>
<td>26849</td>
</tr>
<tr>
<td>MS-MARCO</td>
<td>153726</td>
<td>12468</td>
<td>101093*</td>
</tr>
<tr>