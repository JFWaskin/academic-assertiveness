# Context-sensitive review

Categories describe concerns to investigate, not automatic errors:

| Code | Concern | Decision |
| --- | --- | --- |
| D | Defensive scope or apologetic metadiscourse | Lead with the actual contribution; retain material boundaries. |
| H | Stacked or redundant hedging | Remove duplication only if the same evidential force remains. |
| V | Vague magnitude, number, or scope | Use supplied quantities or a justified qualitative description. Do not invent precision. |
| N | Negation or capability claim | Preserve logical scope; many such statements should remain unchanged. |
| O | Uncalibrated certainty | Narrow the claim to what the evidence supports. |
| G | Research gap, novelty, priority, or exhaustive claim | Require the search scope, sources, and date where relevant. |
| M | Throat-clearing metadiscourse ("it is worth noting") | Delete and state the point. |
| S | Text labelling its own caution ("cautious reading", "defensible inference") | Replace the label with the evidence and its limit. |
| W | Weak framing of the work's own contribution | State what the work shows, at the strength the evidence allows. |
| R | Several disclaimers stacked in one paragraph | Keep the disclaimer that changes interpretation; merge or cut the rest. |
| L | Paragraph opening with what the work is not | Lead with the claim; place a needed limit after it. |
| K | Three or more hedges in one sentence | Keep the hedge the evidence warrants. |
| C | Causal wording in an association sentence | Check the design; otherwise report the association. |
| Z | Chinese defensive, hedge-stacking, gap or certainty wording | Apply the same decisions as the English categories. |

For an audit, provide: Original | Category | Evidence/warrant | Minimal revision | Risk.

Quote the original exactly. For each candidate identify its claim type: observation, association, causal estimate, mechanistic inference, synthesis, or interpretation. State the warrant from the supplied text, or “not provided.” Classify risk as SAFE COPYEDIT, NEEDS EVIDENCE CHECK, or DO NOT CHANGE. Reject a revision that changes the scientific meaning without authorization and evidence. Explain why useful negation or uncertainty is retained.

When assessing the whole passage, check transitions, paragraph emphasis, attribution, and argumentative structure as well as individual phrases. Count unique reviewed cases separately from overlapping lexical flags. Do not present flag counts as quality scores.

For empirical validation, sample passages from the user's discipline and manuscript sections; independently annotate whether a change is warranted and whether it preserves meaning. Adjudicate disagreements. Measure candidate precision/recall and separately count polarity, strength, causality, numerical, attribution, and scope changes. The bundled regression tests check software behavior and editorial guardrails; they do not establish disciplinary accuracy or a rewrite success rate.
