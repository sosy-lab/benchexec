# Multi-property verification

Multi-property verification is aimed at checking several properties
in one verification run and providing status for each property.
For more information about multi-property verification
please read our paper [On-The-Fly Decomposition of Specifications in Software Model Checking](https://www.sosy-lab.org/~dbeyer/spec-decomposition/2016-FSE.On-the-Fly_Decomposition_of_Specifications_in_Software_Model_Checking.pdf).

### Requirements for multi-property verification
 * Corresponding verification tool should support multi-property verification
   (i.e., take several properties as input and produce status for each property
   in one verification run).
 * Method `determine_result_for_property` needs to be overridden
   in corresponding tool-info module.

### Set multi-property verification mode
In order to use multi-property verification in `benchexec`
attribute `kind` of `<propertyfile>` tag should be set to `multiproperty` value.
By default value `composite` (check all specified properties as a single composite property) is used.

### Specify several properties
The property file (which is specified by `<propertyfile>` tag) 
may contain several properties, for example:

    CHECK( init(main()), LTL(G valid-free) )
    CHECK( init(main()), LTL(G valid-deref) )
    CHECK( init(main()), LTL(G valid-memtrack) )

Currently only the following properties are supported (each property is defined [here](properties/INDEX.md))
 
 * `termination`;
 * `no-overflow`;
 * `no-deadlock`;
 * `valid-deref`;
 * `valid-free`;
 * `valid-memtrack`;
 * `unreach-call`.

For properties `unreach-call` different error functions may be specified, for example:

    CHECK( init(main()), LTL(G ! call(error_function_1())) )
    CHECK( init(main()), LTL(G ! call(error_function_2())) )

In this case property name contains error function name, for example: `unreach-call(error_function_1)`.

In general case it is possible to specify any combination of properties in the property file.
Note that verification tool may not support each combination.

### Get correct results
In order to provide expected statuses for each property, verification tasks
for multi-property verification has to be specified in YAML configuration files in the following format:

    input_files:
      - <...>
    expected_results:
      property_name_1:
        correct: true|false
      property_name_2:
        correct: true|false

Tag `input_files` specifies one or more source file for verification;
tag `expected_results` provides expected status (`true` or `false`)
for each property.

Note that this file should be specified in `benchexec` as a source file:
`<include>*.yml</include>`.

### Provide results for runs
For each given property `benchexec` provides separated status as a result
in the following format:

    <column title="status (<property_name>)" value="actual_status"/>

Note that `actual_status` can be one of the `RESULT_*` constants of the 
[`result` module](https://github.com/sosy-lab/benchexec/blob/master/benchexec/result.py).

In case of global errors (parsing failed, out of memory, etc.) each property
gets unknown status.
