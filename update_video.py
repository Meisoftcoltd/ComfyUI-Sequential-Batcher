import sys

def modify_video_py():
    with open('video.py', 'r') as f:
        lines = f.readlines()

    # Find the imports section
    import_uuid_idx = -1
    for i, line in enumerate(lines):
        if line.startswith('import time'):
            import_uuid_idx = i + 1
            break

    if import_uuid_idx != -1:
        lines.insert(import_uuid_idx, 'import uuid\n')

    # Add cache after imports
    for i, line in enumerate(lines):
        if line.startswith('try:'):
            lines.insert(i, '\n# Caché persistente para evitar re-escaneos pesados de vídeo\nVIDEO_ANALYSIS_CACHE = {}\n\n')
            break

    with open('video.py', 'w') as f:
        f.writelines(lines)

if __name__ == '__main__':
    modify_video_py()
