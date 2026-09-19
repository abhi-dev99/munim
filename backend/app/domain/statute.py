"""
Munim.ai — Statutory citation registry.

`itc_engine` already decides *what* a verdict is. This module answers the
question a trader actually asks next: **"says who?"**

Every verdict Munim produces is traced back to the clause of the CGST Act,
2017 that produced it, with the operative words of that clause quoted. The
quoted text is stored here, in code, rather than generated — a compliance
product must never let a model recall statute from memory, because a
plausible-sounding section number that does not exist is worse than no
citation at all.

The LLM's only role downstream is to *translate* `plain` into the trader's
language. It is never asked what the law says.

Scope note, stated deliberately: this covers the clauses Munim's engine
actually applies. It is not a GST encyclopaedia, and `cite_for_reason()`
returning None is a correct answer, not a gap to paper over.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Optional

# Public government source. Cited rather than scraped: the Act's text is not
# something this product should be re-hosting or paraphrasing.
_SOURCE = "https://cbic-gst.gov.in/CGST-bill-e.html"


@dataclass(frozen=True)
class Citation:
    code: str           # stable id, safe to store and to key a UI off
    section: str        # human-facing section label
    title: str          # what the clause is about
    quote: str          # the operative words, trimmed but not paraphrased
    plain: str          # what it means for this trader, in one sentence
    fix: Optional[str]  # what, if anything, can be done about it
    source: str = _SOURCE

    def to_dict(self) -> dict:
        return asdict(self)


CITATIONS: dict[str, Citation] = {
    "17_5_blocked": Citation(
        code="17_5_blocked",
        section="Section 17(5), CGST Act 2017",
        title="Blocked credits",
        quote=(
            "Notwithstanding anything contained in sub-section (1) of section 16 "
            "... input tax credit shall not be available in respect of the "
            "following, namely ... motor vehicles for transportation of persons "
            "having approved seating capacity of not more than thirteen persons "
            "... food and beverages, outdoor catering, beauty treatment, health "
            "services ... membership of a club, health and fitness centre ... "
            "goods or services or both used for personal consumption."
        ),
        plain=(
            "The law puts this category of purchase permanently outside input "
            "tax credit. It is not a paperwork problem — no invoice, no filing "
            "and no supplier action makes this claimable."
        ),
        fix=None,
    ),
    "16_2_a_invoice": Citation(
        code="16_2_a_invoice",
        section="Section 16(2)(a), CGST Act 2017",
        title="A valid tax invoice is a precondition",
        quote=(
            "No registered person shall be entitled to the credit of any input "
            "tax in respect of any supply of goods or services or both to him "
            "unless ... he is in possession of a tax invoice or debit note "
            "issued by a supplier registered under this Act."
        ),
        plain=(
            "The document on file is missing something the law requires a tax "
            "invoice to carry, so it cannot support a credit claim as it stands."
        ),
        fix="Ask the supplier to reissue a complete tax invoice.",
    ),
    "16_2_b_receipt": Citation(
        code="16_2_b_receipt",
        section="Section 16(2)(b), CGST Act 2017",
        title="The goods or services must have been received",
        quote="... he has received the goods or services or both.",
        plain=(
            "Credit attaches to a supply that actually happened. An invoice "
            "raised against goods that were never delivered carries no credit."
        ),
        fix="Confirm delivery, or have the supplier issue a credit note.",
    ),
    "16_2_c_supplier_paid": Citation(
        code="16_2_c_supplier_paid",
        section="Section 16(2)(c), CGST Act 2017",
        title="The supplier's tax must actually reach the government",
        quote=(
            "... subject to the provisions of section 41, the tax charged in "
            "respect of such supply has been actually paid to the Government, "
            "either in cash or through utilisation of input tax credit "
            "admissible in respect of the said supply."
        ),
        plain=(
            "This credit depends on a filing somebody else has to make. Until "
            "the supplier reports this invoice in their GSTR-1, the credit is "
            "exposed however correct the trader's own paperwork is."
        ),
        fix=(
            "Chase the supplier before their GSTR-1 for that period is due — "
            "the 11th of the following month."
        ),
    ),
    "16_2_2nd_proviso_180": Citation(
        code="16_2_2nd_proviso_180",
        section="Section 16(2), second proviso, CGST Act 2017",
        title="The 180-day payment rule",
        quote=(
            "Provided further that where a recipient fails to pay to the "
            "supplier of goods or services or both ... the amount towards the "
            "value of supply along with tax payable thereon within a period of "
            "one hundred and eighty days from the date of issue of invoice by "
            "the supplier, an amount equal to the input tax credit availed by "
            "the recipient shall be paid by him along with interest thereon."
        ),
        plain=(
            "If this bill has not been paid within 180 days of its date, credit "
            "already taken has to be reversed with interest. Paying the supplier "
            "restores it."
        ),
        fix="Pay the supplier, or reverse the credit in this period's GSTR-3B.",
    ),
    "16_4_deadline": Citation(
        code="16_4_deadline",
        section="Section 16(4), CGST Act 2017",
        title="The last date to take credit",
        quote=(
            "A registered person shall not be entitled to take input tax credit "
            "in respect of any invoice or debit note for supply of goods or "
            "services or both after the thirtieth day of November following the "
            "end of financial year to which such invoice or debit note pertains, "
            "or furnishing of the relevant annual return, whichever is earlier."
        ),
        plain=(
            "The window for claiming this invoice has closed. Section 16(4) is "
            "an absolute bar — there is no condonation route."
        ),
        fix=None,
    ),
    "16_2_aa_gstr2b": Citation(
        code="16_2_aa_gstr2b",
        section="Section 16(2)(aa), CGST Act 2017",
        title="Credit only on what the supplier has reported",
        quote=(
            "... the details of the invoice or debit note ... has been furnished "
            "by the supplier in the statement of outward supplies and such "
            "details have been communicated to the recipient of such invoice or "
            "debit note in the manner specified under section 37."
        ),
        plain=(
            "The credit legally exists only once the invoice appears in the "
            "trader's GSTR-2B. Holding the paper invoice is no longer enough on "
            "its own."
        ),
        fix="Get the supplier to file, then re-run reconciliation for the period.",
    ),
    "10_composition": Citation(
        code="10_composition",
        section="Section 10(4), CGST Act 2017",
        title="Composition dealers take no credit",
        quote=(
            "A taxable person to whom the provisions of sub-section (1) apply "
            "shall not collect any tax from the recipient on supplies made by "
            "him nor shall he be entitled to any credit of input tax."
        ),
        plain=(
            "A business registered under the composition scheme cannot claim "
            "input tax credit at all. The figure is informational only."
        ),
        fix=None,
    ),
    "9_3_rcm": Citation(
        code="9_3_rcm",
        section="Section 9(3) and 9(4), CGST Act 2017",
        title="Reverse charge",
        quote=(
            "The Government may, on the recommendations of the Council, by "
            "notification, specify categories of supply of goods or services or "
            "both, the tax on which shall be paid on reverse charge basis by the "
            "recipient of such goods or services or both."
        ),
        plain=(
            "On this purchase the trader — not the supplier — owes the tax. Pay "
            "it first; it then becomes claimable as credit."
        ),
        fix="Pay the tax under reverse charge, then claim it in the same return.",
    ),
    "31_invoice_particulars": Citation(
        code="31_invoice_particulars",
        section="Section 31 read with Rule 46, CGST Rules 2017",
        title="What a tax invoice must contain",
        quote=(
            "A tax invoice referred to in section 31 shall be issued by the "
            "registered person containing the following particulars ... name, "
            "address and Goods and Services Tax Identification Number of the "
            "supplier ... HSN code for goods or services ... rate of tax."
        ),
        plain=(
            "A required particular — the supplier's GSTIN, the HSN code or the "
            "rate — is missing or wrong on the face of the invoice."
        ),
        fix="Ask the supplier for a corrected invoice carrying the missing particular.",
    ),
    "36_one_claim_per_invoice": Citation(
        code="36_one_claim_per_invoice",
        section="Rule 36(1), CGST Rules 2017",
        title="Credit is taken once, against one document",
        quote=(
            "The input tax credit shall be availed by a registered person, "
            "including the Input Service Distributor, on the basis of any of "
            "the following documents, namely ... an invoice issued by the "
            "supplier of goods or services or both in accordance with the "
            "provisions of section 31."
        ),
        plain=(
            "The same purchase appears twice. Credit attaches to the document "
            "once, so claiming both would overstate the return."
        ),
        fix="Keep one copy and drop the duplicate before filing.",
    ),
    "37_gstr1_deadline": Citation(
        code="37_gstr1_deadline",
        section="Section 37 read with Rule 59, CGST Rules 2017",
        title="When the supplier has to report the sale",
        quote=(
            "Every registered person ... shall furnish, electronically ... the "
            "details of outward supplies of goods or services or both ... on or "
            "before the eleventh day of the month succeeding the said tax period."
        ),
        plain=(
            "The supplier's own deadline is the 11th of the next month. That "
            "date is the real deadline for chasing them, not the trader's 20th."
        ),
        fix="Contact the supplier before the 11th.",
    ),
}


# Ordered most-specific first: the first pattern that matches wins, so a reason
# mentioning both "GSTR-2B" and "180 days" resolves to the clause the engine
# actually applied rather than to dictionary order.
_PATTERNS: list[tuple[str, str]] = [
    (r"section\s*17\s*\(\s*5\s*\)", "17_5_blocked"),
    (r"180\s*day|second\s+proviso|2nd\s+proviso", "16_2_2nd_proviso_180"),
    (r"section\s*16\s*\(\s*4\s*\)|time limit expired", "16_4_deadline"),
    (r"duplicate", "36_one_claim_per_invoice"),
    (r"not found in gstr-?2b|gstr-?2b not yet available|pending supplier filing", "16_2_aa_gstr2b"),
    # "Supplier non-compliant" is the single most common stored reason in this
    # database and matched nothing until it was added here. The clause is the
    # one that makes a supplier's failure the trader's problem.
    (r"may not have filed|has not filed|supplier filing|supplier non-?compliant", "16_2_c_supplier_paid"),
    (r"composition", "10_composition"),
    (r"reverse charge|\brcm\b", "9_3_rcm"),
    (r"rate mismatch|hsn", "31_invoice_particulars"),
    # A cancelled or invalid supplier GSTIN is not a missing particular on the
    # face of the invoice — it means the issuer is not a registered person, and
    # 16(2)(a) is the clause that makes that fatal.
    (r"cancelled|suspended|invalid or cancelled|could not be verified", "16_2_a_invoice"),
    (r"gstin", "31_invoice_particulars"),
    (r"invalid tax invoice|defective invoice|missing required fields", "16_2_a_invoice"),
    (r"all section 16 conditions met", "16_2_aa_gstr2b"),
]


def lookup(code: str) -> Optional[Citation]:
    """Fetch a citation by its stable code."""
    return CITATIONS.get(code)


def cite_for_reason(reason: Optional[str]) -> Optional[Citation]:
    """
    Resolve one of `itc_engine`'s reason strings to the clause that produced it.

    Returns None when nothing matches. That is deliberate: a wrong section
    number on a compliance screen is a liability, and "no citation" is an
    honest state the UI is built to render.
    """
    if not reason:
        return None
    text = reason.lower()
    for pattern, code in _PATTERNS:
        if re.search(pattern, text):
            return CITATIONS[code]
    return None


def cite_for_status(status: Optional[str]) -> Optional[Citation]:
    """
    Fallback when an invoice carries a verdict but no stored reason — rows
    written before `itc_block_reason` was populated have a status and nothing
    else.
    """
    return {
        "INELIGIBLE": CITATIONS["17_5_blocked"],
        "AT_RISK": CITATIONS["16_2_c_supplier_paid"],
        "FIXABLE_BLOCKED": CITATIONS["16_2_a_invoice"],
        "MISSED": CITATIONS["16_4_deadline"],
        "CONFIRMED": CITATIONS["16_2_aa_gstr2b"],
    }.get((status or "").upper())
