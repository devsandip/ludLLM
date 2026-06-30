# Cast — Alpha V2

## Review checks

No structural issues found.

## Critique panel

Verdict: **ship**  (lowest dimension 5/5)

| dimension | score | reading | fix |
|---|---|---|---|
| character | 5/5 | The belief states for nearly every character, particularly Sita, Janaki, Fateh, Rudra, and Kaul, are explicitly load-bearing. Their 'knows,' 'does_not_know,' and 'falsely_believes' entries directly drive their motivations, vulnerabilities, and the plot's dramatic irony. For example, Janaki's belief that 'Control is the only honest form of love' and her goal to 'never lose sight of the daughter she gave away' crafts a deeply layered, sympathetic antagonist far removed from cartoon villainy. | While Mira's worldview and role as a 'counter-model' are clear, her specific personal 'wound' is less explicitly stated than the other main characters. Add a brief, concrete detail to her backstory or worldview that establishes the origin of her conviction that 'People are reached, not owned,' rooting it in a personal experience rather than just an abstract principle. For example, 'She learned the hard way that control breaks what it holds, after witnessing a beloved mentor crumble under a handler's possessive grip.' |
| plausibility | 5/5 | The intricate and multi-layered web of character motivations is exceptionally plausible. Janaki leverages both institutional principles (Colonel Kaul's desire for R&AW accountability) and deep personal vulnerabilities (Additional Secretary Sehgal's grievance, Rudra's guilt over Sita) to orchestrate a complex false-flag operation designed to sell TRINETRA. This level of manipulation, using psychologically precise levers and compartmentalized information across a range of players from the institutional to the intimate, is textbook sophisticated tradecraft and human behavior for a high-stakes spy thriller. | For Sita's role, refine 'conditioned R&AW-lineage assassin' to more explicitly separate the program's R&AW origin from her personal conditioning by Fateh's rogue unit. Consider 'assassin conditioned by Fateh's rogue unit, which traces its origin to a sanctioned R&AW program' or similar, to clarify that her direct conditioning isn't a current R&AW mandate. |
| grounding | 5/5 | The belief states across all characters, particularly the nuanced 'falsely_believes' entries for Sita, Janaki, Kaul, Rudra, Mehta, and the Terror Handler, are meticulously consistent with the fact ledger and each character's specific arc of awareness or deception. For example, Janaki's 'falsely_believes' that `f_false_flag_vulnerability` is untraceable perfectly sets up her eventual downfall, contrasting directly with Fateh's 'knows' of that same vulnerability, creating a robust, internally consistent dramatic tension rooted in grounded information. This intricate management of knowledge and ignorance for a large cast is exceptional. | While exceptionally well-grounded, consider a minor refinement to Mira's belief related to `f_mira_limited_hangout`. The fact `f_mira_limited_hangout` describes her *role* as a 'limited hangout' from a narrative perspective. To keep Mira's internal belief distinct from this meta-narrative description, rephrase her belief to directly reflect what *she* knows about the partial truth she delivers (e.g., 'Mira knows that the information she provides to Sita is incomplete regarding Sita's mother') rather than stating she 'knows' the fact `f_mira_limited_hangout` itself. This would enhance the precision of her internal state without altering the plot. |
| originality | 5/5 | The central premise of Janaki, the presumed-dead mother, not only being alive but also having meticulously engineered her daughter Sita's entire existence, including her 'rebellion' and defection, through a global surveillance apparatus (TRINETRA) and a false-flag terror attack as a sales pitch, is profoundly original. This narrative subverts the 'dead parent' trope, the 'trained assassin' trope, and the 'evil mastermind' trope by intertwining them with a twisted, hyper-modern concept of 'control as love' and 'data as power.' The pivot of her company Meridian from a Blackwater-style PMC to a Palantir-esque predictive intelligence firm, directly tying into the real-world evolution of surveillance and the politics of fear (26/11, Pegasus, Aadhaar), provides a brilliant, grounded specificity to this originality. | While Janaki's emotional blind spot ('she cannot model love') is stated, ensure that this isn't just a philosophical flaw but translates into concrete, tactical vulnerabilities in her otherwise perfect machinations. Show how Sita's burgeoning, un-modeled self (or the emotional connections Janaki dismisses) creates genuinely unpredictable 'noise' in Janaki's system, forcing her to improvise in ways that compromise her control and reveal tangible weak points in her 'airtight' operations, rather than just being a philosophical counterpoint. |
| coherence | 5/5 | The core plot mechanism of the false flag operation (f_false_flag) and TRINETRA's vulnerability (f_false_flag_vulnerability) is exceptionally coherent. Janaki's fatal flaw, that she "falsely believes the manufactured retroactive proof is untraceable," perfectly sets up the story's main thread: how "the evidence of TRINETRA's foresight, traced backward, reveals a hand that knew the attack in advance." This provides both a compelling, exploitable vulnerability and a strong character beat for the antagonist's hubris, with no contradictions in the information asymmetry. | While the vulnerability is logically sound, ensure the 'how' of tracing the retroactive proof is made visually or narratively concrete early on. For example, Fateh's recognition of Janaki's tradecraft (f_fateh_recognizes_tradecraft) could specifically refer to unique metadata anomalies or anachronistic data injections that betray the manufactured foresight, giving the audience a tangible, specific element to grasp as 'the thread Sita and Fateh pull' rather than a general concept of 'tracing backward'. |

Highest-leverage fix: While Mira's worldview and role as a 'counter-model' are clear, her specific personal 'wound' is less explicitly stated than the other main characters. Add a brief, concrete detail to her backstory or worldview that establishes the origin of her conviction that 'People are reached, not owned,' rooting it in a personal experience rather than just an abstract principle. For example, 'She learned the hard way that control breaks what it holds, after witnessing a beloved mentor crumble under a handler's possessive grip.'

## Sita  `c_sita`

- role: Codename Alpha; conditioned R&AW-lineage assassin, Fateh's instrument and the protagonist
- provenance: user_locked
- born: 2007
- backstory: Given away as an infant in 2007 after her mother Janaki's staged death, taken by Fateh when the sanctioned program collapsed, and raised in isolation under brutal conditioning as the rogue Alpha unit's weapon. Named for the mother she was taught the enemy murdered. She is a weapon that was never permitted to become a person, and at eighteen she is beginning to suspect it has a self.
- worldview: Reads every room in three fixed channels: lethal threat-geometry first, then break-point profiling, then a suppressed hunger for belonging she distrusts. Believes obedience is identity and that her grief is a debt owed to a dead mother. Spare, flat, tactical, pierced by longing she will not name.

Belief states:
- knows `f_janaki_believed_dead`
- knows `f_sita_biological_daughter`
- does_not_know `f_janaki_alive`
- does_not_know `f_janaki_principal`
- falsely_believes `f_abandonment_made_the_weapon` -> believes: "Believes she was stolen by force as an infant after the enemy murdered her mother, and that Janaki was a victim who would have kept her."
- falsely_believes `f_authored_rebellion` -> believes: "Believes her break from Fateh, her escape, and her march on Lanka are her own free choices, a rebellion she alone authored."
- falsely_believes `f_alpha_rogue_continuation` -> believes: "Believes the unit she serves is a sanctioned arm of the Indian state, not Fateh's disowned, off-books rogue continuation."
- does_not_know `f_first_kill_witness`

## Janaki  `c_janaki`

- role: The architect; presumed-dead R&AW analytic mind, hidden principal of Meridian Risk Group / TRINETRA, Sita's mother
- provenance: user_seed
- born: 1965
- backstory: A formidable R&AW analyst and Fateh's partner in the off-books program Luthra sanctioned. In 2007 she staged her own death and abandoned her infant daughter to make the child worthless as leverage, then vanished abroad to found Meridian as a deniable PMC. She learned the leverage is in data, not soldiers, pivoted to TRINETRA, and built a machine so she would never be blind again, partly to never lose sight of the daughter she gave away.
- worldview: Control is the only honest form of love. The world is unsafe, so safety must be manufactured and sold; certainty is a product and fear is its market. She models every variable and exists to every system as an absence, scrubbing her own traces while harvesting everyone else's. Cold, recursive, sovereign.

Belief states:
- knows `f_janaki_alive`
- knows `f_janaki_principal`
- knows `f_sita_biological_daughter`
- knows `f_abandonment_made_the_weapon`
- falsely_believes `f_janaki_cannot_model_love` -> believes: "Believes she has no blind spot, that her model accounts for every variable including her own feelings toward Sita, whom she treats as just another node."

Belief states in era `e_present`:
- knows `f_authored_rebellion`
- knows `f_sehgal_mole`
- knows `f_rudra_mole`
- knows `f_first_kill_witness`
- knows `f_janaki_watches_sita`
- knows `f_false_flag`
- falsely_believes `f_false_flag_vulnerability` -> believes: "Believes the manufactured retroactive proof is untraceable and leaves no thread back to her hand; treats the operation as airtight."
- knows `f_mehta_front`
- knows `f_trinetra_stalled_sale`
- knows `f_lanka_assault_is_the_trap`
- knows `f_kaul_steered_by_sehgal`
- knows `f_terror_outfit_tool`

## Fateh 'Baba' Singh Lakhawat  `c_fateh`

- role: Handler 'Baba'; founder of the rogue Alpha unit, grey-zone patriot hunting the terror outfit
- provenance: user_locked
- born: 1962
- backstory: Janaki's partner in the original sanctioned program. When she 'died' in 2007 he took the infant Sita and built the present rogue Alpha unit off-books, half as a weapon for the nation and half as Janaki's legacy. He raised and conditioned Sita, who calls him Baba; he is not her father. Hunting the terror outfit decades later, he reads the handling and recognizes Janaki's tradecraft, the ghost in the methodology, and alone realizes she is alive.
- worldview: Love and ownership are the same act. He made a weapon to protect a country and tells himself the cost was necessary. Self-justifying, grand, certain he is the last patriot in a service that has gone soft. Recognition of his old partner breaks him because it indicts everything he built.

Belief states:
- knows `f_sita_biological_daughter`
- knows `f_alpha_rogue_continuation`
- knows `f_luthra_sanctioned_origin`
- does_not_know `f_authored_rebellion`
- does_not_know `f_sehgal_mole`
- does_not_know `f_rudra_mole`
- does_not_know `f_lanka_assault_is_the_trap`

Belief states in era `e_founding`:
- knows `f_janaki_believed_dead`
- does_not_know `f_janaki_alive`
- does_not_know `f_abandonment_made_the_weapon`

Belief states in era `e_present`:
- knows `f_janaki_alive`
- knows `f_fateh_recognizes_tradecraft`
- knows `f_terror_outfit_tool`
- knows `f_false_flag`
- knows `f_false_flag_vulnerability`
- knows `f_abandonment_made_the_weapon`

## Mira  `c_mira`

- role: R&AW field agent under Kaul, sent to turn Sita; the counter-model of connection over control
- provenance: user_locked
- backstory: A genuine R&AW agent recruited for empathy, not violence, and run by Colonel Kaul. Sent to turn the Alpha asset, she offers Sita a real but partial truth, that Fateh weaponized her and her origin is a lie, near the first-half break, and does not fight back when Sita comes to kill her. She does not know Janaki is alive, and never learns she was maneuvered into Sita's path.
- worldview: People are reached, not owned. Where Sita reads a room for exits and break-points, Mira reads it for loneliness and need. Warm, probing, people-first, convinced the answer to a weapon is a witness who sees the person inside it.

Belief states:
- knows `f_janaki_believed_dead`
- does_not_know `f_janaki_alive`
- knows `f_mira_limited_hangout`
- does_not_know `f_janaki_engineered_meeting`
- knows `f_alpha_rogue_continuation`
- knows `f_kaul_moves_to_shut_unit`

## Colonel Vikrant Kaul  `c_kaul`

- role: Chief of R&AW; the accountable institution moving to shut the rogue unit
- provenance: user_locked
- backstory: A good man running deniable ops someone can still answer for. Inheriting Luthra's guilt over the off-books era, he moves to shut down Fateh's unaccountable rogue unit on correct principle and catastrophic timing, never knowing Fateh is the only force hunting the real threat. He is steered onto Fateh by Sehgal, an Additional Secretary he trusts.
- worldview: The state must be answerable or it is just another gang. Restraint is a virtue, not weakness. Ironic, weary, allergic to zealotry; he distrusts men like Fateh precisely because they are sure. His correctness is exactly what the architect needs.

Belief states:
- knows `f_kaul_moves_to_shut_unit`
- knows `f_alpha_rogue_continuation`
- does_not_know `f_janaki_alive`
- does_not_know `f_sehgal_mole`
- falsely_believes `f_kaul_steered_by_sehgal` -> believes: "Believes his case against Fateh's unit rests on his own independent assessment and trusted intelligence, not on Sehgal's deliberate steering."

## Additional Secretary Arvind Sehgal  `c_sehgal`

- role: Additional Secretary, R&AW; Janaki's tasking-desk mole
- provenance: user_seed
- backstory: A senior, embittered careerist turned years ago through grievance and a buried mistake his handler quietly covered. From the Coordination & Tasking Secretariat desk he steers Kaul onto Fateh and places targets into the intelligence stream, including the first-kill lead fed into Fateh's unit. He works only through cutouts and has never met his principal; he does not know it is Janaki, or that she is alive.
- worldview: The service used him up and owes him; treason is just the invoice. Frightened, resentful, telling himself everyone is compromised so his own compromise is ordinary. Pays for safety with his soul, one tasking at a time.

Belief states:
- knows `f_sehgal_mole`
- knows `f_kaul_steered_by_sehgal`
- does_not_know `f_janaki_alive`
- does_not_know `f_janaki_principal`

## Rudra  `c_rudra`

- role: Senior operative in Fateh's unit; Sita's protector-figure and the intimate mole
- provenance: user_seed
- backstory: Ex-special-forces, the unit's senior hand and the closest thing Sita has to a guardian. Turned by Janaki through a moral lever, guilt over what Fateh did to the child, not money. He facilitates Sita's defection and escape believing he is freeing her from a monster, never knowing he is executing the architect's script and serving the very hand that built her cage.
- worldview: Some debts are paid in conscience, not cash. He betrays the only family he has to save the one person in it who never chose this. Guilt-soaked, quiet, convinced for once he is doing the decent thing.

Belief states:
- knows `f_rudra_mole`
- does_not_know `f_janaki_alive`
- does_not_know `f_janaki_principal`
- falsely_believes `f_authored_rebellion` -> believes: "Believes he is freeing Sita of his own moral conviction, springing her from Fateh; does not know the defection is the architect's operation and he is its instrument."

## Julian Mehta  `c_mehta`

- role: Public CEO of Meridian Risk Group; Janaki's controllable front
- provenance: user_seed
- backstory: A charming corporate operator installed as Meridian's plausible face, fronting the TRINETRA pitch to the Indian state. He half-believes he runs the company and cannot bear to look at the half that knows he is a puppet. His exposure as a hollow front is a mid-film reveal that absorbs scrutiny while the real principal stays a name on no filing.
- worldview: Presence is substance; if the room believes you, you are real. Anxious, shallow, terrified of being seen for the nothing behind the smile, so he refuses to see it himself.

Belief states:
- knows `f_trinetra_stalled_sale`
- does_not_know `f_janaki_alive`
- falsely_believes `f_janaki_principal` -> believes: "Believes he is Meridian's true chief executive with no hidden hand above him, and refuses to examine the evidence that he is only a front."

## Salim Reza  `c_terror_handler`

- role: The bought faction handler steering the terror outfit
- provenance: user_seed
- backstory: The single seam between Janaki and the militant network: one faction handler, bought through a cutout, who mounts the attack believing he serves a foreign state's intelligence service. He is real enough to read as a true believer being played, never knowing the operation is a sales pitch and his outfit a demonstration prop. He is the thread Fateh first pulls.
- worldview: The cause is real and the money is just fuel; he tells himself he answers to a sympathetic power, not a corporation. A professional being run, blind to the buyer above his buyer.

Belief states:
- does_not_know `f_false_flag`
- falsely_believes `f_terror_outfit_tool` -> believes: "Believes the money funding the operation comes from a foreign state's intelligence service, not Meridian, and that the attack serves a cause rather than a corporate sales pitch."

## Major Kabir Dhaliwal  `c_kabir`

- role: Major withdrawn to a Himalayan monastery; the man on the far side of Sita's choice
- provenance: user_locked
- backstory: He killed his mentor Luthra to reach a shadowy terrorist group and made peace with the cost, then withdrew to a monastery. Sita and Mira climb to seek him; he is the mirror, the operative already living past the decision Sita faces, and possibly the one man who has seen Meridian from the other end. He gives them what they need, and may have to fight.
- worldview: Some things are done for the greater good and then carried forever in silence. Spare, still, beyond justification; he neither defends nor regrets, he simply lives with it.

Belief states:
- knows `f_kabir_killed_luthra`

## Colonel Sunil Luthra  `c_luthra`

- role: Former Chief of R&AW (deceased); sanctioned the original off-books program
- provenance: user_locked
- born: 1953
- backstory: A clean man with one stain: he sanctioned the off-books program Janaki and Fateh ran, a hard thing done for the nation. He did not foresee the collapse, Janaki's disappearance, or Fateh going rogue with the child. Later killed by his protege Kabir to reach a terrorist group, he does not appear live; he is the conscience the living measure against and the guilt Kaul inherits.
- worldview: The nation sometimes requires sins no clean ledger will admit, and a leader signs for them so no one else has to. Upright, burdened, undone by the one authorization he could not unmake.

Belief states:
- (none)

