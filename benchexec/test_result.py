# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import tempfile
import unittest

from benchexec.result import *  # noqa: F403 @UnusedWildImport everything is tested
from benchexec.result import (
    _SCORE_CORRECT_FALSE,
    _SCORE_CORRECT_TRUE,
    _SCORE_WRONG_TRUE,
    _SCORE_WRONG_FALSE,
)


class TestExpectedResult(unittest.TestCase):
    def test_via_string(self):
        def test(result, subproperty):
            expected_result = ExpectedResult(result, subproperty)
            self.assertEqual(
                ExpectedResult.from_str(str(expected_result)), expected_result
            )

        test(None, None)
        test(True, None)
        test(False, None)
        test(True, "foo")
        test(False, "foo")

    def test_via_instance(self):
        def test(s):
            self.assertEqual(str(ExpectedResult.from_str(s)), s)

        test("")
        test("true")
        test("false")
        test("true(foo)")
        test("false(foo)")

    def test_invalid_string(self):
        def test(s):
            with self.assertRaises(ValueError, msg=f"for '{s}'"):
                ExpectedResult.from_str(s)

        test("foo")
        test("unknown")
        test("true()")


class TestResult(unittest.TestCase):

    def expected_result(self, result, subcategory=None):
        return {"dummy.prp": ExpectedResult(result, subcategory)}

    prop_call = Property("dummy.prp", True, "unreach-call")
    prop_deadlock = Property("dummy.prp", True, "no-deadlock")
    prop_memcleanup = Property("dummy.prp", True, "valid-memcleanup")
    prop_memsafety = Property("dummy.prp", True, "valid-memsafety")
    prop_overflow = Property("dummy.prp", True, "no-overflow")
    prop_termination = Property("dummy.prp", True, "termination")
    prop_sat = Property("dummy.prp", False, "satisfiable")

    def _test_Property_from_file(self, content, is_svcomp):
        with tempfile.NamedTemporaryFile(
            mode="wt", prefix="BenchExec_test_result", suffix=".prp"
        ) as temp_file:
            temp_file.write(content)
            temp_file.flush()
            filename = temp_file.name

            self.assertEqual(
                Property(
                    filename=filename,
                    is_svcomp=is_svcomp,
                    name=os.path.splitext(os.path.basename(filename))[0],
                ),
                Property.create(filename),
                msg="different result for property file with content\n" + content,
            )

    def test_Property_from_non_standard_file(self):
        self._test_Property_from_file("", False)
        self._test_Property_from_file("  ", False)
        self._test_Property_from_file("  CHECK( init(main()), LTL(G p) )", False)
        self._test_Property_from_file("test property", False)
        self._test_Property_from_file("CHECK( init(main()), LTL(G p) )\ntest", False)

    def test_Property_from_sv_comp_file(self):
        self._test_Property_from_file("CHECK( init(main()), LTL(G p) )", True)
        self._test_Property_from_file(
            "CHECK( init(main()), LTL(G p) )\n\nCHECK( init(main()), LTL(F end) )", True
        )
        self._test_Property_from_file(
            "CHECK( init(main()), LTL(G valid-free) )\nCHECK( init(main()), LTL(G valid-deref) )",
            True,
        )
        self._test_Property_from_file(
            "CHECK( init(main()), LTL(G valid-free) and LTL(G valid-deref) )", True
        )

    def test_Property_max_score_not_available(self):
        self.assertEqual(0, self.prop_call.max_score(ExpectedResult(None, None)))
        self.assertEqual(None, self.prop_call.max_score(None))

    def test_Property_max_score_smt(self):
        self.assertEqual(None, self.prop_sat.max_score(ExpectedResult(True, None)))
        self.assertEqual(None, self.prop_sat.max_score(ExpectedResult(False, None)))

    def test_Property_max_score_svcomp(self):
        self.assertEqual(
            _SCORE_CORRECT_TRUE, self.prop_call.max_score(ExpectedResult(True, None))
        )
        self.assertEqual(
            _SCORE_CORRECT_FALSE, self.prop_call.max_score(ExpectedResult(False, None))
        )

        self.assertEqual(
            _SCORE_CORRECT_TRUE,
            self.prop_memsafety.max_score(ExpectedResult(True, None)),
        )
        self.assertEqual(
            _SCORE_CORRECT_FALSE,
            self.prop_memsafety.max_score(ExpectedResult(False, None)),
        )
        self.assertEqual(
            _SCORE_CORRECT_FALSE,
            self.prop_memsafety.max_score(ExpectedResult(False, "valid-free")),
        )

    def test_Property_compute_score_not_available(self):
        self.assertEqual(
            0, self.prop_call.compute_score(CATEGORY_MISSING, RESULT_TRUE_PROP)
        )
        self.assertEqual(
            0, self.prop_call.compute_score(CATEGORY_ERROR, RESULT_TRUE_PROP)
        )
        self.assertEqual(
            0, self.prop_call.compute_score(CATEGORY_UNKNOWN, RESULT_TRUE_PROP)
        )

    def test_Property_compute_score_smt(self):
        self.assertIsNone(
            self.prop_sat.compute_score(CATEGORY_CORRECT, RESULT_TRUE_PROP)
        )
        self.assertIsNone(self.prop_sat.compute_score(CATEGORY_WRONG, RESULT_TRUE_PROP))

    def test_Property_compute_score_svcomp(self):
        self.assertEqual(
            _SCORE_CORRECT_TRUE,
            self.prop_call.compute_score(CATEGORY_CORRECT, RESULT_TRUE_PROP),
        )
        self.assertEqual(
            _SCORE_CORRECT_FALSE,
            self.prop_call.compute_score(CATEGORY_CORRECT, RESULT_FALSE_REACH),
        )
        self.assertEqual(
            _SCORE_CORRECT_TRUE,
            self.prop_memsafety.compute_score(CATEGORY_CORRECT, RESULT_TRUE_PROP),
        )
        self.assertEqual(
            _SCORE_CORRECT_FALSE,
            self.prop_memsafety.compute_score(CATEGORY_CORRECT, RESULT_FALSE_MEMTRACK),
        )
        self.assertEqual(
            _SCORE_CORRECT_TRUE,
            self.prop_termination.compute_score(CATEGORY_CORRECT, RESULT_TRUE_PROP),
        )
        self.assertEqual(
            _SCORE_CORRECT_FALSE,
            self.prop_termination.compute_score(
                CATEGORY_CORRECT, RESULT_FALSE_TERMINATION
            ),
        )
        self.assertEqual(
            _SCORE_CORRECT_TRUE,
            self.prop_overflow.compute_score(CATEGORY_CORRECT, RESULT_TRUE_PROP),
        )
        self.assertEqual(
            _SCORE_CORRECT_FALSE,
            self.prop_overflow.compute_score(CATEGORY_CORRECT, RESULT_FALSE_OVERFLOW),
        )
        self.assertEqual(
            _SCORE_CORRECT_TRUE,
            self.prop_deadlock.compute_score(CATEGORY_CORRECT, RESULT_TRUE_PROP),
        )
        self.assertEqual(
            _SCORE_CORRECT_FALSE,
            self.prop_deadlock.compute_score(CATEGORY_CORRECT, RESULT_FALSE_DEADLOCK),
        )

        self.assertEqual(
            _SCORE_WRONG_FALSE,
            self.prop_call.compute_score(CATEGORY_WRONG, RESULT_FALSE_REACH),
        )
        self.assertEqual(
            _SCORE_WRONG_TRUE,
            self.prop_call.compute_score(CATEGORY_WRONG, RESULT_TRUE_PROP),
        )
        self.assertEqual(
            _SCORE_WRONG_FALSE,
            self.prop_memsafety.compute_score(CATEGORY_WRONG, RESULT_FALSE_MEMTRACK),
        )
        self.assertEqual(
            _SCORE_WRONG_TRUE,
            self.prop_memsafety.compute_score(CATEGORY_WRONG, RESULT_TRUE_PROP),
        )
        self.assertEqual(
            _SCORE_WRONG_FALSE,
            self.prop_memsafety.compute_score(CATEGORY_WRONG, RESULT_FALSE_DEREF),
        )
        self.assertEqual(
            _SCORE_WRONG_FALSE,
            self.prop_termination.compute_score(
                CATEGORY_WRONG, RESULT_FALSE_TERMINATION
            ),
        )
        self.assertEqual(
            _SCORE_WRONG_TRUE,
            self.prop_termination.compute_score(CATEGORY_WRONG, RESULT_TRUE_PROP),
        )
        self.assertEqual(
            _SCORE_WRONG_FALSE,
            self.prop_overflow.compute_score(CATEGORY_WRONG, RESULT_FALSE_OVERFLOW),
        )
        self.assertEqual(
            _SCORE_WRONG_TRUE,
            self.prop_overflow.compute_score(CATEGORY_WRONG, RESULT_TRUE_PROP),
        )
        self.assertEqual(
            _SCORE_WRONG_FALSE,
            self.prop_deadlock.compute_score(CATEGORY_WRONG, RESULT_FALSE_OVERFLOW),
        )
        self.assertEqual(
            _SCORE_WRONG_TRUE,
            self.prop_deadlock.compute_score(CATEGORY_WRONG, RESULT_TRUE_PROP),
        )

    def test_result_classification(self):
        self.assertEqual(RESULT_CLASS_TRUE, get_result_classification(RESULT_TRUE_PROP))

        self.assertEqual(
            RESULT_CLASS_FALSE, get_result_classification(RESULT_FALSE_REACH)
        )
        self.assertEqual(
            RESULT_CLASS_FALSE, get_result_classification(RESULT_FALSE_DEREF)
        )
        self.assertEqual(
            RESULT_CLASS_FALSE, get_result_classification(RESULT_FALSE_FREE)
        )
        self.assertEqual(
            RESULT_CLASS_FALSE, get_result_classification(RESULT_FALSE_MEMTRACK)
        )
        self.assertEqual(
            RESULT_CLASS_FALSE, get_result_classification(RESULT_FALSE_TERMINATION)
        )
        self.assertEqual(
            RESULT_CLASS_FALSE, get_result_classification(RESULT_FALSE_OVERFLOW)
        )
        self.assertEqual(
            RESULT_CLASS_FALSE, get_result_classification(RESULT_FALSE_PROP)
        )
        self.assertEqual(
            RESULT_CLASS_FALSE, get_result_classification(RESULT_FALSE_PROP + "(test)")
        )

        self.assertEqual(RESULT_CLASS_OTHER, get_result_classification(RESULT_DONE))
        self.assertEqual(RESULT_CLASS_OTHER, get_result_classification(RESULT_UNKNOWN))
        self.assertEqual(RESULT_CLASS_OTHER, get_result_classification("KILLED"))
        self.assertEqual(RESULT_CLASS_OTHER, get_result_classification("TIMEOUT"))
        self.assertEqual(RESULT_CLASS_OTHER, get_result_classification(""))

    def test_result_category_true(self):
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(True), RESULT_TRUE_PROP, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(False), RESULT_TRUE_PROP, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(True), RESULT_TRUE_PROP, [self.prop_memsafety]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(False, "valid-memtrack"),
                RESULT_TRUE_PROP,
                [self.prop_memsafety],
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(True), RESULT_TRUE_PROP, [self.prop_memcleanup]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(False), RESULT_TRUE_PROP, [self.prop_memcleanup]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(True), RESULT_TRUE_PROP, [self.prop_termination]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(False), RESULT_TRUE_PROP, [self.prop_termination]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(True), RESULT_TRUE_PROP, [self.prop_overflow]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(False), RESULT_TRUE_PROP, [self.prop_overflow]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(True), RESULT_TRUE_PROP, [self.prop_deadlock]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(False), RESULT_TRUE_PROP, [self.prop_deadlock]
            ),
        )

        test_prop = Property("dummy.prp", True, "test prop")
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(True), RESULT_TRUE_PROP, [test_prop]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(False), RESULT_TRUE_PROP, [test_prop]
            ),
        )

        test_prop = Property("dummy.prp", True, "test prop")
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(True), RESULT_TRUE_PROP, [test_prop]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(False, "a"), RESULT_TRUE_PROP, [test_prop]
            ),
        )

    def test_result_category_false(self):
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_REACH, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(False), RESULT_FALSE_REACH, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_DEREF, [self.prop_memsafety]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_FREE, [self.prop_memsafety]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_MEMTRACK, [self.prop_memsafety]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(False, "valid-deref"),
                RESULT_FALSE_DEREF,
                [self.prop_memsafety],
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(False, "valid-free"),
                RESULT_FALSE_FREE,
                [self.prop_memsafety],
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(False, "valid-memtrack"),
                RESULT_FALSE_MEMTRACK,
                [self.prop_memsafety],
            ),
        )
        self.assertEqual(
            CATEGORY_UNKNOWN,
            get_result_category(
                self.expected_result(False, "valid-deref"),
                RESULT_FALSE_FREE,
                [self.prop_memsafety],
            ),
        )
        self.assertEqual(
            CATEGORY_UNKNOWN,
            get_result_category(
                self.expected_result(False, "valid-free"),
                RESULT_FALSE_MEMTRACK,
                [self.prop_memsafety],
            ),
        )
        self.assertEqual(
            CATEGORY_UNKNOWN,
            get_result_category(
                self.expected_result(False, "valid-memtrack"),
                RESULT_FALSE_DEREF,
                [self.prop_memsafety],
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True),
                RESULT_FALSE_TERMINATION,
                [self.prop_termination],
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(False),
                RESULT_FALSE_TERMINATION,
                [self.prop_termination],
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_OVERFLOW, [self.prop_overflow]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(False), RESULT_FALSE_OVERFLOW, [self.prop_overflow]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_DEADLOCK, [self.prop_deadlock]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(False), RESULT_FALSE_DEADLOCK, [self.prop_deadlock]
            ),
        )

        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_PROP, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(False), RESULT_FALSE_PROP, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_PROP, [self.prop_termination]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(False), RESULT_FALSE_PROP, [self.prop_termination]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_PROP, [self.prop_overflow]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(False), RESULT_FALSE_PROP, [self.prop_overflow]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_PROP, [self.prop_deadlock]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(False), RESULT_FALSE_PROP, [self.prop_deadlock]
            ),
        )

        test_prop = Property("dummy.prp", True, "test prop")
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_PROP, [test_prop]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(False), RESULT_FALSE_PROP, [test_prop]
            ),
        )
        # arbitrary subproperties allowed if property does not specify one
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(False), RESULT_FALSE_PROP + "(a)", [test_prop]
            ),
        )

        test_prop = Property("dummy.prp", True, "test prop")
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_PROP, [test_prop]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_PROP + "(a)", [test_prop]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                self.expected_result(False, "a"), RESULT_FALSE_PROP + "(a)", [test_prop]
            ),
        )

    def test_result_category_different_false_result(self):
        expected_result_false = self.expected_result(False)
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_DEREF, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_TERMINATION, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_OVERFLOW, [self.prop_call]
            ),
        )

        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_REACH, [self.prop_termination]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_DEREF, [self.prop_termination]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_OVERFLOW, [self.prop_termination]
            ),
        )

        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_REACH, [self.prop_sat]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_DEREF, [self.prop_sat]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_TERMINATION, [self.prop_sat]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_OVERFLOW, [self.prop_sat]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_PROP, [self.prop_sat]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_PROP, [self.prop_sat]
            ),
        )

        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_REACH, [self.prop_overflow]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_DEREF, [self.prop_overflow]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_TERMINATION, [self.prop_overflow]
            ),
        )

        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_REACH, [self.prop_deadlock]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_DEREF, [self.prop_deadlock]
            ),
        )
        self.assertEqual(
            CATEGORY_CORRECT,
            get_result_category(
                expected_result_false, RESULT_FALSE_TERMINATION, [self.prop_deadlock]
            ),
        )

        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_OVERFLOW, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_REACH, [self.prop_termination]
            ),
        )
        self.assertEqual(
            CATEGORY_WRONG,
            get_result_category(
                self.expected_result(True), RESULT_FALSE_PROP, [self.prop_memsafety]
            ),
        )
        self.assertEqual(
            CATEGORY_UNKNOWN,
            get_result_category(
                self.expected_result(False, "valid-deref"),
                RESULT_FALSE_PROP,
                [self.prop_memsafety],
            ),
        )
        self.assertEqual(
            CATEGORY_UNKNOWN,
            get_result_category(
                self.expected_result(False, "valid-free"),
                RESULT_FALSE_PROP,
                [self.prop_memsafety],
            ),
        )
        self.assertEqual(
            CATEGORY_UNKNOWN,
            get_result_category(
                self.expected_result(False, "valid-memtrack"),
                RESULT_FALSE_PROP,
                [self.prop_memsafety],
            ),
        )

        test_prop = Property("dummy.prp", True, "test prop")
        self.assertEqual(
            CATEGORY_UNKNOWN,
            get_result_category(
                self.expected_result(False, "a"), RESULT_FALSE_PROP, [test_prop]
            ),
        )

    def test_result_category_no_property(self):
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(self.expected_result(True), RESULT_TRUE_PROP, []),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(self.expected_result(False), RESULT_TRUE_PROP, []),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(self.expected_result(True), RESULT_TRUE_PROP, []),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(
                self.expected_result(False, "valid-memtrack.c"), RESULT_TRUE_PROP, []
            ),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(self.expected_result(True), RESULT_TRUE_PROP, []),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(self.expected_result(False), RESULT_TRUE_PROP, []),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(self.expected_result(True), RESULT_TRUE_PROP, []),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(self.expected_result(False), RESULT_TRUE_PROP, []),
        )

    def test_result_category_no_expected_result(self):
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(
                self.expected_result(None), RESULT_TRUE_PROP, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(
                self.expected_result(None), RESULT_FALSE_PROP, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(
                self.expected_result(None), RESULT_TRUE_PROP, [self.prop_memsafety]
            ),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(
                self.expected_result(None), RESULT_FALSE_FREE, [self.prop_memsafety]
            ),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(
                self.expected_result(None), RESULT_TRUE_PROP, [self.prop_termination]
            ),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(
                self.expected_result(None), RESULT_FALSE_PROP, [self.prop_termination]
            ),
        )

        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category({}, RESULT_TRUE_PROP, [self.prop_call]),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category({}, RESULT_FALSE_PROP, [self.prop_call]),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category({}, RESULT_TRUE_PROP, [self.prop_memsafety]),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category({}, RESULT_FALSE_FREE, [self.prop_memsafety]),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category({}, RESULT_TRUE_PROP, [self.prop_termination]),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category({}, RESULT_FALSE_PROP, [self.prop_termination]),
        )

    def test_result_category_different_property(self):
        def other_expected_result(result, subcategory=None):
            return {"different-file.prp": ExpectedResult(result, subcategory)}

        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(
                other_expected_result(True), RESULT_TRUE_PROP, [self.prop_termination]
            ),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(
                other_expected_result(False), RESULT_TRUE_PROP, [self.prop_termination]
            ),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(
                other_expected_result(True), RESULT_TRUE_PROP, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(
                other_expected_result(False, "valid-memtrack"),
                RESULT_TRUE_PROP,
                [self.prop_call],
            ),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(
                other_expected_result(True), RESULT_TRUE_PROP, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(
                other_expected_result(False), RESULT_TRUE_PROP, [self.prop_call]
            ),
        )

    def test_result_category_other(self):
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(
                self.expected_result(True), RESULT_DONE, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(self.expected_result(True), RESULT_DONE, []),
        )
        self.assertEqual(
            CATEGORY_MISSING,
            get_result_category(
                self.expected_result(None), RESULT_DONE, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_UNKNOWN,
            get_result_category(
                self.expected_result(True), RESULT_UNKNOWN, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_UNKNOWN,
            get_result_category(self.expected_result(True), RESULT_UNKNOWN, []),
        )
        self.assertEqual(
            CATEGORY_UNKNOWN,
            get_result_category(
                self.expected_result(None), RESULT_UNKNOWN, [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_ERROR,
            get_result_category(self.expected_result(True), "KILLED", [self.prop_call]),
        )
        self.assertEqual(
            CATEGORY_ERROR,
            get_result_category(
                self.expected_result(True), "TIMEOUT", [self.prop_call]
            ),
        )
        self.assertEqual(
            CATEGORY_ERROR,
            get_result_category(self.expected_result(True), "", [self.prop_call]),
        )
