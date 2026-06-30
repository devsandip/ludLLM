# Outline — Alpha

## Review checks

4 issue(s) to confirm or fix:

- character 'c_fateh' has era_beliefs for era 'e_inception' but never appears in a chapter placed there - dead intent that is never applied
- character 'c_sehgal' has era_beliefs for era 'e_inception' but never appears in a chapter placed there - dead intent that is never applied
- character 'c_kaul' has era_beliefs for era 'e_inception' but never appears in a chapter placed there - dead intent that is never applied
- character 'c_foreign_principal' has era_beliefs for era 'e_inception' but never appears in a chapter placed there - dead intent that is never applied

## Critique panel

Verdict: **ship**  (lowest dimension 4/5)

| dimension | score | reading | fix |
|---|---|---|---|
| momentum | 5/5 | The outline excels at creating and sustaining momentum, particularly through the relentless, high-impact revelations in Chapters 29-31. The progression from 'the analyst's own name is one Sita half-recognizes' (Ch 29) to the 'home truth: the murdered analyst was Sita's mother' (Ch 30), and culminating in the devastating 'Sita's sanctioned first kill at eighteen was the cover-up of her mother's murder' (Ch 31) creates an explosive, deeply personal escalation of stakes that propels the narrative forward with immense emotional and plot-driven force. This sequence masterfully recontextualizes Sita's entire existence and fuels her motivation. | While the plot moves swiftly through these profound re-contextualizations, ensure that the narrative grants Sita (and by extension, the reader) sufficient internal space—even if just a paragraph of visceral reaction or stunned reflection—for the full emotional weight of these truths to land, rather than immediately pivoting to strategic thinking. This will maximize the shattering impact of the momentum without disrupting the pacing. |
| reveal_craft | 5/5 | The outline demonstrates exceptional reveal craft, with intentional gaps between reader and protagonist knowledge, and meticulously planted clues that pay off dramatically. The entire structure of alternating POV chapters (Janaki in the past, Sita in the present) is designed to create dramatic irony, most powerfully exemplified by the outline's explicit statement in Chapter 21's intent: 'The reader, watching her die for the child with the keepsake, finally connects Janaki to Sita as mother and daughter, fully ahead of Sita. The braid recedes; every present scene is now loaded with irony.' This deliberate management of information for the reader, setting them ahead of the protagonist for crucial emotional and plot reveals (like Sita's true parentage and the recontextualization of her first kill), is a hallmark of superior reveal craft. | In Chapter 9, remove 'f_sita_abducted' from the `reader_reveals` list. While the beat ('Janaki assembles the analog proof while cradling her newborn daughter') and hook ('Unanswered question: how do you hide something so that only your own child could ever find it') expertly foreshadow a separation and danger to the child, explicitly revealing the `f_sita_abducted` fact here diminishes the impact of Mira's reveal to Sita (and thus the reader) in Chapter 11 ('Mira delivers the calibrated partial truth: Sita was abducted, not rescued'). Allowing the reader to infer the child's potential abduction and then confirming it simultaneously with Sita will make the revelation of her compromised origin more impactful for both character and audience. |
| coherence | 4/5 | Chapter 13: "Janaki builds a child's keepsake that secretly carries the route to the analog file, a thing only her grown daughter, with the eye she will inherit, could decode." | Clarify the mechanism of Sita's unique decoding ability by adding a specific, non-mystical component. Instead of solely an 'inherited eye,' suggest that Janaki encoded the keepsake using a pattern or element from Sita's early childhood that only the grown Sita, combining her inherited instinct with her unique experiences, could recognize and unlock. This anchors the 'only she' claim in a more concrete, procedural spy-craft logic. |
| grounding | 4/5 | In Chapter 2, the intent states, 'We learn the world of R&AW's deniable edge,' implying Alpha operates under R&AW's official sanction, yet the fact ledger `f_alpha_rogue` clearly defines Alpha as 'a wholly off-books, unsanctioned assassin unit... with no paper and no accountable owner; if exposed, the state disowns it.' This creates an initial internal inconsistency in Alpha's actual status. | Rephrase the Chapter 2 intent to clarify that the 'deniable edge' is what the characters *believe* or what the *official narrative* is, rather than a direct statement of Alpha's actual sanctioned status, to align with the later reveal that Alpha is truly unsanctioned and rogue. |
| period_authenticity | 5/5 | Chapter 28: "Sita physically retrieves the 2008 analog proof, the one step no machine can do... the safe-deposit box or buried cache opened, microfilm and ledger and cassette carried out by hand, period media untouched by the digital age." | In Chapter 19 (2008, early November), subtly weave in a detail about the specific national security climate of that time. For example, add to Janaki's perspective: "Janaki reads the signs, watchers and silences, and makes her arrangements: the keepsake on the child, the file buried, a last cool calculation against people she cannot name, *even as the daily intelligence briefs hinted at a rising, unnamed storm across the country's western flank.*" This leverages the '2008 Mumbai attacks loom' anchor to deepen the atmosphere of the era. |

Highest-leverage fix: Clarify the mechanism of Sita's unique decoding ability by adding a specific, non-mystical component. Instead of solely an 'inherited eye,' suggest that Janaki encoded the keepsake using a pattern or element from Sita's early childhood that only the grown Sita, combining her inherited instinct with her unique experiences, could recognize and unlock. This anchors the 'only she' claim in a more concrete, procedural spy-craft logic.

| ch | act | era | when | pov | reader reveals | char reveals | beat | hook |
|---|---|---|---|---|---|---|---|---|
| 1 | a1 | e_present | 2026, T-0 | c_sita | - | - | Alpha executes a flawless deniable kill; the weapon works exactly as built. | Tick of the clock: a coded signal from Baba pulls her in for something larger than a single kill. |
| 2 | a1 | e_present | 2026, +2 days | c_sita | f_raw_central,f_restaurant_firstkill | f_restaurant_firstkill | The debrief reveals the scale of Baba's ambition and the depth of Sita's filial bond. | Object lands: Baba unveils the pipeline plan, and Sita is told she is its tip. |
| 3 | a1 | e_inception | 2008, March | c_janaki | f_sleeper_network | f_sleeper_network | Analyst Janaki catches a foreign network at the moment of its inception. | Unanswered question: one routing detail points at a name inside her own service. |
| 4 | a1 | e_present | 2026, +9 days | c_sita | f_golden_crescent_pipeline,f_golden_triangle,f_launder_rails,f_pipeline_seizure,f_drug_justification | f_pipeline_seizure,f_drug_justification | Fateh hijacks the Golden Crescent pipeline, scaling the war chest and setting the bait. | New threat: on exfil Sita clocks surveillance she dismisses as a rival's leak. |
| 5 | a1 | e_present | 2026, +10 days | c_sita | f_alpha_rogue | - | A near-miss shows a hunt closing on Alpha that Sita refuses to see. | Quiet pivot: a woman across the street watches her with the wrong kind of patience. |
| 6 | a1 | e_inception | 2008, May | c_janaki | - | f_sleeper_network | Janaki confirms the penetration is domestic, run by a trusted senior hand. | Reversal: the cleaner she looks for the man, the more the system protects him. |
| 7 | a1 | e_present | 2026, +16 days | c_sita | - | - | A second near-miss; Baba reassures her, and the leash holds. | New threat: the watcher lets herself be seen, an invitation. |
| 8 | a1 | e_present | 2026, +17 days | c_sita | - | f_alpha_rogue | Sita realizes she personally is the quarry, not a stray leak. | Quiet pivot: the watcher leaves a card with no name, only a time. |
| 9 | a1 | e_inception | 2008, July | c_janaki | f_sita_abducted | - | Janaki assembles the analog proof while cradling her newborn daughter. | Unanswered question: how do you hide something so that only your own child could ever find it. |
| 10 | a1 | e_present | 2026, +22 days | c_sita | - | - | Mira makes contact and opens a verbal duel for Sita's trust. | Tick of the clock: Mira says she can prove one thing, if Sita comes back tomorrow. |
| 11 | a1 | e_present | 2026, +22 days (night) | c_sita | - | f_sita_abducted | Mira delivers the calibrated partial truth: Sita was abducted, not rescued. | Reversal: she goes home to Baba and, for the first time, watches him instead of trusting him. |
| 12 | a2 | e_present | 2026, +25 days | c_sita | f_mira_limited_hangout | - | The partial truth takes root; Sita reads her handler for the first time. | Quiet pivot: a discrepancy in Baba's account she cannot un-see. |
| 13 | a2 | e_inception | 2008, September | c_janaki | f_janaki_proof,f_sita_cipher | f_janaki_proof,f_sita_cipher | Janaki encodes the proof's location into the infant's keepsake. | Object lands: she fastens the keepsake to the sleeping child and steps back, finished. |
| 14 | a2 | e_present | 2026, +28 days | c_sita | f_sehgal_loyal_servant | - | The official hunt for Fateh tightens, unknowingly steered from above. | Unanswered question: every break in the case arrives a little too conveniently. |
| 15 | a2 | e_present | 2026, +31 days | c_sita | f_conditioning_trigger | - | A near-miss exposes a buried trigger in Sita's own conditioning. | Quiet pivot: she realizes she may not own her own hands. |
| 16 | a2 | e_inception | 2008, October | c_janaki | f_state_cannot_sanction,f_luthra_burial | f_state_cannot_sanction | Janaki brings the proof to Luthra, who buries it for reasons of state. | Reversal: Luthra orders the file sealed, and Janaki walks out marked without knowing it. |
| 17 | a2 | e_present | 2026, +34 days | c_sita | f_kabir_monastery | - | Sita and Mira set out for the one operative who has walked this road. | Tick of the clock: the network's pipeline is days from full activation behind them. |
| 18 | a2 | e_present | 2026, +36 days | c_sita | - | - | Kabir receives them and refuses easy comfort. | Unanswered question: what did peace cost him, and could Sita pay it. |
| 19 | a2 | e_inception | 2008, early November | c_janaki | - | - | Janaki understands she is going to be killed and secures the child. | Tick of the clock: she sees the car that will be there tomorrow. |
| 20 | a2 | e_present | 2026, +37 days | c_sita | f_luthra_killed_by_kabir | - | Kabir gives them what they need: the courage to look inward, and a method. | Quiet pivot: he tells her the leak is not below her but above everyone. |
| 21 | a2 | e_inception | 2008, mid-November | c_janaki | f_janaki_mother | - | Janaki is murdered in a strike staged to read as enemy action; the infant is taken. | Object lands: the keepsake leaves with the stolen child, and the truth goes into the ground for eighteen years. |
| 22 | a2 | e_present | 2026, +39 days | c_sita | f_fateh_grey | - | Kabir's tell points the rot inward, to the home service itself. | Reversal: the hunter has been hunting at someone else's direction. |
| 23 | a3 | e_present | 2026, +40 days | c_sita | f_pipeline_trap | f_sleeper_network,f_state_cannot_sanction | Midpoint: the hunt turns inward and the activation clock becomes visible at once. | Tick of the clock: the moment Fateh falls, the network activates, and that fall is days away. |
| 24 | a3 | e_present | 2026, +41 days | c_sita | f_alpha_real_target | f_alpha_real_target,f_fateh_grey,f_pipeline_trap | Sita learns Alpha's true target, that Fateh is a grey patriot, and the pipeline is bait. | Reversal: the people hunting Baba are protecting the very thing he is trying to kill. |
| 25 | a3 | e_present | 2026, +42 days | c_sita | - | - | Menon's money trail surfaces a pointer reaching back eighteen years. | Object lands: the keepsake on her wrist suddenly looks like a map. |
| 26 | a3 | e_present | 2026, +43 days | c_sita | - | f_sita_cipher | Sita decodes the keepsake cipher, reading it as only she can. | Unanswered question: who made this for her, and how did they know her eye. |
| 27 | a3 | e_present | 2026, +44 days | c_sita | - | - | The route leads to the exact site where a woman died in 2008. | Quiet pivot: the ground here remembers a death the files called enemy action. |
| 28 | a3 | e_present | 2026, +45 days | c_sita | - | f_janaki_proof | Sita physically retrieves the 2008 analog proof, the one step no machine can do. | Object lands: she holds a dead stranger's evidence and does not yet know it is her mother's. |
| 29 | a3 | e_present | 2026, +45 days (night) | c_sita | - | f_luthra_burial | The proof names the network and the Chief who buried it. | Reversal: the analyst's own name is one Sita half-recognizes. |
| 30 | a3 | e_present | 2026, +46 days | c_sita | f_janaki_mother | f_janaki_mother | Home truth: the murdered analyst was Sita's mother. | Quiet pivot: if her mother was murdered, then someone she has met ordered it. |
| 31 | a3 | e_present | 2026, +46 days | c_sita | f_firstkill_recontext | f_firstkill_recontext | Sita's sanctioned first kill at eighteen was the cover-up of her mother's murder. | Reversal: she was not raised into the work, she was raised to erase her own origin. |
| 32 | a3 | e_present | 2026, +48 days | c_sita | f_decisive_blow,f_false_summit | f_decisive_blow | False summit: the decisive blow appears to land and the case looks won. | Unanswered question: if this is the win, why does the network not flinch. |
| 33 | a3 | e_present | 2026, +48 days (night) | c_sita | f_sehgal_mole | f_false_summit | The false summit collapses, exposing a hand steering the service from inside. | Reversal: the call that wrecked the win came from the highest clean office in the building. |
| 34 | a4 | e_present | 2026, +49 days | c_sita | - | f_mira_limited_hangout | Sita realizes Mira's rescuing truth was itself a limited hangout. | Tick of the clock: the network is already moving to reclaim the pipeline. |
| 35 | a4 | e_present | 2026, +50 days | c_sita | f_fateh_penance,f_fateh_sehgal_irony | f_fateh_penance | Fateh confesses his penance and the irony that defines him. | Quiet pivot: he tells her the only person who can catch the mole is the one he built to see. |
| 36 | a4 | e_present | 2026, +51 days | c_sita | - | f_conditioning_trigger | Under the trigger, the leash breaks; Sita chooses her own hand. | Tick of the clock: free, she turns toward the convergence night. |
| 37 | a4 | e_present | 2026, +52 days (convergence night) | c_sita | - | - | The Lanka sweep springs the trap and the sleeper network exposes itself. | Quiet pivot: amid the chaos one detail in the room is wrong, and only she feels it. |
| 38 | a4 | e_present | 2026, +52 days (night) | c_sita | f_sehgal_tell,f_sehgal_human_crack,f_sita_janaki_gift | f_sehgal_mole,f_sehgal_tell,f_sehgal_human_crack,f_sita_janaki_gift | Sita catches Sehgal's single human tell, the detail no clean officer could know. | Reversal: the most trusted man in the service just told her, without knowing it, that he is the network. |
| 39 | a4 | e_present | 2026, +52 days (late) | c_sita | f_sehgal_turned_1996,f_foreign_principal | f_sehgal_turned_1996,f_foreign_principal | The penetration's age comes clear, and the offscreen principal is felt behind it. | Unanswered question: a mole this old cannot simply be arrested, and the principal will never be touched. |
| 40 | a4 | e_present | 2026, +53 days (dawn) | c_sita | - | f_fateh_sehgal_irony | Fateh dies, vindicated and unforgivable in the same breath. | Quiet pivot: she is the only one who knows he was right. |
| 41 | a4 | e_present | 2026, +54 days | c_sita | - | - | The state cannot sanction the truth, so the mole is managed, not condemned. | Quiet pivot: the system swallows the truth a second time, and lets her live with it. |
| 42 | a4 | e_present | 2026, +56 days | c_sita | f_room_key_bookend | f_room_key_bookend | The room-key bookend closes the circle on her first kill. | Object lands: she sets the key down where it began, and the circle is closed. |
| 43 | a4 | e_present | 2026, +60 days | c_sita | f_ending_residue | f_ending_residue | Vindication without relief; the win is technically complete and emotionally void. | Flat understated final line: the work is done, and she is the only monument her mother will ever have. |

## Information asymmetry (reader vs POV)

- `f_restaurant_firstkill`: reader at ch2, POV at ch2 (gap 0)
- `f_alpha_rogue`: reader at ch5, POV at ch8 (gap 3)
- `f_sita_abducted`: reader at ch9, POV at ch11 (gap 2)
- `f_mira_limited_hangout`: reader at ch12, POV at ch34 (gap 22)
- `f_alpha_real_target`: reader at ch24, POV at ch24 (gap 0)
- `f_fateh_grey`: reader at ch22, POV at ch24 (gap 2)
- `f_sleeper_network`: reader at ch3, POV at ch23 (gap 20)
- `f_decisive_blow`: reader at ch32, POV at ch32 (gap 0)
- `f_pipeline_seizure`: reader at ch4, POV at ch4 (gap 0)
- `f_pipeline_trap`: reader at ch23, POV at ch24 (gap 1)
- `f_state_cannot_sanction`: reader at ch16, POV at ch23 (gap 7)
- `f_drug_justification`: reader at ch4, POV at ch4 (gap 0)
- `f_janaki_mother`: reader at ch21, POV at ch30 (gap 9)
- `f_janaki_proof`: reader at ch13, POV at ch28 (gap 15)
- `f_sita_cipher`: reader at ch13, POV at ch26 (gap 13)
- `f_firstkill_recontext`: reader at ch31, POV at ch31 (gap 0)
- `f_luthra_burial`: reader at ch16, POV at ch29 (gap 13)
- `f_false_summit`: reader at ch32, POV at ch33 (gap 1)
- `f_sehgal_mole`: reader at ch33, POV at ch38 (gap 5)
- `f_sehgal_turned_1996`: reader at ch39, POV at ch39 (gap 0)
- `f_sehgal_human_crack`: reader at ch38, POV at ch38 (gap 0)
- `f_sehgal_tell`: reader at ch38, POV at ch38 (gap 0)
- `f_foreign_principal`: reader at ch39, POV at ch39 (gap 0)
- `f_fateh_penance`: reader at ch35, POV at ch35 (gap 0)
- `f_fateh_sehgal_irony`: reader at ch35, POV at ch40 (gap 5)
- `f_conditioning_trigger`: reader at ch15, POV at ch36 (gap 21)
- `f_sita_janaki_gift`: reader at ch38, POV at ch38 (gap 0)
- `f_room_key_bookend`: reader at ch42, POV at ch42 (gap 0)
- `f_ending_residue`: reader at ch43, POV at ch43 (gap 0)
