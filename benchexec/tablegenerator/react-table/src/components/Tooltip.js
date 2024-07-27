// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";

const tooltipStyles = {
  visibility: "hidden",
  width: "250px",
  textAlign: "center",
  borderRadius: "6px",
  padding: "5px",
  position: "absolute",
  zIndex: 200,
  left: "150%", // Position the tooltip to the right of the icon
  top: "50%",
  transform: "translateY(-50%)", // Center the tooltip vertically
  marginLeft: "10px",
  opacity: 0,
  transition: "opacity 0.3s",
  backgroundColor: "#f9f9f9",
  color: "#000",
  fontSize: "12px", // Smaller font size
  fontWeight: "lighter",
};

const iconContainerStyles = {
  position: "relative",
  display: "inline-block",
};

const iconStyles = {
  cursor: "pointer",
};

const IconWithTooltip = ({ message }) => {
  return (
    <div
      style={iconContainerStyles}
      onMouseEnter={(e) => {
        const tooltip = e.currentTarget.querySelector(".tooltip");
        tooltip.style.visibility = "visible";
        tooltip.style.opacity = 1;
      }}
      onMouseLeave={(e) => {
        const tooltip = e.currentTarget.querySelector(".tooltip");
        tooltip.style.visibility = "hidden";
        tooltip.style.opacity = 0;
      }}
    >
      <FontAwesomeIcon icon={faInfoCircle} style={iconStyles} />
      <span className="tooltip" style={tooltipStyles}>
        {message}
      </span>
    </div>
  );
};

export default IconWithTooltip;
