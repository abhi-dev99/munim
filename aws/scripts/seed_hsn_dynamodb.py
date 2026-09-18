"""
One-off seed script -- NOT part of the deployed Lambda. Reads the same
HSN_SAC.xlsx government master data the real backend uses, applies the
exact same chapter-rate + override table as backend/scripts/fix_hsn_rates.py
(so the AWS pipeline's GST rates match the real product's, not a
re-invented guess), and batch-writes every code into munim-hsn-codes.
"""

from decimal import Decimal

import boto3
import openpyxl

XLSX_PATH = r"D:\hackathob\kleos-4.0\backend\HSN_SAC.xlsx"
TABLE_NAME = "munim-hsn-codes"
REGION = "ap-south-1"

# Ported verbatim from backend/scripts/fix_hsn_rates.py -- same official
# GST chapter schedule, so AWS's rate table agrees with the real backend's.
CHAPTER_RATES = {
    0.0: ['01', '02', '05', '07', '08', '09', '10', '11', '12', '13', '14', '23', '26'],
    5.0: ['03', '04', '06', '15', '17', '25', '27', '31', '41', '50', '51', '52', '53', '54', '55', '60', '61', '62', '63', '89'],
    12.0: ['16', '20', '21', '30', '44', '45', '46', '47', '49', '56', '57', '58', '59', '86', '93', '97'],
    18.0: ['18', '19', '22', '28', '29', '32', '33', '34', '35', '36', '37', '38', '39', '40', '42', '43', '48',
           '64', '65', '66', '67', '68', '69', '70', '72', '73', '74', '75', '76', '77', '78', '79', '80', '81',
           '82', '83', '84', '85', '88', '90', '91', '94', '95', '96', '99'],
    28.0: ['24', '92'],
    3.0: ['71'],
}

HSN_OVERRIDES = [
    ('8703', 28.0), ('8704', 28.0), ('8711', 28.0),
    ('2523', 28.0),
    ('8415', 28.0), ('8418', 28.0), ('8450', 28.0),
    ('8517', 12.0),
    ('8541', 12.0),
    ('3004', 5.0), ('3003', 5.0), ('3002', 5.0),
    ('3101', 5.0), ('3102', 5.0), ('3103', 5.0),
    ('7108', 3.0), ('7107', 3.0),
    ('2709', 0.0), ('2710', 0.0),
    ('4901', 0.0), ('4902', 0.0), ('4903', 0.0),
    ('2401', 28.0), ('2402', 28.0), ('2403', 28.0),
    ('2701', 5.0), ('2702', 5.0),
    ('2711', 5.0),
    ('2601', 5.0),
    ('5205', 5.0), ('5206', 5.0),
    ('8601', 5.0), ('8602', 5.0), ('8603', 5.0),
    ('9954', 18.0), ('9963', 18.0), ('9964', 18.0),
    ('9965', 18.0), ('9971', 18.0), ('9972', 18.0),
    ('9973', 18.0), ('9983', 18.0), ('9984', 18.0),
    ('9985', 18.0), ('9986', 0.0), ('9987', 18.0),
    ('9988', 5.0), ('9991', 0.0), ('9992', 0.0),
    ('9993', 5.0), ('9995', 18.0), ('9996', 28.0),
    ('9997', 18.0),
]


def rate_for(hsn_code: str) -> float:
    for prefix, rate in HSN_OVERRIDES:
        if hsn_code.startswith(prefix):
            return rate
    chapter = hsn_code[:2]
    for rate, chapters in CHAPTER_RATES.items():
        if chapter in chapters:
            return rate
    return 18.0  # backend default for anything unmapped


def _clean_description(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def load_codes():
    wb = openpyxl.load_workbook(XLSX_PATH, read_only=True)

    hsn_ws = wb["HSN_MSTR"]
    for code, description in hsn_ws.iter_rows(min_row=2, values_only=True):
        if not code:
            continue
        code = str(code).strip()
        yield code, _clean_description(description)

    sac_ws = wb["SAC_MSTR"]
    for code, description in sac_ws.iter_rows(min_row=2, values_only=True):
        if not code:
            continue
        code = str(code).strip()
        yield code, _clean_description(description)


def main():
    table = boto3.resource("dynamodb", region_name=REGION).Table(TABLE_NAME)

    written = 0
    with table.batch_writer(overwrite_by_pkeys=["hsn_code"]) as batch:
        for code, description in load_codes():
            batch.put_item(Item={
                "hsn_code": code,
                "description": description[:500],
                "gst_rate": Decimal(str(rate_for(code))),
            })
            written += 1
            if written % 2000 == 0:
                print(f"  ...{written} written")

    print(f"Done. Wrote {written} HSN/SAC codes to {TABLE_NAME}.")


if __name__ == "__main__":
    main()
