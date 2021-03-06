/* eslint react/prop-types: 0 */
import React from 'react';

export default function Indicator({ number }) {
  let circleColor = '#C4C4C4';
  if (number > 1.25) {
    circleColor = '#F45656';
  } else if (number > 1.15) {
    circleColor = '#F4B556';
  } else if (number > 0.85) {
    circleColor = '#C4C4C4';
  } else if (number > 0.75) {
    circleColor = '#B3D2A0';
  } else {
    circleColor = '#8BD45F';
  }
  return (
    <svg height="100%" width="100%">
      <circle cx="50%" cy="50%" r="20%" fill={circleColor} />
    </svg>
  );
}
