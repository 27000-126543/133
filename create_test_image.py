from PIL import Image, ImageDraw
import os

os.makedirs('test_data', exist_ok=True)

img = Image.new('RGB', (800, 600), 'white')
draw = ImageDraw.Draw(img)

draw.rectangle([50, 50, 750, 550], outline='black', width=3)
draw.text((200, 100), 'Certificate', fill='black')
draw.text((100, 200), 'Name: Zhang San', fill='black')
draw.text((100, 250), 'Cert No: TEST001', fill='black')
draw.text((100, 300), 'Authority: HR Ministry', fill='black')
draw.text((100, 350), 'Issue Date: 2024-01-01', fill='black')
draw.text((100, 400), 'Expiry Date: 2029-01-01', fill='black')

img.save('test_data/sample_certificate.jpg')
print('Created test_data/sample_certificate.jpg')
print('File exists:', os.path.exists('test_data/sample_certificate.jpg'))
print('File size:', os.path.getsize('test_data/sample_certificate.jpg'), 'bytes')
