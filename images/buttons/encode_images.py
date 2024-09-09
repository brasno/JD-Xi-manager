import os
import base64

def main():
    OUT = 'images.py'
    dir='.'
    images = [f for f in os.listdir(dir) if f.endswith('.png') or f.endswith('.ico') or f.endswith('.gif')]

    outfile = open(os.path.join(dir, OUT), 'w')

    for i, file in enumerate(images):
        image = open(os.path.join(dir, file), 'rb').read()
        encoded = base64.b64encode(image)
        outfile.write('{} = {}\n'.format(file[:file.index(".")], encoded))

    outfile.close()
    print('{} images encoded.'.format((i+1)))

if __name__ == '__main__':
    main()
