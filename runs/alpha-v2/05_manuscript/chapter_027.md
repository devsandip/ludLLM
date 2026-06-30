The Wi-Fi card had been physically removed from the laptop with a jeweller's screwdriver three nights ago, and Mira had kept the little screw in a film canister since, the way you keep a tooth. A machine with no way to talk to anyone could not be persuaded to lie about what it held. That was the only kind of witness she trusted now.

The flat belonged to a cousin who taught chemistry in Pune and came to Delhi twice a year. It smelled of naphthalene and old newspaper. She had drawn the curtains against the sodium glare of the colony lane, set the laptop on the dining table on a folded towel so the fan would not whine, and laid out beside it three printed pages and a telephone bill she was using as scratch paper. Forty-one days since the unit had been ordered shut. Eleven since the bomb. Four since the committee had voted the procurement through on the strength of a single, beautiful fact: that the machine had seen the men coming when the state had not.

She had sat in that room when they showed it. She had watched the Additional Secretary, Sehgal, let grief do the arguing for him, his voice low and decent, never once raising the temperature, and she had felt the decision close over the room like water over a dropped stone. Meridian's people had brought a sealed evidentiary annex, and because due diligence was her cover and her habit, she had asked the technical liaison, a tired NIA forensics man named Dalvi who owed her nothing but a cigarette in a stairwell two years ago, for a forensic export of the demonstration object. Metadata only. Chain of custody. Nobody refuses chain of custody; it is the most boring word in the language and it had let her carry the thing out under everyone's nose.

The demonstration had a name. TRINETRA's people called it PROPHET in the deck, with the kind of unembarrassed self-regard that came of never having buried anyone. PROPHET was an entity escalation: a risk score, attached to a node the system had resolved to one of Salim Reza's cut-outs, crossing the action threshold at 02:14 on the ninth of November. The attack was the thirteenth. Four days. The whole sale, the whole shift of the constitutional argument, the whole appetite of a frightened country, balanced on those four days.

She did not doubt the four days. She doubted the architecture under them.

A prediction is not a fact. It is a sum. You feed the machine signals, it correlates them, and out the far end comes a number that means worry. The annex was proud of its signals. It listed three, fused, as the basis of the escalation: an IMSI activation on a clean SIM, a UPI transfer of forty-one thousand rupees routed through a mule account, and a geofence cluster, four handsets surfacing inside two hundred metres of the target over six hours. Three threads. Pull them together and you got a man worth killing on the ninth.

Mira pulled them apart.

She had the telco's CDR for the SIM, because the NIA had subpoenaed it after the fact and Dalvi's export carried the raw record in an annexe nobody had bothered to strip. The SIM, the one PROPHET named as the spine of its inference, had gone live on a tower in Kurla at 19:42 on the eleventh of November. She read it twice. She read the field labels, in case the telco logged activation in some local convention, some offset she did not know. The record was in UTC, with the offset stamped beside it in the same row, the dull honest plus-five-thirty. The eleventh. Not the ninth.

She wrote it on the telephone bill. SIM: 11 Nov. PROPHET: 9 Nov.

The machine had used, to make a prediction on the ninth, a fact that did not enter the world until the eleventh.

She sat back. The fan turned. Somewhere below, a scooter coughed and failed and coughed and caught. Her first instinct was the instinct of a competent person, which is to assume she was the one who had made the error. There were a dozen innocent ways for two timestamps to drift apart. Display time versus storage time. A clock on the ingestion server running fast, never disciplined to a time source. An escalation that had been opened on the ninth as a low score and only updated to threshold later, the dashboard showing you the birth date of the record and dressing it in the latest number. Predictive platforms did that. They lived, the salesmen liked to say, in a state of continuous revision. The score you saw was the score now; the timestamp you saw was the score then; and a careless reader conflated the two.

She was not a careless reader. That was the one thing eighteen years had left her in place of a marriage.

So she did the other two threads, because one anomaly is a mistake and two is a pattern and three is a hand.

The UPI transfer. The annex dated the fused signal to the eighth, a day before escalation, which was at least the right side of the arithmetic. But the National Payments Corporation reference number was in the record, the full string, and the NPCI stamps its own transactions, and that stamp was not the demonstration's to edit. She did not have a back channel into NPCI at midnight in a chemistry teacher's flat. She had the reference string, and the reference string encodes its own date. She decoded it by hand on the telephone bill, the way you do when you cannot trust a tool you did not build. The transaction had cleared on the tenth.

The geofence cluster, the four handsets near the target, was the worst of them. The annex put it on the ninth, the very engine of the escalation, the thing that made a watchlist entry into an alarm. The underlying location records were tower-derived, and the towers logged honestly because no salesman owned them. The cluster had not formed until the afternoon of the twelfth. One day before the bomb. Three days after the machine claimed to have seen it.

She lined the four numbers up on the bill, in her small upright hand, and looked at them for a long time.

PROPHET: 9 Nov.
SIM: 11 Nov.
UPI: 10 Nov.
Cluster: 12 Nov.

The prophecy was older than everything it claimed to have read. The machine had not inferred the attack from the signals. The signals had arrived, obediently, after the verdict was already written, like witnesses turning up to a trial after the sentence had been carried out, to swear to a crime the court had decided in advance.

There was still a clean explanation, and she made herself walk to it because the dirty one was so large she did not yet trust her own wish to believe it. The clean explanation was the continuous-revision story again, scaled up. PROPHET was a living record. It had been opened on the ninth as a thin thing, a node and a low score, and then over the following days the system had hung these signals on it as they came, and the dashboard, in its vanity, showed the opening date and the final dressing as if they were one moment. A sloppy demonstration, not a fraudulent one. Marketing, not murder.

She could kill that explanation. She only needed the bones under the dashboard.

The object store kept a ledger the dashboard could not touch. Every write to the record was a versioned event with its own digest, a hash of the bytes, chained so that no version could be inserted behind another without breaking the chain, the same dull cryptography that let a bank prove you had not edited your own statement. Dalvi's export, God bless his thoroughness and his grudge against people who made him feel stupid, had pulled the version history along with the chain of custody, because that was the part that made it evidence. She had skated past it the first night, taking it for noise. Now she opened it and read from the bottom, from the genesis write, the first time the record PROPHET had ever existed as bytes on a disk.

The genesis hash was timestamped, and the timestamp was disciplined to a hardware time source, because an immutable ledger that lies about when it was written is not immutable, and Meridian's engineers, whatever else they were, were not amateurs. They had built the strongroom honestly. They had only put a forged painting inside it.

PROPHET had first been written at 23:51 on the seventh of November.

The seventh. Two days before its own published birthday of the ninth, which had itself been a lie of convenience. Six days before the bomb. Five days before the cluster that was supposed to have raised the alarm. The record had come into the world fully formed, the node named, the verdict set, on a night when not one of the three signals it cited as its reason yet existed anywhere on earth except inside the head of whoever typed it.

She put her hand flat on the table.

A machine cannot predict the contents of a database that has not been written. There is no model, no foresight, no clever fusion of exhaust that lets a system reason from data three days in its own future. The thing was not a prediction that had got lucky. It was a document, authored in advance, by someone who already knew the SIM that would be activated, the account that would move money, the corner where four phones would gather, the day a bomb would go off, because that someone had arranged all of it. You do not predict a thing you are building. You schedule it. And then, afterward, you point at the schedule and call it prophecy and ask a grieving nation to buy the prophet.

The proof of foresight was the proof of foreknowledge. The evidence that sold the machine was the confession that whoever ran the machine had ordered the dead.

She thought, without wanting to, of the file she had read weeks ago, the classified one, the dead operative's tradecraft she had recognised in Sehgal's handling and in Meridian's structure, the hand that flowed up through Almeida and lost itself above Mauritius into a principal with no name. She had smelled this hand for months and had owned proof of nothing, only a discipline of method she could not point at without sounding like a woman who had stayed too long in the dark. Now she had a number on a telephone bill that said a massacre had been written down before it happened. She still did not have the name. She had the seventh of November. Sometimes that was the longer reach.

She did not sleep. At eight she put the laptop in a cloth bag with a kilo of onions on top of it, took two buses and a cycle-rickshaw she paid in cash, and came to Kaul's office the back way, through the annexe where the air handling was loud enough to drown a quiet conversation.

Kaul heard her out without interrupting, which was how she knew he understood. A man who does not follow you asks questions in the middle. A man who is ahead of you goes still. He stood at the window with his back to her while she laid it down in order, the four signals, the impossible arithmetic, the genesis write on the seventh. He let her finish. He let the silence run past the point of comfort, the way he did in interrogations, except that she was the one in the chair.

"Who has touched this," he said at last. Not a question about the crime. A question about the contagion.

"Dalvi pulled the export. He doesn't know what's in it; he thinks I'm checking provenance for the audit. The numbers are mine. The laptop has no radio in it. Nobody, sir."

"Keep it that way." He turned. He looked older than he had four days ago, which she had thought was not possible. "You understand what you are holding."

"I'm holding the only fact that matters. The machine didn't see the attack. The men who own the machine staged it. We bought a surveillance state, we changed the argument the courts are having about Aadhaar and lawful intercept and every phone in this country, on the strength of a document somebody wrote before the bomb went off."

"I understand the forensics," Kaul said. "I asked whether you understand what you are holding." He came back to the desk and sat, and she saw him choose his next sentence the way a man chooses where to put his weight on bad ice. "Four days ago the procurement carried. The Cabinet Committee. The Prime Minister's office leaned across the table to make sure of it. There are condolence cheques signed. There is a memorial fund with a minister's name on the masthead. The whole apparatus of the country has decided that this machine is the answer to its grief." He folded his hands. "Now you bring me the seventh of November. And what you are asking me to carry to those same people is not that the machine is imperfect. It is that the company we have just handed the keys of the republic to murdered our citizens in order to win the contract, and that they did it past every system I run, and that I, four days ago, recommended we buy it. You are asking the state to indict itself for being the mark."

"I'm asking you to stop it before they're inside the wire."

"They are inside the wire," Kaul said quietly. "That happened on Tuesday."

She had known it walking up the stairs and had refused to know it, and hearing him say it out loud was like having a tooth confirmed by a second dentist. She kept her voice level. "Then we open it. NIA. A real forensic team on that object store, with a warrant, before they have a chance to roll the ledger."

"On what predicate." He said it gently, which was worse than if he had snapped. "Brought by whom. Signed by whom. I shut a rogue unit six weeks ago because I was advised, correctly, that the state could not answer for an unaccountable hand operating off the books. That advice has my signature under it. The man I shut down" he stopped, and she watched something move behind his face that she did not have a name for, and that she filed away "was, it now appears, the only officer in this service who was actually hunting these people. If I reopen this, I am not exposing Meridian. The first body the inquiry finds is mine. The second is yours. We are the two people who can be shown to have known and to have built nothing on it but a private file in a borrowed flat. Meridian will say a disgruntled officer fabricated metadata to discredit a procurement she opposed, and they will have the grieving families and a minister and the whole architecture of the country's relief standing behind them, and they will be believed, because the alternative is too large for anyone in that building to hold in their hands and keep standing."

"So it walks."

"So I cannot move it through the door you are pointing at," Kaul said. "There is a difference. I would like you to believe there is a difference." But he did not promise her another door. He looked at the cloth bag with the onions on top of her witness, and for a moment he was simply a tired man who had given his life to an institution that had just demonstrated, with great courtesy, that it would defend itself before it defended the truth, because to the institution it could not tell the two apart.

She understood then. It arrived not as despair but as a narrowing, the way a corridor narrows and you stop looking at the walls and start looking at the door. The system would not arrest them. The system could not arrest them without arresting itself, and an organism does not do that; it has antibodies against exactly that. Every lawful channel ran uphill into the same closed room, and the room had decided. Sehgal's quiet decency was in that room. The minister's masthead was in that room. Her own loyalty had been in that room for eighteen years, and it had just been shown the exit.

There was one weapon left that did not require the room's permission. Not arrest. Arrest needed a predicate, a signature, a willing state. Exposure needed only a true thing and a way to let go of it. The seventh of November did not have to be admitted into evidence. It had to be made impossible to un-know, dropped into the open square where the country was already arguing about its own phones, where the privacy litigants and the journalists who had carried the Pegasus files and the people who had never wanted their lives fused into one searchable grid were waiting for exactly this and did not know it. You could not indict Meridian. You could make it so that no one would ever again be able to call the machine a prophet without someone, somewhere, saying the seventh.

It would cost her everything she had not already lost. They would say she fabricated it. They would empty her life onto a table and read it aloud. She would never again be a woman the service trusted in a quiet room.

"Sir," she said, standing, lifting the bag, settling the onions over the laptop with a care that was almost tender. "Thank you for your time."

Kaul looked at her, and he was not a stupid man, and she watched him decide not to ask her what she meant to do, because not asking was the last protection he could offer her and the last he could offer himself.

"Mira," he said, as she reached the door. Just her name. A warning, or a blessing, or the sound of a man letting go of a rope he could no longer hold.

She did not turn around. She went down the loud stairwell and out into the white morning, the bag heavy and innocent against her hip, and began, for the first time in her career, to think about how a thing got out instead of how it stayed in.