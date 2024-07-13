# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import bz2
import glob
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from xml.etree import ElementTree

here = os.path.dirname(__file__)
base_dir = os.path.join(here, "..", "..")
bin_dir = os.path.join(base_dir, "bin")
benchmarks_dir = here
benchexec = os.path.join(bin_dir, "benchexec")
result_dtd = os.path.join(base_dir, "doc", "result.dtd")
result_dtd_public_id = "+//IDN sosy-lab.org//DTD BenchExec result 3.0//EN"

benchmark_test_name = "benchmark-example-rand"
benchmark_test_file = os.path.join(here, "benchmark-example-rand.xml")
benchmark_test_tasks = [
    "DTD files",
    "Markdown files",
    "XML files",
    "Dummy tasks",
    "Tasks from templates",
]
benchmark_test_rundefs = None

# Set to True to let tests overwrite the expected result with the actual result
# instead of letting them fail.
# Use this to update expected files if necessary. Do not commit this flag set to True!
OVERWRITE_MODE = False


class BenchExecIntegrationTests(unittest.TestCase):

    def _build_tmp_dir(self):
        """
        Initializes the temporary directory structure for testing.
        Current structure:
            $TMP_DIR$
                |-- doc                                # contains some files used as pseudo-benchmark tasks
                |-- benchexec/test_integration
                     |-- actual                        # output directory for benchexec runs
                     |-- *.xml                         # benchmark definitions used
        """
        tmp_dir = tempfile.mkdtemp(prefix="BenchExec_integration_test")
        relative_benchmark_dir = os.path.relpath(benchmarks_dir, base_dir)
        tmp_benchmarks_dir = os.path.join(tmp_dir, relative_benchmark_dir)
        shutil.copytree(benchmarks_dir, tmp_benchmarks_dir)
        shutil.copytree(os.path.join(base_dir, "doc"), os.path.join(tmp_dir, "doc"))
        shutil.copy(os.path.join(base_dir, "README.md"), os.path.join(tmp_dir))
        output_dir = os.path.join(tmp_dir, "benchexec", "test_integration", "actual")
        os.makedirs(output_dir)
        self.tmp = tmp_dir
        self.benchmarks_dir = tmp_benchmarks_dir
        self.output_dir = output_dir
        self.benchmark_test_file = os.path.join(
            self.tmp, os.path.relpath(benchmark_test_file, base_dir)
        )

    def setUp(self):
        self._build_tmp_dir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_cmd(self, *args, additional_env=None):
        standard_args = [
            benchexec,
            "--container",
            "--read-only-dir",
            "/",
            "--read-only-dir",
            os.path.normpath(base_dir),
            "--outputpath",
            self.output_dir,
            "--startTime",
            "2015-01-01 00:00:00",
        ]
        env = None
        if additional_env:
            env = os.environ.copy()
            env.update(additional_env)
        try:
            output = subprocess.check_output(
                args=standard_args + list(args),
                env=env,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )
        except subprocess.CalledProcessError as e:
            print(e.output)
            raise e
        print(output)
        return output

    def run_benchexec_and_compare_expected_files(
        self,
        *args,
        name=None,
        tasks=benchmark_test_tasks,
        rundefs=benchmark_test_rundefs,
        test_name=benchmark_test_name,
        test_file=None,
        compress=False,
    ):
        if not test_file:  # Assign default test file
            test_file = self.benchmark_test_file
        self.run_cmd(
            *[test_file] + ([] if compress else ["--no-compress-results"]) + list(args)
        )
        generated_files = set(os.listdir(self.output_dir))

        xml_suffix = ".xml.bz2" if compress else ".xml"

        if rundefs == []:
            expected_files = []
        else:
            expected_files = ["logfiles.zip" if compress else "logfiles"]

        if rundefs is None or len(rundefs) != 1:
            expected_files += ["results.txt"]
        else:
            expected_files += [f"results.{rundefs[0]}.txt"]

        if rundefs is None:
            expected_files += [f"results.{task}{xml_suffix}" for task in tasks]
            expected_files += [f"results{xml_suffix}"]
        else:
            expected_files += [
                f"results.{rundef}.{task}{xml_suffix}"
                for task in tasks
                for rundef in rundefs
            ]
            expected_files += [f"results.{rundef}{xml_suffix}" for rundef in rundefs]

        if name is None:
            basename = f"{test_name}.2015-01-01_00-00-00."
        else:
            basename = f"{test_name}.{name}.2015-01-01_00-00-00."

        expected_files = {basename + expected_file for expected_file in expected_files}
        self.assertSetEqual(
            generated_files,
            expected_files,
            "Set of generated files differs from set of expected files",
        )
        # TODO find way to compare expected output to generated output

        if compress:
            with zipfile.ZipFile(
                os.path.join(self.output_dir, basename + "logfiles.zip")
            ) as log_zip:
                self.assertIsNone(log_zip.testzip(), "Logfiles zip archive is broken")
                for file in log_zip.namelist():
                    self.assertTrue(
                        file.startswith(f"{basename}logfiles{os.sep}"),
                        "Unexpected file in logfiles zip: " + file,
                    )

            for file in generated_files:
                if file.endswith(".bz2"):
                    # try to decompress and read to see if there are any errors with it
                    with bz2.BZ2File(os.path.join(self.output_dir, file)) as bz2file:
                        bz2file.read()

    def _assertEqualXmlTree(self, actual_tree, expected_tree):
        actual = ElementTree.tostring(actual_tree).splitlines()
        expected = ElementTree.tostring(expected_tree).splitlines()

        for actual_line, expected_line in zip(actual, expected):
            self.assertEqual(actual_line, expected_line)

    def assertSameRunResults(self, actual_result_xml, other_result_xml):
        if OVERWRITE_MODE and not actual_result_xml == other_result_xml:
            shutil.copyfile(actual_result_xml, other_result_xml)
            return

        actual_result = ElementTree.ElementTree().parse(actual_result_xml)
        expected_result = ElementTree.ElementTree().parse(other_result_xml)

        self.assertEqual(actual_result.tag, expected_result.tag)
        self._assertEqualXmlTree(
            actual_result.find("columns"), expected_result.find("columns")
        )
        actual_runs = actual_result.findall("run")
        expected_runs = expected_result.findall("run")
        self.assertListEqual(
            [run.get("name") for run in actual_runs],
            [run.get("name") for run in expected_runs],
        )
        for actual, expected in zip(actual_runs, expected_runs):
            self.assertEqual(actual.get("files"), expected.get("files"))
            self.assertEqual(actual.get("name"), expected.get("name"))

            actual_columns = {
                column.get("title"): column for column in actual.findall("column")
            }
            expected_columns = {
                column.get("title"): column for column in expected.findall("column")
            }
            comparable_columns = ["status", "category", "returnvalue"]
            for column in comparable_columns:
                self.assertEqual(
                    actual_columns[column].get("value"),
                    expected_columns[column].get("value"),
                )

    def test_same_results_file(self):
        results_file = os.path.join(
            here,
            "expected/benchmark-example-true.2015-01-01_0000.results.no options.xml",
        )
        self.assertSameRunResults(results_file, results_file)

    def test_simple(self):
        self.run_benchexec_and_compare_expected_files()

    def test_simple_select_tasks(self):
        self.run_benchexec_and_compare_expected_files(
            "--tasks",
            "DTD files",
            "--tasks",
            "XML files",
            tasks=["DTD files", "XML files"],
        )

    def test_simple_set_name(self):
        test_name = "integration test"
        self.run_benchexec_and_compare_expected_files(
            "--name", test_name, name=test_name
        )

    def test_simple_parallel(self):
        self.run_benchexec_and_compare_expected_files("--numOfThreads", "12")

    def test_wildcard_tasks_1(self):
        self.run_benchexec_and_compare_expected_files(
            "--tasks", "*", tasks=benchmark_test_tasks
        )

    def test_wildcard_tasks_2(self):
        self.run_benchexec_and_compare_expected_files(
            "--tasks", "* files", tasks=["DTD files", "Markdown files", "XML files"]
        )

    def test_wildcard_tasks_3(self):
        self.run_benchexec_and_compare_expected_files(
            "--tasks", "*M* files", tasks=["Markdown files", "XML files"]
        )

    def test_wildcard_tasks_4(self):
        self.run_benchexec_and_compare_expected_files(
            "--tasks", "??? files", tasks=["DTD files", "XML files"]
        )

    def test_wildcard_tasks_5(self):
        self.run_benchexec_and_compare_expected_files(
            "--tasks", "[MD]* files", tasks=["DTD files", "Markdown files"]
        )

    def test_wildcard_tasks_6(self):
        self.run_benchexec_and_compare_expected_files(
            "--tasks",
            "[!D]*",
            tasks=["Markdown files", "XML files", "Tasks from templates"],
        )

    def test_wildcard_tasks_7(self):
        self.run_benchexec_and_compare_expected_files(
            "--tasks", "D*", tasks=["DTD files", "Dummy tasks"]
        )

    def test_wildcard_rundefinition_1(self):
        self.run_benchexec_and_compare_expected_files(
            "--rundefinition",
            "*",
            test_name="benchmark-example-true",
            test_file=os.path.join(base_dir, "doc", "benchmark-example-true.xml"),
            rundefs=["no options", "some options", "other options"],
        )

    def test_wildcard_rundefinition_2(self):
        self.run_benchexec_and_compare_expected_files(
            "--rundefinition",
            "*",
            test_name="benchmark-example-true",
            test_file=os.path.join(base_dir, "doc", "benchmark-example-true.xml"),
            rundefs=["no options", "some options", "other options"],
        )

    def test_wildcard_rundefinition_3(self):
        self.run_benchexec_and_compare_expected_files(
            "--rundefinition",
            "?o* options",
            test_name="benchmark-example-true",
            test_file=os.path.join(base_dir, "doc", "benchmark-example-true.xml"),
            rundefs=["no options", "some options"],
        )

    def test_wildcard_rundefinition_4(self):
        self.run_benchexec_and_compare_expected_files(
            "--rundefinition",
            "?[!o]*",
            test_name="benchmark-example-true",
            test_file=os.path.join(base_dir, "doc", "benchmark-example-true.xml"),
            rundefs=["other options"],
        )

    def test_wildcard_rundefinition_5(self):
        self.run_benchexec_and_compare_expected_files(
            "--rundefinition",
            "?",
            test_name="benchmark-example-true",
            test_file=os.path.join(base_dir, "doc", "benchmark-example-true.xml"),
            rundefs=[],
        )

    def test_simple_compressed_results(self):
        self.run_benchexec_and_compare_expected_files(compress=True)

    def test_validate_result_xml(self):
        self.run_cmd(
            self.benchmark_test_file,
            "--no-compress-results",
            "--description-file",
            self.benchmark_test_file,
        )
        basename = "benchmark-example-rand.2015-01-01_00-00-00."
        xml_files = ["results.xml"] + [
            f"results.{files}.xml" for files in benchmark_test_tasks
        ]
        xml_files = [os.path.join(self.output_dir, basename + x) for x in xml_files]

        # setup parser with DTD validation
        from lxml import etree

        class DTDResolver(etree.Resolver):
            def resolve(self, url, public_id, context):
                if public_id == result_dtd_public_id:
                    return self.resolve_filename(result_dtd, context)
                return None

        parser = etree.XMLParser(dtd_validation=True)
        parser.resolvers.add(DTDResolver())

        for xml_file in xml_files:
            try:
                etree.parse(xml_file, parser=parser)
            except etree.XMLSyntaxError as e:
                self.assertIsNone(e)

    def test_run_results_information(self):
        expected_xml = os.path.join(
            here,
            "expected/benchmark-example-true.2015-01-01_0000.results.no options.xml",
        )
        benchmark_xml = os.path.join(self.benchmarks_dir, "benchmark-example-true.xml")
        self.run_cmd(
            benchmark_xml, "--no-compress-results", "--rundefinition", "no options"
        )
        actual_xml = os.path.join(
            self.output_dir,
            "benchmark-example-true.2015-01-01_00-00-00.results.no options.xml",
        )

        self.assertSameRunResults(actual_xml, expected_xml)

    def test_description(self):
        test_description = """
            äöüß     This tests non-ASCII characters, line breaks, whitespace, and
              <>&"'  XML special characters.
            """
        with tempfile.NamedTemporaryFile(
            prefix="description", suffix=".txt", dir=self.tmp, mode="w+"
        ) as desc:
            desc.write(test_description)
            desc.flush()

            self.run_cmd(
                self.benchmark_test_file,
                "--no-compress-results",
                "--description-file",
                desc.name,
            )

        generated_files = glob.glob(os.path.join(self.output_dir, "*.xml"))
        assert generated_files, "error in test, no results generated"

        for f in generated_files:
            result_xml = ElementTree.ElementTree().parse(f)
            actual_description = result_xml.find("description").text
            self.assertEqual(actual_description, test_description.strip())

    def test_environment(self):
        self.run_cmd(
            self.benchmark_test_file,
            "--no-compress-results",
            additional_env={
                "BENCHEXEC_TEST_VAR": "a\x01\x1bb",
                "BENCHEXEC_TEST_VAR2": "ab",
            },
        )

        generated_files = glob.glob(os.path.join(self.output_dir, "*.xml"))
        assert generated_files, "error in test, no results generated"

        for f in generated_files:
            result_xml = ElementTree.ElementTree().parse(f)
            environment = result_xml.find("systeminfo").find("environment")
            var_tags = {tag.attrib["name"]: tag for tag in environment.findall("var")}
            self.assertEqual(var_tags["BENCHEXEC_TEST_VAR"].text, "YQEbYg==")
            self.assertEqual(
                var_tags["BENCHEXEC_TEST_VAR"].attrib["encoding"], "base64"
            )
            # Check that other variables are not unnecessarily encoded.
            self.assertEqual(var_tags["BENCHEXEC_TEST_VAR2"].text, "ab")
            self.assertNotIn("encoding", var_tags["BENCHEXEC_TEST_VAR2"].attrib)
