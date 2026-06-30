"""A curated catalogue of spy-genre tropes, drawn from John le Carre, Frederick
Forsyth, and Robert Littell, each with a real example and a fresh-take note.

The structure stage selects from this palette under a guiding principle, never at
random: pick only the tropes that serve THIS story's secret, and use at least one
against the grain (a trope played straight reads as cliche; the craft is in the
selection and the inversion). The catalogue is reference data the model consults;
the chosen tropes are recorded in state (Authored.tropes) so the choice is
auditable.

Each entry: `name`, `what` (one line), `example` (a real scene from a named
novel), and `fresh` (how to use it well or subvert it). The examples are research-
derived; treat them as calibration, not as plot to copy.
"""

from __future__ import annotations

SPY_TROPES: list[dict[str, str]] = [
    # --- Moles, doubles, sleepers ---
    {
        "name": "The mole at the top",
        "what": "A long-buried penetration agent sits at the senior level of the home service; the real enemy is internal.",
        "example": "le Carre, Tinker Tailor Soldier Spy: Bill Haydon feeds Karla via Polyakov (modelled on Kim Philby).",
        "fresh": "Skip the whodunit-among-five shape; let the reader know early and mine the cost of staying silent, or make the mole's treason a sincerely-held rival patriotism so exposure resolves nothing morally.",
    },
    {
        "name": "The double / triple agent",
        "what": "An operative serving two services at once, where who they truly serve is the engine.",
        "example": "le Carre, The Spy Who Came in from the Cold: the op is built so Leamas's 'evidence' clears the British double Mundt and destroys the sincere Fiedler.",
        "fresh": "Resist the final-page reveal of 'true' loyalty; the richer version is an agent for whom the question has stopped having an answer. Show the bookkeeping of running a double (lies kept consistent across two files), not just the gotcha.",
    },
    {
        "name": "The sleeper / long-buried asset",
        "what": "An agent planted years earlier lives an ordinary cover life until activation; the threat is already inside, indistinguishable from a neighbor.",
        "example": "Littell, The Sisters: a deep-cover sleeper living quietly in the US, trained at the Potter's school, waiting to be triggered.",
        "fresh": "Make the cover life real (a marriage, a mortgage he isn't faking) so activation is the tragedy of a built life, and the suspense is whether he has quietly become someone who will refuse.",
    },
    {
        "name": "Intelligence too good to question",
        "what": "A source delivers product so valuable the service stops scrutinizing it; the lack of scrutiny is the vulnerability.",
        "example": "le Carre, Tinker Tailor Soldier Spy: Operation Witchcraft / the 'Merlin' material is prized so highly the Circus protects the very channel Karla is using.",
        "fresh": "Subvert by making the intelligence genuinely accurate, yet catastrophic because trusting perfect truth too completely, or acting on it at the wrong moment, is itself the trap.",
    },
    # --- Deception tradecraft ---
    {
        "name": "The honey trap",
        "what": "Seduction deployed to recruit or compromise a target.",
        "example": "le Carre, Tinker Tailor Soldier Spy: Karla engineers Haydon's affair with Smiley's wife Ann not to recruit but to BLIND Smiley, weaponizing intimacy as misdirection.",
        "fresh": "Drop the femme-fatale cliche; aim the trap at the spymaster's loyalty or ego rather than an asset's appetite, or let it fail because genuine attachment forms.",
    },
    {
        "name": "The dead drop gone wrong",
        "what": "An impersonal hand-off via a hidden site that is blown, missed, or sprung. (Genre staple rather than one canonical scene.)",
        "example": "A pervasive tradecraft set-piece across the Cold War canon; the tension is procedural, not pyrotechnic.",
        "fresh": "Make it fail for a human reason (the asset changed his routine, a stranger pockets the package), not enemy countersurveillance. Or invert: the enemy WANTS it found, turning the site into a disinformation channel.",
    },
    {
        "name": "The cutout / unwitting courier",
        "what": "An intermediary relays between two parties so neither can reach or identify the other.",
        "example": "le Carre, The Russia House: Katya carries the scientist Savelyev's manuscript toward Barley Blair, standing between source and recipient.",
        "fresh": "Promote the cutout to protagonist: the person who carries messages they don't understand bears all the risk and none of the knowledge. The disposable middle is the most exposed link.",
    },
    {
        "name": "The false flag",
        "what": "An operation staged to look like another actor's work, so the target misattributes who runs them. (Verified tradecraft concept; a genre staple.)",
        "example": "Recruitment or sabotage misattributed to a third party; used widely across the tradition.",
        "fresh": "Beyond 'recruited under a false flag, then learns the truth,' try the long con where the asset would have cooperated anyway, making the deception pointless cruelty.",
    },
    {
        "name": "The cover that becomes real",
        "what": "A fabricated identity, relationship, or life starts to supplant the real one.",
        "example": "le Carre, The Spy Who Came in from the Cold: Leamas's cover as a washed-out drunk bleeds into reality, and his real feeling for Liz Gold becomes the flaw the op cannot survive.",
        "fresh": "The danger isn't exposure, it's preferring the lie: make the cover identity happier or kinder than the real person, so the agent grieves the cover when the op ends.",
    },
    {
        "name": "The unstable legend (identity dissolution)",
        "what": "A deep-cover operative's manufactured identities metastasize until even the agent cannot tell which self is real.",
        "example": "Littell, Legends: Martin Odum cannot tell whether he is Odum, Dante Pippen (IRA bombmaker), or Lincoln Dittmann; the 'true' self is the book's mystery.",
        "fresh": "Skip the clinical DID framing; make the ambiguity load-bearing for PLOT (a reveal hinges on which legend remembers a fact the base self never could), resolved by evidence, not diagnosis.",
    },
    # --- The institution ---
    {
        "name": "The bureaucratic betrayal",
        "what": "The real enemy is one's own institution: careerism, turf wars, and committee politics get agents killed.",
        "example": "le Carre, Tinker Tailor Soldier Spy: Alleline's empire-building around Witchcraft is the soil the mole grows in; the Circus's vanity is what Haydon exploits.",
        "fresh": "Show a specific mechanism (a budget line, a reorganization, an interagency credit war) producing a body. It lands hardest when the betrayer is a decent person optimizing a metric, not a villain.",
    },
    {
        "name": "The compromised handler",
        "what": "The case officer running the agent is themselves turned, blackmailed, or working another agenda.",
        "example": "le Carre, The Spy Who Came in from the Cold: Control and the Circus direct Leamas while protecting the very man he is sent to destroy.",
        "fresh": "Make the compromise emotional or financial rather than ideological, and have the handler keep running the agent WELL to assuage guilt; the asset's safety becomes the handler's penance.",
    },
    {
        "name": "The agency as antagonist",
        "what": "The protagonist's own service is the obstacle: it sacrifices, lies to, or hunts its own people for raison d'etat.",
        "example": "Littell, The Amateur: the CIA refuses to pursue Heller's fiancee's killers and then tries to stop and eliminate him.",
        "fresh": "Avoid the single corrupt director; the colder version is emergent betrayal, a sum of reasonable incentives with no one to punish. Let the protagonist find the logic destroying him persuasive.",
    },
    {
        "name": "The committee / war-room scene",
        "what": "Senior officials convene to assess a threat and authorize a response, dramatizing the machinery of the state.",
        "example": "Forsyth, The Devil's Alternative / The Fourth Protocol: interdepartmental crisis conclaves weigh the response to the threat.",
        "fresh": "Make the room itself the antagonist: the right answer is known by minute two, and the scene is watching turf, careerism, and deniability strangle it.",
    },
    {
        "name": "The disgraced insider proven right",
        "what": "A demoted or distrusted professional sees the threat the complacent establishment dismisses, and is vindicated.",
        "example": "Forsyth, The Fourth Protocol: sidelined MI5 officer John Preston, ignored by superiors, uncovers the Soviet bomb plot.",
        "fresh": "Make the establishment's skepticism reasonable on the evidence it had, so being right is partly luck, and let that ambiguity haunt the vindication.",
    },
    # --- People ---
    {
        "name": "The intimate enemy / mirror antagonist",
        "what": "The true adversary is a single opposite-number the protagonist half-admires; the duel is personal and quasi-moral.",
        "example": "le Carre, Smiley's People: Smiley beats Karla only by exploiting Karla's love for his daughter, and feels he has become Karla to do it.",
        "fresh": "Make the win taste like loss; keep the nemesis barely on the page. Subvert by having the protagonist refuse a victory that requires weaponizing his enemy's love.",
    },
    {
        "name": "The morally exhausted spymaster",
        "what": "An aging chess-player runs the human board with weary mastery, having long since traded conscience for the long game.",
        "example": "Littell, The Company: Starik runs the penetration with patient detachment; Angleton mirrors him as the molehunter whose brilliance curdles into paranoia.",
        "fresh": "Don't make him an omniscient puppet-master; show his model of the world quietly diverging from reality, his legendary intuition becoming the flaw the other side exploits. Mastery as a trap.",
    },
    {
        "name": "The lone professional operator",
        "what": "A solitary, hyper-competent specialist executes a long operation through tradecraft and discipline, not a team.",
        "example": "Forsyth, The Day of the Jackal: the unnamed assassin hired by the OAS works alone to plan the killing of de Gaulle.",
        "fresh": "Forsyth's operator is hollow by design; give him one genuine attachment the mission forces him to spend, so competence and cost are weighed in the same scene.",
    },
    {
        "name": "The amateur turned operator",
        "what": "A desk-bound civilian, untrained in fieldcraft, is forced into operational violence and is dangerous because he doesn't follow the rules.",
        "example": "Littell, The Amateur: CIA cryptographer Charlie Heller, his fiancee murdered, blackmails the Agency into training him and goes after her killers.",
        "fresh": "Keep him genuinely bad at the physical craft; let him win through his ACTUAL skill (a code man weaponizes information). His improvisation should horrify the professionals because it's unpredictable, not secretly expert.",
    },
    {
        "name": "The man recalled from the wilderness",
        "what": "An aging, sidelined officer is pulled back for one operation because only he has the memory and the doggedness.",
        "example": "le Carre, Smiley's People: the retired Smiley is quietly brought back after the murder of his old agent to run the Karla case off the books.",
        "fresh": "Resist 'one last job' action energy; make it reluctant and melancholy, partly an old man settling a private account. Subvert by letting his out-of-date methods fail against a faster service.",
    },
    {
        "name": "The handler-protege bond",
        "what": "The deepest relationship is between a trainer and the agent he made, a paternal intimacy the tradecraft forces into betrayal.",
        "example": "Littell, The Sisters: the Potter races to stop the assassin he personally trained once he realizes the man has been activated.",
        "fresh": "Resist sentimental redemption; make the betrayal mutual and bureaucratically banal, both men knowing the bond was always instrumental and grieving a closeness they each half-performed.",
    },
    {
        "name": "The making of the spy (paternal betrayal)",
        "what": "The spy's capacity for deception is traced to a formative, often paternal, betrayal.",
        "example": "le Carre, A Perfect Spy: Magnus Pym is shaped into the perfect double by his conman father Rick; his treason is rooted in a childhood of performance and lies.",
        "fresh": "Avoid 'troubled childhood explains everything.' Use it structurally (a confessional memoir written as the manhunt closes) so past and present indict each other; make the formative betrayal small and ordinary, not operatic.",
    },
    {
        "name": "The defector of uncertain authenticity",
        "what": "Someone crosses over offering secrets; the tension is whether they are genuine, a plant, or a provocation.",
        "example": "The historical Nosenko/Golitsyn problem; a recurring device underpinning many Cold War novels.",
        "fresh": "Don't resolve 'real or fake.' Let the service never resolve it and act anyway, so the institutional paranoia the defector seeds does more damage than any plant could. The uncertainty is permanent and corrosive.",
    },
    # --- Structure, set-piece, ending ---
    {
        "name": "The interrogation / debrief as battlefield",
        "what": "The decisive confrontations are conversations: the slow extraction of truth, where the question is who is really steering.",
        "example": "le Carre, The Spy Who Came in from the Cold: Leamas feeds mostly-true material laced with a planted thread, so the debrief the reader thinks incriminates Mundt actually destroys Fiedler.",
        "fresh": "Write it as a duel of patience where the questioner half-becomes the subject; no torture shortcut. Subvert by having the subject extract a truth from the interrogator he didn't mean to give.",
    },
    {
        "name": "The reveal hidden in plain documents",
        "what": "The crucial secret is buried in mundane paperwork and surfaces through reading rather than action.",
        "example": "le Carre, Tinker Tailor Soldier Spy: the case is built from duty rosters, the Testify file, and Tarr's report, cross-checked until one suspect fits.",
        "fresh": "Plant the load-bearing clue early and dull, so the reader could have caught it; the payoff is recognition, not surprise. Subvert by leaving the document genuinely ambiguous, so the interpretation is a leap that might be wrong.",
    },
    {
        "name": "The procedural set-piece (competence as suspense)",
        "what": "A whole sequence devoted to one technical operation executed step by precise step.",
        "example": "Forsyth, The Day of the Jackal: a gunsmith builds a breakdown sniper rifle concealable in aluminium crutches, walked through in technical detail.",
        "fresh": "Build dread, not a jargon display. Keep one analog step that can only be done in person, so the body is still at risk. The finished instrument becomes a Chekhov object for later.",
    },
    {
        "name": "Documentary realism (real events braided in)",
        "what": "Real institutions, figures, and events are woven into invented plot so the fiction borrows the authority of the record.",
        "example": "Forsyth, The Odessa File: opens on the JFK assassination date and builds on the real ODESSA network and the Egyptian rocket programme.",
        "fresh": "Let the seam become characterization: have a character be wrong about a real event the reader knows the truth of, so realism does plot work rather than set dressing.",
    },
    {
        "name": "The dual-track manhunt",
        "what": "Chapters alternate the operative advancing and the investigator closing; the reader holds both clocks.",
        "example": "Forsyth, The Day of the Jackal: the Jackal's preparations intercut with Detective Lebel's police hunt.",
        "fresh": "Forsyth keeps the tracks ignorant of each other until late; compound the irony by putting them in unwitting contact early (the hunter helps the hunted once, not knowing it).",
    },
    {
        "name": "The single slip that unravels everything",
        "what": "A meticulous operation is undone by one small, plausible human or administrative error, not a heroic intervention.",
        "example": "Forsyth, The Day of the Jackal: the assassin's forged identity is compromised through dogged record cross-checking.",
        "fresh": "Plant the slip early and in plain sight as an apparent STRENGTH (a habit, a courtesy, the operator's one indulgence), so when it is pulled the reader recognizes it as character, not contrivance.",
    },
    {
        "name": "The plot-of-plots (operation behind the operation)",
        "what": "The scheme the reader follows is a wrapper around a second, hidden operation, often run by a faction on one's own side.",
        "example": "Littell, The Sisters: the CIA pair engineer a deception to turn the KGB's own sleeper into the instrument of their privately conceived plot.",
        "fresh": "Don't stack twist on twist; make the inner operation thematically rhyme with the outer one so the reveal recontextualizes rather than merely surprises, and the clues read as ethical in hindsight, not just factual.",
    },
    {
        "name": "Betrayal as the price of love",
        "what": "Personal love and professional loyalty collide, and the human attachment is what breaks or kills the character.",
        "example": "le Carre, The Spy Who Came in from the Cold: Leamas turns back for Liz at the Wall and is shot, choosing the woman over cold survival.",
        "fresh": "Keep love unsentimental and mismatched (the burnt-out spy and the idealistic naif) so the loss reads as waste, not romance. Subvert by making love save a character's soul precisely by ruining his career.",
    },
    {
        "name": "The hollow victory",
        "what": "The mission succeeds but the win is ashes; the cost in lives, loyalty, or the hunter's soul outweighs the gain.",
        "example": "le Carre, Smiley's People: Smiley wins the lifelong duel when Karla crosses to the West, and can only answer 'Did I? Yes... I suppose I did.'",
        "fresh": "Let the win be technically complete and emotionally void, requiring the hunter to use his enemy's exact methods. End on the cost (a ruined source, a dead friend), reported almost in passing. Never let the reader cheer.",
    },
    {
        "name": "The geopolitical macguffin on a clock",
        "what": "The stakes are a concrete strategic object (a weapon, a resource, a treaty clause) whose timeline imposes a hard deadline.",
        "example": "Forsyth, The Fourth Protocol / The Devil's Alternative: a treaty clause, or a hijacked supertanker, forces a decision against a fixed horizon.",
        "fresh": "Tie the clock to something irreversible and mundane (a shipping schedule, a parliamentary recess, a perishable) so the deadline feels like the world's indifference rather than a countdown timer.",
    },
]


def tropes_digest() -> str:
    """A compact text block of the catalogue, for injection into a stage prompt."""
    lines = []
    for t in SPY_TROPES:
        lines.append(
            f"- {t['name']}: {t['what']} Example: {t['example']} Fresh take: {t['fresh']}"
        )
    return "\n".join(lines)
