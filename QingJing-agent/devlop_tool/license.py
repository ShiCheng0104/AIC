# Copyright (c) 2025 试试又不会怎样
#
# This file is part of DeepseaAgent.
#
# All rights reserved.
# Licensed under the MIT License.

import os
import re

author = "试试又不会怎样"
project_name = "DeepseaAgent"
license_type = "MIT"
target_extensions = [".py", ".c", ".cpp", ".h", ".java"]


def get_license():
    return f"""# Copyright (c) 2025 {author}
#
# This file is part of {project_name}.
#
# All rights reserved.
# Licensed under the {license_type} License.
"""


def add_license_to_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if re.match(rf"^# Copyright .*{author}", content):
        print(f"[跳过] {file_path} - 已存在 LICENSE")
        return

    new_content = get_license() + "\n" + content
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"[已处理] {file_path}")


def process_folder(root_folder):
    for root, _, files in os.walk(root_folder):
        for file in files:
            if any(file.endswith(ext) for ext in target_extensions):
                file_path = os.path.join(root, file)
                add_license_to_file(file_path)


if __name__ == "__main__":
    target_folder = os.getcwd()
    process_folder(target_folder)
    print("✅ LICENSE 处理完成！")
