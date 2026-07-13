import os
import shutil
import subprocess
import tarfile
import urllib.request

# Download
url = "https://files.pythonhosted.org/packages/source/l/llama-cpp-python/llama_cpp_python-0.3.23.tar.gz"
tar_path = "C:\\temp\\llama.tar.gz"
print("Downloading...")
urllib.request.urlretrieve(url, tar_path)

print("Extracting...")
# Extract
with tarfile.open(tar_path, "r:gz") as tar:
    tar.extractall("C:\\temp\\llama_src")

# The extracted folder
src_dir = "C:\\temp\\llama_src\\llama_cpp_python-0.3.23"

# Remove the webui directory which has the extremely long paths
webui_dir = os.path.join(src_dir, "vendor", "llama.cpp", "tools", "server", "webui")
if os.path.exists(webui_dir):
    print("Deleting webui directory to bypass Long Path issue...")
    shutil.rmtree(webui_dir)

print("Installing...")
subprocess.run(["pip", "install", "."], cwd=src_dir, check=True)
print("Done!")
