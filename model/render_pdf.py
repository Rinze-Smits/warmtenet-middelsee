import pypdfium2,sys,os
pdf=pypdfium2.PdfDocument(sys.argv[1]); os.makedirs(sys.argv[2],exist_ok=True)
for i in range(len(pdf)):
    pdf[i].render(scale=1.6).to_pil().save(f'{sys.argv[2]}/p{i+1}.png')
print(len(pdf))
