import os
from typing import List

def merge_files(directories: List[str], output_file: str):
    """
    Merge all files from the given list of directories into one master file.
    Files are merged in alphabetical order per directory.
    """

    with open(output_file, "w", encoding="utf-8") as master:

        for input_dir in directories:
            if not os.path.isdir(input_dir):
                print(f"Skipping: {input_dir} (not a directory)")
                continue

            # List files
            files = [
                f for f in os.listdir(input_dir)
                if os.path.isfile(os.path.join(input_dir, f))
            ]
            files.sort()

            master.write(f"\n\n===== DIRECTORY: {input_dir} =====\n")

            for filename in files:
                file_path = os.path.join(input_dir, filename)

                master.write(f"\n--- BEGIN FILE: {filename} ---\n")

                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    master.write(f.read())

                master.write(f"\n--- END FILE: {filename} ---\n")

        print(f"Merged files from {len(directories)} directories into: {output_file}")


if __name__ == "__main__":
    dirs = [
        "src/rdt/",
        "src/pop3",
        "src/server",
        "src/smtp"
    ]
    merge_files(dirs, output_file="master_output.txt")
