import os, shutil, random

src = 'all_my_images'          
random.seed(42)

images = [f for f in os.listdir(src) if f.endswith(('.jpg','.png','.jpeg'))]
random.shuffle(images)

n = len(images)
train = images[:int(n*0.80)]
val   = images[int(n*0.80):int(n*0.95)]
test  = images[int(n*0.95):]

for split, files in [('train', train), ('val', val), ('test', test)]:
    os.makedirs(f'nigeria_plates/images/{split}', exist_ok=True)
    os.makedirs(f'nigeria_plates/labels/{split}', exist_ok=True)
    for f in files:
        # copy image
        shutil.copy(f'{src}/{f}', f'nigeria_plates/images/{split}/{f}')
        # copy matching label
        label = f.rsplit('.', 1)[0] + '.txt'
        if os.path.exists(f'{src}/{label}'):
            shutil.copy(f'{src}/{label}', f'nigeria_plates/labels/{split}/{label}')

print("Dataset split complete!")