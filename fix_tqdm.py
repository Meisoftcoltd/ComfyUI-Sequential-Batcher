def fix():
    with open('video.py', 'r') as f:
        content = f.read()

    if 'from tqdm import tqdm' not in content:
        content = 'from tqdm import tqdm\n' + content

    with open('video.py', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    fix()
