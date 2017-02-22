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
If this attribute is not set (by default) or set to the other value then all specified properties 
will be considered as a single composite property.

### Specify several properties
The property file (which is specified by `<propertyfile>` tag) 
may contain several properties, for example:

    CHECK( init(main()), LTL(G valid-free) )
    CHECK( init(main()), LTL(G valid-deref) )
    CHECK( init(main()), LTL(G valid-memtrack) )

In this case property name is equal to corresponding SV-Comp category:
`valid-deref`, `valid-free`, `valid-memtrack`, `no-overflow`, `no-deadlock`, `termination`.

Also different error functions may be used in `unreach-call` properties:

    CHECK( init(main()), LTL(G ! call(error_function_1())) )
    CHECK( init(main()), LTL(G ! call(error_function_2())) )

In this case property name contains error function name: `unreach-call,error_function_1`.

In general case it is possible to specify any combination of properties in the property file.
Note that verification tool may not support each combination.

### Provide results in xml file
For each given property `benchexec` provides separated status as a result
in the following format:

    <column title="status (<property_name>)" value="true|false|unknown"/>

In case of global errors (parsing failed, out of memory, etc.) each property
gets unknown status.

### Get correct results
Correct results for each task are placed in YAML configuration file
`<task_file_name>.yml` in the following format:

    correct results:
      property1: true|false|unknown
      ...
      propertyN: true|false|unknown

`benchexec` uses information from this configuration file to decide 
whether obtained results are correct or not and to compute a score.
