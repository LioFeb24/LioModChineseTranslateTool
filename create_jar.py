import os
import shutil
import subprocess
import zipfile


def _find_jar_exe() -> str | None:
    jar = shutil.which("jar")
    if jar:
        return jar
    java_home = os.getenv("JAVA_HOME")
    if java_home:
        cand = os.path.join(java_home, "bin", "jar.exe" if os.name == "nt" else "jar")
        if os.path.exists(cand):
            return cand
    return None


def _create_jar_with_java(folder: str, output_path: str) -> None:
    jar = _find_jar_exe()
    if not jar:
        raise FileNotFoundError("未找到 jar 可执行文件（PATH/JAVA_HOME）")

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    if os.path.exists(output_path):
        os.remove(output_path)

    folder_abs = os.path.abspath(folder)
    cmd = [jar, "cf", output_path, "-C", folder_abs, "."]
    subprocess.run(cmd, check=True)


def _create_jar_with_zip(folder: str, output_path: str) -> None:
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    if os.path.exists(output_path):
        os.remove(output_path)

    folder_abs = os.path.abspath(folder)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder_abs):
            for name in files:
                abs_path = os.path.join(root, name)
                rel_path = os.path.relpath(abs_path, folder_abs)
                zf.write(abs_path, rel_path)


def create_jar(folder: str, output_path: str, prefer_java: bool = True) -> str:
    """
    将 folder 目录打包为 jar（本质为 zip），并写入 output_path。

    优先使用本地 Java 的 jar 工具；不可用时自动降级为 Python zipfile 打包。
    返回 output_path 的绝对路径。
    """
    if not folder:
        raise ValueError("folder 不能为空")
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"folder 不存在或不是目录：{folder}")
    if not output_path:
        raise ValueError("output_path 不能为空")
    if not output_path.lower().endswith(".jar"):
        raise ValueError("output_path 必须以 .jar 结尾")

    out_abs = os.path.abspath(output_path)
    if prefer_java:
        try:
            _create_jar_with_java(folder, out_abs)
            return out_abs
        except Exception:
            pass
    _create_jar_with_zip(folder, out_abs)
    return out_abs


folder = "files/temp"
output_path = "files/DistantHorizons-2.4.5-b-1.21.11-fabric-neoforge_zh.jar"

if __name__ == "__main__":
    print(create_jar(folder, output_path, prefer_java=True))

