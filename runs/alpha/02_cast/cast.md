# Cast — Alpha

## Review checks

4 issue(s) to confirm or fix:

- character 'c_fateh' has era_beliefs for era 'e_inception' but never appears in a chapter placed there - dead intent that is never applied
- character 'c_sehgal' has era_beliefs for era 'e_inception' but never appears in a chapter placed there - dead intent that is never applied
- character 'c_kaul' has era_beliefs for era 'e_inception' but never appears in a chapter placed there - dead intent that is never applied
- character 'c_foreign_principal' has era_beliefs for era 'e_inception' but never appears in a chapter placed there - dead intent that is never applied

## Critique panel

Verdict: **ship** (after one auto-revise)  (lowest dimension 3/5)

| dimension | score | reading | fix |
|---|---|---|---|
| character | 5/5 | The character work, particularly for Fateh and Sehgal, exhibits exceptional layering. Fateh's 'Ravana made literal' worldview, where he 'poison[s] his own people to save them' and carries the specific, complex penance of not using Sita's cipher 'because to open that door is to use her on the one thing that is truly hers,' establishes a deeply sympathetic and internally conflicted antagonist. Similarly, Sehgal, the true end-antagonist, is grounded not by cartoon villainy but by an ideological conviction ('Nations are weather; loyalty is to the structure that survives the storm') and a single, specific human fault line ('arranging Janaki's murder... it cost him something he thought himself long past feeling'). Sita's own internal conflict, her 'instinct she distrusts: the snag in a story someone wants left smooth, the buried lie,' further solidifies how specific and load-bearing belief states and wounds are across the cast. | For Sita, clarify how her 'distrust' of her innate instinct for 'the buried lie' actively manifests during her operations. Currently, she is a 'flawless reader... perfect killer' with an instinct she 'distrusts.' To make this internal conflict more immediately load-bearing, show that this distrust doesn't just make the instinct 'dangerous' for her, but actively introduces a momentary hesitation or internal friction she must fight to suppress, subtly degrading the effortlessness of her 'perfection.' |
| plausibility | 3/5 | Sita's backstory states she was "raised in isolation by Fateh into a flawless reader of people and the perfect killer." | Reconcile 'isolation' with 'flawless reader of people.' Instead of complete social isolation, describe a highly controlled, weaponized upbringing that specifically included intensive, curated exposure to social engineering, human psychology, and deception detection exercises (e.g., through role-playing, simulations, or controlled interactions) to develop her 'reading' skills, rather than total social deprivation. True isolation would make her socially inept, not a 'flawless reader.' |
| grounding | 5/5 | The character of Gopal Menon and Fateh's backstory regarding Alpha unit's funding precisely details the use of 'Golden Triangle money,' 'hawala broker,' 'Moreh crossing-master,' and a 'Bangkok trading house' to siphon narcotics proceeds, directly and accurately leveraging the factual grounding provided in `f_golden_triangle` and `f_launder_rails`. | For the character of Gopal Menon, provide a specific 'born' year (e.g., 1965) that aligns with Fateh's backstory of recruiting him 'decades ago,' ensuring his age is consistent with the timeline of operations starting in 2008 and earlier, and completing the grounding of a key functionary. |
| originality | 5/5 | Almost every character description, particularly Sita's 'living cipher and her mother's inherited eye,' Fateh's 'Ravana made literal' worldview, Mira's genuine honesty becoming 'the most effective deception,' and Kabir's backstory as a 'living proof that a person can destroy the one who shaped them and still be right,' takes a strong, specific swing at subverting common spy tropes. | Continue to lean into the highly specific cultural grounding (like the Ravana analogy for Fateh) and the granular, real-world mechanics of intelligence (like Menon's financing methods) throughout the narrative. These details provide crucial texture that elevates the already strong character concepts from 'clever' to 'exceptional' by rooting them in a unique, palpable reality. |
| coherence | 3/5 | Fateh's character is described as 'the deranged patriot who saw clearest' and who 'traced a foreign sleeper network being embedded in India's strategic establishment' 18 years ago. Yet, his initial beliefs state `f_sehgal_mole: 'does_not_know'`, meaning he is unaware of Sehgal, the current, active, highest-level mole who is actively manipulating R&AW to undermine Fateh's operation and who arranged Janaki's murder. This makes Fateh less perceptive than his backstory implies, creating a significant logical gap in his understanding of the ongoing threat. | Adjust Fateh's initial beliefs to reflect that he *suspects* a high-level mole still exists within the establishment, even if he doesn't know their identity or that it is Sehgal. This aligns with his 'saw clearest' attribute and enhances the coherence of his isolated, rogue actions, as he would implicitly trust no one within the official system. |

Highest-leverage fix: Reconcile 'isolation' with 'flawless reader of people.' Instead of complete social isolation, describe a highly controlled, weaponized upbringing that specifically included intensive, curated exposure to social engineering, human psychology, and deception detection exercises (e.g., through role-playing, simulations, or controlled interactions) to develop her 'reading' skills, rather than total social deprivation. True isolation would make her socially inept, not a 'flawless reader.'

## Sita (codename Alpha)  `c_sita`

- role: Protagonist. Deniable assassin of the Alpha unit; abducted as an infant, raised and weaponized by Fateh, whom she calls Baba. The living cipher and her mother's inherited eye.
- provenance: user_locked
- born: 2008
- backstory: Taken as an infant the night her mother Janaki was murdered, raised in isolation by Fateh into a flawless reader of people and the perfect killer. Named, she is told, after a woman Baba admired. On her eighteenth birthday he handed her a hotel room key and she made her first kill without knowing it was the burial of her own origin. The keepsake she has worn against her skin since infancy she believes is just her mother's only gift.
- worldview: Loyalty is the only clean thing; Baba is the one fixed point. Beneath the discipline runs an instinct she distrusts: the snag in a story someone wants left smooth, the buried lie. She is only beginning to suspect that instinct is hers, and that it is the most dangerous thing about her.

Belief states:
- falsely_believes `f_sita_abducted` -> believes: "The enemy murdered her mother and Fateh rescued the orphaned infant; her origin is exactly as Baba has always told it."
- falsely_believes `f_alpha_rogue` -> believes: "Alpha is a sanctioned secret arm of the state, and the killings she carries out are authorized by a nation that needs them."
- knows `f_restaurant_firstkill`
- does_not_know `f_firstkill_recontext`
- does_not_know `f_janaki_mother`
- does_not_know `f_sita_cipher`
- does_not_know `f_conditioning_trigger`
- does_not_know `f_sita_janaki_gift`
- does_not_know `f_alpha_real_target`
- does_not_know `f_fateh_grey`
- does_not_know `f_sehgal_mole`

## Fateh 'Baba' Singh Lakhawat  `c_fateh`

- role: Grey-zone antagonist and deuteragonist. The handler who built and runs the off-books Alpha unit; the deranged patriot who saw clearest.
- provenance: user_locked
- born: 1968
- backstory: Eighteen years ago Fateh traced a foreign sleeper network being embedded in India's strategic establishment, and watched the sanctioned path die when the discovery was buried. He took Janaki's infant daughter, both because she is the key to the hidden proof and because he loved or failed Janaki, and raised her as penance and as a weapon. He never built an empire he owns; he cultivated leverage, a Moreh crossing-master in his debt, a hawala broker he can break, a corrupt diversion here and there, enough to siphon Golden Triangle money for eighteen years without commanding anything. His recent move against the enemy's Golden Crescent pipeline is the same method at scale: not ownership but a chokehold on the men who run it, starving the network and baiting it toward one deniable night, the Lanka sweep.
- worldview: Ravana made literal: poison your own people to save them, choose the smaller atrocity, answer to no one because no one would sign this. He weighs every gram of narcotics against a catastrophe only he can see coming. He has never once reached for the cipher his daughter carries, because to open that door is to use her on the one thing that is truly hers.

Belief states:
- knows `f_alpha_rogue`
- knows `f_fateh_grey`
- knows `f_sleeper_network`
- knows `f_pipeline_seizure`
- knows `f_pipeline_trap`
- knows `f_drug_justification`
- knows `f_state_cannot_sanction`
- knows `f_decisive_blow`
- knows `f_janaki_mother`
- knows `f_janaki_proof`
- knows `f_sita_cipher`
- knows `f_fateh_penance`
- knows `f_sita_abducted`
- knows `f_firstkill_recontext`
- knows `f_conditioning_trigger`
- knows `f_luthra_burial`
- knows `f_foreign_principal`
- does_not_know `f_sehgal_mole`
- does_not_know `f_fateh_sehgal_irony`

Belief states in era `e_inception`:
- does_not_know `f_pipeline_seizure`
- does_not_know `f_pipeline_trap`
- does_not_know `f_decisive_blow`

## Additional Secretary Arvind Sehgal  `c_sehgal`

- role: True end-antagonist. Senior, trusted R&AW figure over clandestine financing and tasking; secretly the foreign principal's deepest penetration of Indian intelligence. The cold mirror to Fateh's heat.
- provenance: user_seed
- born: 1958
- backstory: Recruited roughly thirty years ago in the post-Soviet realignment, Sehgal chose the side he believes endures over the sentimental fiction of nations and never looked back across an impeccable career. He arranged Janaki's murder, dressed as enemy action, when she came too close, and it cost him something he thought himself long past feeling, because he had respected her. Now he uses his control of money and the org chart to bury domestic trails and steer Colonel Kaul, a good man, onto Fateh, knowing that destroying Fateh collapses the lure and saves the network. He cannot pull a trigger; he does not need to. He carries one detail tied to Janaki that no clean officer should know.
- worldview: Nations are weather; loyalty is to the structure that survives the storm. He feels nothing he cannot account for, except the single fault line of Janaki, which he files away and does not examine. He believes his own perfection, which is why he will never see the one reader alive who can catch his single slip.

Belief states:
- knows `f_sehgal_mole`
- knows `f_sehgal_turned_1996`
- knows `f_sehgal_human_crack`
- knows `f_sehgal_tell`
- knows `f_foreign_principal`
- knows `f_sleeper_network`
- knows `f_alpha_rogue`
- knows `f_fateh_grey`
- knows `f_pipeline_seizure`
- knows `f_pipeline_trap`
- knows `f_decisive_blow`
- knows `f_state_cannot_sanction`
- knows `f_false_summit`
- knows `f_luthra_burial`
- falsely_believes `f_janaki_proof` -> believes: "Janaki's proof died with her; nothing she hid survived, and no evidence remains anywhere that can name him."
- does_not_know `f_janaki_mother`
- does_not_know `f_sita_cipher`

Belief states in era `e_inception`:
- does_not_know `f_pipeline_seizure`
- does_not_know `f_pipeline_trap`
- does_not_know `f_alpha_rogue`
- does_not_know `f_decisive_blow`
- does_not_know `f_false_summit`

## Mira  `c_mira`

- role: Co-lead and deuteragonist. R&AW field agent run by Kaul, sent to turn Sita with a calibrated partial truth. Genuine, compassionate, unwitting; not a mole.
- provenance: user_locked
- born: 1998
- backstory: A field officer whose real gift is seeing the person inside the asset, which is exactly why Kaul sends her to flip Sita rather than break her. She carries the truth she was given, that Fateh stole and weaponized this woman, and she delivers it not to win but because she believes Sita deserves to know it. When Sita is sent to kill her, she does not fight; she asks to be heard. She does not know her truth is only the top layer of a much deeper lie.
- worldview: People are not their files. Compassion is a method, not a weakness, and the kindest thing you can do to a weapon is show it the hand that forged it. She trusts that the truth she carries is the whole truth, which makes her honesty the most effective deception in the book.

Belief states:
- falsely_believes `f_mira_limited_hangout` -> believes: "The truth she gives Sita, that Fateh stole and weaponized her, is the complete truth of Sita's origin; there is nothing deeper beneath it."
- knows `f_sita_abducted`
- knows `f_alpha_rogue`
- does_not_know `f_fateh_grey`
- does_not_know `f_alpha_real_target`
- does_not_know `f_janaki_mother`
- does_not_know `f_sehgal_mole`

## Colonel Vikrant Kaul  `c_kaul`

- role: Pillar. Chief of R&AW, running sanctioned but deniable operations that always keep an accountable owner. The good man whose correctness is steered onto the wrong target.
- provenance: user_locked
- born: 1962
- backstory: A career officer who rose by insisting that a service is not a death squad, that every deniable operation must keep someone who can answer for it. When the trails point at Fateh's ownerless rogue unit, everything in his training and conscience agrees: this is the threat, this must be shut down. He trusts Sehgal completely, the way the whole building does, and that trust is the lever the rot uses. His instinct is right about the principle and catastrophically wrong about the target.
- worldview: Accountability is the line between a state and its enemies; an operation no one will sign is an operation that has already gone rotten. His virtue is real and it is precisely what is turned against the country, because stopping the patriot is exactly what the enemy needs.

Belief states:
- falsely_believes `f_fateh_grey` -> believes: "Fateh is a deranged rogue running an unaccountable death squad and is the principal threat to the nation; nothing he is doing serves the country."
- knows `f_alpha_rogue`
- knows `f_sehgal_loyal_servant`
- knows `f_state_cannot_sanction`
- does_not_know `f_false_summit`
- does_not_know `f_sehgal_mole`

Belief states in era `e_inception`:
- does_not_know `f_fateh_grey`

## Janaki  `c_janaki`

- role: Pillar (Inception era). R&AW analyst, Sita's mother. The conscience who found the truth and was murdered for it.
- provenance: user_locked
- born: 1978
- backstory: An analyst with an unteachable instinct for the thread someone wants left alone, Janaki detected the foreign network at its inception and followed it to evidence implicating a senior insider. She refused to bury it; when the institution buried it for her and left her exposed, she hid the proof, a dead-drop ledger and a recording at a locatable site, and encoded its location into the only keepsake she could leave with her infant daughter. Then she was killed, in a murder staged to read as enemy action. Her gift went into her child.
- worldview: The truth is a duty, not a transaction; a lie left alone metastasizes. She believed the institution would eventually be worth the proof she died protecting, a faith the book never quite rewards.

Belief states:
- knows `f_sleeper_network`
- knows `f_janaki_proof`
- knows `f_sita_cipher`
- knows `f_janaki_mother`
- knows `f_sehgal_mole`
- knows `f_foreign_principal`
- knows `f_luthra_burial`

## Colonel Sunil Luthra  `c_luthra`

- role: Pillar (Inception era; deceased by the present). Former Chief of R&AW who buried Janaki's discovery for reasons of state. Later killed by his protege Kabir (canon).
- provenance: user_locked
- born: 1955
- backstory: A good man and a Chief who made the institution's oldest mistake: he judged that surfacing Janaki's discovery would blow live operations or trigger a worse crisis, and he buried it. The burial left Janaki exposed and convinced Fateh the sanctioned path was dead, which birthed Alpha. His sin is concealment, not murder, and not the sanctioning of any death squad. Years later he died at the hands of his protege Kabir, at peace with it, to buy Kabir access to a terrorist group.
- worldview: The state survives on the secrets its servants agree to keep; sometimes the truth costs more than the lie. He carried that arithmetic to his grave, never knowing the insider his silence protected.

Belief states:
- knows `f_luthra_burial`
- knows `f_sleeper_network`
- does_not_know `f_janaki_proof`
- does_not_know `f_sehgal_mole`

## The Foreign Principal  `c_foreign_principal`

- role: Pillar, kept wholly offscreen. The shadow spymaster who runs the sleeper network, the original Golden Crescent pipeline, and Sehgal as his deepest asset. Felt through Sehgal, never seen, never given a monologue.
- provenance: user_seed
- born: 1950
- backstory: Across two decades he embedded deep-cover assets inside India's missile and nuclear command and cyber establishment, patient toward a single coordinated sabotage-plus-false-flag blow timed to a moment of crisis. He turned Sehgal thirty years ago and has run him through deniable tradecraft ever since. When Fateh seized his pipeline, he made the cleanest move available: not to walk into the trap but to have India's own service destroy the man who set it.
- worldview: Reach without a face; the longest game wins. He must never appear on the page, only be inferred through the precision of what Sehgal does.

Belief states:
- knows `f_foreign_principal`
- knows `f_sleeper_network`
- knows `f_sehgal_mole`
- knows `f_decisive_blow`
- knows `f_pipeline_trap`

Belief states in era `e_inception`:
- does_not_know `f_decisive_blow`
- does_not_know `f_pipeline_trap`

## Major Kabir Dhaliwal  `c_kabir`

- role: Functionary (cameo). The universe's foremost operative, sought at a remote Himalayan monastery; the mirror who already killed his own father-figure for the greater good and made peace with it. Gives Sita and Mira what they need.
- provenance: user_locked
- born: 1975
- backstory: A legend in retreat, found at the monastery, who once killed his mentor Luthra to penetrate a terrorist group and carries that choice without flinching. He is the living proof that a person can destroy the one who shaped them and still be right, and survive it.
- worldview: The work asks for the unforgivable thing; you do it and you live with it. He offers Sita not absolution but a map of how to carry what is coming.

Belief states:
- (none)

## Gopal Menon  `c_gopal_menon`

- role: Functionary. Fateh's financial cutout: a soft-spoken chartered-accountant-turned-launderer who holds the hawala and trade-laundering relationships and the specific leverage points that let Alpha siphon narcotics money without owning a thing.
- provenance: invented
- backstory: Recruited by Fateh decades ago over a debt he could never repay, Menon is the human ledger of Alpha's funding: the broker in Dubai, the crossing-master at Moreh, the diversion through a Bangkok trading house. He owns nothing and controls everything that matters, which is precisely how Fateh keeps a private war funded without a footprint.
- worldview: Money is just a story everyone agrees to believe; he keeps the story straight. He asks no questions about where the orders point, which is the only way to stay alive this close to Baba.

Belief states:
- (none)

