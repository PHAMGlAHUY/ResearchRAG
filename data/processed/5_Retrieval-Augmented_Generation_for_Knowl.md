flow_chart: End-to-End Backprop through q and pθ diagram  
```mermaid
flowchart LR
subgraph Retriever ["Retriever pη (Non-Parametric)"]
direction LR
Q["Query Encoder"]
Q_in["q(x)"]
Q_out["q"]
Q_in --> Q_out
Q_out --> MIPS["MIPS"]
MIPS --> DI["Document Index"]
DI --> d_z["d(z)"]
d_z --> z1["z1"]
d_z --> z2["z2"]
d_z --> z3["z3"]
d_z --> z4["z4"]
end
subgraph Generator ["Generator pθ (Parametric)"]
p_theta["pθ"]
end
Q_in --> Q_out
Q_out --> MIPS
MIPS -.-> DI
DI --> p_theta
p_theta --> Output["This 14th century work is divided into 3 sections: #quot;Inferno#quot;, #quot;Purgatorio#quot; & #quot;Paradiso#quot; (y)"]
Input1["Define #quot;middle ear#quot; (x)"] -.-> Q_in
Input2["Barack Obama was born in Hawaii. (x)"] --> Q_in
Input3["The Divine Comedy (x)"] --> Q_in
Output1["The middle ear includes the tympanic cavity and the three ossicles. (y)"] -.-> Output
Output2["supports (y)"] --> Output
Output3["Question Answering: Answer Generation"] --> Output