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
            assert "Not a valid expected verdict" in str(exc_info.value)

        test("foo")
        test("unknown")
        test("true()")


class TestResult:
    @classmethod
    def setup_class(cls):
        cls.longMessage = True
        logging.disable(logging.CRITICAL)

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
            ) == Property.create(filename), (
                "different result for property file with content\n" + content
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
        assert self.prop_call.max_score(ExpectedResult(None, None)) == 0
        assert self.prop_call.max_score(None) is None

    def test_Property_max_score_smt(self):
        assert self.prop_sat.max_score(ExpectedResult(True, None)) is None
        assert self.prop_sat.max_score(ExpectedResult(False, None)) is None

    def test_Property_max_score_svcomp(self):
        assert (
            self.prop_call.max_score(ExpectedResult(True, None)) == _SCORE_CORRECT_TRUE
        )
        assert (
            self.prop_call.max_score(ExpectedResult(False, None))
            == _SCORE_CORRECT_FALSE
        )

        assert (
            self.prop_memsafety.max_score(ExpectedResult(True, None))
            == _SCORE_CORRECT_TRUE
        )
        assert (
            self.prop_memsafety.max_score(ExpectedResult(False, None))
            == _SCORE_CORRECT_FALSE
        )
        assert (
            self.prop_memsafety.max_score(ExpectedResult(False, "valid-free"))
            == _SCORE_CORRECT_FALSE
        )

    def test_Property_compute_score_not_available(self):
        assert self.prop_call.compute_score(CATEGORY_MISSING, RESULT_TRUE_PROP) == 0
        assert self.prop_call.compute_score(CATEGORY_ERROR, RESULT_TRUE_PROP) == 0
        assert self.prop_call.compute_score(CATEGORY_UNKNOWN, RESULT_TRUE_PROP) == 0

    def test_Property_compute_score_smt(self):
        assert self.prop_sat.compute_score(CATEGORY_CORRECT, RESULT_TRUE_PROP) is None
        assert self.prop_sat.compute_score(CATEGORY_WRONG, RESULT_TRUE_PROP) is None

    def test_Property_compute_score_svcomp(self):
        assert (
            self.prop_call.compute_score(CATEGORY_CORRECT, RESULT_TRUE_PROP)
            == _SCORE_CORRECT_TRUE
        )
        assert (
            self.prop_call.compute_score(CATEGORY_CORRECT, RESULT_FALSE_REACH)
            == _SCORE_CORRECT_FALSE
        )
        assert (
            self.prop_memsafety.compute_score(CATEGORY_CORRECT, RESULT_TRUE_PROP)
            == _SCORE_CORRECT_TRUE
        )
        assert (
            self.prop_memsafety.compute_score(CATEGORY_CORRECT, RESULT_FALSE_MEMTRACK)
            == _SCORE_CORRECT_FALSE
        )
        assert (
            self.prop_termination.compute_score(CATEGORY_CORRECT, RESULT_TRUE_PROP)
            == _SCORE_CORRECT_TRUE
        )
        assert (
            self.prop_termination.compute_score(
                CATEGORY_CORRECT, RESULT_FALSE_TERMINATION
            )
            == _SCORE_CORRECT_FALSE
        )
        assert (
            self.prop_overflow.compute_score(CATEGORY_CORRECT, RESULT_TRUE_PROP)
            == _SCORE_CORRECT_TRUE
        )
        assert (
            self.prop_overflow.compute_score(CATEGORY_CORRECT, RESULT_FALSE_OVERFLOW)
            == _SCORE_CORRECT_FALSE
        )
        assert (
            self.prop_deadlock.compute_score(CATEGORY_CORRECT, RESULT_TRUE_PROP)
            == _SCORE_CORRECT_TRUE
        )
        assert (
            self.prop_deadlock.compute_score(CATEGORY_CORRECT, RESULT_FALSE_DEADLOCK)
            == _SCORE_CORRECT_FALSE
        )

        assert (
            self.prop_call.compute_score(CATEGORY_WRONG, RESULT_FALSE_REACH)
            == _SCORE_WRONG_FALSE
        )
        assert (
            self.prop_call.compute_score(CATEGORY_WRONG, RESULT_TRUE_PROP)
            == _SCORE_WRONG_TRUE
        )
        assert (
            self.prop_memsafety.compute_score(CATEGORY_WRONG, RESULT_FALSE_MEMTRACK)
            == _SCORE_WRONG_FALSE
        )
        assert (
            self.prop_memsafety.compute_score(CATEGORY_WRONG, RESULT_TRUE_PROP)
            == _SCORE_WRONG_TRUE
        )
        assert (
            self.prop_memsafety.compute_score(CATEGORY_WRONG, RESULT_FALSE_DEREF)
            == _SCORE_WRONG_FALSE
        )
        assert (
            self.prop_termination.compute_score(
                CATEGORY_WRONG, RESULT_FALSE_TERMINATION
            )
            == _SCORE_WRONG_FALSE
        )
        assert (
            self.prop_termination.compute_score(CATEGORY_WRONG, RESULT_TRUE_PROP)
            == _SCORE_WRONG_TRUE
        )
        assert (
            self.prop_overflow.compute_score(CATEGORY_WRONG, RESULT_FALSE_OVERFLOW)
            == _SCORE_WRONG_FALSE
        )
        assert (
            self.prop_overflow.compute_score(CATEGORY_WRONG, RESULT_TRUE_PROP)
            == _SCORE_WRONG_TRUE
        )
        assert (
            self.prop_deadlock.compute_score(CATEGORY_WRONG, RESULT_FALSE_OVERFLOW)
            == _SCORE_WRONG_FALSE
        )
        assert (
            self.prop_deadlock.compute_score(CATEGORY_WRONG, RESULT_TRUE_PROP)
            == _SCORE_WRONG_TRUE
        )

    def test_result_classification(self):
        assert get_result_classification(RESULT_TRUE_PROP) == RESULT_CLASS_TRUE

        assert get_result_classification(RESULT_FALSE_REACH) == RESULT_CLASS_FALSE
        assert get_result_classification(RESULT_FALSE_DEREF) == RESULT_CLASS_FALSE
        assert get_result_classification(RESULT_FALSE_FREE) == RESULT_CLASS_FALSE
        assert get_result_classification(RESULT_FALSE_MEMTRACK) == RESULT_CLASS_FALSE
        assert get_result_classification(RESULT_FALSE_TERMINATION) == RESULT_CLASS_FALSE
        assert get_result_classification(RESULT_FALSE_OVERFLOW) == RESULT_CLASS_FALSE
        assert get_result_classification(RESULT_FALSE_PROP) == RESULT_CLASS_FALSE
        assert (
            get_result_classification(RESULT_FALSE_PROP + "(test)")
            == RESULT_CLASS_FALSE
        )

        assert get_result_classification(RESULT_DONE) == RESULT_CLASS_OTHER
        assert get_result_classification(RESULT_UNKNOWN) == RESULT_CLASS_OTHER
        assert get_result_classification("KILLED") == RESULT_CLASS_OTHER
        assert get_result_classification("TIMEOUT") == RESULT_CLASS_OTHER
        assert get_result_classification("") == RESULT_CLASS_OTHER

    def test_result_category_true(self):
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_TRUE_PROP,
                [self.prop_call],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(False),
                RESULT_TRUE_PROP,
                [self.prop_call],
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_TRUE_PROP,
                [self.prop_memsafety],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(False, "valid-memtrack"),
                RESULT_TRUE_PROP,
                [self.prop_memsafety],
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_TRUE_PROP,
                [self.prop_memcleanup],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(False),
                RESULT_TRUE_PROP,
                [self.prop_memcleanup],
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_TRUE_PROP,
                [self.prop_termination],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(False),
                RESULT_TRUE_PROP,
                [self.prop_termination],
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_TRUE_PROP,
                [self.prop_overflow],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(False),
                RESULT_TRUE_PROP,
                [self.prop_overflow],
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_TRUE_PROP,
                [self.prop_deadlock],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(False),
                RESULT_TRUE_PROP,
                [self.prop_deadlock],
            )
            == CATEGORY_WRONG
        )

        test_prop = Property("dummy.prp", True, "test prop")
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_TRUE_PROP,
                [test_prop],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(False),
                RESULT_TRUE_PROP,
                [test_prop],
            )
            == CATEGORY_WRONG
        )

        test_prop = Property("dummy.prp", True, "test prop")
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_TRUE_PROP,
                [test_prop],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(False, "a"),
                RESULT_TRUE_PROP,
                [test_prop],
            )
            == CATEGORY_WRONG
        )

    def test_result_category_false(self):
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_FALSE_REACH,
                [self.prop_call],
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(False),
                RESULT_FALSE_REACH,
                [self.prop_call],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_FALSE_DEREF,
                [self.prop_memsafety],
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_FALSE_FREE,
                [self.prop_memsafety],
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_FALSE_MEMTRACK,
                [self.prop_memsafety],
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(False, "valid-deref"),
                RESULT_FALSE_DEREF,
                [self.prop_memsafety],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(False, "valid-free"),
                RESULT_FALSE_FREE,
                [self.prop_memsafety],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(False, "valid-memtrack"),
                RESULT_FALSE_MEMTRACK,
                [self.prop_memsafety],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(False, "valid-deref"),
                RESULT_FALSE_FREE,
                [self.prop_memsafety],
            )
            == CATEGORY_UNKNOWN
        )
        assert (
            get_result_category(
                self.expected_result(False, "valid-free"),
                RESULT_FALSE_MEMTRACK,
                [self.prop_memsafety],
            )
            == CATEGORY_UNKNOWN
        )
        assert (
            get_result_category(
                self.expected_result(False, "valid-memtrack"),
                RESULT_FALSE_DEREF,
                [self.prop_memsafety],
            )
            == CATEGORY_UNKNOWN
        )
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_FALSE_TERMINATION,
                [self.prop_termination],
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(False),
                RESULT_FALSE_TERMINATION,
                [self.prop_termination],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_FALSE_OVERFLOW,
                [self.prop_overflow],
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(False),
                RESULT_FALSE_OVERFLOW,
                [self.prop_overflow],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(True), RESULT_FALSE_DEADLOCK, [self.prop_deadlock]
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(False),
                RESULT_FALSE_DEADLOCK,
                [self.prop_deadlock],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_FALSE_PROP,
                [self.prop_call],
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(False),
                RESULT_FALSE_PROP,
                [self.prop_call],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_FALSE_PROP,
                [self.prop_termination],
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(False),
                RESULT_FALSE_PROP,
                [self.prop_termination],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_FALSE_PROP,
                [self.prop_overflow],
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(False),
                RESULT_FALSE_PROP,
                [self.prop_overflow],
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_FALSE_PROP,
                [self.prop_deadlock],
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(False),
                RESULT_FALSE_PROP,
                [self.prop_deadlock],
            )
            == CATEGORY_CORRECT
        )

        test_prop = Property("dummy.prp", True, "test prop")
        assert (
            get_result_category(
                self.expected_result(True),
                RESULT_FALSE_PROP,
                [test_prop],
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(False),
                RESULT_FALSE_PROP,
                [test_prop],
            )
            == CATEGORY_CORRECT
        )
        # arbitrary subproperties allowed if property does not specify one
        assert (
            get_result_category(
                self.expected_result(False),
                RESULT_FALSE_PROP + "(a)",
                [test_prop],
            )
            == CATEGORY_CORRECT
        )

        test_prop = Property("dummy.prp", True, "test prop")
        assert (
            get_result_category(
                self.expected_result(True), RESULT_FALSE_PROP, [test_prop]
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(True), RESULT_FALSE_PROP + "(a)", [test_prop]
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(False, "a"), RESULT_FALSE_PROP + "(a)", [test_prop]
            )
            == CATEGORY_CORRECT
        )

    def test_result_category_different_false_result(self):
        expected_result_false = self.expected_result(False)
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_DEREF, [self.prop_call]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_TERMINATION, [self.prop_call]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_OVERFLOW, [self.prop_call]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_REACH, [self.prop_termination]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_DEREF, [self.prop_termination]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_OVERFLOW, [self.prop_termination]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_REACH, [self.prop_sat]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_DEREF, [self.prop_sat]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_TERMINATION, [self.prop_sat]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_OVERFLOW, [self.prop_sat]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(True), RESULT_FALSE_PROP, [self.prop_sat]
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_PROP, [self.prop_sat]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_REACH, [self.prop_overflow]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_DEREF, [self.prop_overflow]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_TERMINATION, [self.prop_overflow]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_REACH, [self.prop_deadlock]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_DEREF, [self.prop_deadlock]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                expected_result_false, RESULT_FALSE_TERMINATION, [self.prop_deadlock]
            )
            == CATEGORY_CORRECT
        )
        assert (
            get_result_category(
                self.expected_result(True), RESULT_FALSE_OVERFLOW, [self.prop_call]
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(True), RESULT_FALSE_REACH, [self.prop_termination]
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(True), RESULT_FALSE_PROP, [self.prop_memsafety]
            )
            == CATEGORY_WRONG
        )
        assert (
            get_result_category(
                self.expected_result(False, "valid-deref"),
                RESULT_FALSE_PROP,
                [self.prop_memsafety],
            )
            == CATEGORY_UNKNOWN
        )
        assert (
            get_result_category(
                self.expected_result(False, "valid-free"),
                RESULT_FALSE_PROP,
                [self.prop_memsafety],
            )
            == CATEGORY_UNKNOWN
        )
        assert (
            get_result_category(
                self.expected_result(False, "valid-memtrack"),
                RESULT_FALSE_PROP,
                [self.prop_memsafety],
            )
            == CATEGORY_UNKNOWN
        )
        test_prop = Property("dummy.prp", True, "test prop")
        assert (
            get_result_category(
                self.expected_result(False, "a"), RESULT_FALSE_PROP, [test_prop]
            )
            == CATEGORY_UNKNOWN
        )

    def test_result_category_no_property(self):
        assert (
            get_result_category(self.expected_result(True), RESULT_TRUE_PROP, [])
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(self.expected_result(False), RESULT_TRUE_PROP, [])
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(self.expected_result(True), RESULT_TRUE_PROP, [])
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(
                self.expected_result(False, "valid-memtrack.c"), RESULT_TRUE_PROP, []
            )
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(self.expected_result(True), RESULT_TRUE_PROP, [])
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(self.expected_result(False), RESULT_TRUE_PROP, [])
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(self.expected_result(True), RESULT_TRUE_PROP, [])
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(self.expected_result(False), RESULT_TRUE_PROP, [])
            == CATEGORY_MISSING
        )

    def test_result_category_no_expected_result(self):
        assert (
            get_result_category(
                self.expected_result(None), RESULT_TRUE_PROP, [self.prop_call]
            )
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(
                self.expected_result(None), RESULT_FALSE_PROP, [self.prop_call]
            )
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(
                self.expected_result(None), RESULT_TRUE_PROP, [self.prop_memsafety]
            )
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(
                self.expected_result(None), RESULT_FALSE_FREE, [self.prop_memsafety]
            )
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(
                self.expected_result(None), RESULT_TRUE_PROP, [self.prop_termination]
            )
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(
                self.expected_result(None), RESULT_FALSE_PROP, [self.prop_termination]
            )
            == CATEGORY_MISSING
        )
        assert (
            get_result_category({}, RESULT_TRUE_PROP, [self.prop_call])
            == CATEGORY_MISSING
        )
        assert (
            get_result_category({}, RESULT_FALSE_PROP, [self.prop_call])
            == CATEGORY_MISSING
        )
        assert (
            get_result_category({}, RESULT_TRUE_PROP, [self.prop_memsafety])
            == CATEGORY_MISSING
        )
        assert (
            get_result_category({}, RESULT_FALSE_FREE, [self.prop_memsafety])
            == CATEGORY_MISSING
        )
        assert (
            get_result_category({}, RESULT_TRUE_PROP, [self.prop_termination])
            == CATEGORY_MISSING
        )
        assert (
            get_result_category({}, RESULT_FALSE_PROP, [self.prop_termination])
            == CATEGORY_MISSING
        )

    def test_result_category_different_property(self):
        def other_expected_result(result, subcategory=None):
            return {"different-file.prp": ExpectedResult(result, subcategory)}

        assert (
            get_result_category(
                other_expected_result(True), RESULT_TRUE_PROP, [self.prop_termination]
            )
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(
                other_expected_result(False), RESULT_TRUE_PROP, [self.prop_termination]
            )
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(
                other_expected_result(True), RESULT_TRUE_PROP, [self.prop_call]
            )
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(
                other_expected_result(False, "valid-memtrack"),
                RESULT_TRUE_PROP,
                [self.prop_call],
            )
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(
                other_expected_result(True), RESULT_TRUE_PROP, [self.prop_call]
            )
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(
                other_expected_result(False), RESULT_TRUE_PROP, [self.prop_call]
            )
            == CATEGORY_MISSING
        )

    def test_result_category_other(self):
        assert (
            get_result_category(
                self.expected_result(True), RESULT_DONE, [self.prop_call]
            )
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(self.expected_result(True), RESULT_DONE, [])
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(
                self.expected_result(None), RESULT_DONE, [self.prop_call]
            )
            == CATEGORY_MISSING
        )
        assert (
            get_result_category(
                self.expected_result(True), RESULT_UNKNOWN, [self.prop_call]
            )
            == CATEGORY_UNKNOWN
        )
        assert (
            get_result_category(self.expected_result(True), RESULT_UNKNOWN, [])
            == CATEGORY_UNKNOWN
        )
        assert (
            get_result_category(
                self.expected_result(None), RESULT_UNKNOWN, [self.prop_call]
            )
            == CATEGORY_UNKNOWN
        )
        assert (
            get_result_category(self.expected_result(True), "KILLED", [self.prop_call])
            == CATEGORY_ERROR
        )
        assert (
            get_result_category(self.expected_result(True), "TIMEOUT", [self.prop_call])
            == CATEGORY_ERROR
        )
        assert (
            get_result_category(self.expected_result(True), "", [self.prop_call])
            == CATEGORY_ERROR
        )
