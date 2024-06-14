# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2024 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import sys
import tempfile
import pytest

from benchexec.result import *  # noqa: F403 @UnusedWildImport everything is tested
from benchexec.result import (
    _SCORE_CORRECT_FALSE,
    _SCORE_CORRECT_TRUE,
    _SCORE_WRONG_TRUE,
    _SCORE_WRONG_FALSE,
)

sys.dont_write_bytecode = True  # prevent creation of .pyc files


class TestExpectedResult:
    def test_via_string(self):
        def test(result, subproperty):
            expected_result = ExpectedResult(result, subproperty)
            assert ExpectedResult.from_str(str(expected_result)) == expected_result

        test(None, None)
        test(True, None)
        test(False, None)
        test(True, "foo")
        test(False, "foo")

    def test_via_instance(self):
        def test(s):
            assert str(ExpectedResult.from_str(s)) == s

        test("")
        test("true")
        test("false")
        test("true(foo)")
        test("false(foo)")

    def test_invalid_string(self):
        def test(s):
            with pytest.raises(ValueError) as exc_info:
                ExpectedResult.from_str(s)
            assert str(exc_info.value) == f"Not a valid expected verdict: {s}"

        test("foo")
        test("unknown")
        test("true()")


@pytest.fixture(scope="class")
def disable_non_critical_logging():
    logging.disable(logging.CRITICAL)


@pytest.mark.usefixtures("disable_non_critical_logging")
class TestResult:
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

            assert Property(
                filename=filename,
                is_svcomp=is_svcomp,
                name=os.path.splitext(os.path.basename(filename))[0],
            ) == Property.create(
                filename
            ), f"different result for property file with content\n{ content }"

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
        assert 0 == self.prop_call.max_score(ExpectedResult(None, None))
        assert None is self.prop_call.max_score(None)

    def test_Property_max_score_smt(self):
        assert None is self.prop_sat.max_score(ExpectedResult(True, None))
        assert None is self.prop_sat.max_score(ExpectedResult(False, None))

    def test_Property_max_score_svcomp(self):
        assert _SCORE_CORRECT_TRUE == self.prop_call.max_score(
            ExpectedResult(True, None)
        )
        assert _SCORE_CORRECT_FALSE == self.prop_call.max_score(
            ExpectedResult(False, None)
        )

        assert _SCORE_CORRECT_TRUE == self.prop_memsafety.max_score(
            ExpectedResult(True, None)
        )
        assert _SCORE_CORRECT_FALSE == self.prop_memsafety.max_score(
            ExpectedResult(False, None)
        )
        assert _SCORE_CORRECT_FALSE == self.prop_memsafety.max_score(
            ExpectedResult(False, "valid-free")
        )

    def test_Property_compute_score_not_available(self):
        assert 0 == self.prop_call.compute_score(CATEGORY_MISSING, RESULT_TRUE_PROP)
        assert 0 == self.prop_call.compute_score(CATEGORY_ERROR, RESULT_TRUE_PROP)
        assert 0 == self.prop_call.compute_score(CATEGORY_UNKNOWN, RESULT_TRUE_PROP)

    def test_Property_compute_score_smt(self):
        assert None is self.prop_sat.compute_score(CATEGORY_CORRECT, RESULT_TRUE_PROP)
        assert None is self.prop_sat.compute_score(CATEGORY_WRONG, RESULT_TRUE_PROP)

    def test_Property_compute_score_svcomp(self):
        assert _SCORE_CORRECT_TRUE == self.prop_call.compute_score(
            CATEGORY_CORRECT, RESULT_TRUE_PROP
        )
        assert _SCORE_CORRECT_FALSE == self.prop_call.compute_score(
            CATEGORY_CORRECT, RESULT_FALSE_REACH
        )
        assert _SCORE_CORRECT_TRUE == self.prop_memsafety.compute_score(
            CATEGORY_CORRECT, RESULT_TRUE_PROP
        )
        assert _SCORE_CORRECT_FALSE == self.prop_memsafety.compute_score(
            CATEGORY_CORRECT, RESULT_FALSE_MEMTRACK
        )
        assert _SCORE_CORRECT_TRUE == self.prop_termination.compute_score(
            CATEGORY_CORRECT, RESULT_TRUE_PROP
        )
        assert _SCORE_CORRECT_FALSE == self.prop_termination.compute_score(
            CATEGORY_CORRECT, RESULT_FALSE_TERMINATION
        )
        assert _SCORE_CORRECT_TRUE == self.prop_overflow.compute_score(
            CATEGORY_CORRECT, RESULT_TRUE_PROP
        )
        assert _SCORE_CORRECT_FALSE == self.prop_overflow.compute_score(
            CATEGORY_CORRECT, RESULT_FALSE_OVERFLOW
        )
        assert _SCORE_CORRECT_TRUE == self.prop_deadlock.compute_score(
            CATEGORY_CORRECT, RESULT_TRUE_PROP
        )
        assert _SCORE_CORRECT_FALSE == self.prop_deadlock.compute_score(
            CATEGORY_CORRECT, RESULT_FALSE_DEADLOCK
        )

        assert _SCORE_WRONG_FALSE == self.prop_call.compute_score(
            CATEGORY_WRONG, RESULT_FALSE_REACH
        )
        assert _SCORE_WRONG_TRUE == self.prop_call.compute_score(
            CATEGORY_WRONG, RESULT_TRUE_PROP
        )
        assert _SCORE_WRONG_FALSE == self.prop_memsafety.compute_score(
            CATEGORY_WRONG, RESULT_FALSE_MEMTRACK
        )
        assert _SCORE_WRONG_TRUE == self.prop_memsafety.compute_score(
            CATEGORY_WRONG, RESULT_TRUE_PROP
        )
        assert _SCORE_WRONG_FALSE == self.prop_memsafety.compute_score(
            CATEGORY_WRONG, RESULT_FALSE_DEREF
        )
        assert _SCORE_WRONG_FALSE == self.prop_termination.compute_score(
            CATEGORY_WRONG, RESULT_FALSE_TERMINATION
        )
        assert _SCORE_WRONG_TRUE == self.prop_termination.compute_score(
            CATEGORY_WRONG, RESULT_TRUE_PROP
        )
        assert _SCORE_WRONG_FALSE == self.prop_overflow.compute_score(
            CATEGORY_WRONG, RESULT_FALSE_OVERFLOW
        )
        assert _SCORE_WRONG_TRUE == self.prop_overflow.compute_score(
            CATEGORY_WRONG, RESULT_TRUE_PROP
        )
        assert _SCORE_WRONG_FALSE == self.prop_deadlock.compute_score(
            CATEGORY_WRONG, RESULT_FALSE_OVERFLOW
        )
        assert _SCORE_WRONG_TRUE == self.prop_deadlock.compute_score(
            CATEGORY_WRONG, RESULT_TRUE_PROP
        )

    def test_result_classification(self):
        assert RESULT_CLASS_TRUE == get_result_classification(RESULT_TRUE_PROP)

        assert RESULT_CLASS_FALSE == get_result_classification(RESULT_FALSE_REACH)
        assert RESULT_CLASS_FALSE == get_result_classification(RESULT_FALSE_DEREF)
        assert RESULT_CLASS_FALSE == get_result_classification(RESULT_FALSE_FREE)
        assert RESULT_CLASS_FALSE == get_result_classification(RESULT_FALSE_MEMTRACK)
        assert RESULT_CLASS_FALSE == get_result_classification(RESULT_FALSE_TERMINATION)
        assert RESULT_CLASS_FALSE == get_result_classification(RESULT_FALSE_OVERFLOW)
        assert RESULT_CLASS_FALSE == get_result_classification(RESULT_FALSE_PROP)
        assert RESULT_CLASS_FALSE == get_result_classification(
            RESULT_FALSE_PROP + "(test)"
        )

        assert RESULT_CLASS_OTHER == get_result_classification(RESULT_DONE)
        assert RESULT_CLASS_OTHER == get_result_classification(RESULT_UNKNOWN)
        assert RESULT_CLASS_OTHER == get_result_classification("KILLED")
        assert RESULT_CLASS_OTHER == get_result_classification("TIMEOUT")
        assert RESULT_CLASS_OTHER == get_result_classification("")

    def test_result_category_true(self):
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(True), RESULT_TRUE_PROP, [self.prop_call]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(False), RESULT_TRUE_PROP, [self.prop_call]
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(True), RESULT_TRUE_PROP, [self.prop_memsafety]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(False, "valid-memtrack"),
            RESULT_TRUE_PROP,
            [self.prop_memsafety],
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(True), RESULT_TRUE_PROP, [self.prop_memcleanup]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(False), RESULT_TRUE_PROP, [self.prop_memcleanup]
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(True), RESULT_TRUE_PROP, [self.prop_termination]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(False), RESULT_TRUE_PROP, [self.prop_termination]
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(True), RESULT_TRUE_PROP, [self.prop_overflow]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(False), RESULT_TRUE_PROP, [self.prop_overflow]
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(True), RESULT_TRUE_PROP, [self.prop_deadlock]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(False), RESULT_TRUE_PROP, [self.prop_deadlock]
        )

        test_prop = Property("dummy.prp", True, "test prop")
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(True), RESULT_TRUE_PROP, [test_prop]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(False), RESULT_TRUE_PROP, [test_prop]
        )

        test_prop = Property("dummy.prp", True, "test prop")
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(True), RESULT_TRUE_PROP, [test_prop]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(False, "a"), RESULT_TRUE_PROP, [test_prop]
        )

    def test_result_category_false(self):
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_REACH, [self.prop_call]
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(False), RESULT_FALSE_REACH, [self.prop_call]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_DEREF, [self.prop_memsafety]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_FREE, [self.prop_memsafety]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_MEMTRACK, [self.prop_memsafety]
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(False, "valid-deref"),
            RESULT_FALSE_DEREF,
            [self.prop_memsafety],
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(False, "valid-free"),
            RESULT_FALSE_FREE,
            [self.prop_memsafety],
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(False, "valid-memtrack"),
            RESULT_FALSE_MEMTRACK,
            [self.prop_memsafety],
        )
        assert CATEGORY_UNKNOWN == get_result_category(
            self.expected_result(False, "valid-deref"),
            RESULT_FALSE_FREE,
            [self.prop_memsafety],
        )
        assert CATEGORY_UNKNOWN == get_result_category(
            self.expected_result(False, "valid-free"),
            RESULT_FALSE_MEMTRACK,
            [self.prop_memsafety],
        )
        assert CATEGORY_UNKNOWN == get_result_category(
            self.expected_result(False, "valid-memtrack"),
            RESULT_FALSE_DEREF,
            [self.prop_memsafety],
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True),
            RESULT_FALSE_TERMINATION,
            [self.prop_termination],
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(False),
            RESULT_FALSE_TERMINATION,
            [self.prop_termination],
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_OVERFLOW, [self.prop_overflow]
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(False), RESULT_FALSE_OVERFLOW, [self.prop_overflow]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_DEADLOCK, [self.prop_deadlock]
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(False), RESULT_FALSE_DEADLOCK, [self.prop_deadlock]
        )

        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_PROP, [self.prop_call]
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(False), RESULT_FALSE_PROP, [self.prop_call]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_PROP, [self.prop_termination]
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(False), RESULT_FALSE_PROP, [self.prop_termination]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_PROP, [self.prop_overflow]
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(False), RESULT_FALSE_PROP, [self.prop_overflow]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_PROP, [self.prop_deadlock]
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(False), RESULT_FALSE_PROP, [self.prop_deadlock]
        )

        test_prop = Property("dummy.prp", True, "test prop")
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_PROP, [test_prop]
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(False), RESULT_FALSE_PROP, [test_prop]
        )
        # arbitrary subproperties allowed if property does not specify one
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(False), RESULT_FALSE_PROP + "(a)", [test_prop]
        )

        test_prop = Property("dummy.prp", True, "test prop")
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_PROP, [test_prop]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_PROP + "(a)", [test_prop]
        )
        assert CATEGORY_CORRECT == get_result_category(
            self.expected_result(False, "a"), RESULT_FALSE_PROP + "(a)", [test_prop]
        )

    def test_result_category_different_false_result(self):
        expected_result_false = self.expected_result(False)
        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_DEREF, [self.prop_call]
        )
        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_TERMINATION, [self.prop_call]
        )
        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_OVERFLOW, [self.prop_call]
        )

        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_REACH, [self.prop_termination]
        )
        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_DEREF, [self.prop_termination]
        )
        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_OVERFLOW, [self.prop_termination]
        )

        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_REACH, [self.prop_sat]
        )
        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_DEREF, [self.prop_sat]
        )
        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_TERMINATION, [self.prop_sat]
        )
        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_OVERFLOW, [self.prop_sat]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_PROP, [self.prop_sat]
        )
        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_PROP, [self.prop_sat]
        )

        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_REACH, [self.prop_overflow]
        )
        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_DEREF, [self.prop_overflow]
        )
        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_TERMINATION, [self.prop_overflow]
        )

        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_REACH, [self.prop_deadlock]
        )
        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_DEREF, [self.prop_deadlock]
        )
        assert CATEGORY_CORRECT == get_result_category(
            expected_result_false, RESULT_FALSE_TERMINATION, [self.prop_deadlock]
        )

        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_OVERFLOW, [self.prop_call]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_REACH, [self.prop_termination]
        )
        assert CATEGORY_WRONG == get_result_category(
            self.expected_result(True), RESULT_FALSE_PROP, [self.prop_memsafety]
        )
        assert CATEGORY_UNKNOWN == get_result_category(
            self.expected_result(False, "valid-deref"),
            RESULT_FALSE_PROP,
            [self.prop_memsafety],
        )
        assert CATEGORY_UNKNOWN == get_result_category(
            self.expected_result(False, "valid-free"),
            RESULT_FALSE_PROP,
            [self.prop_memsafety],
        )
        assert CATEGORY_UNKNOWN == get_result_category(
            self.expected_result(False, "valid-memtrack"),
            RESULT_FALSE_PROP,
            [self.prop_memsafety],
        )

        test_prop = Property("dummy.prp", True, "test prop")
        assert CATEGORY_UNKNOWN == get_result_category(
            self.expected_result(False, "a"), RESULT_FALSE_PROP, [test_prop]
        )

    def test_result_category_no_property(self):
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(True), RESULT_TRUE_PROP, []
        )
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(False), RESULT_TRUE_PROP, []
        )
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(True), RESULT_TRUE_PROP, []
        )
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(False, "valid-memtrack.c"), RESULT_TRUE_PROP, []
        )
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(True), RESULT_TRUE_PROP, []
        )
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(False), RESULT_TRUE_PROP, []
        )
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(True), RESULT_TRUE_PROP, []
        )
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(False), RESULT_TRUE_PROP, []
        )

    def test_result_category_no_expected_result(self):
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(None), RESULT_TRUE_PROP, [self.prop_call]
        )
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(None), RESULT_FALSE_PROP, [self.prop_call]
        )
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(None), RESULT_TRUE_PROP, [self.prop_memsafety]
        )
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(None), RESULT_FALSE_FREE, [self.prop_memsafety]
        )
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(None), RESULT_TRUE_PROP, [self.prop_termination]
        )
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(None), RESULT_FALSE_PROP, [self.prop_termination]
        )

        assert CATEGORY_MISSING == get_result_category(
            {}, RESULT_TRUE_PROP, [self.prop_call]
        )
        assert CATEGORY_MISSING == get_result_category(
            {}, RESULT_FALSE_PROP, [self.prop_call]
        )
        assert CATEGORY_MISSING == get_result_category(
            {}, RESULT_TRUE_PROP, [self.prop_memsafety]
        )
        assert CATEGORY_MISSING == get_result_category(
            {}, RESULT_FALSE_FREE, [self.prop_memsafety]
        )
        assert CATEGORY_MISSING == get_result_category(
            {}, RESULT_TRUE_PROP, [self.prop_termination]
        )
        assert CATEGORY_MISSING == get_result_category(
            {}, RESULT_FALSE_PROP, [self.prop_termination]
        )

    def test_result_category_different_property(self):
        def other_expected_result(result, subcategory=None):
            return {"different-file.prp": ExpectedResult(result, subcategory)}

        assert CATEGORY_MISSING == get_result_category(
            other_expected_result(True), RESULT_TRUE_PROP, [self.prop_termination]
        )
        assert CATEGORY_MISSING == get_result_category(
            other_expected_result(False), RESULT_TRUE_PROP, [self.prop_termination]
        )
        assert CATEGORY_MISSING == get_result_category(
            other_expected_result(True), RESULT_TRUE_PROP, [self.prop_call]
        )
        assert CATEGORY_MISSING == get_result_category(
            other_expected_result(False, "valid-memtrack"),
            RESULT_TRUE_PROP,
            [self.prop_call],
        )
        assert CATEGORY_MISSING == get_result_category(
            other_expected_result(True), RESULT_TRUE_PROP, [self.prop_call]
        )
        assert CATEGORY_MISSING == get_result_category(
            other_expected_result(False), RESULT_TRUE_PROP, [self.prop_call]
        )

    def test_result_category_other(self):
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(True), RESULT_DONE, [self.prop_call]
        )
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(True), RESULT_DONE, []
        )
        assert CATEGORY_MISSING == get_result_category(
            self.expected_result(None), RESULT_DONE, [self.prop_call]
        )
        assert CATEGORY_UNKNOWN == get_result_category(
            self.expected_result(True), RESULT_UNKNOWN, [self.prop_call]
        )
        assert CATEGORY_UNKNOWN == get_result_category(
            self.expected_result(True), RESULT_UNKNOWN, []
        )
        assert CATEGORY_UNKNOWN == get_result_category(
            self.expected_result(None), RESULT_UNKNOWN, [self.prop_call]
        )
        assert CATEGORY_ERROR == get_result_category(
            self.expected_result(True), "KILLED", [self.prop_call]
        )
        assert CATEGORY_ERROR == get_result_category(
            self.expected_result(True), "TIMEOUT", [self.prop_call]
        )
        assert CATEGORY_ERROR == get_result_category(
            self.expected_result(True), "", [self.prop_call]
        )
