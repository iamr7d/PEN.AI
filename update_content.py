import subprocess
import sys
from tqdm import tqdm

scripts = [
    'aggregate_news.py',
    'gemini_news_enhancer.py',
    'image_generator.py',
]

for script in tqdm(scripts, desc="Updating news pipeline"):
    print(f"Running {script}...")
    result = subprocess.run([sys.executable, script], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"Error running {script}: {result.stderr}")
        sys.exit(result.returncode)
print("All update steps completed successfully.")
