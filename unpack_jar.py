import zipfile
import os
def unpack_jar(jar_path: str, extract_path: str):
    """
    解压jar 文件
    """
    if not os.path.exists(extract_path):
        os.makedirs(extract_path)
    with zipfile.ZipFile(jar_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)