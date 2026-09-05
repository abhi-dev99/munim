from PIL import Image, ImageDraw, ImageFont

# Create a white image
img = Image.new('RGB', (800, 1000), color = (255, 255, 255))
d = ImageDraw.Draw(img)

# Try to use a default font or fall back
try:
    font_title = ImageFont.truetype('arial.ttf', 40)
    font_bold = ImageFont.truetype('arialbd.ttf', 24)
    font = ImageFont.truetype('arial.ttf', 20)
except:
    font_title = ImageFont.load_default()
    font_bold = ImageFont.load_default()
    font = ImageFont.load_default()

# Draw text
d.text((50, 50), "TAX INVOICE", fill=(0,0,0), font=font_title)
d.text((50, 120), "Supplier: Ramesh Trading Co.", fill=(0,0,0), font=font_bold)
d.text((50, 160), "GSTIN: ", fill=(255,0,0), font=font_bold) # INTENTIONALLY BLANK
d.text((150, 160), "<MISSING>", fill=(255,0,0), font=font)
d.text((50, 200), "Date: 28/05/2026", fill=(0,0,0), font=font)
d.text((50, 240), "Invoice No: RTC/1058", fill=(0,0,0), font=font)

d.line([(50, 280), (750, 280)], fill=(0,0,0), width=2)

d.text((50, 300), "Description", fill=(0,0,0), font=font_bold)
d.text((450, 300), "Quantity", fill=(0,0,0), font=font_bold)
d.text((600, 300), "Amount (Rs)", fill=(0,0,0), font=font_bold)

d.text((50, 350), "1. Hardware Supplies (Bricks & Cement)", fill=(0,0,0), font=font)
d.text((450, 350), "1 Lumpsum", fill=(0,0,0), font=font)
d.text((600, 350), "1,00,000.00", fill=(0,0,0), font=font)

d.line([(50, 450), (750, 450)], fill=(0,0,0), width=1)

d.text((450, 480), "Subtotal:", fill=(0,0,0), font=font)
d.text((600, 480), "1,00,000.00", fill=(0,0,0), font=font)

d.text((450, 520), "CGST @ 9%:", fill=(0,0,0), font=font)
d.text((600, 520), "9,000.00", fill=(0,0,0), font=font)

d.text((450, 560), "SGST @ 9%:", fill=(0,0,0), font=font)
d.text((600, 560), "9,000.00", fill=(0,0,0), font=font)

d.line([(450, 600), (750, 600)], fill=(0,0,0), width=2)

d.text((450, 620), "GRAND TOTAL:", fill=(0,0,0), font=font_bold)
d.text((600, 620), "1,18,000.00", fill=(0,0,0), font=font_bold)

img.save('../testing/invoices/defective_invoice_test.png')
print('Image saved successfully to testing/invoices/defective_invoice_test.png')
