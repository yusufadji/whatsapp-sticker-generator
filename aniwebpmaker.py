import os
import subprocess

# workspace setup
src_folder = "src"
file_extension = ".webp"


# preferences
duration = 30
offsetX = 0
offsetY = 0


file_list = [file for file in os.listdir(src_folder) if file.endswith(file_extension)]


input_files = " ".join([f"-frame {os.path.join(src_folder, file)} +{duration}+{offsetX}+{offsetY}" for file in file_list])
output_file = "dst/a.webp"


command = ["webpmux", "-o", output_file] + input_files.split()


subprocess.run(command)
