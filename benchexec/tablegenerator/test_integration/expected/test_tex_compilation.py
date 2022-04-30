import os
import subprocess
import textwrap
from pathlib import Path

latex_header = textwrap.dedent(
    """\
            \\documentclass{standalone}
            \\input{command_file}
            \\begin{document}
                test
            \\end{document}
            """
)


def main():
    folder = Path(__file__).resolve().parent
    count = 0
    error = 0
    for tex_file in folder.glob("*.tex"):
        test_file_content = latex_header.replace("command_file", "../" + tex_file.name)

        test_file = folder / "test" / "test.tex"

        test_file.parent.mkdir(parents=True, exist_ok=True)

        with open(test_file, "w+") as f:
            f.write(test_file_content)
        cwd = os.getcwd()
        try:
            os.chdir(test_file.parent)
            return_code = subprocess.Popen(
                ["pdflatex", "-interaction=nonstopmode", test_file.name],
                stdout=subprocess.DEVNULL,
            ).wait()
            count += 1
            if return_code != 0:
                error += 1
                print("ERROR ===============")
                print(test_file_content)
                print("ERROR ===============")

        finally:
            os.chdir(cwd)

    print(count, error)


if __name__ == "__main__":
    main()
