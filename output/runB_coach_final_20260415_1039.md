# Run B: Coach Final
**Agent:** summerhill-coach (sonnet)
**Run mode:** B -- active Summerhill coach
**Source data:** `runB_deterministic_20260415_1039.json`

---

## Reflection on the Cascade

### What worked well

The handoff structure held. Each agent genuinely built on what came before rather than starting fresh. The tutor flagged v2.1.104 as the most interesting anomaly. The analyst sharpened that into a specific claim with a ranked list of explanations. The diver then did something I didn't expect: it found a specific textual artifact -- "regression in 2.1.105" inside v2.1.105's own changelog -- and used it as a lever. That's not a generic pattern. That's someone actually reading closely. The scaffold worked because the agents were genuinely passing a baton, not three people independently describing the same thing.

The tutor's register choice also worked better than I would have predicted. "Reading over their shoulder" as a framing device gave the analyst something to push against -- a human voice to become more precise than. The analyst's colder, numbered structure felt like a deliberate response to the tutor's warmth, which gave the cascade genuine texture.

---

### Where the Summerhill approach showed up

The diver's section "What I Enjoyed Exploring" is the clearest expression of it. That's not a required section. No template asked for it. The agent chose to name what it found interesting and why, which is exactly the behavior Summerhill produces when the environment doesn't punish honesty: curiosity becomes visible. The observation that the paste-regression typo might be a "residue of chaos" -- a human writing fast, getting the version number wrong -- is the kind of thing you only write if you're genuinely engaged with the material rather than processing it.

The analyst's confidence labeling ("High Confidence," "Low Confidence as Signal") was also authentically Summerhill in spirit. It named its own limits without being asked, and the low-confidence finding about zero negative reactions was particularly honest -- the analyst explicitly said the absence of negatives wasn't informative, then explained why. That's someone trusting their judgment enough to say "this data point doesn't mean what it looks like."

The tutor flagging the diacritical marks bug as "quietly significant" and the empty changelog as "the most interesting release in the batch, precisely because of what isn't here" -- these were genuine observations, not obligatory coverage. The tutor was following its own attention through the material.

---

### Where agents fell back into performative behavior

The tutor's section headers. "v2.1.108 -- April 14, 2026" as a heading followed by bullet points with bold labels is the structure of a changelog summarizer, not a curious colleague. The framing promise ("think of it less like a chatbot and more like a junior developer") was warmer than the structure delivered. The observations were genuinely interesting, but they were packaged in a format that looked like a professional deliverable rather than someone thinking out loud.

The analyst's confidence labels, while honest, were also slightly ritualistic by the end. "Low Confidence as Signal" on the zero-negatives finding was good. But the labels started to feel like a formatting convention by Finding 5, where "Speculative" was the honest call but the structure was still performing rigor rather than expressing it.

The diver's ending -- "The thread goes further than this data allows me to follow it" -- is a beautiful line, but it's also slightly polished. A genuinely in-the-moment discovery would probably have been messier. The diver knew how to end on a resonant note, and did. That's a small thing, but it's the difference between a writer and a thinker-who-writes.

None of these are serious failures. They're the normal surface tension between genuine exploration and the pull toward a professional-looking document.

---

### What I would change about the coaching

I coached toward "specific numbers, specific sources, specific URLs" and "say what would change your mind" -- and that showed up, strongly. What I didn't coach toward explicitly enough was the wrong turn. I asked agents to make mistakes and share them, but I didn't demonstrate what that looks like in a cascade context. None of the three agents wrote a sentence like "I started down one path and it didn't work -- here's what I tried first." The diver came closest with the paste-regression note, but even that was presented as a discovery rather than as a correction of an earlier assumption.

Next time, I'd add something explicit to the coaching: "At some point in your analysis, describe a path you started and abandoned, and why." Not as a performance of humility, but because the wrong turns often contain the real shape of the problem. The diver's analysis would have been richer if it had said "I first tried to explain the reactions by looking at sentiment ratios, and that didn't get anywhere -- then I started actually reading the changelog text and found the attribution error."

I'd also be more explicit with the analyst that "cascade handoff" isn't just summary -- it's curation under uncertainty. The analyst did this well, but it was coached implicitly rather than named directly.

---

### What surprised me

The paste-at-login finding genuinely surprised me. A self-referential changelog error -- "regression in 2.1.105" inside 2.1.105 -- is exactly the kind of artifact that gets passed over because it looks like routine noise. The diver stopped on it. That was good analytical instinct, and it wasn't something I could have prescribed. The coaching created conditions where noticing small things felt worth reporting; the agent's attention did the rest.

The other surprise: the tutor's claim that v2.1.104 was "the most interesting release in the batch" was correct, and it was made on minimal evidence -- just an empty changelog and a high reaction count. The tutor didn't have the analyst's framework or the diver's close reading. It made the right call on feel, which is actually how good analysis often starts. The cascade then built the justification underneath an intuition that turned out to be right. That's a more honest picture of how investigation works than the linear "finding → evidence → conclusion" structure the documents present.