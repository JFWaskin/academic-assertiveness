#!/usr/bin/env python3
"""Regression tests for audit.py. They check detector behaviour and editorial guardrails, not disciplinary accuracy.

POSITIVE  real defensive passages (adapted from a master's-thesis revision) that an editor changed; each must raise a flag.
NEGATIVE  warranted limitations, null results and neutral reporting that must raise no default flag.
Run: python3 test_audit.py
"""
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit  # noqa: E402

POSITIVE = [
    "The framework is thus offered as a testable theoretical model that the present data motivate but do not yet establish.",
    "The recordings are aligned through a shared-clock protocol intended to hold alignment within approximately "
    "20 ms; this is the design intent of the alignment pipeline rather than a separately validated measurement, "
    "and is reported as such.",
    "The contrast is therefore discussed as a hypothesis-consistent pattern, not as a physiological signature of a "
    "verified cognitive mechanism.",
    "This design protects the central N = 40 evidence from pseudo-replication, item confounding, and "
    "over-interpretation of trial-level measures.",
    "Archived diagnostics are not used for primary inference. These boundaries specify where, and how far, the results "
    "can be read.",
    "Two further cross-modal views were inspected and deliberately kept supplementary.",
    "The cross-method reading is therefore the cautious one. Response times and ratings provide converging views.",
    "This reading is intentionally weaker than a causal attention-control claim.",
    "Taken together, the results support a restrained interpretation: reading expertise may involve a more "
    "differentiated relation among fixation, regression, and recall.",
    "That combination is the result this thesis defends, and it is worth stating why it is not a null.",
    "Read against the compression, the defensible inference is that the sample does not separate into levels.",
    "The constraint is not an admission that the framework failed. It is the condition under which the framework claims "
    "are meant to be read.",
    "The chapter therefore closes where the framework began, with a claim it does not overstate.",
    "The thesis has stated the conditions under which the question could be answered rather than answering it.",
    "Its contribution is empirical and bounded: a reproducible record connects response timing and accuracy.",
    "Across the modalities, the study yields a consistent but bounded picture of skill change.",
    "They are intentionally not called causal architecture or synergy.",
    "The distance index provides one useful example.",
    "The results suggest a practical direction rather than a validated intervention.",
    "In sum, the thesis delivers a cautious mixed-methods account of learner behaviour.",
    "Their bounded integration is stronger than either strand alone.",
    "The framework is therefore internally coherent and empirically bounded.",
    "Together, the accuracy and latency summaries are best understood as a reorganisation hypothesis.",
    "Six boundaries keep the discussion proportionate.",
    "The network measure likewise warrants a careful reading.",
    "This study does not attempt to explain neural mechanisms.",
    "The findings may possibly reflect sampling variation.",
    "It should be noted that the sample was small.",
    "To our knowledge, no studies have examined this question.",
    "These correlations conclusively prove the mechanism.",
    "Higher pupil dilation was associated with longer pauses, which shows that load causes hesitation.",
    "This might perhaps suggest that the effect could possibly be larger.",
    "本文并不试图建立因果关系。",
    "值得注意的是，样本量较小。",
    "本研究首次将三种模态整合起来。",
]

NEGATIVE = [
    "We found no statistically detectable difference between groups (p = .18).",
    "The association may reflect unmeasured confounding.",
    "Every participant completed the easy block before the hard block, so difficulty is also confounded with order.",
    "No group contrast survived false-discovery-rate correction (q = .31).",
    "Mean error rate fell from 0.42 in the novice group to 0.11 and 0.05.",
    "On the first block alone the group means rise to 0.71 and 0.69, and the permutation test is not "
    "significant (p = .41).",
    "Participants who read faster recalled fewer details (Spearman rho = -.44).",
    "Eye-tracking metrics enter a session only when calibration error is below 1 degree.",
    "The study lacks stimulated recall and participant-linked quality ratings.",
    "Eighteen of 30 participants improved.",
    "研究结论受到若干条件的限制，每组仅十名被试。",
    "A retrospective report is associated with salience, but it cannot label the cause of a particular pause.",
    "Pioneering think-aloud studies illuminated the strategic, iterative character of translation.",
    "The model makes predictions that a measure-by-measure account does not make.",
    "Multi-rate signals were correlated, but the tools must not turn covariance into a psychological cause.",
    "The reported contrasts do not survive correction at seven participants per cell, so each is carried forward.",
]


def default_flags(text, **kw):
    return audit.scan_text(text, 'case.txt', **kw)


class Recall(unittest.TestCase):
    def test_positive_cases_flagged(self):
        missed = [p for p in POSITIVE if not default_flags(p)]
        self.assertEqual(missed, [], f"{len(missed)} of {len(POSITIVE)} defensive passages not flagged")


class Precision(unittest.TestCase):
    def test_negative_cases_clean(self):
        noisy = {n: [r['category'] for r in default_flags(n)] for n in NEGATIVE}
        noisy = {k: v for k, v in noisy.items() if v}
        self.assertEqual(noisy, {}, "warranted limitation or neutral result flagged")

    def test_negation_rule_is_opt_in(self):
        self.assertFalse(default_flags("The design cannot identify a causal effect."))
        self.assertTrue(default_flags("The design cannot identify a causal effect.", include_negation=True))


class Structural(unittest.TestCase):
    def test_stacked_disclaimers(self):
        para = ("Correlations describe co-variation and do not identify a mental sequence. Granger models do not "
                "establish causation. The interviews cannot label the cause of a pause. Product scores are not "
                "evidence of strategy.")
        self.assertIn('R_REPEATED_DISCLAIMER', [r['category'] for r in default_flags(para)])

    def test_negative_lead(self):
        para = ("This controlled-to-automatic account does not imply that experts dispense with executive "
                "engagement. Research instead motivates a selective account of control.")
        self.assertIn('L_NEGATIVE_LEAD', [r['category'] for r in default_flags(para)])

    def test_hedge_cluster(self):
        s = "These results may suggest that the pattern could plausibly reflect a possible strategy shift."
        self.assertIn('K_HEDGE_CLUSTER', [r['category'] for r in default_flags(s)])

    def test_negated_causal_wording_not_flagged(self):
        s = "The correlation does not show that load causes hesitation in this sample."
        self.assertNotIn('C_CAUSAL_IN_ASSOCIATION', [r['category'] for r in default_flags(s)])

    def test_paragraph_numbers(self):
        rows = default_flags("Neutral first paragraph.\n\nIt should be noted that this is second.")
        self.assertEqual(rows[0]['paragraph'], 2)


class Inputs(unittest.TestCase):
    def _docx(self, body):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            z.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/'
                       'wordprocessingml/2006/main"><w:body>' + body + '</w:body></w:document>')
        f = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
        f.write(buf.getvalue())
        f.close()
        return Path(f.name)

    def test_docx_accepted_view(self):
        path = self._docx('<w:p><w:r><w:t>Results. </w:t></w:r><w:del><w:r><w:delText>It should be noted that x.'
                          '</w:delText></w:r></w:del><w:ins><w:r><w:t>Hopefully this helps.</w:t></w:r></w:ins></w:p>')
        text, _ = audit.load(path)
        self.assertEqual(text, 'Results. Hopefully this helps.')

    def test_docx_reference_list_skipped(self):
        body = ''.join(f'<w:p><w:r><w:t>Body paragraph {i}.</w:t></w:r></w:p>' for i in range(8))
        body += '<w:p><w:r><w:t>References</w:t></w:r></w:p><w:p><w:r><w:t>A novel pioneering study.</w:t></w:r></w:p>'
        text, _ = audit.load(self._docx(body))
        self.assertNotIn('pioneering', text)


if __name__ == '__main__':
    unittest.main(verbosity=1)
