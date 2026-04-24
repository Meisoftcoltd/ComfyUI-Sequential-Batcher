def fix():
    with open('video.py', 'r') as f:
        content = f.read()

    content = content.replace('_log(f"{'+'=\'*50}\n")', '_log(f"{'+'=\'*50}\\n")')
    content = content.replace('", "\n".join(log_output))}', '", "\\n".join(log_output))}')

    with open('video.py', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    fix()
