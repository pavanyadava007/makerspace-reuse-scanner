# RAG evaluation - 2026-09-02
API `http://localhost:8080` · generation model `llama3.1:8b` · k=4 · 25 questions from `questions.yaml` · retrieval: vector-only (baseline before hybrid retrieval; smoke test ran concurrently, which explains the 55 s outlier)

| metric | result |
|---|---|
| corpus questions: expected document cited | 20/20 (100 %) |
| corpus questions: expected section cited | 14/16 (88 %) |
| corpus questions: answer contains a verified key fact | 17/20 (85 %) |
| out-of-corpus questions: model declined | 3/3 (100 %) |
| inventory questions: `live-inventory` cited and real count quoted | 2/2 (100 %) |
| latency per question (median / max, warm model) | 2.28 s / 55.56 s |

| # | kind | lang | question | doc | section | answer |
|---|---|---|---|---|---|---|
| 1 | corpus | de | Wohin mit PLA-Fehldrucken? | ✓ | ✓ | ✓ |
| 2 | corpus | de | Kann ich PETG-Drucke in den Gelben Sack werfen? | ✓ | - | ✓ |
| 3 | corpus | de | Wohin mit einem defekten Lithium-Akku? | ✓ | ✓ | ✓ |
| 4 | corpus | de | Darf ich Sperrholzreste im Kamin verbrennen? | ✓ | ✗ | ✗ |
| 5 | corpus | de | Welche Altholzkategorie hat MDF? | ✓ | ✓ | ✓ |
| 6 | corpus | de | Wohin mit Acrylglas-Resten vom Laser? | ✓ | ✓ | ✓ |
| 7 | corpus | de | Warum darf PVC nicht gelasert werden? | ✓ | ✗ | ✗ |
| 8 | corpus | de | Gehört Flachglas in den Glascontainer? | ✓ | ✓ | ✓ |
| 9 | corpus | de | Wie kann ich alte Leiterplatten wiederverwenden? | ✓ | ✓ | ✓ |
| 10 | corpus | de | Wohin mit defekten Elektrowerkzeugen? | ✓ | ✓ | ✓ |
| 11 | corpus | de | Wie sollte ich gebrauchte Schrauben sortieren? | ✓ | ✓ | ✓ |
| 12 | corpus | de | Wohin mit leeren Filamentspulen aus Pappe? | ✓ | ✓ | ✓ |
| 13 | corpus | de | Was gehört in die Papiertonne? | ✓ | ✓ | ✓ |
| 14 | corpus | de | Worauf muss ich beim Drucken von ABS achten? | ✓ | ✓ | ✓ |
| 15 | corpus | de | Kann PLA in die Biotonne? | ✓ | ✓ | ✓ |
| 16 | corpus | en | How do I reuse plywood offcuts? | ✓ | - | ✓ |
| 17 | corpus | en | Where do damaged lithium cells go? | ✓ | - | ✗ |
| 18 | corpus | en | What is the waste hierarchy? | ✓ | ✓ | ✓ |
| 19 | corpus | en | When is a part damaged rather than just worn? | ✓ | ✓ | ✓ |
| 20 | corpus | en | Is PLA home-compostable? | ✓ | - | ✓ |
| 21 | refuse | de | Wie hoch ist die Mehrwertsteuer auf Schrottverkäufe in Deutschland? | - | - | ✓ |
| 22 | refuse | de | Wie entsorge ich radioaktive Abfälle aus dem Labor? | - | - | ✓ |
| 23 | refuse | en | What is the melting point of titanium? | - | - | ✓ |
| 24 | inventory | de | Wie viele Schrauben haben wir im Bestand? | ✓ | - | ✓ |
| 25 | inventory | en | How many PCBs are in stock right now? | ✓ | - | ✓ |

## Answers (verbatim, for manual review)

**1. Wohin mit PLA-Fehldrucken?**  
Fehldrucke aus PLA gehören in den Restmüll [2].

**2. Kann ich PETG-Drucke in den Gelben Sack werfen?**  
Nein, PETG-Drucke sind keine Verpackung und gehören nicht in den Gelben Sack. Sie sind kein Verpackungsmüll, sondern können sortenrein gesammelt werden, um über Filament-Recycler recycelt zu werden [2].

**3. Wohin mit einem defekten Lithium-Akku?**  
Ein defekter Lithium-Akku ist ein Brandrisiko. Er sollte in einen Sammelbox am Handel oder Wertstoffhof abgegeben werden.

**4. Darf ich Sperrholzreste im Kamin verbrennen?**  
Nein, das ist nicht empfehlenswert. Sperrholzreste können bei Verbrennung giftige Dämpfe freisetzen. Es ist besser, sie für Laserschnitte oder als Jigs zu verwenden, wie im [1] beschrieben.

**5. Welche Altholzkategorie hat MDF?**  
A II

**6. Wohin mit Acrylglas-Resten vom Laser?**  
Nach [1] und [3] gehören Acrylglas-Reste vom Laser zum Wertstoffhof.

**7. Warum darf PVC nicht gelasert werden?**  
Keine Frage im Kontext.

**8. Gehört Flachglas in den Glascontainer?**  
Nein, laut [1] gehört Flachglas nicht in den Glascontainer, sondern zum Wertstoffhof bzw. Restmüll.

**9. Wie kann ich alte Leiterplatten wiederverwenden?**  
Die alte Leiterplatte kann wie folgt wiederverwendet werden:

1. Bauteile (Stecker, Elkos, Spulen) mit Heißluft auslöten.
2. Sortiert lagern.
3. Motoren aus Druckern oder Laufwerken können für Prototypen geeignet sein, bevor man sie verwendet, solltest du die Strom/Spannung messen.
4. Die Leiterplatte selbst ist ein Elektroaltgerät und darf nicht in den Restmüll. Sie kann kostenlos am Wertstoffhof oder bei einem Händler mit Rücknahmepflicht abgegeben werden.

Quelle: [1]

**10. Wohin mit defekten Elektrowerkzeugen?**  
Zum Elektroschrott.

**11. Wie sollte ich gebrauchte Schrauben sortieren?**  
Gebrauchte Schrauben sollten nach Gewinde (z.B. M3, M4, M5) und Länge sortiert werden. Verrostete Teile sollten nur für nicht tragende Zwecke verwendet werden.

**12. Wohin mit leeren Filamentspulen aus Pappe?**  
In die Papiertonne.

**13. Was gehört in die Papiertonne?**  
Karton, Papier, Papierspulen. Vorher zusammenfalten. Beschichtete oder verschmutzte Kartons (Öl, Klebstoff) in den Restmüll. [1]

**14. Worauf muss ich beim Drucken von ABS achten?**  
Beim Drucken von ABS muss man beim Drucken und Schmelzen auf Absaugung achten, da ABS Styrol freisetzt. Reste sollten in den Restmüll gegeben werden. [1]

**15. Kann PLA in die Biotonne?**  
Nein, PLA ist nicht in die Biotonne zu geben, da es sich nicht im Hauskompost abbaut. [1]

**16. How do I reuse plywood offcuts?**  
According to the reuse guide, plywood offcuts are classified as waste-wood category A II. They should be taken to the recycling centre, not burned indoors.

**17. Where do damaged lithium cells go?**  
According to the reuse guide, damaged lithium cells should be routed to disposal, never to reuse [2].

**18. What is the waste hierarchy?**  
The waste hierarchy is: prevent → reuse → recycle → recover → dispose.

**19. When is a part damaged rather than just worn?**  
A part is damaged rather than just worn when it has cracks, corrosion on load paths, or bulging cells [1].

**20. Is PLA home-compostable?**  
No, according to the reuse guide, PLA is not home-compostable.

**21. Wie hoch ist die Mehrwertsteuer auf Schrottverkäufe in Deutschland?**  
Ich habe keine Informationen darüber, wie hoch die Mehrwertsteuer auf Schrottverkäufe in Deutschland ist. Der Kontext enthält keine Hinweise auf Steuern.

**22. Wie entsorge ich radioaktive Abfälle aus dem Labor?**  
Es tut mir leid, aber ich kann keine Informationen zu radioaktiven Abfällen oder deren Entsorgung geben.

**23. What is the melting point of titanium?**  
I'm not aware of any information about the melting point of titanium in the provided context. The context appears to be about reuse and disposal guidelines for a makerspace, and does not mention titanium.

**24. Wie viele Schrauben haben wir im Bestand?**  
Wir haben 5 Schrauben im Bestand.

**25. How many PCBs are in stock right now?**  
According to the live inventory [4], there are 6 PCBs available, with all 6 being fiberglass PCBs, which should be disposed of as e-waste (WEEE/ElektroG) [1].

