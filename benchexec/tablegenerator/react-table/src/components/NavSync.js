// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import { useMemo } from "react";
import { useNavigationType } from "react-router-dom";

// This component is used to sync the navigation URL of POP events
// This component does not render anything, and is a workaround to use a hook in the parent class component.
// This logic should be moved to the parent class component in the future after the same is converted to a functional component.

/*
 * @param {Object} props - The props object
 * @param {Function} props.updateState - The function to update the state of the parent component
 * @param {Function} props.updateFiltersFromUrl - The function to update the filters from the URL
 */
const NavSync = (props) => {
  const navType = useNavigationType();
  useMemo(() => {
    props.updateState();
    if (navType === "POP") {
      props.updateFiltersFromUrl();
    }

    // We only want to update the state of the parent component when the navigation type changes
    // and not when the other props change due to rerendering of the parent component
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navType]);

  return null;
};

export default NavSync;
